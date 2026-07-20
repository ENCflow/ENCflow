submodule(m_swflow_enc) m_swflow_enc_adv
  use m_state, only : t_state
  implicit none
contains
!----------------------------------------------------------------------
! 移流項を計算する
!----------------------------------------------------------------------
module function calc_kth_advection(s, sx, i, j, k, in, jn, uve) result(ta)
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(in) :: sx
  integer, intent(in) :: i, j, k, in, jn
  real, intent(in) :: uve
  real :: ta
  real :: taxe, taye
  real :: taxe2, taye2, tae2
  integer :: inn, jnn, ino, jno
  real :: duvc, duvr, duvl, duv0
  real :: rr, rl, phir, phil, phi
  if (uve > 0.0) continue
  ! 風上差分による移流項
  taxe = (sx%taxy(1,i,j) + sx%taxy(1,in,jn)) / 2  ! 移流項(x方向, 符合は座標軸方向が正)
  taye = (sx%taxy(2,i,j) + sx%taxy(2,in,jn)) / 2  ! 移流項(y方向, 符合は座標軸方向が正)
  ta = taxe * n8x(k) + taye * n8y(k)             ! 移流項(符合は中心セルから近傍セルに向かい正)
  !ta = ta * 1.5
  ! TVD(風上差分と中心差分の混合)
  if (f_advection_tvd > 0) then
    ! 中心差分による移流項
    taxe2 = (sx%taxy(3,i,j) + sx%taxy(3,in,jn)) / 2
    taye2 = (sx%taxy(4,i,j) + sx%taxy(4,in,jn)) / 2
    tae2 = taxe2 * n8x(k) + taye2 * n8y(k)
    tae2 = tae2 * 1.5
    inn = in + din(k)  ! k近傍のさらに外側のセル
    jnn = jn + djn(k)  ! k近傍のさらに外側のセル
    ino = i + din(9-k) ! k近傍の反対側のセル
    jno = j + djn(9-k) ! k近傍の反対側のセル
    duvr = (s%u(inn,jnn) - s%u(in ,jn )) * n8x(k) + (s%v(inn,jnn) - s%v(in ,jn )) * n8y(k)
    duvc = (s%u(in ,jn ) - s%u(i  ,j  )) * n8x(k) + (s%v(in ,jn ) - s%v(i  ,j  )) * n8y(k)
    duvl = (s%u(i  ,j  ) - s%u(ino,jno)) * n8x(k) + (s%v(i  ,j  ) - s%v(ino,jno)) * n8y(k)
    duv0 = duvc + sign(1.E-5, duvc)
    rr = duvr / duv0
    rl = duvl / duv0

    phil = max(0.0, min(1.0, rl))
    phir = max(0.0, min(1.0, rr))

    !phir = max(0.0, min(1.0, 2 * rr))
    !phil = max(0.0, min(1.0, 2 * rl))

    if (phil >= 0 .and. phir >= 0) then
      phi = min(1.0, min(phir, phil))
    else
      phi = 0.0
    end if

    !if (uve > 0) then
    !  phi = phil
    !else if (uve < 0) then
    !  phi = phir
    !else
    !  phi = min(phir, phil)
    !end if

    ! 風上差分と中心差分の混合
    ta = ta + phi * (tae2 - ta)
    !ta = (ta + tae2) / 2
  end if
end function


!----------------------------------------------------------------------
! 移流項の計算
!----------------------------------------------------------------------
module subroutine advection(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(inout) :: sx

  integer :: i, j, k
  real :: dux, duy, dvx, dvy
  real :: ww(1:8), wwx(1:8), wwy(1:8)
  !real :: ulm(1:g%nx,1:g%ny), vlm(1:g%nx,1:g%ny)

  if (f_advection_term == 0) return

  !$omp parallel do private(i, j)
  do j = g%wy(1), g%wy(2)
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle   ! get_diffで陸から1セル外側まで参照することに注意
      if (s%h(i,j) < p%dd) cycle
      sx%ulm(i,j) = s%u(i,j) * g%lm(i,j)
      sx%vlm(i,j) = s%v(i,j) * g%lm(i,j)
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
      call get_diff(sx%ulm, sx%vlm, s%h, p%dd, wwx, wwy, g%x, i, j, g%nx, g%ny, dux, duy, dvx, dvy)
      sx%taxy(1,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy)
      sx%taxy(2,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy)
      if (f_advection_tvd > 0) then
        ! 中心差分による移流項の計算
        call get_diff(sx%ulm, sx%vlm, s%h, p%dd, w8x, w8y, g%x, i, j, g%nx, g%ny, dux, duy, dvx, dvy)
        sx%taxy(3,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy)
        sx%taxy(4,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy)
      end if
    end do
  end do
  !$omp end parallel do

!end subroutine
contains
  ! 風上差分用のウェイトを計算
  function get_ww(u, v, vv) result(ww_upw)
    real, intent(in) :: u, v
    real, intent(in) :: vv
    integer :: k
    real :: ww_upw(1:8)
    real :: wk
    if (p_adv_upwind_index > 0 .and. vv > 0) then
      do k = 1, 8
        wk = -(u * n8x(k) + v * n8y(k)) / vv                    ! -1~1
        wk = max(1 - (1 - wk) * p_adv_upwind_index / 2, 0.0)    ! 0～1
        ww_upw(k) = wk
      end do
    else
      ww_upw(:) = 1
    end if
  end function
end subroutine


!----------------------------------------------------------------------
! 変数u, vの微分
!----------------------------------------------------------------------
subroutine get_diff(u, v, h, dd, wx, wy, x, i, j, nx, ny, dux, duy, dvx, dvy)
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
