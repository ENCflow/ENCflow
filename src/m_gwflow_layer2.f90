module m_gwflow_layer2
  ! ============== 風化基岩層(第2地下水層)モジュール(§16) ==============
  ! 土層(sd, sy0, s%hg)の直下に厚さ d2・比湧水量 sy2 の層を挟む加算的
  ! プロセス。&list_gwflow の f_gwlayer2=1 で有効化(無効時は s%hg2 を
  ! 確保せず、呼び出しもハロ交換も行わない = メモリ・CPU ゼロ追加)。
  !
  ! 【毎 gwflow ステップの処理】
  !  (1) 鉛直浸透(層1→2): fx = min(kv2·dts, s%hg, cap2 − hg2) の
  !      定数浸透能・容量制限。反対称適用(s%hg から引き s%hg2 に足す)
  !  (2) 側方 Darcy 流(層2内。gw2_ksh_mmh > 0 のとき):
  !      m_gwflow_lateral の層非依存カーネル lateral_core を再利用。
  !      水頭 H2 = (z − sd − d2) + hg2/sy2(地表湛水結合なし)。
  !      飽和超過(hg2 > cap2)は層1へ戻し、層1の容量超過はカーネルが
  !      直列に地表へ渡す(湧出の連鎖が同一ステップで閉じる)
  !
  ! 【制約】
  !  - バケツ鉛直モデル(f_gwvertical=1)とは併用不可(底面標高
  !    z − sd − d2 に実土層 sd が要る。bucket×lateral と同じ排他。
  !    m_gwflow_init が停止する)
  !  - 蒸発散は hg2 に触れない(根群域より深い層という意味論)
  !  - 層1→2 の浸透に輸送物質(wq の cg)は同伴しない(cg2 は将来拡張。
  !    handoff 1l)
  !
  ! 【初期値】
  !  gw2_sat0(飽和度 0〜1。既定 0 = 空)の一様指定。hg2 = sat0·cap2。
  !  平衡初期分布が必要な長期計算はスピンアップ→save→restore を初期値と
  !  するワークフローを使う(分布初期値ファイルより正確。§16)
  !
  ! 【リスタート】
  !  s%hg2 はモデル私有ファイル gwflow_layer2.dat(RLE)で保存
  !  (m_gwflow_bucket ヘッダの契約5。state.dat の形式は不変)。
  !  restore 時に自ファイルが無ければ par_stop
  ! ======================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_gwflow_lateral, only : t_latlayer, gwflow_lateral_geom_init, &
                               gwflow_lateral_dtcheck, lateral_core
  use m_fileio, only : fileio_write_rle, fileio_read_rle
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : par_info, par_stop, dcp, is_root, par_halo_cell, &
                         par_gather_to, par_scatter_cell
  implicit none
  private
  public :: gwflow_layer2_init
  public :: gwflow_layer2_calc
  public :: gwflow_layer2_dispose

  ! モデル私有の設定(単一インスタンス前提。developer.md §12)
  type t_gwl2
    real :: kv = 0.0                 ! 層1→2 浸透能 (m/s)
    real :: d2 = 0.0                 ! 層厚 (m)
    real :: sy2 = 0.0                ! 比湧水量
    real :: cap = 0.0                ! 容量 d2·sy2 (m)
    logical :: lat = .false.         ! 側方流動の有効(gw2_ksh_mmh > 0)
    type(t_latlayer) :: lay          ! 側方カーネルの層係数
    logical :: initialized = .false.
  end type
  type(t_gwl2) :: gl2

contains


