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

  ta = calc_kth_advection_v1(s, sx, i, j, k, in, jn, uve)
  !ta = calc_kth_advection_v2(s, sx, i, j, k, in, jn, uve)

end function

!----------------------------------------------------------------------
! 移流項の計算
!----------------------------------------------------------------------
module subroutine advection(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(inout) :: sx

  call  advection_v1(p, g, s, sx)
  !call  advection_v2(p, g, s, sx)

end subroutine



!======================================================================
!======================================================================
!----------------------------------------------------------------------
! 移流項を計算する
!----------------------------------------------------------------------
function calc_kth_advection_v1(s, sx, i, j, k, in, jn, uve) result(ta)
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
subroutine advection_v1(p, g, s, sx)
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
      call get_diff_v1(sx%ulm, sx%vlm, s%h, p%dd, wwx, wwy, g%x, i, j, g%nx, g%ny, dux, duy, dvx, dvy)
      sx%taxy(1,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy)
      sx%taxy(2,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy)
      if (f_advection_tvd > 0) then
        ! 中心差分による移流項の計算
        call get_diff_v1(sx%ulm, sx%vlm, s%h, p%dd, w8x, w8y, g%x, i, j, g%nx, g%ny, dux, duy, dvx, dvy)
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
subroutine get_diff_v1(u, v, h, dd, wx, wy, x, i, j, nx, ny, dux, duy, dvx, dvy)
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


!======================================================================
!======================================================================
!----------------------------------------------------------------------
! 移流項を計算する
!----------------------------------------------------------------------
function calc_kth_advection_v2(s, sx, i, j, k, in, jn, uve) result(ta)
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  integer, intent(in) :: i, j, k, in, jn
  real, intent(in) :: uve
  real :: ta
  real :: taxe, taye
  if (s%initialized) continue
  if (f_advection_term <= 0) then
    ta = 0
    return
  end if
  if (.true.) then    ! 両側セル平均  tada
  !if (.false.) then   ! 風上セル
    ! 境界の両側セルの平均移流項を用いる
    taxe = (sx%taxy(1,i,j) + sx%taxy(1,in,jn)) / 2
    taye = (sx%taxy(2,i,j) + sx%taxy(2,in,jn)) / 2
  else
    ! 境界から見て風上側のセルの移流項を用いる
    if (uve > 0) then
      taxe = sx%taxy(1,i,j)
      taye = sx%taxy(2,i,j)
    else if (uve < 0) then
      taxe = sx%taxy(1,in,jn)
      taye = sx%taxy(2,in,jn)
    else
      taxe = 0
      taye = 0
    endif
  end if
  ta = taxe * n8x(k) + taye * n8y(k)             ! 移流項(符合は中心セルから近傍セルに向かい正)
  !ta = ta * 1.5
end function


!----------------------------------------------------------------------
! 移流項の計算(局所型)
!----------------------------------------------------------------------
subroutine advection_v2(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(inout) :: sx

  integer :: i, j, k
  real :: ww(1:8), wwx(1:8), wwy(1:8)
  real :: uu(1:3,1:3), vv(1:3,1:3), uv(1:3,1:3)
  real :: hh(1:3,1:3)
  integer :: xx(0:4,0:4)
  real :: u(0:8), v(0:8)
  integer :: ii(1:8), jj(1:8)
        real :: dux, duy, dvx, dvy
        real :: duux, dvvy, duvx, duvy

  if (f_advection_term == 0) return

  !$omp parallel do private(i, j, k, ww, wwx, wwy, ii, jj, u, v, uu, vv, uv, hh, xx, dux, duy, dvx, dvy, duux, dvvy, duvx, duvy)
  do j = g%wy(1)+1, g%wy(2)-1
    do i = g%wx(1,j)+1, g%wx(2,j)-1
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) < p%dd) cycle

      ! 風上差分による重みの計算
      ww(:) = get_ww_upw_v2(s%u(i,j), s%v(i,j), s%vv(i,j))
      forall(k=1:8) wwx(k) = w8x(k) * ww(k)
      forall(k=1:8) wwy(k) = w8y(k) * ww(k)

      ! 水深と領域フラグを切り出す
      hh(1:3,1:3) = s%h(i-1:i+1,j-1:j+1)
      xx(0:4,0:4) = g%x(i-2:i+2,j-2:j+2)

      ! セル中心の流速
      u(0) = s%u(i,j)
      v(0) = s%v(i,j)

      !if (.true.) then   ! 隣接セル  tada
      if (.false.) then  ! セル界面上
        ! 隣接セルの流速を使用
        do k = 1, 8
          u(k) = s%u(i+din(k),j+djn(k))
          v(k) = s%v(i+din(k),j+djn(k))
        end do
      else
        ! セル界面上(頂点)の流速を使用
        do k = 1, 8
          ii(k) = i + die(k)    ! セルi,jの界面上のベクトルのインデックス
          jj(k) = j + dje(k)    ! セルi,jの界面上のベクトルのインデックス
          select case(k)
            case (1, 3, 6, 8)
              ! 頂点の流速はU1とU3を軸方向に変換して平均化
              u(k) = (sx%uv(1, ii(k),jj(k)) / n8x(1) + sx%uv(3, ii(k),jj(k)) / n8x(3)) / 2
              v(k) = (sx%uv(1, ii(k),jj(k)) / n8y(1) + sx%uv(3, ii(k),jj(k)) / n8y(3)) / 2
            case default
              ! 2,4,5,7は後で計算するのでここでは何もしない
          end select
        end do
        ! セル界面上(辺の中点)の流速
        u(2) = (u(1) + u(3)) / 2               ! 辺の左右端から補間
        v(2) = -sx%uv(2, ii(2),jj(2))          ! yの正の方向に変換
        u(4) = -sx%uv(4, ii(4),jj(4))          ! xの正の方向に変換
        v(4) = (v(1) + v(6)) / 2               ! 辺の上限端から補間
        u(5) = -sx%uv(4, ii(5),jj(5))          ! 右のセルのu5をxの正方向に変換
        v(5) = (v(3) + v(8)) / 2               ! 辺の上下端から補間
        u(7) = (u(6) + u(8)) / 2               ! 辺の左右端から補間
        v(7) = -sx%uv(2, ii(7),jj(7))          ! 上のセルのv2をyの正方向に変換
      end if

      !if (.true.) then   ! 非保存形 tada
      if (.false.) then  ! 保存形
        ! 非保存形
        ! uとvを並べてuuとvvの形に整形して代入
        uu = reshape([ u(1), u(2), u(3), u(4), u(0), u(5), u(6), u(7), u(8) ], shape(uu))
        vv = reshape([ v(1), v(2), v(3), v(4), v(0), v(5), v(6), v(7), v(8) ], shape(vv))
        ! 勾配を計算
        call get_diff_v2(uu, vv, hh, p%dd, wwx, wwy, xx, 2, 2, 3, 3, dux, duy, dvx, dvy)
        ! 移流項を計算
        sx%taxy(1,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy) * g%lm(i,j)
        sx%taxy(2,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy) * g%lm(i,j)
      else
        ! 保存形
        ! uとvを並べてuu,vv,uvの形に整形して代入
        uu = reshape([ u(1)**2, u(2)**2, u(3)**2, &
                       u(4)**2, u(0)**2, u(5)**2, &
                       u(6)**2, u(7)**2, u(8)**2 ], shape(uu))
        vv = reshape([ v(1)**2, v(2)**2, v(3)**2, &
                       v(4)**2, v(0)**2, v(5)**2, &
                       v(6)**2, v(7)**2, v(8)**2 ], shape(vv))
        uv = reshape([ u(1)*v(1), u(2)*v(2), u(3)*v(3), &
                       u(4)*v(4), u(0)*v(0), u(5)*v(5), &
                       u(6)*v(6), u(7)*v(7), u(8)*v(8) ], shape(uv))
        ! 勾配を計算
        call get_diff2_v2(uu, vv, uv, hh, p%dd, wwx, wwy, xx, duux, dvvy, duvx, duvy)
        ! 移流項を計算
        sx%taxy(1,i,j) = -(duux + duvy) * g%lm(i,j)
        sx%taxy(2,i,j) = -(duvx + dvvy) * g%lm(i,j)
      end if

    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! 風上差分用のウェイトを計算
