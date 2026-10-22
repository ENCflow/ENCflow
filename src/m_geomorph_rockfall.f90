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
!   崖錐に支えられた面(rf_fface >= 0。窓版が前提。崖錐律速の後退):
!     (a) 支えられた面: 安息角より急な落差の先(脚部)が崖錐 ht >= h_min(または崩落中の
!         柱)に覆われたセル(sup = 1)。eval_splash はそのセルの E を rf_fface 倍にする
!         (前回更新のフラグ。1 更新の遅れ)。脚部が覆われている間、面は削れない(0 なら)。
!     (b) 柱の崩落: 窓版の規則(超過分を削って H_w を H_c まで下げる = 縁が段々に
!         丸まる)に代えて、面の頂(上に H_c より高い段がないセル)で H_w > H_c なら
!         その柱を崩落中(col = 1)にし、低い隣接と同じ高さになるまで落とす(excess =
!         落差そのもの。1 エッジ・1 更新の移動は tanφ_t·dist/32 まで = 受け手の崖錐が
!         捌ける量)。崩落中の柱を脚にする隣接は始まらないので、面は垂直のまま 1 柱ずつ
!         後退し、落ちた柱の岩盤は崖錐の上端の高さの棚として埋もれる。安息角より急な
!         落差が無くなった柱は終わる(フラグを外す)。フラグは更新をまたぐ状態なので
!         私有 save に含める(ht の後ろ。face のみ)。
!     脚部の崖錐が厚くなると H_w <= H_c で崩落が止まり、崖錐が乾式侵食(rf_ftalus)で
!     除かれて H_w が戻ると再開する(定常では 後退速度 × 崖高 ≈ 崖錐の除去率 × 崖錐幅)。
!   海セル(sw > 0)への崩落: 供給側が陸、受け手が海セルのエッジも対象にする
!   (海セルが供給側になることはない)。apply_edge_flux は海セルの z を更新しない
!   ので、落下分は系外へ出る(海食崖の崩落 = 崖錐が波で除去される極限。乾式侵食の
!   「splash exported」と同型)。排出量は台帳 vsea に積んで dispose で報告する。
!   窓版の最低点には海セルの z(海底)も入る(海底が深いと自由面の高さに水面下の
!   分が加わる。海面を自由面の下端にしたいなら海セルの z を海面に置く)。
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
  ! 崖錐に支えられた面(rf_fface >= 0。窓版が前提)
  gm%rf%face = (list%rf_fface >= 0.0)
  if (gm%rf%face) then
    if (gm%rf%npass <= 0) call par_stop("list_geomorph: rf_fface >= 0 requires rf_rc > 0 (window)")
    gm%rf%fface = list%rf_fface
    allocate(gm%rf%col(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(gm%rf%colt(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)
    allocate(gm%rf%sup(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    call par_info("geomorph: rockfall talus-supported faces on (face erodibility x" // rtoa(gm%rf%fface) &
                  // "; column collapse at the top of the face)")
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
! 支えられた面のフラグ sup(0/1): 安息角より急な落差の先(脚部)が崖錐 ht >= h_min に
!   覆われた(または崩落中の柱である)陸セル。calc_rockfall の末尾(と restore)で更新し、次の更新の eval_splash
!   が読む(1 更新の遅れ)。判定は全ランク同一 = ハロ交換は collective 安全
!----------------------------------------------------------------------
subroutine face_support(gm, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: i, j, k, in, jn

  !$omp parallel do schedule(static) private(i, j, k, in, jn)
  do j = dcp%js, dcp%je
    gm%rf%sup(:, j) = 0.0
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (in < 1 .or. in > g%nx) cycle
        if (g%x(in,jn) <= 0) cycle
        ! 脚部 = 崖錐に覆われたセル、または崩落中の柱(通過中の岩屑)
        if (s%ht(in,jn) < gm%rf%hmin .and. gm%rf%col(in,jn) < 0.5) cycle
        if (s%z(i,j) - s%z(in,jn) > gm%rf%tanphi * gm%rf%dist(ke(k))) then
          gm%rf%sup(i,j) = 1.0
          exit
        end if
      end do
    end do
  end do
  !$omp end parallel do
  call par_halo_cell(gm%rf%sup)
end subroutine


!----------------------------------------------------------------------
! 崩落中の柱のフラグ col(0/1)の更新(calc_rockfall の冒頭。z・ht・zmin は時刻 n):
!   継続: 崩落中の柱は、安息角より急な落差がまだあれば続け、なければ終わる。
!   開始: 面の頂(上に H_c より高い段がない陸セル。乾式侵食で丸まった肩も含む)で、
!         窓内落差 H_w > H_c、かつ安息角より急な落差の先に崩落中でないセルがあるもの
!         (前回のフラグで判定 = 評価順に依存しない。崩落中の柱を脚にする柱は待つ =
!         面は 1 柱ずつ後退し、柱の連鎖で斜路にならない)。
!   判定は全ランク同一 = ハロ交換は collective 安全
!----------------------------------------------------------------------
subroutine face_start(gm, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: i, j, k, in, jn
  real :: dz, lim
  logical :: steep, top, foot

  !$omp parallel do schedule(static) private(i, j, k, in, jn, dz, lim, steep, top, foot)
  do j = dcp%js, dcp%je
    gm%rf%colt(:, j) = 0.0
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%sd(i,j) <= 0.0) cycle
      steep = .false.
      top = .true.
      foot = .false.
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (in < 1 .or. in > g%nx) cycle
        if (g%x(in,jn) <= 0) cycle
        dz = s%z(i,j) - s%z(in,jn)
        lim = gm%rf%tanphi * gm%rf%dist(ke(k))
        if (dz > lim) then
          steep = .true.
          if (gm%rf%col(in,jn) < 0.5) foot = .true.
        else if (-dz > gm%rf%hc) then
          top = .false.                           ! H_c より高い段の脚(埋もれた棚)は始めない
        end if
      end do
      if (gm%rf%col(i,j) > 0.5) then
        if (steep) gm%rf%colt(i,j) = 1.0      ! 安息角以内に収まったら終わる
      else if (top .and. foot) then
        if (s%z(i,j) - gm%rf%zmin(i,j) > gm%rf%hc) gm%rf%colt(i,j) = 1.0
      end if
    end do
  end do
  !$omp end parallel do
  gm%rf%col(:, dcp%js:dcp%je) = gm%rf%colt(:, dcp%js:dcp%je)
  call par_halo_cell(gm%rf%col)
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
  real :: gq, dzc, drop, lim, exc, exct, dzm, vmove, vsea, qfac, hfac, hw
  real :: qk, fd, dvi, dvo, winv
  logical :: okc, window, okn, tosea, ok

  window = (gm%rf%npass > 0)
  if (window) call window_min(gm, g, s)
  if (gm%rf%face) call face_start(gm, g, s)
  nrock = 0
  ntal = 0
  nclip = 0
  vmove = 0.0
  vsea = 0.0
  ! 高さ差 → 固体流量の換算: 1 更新・1 エッジで relax·excess/2/8 の高さ
  qfac = gm%rf%relax * 0.5 / 8.0 * gm%rf%area / (dts * gm%poroi)
  hfac = gm%rf%relax * 0.5 / 8.0                 ! excess → 1 エッジの移動高さ
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) reduction(+: nrock, ntal, nclip, vmove, vsea) &
  !$omp   private(i, j, k, in, jn, id, jd, okc, okn, tosea, ok, gq, dzc, drop, lim, exc, exct, dzm, hw)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        gq = 0.0                                   ! 必ず上書き(書き手の契約)
        if (g%x(in,jn) > 0) then
          okn = (g%sw(in,jn) <= 0)
          ! 陸どうし、または供給側(高い側)が陸で受け手が海セル(海セルが供給側に
          ! なることはない)
          dzc = s%z(i,j) - s%z(in,jn)
          if (dzc > 0.0) then
            id = i; jd = j
            ok = okc
          else
            id = in; jd = jn
            ok = okn
          end if
          tosea = ok .and. .not. (okc .and. okn)
          if (ok) then
            drop = abs(dzc)
            ! 高い側(供給側)が非侵食(sd <= 0)なら動かない(§84.14 と同じ扱い)
            if (drop > 0.0 .and. s%sd(id,jd) > 0.0) then
              exc = 0.0
              lim = gm%rf%tanphi * gm%rf%dist(k)
              if (gm%rf%face) then
                ! (1'') 柱の崩落(支え方式): 崩落中の柱(face_start)は、低い隣接のどれとも
                !       同じ高さになるまで落ちる(落差そのもの。最も低い隣接の高さ = 崖錐の
                !       上端の下まで)。1 エッジ・1 更新の移動高さは tanφ_t·dist/32 まで =
                !       受け手(崖錐の上端)が安息角で捌ける量に抑え、受け手の上に一時的な
                !       山ができて柱の残りが高止まりする(岩盤の斜路が残る)のを防ぐ
                if (gm%rf%col(id,jd) > 0.5) then
                  exc = min(drop, lim / (32.0 * hfac))
                  nrock = nrock + 1
                end if
              else if (window) then
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
                if (j <= dcp%je) then
                  vmove = vmove + dzm * gm%rf%area
                  if (tosea) vsea = vsea + dzm * gm%rf%area
                end if
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
  gm%rf%vsea = gm%rf%vsea + vsea

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
  if (gm%rf%face) call face_support(gm, g, s)
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
  if (gm%rf%vsea > 0.0) then
    call par_warn("geomorph: rockfall exported to sea cells = " // rtoa(gm%rf%vsea) // " m3 (bulk)")
  end if
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
  if (gm%rf%face) call restart_write_cell(un, gm%rf%col)   ! 崩落中の柱(支え方式のみ)
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
  if (gm%rf%face) call restart_read_cell(un, gm%rf%col)
  if (is_root) close(un)
  call par_halo_cell(s%ht)
  ! 支え方式: 崩落中の柱は save から、支えられた面のフラグは状態(z, ht)から再構成する
  ! (連続計算と同じ 1 更新遅れの値)
  if (gm%rf%face) then
    call par_halo_cell(gm%rf%col)
    call face_support(gm, g, s)
  end if
end subroutine

end submodule
