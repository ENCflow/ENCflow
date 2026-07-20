submodule(m_state) user_initial
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  implicit none

contains


!----------------------------------------------------------------------
!----------------------------------------------------------------------
module subroutine init_state_user_1(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s

  integer :: i, j
  real, parameter :: ll = 30., hh = 0.5
  real :: xx, yy, rr, dx, dy, eta
  real :: lx, ly
  real :: pi = acos(-1.0)

  lx = g%lx
  ly = g%ly

  dx = lx / p%nx
  dy = ly / p%ny

  !s%h = 1.0

  do j = 1, p%ny
    do i = 1, p%nx
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
!----------------------------------------------------------------------
module subroutine init_state_user_2(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  if (p%initialized) continue
  if (g%initialized) continue
  if (s%initialized) continue
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
module subroutine init_state_user_3(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  if (p%initialized) continue
  if (g%initialized) continue
  if (s%initialized) continue
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
module subroutine init_state_user_4(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  if (p%initialized) continue
  if (g%initialized) continue
  if (s%initialized) continue
end subroutine

end submodule
