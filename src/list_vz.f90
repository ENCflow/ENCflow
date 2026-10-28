module list_vz
  ! 鉛直不飽和浸透(VZ)流出の設定ファイル(fn_vz の namelist)の読み込み専任
  ! (層契約 §12)。生の値を t_list_vz に運ぶだけで、解釈・検証・既定値の
  ! 適用・導出は m_vzflow の init が行う(developer.md §87、docs/vz_plan.md)。
  !   &list_vz        : 共通設定(有効化・区画番号マップ・同期間隔・雨の扱い・
  !                     界面透水係数・数値制御・診断出力)
  !   &list_vz_column : 共有参照柱ごとの物性・格子・初期条件・下端(配列。柱番号で添字)
  !   &list_vz_zone   : VZ 区画ごとの参照柱・出口・基底流(配列。区画番号で添字)
  ! 未指定の番兵は実数 −9999、整数 −9999。グループ不在は全番兵のまま(init が判定)。
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_vz
  public :: list_vz_read
  public :: vz_ncolmax, vz_nzonemax, vz_noutmax, vz_ndepmax, vz_nbasemax

  integer, parameter :: maxpathlen = 256
  integer, parameter :: vz_ncolmax = 50     ! 共有参照柱の最大数
  integer, parameter :: vz_nzonemax = 50    ! VZ 区画の最大数
  integer, parameter :: vz_noutmax = 99     ! 1 区画あたりの出口セルの最大数
  integer, parameter :: vz_ndepmax = 20     ! 柱の診断出力の深さの最大数
  integer, parameter :: vz_nbasemax = 100   ! 基底流の時系列の namelist の最大点数(長い系列はファイルで)

  type t_list_vz
    ! ---- &list_vz ----
    integer :: f_vz = 1                           ! 0 で書いたまま一時無効化
    character(len=maxpathlen) :: fn_vz_zone = ""  ! 区画番号ラスタ(整数。0 = 適用外)
    real :: dt_vz = -9999.0                       ! 同期間隔 (s。0 = 毎ステップ)
    integer :: f_vz_rain = 0                      ! 0: 柱内で雨量が一致しなければ停止 / 1: 柱内面積平均
    integer :: f_vz_kface = 1                     ! 界面透水係数 1: 算術平均 / 2: 調和平均
    real :: vz_dt_init = -9999.0                  ! 内部刻みの初期値 (s)
    real :: vz_dt_min = -9999.0                   ! 内部刻みの下限 (s)
    real :: vz_dt_max = -9999.0                   ! 内部刻みの上限 (s)
    real :: vz_tol_theta = -9999.0                ! 時間誤差の θ 尺度(θs − θr に対する比)
    real :: vz_tol_psi = -9999.0                  ! 時間誤差の ψ 尺度(絶対 m と相対の共通値)
    real :: vz_tol_q = -9999.0                    ! 時間誤差の積算流束の相対尺度
    real :: vz_mb_rate = -9999.0                  ! 柱の非線形水収支誤差の予算 (m/s)
    integer :: vz_maxit = -9999                   ! Picard 反復の上限
    real :: vz_out_depth(1:vz_ndepmax) = -9999.0  ! 柱 CSV に出す深さ (m)
    integer :: f_vz_outprof = 0                   ! 1: 分布出力の時刻に柱の鉛直分布を CSV 出力
    ! ---- &list_vz_column(柱番号 c で添字) ----
    real :: vz_ks_mmh(1:vz_ncolmax) = -9999.0     ! 飽和透水係数 (mm/h)
    real :: vz_thetas(1:vz_ncolmax) = -9999.0     ! 飽和含水率
    real :: vz_thetar(1:vz_ncolmax) = -9999.0     ! 残留含水率
    real :: vz_psim(1:vz_ncolmax) = -9999.0       ! 小杉式の ψm (m。負)
    real :: vz_sigma(1:vz_ncolmax) = -9999.0      ! 小杉式の σ
    real :: vz_depth(1:vz_ncolmax) = -9999.0      ! 計算柱の深さ L (m)
    real :: vz_dz(1:vz_ncolmax) = -9999.0         ! 層厚 (m)
    real :: vz_q0_mmh(1:vz_ncolmax) = -9999.0     ! 初期条件: 定常重力排水の流束 (mm/h)
    real :: vz_psi0(1:vz_ncolmax) = -9999.0       ! 初期条件: 一様な圧力水頭 (m。負)
    real :: vz_wt0(1:vz_ncolmax) = -9999.0        ! 初期条件: 静水圧の地下水面の深さ (m。0 以上)
    integer :: f_vz_bottom(1:vz_ncolmax) = 1      ! 下端 1: 自由排水 / 2: 固定圧(検証用)
    real :: vz_psibot(1:vz_ncolmax) = -9999.0     ! 固定圧の ψ_b (m。f_vz_bottom = 2)
    ! ---- &list_vz_zone(区画番号 z で添字) ----
    integer :: vz_zone_col(1:vz_nzonemax) = -9999 ! 参照する柱(未指定 = 区画番号と同じ)
    integer :: vz_out_kind(1:vz_nzonemax) = -9999 ! 出口 1: 地表セルへ移送 / 2: 系外流出
    integer :: vz_out_cell(1:2, 1:vz_noutmax, 1:vz_nzonemax) = -9999  ! 出口セル (i, j)
    real :: vz_out_w(1:vz_noutmax, 1:vz_nzonemax) = -9999.0          ! 出口の配分率
    real :: vz_base(1:2, 1:vz_nbasemax, 1:vz_nzonemax) = -9999.0     ! 基底流の時系列 (時刻(分), mm/h)
    character(len=maxpathlen) :: fn_vz_base(1:vz_nzonemax) = ""     ! 基底流の時系列ファイル(1 行「時刻(分) mm/h」)
  end type

