module list_sfm
  ! 貯留関数法の区画流出の設定ファイル(fn_sfm の namelist)の読み込み専任
  ! (層契約 §12)。生の値を t_list_sfm に運ぶだけで、解釈・検証・既定値の
  ! 適用・導出は m_sfm の init が行う(developer.md §106)。
  !   &list_sfm      : 共通設定(有効化・区画番号マップ・同期間隔・雨の扱い・数値制御)
  !   &list_sfm_zone : 区画ごとの貯留関数のパラメータ・遅れ時間・初期条件・出口・基底流
  !                    (配列。区画番号で添字。出口と基底流の指定は &list_vz_zone と同じ形)
  ! 未指定の番兵は実数 −9999、整数 −9999。グループ不在は全番兵のまま(init が判定)。
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_sfm
  public :: list_sfm_read
  public :: sfm_nzonemax, sfm_noutmax, sfm_nbasemax

  integer, parameter :: maxpathlen = 256
  integer, parameter :: sfm_nzonemax = 50    ! 区画の最大数
  integer, parameter :: sfm_noutmax = 99     ! 1 区画あたりの出口セルの最大数
  integer, parameter :: sfm_nbasemax = 100   ! 基底流の時系列の namelist の最大点数(長い系列はファイルで)

  type t_list_sfm
    ! ---- &list_sfm ----
    integer :: f_sfm = 1                          ! 0 で書いたまま一時無効化
    character(len=maxpathlen) :: fn_sfm_zone = "" ! 区画番号ラスタ(整数。0 = 適用外)
    real :: dt_sfm = -9999.0                      ! 同期間隔 (s。0 = 毎ステップ)
    integer :: f_sfm_rain = 0                     ! 0: 区画内で雨量が一致しなければ停止 / 1: 区画内面積平均
    real :: sfm_tol = -9999.0                     ! 内部刻みの時間誤差の相対許容(貯留量に対する比)
    real :: sfm_dt_min = -9999.0                  ! 内部刻みの下限 (s)
    ! ---- &list_sfm_zone(区画番号 z で添字) ----
    real :: sfm_k(1:sfm_nzonemax) = -9999.0       ! 貯留係数 K(S[mm] = K·q[mm/h]^P)
    real :: sfm_p(1:sfm_nzonemax) = -9999.0       ! 貯留指数 P
    real :: sfm_q0_mmh(1:sfm_nzonemax) = -9999.0  ! 初期条件: 初期の流出強度 (mm/h)
    real :: sfm_tl_h(1:sfm_nzonemax) = -9999.0    ! 遅れ時間 T_L (h。未指定 = 0)
    real :: sfm_elim_mm(1:sfm_nzonemax) = -9999.0 ! 蒸発散の線形低減を始める貯留 (mm。未指定 = 供給制限のみ)
    integer :: sfm_out_kind(1:sfm_nzonemax) = -9999 ! 出口 1: 地表セルへ移送 / 2: 系外流出
    integer :: sfm_out_cell(1:2, 1:sfm_noutmax, 1:sfm_nzonemax) = -9999  ! 出口セル (i, j)
    real :: sfm_out_w(1:sfm_noutmax, 1:sfm_nzonemax) = -9999.0          ! 出口の配分率
    real :: sfm_base(1:2, 1:sfm_nbasemax, 1:sfm_nzonemax) = -9999.0     ! 基底流の時系列 (時刻(分), mm/h)
    character(len=maxpathlen) :: fn_sfm_base(1:sfm_nzonemax) = ""      ! 基底流の時系列ファイル(1 行「時刻(分) mm/h」)
  end type

contains


!----------------------------------------------------------------------
! 設定ファイルを読み込む(2 グループとも不在可。構文エラーは停止)
!----------------------------------------------------------------------
subroutine list_sfm_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_sfm), intent(out) :: list
  integer :: un, ios
  character(len=256) :: msg

  integer :: f_sfm
  character(len=maxpathlen) :: fn_sfm_zone
  real :: dt_sfm
  integer :: f_sfm_rain
  real :: sfm_tol, sfm_dt_min
  real :: sfm_k(1:sfm_nzonemax), sfm_p(1:sfm_nzonemax), sfm_q0_mmh(1:sfm_nzonemax), sfm_tl_h(1:sfm_nzonemax)
  real :: sfm_elim_mm(1:sfm_nzonemax)
  integer :: sfm_out_kind(1:sfm_nzonemax)
  integer :: sfm_out_cell(1:2, 1:sfm_noutmax, 1:sfm_nzonemax)
  real :: sfm_out_w(1:sfm_noutmax, 1:sfm_nzonemax)
  real :: sfm_base(1:2, 1:sfm_nbasemax, 1:sfm_nzonemax)
  character(len=maxpathlen) :: fn_sfm_base(1:sfm_nzonemax)

  namelist /list_sfm/ f_sfm, fn_sfm_zone, dt_sfm, f_sfm_rain, sfm_tol, sfm_dt_min
  namelist /list_sfm_zone/ sfm_k, sfm_p, sfm_q0_mmh, sfm_tl_h, sfm_elim_mm, sfm_out_kind, sfm_out_cell, sfm_out_w, &
                           sfm_base, fn_sfm_base

  f_sfm = list%f_sfm
  fn_sfm_zone = list%fn_sfm_zone
  dt_sfm = list%dt_sfm
  f_sfm_rain = list%f_sfm_rain
  sfm_tol = list%sfm_tol
  sfm_dt_min = list%sfm_dt_min
  sfm_k = list%sfm_k
  sfm_p = list%sfm_p
  sfm_q0_mmh = list%sfm_q0_mmh
  sfm_tl_h = list%sfm_tl_h
  sfm_elim_mm = list%sfm_elim_mm
  sfm_out_kind = list%sfm_out_kind
  sfm_out_cell = list%sfm_out_cell
  sfm_out_w = list%sfm_out_w
  sfm_base = list%sfm_base
  fn_sfm_base = list%fn_sfm_base

  call par_info("reading list_sfm in " // trim(p%fn_sfm))
  open(newunit=un, file=trim(p%fn_sfm), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_sfm: cannot open " // trim(p%fn_sfm))
  read(un, nml=list_sfm, iostat=ios, iomsg=msg)
  if (ios > 0) call par_stop("list_sfm: cannot read namelist: " // trim(msg))
  rewind(un)
  read(un, nml=list_sfm_zone, iostat=ios, iomsg=msg)
  if (ios > 0) call par_stop("list_sfm_zone: cannot read namelist: " // trim(msg))
  close(un)

  list%f_sfm = f_sfm
  list%fn_sfm_zone = fn_sfm_zone
  list%dt_sfm = dt_sfm
  list%f_sfm_rain = f_sfm_rain
  list%sfm_tol = sfm_tol
  list%sfm_dt_min = sfm_dt_min
  list%sfm_k = sfm_k
  list%sfm_p = sfm_p
  list%sfm_q0_mmh = sfm_q0_mmh
  list%sfm_tl_h = sfm_tl_h
  list%sfm_elim_mm = sfm_elim_mm
  list%sfm_out_kind = sfm_out_kind
  list%sfm_out_cell = sfm_out_cell
  list%sfm_out_w = sfm_out_w
  list%sfm_base = sfm_base
  list%fn_sfm_base = fn_sfm_base

end subroutine

end module