!----------------------------------------------------------------------
! 風化基岩層の初期化(固有グループ &list_gwflow_layer2 を自分で読む)。
! g%sd は m_gwflow_init が m_geoinfo_require_sd で確保済み
!----------------------------------------------------------------------
subroutine gwflow_layer2_init(p, g, s, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: un, ios, i, j
  real :: gw2_depth, gw2_sy, gw2_infil_mmh, gw2_ksh_mmh, gw2_sat0
  namelist /list_gwflow_layer2/ gw2_depth, gw2_sy, gw2_infil_mmh, gw2_ksh_mmh, gw2_sat0

  gw2_depth = 0.0
  gw2_sy = 0.0
  gw2_infil_mmh = 0.0
  gw2_ksh_mmh = 0.0
  gw2_sat0 = 0.0

  call par_info("reading list_gwflow_layer2 in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow_layer2, iostat=ios)
  if (ios /= 0) call par_stop("error in reading list_gwflow_layer2")
  close(un)

  if (gw2_depth <= 0.0) call par_stop("list_gwflow_layer2: gw2_depth must be > 0")
  if (gw2_sy <= 0.0 .or. gw2_sy > 1.0) then
    call par_stop("list_gwflow_layer2: gw2_sy must be in (0,1]")
  end if
  if (gw2_infil_mmh <= 0.0) call par_stop("list_gwflow_layer2: gw2_infil_mmh must be > 0")
  if (gw2_ksh_mmh < 0.0) call par_stop("list_gwflow_layer2: gw2_ksh_mmh must be >= 0")
  if (gw2_sat0 < 0.0 .or. gw2_sat0 > 1.0) then
    call par_stop("list_gwflow_layer2: gw2_sat0 must be in [0,1]")
  end if
  if (.not. allocated(g%sd)) call par_stop("gwflow_layer2: g%sd is not allocated")

  gl2%kv = gw2_infil_mmh / 1000.0 / 3600.0    ! mm/h -> m/s
  gl2%d2 = gw2_depth
  gl2%sy2 = gw2_sy
  gl2%cap = gw2_depth * gw2_sy
  gl2%lat = (gw2_ksh_mmh > 0.0)

  ! --- 状態の確保と初期値(海セル・無効セルには置かない) ---
  allocate(s%hg2(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (gw2_sat0 > 0.0) then
    ! ゾーン2 = x/sw は全域が使える(帯行 jsh:jeh は全域の有効行)
    do j = dcp%jsh, dcp%jeh
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        s%hg2(i,j) = gw2_sat0 * gl2%cap
      end do
    end do
  end if

  ! --- 側方カーネルの層係数と幾何(層1側方と共有・冪等) ---
  if (gl2%lat) then
    gl2%lay%ksh = gw2_ksh_mmh / 1000.0 / 3600.0
    gl2%lay%sy = gw2_sy
    gl2%lay%syinv = 1.0 / gw2_sy
    gl2%lay%dbot = gw2_depth
    gl2%lay%cap_const = gl2%cap
    gl2%lay%to_surface = .false.
    ! 層1側方が有効ならその diagratio/eps が既に設定済み(冪等口が勝つ)。
    ! 層2のみ有効の場合は既定値(m_swflow_enc の p_diagratio と同値)
    call gwflow_lateral_geom_init(g, 2.0 / (2.0 + sqrt(2.0)), 1.0e-3)
    call gwflow_lateral_dtcheck(g, "gwflow_layer2", gl2%lay%ksh, gl2%lay%sy, &
                                gl2%d2, dts)
  end if

  ! --- リスタート ---
  if (p%f_state_restore > 0) call restore_state(p, g, s)

  gl2%initialized = .true.
  call par_info("gwflow layer2 (weathered bedrock) enabled")
end subroutine


!----------------------------------------------------------------------
! 風化基岩層の計算(毎 gwflow ステップ。鉛直浸透→側方流動)
!----------------------------------------------------------------------
subroutine gwflow_layer2_calc(p, g, s, it, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  real, intent(in) :: dts
  integer :: i, j
  real :: fx

  if (it < 0) continue  ! 引数未使用の警告を抑制
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  ! (1) 鉛直浸透(層1→2。反対称適用。s%h に触れないため s%e の回復は不要)
  !$omp parallel do schedule(static) private(i, j, fx)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      fx = min(gl2%kv * dts, s%hg(i,j), gl2%cap - s%hg2(i,j))
      if (fx <= 0.0) cycle
      s%hg(i,j) = s%hg(i,j) - fx
      s%hg2(i,j) = s%hg2(i,j) + fx
    end do
  end do
  !$omp end parallel do

  ! (2) 側方 Darcy 流(層2内。飽和超過はカーネルが層1→地表へ直列に渡す)
  if (gl2%lat) then
    call par_halo_cell(s%hg2)
    call lateral_core(g, s, s%hg2, gl2%lay, dts)
  end if
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル gwflow_layer2.dat。契約5。§7)
!----------------------------------------------------------------------
subroutine save_state(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, allocatable :: wk(:,:)
  integer :: un
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
  else
    allocate(wk(1, 1), source = 0.0)
  end if
  call par_gather_to(wk, s%hg2)
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/gwflow_layer2.dat', form='unformatted', &
         status='replace')
    call fileio_write_rle(un, wk)
    close(un)
  end if
end subroutine


subroutine restore_state(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  logical :: found
  integer :: un

  ! 版・格子・精度の検証は m_state(check_save_info)が済ませている。
  ! 自ファイルの有無のみ確認(無ければ「保存時は層2無効だった」として
  ! ゼロ継続を許さず停止 — 意図しない水収支の断絶を防ぐ)
  fname = trim(p%dir_save)//'/gwflow_layer2.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("gwflow_layer2 の保存ファイルがありません" &
                  // "(保存時に f_gwlayer2 は有効でしたか): "//fname)
  end if

  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    close(un)
    call par_scatter_cell(wk, s%hg2)
  else
    call par_scatter_cell(dum, s%hg2)
  end if
end subroutine


!----------------------------------------------------------------------
! 風化基岩層の破棄(save は dispose で行う。契約5)
!----------------------------------------------------------------------
subroutine gwflow_layer2_dispose(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (.not. gl2%initialized) return
  if (p%f_state_save > 0) call save_state(p, g, s)
  gl2%initialized = .false.
end subroutine

end module
