submodule(m_geoinfo) user_geoinfo
  use m_sysparam, only : t_sysparam
  implicit none
contains

!----------------------------------------------------------------------
! Example Wave (1)
!----------------------------------------------------------------------
module subroutine init_geoinfo_user_1(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: k, ix, iy

  do k = 1, int(p%nx / 4. * 3.)
    ix = k;
    iy = k + p%ny / 4
    iy = min(iy, p%ny)
    g%z(ix,iy) = 1.5
    g%x(ix,iy) = 0
    g%z(ix+1,iy) = 1.5
    g%x(ix+1,iy) = 0
  end do

end subroutine

!----------------------------------------------------------------------
! Example Wave (2)
!----------------------------------------------------------------------
module subroutine init_geoinfo_user_2(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: k, ix, iy

  do k = 1, int(p%nx / 4. * 3.)
    ix = k;
    iy = k + p%ny / 4
    iy = min(iy, p%ny)
    g%z(ix,iy) = 1.5
    g%x(ix,iy) = 0
  end do

end subroutine

!----------------------------------------------------------------------
! Example Wave (3)
!----------------------------------------------------------------------
module subroutine init_geoinfo_user_3(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: i, j
  
  do j = 1, p%ny
    do i = 1, p%nx

      if (g%z(i,j) <= -2000) then
        g%z(i,j) = 1000
        g%x(i,j) = 0
      else if (g%z(i,j) <= -100) then
        g%z(i,j) = 1000
        g%x(i,j) = 0
      else
        g%z(i,j) = g%z(i,j) / 10
        g%x(i,j) = 1
      endif

    enddo
  enddo

end subroutine

!----------------------------------------------------------------------
! 東北大氾濫計算
!----------------------------------------------------------------------
module subroutine init_geoinfo_user_4(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  if (p%initialized) continue
  if (g%initialized) continue
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
module subroutine init_geoinfo_user_5(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  if (p%initialized) continue
  if (g%initialized) continue
end subroutine



end submodule
