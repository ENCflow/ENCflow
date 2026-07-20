module m_util
  use m_parallel, only : par_stop
  implicit none
  private

  public :: str2sec
  public :: itoa
  public :: rtoa

contains
!=======================================================================
!=======================================================================
function str2sec(str, message) result(t)
  character(len=*), intent(in) :: str        ! NNN.N[d day h hour m min s sec]
  character(len=*), intent(in) :: message    ! error message
  real :: t                                  ! second
  character(:), allocatable :: s
  integer :: l, ll, ierr
  integer :: id, ih, im, is
  real :: c

  t = 0.0         ! 戻り値
  c = 1.0         ! 換算係数
  s = trim(str)   ! 文字列
  l = len(s)      ! 文字列長
  ll = 0          ! 数字の最後の位置
  ierr = 0

  id = index(s, "d")   ! 最初の"d"の位置
  ih = index(s, "h")   ! 最初の"h"の位置
  im = index(s, "m")   ! 最初の"m"の位置
  is = index(s, "s")   ! 最初の"s"の位置

  if (id > 0) then
    if (s(id:l) == "d" .or. s(id:l) == "day") then
      c = 60 * 60 * 24
      ll = id - 1
    else
      ierr = 1
    end if
  else if (ih > 0) then
    if (s(ih:l) == "h" .or. s(ih:l) == "hour") then
      c = 60 * 60
      ll = ih - 1
    else
      ierr = 1
    end if
  else if (im > 0) then
    if (s(im:l) == "m" .or. s(im:l) == "min") then
      c = 60
      ll = im - 1
    else
      ierr = 1
    end if
  else if (is > 0) then
    if (s(is:l) == "s" .or. s(is:l) == "sec") then
      ll = is - 1
    else
      ierr = 1
    end if
  else
    ll = l
  end if

  if (ierr > 0) then
    call par_stop("Error, "//message)
  end if

  if (isnumber(s(1:ll))) then
    read(s(1:ll), *) t
    t = t * c
  else
    call par_stop("Error, "//message)
  end if
end function str2sec


!-----------------------------------------------------------------------
!-----------------------------------------------------------------------
function isnumber(str) result(r)
  character(len=*), intent(in) :: str
  logical :: r
  integer :: i, l
  character :: c
  r = .false.
  l = len(trim(str))
  if (l < 1) return
  do i = 1, l
    c = str(i:i)
    if ((c >= "0" .and. c <= "9") .or. c == "." .or. c == " ") then
      r = .true.
    else
      r = .false.
      return
    end if
  end do
end function isnumber


!-----------------------------------------------------------------------
!-----------------------------------------------------------------------
pure function itoa(i) result(s)
  integer, intent(in) :: i
  character(:), allocatable :: s
  character(len=32) :: buf
  write(buf,'(i0)') i
  s = trim(buf)
end function itoa


!-----------------------------------------------------------------------
!-----------------------------------------------------------------------
pure function rtoa(r) result(s)
  real, intent(in) :: r
  character(:), allocatable :: s
  character(len=32) :: buf
  write(buf,'(f0.5)') r
  s = trim(buf)
end function rtoa


end module
