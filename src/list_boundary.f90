module list_boundary
  use m_sysparam, only : t_sysparam
  implicit none
  private

  public :: t_list_boundary
  public :: list_boundary_read

  integer, parameter :: maxpathlen = 256
  integer, parameter :: nsrccmax = 999
  integer, parameter :: nsrcvmax = 999

  type t_list_boundary
    integer :: nsrcc = 0                           ! 湧出しセル数
    integer :: srccell(1:2,1:nsrccmax) = -9999     ! 湧出しセルの座標　
    character(len=maxpathlen) :: fn_srccell = ""   ! 湧出しセルファイル名
    integer :: nsrcv = 0                           ! 湧出し時系列のデータ数 
    real :: srcval(1:2,1:nsrcvmax) = -9999         ! 湧出し時系列値 (min, m3/s)
    character(len=maxpathlen) :: fn_srcval = ""    ! 湧出し時系列ファイル名
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 降水設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_boundary_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_boundary), intent(inout) :: list
  integer :: nsrcc                               ! 湧出しセル数
  integer :: srccell(1:2,1:nsrccmax)             ! 湧出しセルの座標　
  integer :: nsrcv                               ! 湧出し時系列のデータ数 
  real :: srcval(1:2,1:nsrcvmax)                 ! 湧出し時系列値
  character(:), allocatable :: fn_srccell                     ! 湧出しセルファイル名
  character(:), allocatable :: fn_srcval                      ! 湧出し時系列ファイル名
  integer :: un
  namelist /list_boundary/ nsrcc, srccell, nsrcv, srcval, fn_srccell, fn_srcval


  nsrcc = list%nsrcc
  srccell = list%srccell
  nsrcv = list%nsrcv
  srcval = list%srcval
  fn_srccell = list%fn_srccell
  fn_srcval = list%fn_srcval

  !---- 設定ファイルを読み込む ----
  print *, "reading list_boundary in ", trim(p%fn_boundary)
  open(newunit=un, file=trim(p%fn_boundary), status='old')
  read(un, list_boundary)
  close(un)

  list%nsrcc = nsrcc
  list%srccell = srccell
  list%nsrcv = nsrcv
  list%srcval = srcval
  list%fn_srccell = fn_srccell
  list%fn_srcval = fn_srcval


end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
