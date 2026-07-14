program main
  use m_main, only : m_main_all
  implicit none
  character(len=256) :: fn_param

  call get_fn_param(fn_param)
  call m_main_all(fn_param)

contains
!----------------------------------------------------------------------
! コマンドライン引数から設定ファイル名を取得する
!----------------------------------------------------------------------
subroutine get_fn_param(fn_param)
  character(len=*) :: fn_param

  ! コマンドライン引数の文字列を保存する構造体の宣言
  !  可変長文字列の配列が直接作れないため構造体の配列を利用
  type :: arguments
    character(:), allocatable :: v           ! 無指定文字長（可変長）文字列変数vを要素に持つ
  end type

  ! コマンドライン引数の数と文字列
  integer :: argc
  type(arguments), allocatable :: arg(:)

  
  !--- コマンドライン引数取得の準備 ---
  argc = command_argument_count()            ! 引数の数を取得
  allocate(arg(0:argc))                      ! 構造体のメモリを確保

  !--- コマンドライン引数を取得 ---
  get_arguments: block
    integer :: i, l
    do i = 0, argc
      call get_command_argument(number=i, length=l)         ! i番目の引数の長さを取得
      allocate(character(l) :: arg(i)%v)                    ! 構造体中の文字列用メモリを確保
      call get_command_argument(number=i, value=arg(i)%v)   ! 引数の文字列を取得
    end do
  end block get_arguments

  if (argc >= 1) then
    fn_param = arg(1)%v
  else
    print ('(a, a, a)'), "usage: ", arg(0)%v, " parameterfile"
    stop
  end if
end subroutine

end program
