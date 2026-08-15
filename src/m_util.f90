module m_util
  use m_parallel, only : par_stop
  implicit none
  private

  public :: str2sec
  public :: itoa
  public :: rtoa
  public :: ymd_to_jdn
  public :: jdn_to_ymd
  public :: parse_datetime

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
    call par_stop(message//" (bad time unit): "//trim(s))
  end if

  if (isnumber(s(1:ll))) then
    read(s(1:ll), *) t
    t = t * c
  else
    call par_stop(message//" (not a number): "//trim(s))
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


!----------------------------------------------------------------------
! 暦(グレゴリオ暦)とユリウス通日の相互変換(Fliegel & Van Flandern。
! 整数演算・うるう年規則込み。往復・2100年平年を Python 対照で検証済み。§27)
!----------------------------------------------------------------------
pure function ymd_to_jdn(y, mo, d) result(jdn)
  integer, intent(in) :: y, mo, d
  integer :: jdn
  integer :: a
  a = (mo - 14) / 12
  jdn = (1461 * (y + 4800 + a)) / 4 + (367 * (mo - 2 - 12 * a)) / 12 &
        - (3 * ((y + 4900 + a) / 100)) / 4 + d - 32075
end function

pure subroutine jdn_to_ymd(jdn, y, mo, d)
  integer, intent(in) :: jdn
  integer, intent(out) :: y, mo, d
  integer :: l, n, i, j
  l = jdn + 68569
  n = (4 * l) / 146097
  l = l - (146097 * n + 3) / 4
  i = (4000 * (l + 1)) / 1461001
  l = l - (1461 * i) / 4 + 31
  j = (80 * l) / 2447
  d = l - (2447 * j) / 80
  l = j / 11
  mo = j + 2 - 12 * l
  y = 100 * (n - 49) + i + l
end subroutine


!----------------------------------------------------------------------
! 日時文字列の解析("YYYY-MM-DD" または "YYYY-MM-DD hh:mm"。
! 区切りは - : / 可)。jdn = その日のユリウス通日、sec = 日内秒
!----------------------------------------------------------------------
subroutine parse_datetime(str, jdn, sec, message)
  character(len=*), intent(in) :: str
  integer, intent(out) :: jdn
  real, intent(out) :: sec
  character(len=*), intent(in) :: message
  character(len=len(str)) :: buf
  integer :: y, mo, d, hh, mi, k, ios
  buf = str
  do k = 1, len_trim(buf)
    if (buf(k:k) == '-' .or. buf(k:k) == ':' .or. buf(k:k) == '/') buf(k:k) = ' '
  end do
  hh = 0
  mi = 0
  read(buf, *, iostat=ios) y, mo, d, hh, mi
  if (ios /= 0) then
    hh = 0
    mi = 0
    read(buf, *, iostat=ios) y, mo, d
    if (ios /= 0) call par_stop(message//" (unreadable date): "//trim(str))
  end if
  if (mo < 1 .or. mo > 12 .or. d < 1 .or. d > 31 .or. &
      hh < 0 .or. hh > 23 .or. mi < 0 .or. mi > 59) then
    call par_stop(message//" (out of range): "//trim(str))
  end if
  jdn = ymd_to_jdn(y, mo, d)
  sec = real(hh) * 3600.0 + real(mi) * 60.0
end subroutine


end module
