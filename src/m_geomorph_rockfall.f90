!======================================================================
! m_geomorph の submodule: 崩落と崖錐(f_rockfall。§48.7)
!
!   キャップロックのメサ・ビュートの崖は、軟層の掘り込みでキャップが崩落し、
!   落下した岩屑が崖の脚部に崖錐として積もり、崖錐が軟層を保護することで
!   垂直な自由面を保ったまま後退する。ラスタ(セルごとに 1 つの z)では
!   オーバーハングを表せないので、次の 3 つで近似する:
!     (1) 崩落: 隣接セル間の高さ差(自由面の高さ)|z_c − z_n| が限界高さ H_c
!         (rf_hc)を超えた分 excess について、1 更新に relax·excess/2/8 の
!         高さを高い側から低い側へ移す(安息角崩落 calc_repose と同じ数値形。
!         8 方向同時でも合計は relax·excess_max/2 以下 = 行き過ぎなし)。
!         窓の半径 r_c(rf_rc)> 0 なら、自由面の高さは「nint(r_c/Δx) セルの
!         正方形窓内の最低点との落差 H_w」で測り(3×3 の min フィルタをハロ交換
!         しながら反復 = MPI 安全。Δx に依らない限界高さ)、崖錐の安息角より急な
!         エッジで H_w > H_c の超過分(そのエッジの安息角超過を上限)を移す。
!         崖が何セルにもまたがる細かい格子でも、面全体が崩落の対象になる。
!     (2) 崖錐: 低い側に移った体積は崖錐の厚さ ht(s%ht。出力 Ht)として積む。
!         崖錐に覆われたセル(ht > 0)が供給側のエッジは安息角 φ_t(rf_phi)
!         を超えた分も動く(1 エッジの移動高さは ht/8 まで = 崖錐の分だけ)。
!         移動先はやはり崖錐になる(ht の収支は z と同じ流量から求める)。
!     (3) 保護: 崖錐に覆われたセル(ht > 0)の乾式侵食 f_splash を rf_ftalus 倍
!         (> 0)に抑え、剥離分だけ ht を先に減らす(eval_splash / apply_splash)。
!         落下した岩屑は着地セルを覆うとみなす(部分被覆の線形則は、緩和形の崩落が
!         運ぶ薄い到着分が被覆厚に届く前に削られて崖錐が積もらないため採らない)。
!         rf_ftalus > 0 なので微量の崖錐は消耗して消え、永久の不侵食にはならない。
!         崖錐の安息角での移動は h_min(rf_hmin)以上の厚さだけ(微量の散らばり防止)。
!   崖錐の除去速度(rf_ftalus × 乾式侵食)が崖の後退速度を律する(崖錐に
!   律速される後退 = 実際のメサの崖)。崩落の規模は H_c で、崖錐の勾配は
!   φ_t で与える。
!
!   流量は calc_repose と同じく独自の 2 ループで wrk%q に書き(全成分上書き、
!   x<=0 の近傍へ向く面スロットも 0)、apply_edge_flux(供給量制限 → 発散 →
!   z・sd の共動更新)で適用する。ht の収支は apply の発散と同じ式(風上の
!   fdon を乗じたエッジ流量)で求め、流出は ht から(0 でクランプ)、流入は
!   ht へ積む。1 エッジ・1 更新の変動は fluv_dzmax で頭打ち(流量段階 =
!   保存則を保つ)。状態 ht は帯±ハロ(更新は自帯、末尾で par_halo_cell)。
!   私有 save geomorph_rockfall.dat(契約 5。m_restart の restart_write_cell。§83)。
!   無効時は配列未確保・呼び出しなし(ゼロコスト)。
!======================================================================
submodule(m_geomorph) m_geomorph_rockfall
  use m_parallel, only : par_info, par_warn, par_stop, dcp, is_root, par_halo_cell
  use m_swflow_enc, only : chn
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : itoa, rtoa
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_rockfall(gm, p, g, s, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_geomorph), intent(in) :: list
  real :: phi
  real, parameter :: deg = acos(-1.0) / 180.0

  ! 限界高さは構造的な量(岩体の強度)で既定を置かない
  if (list%rf_hc <= 0.0) then
    call par_stop("list_geomorph: f_rockfall=1 requires rf_hc > 0 (critical free-face height, m)")
  end if
  gm%rf%hc = list%rf_hc
  ! 崖錐の安息角の既定 35°(岩屑の崖錐 30〜40° の中央)
  phi = gm_param("rf_phi", list%rf_phi, 35.0, " deg")
  if (phi <= 0.0 .or. phi >= 90.0) call par_stop("list_geomorph: rf_phi must be in (0,90) deg")
  gm%rf%tanphi = tan(phi * deg)
  if (list%rf_relax <= 0.0 .or. list%rf_relax > 1.0) call par_stop("list_geomorph: rf_relax must be in (0,1]")
  gm%rf%relax = list%rf_relax
  ! 崖錐の侵食性の倍率(既定 0.3)。0 は許さない: 微量の崖錐が乗ったセルが永久に
  ! 不侵食になり、崖錐の再移動で散らばった微量が斜面全体を止める(試行で検出)
  if (list%rf_ftalus < 0.0) call par_stop("list_geomorph: rf_ftalus must be >= 0 (0 = default 0.3)")
  gm%rf%ftalus = gm_param("rf_ftalus", list%rf_ftalus, 0.3, "")
  ! 崖錐が動く最小厚さの既定 0.01 m(これより薄い崖錐はその場に留まる)
  gm%rf%hmin = gm_param("rf_hmin", list%rf_hmin, 0.01, " m")
  ! 自由面の高さの窓(0 = 隣接セル間の段差 = 従来)
  if (list%rf_rc < 0.0) call par_stop("list_geomorph: rf_rc must be >= 0")
  gm%rf%npass = 0
  if (list%rf_rc > 0.0) then
    gm%rf%npass = max(1, nint(list%rf_rc / min(g%dx, g%dy)))
    allocate(gm%rf%zmin(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(gm%rf%zt(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)
    call par_info("geomorph: rockfall free-face height over a window of " // itoa(gm%rf%npass) &
                  // " cells (rf_rc = " // rtoa(list%rf_rc) // " m)")
  end if
  ! fluvial・repose なしでも動けるように dzmax・共有スクラッチ・供給量制限係数を整える
  if (gm%dzmax <= 0.0) then
    if (list%fluv_dzmax <= 0.0) call par_stop("list_geomorph: fluv_dzmax must be > 0")
    gm%dzmax = list%fluv_dzmax
  end if
  call require_work(gm, g)
  if (.not. allocated(gm%flv%fdon)) then
    allocate(gm%flv%fdon(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 1.0)
  end if
  gm%rf%dist(1) = sqrt(g%dx**2 + g%dy**2)
  gm%rf%dist(2) = g%dy
  gm%rf%dist(3) = gm%rf%dist(1)
  gm%rf%dist(4) = g%dx
  gm%rf%area = g%dx * g%dy
  call par_info("geomorph: rockfall on (H_c = " // rtoa(list%rf_hc) // " m, talus phi = " // rtoa(phi) &
                // " deg, relax = " // rtoa(list%rf_relax) // ", talus erodibility x" // rtoa(gm%rf%ftalus) // ")")

  ! --- 状態(有効時のみ確保 = 無効時ゼロコスト) ---
  if (.not. allocated(s%ht)) allocate(s%ht(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (p%f_state_restore > 0) call restore_rockfall(gm, p, g, s)
end subroutine


!----------------------------------------------------------------------
! 窓内の最低標高(npass 回の 3×3 min フィルタ。各パスの後にハロ交換 = パス数は
!   namelist 由来の静的量で全ランク同一 = collective 安全。無効な近傍は飛ばす)
!----------------------------------------------------------------------
subroutine window_min(gm, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: i, j, k, in, jn, n
  real :: zm

  gm%rf%zmin(:, dcp%jsh:dcp%jeh) = s%z(:, dcp%jsh:dcp%jeh)
  do n = 1, gm%rf%npass
    !$omp parallel do schedule(static) private(i, j, k, in, jn, zm)
    do j = dcp%js, dcp%je
      gm%rf%zt(:, j) = gm%rf%zmin(:, j)
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        zm = gm%rf%zmin(i,j)
        do k = 1, 8
          in = i + din(k)
          jn = j + djn(k)
          if (in < 1 .or. in > g%nx) cycle
          if (g%x(in,jn) <= 0) cycle
          zm = min(zm, gm%rf%zmin(in,jn))
        end do
        gm%rf%zt(i,j) = zm
      end do
    end do
    !$omp end parallel do
    gm%rf%zmin(:, dcp%js:dcp%je) = gm%rf%zt(:, dcp%js:dcp%je)
    call par_halo_cell(gm%rf%zmin)
  end do
end subroutine


!----------------------------------------------------------------------
! 崩落と崖錐の移動(独立の 2 ループ。z・sd・ht のハロは呼び出し側が最新化済み)
!----------------------------------------------------------------------
module subroutine calc_rockfall(gm, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt, id, jd, nrock, ntal, nclip
  real :: gq, dzc, drop, lim, exc, exct, dzm, vmove, qfac, hfac, hw
  real :: qk, fd, dvi, dvo, winv
  logical :: okc, window

  window = (gm%rf%npass > 0)
  if (window) call window_min(gm, g, s)
  nrock = 0
  ntal = 0
  nclip = 0
  vmove = 0.0
  ! 高さ差 → 固体流量の換算: 1 更新・1 エッジで relax·excess/2/8 の高さ
  qfac = gm%rf%relax * 0.5 / 8.0 * gm%rf%area / (dts * gm%poroi)
  hfac = gm%rf%relax * 0.5 / 8.0                 ! excess → 1 エッジの移動高さ
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) reduction(+: nrock, ntal, nclip, vmove) &
  !$omp   private(i, j, k, in, jn, id, jd, okc, gq, dzc, drop, lim, exc, exct, dzm, hw)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        gq = 0.0                                   ! 必ず上書き(書き手の契約)
        if (okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            dzc = s%z(i,j) - s%z(in,jn)
            drop = abs(dzc)
            if (dzc > 0.0) then
              id = i; jd = j
            else
              id = in; jd = jn
            end if
            ! 高い側(供給側)が非侵食(sd <= 0)なら動かない(§84.14 と同じ扱い)
            if (drop > 0.0 .and. s%sd(id,jd) > 0.0) then
              exc = 0.0
              lim = gm%rf%tanphi * gm%rf%dist(k)
              if (window) then
                ! (1') 崩落(窓): 供給側の窓内最低点との落差 H_w が限界 H_c を超え、かつこの
                !      エッジが崖錐の安息角より急なら、超過分(安息角超過を上限)
                if (drop > lim) then
                  hw = s%z(id,jd) - gm%rf%zmin(id,jd)
                  if (hw > gm%rf%hc) then
                    exc = min(hw - gm%rf%hc, drop - lim)
                    nrock = nrock + 1
                  end if
                end if
              else
                ! (1) 崩落: 隣接セル間の段差(自由面の高さ)が限界 H_c を超えた分
                if (drop > gm%rf%hc) then
                  exc = drop - gm%rf%hc
                  nrock = nrock + 1
                end if
              end if
              ! (2) 崖錐の安息角: 供給側に h_min 以上の崖錐があれば tanφ_t·dist を超えた分
              !     (1 エッジの移動高さは崖錐の厚さの 1/8 まで = 崖錐の分だけ動く)
              if (s%ht(id,jd) >= gm%rf%hmin) then
                if (drop > lim) then
                  exct = min(drop - lim, s%ht(id,jd) / (8.0 * hfac))
                  if (exct > exc) then
                    exc = exct
                    ntal = ntal + 1
                  end if
                end if
              end if
              if (exc > 0.0) then
                gq = sign(qfac * exc, dzc)         ! 高い側 → 低い側(c→n 正)
                dzm = hfac * exc
                if (dzm > gm%dzmax) then
                  gq = gq * (gm%dzmax / dzm)
                  dzm = gm%dzmax
                  nclip = nclip + 1
                end if
                if (j <= dcp%je) vmove = vmove + dzm * gm%rf%area
              end if
            end if
          end if
        end if
        gm%wrk%q(k, i+die(k), j+dje(k)) = gq
      end do
      ! 域外(x<=0)に向く面スロットは 0(fluvial の開境界書き込みの残りを消す)
      do k = 5, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) gm%wrk%q(ke(k), i+die(k), j+dje(k)) = 0.0
      end do
    end do
  end do
  !$omp end parallel do
  gm%rf%nrock = gm%rf%nrock + nrock
  gm%rf%ntal = gm%rf%ntal + ntal
  gm%rf%nclip = gm%rf%nclip + nclip
  gm%rf%vmove = gm%rf%vmove + vmove

  call apply_edge_flux(gm, g, s, dts)

  ! --- 崖錐の収支: 発散と同じ式(風上の fdon を乗じたエッジ流量)で流出・流入を
  !     分けて集計し、流出は ht から(0 でクランプ)、流入は ht へ積む ---
  !$omp parallel do schedule(static) private(i, j, k, in, jn, qk, fd, dvi, dvo, winv)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      dvi = 0.0
      dvo = 0.0
      do k = 1, 8
        qk = gm%wrk%q(ke(k), i+die(k), j+dje(k))
        fd = 1.0
        if (sign_e(k) * qk > 0.0) then
          fd = gm%flv%fdon(i,j)
          dvo = dvo + sign_e(k) * (qk * fd)
        else if (sign_e(k) * qk < 0.0) then
          in = i + din(k)
          jn = j + djn(k)
          if (g%x(in,jn) > 0) fd = gm%flv%fdon(in,jn)
          dvi = dvi - sign_e(k) * (qk * fd)
        end if
      end do
      if (dvi > 0.0 .or. dvo > 0.0) then
        winv = 1.0
        if (chn%have_width) winv = 1.0 / chn%wfrac(i,j)
        s%ht(i,j) = max(s%ht(i,j) - dvo * dts * gm%wrk%ainv * winv * gm%poroi, 0.0) &
                    + dvi * dts * gm%wrk%ainv * winv * gm%poroi
      end if
    end do
  end do
  !$omp end parallel do
  call par_halo_cell(s%ht)
end subroutine


!----------------------------------------------------------------------
module subroutine dispose_rockfall(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (p%f_state_save > 0) call save_rockfall(gm, p, g, s)
  ! ランク局所の台帳
  call par_warn("geomorph: rockfall moved " // rtoa(gm%rf%vmove) // " m3 (bulk) over " &
                // itoa(gm%rf%nrock) // " free-face edge-updates and " // itoa(gm%rf%ntal) &
                // " talus edge-updates (dzmax clip " // itoa(gm%rf%nclip) // ")")
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル geomorph_rockfall.dat。契約5。§7)
!----------------------------------------------------------------------
subroutine save_rockfall(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: un
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (gm%enabled) continue
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/geomorph_rockfall.dat', form='unformatted', &
         status='replace')
  end if
  call restart_write_cell(un, s%ht)
  if (is_root) close(un)
end subroutine


subroutine restore_rockfall(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  character(:), allocatable :: fname
  logical :: found
  integer :: un
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (gm%enabled) continue

  fname = trim(p%dir_save)//'/geomorph_rockfall.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("geomorph: rockfall state file not found (was f_rockfall enabled when saving): " &
                  // fname)
  end if
  if (is_root) open(newunit=un, file=fname, form='unformatted', status='old')
  call restart_read_cell(un, s%ht)
  if (is_root) close(un)
  call par_halo_cell(s%ht)
end subroutine

end submodule
