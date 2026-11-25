module m_paddy_law
  ! ============ 田んぼダムの落水口の装置則(葉のモジュール。developer.md §119) ============
  ! m_paddy(表現 A のタンク)と、区画を解像する表現 B の落水口のエッジ(浅水流の本体)の両方が使うので、
  ! 状態を持たない型と純粋関数だけをここに置く(m_paddy から移した。式は paddy_plan.md §5)。
  !   堰(天端 z、幅 B): 本間公式の形を流量係数 C で一般化(C = 0.525 で本間公式 0.35・0.91。独自の一般化)。
  !     h1 = H − z、h2 = max(h_D − z, 0)。自由 (2/3)C√(2g)B h1^1.5、h2/h1 ≥ 2/3 で潜り
  !     √3 C B h2 √(2g(h1 − h2)) = 自由 × S(r)、S(r) = (3√3/2) r √(1 − r)
  !   三角の切欠き: 自由 (8/15) C tan(θ/2)√(2g) h1^2.5 に同じ S(r) を掛ける(独自の類推)
  !   穴(円・長方形。下端 z_o): 自由流出は開口の弦の幅の積分、潜り C A_w √(2g(H − h_D))、h_D が穴の下端を
  !     超えたら両者の小さい方(独自の組み立て)。円の積分は正規化した G(η) の表(η ≤ 4。η > 4 は展開)
  !   型 0: 水位調整板の堰、型 1(機能分離型): min(水位調整板の堰, 穴 + 流出量調整板の越流)、
  !   型 2(機能一体型): 穴 + 水位調整板の天端の越流
  ! ==========================================================================
  use, intrinsic :: iso_fortran_env, only : real64
  implicit none
  private
  public :: t_pddev, t_gtab
  public :: dev_q, weir_q, open_q, gfun, build_gtab
  public :: pi8

  real(real64), parameter :: pi8 = 3.14159265358979323846_real64

  !-------------------------------------------
  ! 落水口の装置(種類ごとに 1 つ。高さは田面から m)
  !-------------------------------------------
  type t_pddev
    integer :: kind = 0             ! 0: 水位調整板だけ, 1: 機能分離型, 2: 機能一体型
    real :: zb = 0.0, bb = 0.0      ! 水位調整板の天端の高さ・幅 (m)
    integer :: otype = 1            ! 穴の形 1: 円, 2: 長方形, 3: 三角(型 1・2 のみ)
    real :: od = 0.0                ! 円の径 (m)
    real :: ob = 0.0, oe = 0.0      ! 長方形の幅・高さ (m)
    real :: oang = 0.0              ! 三角の角度 (度)
    real :: oz = 0.0                ! 穴の下端(三角は頂点)の高さ (m)
    real :: zt = -1.0, bt = 0.0     ! 流出量調整板の天端の高さ・越流の幅(型 1。zt < 0 = 越流なし)
    real :: cw = 0.0, co = 0.0      ! 堰・穴の流量係数
    real :: zlow = 0.0              ! 流れ始める高さ (m)
    real :: kwb = 0.0, kwt = 0.0    ! 堰の係数 (2/3)C√(2g)B(水位調整板・流出量調整板)
    real :: ko = 0.0                ! 穴の自由流出の係数(円 C√(2g)d^2.5、長方形 (2/3)C√(2g)b、
                                    !   三角 (8/15)C tan(θ/2)√(2g))
    real :: kos = 0.0               ! 穴の潜りの係数 C√(2g)
  end type

  !-------------------------------------------
  ! 円の穴の正規化した積分 G(η) = ∫_0^min(η,1) 2√(u(1−u)) √(η − u) du の表(0 ≤ η ≤ etamax)
  !-------------------------------------------
  type t_gtab
    integer :: n = 0
    real :: deta = 0.0, etamax = 0.0
    real, allocatable :: v(:)       ! (0:n)
  end type


contains


!----------------------------------------------------------------------
! 落水口 1 か所の流量 (m3/s)。h: 田面からの湛水深、hd: 同じ基準の下流の水深(片方向: hd ≥ h なら 0)
!----------------------------------------------------------------------
pure real function dev_q(dev, gt, h, hd) result(q)
  type(t_pddev), intent(in) :: dev
  type(t_gtab), intent(in) :: gt
  real, intent(in) :: h, hd
  real :: qt
  q = 0.0
  if (h <= dev%zlow .or. hd >= h) return
  select case (dev%kind)
    case (0)
      q = weir_q(dev%kwb, dev%zb, h, hd)
    case (1)
      qt = 0.0
      if (dev%zt >= 0.0) qt = weir_q(dev%kwt, dev%zt, h, hd)
      q = min(weir_q(dev%kwb, dev%zb, h, hd), open_q(dev, gt, h, hd) + qt)
    case (2)
      q = open_q(dev, gt, h, hd) + weir_q(dev%kwb, dev%zb, h, hd)
  end select
end function


!----------------------------------------------------------------------
! 四角セキ(係数 k = (2/3)C√(2g)B、天端 z)。h2/h1 ≥ 2/3 で潜り(本間公式の形)
!----------------------------------------------------------------------
pure real function weir_q(k, z, h, hd) result(q)
  real, intent(in) :: k, z, h, hd
  real :: h1, h2
  q = 0.0
  h1 = h - z
  if (h1 <= 0.0) return
  h2 = max(hd - z, 0.0)
  if (h2 >= h1) return
  q = k * h1 * sqrt(h1)
  if (h2 > h1 * (2.0 / 3.0)) q = q * sub_ratio(h2 / h1)