contains


!----------------------------------------------------------------------
! 設定ファイルを読み込む(3 グループとも不在可。構文エラーは停止)
!----------------------------------------------------------------------
subroutine list_vz_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_vz), intent(out) :: list
  integer :: un, ios
  character(len=256) :: msg

  integer :: f_vz
  character(len=maxpathlen) :: fn_vz_zone
  real :: dt_vz
  integer :: f_vz_rain, f_vz_kface
  real :: vz_dt_init, vz_dt_min, vz_dt_max, vz_tol_theta, vz_tol_psi, vz_tol_q, vz_mb_rate
  integer :: vz_maxit
  real :: vz_out_depth(1:vz_ndepmax)
  integer :: f_vz_outprof
  real :: vz_ks_mmh(1:vz_ncolmax), vz_thetas(1:vz_ncolmax), vz_thetar(1:vz_ncolmax)
  real :: vz_psim(1:vz_ncolmax), vz_sigma(1:vz_ncolmax)
  real :: vz_depth(1:vz_ncolmax), vz_dz(1:vz_ncolmax)
  real :: vz_q0_mmh(1:vz_ncolmax), vz_psi0(1:vz_ncolmax), vz_wt0(1:vz_ncolmax)
  integer :: f_vz_bottom(1:vz_ncolmax)
  real :: vz_psibot(1:vz_ncolmax)
  integer :: vz_zone_col(1:vz_nzonemax), vz_out_kind(1:vz_nzonemax)
  integer :: vz_out_cell(1:2, 1:vz_noutmax, 1:vz_nzonemax)
  real :: vz_out_w(1:vz_noutmax, 1:vz_nzonemax)
  real :: vz_base(1:2, 1:vz_nbasemax, 1:vz_nzonemax)
  character(len=maxpathlen) :: fn_vz_base(1:vz_nzonemax)

  namelist /list_vz/ f_vz, fn_vz_zone, dt_vz, f_vz_rain, f_vz_kface, &
                     vz_dt_init, vz_dt_min, vz_dt_max, vz_tol_theta, vz_tol_psi, vz_tol_q, &
                     vz_mb_rate, vz_maxit, vz_out_depth, f_vz_outprof
  namelist /list_vz_column/ vz_ks_mmh, vz_thetas, vz_thetar, vz_psim, vz_sigma, &
                            vz_depth, vz_dz, vz_q0_mmh, vz_psi0, vz_wt0, f_vz_bottom, vz_psibot
  namelist /list_vz_zone/ vz_zone_col, vz_out_kind, vz_out_cell, vz_out_w, vz_base, fn_vz_base

  f_vz = list%f_vz
  fn_vz_zone = list%fn_vz_zone
  dt_vz = list%dt_vz
  f_vz_rain = list%f_vz_rain
  f_vz_kface = list%f_vz_kface
  vz_dt_init = list%vz_dt_init
  vz_dt_min = list%vz_dt_min
  vz_dt_max = list%vz_dt_max
  vz_tol_theta = list%vz_tol_theta
  vz_tol_psi = list%vz_tol_psi
  vz_tol_q = list%vz_tol_q
  vz_mb_rate = list%vz_mb_rate
  vz_maxit = list%vz_maxit
  vz_out_depth = list%vz_out_depth
  f_vz_outprof = list%f_vz_outprof
  vz_ks_mmh = list%vz_ks_mmh
  vz_thetas = list%vz_thetas
  vz_thetar = list%vz_thetar
  vz_psim = list%vz_psim
  vz_sigma = list%vz_sigma
  vz_depth = list%vz_depth
  vz_dz = list%vz_dz
  vz_q0_mmh = list%vz_q0_mmh
  vz_psi0 = list%vz_psi0
  vz_wt0 = list%vz_wt0
  f_vz_bottom = list%f_vz_bottom
  vz_psibot = list%vz_psibot
  vz_zone_col = list%vz_zone_col
  vz_out_kind = list%vz_out_kind
  vz_out_cell = list%vz_out_cell
  vz_out_w = list%vz_out_w
  vz_base = list%vz_base
  fn_vz_base = list%fn_vz_base

  call par_info("reading list_vz in " // trim(p%fn_vz))
  open(newunit=un, file=trim(p%fn_vz), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_vz: cannot open " // trim(p%fn_vz))
  read(un, nml=list_vz, iostat=ios, iomsg=msg)
  if (ios > 0) call par_stop("list_vz: cannot read namelist: " // trim(msg))
  rewind(un)
  read(un, nml=list_vz_column, iostat=ios, iomsg=msg)
  if (ios > 0) call par_stop("list_vz_column: cannot read namelist: " // trim(msg))
  rewind(un)
  read(un, nml=list_vz_zone, iostat=ios, iomsg=msg)
  if (ios > 0) call par_stop("list_vz_zone: cannot read namelist: " // trim(msg))
  close(un)

  list%f_vz = f_vz
  list%fn_vz_zone = fn_vz_zone
  list%dt_vz = dt_vz
  list%f_vz_rain = f_vz_rain
  list%f_vz_kface = f_vz_kface
  list%vz_dt_init = vz_dt_init
  list%vz_dt_min = vz_dt_min
  list%vz_dt_max = vz_dt_max
  list%vz_tol_theta = vz_tol_theta
  list%vz_tol_psi = vz_tol_psi
  list%vz_tol_q = vz_tol_q
  list%vz_mb_rate = vz_mb_rate
  list%vz_maxit = vz_maxit
  list%vz_out_depth = vz_out_depth
  list%f_vz_outprof = f_vz_outprof
  list%vz_ks_mmh = vz_ks_mmh
  list%vz_thetas = vz_thetas
  list%vz_thetar = vz_thetar
  list%vz_psim = vz_psim
  list%vz_sigma = vz_sigma
  list%vz_depth = vz_depth
  list%vz_dz = vz_dz
  list%vz_q0_mmh = vz_q0_mmh
  list%vz_psi0 = vz_psi0
  list%vz_wt0 = vz_wt0
  list%f_vz_bottom = f_vz_bottom
  list%vz_psibot = vz_psibot
  list%vz_zone_col = vz_zone_col
  list%vz_out_kind = vz_out_kind
  list%vz_out_cell = vz_out_cell
  list%vz_out_w = vz_out_w
  list%vz_base = vz_base
  list%fn_vz_base = fn_vz_base

end subroutine

end module
