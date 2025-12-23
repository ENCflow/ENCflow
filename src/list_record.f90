!======================================================================
module list_record
  use m_sysparam, only : t_sysparam
  implicit none
  private

  public :: t_list_record
  public :: list_record_read

  integer, parameter :: npbmax = 1000
  integer, parameter :: nflmax = 3000


  type t_list_record
    integer :: pbxytype = 0
    real :: pbxy(1:2,1:npbmax) = -9999
    integer :: flxyfile = 0
    character(len=256) :: fn_flxy
    integer :: flxytype = 0
    real :: flxy(1:4,1:nflmax) = -9999
    ! ここで初期値を非現実的な値で初期化しておくと
    ! データが存在しな場合にはその値が残っているため
    ! データ数を明示的に指定しなくても
    ! 有効なデータの数を判別することができる
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! レコード設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_record_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_record), intent(inout) :: list
  integer :: pbxytype
  real :: pbxy(1:2,1:npbmax)
  integer :: flxyfile
  character(:), allocatable :: fn_flxy
  integer :: flxytype
  real :: flxy(1:4,1:nflmax)
  integer :: un
  namelist /list_record/ pbxytype, pbxy, flxyfile, fn_flxy, flxytype, flxy

  pbxytype = list%pbxytype
  pbxy = list%pbxy
  flxyfile = list%flxyfile
  fn_flxy = list%fn_flxy
  flxytype = list%flxytype
  flxy = list%flxy

  !---- 設定ファイルを読み込む ----
  print *, "reading list_record in ", trim(p%fn_record)
  open(newunit=un, file=trim(p%fn_record), status='old')
  read(un, list_record)
  close(un)

  list%pbxytype = pbxytype
  list%pbxy = pbxy
  list%flxyfile = flxyfile
  list%fn_flxy = fn_flxy
  list%flxytype = flxytype
  list%flxy = flxy

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
