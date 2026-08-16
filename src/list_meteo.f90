module list_meteo
  ! ============== 気象強制場設定ファイルの読み込み(&list_meteo) ==============
  ! list_* は namelist を読むだけ。解釈・検証・導出(単位換算、基準標高の
  ! 既定値決定など)は m_meteo の init が行う(developer.md §12, §29)
  ! ==========================================================================
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_meteo
  public :: list_meteo_read
  public :: nmtmax

  integer, parameter :: maxpathlen = 256
  integer, parameter :: nmtmax = 4000    ! 気温時系列の最大点数(日次で約11年)

  type t_list_meteo
    ! ---- 気温入力(いずれか1つを指定)----
    real :: temp0 = -9999.0                        ! 一様定数 (℃)
    real :: tempval(1:2,1:nmtmax) = -9999.0        ! 一様時系列 (経過日数, ℃)。
                                                   !   時刻は t=0 からの経過「日」
    character(len=maxpathlen) :: fn_tempmap = ""   ! 気温分布ファイルリスト名
                                                   !   (1行1ファイル。等間隔で順次適用)
    character(len=80) :: dt_tempmap_c = "1 day"    ! 気温分布ファイルの時間間隔
    ! ---- 標高による気温減率(オプション。一様入力のみ)----
    integer :: f_temp_lapse = 0                    ! 1 で有効
    real :: temp_lapse = 0.65                      ! 減率 (℃/100m)
    real :: temp_zref = -9999.0                    ! 基準標高 (m。省略時=領域最低標高)
    ! ---- 長周期の気候変調(オプション。§45)----
    real :: tempofs(1:2,1:nmtmax) = -9999.0        ! 気温オフセット系列 (経過日数, ΔT ℃)。
                                                   !   t_cycle で折り返さない実時間軸で
                                                   !   評価し、気温入力に加算する
                                                   !   (代表年反復×長期気候トレンドの重畳)
    ! ---- 標高による降水勾配(オプション。§45)----
    integer :: f_prec_lapse = 0                    ! 1 で有効
    real :: prec_lapse = 0.0                       ! 降水の増率 (%/100m)
    real :: prec_zref = -9999.0                    ! 基準標高 (m。省略時=領域最低標高)
  end type

contains

!----------------------------------------------------------------------
! 気象強制場設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_meteo_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_meteo), intent(inout) :: list

  real :: temp0
  real :: tempval(1:2,1:nmtmax)
  character(len=maxpathlen) :: fn_tempmap
  character(len=80) :: dt_tempmap_c
  integer :: f_temp_lapse
  real :: temp_lapse
  real :: temp_zref
  real :: tempofs(1:2,1:nmtmax)
  integer :: f_prec_lapse
  real :: prec_lapse
  real :: prec_zref
  integer :: un
  integer :: ios
  character(len=1024) :: iom

  namelist /list_meteo/ temp0, tempval, fn_tempmap, dt_tempmap_c, &
                        f_temp_lapse, temp_lapse, temp_zref, &
                        tempofs, f_prec_lapse, prec_lapse, prec_zref

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  temp0 = list%temp0
  tempval = list%tempval
  fn_tempmap = list%fn_tempmap
  dt_tempmap_c = list%dt_tempmap_c
  f_temp_lapse = list%f_temp_lapse
  temp_lapse = list%temp_lapse
  temp_zref = list%temp_zref
  tempofs = list%tempofs
  f_prec_lapse = list%f_prec_lapse
  prec_lapse = list%prec_lapse
  prec_zref = list%prec_zref

  call par_info("reading list_meteo in "//trim(p%fn_meteo))
  open(newunit=un, file=trim(p%fn_meteo), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_meteo: cannot open "//trim(p%fn_meteo)//": "//trim(iom))
  read(un, nml=list_meteo, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_meteo: cannot read namelist: "//trim(iom))
  close(un)

  list%temp0 = temp0
  list%tempval = tempval
  list%fn_tempmap = fn_tempmap
  list%dt_tempmap_c = dt_tempmap_c
  list%f_temp_lapse = f_temp_lapse
  list%temp_lapse = temp_lapse
  list%temp_zref = temp_zref
  list%tempofs = tempofs
  list%f_prec_lapse = f_prec_lapse
  list%prec_lapse = prec_lapse
  list%prec_zref = prec_zref

end subroutine

end module
