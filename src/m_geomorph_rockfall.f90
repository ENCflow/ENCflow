!======================================================================
! m_geomorph の submodule: 岩盤の崩落(f_rockfall。developer.md §87、
!   docs/karst_plan.md §2.6)
!
!   安息角崩落 f_repose(土層 sd を隣へ移す保存形)の岩盤版。基岩面
!   zb = z − sd が隣接セルの地表 z_w より tanφ_rock × 距離を超えて高い
!   セルは、超過分の一部を岩 → 岩屑として隣へ落とす:
!     v_k = relax · (zb_n − z_w − tanφ·dist_k) / (1 + bulk) / 8   (方向 k ごと)
!     供給側 n: z −= Σ v_k(sd 不変 = 基岩面が下がり、上の土層は載ったまま)
!     受け手 w: z += bulk·v、sd += bulk·v(岩屑はかさ比 bulk で土層になる)
!   1 更新 1 スイープ。緩和率 relax と /(1+bulk)/8 で 1 更新あたりの変化は
!   超過高さの relax 倍以下(両側の変化の和で段差が縮む)。1 セル 1 更新の
!   総崩落量は dzmax(fluv_dzmax 共用)で頭打ち(流量段階 = 保存則は保つ)。
!   岩の体積は保存(受け手の岩屑体積 = bulk × 岩)。海セルは供給側にも
!   受け手にもならない。
!
!   2 パス(owner-compute):
!     (1) 先頭で z・sd のハロを交換し、自帯の各セルが 8 方向の崩落量 qr(:,:,k)
!         を時刻 n の z・sd から作る(近傍は読むだけ)
!     (2) qr の 8 面のハロを交換し、各セルが自分の流出 Σ_k qr(i,j,k) と
!         近傍からの流入 Σ_k qr(i+d_k, j+d_k, 9−k)(= 近傍の自分向き成分)を
!         まとめて適用する。順序固定 = ランク数不変
!   無効時は配列未確保・呼び出しなし(ゼロコスト)。リスタート状態なし。
!======================================================================
submodule(m_geomorph) m_geomorph_rockfall
  use m_parallel, only : par_info, par_stop, dcp, par_halo_cell
  use m_util, only : rtoa
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_rockfall(gm, g, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_list_geomorph), intent(in) :: list
  real, parameter :: deg = acos(-1.0) / 180.0
  real :: phi, bulk

  ! 既定 60°(裸の石灰岩壁の安定勾配の代表。岩盤の内部摩擦角 35〜45° に
  ! 粘着を加味した概算。§62)
  phi = gm_param("rockfall_phi", list%rockfall_phi, 60.0, " deg")
  if (phi <= 0.0 .or. phi >= 90.0) call par_stop("list_geomorph: rockfall_phi must be in (0,90) deg")
  if (list%rockfall_relax <= 0.0 .or. list%rockfall_relax > 1.0) then
    call par_stop("list_geomorph: rockfall_relax must be in (0,1]")
  end if
  ! 既定のかさ比 = 1/(1 − λ)(河床の空隙率と同じ扱い。岩屑を土層として運ぶ
  ! 掃流・クリープと整合)
  bulk = gm_param("rockfall_bulk", list%rockfall_bulk, gm%poroi, "")
  if (bulk < 1.0) call par_stop("list_geomorph: rockfall_bulk must be >= 1")
  gm%rck%tanphi = tan(phi * deg)
  gm%rck%relax = list%rockfall_relax
  gm%rck%bulk = bulk
  ! fluvial なしでも動けるように dzmax を確保する(init_bank と同じ)
  if (gm%dzmax <= 0.0) then
    if (list%fluv_dzmax <= 0.0) call par_stop("list_geomorph: fluv_dzmax must be > 0")
    gm%dzmax = list%fluv_dzmax
  end if
  gm%rck%dist(1) = sqrt(g%dx**2 + g%dy**2)
  gm%rck%dist(2) = g%dy
  gm%rck%dist(3) = gm%rck%dist(1)
  gm%rck%dist(4) = g%dx
  gm%rck%dist(5) = g%dx
  gm%rck%dist(6) = gm%rck%dist(1)
  gm%rck%dist(7) = g%dy
  gm%rck%dist(8) = gm%rck%dist(1)
  allocate(gm%rck%qr(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:8), source = 0.0)
  call par_info("geomorph: rockfall on (phi_rock = " // rtoa(phi) // " deg, relax = " &
                // rtoa(gm%rck%relax) // ", bulk = " // rtoa(gm%rck%bulk) // ", dzmax = " &
                // rtoa(gm%dzmax) // " m)")
end subroutine


!----------------------------------------------------------------------
module subroutine calc_rockfall(gm, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, k, in, jn, nfall, nclip
  real :: zb, dzc, v, vtot, fac, vin, vrock

  call par_halo_cell(s%z)
  call par_halo_cell(s%sd)
  gm%rck%qr(:,:,:) = 0.0
  fac = gm%rck%relax / (1.0 + gm%rck%bulk) / 8.0

  ! (1) 方向別の崩落量(自帯のみ書く。近傍の z は読むだけ)
  nclip = 0
  !$omp parallel do schedule(static) reduction(+: nclip) private(i, j, k, in, jn, zb, dzc, v, vtot)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      zb = s%z(i,j) - s%sd(i,j)
      vtot = 0.0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (in < dcp%ish .or. in > dcp%ieh .or. jn < dcp%jsh .or. jn > dcp%jeh) cycle
        if (g%x(in,jn) <= 0) cycle
        if (g%sw(in,jn) > 0) cycle
        dzc = zb - s%z(in,jn) - gm%rck%tanphi * gm%rck%dist(k)
        if (dzc > 0.0) then
          v = fac * dzc
          gm%rck%qr(i,j,k) = v
          vtot = vtot + v
        end if
      end do
      if (vtot > gm%dzmax) then
        gm%rck%qr(i,j,1:8) = gm%rck%qr(i,j,1:8) * (gm%dzmax / vtot)
        nclip = nclip + 1
      end if
    end do
  end do
  !$omp end parallel do
  gm%rck%nclip = gm%rck%nclip + nclip

  ! (2) 流出と流入をまとめて適用(近傍の qr はハロ込みで読むだけ)
  do k = 1, 8
    call par_halo_cell(gm%rck%qr(:,:,k))
  end do
  nfall = 0
  vrock = 0.0
  !$omp parallel do schedule(static) reduction(+: nfall, vrock) private(i, j, k, in, jn, vtot, vin)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      vtot = 0.0
      vin = 0.0
      do k = 1, 8
        vtot = vtot + gm%rck%qr(i,j,k)
        in = i + din(k)
        jn = j + djn(k)
        if (in < dcp%ish .or. in > dcp%ieh .or. jn < dcp%jsh .or. jn > dcp%jeh) cycle
        vin = vin + gm%rck%qr(in,jn,9-k)        ! 近傍 n の「自分向き」成分
      end do
      if (vtot > 0.0) then
        nfall = nfall + 1
        vrock = vrock + vtot
      end if
      s%z(i,j) = s%z(i,j) - vtot + gm%rck%bulk * vin
      s%sd(i,j) = s%sd(i,j) + gm%rck%bulk * vin
    end do
  end do
  !$omp end parallel do
  gm%rck%nfall = gm%rck%nfall + nfall
  gm%rck%vrock = gm%rck%vrock + vrock * g%dx * g%dy
end subroutine

end submodule
