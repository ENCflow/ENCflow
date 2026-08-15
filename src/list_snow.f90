module list_snow
  ! ============== 積雪・融雪設定ファイルの読み込み(&list_snow) ==============
  ! list_* は namelist を読むだけ。解釈・検証・導出は m_snow の init が行う
  ! (developer.md §12, §31)
  ! ==========================================================================
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_snow
  public :: list_snow_read

  integer, parameter :: maxpathlen = 256

  type t_list_snow
    integer :: f_snow = 1                    ! 0 でファイルを残したまま一時無効化
    real :: snow_t_snow = 0.0                ! 全て雪になる気温閾値 (℃)
    real :: snow_t_rain = 2.0                ! 全て雨になる気温閾値 (℃。間は線形混合)
    real :: snow_t_melt = 0.0                ! 融雪閾値 (℃)
    real :: snow_ddf = -9999.0               ! 度日係数 (mm/℃/day。必須)
    real :: snow_swe0 = -9999.0              ! 初期積雪水量 (mm。一様)
    character(len=maxpathlen) :: fn_snow_swe0 = ""  ! 初期積雪水量分布 (mm。swe0 と排他)
  end type

contains

!----------------------------------------------------------------------
! 積雪・融雪設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_snow_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_snow), intent(inout) :: list

  integer :: f_snow
  real :: snow_t_snow, snow_t_rain, snow_t_melt, snow_ddf, snow_swe0
  character(len=maxpathlen) :: fn_snow_swe0
  integer :: un, ios
  character(len=1024) :: iom

  namelist /list_snow/ f_snow, snow_t_snow, snow_t_rain, snow_t_melt, &
                       snow_ddf, snow_swe0, fn_snow_swe0

  f_snow = list%f_snow
  snow_t_snow = list%snow_t_snow
  snow_t_rain = list%snow_t_rain
  snow_t_melt = list%snow_t_melt
  snow_ddf = list%snow_ddf
  snow_swe0 = list%snow_swe0
  fn_snow_swe0 = list%fn_snow_swe0

  call par_info("reading list_snow in "//trim(p%fn_snow))
  open(newunit=un, file=trim(p%fn_snow), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_snow: cannot open "//trim(p%fn_snow)//": "//trim(iom))
  read(un, nml=list_snow, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_snow: cannot read namelist: "//trim(iom))
  close(un)

  list%f_snow = f_snow
  list%snow_t_snow = snow_t_snow
  list%snow_t_rain = snow_t_rain
  list%snow_t_melt = snow_t_melt
  list%snow_ddf = snow_ddf
  list%snow_swe0 = snow_swe0
  list%fn_snow_swe0 = fn_snow_swe0

end subroutine

end module
