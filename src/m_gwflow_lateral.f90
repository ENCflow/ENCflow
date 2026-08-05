module m_gwflow_lateral
  ! ========= 側方流動モデル: 非線形 Boussinesq(2次元・4近傍 FV) =========
  ! 飽和帯の側方 Darcy 流(handoff_gwflow_tani.md §3.2b)。エッジ状態レス
  ! 設計(同 §4a): フラックスは無履歴でエッジごとにその場計算し発散に
  ! 消費する。永続エッジ配列・二重バッファ・エッジ交換は持たない。
  !
  ! 【定式化】
  !   h_gw = s%hg / sy0(飽和帯厚。s%hg は柱状換算水量)
  !   H    = (s%z - sd) + h_gw [+ s%h]   … 全水頭(同 §3.2.3)。
  !          地表湛水 s%h の寄与は飽和セル(s%hg >= sd*sy0)のみ。
  !          ENCflow は不飽和セルにも湛水が存在しうる(浸透途中の
  !          表面水)が、不飽和帯を介した湛水は地下水面と水圧的に
  !          連続でないため駆動力に含めない(§3.2.3 の実装細目)
  !   q_k  = -K_sh * h_e * ΔH/dr_k * l_k … 界面フラックス。h_e は
  !          算術平均を上流側(H の高い側)の h_gw でキャップ(§5)
  !   近傍は4方向(E/W/N/S)。等方拡散の FV には十分で RRI と同じ。
  !   m_swflow_enc の8近傍対角配分は運動方程式向けの装置であり不採用
  !
  ! 【数値安定化(§5)】
  !   - 両セル h_gw <= eps で流量ゼロ(乾燥判定)
  !   - 上流側 h_gw <= eps で流量ゼロ
  !   - 過大流出の抑制: 1エッジの流出で上流側が eps を割る場合は縮小
  !     (exflux_reduction 相当。複数エッジ同時流出での微小な行き過ぎは
  !      浅水側と同じく許容し、次ステップの乾燥判定で自己回復する)
  !   - 陽解法の安定条件は h_gw <= sd の構造的上界から静的に評価できる:
  !     dt <= 0.5 / (D*(1/dx^2+1/dy^2)), D = K_sh*max(sd)/sy0。
  !     init で検査し、実効時間刻み dts が超えるときは par_stop
  !
  ! 【MPI(§4a)】
  !   calc 冒頭で par_halo_cell(s%hg) と par_halo_cell(s%h) を交換する
  !   (鉛直モデルと引き渡しが帯のみ更新するため、末尾交換では古くなる)。
  !   s%z のハロは m_swflow_enc がステップ頭で毎ステップ交換済みのものに
  !   依存する(呼び出し順 swflow→gwflow が前提。順序を変えるなら再検討)。
  !   界面フラックスは両ランクが同一入力から同一値をビット厳密に再計算する
  !   (冗長計算=配布機構。式は c/n を入れ替えても大きさがビット同値に
  !    なる形: 平均は和の半分、勾配は abs、上流量は H 比較で選択)
  !
  ! 【地表流との結合】
  !   側方流入で飽和容量 sd*sy0 を超えたセルは、超過分を s%h へ渡し
  !   s%e を回復する(反対称適用。m_gwflow_bucket 契約(1)(2)と同型)。
  !   海域セルとは無フラックス(海への地下水流出は当面扱わない)
  !
  ! 【リスタート】
  !   無履歴のためモデル私有状態なし(s%hg は m_state が保存)。契約5の
  !   私有ファイルは不要
  ! =====================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_parallel, only : par_info, par_stop, dcp, par_halo_cell, par_allreduce_max
  implicit none
  private
  public :: gwflow_lateral_init
  public :: gwflow_lateral_calc
  public :: gwflow_lateral_dispose

  ! 4近傍(E, W, N, S)
  integer, parameter :: din4(1:4) = [ 1, -1, 0, 0 ]
  integer, parameter :: djn4(1:4) = [ 0, 0, 1, -1 ]

  ! モデル私有の設定・作業領域(単一インスタンス前提。developer.md §12)
  type t_lat_bsq
    real :: ksh = 0.0                ! 側方飽和透水係数 (m/s)
    real :: eps = 0.0                ! 乾燥判定・過大流出抑制の正則化厚 (m)
    real :: sy0 = 0.0                ! 比湧水量(= g%sy0。init で転記)
    real :: syinv = 0.0              ! 1 / sy0
    real :: ainv = 0.0               ! 1 / (dx*dy)
    real :: rdr(1:4) = 0.0           ! 1 / セル中心間距離
    real :: wl(1:4) = 0.0            ! 界面幅
    real, allocatable :: wk(:,:)     ! 時刻 n の s%hg の退避(帯+ハロ)
    logical :: initialized = .false.
  end type
  type(t_lat_bsq) :: lbq

