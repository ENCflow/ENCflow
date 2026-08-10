module m_snow
  ! ============== 積雪・融雪プロセスモジュール(度日法。§31) ==============
  ! セル別の積雪水量 s%swe(SWE、m 水柱・幾何面積基底)1本を状態に持つ
  ! 加算的プロセス。fn_snow の指定で有効化(&list_snow。f_snow=0 で一時
  ! 無効化)。無効時は s%swe を確保せず呼び出しもしない(ゼロコスト。§0)。
  !
  ! 【毎ステップの処理(run_main が intercept_step の後・swflow の前に呼ぶ)】
  !  (1) 降雨/降雪の分離: 気温 T(m_meteo。標高減率込み=雪線の標高依存が
  !      自動で出る)の二重閾値線形混合で、遮断後降水 s%pre/s%prh を
  !      「液体分のみ」へ同率で減じ、雪分を SWE へ蓄積する。
  !      T <= snow_t_snow で全て雪、T >= snow_t_rain で全て雨。
  !  (2) 度日融雪: M = ddf·max(T − snow_t_melt, 0)。min(SWE, M·dt) を
  !      s%h へ直接投入(gv・wfrac 換算+ e 回復 = swflow の降雨適用と同型)。
  !
  ! 【s%pre の再計算契約(遮断 initloss の契約 A/B と同型)】
  !  s%pre は遮断モデル(貯留型)が毎ステップ原雨量から計算し直すため、
  !  雪の分離を in-place で掛けると上流の再計算有無で二重適用になる。
  !  本モジュールは「上流が s%pre を書き直したステップ」でスナップショット
  !  pr0/prh0 を取り、毎ステップ pr0×液体率から s%pre/s%prh を計算し直す。
  !  上流の書き直し判定は pr_fresh 引数(run_main が makepre 更新 or
  !  貯留型遮断の有無から渡す)。初回呼び出しは無条件でスナップショット。
  !
  ! 【水質との整合(§30)】
  !  s%pre が液体降水のみになるため、湿性沈着(wq_rain_conc)と
  !  buildup-washoff の雨滴項は自動的に液体分のみに作用する(降雪中の
  !  雨滴洗い出し停止=物理的に正しい)。降雪に載る沈着分は当面無視
  !  (既知の妥協。雪面沈着プール+融雪同伴放出は将来拡張)。
  !  融雪水は無溶質で h に入る(cq 不変=希釈。正しい挙動)。
  !
  ! 【妥協(文書化済みの割り切り)】
  !  積雪深・密度・冷量・再凍結・昇華・rain-on-snow の雪内保持は持たない。
  !  樹冠遮断は降雪も一括で先取りする(遮断が雪より先)。
  !  ddf の季節変化は将来拡張(HBV 流の正弦補間)。
  !  SWE に上限はない(多年性雪渓・氷河涵養の布石)。
  !
  ! 【リスタート】
  !  s%swe はモデル私有ファイル snow.dat(RLE。m_gwflow_bucket 契約5)。
  !  restore 時に自ファイルが無ければ par_stop。pr0/prh0 はスクラッチ
  !  (初回スナップショットで再構成される)。
  ! ======================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_meteo, only : t_meteo, meteo_temp_set, meteo_temp_cell
  use m_swflow_enc, only : have_width, wfrac
  use list_snow, only : t_list_snow, list_snow_read
  use m_fileio, only : fileio_write_rle, fileio_read_rle, fileio_read_matrix
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : par_info, par_stop, par_abort, dcp, is_root, &
                         par_gather_to, par_scatter_cell
  implicit none
  private
  public :: t_snow
  public :: m_snow_init
  public :: m_snow_calc
  public :: m_snow_dispose

  real, parameter :: secday = 86400.0
  real, parameter :: mm2m = 1.0e-3

  type t_snow
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    real :: tsnow = 0.0                  ! 全雪閾値 (℃)
    real :: train = 2.0                  ! 全雨閾値 (℃)
    real :: tmelt = 0.0                  ! 融雪閾値 (℃)
    real :: ddf = 0.0                    ! 度日係数 (m/℃/s に換算済み)
    real :: rtrans = 0.0                 ! 1/(train - tsnow)(同値なら 0 = 単一閾値)
    real, allocatable :: pr0(:,:)        ! 遮断後降水のスナップショット (m/s)
    real, allocatable :: prh0(:,:)       ! 同 表示用 (mm/h)
    logical :: have0 = .false.           ! スナップショット取得済み
    logical :: initialized = .false.
  end type

