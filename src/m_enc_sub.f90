submodule(m_swflow_enc) m_enc_sub
  use m_sysparam, only : t_sysparam
  use m_state, only : t_state
  implicit none

contains
 
!----------------------------------------------------------------------
! 移流項の計算
!----------------------------------------------------------------------
module subroutine advection_sub(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(inout) :: sx

  integer :: i, j, k
  real :: dux, duy, dvx, dvy
  real :: ww(1:8), wwx(1:8), wwy(1:8)
  real :: ulm(1:p%nx,1:p%ny), vlm(1:p%nx,1:p%ny)
  real :: lm

  if (f_advection_term == 0) return

  !$omp parallel do private(i, j, lm)
  do j = g%wy(1), g%wy(2)
    do i = g%wx(1,j)+1, g%wx(2,j)-1
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) < p%dd) cycle
      lm = g%gv(i,j) + (1 - g%gv(i,j)) * p%cm
      ulm(i,j) = s%u(i,j) * lm
      vlm(i,j) = s%v(i,j) * lm
    end do
  end do
  !$omp end parallel do

  !$omp parallel do private(i, j, k, ww, wwx, wwy, dux, duy, dvx, dvy)
  do j = g%wy(1)+1, g%wy(2)-1
    do i = g%wx(1,j)+1, g%wx(2,j)-1
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) < p%dd) cycle
      ! 風上差分による移流項の計算
      ww(:) = get_ww(s%u(i,j), s%v(i,j), s%vv(i,j))
      forall(k=1:8) wwx(k) = w8x(k) * ww(k)
      forall(k=1:8) wwy(k) = w8y(k) * ww(k)
      call get_diff_sub(ulm, vlm, s%h, p%dd, wwx, wwy, g%x, i, j, p%nx, p%ny, dux, duy, dvx, dvy)
      sx%taxy(1,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy)
      sx%taxy(2,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy)
      if (f_advection_tvd > 0) then
        ! 中心差分による移流項の計算
        call get_diff_sub(ulm, vlm, s%h, p%dd, w8x, w8y, g%x, i, j, p%nx, p%ny, dux, duy, dvx, dvy)
        sx%taxy(3,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy)
        sx%taxy(4,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy)
      end if
    end do
  end do
  !$omp end parallel do

!end subroutine
contains
  ! 風上差分用のウェイトを計算
  function get_ww(u, v, vv) result(ww)
    real, intent(in) :: u, v
    real, intent(in) :: vv
    real :: ww(1:8)
    real :: wk
    integer :: k
    if (p_adv_upwind_index > 0 .and. vv > 0) then
      do k = 1, 8
        wk = -(u * n8x(k) + v * n8y(k)) / vv                    ! -1~1
        wk = max(1 - (1 - wk) * p_adv_upwind_index / 2, 0.0)    ! 0～1
        ww(k) = wk
      end do
    else
      ww(:) = 1
    end if
  end function
end subroutine


!----------------------------------------------------------------------
! 変数u, vの微分
!----------------------------------------------------------------------
subroutine get_diff_sub(u, v, h, dd, wx, wy, x, i, j, nx, ny, dux, duy, dvx, dvy)
  real, intent(in) :: u(1:nx,1:ny)
  real, intent(in) :: v(1:nx,1:ny)
  real, intent(in) :: h(1:nx,1:ny)
  real, intent(in) :: dd
  real, intent(in) :: wx(1:8), wy(1:8)
  integer, intent(in) :: x(0:nx+1,0:ny+1)
  integer, intent(in) :: i, j, nx, ny
  real, intent(out) :: dux, duy
  real, intent(out) :: dvx, dvy

  real :: du, dv
  real :: swx, swy, wwx, wwy
  integer :: in, jn, k

  dux = 0
  duy = 0
  dvx = 0
  dvy = 0
  swx = 0
  swy = 0

  do k = 1, 8
    in = i + din(k)
    jn = j + djn(k)
    if (h(in,jn) < dd) cycle
    wwx = x(in,jn) * wx(k)
    wwy = x(in,jn) * wy(k)
    du = (u(in,jn) - u(i,j))
    dv = (v(in,jn) - v(i,j))
    dux = dux + du * r8x(k) * wwx
    dvx = dvx + dv * r8x(k) * wwx
    duy = duy + du * r8y(k) * wwy
    dvy = dvy + dv * r8y(k) * wwy
    swx = swx + wwx !* din2(k)
    swy = swy + wwy !* djn2(k)
  end do

  if (swx > 0) then
    dux = dux / swx
    dvx = dvx / swx
  end if
  if (swy > 0) then
    duy = duy / swy
    dvy = dvy / swy
  end if

end subroutine


end submodule
