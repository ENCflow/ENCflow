module list_initial
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public t_list_initial
  public list_initial_read

  integer, parameter :: maxpathlen = 256

  type t_list_initial
    integer :: f_user_routine_id = 0   ! ユーザールーチンID
    integer :: f_htype = 0             ! 初期水深タイプ (0:水深固定値, 1:水深ファイル,
                                       !                 2:水位固定値, 3:水位ファイル)
    integer :: f_uvtype = 0            ! 初期流速タイプ (0: 固定値)
    integer :: f_fill_depres = 0       ! 窪地を満水にする (0:無効, 1:有効)
    real :: h0 = 0                     ! 初期水深固定値 (m)
    real :: e0 = 0                     ! 初期水位固定値 (m。z と同じ基準)
    real :: u0 = 0                     ! 初期x方向流速 (m/s)
    real :: v0 = 0                     ! 初期y方向流速 (m/s)
    real :: h0_rw = 0                  ! 河道マスク部の初期水深増分(m)
    character(len=maxpathlen) :: fn_hinit = ""  ! 初期水深/水位の分布ファイル名
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 初期条件設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_initial_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_initial), intent(inout) :: list
  integer :: f_user_routine_id   ! ユーザールーチンID
  integer :: f_htype             ! 初期水深タイプ (0:水深固定値, 1:水深ファイル,
                                 !                 2:水位固定値, 3:水位ファイル)
  integer :: f_uvtype            ! 初期流速タイプ (0: 固定値)
  integer :: f_fill_depres       ! 窪地を満水にする (0:無効, 1:有効)
  real :: h0                     ! 初期水深固定値 (m)
  real :: e0                     ! 初期水位固定値 (m)
  real :: u0                     ! 初期x方向流速 (m/s)
  real :: v0                     ! 初期y方向流速 (m/s)
  real :: h0_rw                  ! 河道マスク部の初期水深増分 (m)
  character(len=maxpathlen) :: fn_hinit  ! 初期水深/水位の分布ファイル名
  integer :: un
  integer :: ios
  character(len=1024) :: iom
  namelist /list_initial/ f_user_routine_id, f_htype, f_uvtype, f_fill_depres, &
                                h0, e0, u0, v0, h0_rw, fn_hinit

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  f_user_routine_id = list%f_user_routine_id 
  f_htype = list%f_htype 
  f_uvtype = list%f_uvtype 
  f_fill_depres = list%f_fill_depres 
  h0 = list%h0 
  e0 = list%e0
  u0 = list%u0 
  v0 = list%v0 
  h0_rw = list%h0_rw 
  fn_hinit = list%fn_hinit

  call par_info("reading list_initial in "//trim(p%fn_initial))
  open(newunit=un, file=trim(p%fn_initial), status='old')
  read(un, nml=list_initial, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_initial 読込失敗: "//trim(iom))
  close(un)

  list%f_user_routine_id = f_user_routine_id
  list%f_htype = f_htype
  list%f_uvtype = f_uvtype
  list%f_fill_depres = f_fill_depres
  list%h0 = h0
  list%e0 = e0
  list%u0 = u0
  list%v0 = v0
  list%h0_rw = h0_rw
  list%fn_hinit = fn_hinit

end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================
end module