end function


!----------------------------------------------------------------------
! 潜り越流と自由越流の比 S(r) = (3√3/2) r √(1 − r)(r = h2/h1 ≥ 2/3。r = 2/3 で 1、r = 1 で 0)
!----------------------------------------------------------------------
pure real function sub_ratio(r)
  real, intent(in) :: r
  sub_ratio = 1.5 * sqrt(3.0) * r * sqrt(max(1.0 - r, 0.0))
end function


!----------------------------------------------------------------------
! 穴(円・長方形・三角)の流量。自由流出は開口の積分、潜りは C A_w √(2g(H − h_D)) との小さい方
!----------------------------------------------------------------------
pure real function open_q(dev, gt, h, hd) result(q)
  type(t_pddev), intent(in) :: dev
  type(t_gtab), intent(in) :: gt
  real, intent(in) :: h, hd
  real :: hh, eta, qf, qs, h2
  q = 0.0
  hh = h - dev%oz
  if (hh <= 0.0) return
  select case (dev%otype)
    case (1)      ! 円
      eta = hh / dev%od
      qf = dev%ko * gfun(gt, eta)
      if (hd > dev%oz) then
        qs = dev%kos * dev%od**2 * seg_area(min(eta, 1.0)) * sqrt(h - hd)
        q = min(qf, qs)
      else
        q = qf
      end if
    case (2)      ! 長方形(幅 ob・高さ oe)
      qf = dev%ko * (hh * sqrt(hh) - max(hh - dev%oe, 0.0) * sqrt(max(hh - dev%oe, 0.0)))
      if (hd > dev%oz) then
        qs = dev%kos * dev%ob * min(hh, dev%oe) * sqrt(h - hd)
        q = min(qf, qs)
      else
        q = qf
      end if
    case (3)      ! 三角(V 字の切欠き。頂点 oz)
      q = dev%ko * hh * hh * sqrt(hh)
      h2 = max(hd - dev%oz, 0.0)
      if (h2 > hh * (2.0 / 3.0)) q = q * sub_ratio(h2 / hh)
  end select
end function


!----------------------------------------------------------------------
! 直径 1 の円の、下端から高さ t(0〜1)までの部分の面積 = ∫_0^t 2√(u(1−u)) du
!----------------------------------------------------------------------
pure real function seg_area(t)
  real, intent(in) :: t
  real :: tt
  tt = min(max(t, 0.0), 1.0)
  seg_area = 0.25 * acos(1.0 - 2.0 * tt) - (0.5 - tt) * sqrt(max(tt - tt * tt, 0.0))
end function


!----------------------------------------------------------------------
! G(η)(表の線形補間。η > etamax は (π/4)√s の展開、s = η − 1/2)
!----------------------------------------------------------------------
pure real function gfun(gt, eta)
  type(t_gtab), intent(in) :: gt
  real, intent(in) :: eta
  real :: x, w, sv, is2
  integer :: k
  if (eta >= gt%etamax) then
    sv = eta - 0.5
    is2 = 1.0 / (sv * sv)
    gfun = 0.25 * real(pi8) * sqrt(sv) * (1.0 - is2 * (1.0 / 128.0 + is2 * (20.0 / 65536.0 &
           + is2 * (140.0 / 4194304.0))))
  else
    x = max(eta, 0.0) / gt%deta
    k = min(int(x), gt%n - 1)
    w = x - real(k)
    gfun = (1.0 - w) * gt%v(k) + w * gt%v(k + 1)
  end if
end function


!----------------------------------------------------------------------
! G(η) の表を作る(全ランクが同じ演算で冗長に)。積分は u = (1 − cos θ)/2、θ = θm(1 − v²) で
! 両端の特異性を除いた滑らかな被積分関数を複合 Simpson(256 区間)で
!----------------------------------------------------------------------
subroutine build_gtab(gt)
  type(t_gtab), intent(inout) :: gt
  integer, parameter :: n = 8192
  integer :: k
  gt%n = n
  gt%etamax = 4.0
  gt%deta = gt%etamax / real(n)
  allocate(gt%v(0:n))
  do k = 0, n
    gt%v(k) = real(gquad(real(k, real64) * real(gt%deta, real64)))
  end do
end subroutine


real(real64) function gquad(eta)
  real(real64), intent(in) :: eta
  integer, parameter :: m = 256
  integer :: i
  real(real64) :: um, tm, v, th, u, f, w, sm
  gquad = 0.0_real64
  if (eta <= 0.0_real64) return
  um = min(eta, 1.0_real64)
  tm = acos(1.0_real64 - 2.0_real64 * um)
  sm = 0.0_real64
  do i = 0, m
    v = real(i, real64) / real(m, real64)
    th = tm * (1.0_real64 - v * v)
    u = 0.5_real64 * (1.0_real64 - cos(th))
    f = 0.5_real64 * sin(th)**2 * sqrt(max(eta - u, 0.0_real64)) * 2.0_real64 * tm * v
    if (i == 0 .or. i == m) then
      w = 1.0_real64
    else if (mod(i, 2) == 1) then
      w = 4.0_real64
    else
      w = 2.0_real64
    end if
    sm = sm + w * f
  end do
  gquad = sm / (3.0_real64 * real(m, real64))
end function

end module
