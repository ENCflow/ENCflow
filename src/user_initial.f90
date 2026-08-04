!======================================================================
! 初期条件のユーザールーチン集(m_state の submodule)
!
!   親モジュールへの公開面は入口の手続きのみ:
!     user_initial_defined : 識別名が登録済みかを返す(検証用。副作用なし)
!     user_initial_names   : 登録済み識別名の一覧文字列(エラー表示用)
!     user_initial_run     : 識別名で該当ルーチンを実行(全ランクで呼ばれる)
!   分岐(resolve)と識別名簿(routine_names)はこの submodule に閉じる。
!
!   ルーチンの追加手順(このファイルだけで完結する):
!     1. initial_template を複製して実装する(全域一時状態 ts に
!        全域添字 1:nx, 1:ny で書く契約)
!     2. routine_names に識別名を登録する(snake_case)
!     3. resolve の select case に分岐を1行追加する
!======================================================================
submodule(m_state) user_initial
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_parallel, only : par_abort
  implicit none

  ! ユーザールーチンの呼び出し規約
  abstract interface
    subroutine user_initial_if(p, g, s)
      import :: t_sysparam, t_geoinfo, t_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
    end subroutine
  end interface

  ! 識別名簿(エラー表示用の一覧)。名簿と resolve の分岐は同時に
  ! 更新すること(乖離は defined/run が「未定義名」として検出する)
  character(len=*), parameter :: routine_names(1:2) = [ character(len=32) :: &
      "wave_hump",   &   ! 波例題: 円形コサイン型の初期水位
      "template"     ]   ! 新規ルーチンの雛形(空)

contains

!======================================================================
!===================== 入口(親モジュールへ公開)=====================
!======================================================================

!----------------------------------------------------------------------
! 識別名が登録済みかを返す(検証用)
!----------------------------------------------------------------------
module function user_initial_defined(name) result(res)
  character(len=*), intent(in) :: name
  logical :: res
  procedure(user_initial_if), pointer :: fp
  fp => resolve(name)
  res = associated(fp)
end function

!----------------------------------------------------------------------
! 登録済み識別名の一覧文字列(エラー表示用)
!----------------------------------------------------------------------
module function user_initial_names() result(names)
  character(len=:), allocatable :: names
  integer :: i
  names = ""
  do i = 1, size(routine_names)
    if (i > 1) names = names//", "
    names = names//trim(routine_names(i))
  end do
end function

!----------------------------------------------------------------------
! 識別名で該当ルーチンを実行する(全ランクで冗長に呼ばれる)
!   名前の検証は呼び出し側が済ませている前提。ここでの不一致は
!   名簿と resolve の乖離(プログラミングエラー)なので abort
!----------------------------------------------------------------------
module subroutine user_initial_run(p, g, s, name)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  character(len=*), intent(in) :: name
  procedure(user_initial_if), pointer :: fp
  fp => resolve(name)
  if (.not. associated(fp)) call par_abort("user_initial_run: 未定義の識別名 "//trim(name))
  call fp(p, g, s)
end subroutine

!======================================================================
!======================= 分岐(submodule 私有)=======================
!======================================================================

!----------------------------------------------------------------------
! 識別名 → 手続きポインタ(未定義名は null)
!----------------------------------------------------------------------
function resolve(name) result(fp)
  character(len=*), intent(in) :: name
  procedure(user_initial_if), pointer :: fp
  select case (trim(name))
    case ("wave_hump")
      fp => initial_wave_hump
    case ("template")
      fp => initial_template
    case default
      fp => null()
  end select
end function

!======================================================================
!========================== ユーザールーチン ==========================
!======================================================================

!----------------------------------------------------------------------
! 波例題: 円形コサイン型の初期水位
!----------------------------------------------------------------------
subroutine initial_wave_hump(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s

  integer :: i, j
  real, parameter :: ll = 30., hh = 0.5
  real :: xx, yy, rr, dx, dy, eta
  real :: lx, ly
  real :: pi = acos(-1.0)
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  lx = g%lx
  ly = g%ly

  dx = g%dx
  dy = g%dy

  !s%h = 1.0

  do j = 1, g%ny
    do i = 1, g%nx
      xx = (i - 0.5) * dx - lx / 2
      yy = (j - 0.5) * dy - lx / 2
      rr = sqrt(xx**2 + yy**2)
      !rr = abs(xx)
      if (rr < ll / 2) then
        eta = hh * cos(rr / ll * 2 * pi) + hh
      else
        eta = 0.0
      end if
      !if (x(i,j) > 0) then
        s%h(i,j) = max(s%h(i,j) + eta - g%z(i,j), 0.0)
      !else
      !  d(i,j) = 0.0
      !end if
    end do
  end do

end subroutine


!----------------------------------------------------------------------
! 新規ルーチンの雛形(空。複製して使う)
!----------------------------------------------------------------------
subroutine initial_template(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (s%initialized) continue  ! 引数未使用の警告を抑制
end subroutine

end submodule
