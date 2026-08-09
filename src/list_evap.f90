module list_evap
  ! ============== 蒸発散設定ファイルの読み込み(&list_evap) ==============
  ! list_* は namelist を読むだけ。解釈・検証・導出(日付の解析、
  ! 単位換算、熱指数の計算、基準標高の既定値決定など)は m_evap の
  ! init が行う(developer.md §12, §27)
  ! ======================================================================
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_evap
  public :: list_evap_read
  public :: nevmax

  integer, parameter :: maxpathlen = 256
  integer, parameter :: nevmax = 4000    ! 気温時系列の最大点数(日次で約11年)

  type t_list_evap
    ! 可能蒸発散(PET)の決定法(排他切替)
    !   1: 一定速度 evap0
    !   2: 月別気候値 evap_monthly(暦が必要)
    !   3: Hamon 式(気温+可照時間。暦・緯度が必要)
    !   4: Thornthwaite 式(気温+可照時間+熱指数。暦・緯度・平年値が必要)
    integer :: f_evmodel = 0
    real :: evap0 = -9999.0                        ! モード1: PET (mm/day)
    real :: evap_monthly(1:12) = -9999.0           ! モード2: 月別 PET (mm/day)
    real :: evap_kc = 1.0                          ! 換算係数(パン係数・校正用。全モード共通)
    character(len=80) :: date0_c = ""              ! シミュレーション時刻 t=0 の暦
                                                   !   "YYYY-MM-DD" または "YYYY-MM-DD hh:mm"
                                                   !   (モード2〜4で必須)
    real :: lat = -9999.0                          ! 代表緯度 (deg。モード3,4で必須)
    real :: temp_normal(1:12) = -9999.0            ! 月平均気温の平年値 (℃。モード4の
                                                   !   熱指数 I の算定用)
    ! ---- 気温入力(モード3,4。いずれか1つを指定)----
    real :: temp0 = -9999.0                        ! 一様定数 (℃)
    real :: tempval(1:2,1:nevmax) = -9999.0        ! 一様時系列 (経過日数, ℃)。
                                                   !   時刻は t=0 からの経過「日」
    character(len=maxpathlen) :: fn_tempmap = ""   ! 気温分布ファイルリスト名
                                                   !   (1行1ファイル。等間隔で順次適用)
    character(len=80) :: dt_tempmap_c = "1 day"    ! 気温分布ファイルの時間間隔
    ! ---- 標高による気温減率(モード3,4のオプション)----
    integer :: f_temp_lapse = 0                    ! 1 で有効(一様定数・一様時系列のみ)
    real :: temp_lapse = 0.65                      ! 減率 (℃/100m)
    real :: temp_zref = -9999.0                    ! 基準標高 (m。省略時=領域最低標高)
  end type

contains

!----------------------------------------------------------------------
! 蒸発散設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_evap_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_evap), intent(inout) :: list

  integer :: f_evmodel
  real :: evap0
  real :: evap_monthly(1:12)
  real :: evap_kc
  character(len=80) :: date0_c
  real :: lat
  real :: temp_normal(1:12)
  real :: temp0
  real :: tempval(1:2,1:nevmax)
  character(len=maxpathlen) :: fn_tempmap
  character(len=80) :: dt_tempmap_c
  integer :: f_temp_lapse
  real :: temp_lapse
  real :: temp_zref
  integer :: un
  integer :: ios
  character(len=1024) :: iom

  namelist /list_evap/ f_evmodel, evap0, evap_monthly, evap_kc, date0_c, lat, &
                       temp_normal, temp0, tempval, fn_tempmap, dt_tempmap_c, &
                       f_temp_lapse, temp_lapse, temp_zref

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  f_evmodel = list%f_evmodel
  evap0 = list%evap0
  evap_monthly = list%evap_monthly
  evap_kc = list%evap_kc
  date0_c = list%date0_c
  lat = list%lat
  temp_normal = list%temp_normal
  temp0 = list%temp0
  tempval = list%tempval
  fn_tempmap = list%fn_tempmap
  dt_tempmap_c = list%dt_tempmap_c
  f_temp_lapse = list%f_temp_lapse
  temp_lapse = list%temp_lapse
  temp_zref = list%temp_zref

  call par_info("reading list_evap in "//trim(p%fn_evap))
  open(newunit=un, file=trim(p%fn_evap), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("cannot open file: "//trim(p%fn_evap)//" : "//trim(iom))
  read(un, nml=list_evap, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("error in reading list_evap: "//trim(iom))
  close(un)

  list%f_evmodel = f_evmodel
  list%evap0 = evap0
  list%evap_monthly = evap_monthly
  list%evap_kc = evap_kc
  list%date0_c = date0_c
  list%lat = lat
  list%temp_normal = temp_normal
  list%temp0 = temp0
  list%tempval = tempval
  list%fn_tempmap = fn_tempmap
  list%dt_tempmap_c = dt_tempmap_c
  list%f_temp_lapse = f_temp_lapse
  list%temp_lapse = temp_lapse
  list%temp_zref = temp_zref

end subroutine

end module
