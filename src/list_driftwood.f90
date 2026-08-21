module list_driftwood
  ! ============ 流木設定ファイルの読み込み(&list_driftwood) ============
  ! list_* は namelist を読むだけ。解釈・検証・導出(単位換算・排他検査・
  ! 有効判定など)は m_driftwood の init が行う(developer.md §12, §50)
  ! ======================================================================
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_driftwood
  public :: list_driftwood_read

  integer, parameter :: maxpathlen = 256

  type t_list_driftwood
    integer :: f_dw = 1                            ! 0 でファイルを残したまま一時無効化
    character(len=maxpathlen) :: fn_dwstock = ""   ! 立木ストック分布 (m3/m2。
                                                   !   dw_stock0 と排他でどちらか必須)
    real :: dw_stock0 = -9999.0                    ! 一様な立木ストック (m3/m2)
    real :: dw_dlog = -9999.0                      ! 流木の代表直径 (m。必須)
    real :: dw_sglog = -9999.0                     ! 材比重 ρlog/ρw (0<sg<1。必須)
    ! ---- 発生(流木化)。少なくとも一方の指定が必須 ----
    real :: dw_wrec = -9999.0                      ! 水理的流失レート (m/s = m3/m2/s。
                                                   !   >0 で水理的流失を有効化)
    real :: dw_hrec = -9999.0                      ! 水理的流失の水深閾値 (m。h+hs)
    real :: dw_vrec = -9999.0                      ! 水理的流失の流速閾値 (m/s)
    real :: dw_droot = -9999.0                     ! 根系深 (m。累積侵食深がこれを
                                                   !   超えたセルの立木は全量流失。
                                                   !   >0 で侵食連行を有効化)
    ! ---- 停止・堆積 ----
    real :: dw_wstop = -9999.0                     ! 接地堆積レート (m/s。必須)
    real :: dw_vstop = 0.0                         ! 低速堆積の流速閾値 (m/s。0=水深のみ)
    ! ---- 再流動(既定 dw_wfloat=0 = なし)----
    real :: dw_wfloat = 0.0                        ! 再流動レート (m/s。0=再流動なし)
    real :: dw_rfloat = 1.5                        ! 浮遊余裕率(再流動水深 = rfloat×喫水)
    real :: dw_vfloat = -9999.0                    ! 再流動の流速閾値 (m/s。wfloat>0 で必須)
  end type

contains

!----------------------------------------------------------------------
! 流木設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_driftwood_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_driftwood), intent(inout) :: list

  integer :: f_dw
  character(len=maxpathlen) :: fn_dwstock
  real :: dw_stock0
  real :: dw_dlog, dw_sglog
  real :: dw_wrec, dw_hrec, dw_vrec, dw_droot
  real :: dw_wstop, dw_vstop
  real :: dw_wfloat, dw_rfloat, dw_vfloat
  integer :: un
  integer :: ios
  character(len=1024) :: iom

  namelist /list_driftwood/ f_dw, fn_dwstock, dw_stock0, dw_dlog, dw_sglog, &
                            dw_wrec, dw_hrec, dw_vrec, dw_droot, &
                            dw_wstop, dw_vstop, &
                            dw_wfloat, dw_rfloat, dw_vfloat

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  f_dw = list%f_dw
  fn_dwstock = list%fn_dwstock
  dw_stock0 = list%dw_stock0
  dw_dlog = list%dw_dlog
  dw_sglog = list%dw_sglog
  dw_wrec = list%dw_wrec
  dw_hrec = list%dw_hrec
  dw_vrec = list%dw_vrec
  dw_droot = list%dw_droot
  dw_wstop = list%dw_wstop
  dw_vstop = list%dw_vstop
  dw_wfloat = list%dw_wfloat
  dw_rfloat = list%dw_rfloat
  dw_vfloat = list%dw_vfloat

  call par_info("reading list_driftwood in "//trim(p%fn_driftwood))
  open(newunit=un, file=trim(p%fn_driftwood), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_driftwood: cannot open "//trim(p%fn_driftwood) &
                              //": "//trim(iom))
  read(un, nml=list_driftwood, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_driftwood: cannot read namelist: "//trim(iom))
  close(un)

  list%f_dw = f_dw
  list%fn_dwstock = fn_dwstock
  list%dw_stock0 = dw_stock0
  list%dw_dlog = dw_dlog
  list%dw_sglog = dw_sglog
  list%dw_wrec = dw_wrec
  list%dw_hrec = dw_hrec
  list%dw_vrec = dw_vrec
  list%dw_droot = dw_droot
  list%dw_wstop = dw_wstop
  list%dw_vstop = dw_vstop
  list%dw_wfloat = dw_wfloat
  list%dw_rfloat = dw_rfloat
  list%dw_vfloat = dw_vfloat

end subroutine

end module