contains


!----------------------------------------------------------------------
! 積雪・融雪モジュールを初期化する
!   fn_snow 未指定 or f_snow=0 なら何もしない(enabled = .false.)。
!   気温は m_meteo 必須(m_meteo_init の後に呼ぶこと)
!----------------------------------------------------------------------
subroutine m_snow_init(sn, p, g, s, mt)
  type(t_snow), intent(out) :: sn
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s      ! swe の確保
  type(t_meteo), intent(in) :: mt
  type(t_list_snow) :: list
  integer :: i, j

  if (len_trim(p%fn_snow) == 0) return

  call list_snow_read(p, list)
  if (list%f_snow == 0) return    ! fn を書いたまま一時無効化する経路

  if (.not. mt%enabled) then
    call par_stop("list_snow: 積雪・融雪には気温が必要です(fn_meteo を指定して" &
                  //"ください)")
  end if
  if (list%snow_t_rain < list%snow_t_snow) then
    call par_stop("list_snow: snow_t_rain は snow_t_snow 以上にしてください")
  end if
  if (list%snow_ddf <= -9998.0) call par_stop("list_snow: snow_ddf は必須です")
  if (list%snow_ddf <= 0.0) call par_stop("list_snow: snow_ddf は正のみです")
  if (list%snow_swe0 > -9998.0 .and. list%snow_swe0 < 0.0) then
    call par_stop("list_snow: snow_swe0 は非負のみです")
  end if
  if (list%snow_swe0 > -9998.0 .and. len_trim(list%fn_snow_swe0) > 0) then
    call par_stop("list_snow: 初期積雪は snow_swe0(一様)か fn_snow_swe0(分布)の" &
                  //"どちらか一方で指定してください")
  end if

  sn%tsnow = list%snow_t_snow
  sn%train = list%snow_t_rain
  sn%tmelt = list%snow_t_melt
  sn%ddf = list%snow_ddf * mm2m / secday          ! mm/℃/day -> m/℃/s
  if (list%snow_t_rain > list%snow_t_snow) then
    sn%rtrans = 1.0 / (list%snow_t_rain - list%snow_t_snow)
  end if

  ! --- 状態の確保と初期値(海セル・無効セルには置かない) ---
  allocate(s%swe(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (list%snow_swe0 > 0.0) then
    ! ゾーン2 = x/sw は全域が使える(帯行 jsh:jeh は全域の有効行)
    do j = dcp%jsh, dcp%jeh
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        s%swe(i,j) = list%snow_swe0 * mm2m
      end do
    end do
  else if (len_trim(list%fn_snow_swe0) > 0) then
    call setup_swe0_map(p, g, s, list%fn_snow_swe0)
  end if

  ! --- スナップショット作業領域 ---
  allocate(sn%pr0(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(sn%prh0(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)

  ! --- リスタート ---
  if (p%f_state_restore > 0) call restore_state(p, g, s)

  sn%enabled = .true.
  sn%initialized = .true.
  call par_info("snow (degree-day) enabled")
end subroutine


!----------------------------------------------------------------------
! 初期積雪分布の読み込み(mm。rank0 読み+帯 scatter。使用セルの負値は
! エラー。海セルはゼロ化)
!----------------------------------------------------------------------
subroutine setup_swe0_map(p, g, s, fn)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  character(len=*), intent(in) :: fn
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  character(len=1024) :: msg
  logical :: found
  integer :: i, j

  fname = trim(p%dir_data)//"/"//trim(fn)
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("list_snow: fn_snow_swe0 が見つかりません: "//fname)
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny))
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (wk(i,j) < 0.0) then
          write(msg,'(a,2i7,es12.4)') "list_snow: fn_snow_swe0 の値が負", i, j, wk(i,j)
          call par_abort(trim(msg))
        end if
      end do
    end do
    wk(:,:) = wk(:,:) * mm2m                     ! mm -> m
    call par_scatter_cell(wk, s%swe)
  else
    call par_scatter_cell(dum, s%swe)
  end if
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      if (g%sw(i,j) > 0) s%swe(i,j) = 0.0
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 積雪・融雪の毎ステップ更新(intercept_step の後・swflow の前)
!   pr_fresh: このステップに上流(makepre/貯留型遮断)が s%pre を
!   書き直したか(スナップショット更新の判定。ヘッダの契約参照)
!----------------------------------------------------------------------
subroutine m_snow_calc(sn, p, g, s, mt, pr_fresh)
  type(t_snow), intent(inout) :: sn
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_meteo), intent(inout) :: mt
  logical, intent(in) :: pr_fresh
  integer :: i, j
  real :: tc, fsnow, w, wf

  if (.not. sn%enabled) return

  ! 評価時刻の気温をセット(collective。全ランク同一judgment で呼ぶ)
  call meteo_temp_set(mt, p, g, s%t)

  ! スナップショットの更新(初回は無条件)
  if (pr_fresh .or. .not. sn%have0) then
    sn%pr0(:,:) = s%pre(:,:)
    sn%prh0(:,:) = s%prh(:,:)
    sn%have0 = .true.
  end if

  !$omp parallel do schedule(static) private(i, j, tc, fsnow, w, wf)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      tc = meteo_temp_cell(mt, i, j, s%z(i,j))

      ! (1) 降雨/降雪の分離(スナップショットから毎ステップ再計算)
      if (sn%pr0(i,j) > 0.0) then
        if (tc <= sn%tsnow) then
          fsnow = 1.0
        else if (tc >= sn%train .or. sn%rtrans <= 0.0) then
          fsnow = 0.0
        else
          fsnow = (sn%train - tc) * sn%rtrans
        end if
        s%pre(i,j) = sn%pr0(i,j) * (1.0 - fsnow)          ! 液体降水 (m/s)
        s%prh(i,j) = sn%prh0(i,j) * (1.0 - fsnow)         ! 同率(遮断の契約1と同型)
        if (fsnow > 0.0) then
          s%swe(i,j) = s%swe(i,j) + sn%pr0(i,j) * fsnow * p%dt
        end if
      end if

      ! (2) 度日融雪(min(SWE, M·dt) を h へ直接投入。gv・wfrac 換算)
      if (s%swe(i,j) > 0.0 .and. tc > sn%tmelt) then
        w = min(s%swe(i,j), sn%ddf * (tc - sn%tmelt) * p%dt)
        s%swe(i,j) = s%swe(i,j) - w
        wf = 1.0
        if (have_width) wf = wfrac(i,j)
        s%h(i,j) = s%h(i,j) + w / g%gv(i,j) / wf
        s%e(i,j) = s%z(i,j) + s%h(i,j)
      end if
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル snow.dat。契約5。§7)
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
  call par_gather_to(wk, s%swe)
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/snow.dat', form='unformatted', &
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

  fname = trim(p%dir_save)//'/snow.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("snow の保存ファイルがありません(保存時に fn_snow は有効でしたか): " &
                  //fname)
  end if
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    close(un)
    call par_scatter_cell(wk, s%swe)
  else
    call par_scatter_cell(dum, s%swe)
  end if
end subroutine


!----------------------------------------------------------------------
! 積雪・融雪モジュールを破棄する(save は dispose で行う。契約5)
!----------------------------------------------------------------------
subroutine m_snow_dispose(sn, p, g, s)
  type(t_snow), intent(inout) :: sn
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (.not. sn%enabled) return
  if (p%f_state_save > 0) call save_state(p, g, s)
  if (allocated(sn%pr0)) deallocate(sn%pr0)
  if (allocated(sn%prh0)) deallocate(sn%prh0)
  sn%enabled = .false.
  sn%initialized = .false.
end subroutine

end module
