module list_bldgdebris
  ! ======== 家屋破壊・瓦礫設定ファイルの読み込み(&list_bldgdebris) ========
  ! list_* は namelist を読むだけ。解釈・検証・導出(喫水の導出・排他検査・
  ! 有効判定など)は m_bldgdebris の init が行う(developer.md §12, §63)
  ! ======================================================================
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_bldgdebris
  public :: list_bldgdebris_read

  integer, parameter :: maxpathlen = 256

  type t_list_bldgdebris
    integer :: f_bd = 1                            ! 0 でファイルを残したまま一時無効化
    character(len=maxpathlen) :: fn_bdstock = ""   ! 家屋ストック分布 (m3/m2。瓦礫化可能
                                                   !   材積。木造率込み。bd_stock0 と排他で
                                                   !   どちらか必須)
    real :: bd_stock0 = -9999.0                    ! 一様な家屋ストック (m3/m2)
    character(len=maxpathlen) :: fn_bdfrac = ""    ! 建物占有のうち破壊可能な割合 fw の
                                                   !   分布 (0〜1。省略時 1。空隙率帰還の
                                                   !   上限 = 残る RC 造・耐津波構造。§63.4)
    real :: bd_dlog = -9999.0                      ! 瓦礫の代表寸法 (m。喫水の導出。必須)
    real :: bd_sg = -9999.0                        ! 瓦礫の見かけ比重 (0<sg<1。必須)
    ! ---- 破壊判定 ----
    integer :: f_bdcrit = 1                        ! 判定量 1:浸水深 h+hs、2:荷重
                                                   !   (h+(1+s)hs+sg_log·hd+sg_bd·hbd)V²
    real :: bd_hcrit = -9999.0                     ! 浸水深閾値 (m。f_bdcrit=1 で必須)
    real :: bd_hcrit2 = -9999.0                    ! 浸水深の第2閾値 (m。任意。線形ランプの
                                                   !   上端 = 破壊可能率 1 になる水深)
    real :: bd_fcrit = -9999.0                     ! 荷重閾値 (m3/s2。f_bdcrit=2 で必須)
    real :: bd_fcrit2 = -9999.0                    ! 荷重の第2閾値 (m3/s2。任意。同上)
    real :: bd_wdes = -9999.0                      ! 破壊レート (m/s = m3/m2/s。必須)
    real :: bd_fsink = 0.0                         ! 沈下率 (0〜1。破壊量のうちその場で
                                                   !   堆積に直行する比率。0 = 全量浮遊)
    ! ---- 停止・堆積 ----
    real :: bd_wstop = -9999.0                     ! 接地堆積レート (m/s。必須)
    real :: bd_vstop = 0.0                         ! 低速堆積の流速閾値 (m/s。0=水深のみ)
    ! ---- 再流動(既定 bd_wfloat=0 = なし)----
    real :: bd_wfloat = 0.0                        ! 再流動レート (m/s。0=再流動なし)
    real :: bd_rfloat = 1.5                        ! 浮遊余裕率(再流動水深 = rfloat×喫水)
    real :: bd_vfloat = -9999.0                    ! 再流動の流速閾値 (m/s。wfloat>0 で必須)
    ! ---- 空隙率への帰還(B2。§63.4)----
    integer :: f_bdgv = 1                          ! 1: 破壊率に応じて空隙率 gv を上げる
                                                   !   (gv = gv0 + (1−gv0)·fw·d)、0: 片方向
  end type

contains

!----------------------------------------------------------------------
! 家屋破壊・瓦礫設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_bldgdebris_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_bldgdebris), intent(inout) :: list

  integer :: f_bd, f_bdcrit, f_bdgv
  character(len=maxpathlen) :: fn_bdstock, fn_bdfrac
  real :: bd_stock0, bd_dlog, bd_sg
  real :: bd_hcrit, bd_hcrit2, bd_fcrit, bd_fcrit2, bd_wdes, bd_fsink
  real :: bd_wstop, bd_vstop
  real :: bd_wfloat, bd_rfloat, bd_vfloat
  integer :: un
  integer :: ios
  character(len=1024) :: iom

  namelist /list_bldgdebris/ f_bd, fn_bdstock, bd_stock0, fn_bdfrac, bd_dlog, bd_sg, &
                             f_bdcrit, bd_hcrit, bd_hcrit2, bd_fcrit, bd_fcrit2, &
                             bd_wdes, bd_fsink, bd_wstop, bd_vstop, &
                             bd_wfloat, bd_rfloat, bd_vfloat, f_bdgv

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  f_bd = list%f_bd
  fn_bdstock = list%fn_bdstock
  bd_stock0 = list%bd_stock0
  fn_bdfrac = list%fn_bdfrac
  bd_dlog = list%bd_dlog
  bd_sg = list%bd_sg
  f_bdcrit = list%f_bdcrit
  bd_hcrit = list%bd_hcrit
  bd_hcrit2 = list%bd_hcrit2
  bd_fcrit = list%bd_fcrit
  bd_fcrit2 = list%bd_fcrit2
  bd_wdes = list%bd_wdes
  bd_fsink = list%bd_fsink
  bd_wstop = list%bd_wstop
  bd_vstop = list%bd_vstop
  bd_wfloat = list%bd_wfloat
  bd_rfloat = list%bd_rfloat
  bd_vfloat = list%bd_vfloat
  f_bdgv = list%f_bdgv

  call par_info("reading list_bldgdebris in "//trim(p%fn_bldgdebris))
  open(newunit=un, file=trim(p%fn_bldgdebris), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_bldgdebris: cannot open "//trim(p%fn_bldgdebris) &
                              //": "//trim(iom))
  read(un, nml=list_bldgdebris, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_bldgdebris: cannot read namelist: "//trim(iom))
  close(un)

  list%f_bd = f_bd
  list%fn_bdstock = fn_bdstock
  list%bd_stock0 = bd_stock0
  list%fn_bdfrac = fn_bdfrac
  list%bd_dlog = bd_dlog
  list%bd_sg = bd_sg
  list%f_bdcrit = f_bdcrit
  list%bd_hcrit = bd_hcrit
  list%bd_hcrit2 = bd_hcrit2
  list%bd_fcrit = bd_fcrit
  list%bd_fcrit2 = bd_fcrit2
  list%bd_wdes = bd_wdes
  list%bd_fsink = bd_fsink
  list%bd_wstop = bd_wstop
  list%bd_vstop = bd_vstop
  list%bd_wfloat = bd_wfloat
  list%bd_rfloat = bd_rfloat
  list%bd_vfloat = bd_vfloat
  list%f_bdgv = f_bdgv

end subroutine

end module