contains


!----------------------------------------------------------------------
! Boussinesq 側方流の初期化(固有グループを自分で読む)。
! g%sd は m_gwflow_init が m_geoinfo_require_sd で確保済み。
! dts は実効時間刻み(安定条件の静的検査に使う)
!----------------------------------------------------------------------
subroutine gwflow_lateral_init(p, g, s, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: un, ios, i, j
  real :: gw_ksh_mmh, gw_eps
  real :: sdmax(1), dcoef, dt_lim
  character(len=256) :: msg
  namelist /list_gwflow_lateral/ gw_ksh_mmh, gw_eps

  if (s%initialized) continue  ! 引数未使用の警告を抑制

  gw_ksh_mmh = 0.0
  gw_eps = 1.0e-3

  call par_info("reading list_gwflow_lateral in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow_lateral, iostat=ios)
  if (ios /= 0) call par_stop("error in reading list_gwflow_lateral")
  close(un)

  if (gw_ksh_mmh <= 0.0) call par_stop("list_gwflow_lateral: gw_ksh_mmh must be > 0")
  if (gw_eps <= 0.0) call par_stop("list_gwflow_lateral: gw_eps must be > 0")
  if (g%sy0 <= 0.0 .or. g%sy0 > 1.0) then
    call par_stop("list_geoinfo: sy0 must be in (0,1] for gwflow lateral")
  end if
  ! 遅延確保口の呼び忘れ(m_gwflow_init の needs_sd)をここで検出する
  if (.not. allocated(g%sd)) call par_stop("gwflow_lateral: g%sd is not allocated")

  lbq%ksh = gw_ksh_mmh / 1000.0 / 3600.0   ! mm/h -> m/s
  lbq%eps = gw_eps
  lbq%sy0 = g%sy0
  lbq%syinv = 1.0 / g%sy0
  lbq%ainv = 1.0 / (g%dx * g%dy)
  lbq%rdr(1:4) = [ 1.0/g%dx, 1.0/g%dx, 1.0/g%dy, 1.0/g%dy ]
  lbq%wl(1:4)  = [ g%dy, g%dy, g%dx, g%dx ]

  ! 陽解法の安定条件の静的検査(ヘッダ参照。h_gw <= sd の構造的上界)
  sdmax(1) = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      sdmax(1) = max(sdmax(1), g%sd(i,j))
    end do
  end do
  call par_allreduce_max(sdmax)
  dcoef = lbq%ksh * sdmax(1) * lbq%syinv
  if (dcoef > 0.0) then
    dt_lim = 0.5 / (dcoef * (1.0/g%dx**2 + 1.0/g%dy**2))
    write(msg,'(a,es10.3,a,es10.3,a)') "gwflow_lateral: dt limit = ", dt_lim, &
                                       " s (dts = ", dts, " s)"
    call par_info(trim(msg))
    if (dts > dt_lim) then
      call par_stop("gwflow_lateral: dts exceeds the explicit stability limit " &
                    // "(reduce dt/dt_gwflow or K_sh)")
    end if
  end if

  allocate(lbq%wk(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  lbq%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! Boussinesq 側方流の計算(1回の呼び出しで実効時間刻み dts ぶんの更新)
!   時刻 n の s%hg を wk に退避し、全フラックスを時刻 n の状態から計算
!   する(更新途中の値を読まない)。末尾で飽和超過分を地表流へ渡す
!----------------------------------------------------------------------
subroutine gwflow_lateral_calc(p, g, s, it, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  real, intent(in) :: dts
  integer :: i, j, k, in, jn
  real :: hgwc, hgwn, hc0, hn0, hgw_up, hgw_e, gq, dh_up, cor, dhg, capc, fx

  if (it < 0) continue  ! 引数未使用の警告を抑制(独自周期を持つモデル用に供給)
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  ! ステップ頭のハロ交換(ヘッダ【MPI】参照)
  call par_halo_cell(s%hg)
  call par_halo_cell(s%h)

  ! 時刻 n の hg を退避(ハロ込み)
  lbq%wk(:,:) = s%hg(:,:)

  !$omp parallel do schedule(static) &
  !$omp   private(i, j, k, in, jn, hgwc, hgwn, hc0, hn0, hgw_up, hgw_e, gq, dh_up, cor, dhg)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      hgwc = lbq%wk(i,j) * lbq%syinv
      ! 全水頭(地表湛水は飽和セルのみ寄与。ヘッダ【定式化】参照)
      hc0 = s%z(i,j) - g%sd(i,j) + hgwc
      if (lbq%wk(i,j) >= g%sd(i,j) * lbq%sy0) hc0 = hc0 + s%h(i,j)
      dhg = 0.0
      do k = 1, 4
        in = i + din4(k)
        jn = j + djn4(k)
        ! 領域外・海域とは無フラックス(x の番兵により配列参照より先に判定)
        if (g%x(in,jn) <= 0) cycle
        if (g%sw(in,jn) > 0) cycle
        hgwn = lbq%wk(in,jn) * lbq%syinv
        if (hgwc <= lbq%eps .and. hgwn <= lbq%eps) cycle   ! 両側乾燥
        hn0 = s%z(in,jn) - g%sd(in,jn) + hgwn
        if (lbq%wk(in,jn) >= g%sd(in,jn) * lbq%sy0) hn0 = hn0 + s%h(in,jn)
        if (hc0 == hn0) cycle              ! 勾配ゼロ(上流側の選択が不定でも流量0)
        ! 上流側(全水頭の高い側)の飽和帯厚
        if (hc0 > hn0) then
          hgw_up = hgwc
        else
          hgw_up = hgwn
        end if
        if (hgw_up <= lbq%eps) cycle       ! 上流側が乾燥
        ! 界面飽和帯厚: 算術平均を上流側でキャップ(correct_he 相当。§5)
        hgw_e = min(0.5 * (hgwc + hgwn), hgw_up)
        ! フラックスの大きさ(c/n を入れ替えてもビット同値になる形で評価)
        gq = lbq%ksh * hgw_e * abs(hn0 - hc0) * lbq%rdr(k) * lbq%wl(k)
        ! 過大流出の抑制: このエッジの流出で上流側が eps を割るなら縮小(§5.1)
        dh_up = gq * dts * lbq%ainv * lbq%syinv
        if (hgw_up - dh_up <= lbq%eps) then
          cor = max(hgw_up - lbq%eps, 0.0) / dh_up
          gq = gq * cor
        end if
        ! 発散への寄与(柱状水量。流入を正に)
        if (hc0 > hn0) then
          dhg = dhg - gq * dts * lbq%ainv
        else
          dhg = dhg + gq * dts * lbq%ainv
        end if
      end do
      s%hg(i,j) = lbq%wk(i,j) + dhg
    end do
  end do
  !$omp end parallel do

  ! 飽和超過分の地表流への引き渡し(反対称適用と水位の回復。契約(1)(2)相当)
  !   フラックス計算と分離した後段ループで行う(前段は時刻 n の s%h を読む)
  !$omp parallel do schedule(static) private(i, j, capc, fx)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      capc = g%sd(i,j) * lbq%sy0
      if (s%hg(i,j) > capc) then
        fx = s%hg(i,j) - capc
        s%hg(i,j) = capc
        s%h(i,j) = s%h(i,j) + fx
        s%e(i,j) = s%z(i,j) + s%h(i,j)
      end if
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! Boussinesq 側方流の破棄(無履歴のため私有保存なし。ヘッダ【リスタート】)
!----------------------------------------------------------------------
subroutine gwflow_lateral_dispose(p)
  type(t_sysparam), intent(in) :: p
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (allocated(lbq%wk)) deallocate(lbq%wk)
  lbq%initialized = .false.
end subroutine

end module