!----------------------------------------------------------------------
function get_ww_upw_v2(u, v, vv) result(ww_upw)
  real, intent(in) :: u, v
  real, intent(in) :: vv
  real :: ww_upw(1:8)
  real :: wk
  integer :: k
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


!----------------------------------------------------------------------
! 変数uu, vv, uvの微分(保存形)
!----------------------------------------------------------------------
subroutine get_diff2_v2(uu, vv, uv, h, dd, wx, wy, x, duux, dvvy, duvx, duvy)
  real, intent(in) :: uu(1:3,1:3)
  real, intent(in) :: vv(1:3,1:3)
  real, intent(in) :: uv(1:3,1:3)
  real, intent(in) :: h(1:3,1:3)
  real, intent(in) :: dd
  real, intent(in) :: wx(1:8), wy(1:8)
  integer, intent(in) :: x(0:4,0:4)
  real, intent(out) :: duux, dvvy
  real, intent(out) :: duvx, duvy

  real :: duu, dvv, duv
  real :: swx, swy, wwx, wwy
  integer :: in, jn, k

  duux = 0
  dvvy = 0
  duvx = 0
  duvy = 0
  swx = 0
  swy = 0

  do k = 1, 8
    in = 2 + din(k)
    jn = 2 + djn(k)
    if (h(in,jn) < dd) cycle
    wwx = x(in,jn) * wx(k)
    wwy = x(in,jn) * wy(k)
    duu = (uu(in,jn) - uu(2,2))
    dvv = (vv(in,jn) - vv(2,2))
    duv = (uv(in,jn) - uv(2,2))
    duux = duux + duu * r8x(k) * wwx
    dvvy = dvvy + dvv * r8y(k) * wwy
    duvx = duvx + duv * r8x(k) * wwx
    duvy = duvy + duv * r8y(k) * wwy
    swx = swx + wwx
    swy = swy + wwy
  end do

  if (swx > 0) then
    duux = duux / swx
    duvx = duvx / swx
  end if
  if (swy > 0) then
    dvvy = dvvy / swy
    duvy = duvy / swy
  end if

end subroutine


!----------------------------------------------------------------------
! 変数u, vの微分(非保存形)
!----------------------------------------------------------------------
subroutine get_diff_v2(u, v, h, dd, wx, wy, x, i, j, nx, ny, dux, duy, dvx, dvy)
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
