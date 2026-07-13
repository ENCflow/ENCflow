module m_fileio
  use, intrinsic :: iso_fortran_env, only: real32
  use m_sysparam
  use sysdep_util

  implicit none
  private

  public :: fileio_read_matrix
  public :: fileio_write_matrix
  public :: fileio_un_open
  public :: fileio_un_read_matrix



  interface fileio_read_matrix
    procedure :: fileio_read_matrix_int
    procedure :: fileio_read_matrix_real
  end interface

  interface fileio_write_matrix
    procedure :: fileio_write_matrix_int
    procedure :: fileio_write_matrix_real
  end interface


  ! enumerator
  integer, parameter, public :: e_fmt_txt = 1    ! Don't change. Defined in sysparam
  integer, parameter, public :: e_fmt_bil = 2    ! Don't change. Defined in sysparam
  integer, parameter, public :: e_cmp_off = 0
  integer, parameter, public :: e_cmp_on = 1

contains

!----------------------------------------------------------------------
!----------------------------------------------------------------------
function fileio_un_open(fname, e_fmt) result(un)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: e_fmt
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      open(newunit=un, file=fname, status='old')
    case (e_fmt_bil)
      open(newunit=un,file=fname, form='unformatted', status='old', access='stream')
    case default
      open(newunit=un, file=fname, status='old')
  end select

end function


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine fileio_un_read_matrix(un, nx, ny, a, e_fmt)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  real, intent(inout) :: a(1:nx,1:ny)
  integer, intent(in) :: e_fmt

  select case (e_fmt)
    case (e_fmt_txt)
      call read_textmatrix_real(un, nx, ny, a)
    case (e_fmt_bil)
      call read_bil_real(un, nx, ny, a)
    case default
      call read_textmatrix_real(un, nx, ny, a)
  end select

end subroutine



!======================================================================
!======================================================================
!======================================================================
!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine fileio_read_matrix_int(fname, nx, ny, a, e_fmt)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  integer, intent(inout) :: a(1:nx,1:ny)
  integer, intent(in) :: e_fmt
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      open(newunit=un, file=fname, status='old')
      call read_textmatrix_int(un, nx, ny, a)
    case (e_fmt_bil)
      open(newunit=un,file=fname, form='unformatted', status='old', access='stream')
      call read_bil_int(un, nx, ny, a)
    case default
      open(newunit=un, file=fname, status='old')
      call read_textmatrix_int(un, nx, ny, a)
  end select
  close(un)

end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine fileio_write_matrix_int(fname, nx, ny, a, e_fmt, compress)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  integer, intent(in) :: a(1:nx,1:ny)
  integer, intent(in) :: e_fmt
  integer, intent(in) :: compress
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      open(newunit=un, file=fname, status='replace')
      call write_textmatrix_int(un, nx, ny, a)
    case (e_fmt_bil)
      open(newunit=un,file=fname, form='unformatted', status='replace', access='stream')
      call write_bil_int(un, nx, ny, a)
    case default
      open(newunit=un, file=fname, status='replace')
      call write_textmatrix_int(un, nx, ny, a)
  end select
  close(un)

  if (compress > 0) then
    call sysdep_compress(fname)
  end if

end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine fileio_read_matrix_real(fname, nx, ny, a, e_fmt)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  real, intent(inout) :: a(1:nx,1:ny)
  integer, intent(in) :: e_fmt
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      open(newunit=un, file=fname, status='old')
      call read_textmatrix_real(un, nx, ny, a)
    case (e_fmt_bil)
      open(newunit=un,file=fname, form='unformatted', status='old', access='stream')
      call read_bil_real(un, nx, ny, a)
    case default
      open(newunit=un, file=fname, status='old')
      call read_textmatrix_real(un, nx, ny, a)
  end select
  close(un)

end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine fileio_write_matrix_real(fname, nx, ny, a, e_fmt, compress)
  character(len=*), intent(in) :: fname
  integer, intent(in) :: nx, ny
  real, intent(in) :: a(1:nx,1:ny)
  integer, intent(in) :: e_fmt
  integer, intent(in) :: compress
  integer :: un

  select case (e_fmt)
    case (e_fmt_txt)
      open(newunit=un, file=fname, status='replace')
      call write_textmatrix_real(un, nx, ny, a)
    case (e_fmt_bil)
      open(newunit=un,file=fname, form='unformatted', status='replace', access='stream')
      call write_bil_real(un, nx, ny, a)
    case default
      open(newunit=un, file=fname, status='replace')
      call write_textmatrix_real(un, nx, ny, a)
  end select
  close(un)

  if (compress > 0) then
    call sysdep_compress(fname)
  end if

end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine read_textmatrix_int(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  integer, intent(inout) :: a(1:nx,1:ny)
  integer :: j
  do j = 1, ny
    read(un, *) a(1:nx,j)
  enddo
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine write_textmatrix_int(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  integer, intent(in) :: a(1:nx,1:ny)
  integer :: j
  do j = 1, ny
    write(un,'(*(i8))') a(1:nx,j)
  enddo
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine read_textmatrix_real(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  real, intent(inout) :: a(1:nx,1:ny)
  integer :: j
  do j = 1, ny
    read(un, *) a(1:nx,j)
  enddo
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine write_textmatrix_real(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  real, intent(in) :: a(1:nx,1:ny)
  integer :: j
  do j = 1, ny
    write(un,'(*(f12.4))') a(1:nx,j)
  enddo
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine read_bil_int(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  integer, intent(inout) :: a(1:nx,1:ny)
  read(un) a
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine write_bil_int(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  integer, intent(in) :: a(1:nx,1:ny)
  write(un) a
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine read_bil_real(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  real, intent(inout) :: a(1:nx,1:ny)
  real(real32) :: r(1:nx,1:ny)
  read(un) r
  a(:,:) = r(:,:)
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine write_bil_real(un, nx, ny, a)
  integer, intent(in) :: un
  integer, intent(in) :: nx, ny
  real, intent(in) :: a(1:nx,1:ny)
  real(real32) :: r(1:nx,1:ny)
  r(:,:) = real(a(:,:), kind=real32)
  write(un) r
end subroutine


end module
