module m_util
  implicit none
  private

  public :: util_str2sec

contains
!=======================================================================
!=======================================================================
function util_str2sec(str, message) result(t)
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
    print *, "Error, ", message
    stop
  end if

  if (isnumber(s(1:ll))) then
    read(s(1:ll), *) t
    t = t * c
  else
    print *, "Error, ", message
    stop
  end if

contains
  function isnumber(s) result(r)
    character(len=*), intent(in) :: s
    logical :: r
    integer :: i, l
    character :: c
    r = .false.
    l = len(trim(s))
    if (l < 1) return
    do i = 1, l
      c = s(i:i)
      if ((c >= "0" .and. c <= "9") .or. c == "." .or. c == " ") then
        r = .true.
      else
        r = .false.
        return
      end if
    end do
  end function
end function


end module

!=======================================================================
!=======================================================================
!
!program tadada
!  use m_datetime
!  real :: t
!  character(len=256) :: str
!
!  call get_arg(str)
!  t = str2sec(str, "Wwwwwww")
!  print *, t
!
!
!contains
!!----------------------------------------------------------------------
!! コマンドライン引数から文字列を取得
!!----------------------------------------------------------------------
!subroutine get_arg(str)
!  character(len=*) :: str
!
!  ! コマンドライン引数の文字列を保存する構造体の宣言
!  !  可変長文字列の配列が直接作れないため構造体の配列を利用
!  type :: arguments
!    character(:), allocatable :: v           ! 無指定文字長（可変長）文字列変数vを要素に持つ
!  end type
!
!  ! コマンドライン引数の数と文字列
!  integer :: argc
!  type(arguments), allocatable :: arg(:)
!
!  
!  !--- コマンドライン引数取得の準備 ---
!  argc = command_argument_count()            ! 引数の数を取得
!  allocate(arg(0:argc))                      ! 構造体のメモリを確保
!  !print *, argc
!
!  !--- コマンドライン引数を取得 ---
!  get_arguments: block
!    integer :: i, l
!    do i = 0, argc
!      call get_command_argument(number=i, length=l)         ! i番目の引数の長さを取得
!      allocate(character(l) :: arg(i)%v)                    ! 構造体中の文字列用メモリを確保
!      call get_command_argument(number=i, value=arg(i)%v)   ! 引数の文字列を取得
!      !print *, i, arg(i)%v
!    end do
!  end block get_arguments
!
!  if (argc >= 1) then
!    str = arg(1)%v
!    !print *, "get_str: str = ", str
!  else
!    print ('(a, a, a)'), "usage: ", arg(0)%v, " strings"
!    stop
!  end if
!end subroutine
!
!end program
