module list_evap
  ! ============== 蒸発散設定ファイルの読み込み(&list_evap) ==============
  ! list_* は namelist を読むだけ。解釈・検証・導出(単位換算、熱指数の
  ! 計算など)は m_evap の init が行う(developer.md §12, §27)。
  ! 暦(date0_c)は &list_sysparam、気温入力は &list_meteo に移設済み
  ! (§29。旧 &list_evap の date0_c / temp0 / tempval / fn_tempmap /
  ! 減率パラメータは廃止 — 指定すると namelist 読込エラーになる)
  ! ======================================================================
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_evap
  public :: list_evap_read

  type t_list_evap
    ! 可能蒸発散(PET)の決定法(排他切替)
    !   1: 一定速度 evap0
    !   2: 月別気候値 evap_monthly(暦 = &list_sysparam の date0_c が必要)
    !   3: Hamon 式(気温 = &list_meteo+可照時間。暦・緯度が必要)
    !   4: Thornthwaite 式(3 に加えて熱指数用の平年値が必要)
    integer :: f_evmodel = 0
    real :: evap0 = -9999.0                        ! モード1: PET (mm/day)
    real :: evap_monthly(1:12) = -9999.0           ! モード2: 月別 PET (mm/day)
    real :: evap_kc = 1.0                          ! 換算係数(パン係数・校正用。全モード共通)
    real :: lat = -9999.0                          ! 代表緯度 (deg。モード3,4で必須)
    real :: temp_normal(1:12) = -9999.0            ! 月平均気温の平年値 (℃。モード4の
                                                   !   熱指数 I の算定用)
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
  real :: lat
  real :: temp_normal(1:12)
  integer :: un
  integer :: ios
  character(len=1024) :: iom

  namelist /list_evap/ f_evmodel, evap0, evap_monthly, evap_kc, lat, temp_normal

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  f_evmodel = list%f_evmodel
  evap0 = list%evap0
  evap_monthly = list%evap_monthly
  evap_kc = list%evap_kc
  lat = list%lat
  temp_normal = list%temp_normal

  call par_info("reading list_evap in "//trim(p%fn_evap))
  open(newunit=un, file=trim(p%fn_evap), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("cannot open file: "//trim(p%fn_evap)//" : "//trim(iom))
  read(un, nml=list_evap, iostat=ios, iomsg=iom)
  if (ios /= 0) then
    call par_stop("error in reading list_evap: "//trim(iom) &
                  //"(旧 date0_c は &list_sysparam、気温入力は &list_meteo へ移設。§29)")
  end if
  close(un)

  list%f_evmodel = f_evmodel
  list%evap0 = evap0
  list%evap_monthly = evap_monthly
  list%evap_kc = evap_kc
  list%lat = lat
  list%temp_normal = temp_normal

end subroutine

end module
