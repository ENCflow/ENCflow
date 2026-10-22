!======================================================================
! m_geomorph の submodule: 波浪による沿岸漂砂(f_wave_long。fn_wave)
!   設計は docs/wave_plan.md 案 A、決定は developer.md §84.15。
!   沖の波(有義波高 H0・周期 T・進行方向 φ0。固定値または時系列)を与件とし、
!   砕波帯のセル(湿潤で h <= h_b/γ)で局所の汀線方位を平滑化した水深の勾配から
!   取り、沖波で書いた CERC 式(Ashton & Murray 2006 式 (2))
!     Q_s = K2 H0^{12/5} T^{1/5} cos^{6/5}(α) sin(α)   [m3/s かさ]
!   (α = 波の進行方向と岸向き法線のなす角)を単位岸沖幅の流束 q = Q_s/W_b
!   (W_b = max(h_b/S, Δx)。S = 局所の海底勾配)に直し、岸平行の流束ベクトル
!   q⃗ = q t̂ を両セル平均で 8 方向のエッジへ射影して掃流砂と同じエッジ流束
!   (gm%wrk%q → apply_edge_flux: 供給量制限・dzmax・保存則)に乗せる。
!   波は解かない: 伝播・屈折・砕波は「岸平行等深線」の仮定で沖波の式に内包。
!
!   露出度(遮蔽の簡易扱い): 砕波帯より深い湿潤セル(h > h_b/γ)を源とし、波の
!   風上(進行方向の逆)の 8 近傍から Jacobi 更新で 1 更新 1 セルずつ伝える
!   (乾いたセルで途切れる)。デルタの陰・入り江・河道の内部に波が入らない。
!   Jacobi(前回値から更新 + ハロ交換)なので掃引順に依らずランク数不変。
!   回折は扱わない。
!
!   規則(掃流砂 §84.2 と同じ): 供給側が乾いていれば運ばない(R1)、受け手の
!   地盤が供給側の水面以上なら運ばない(R2 = 土砂は水面より上へ登らない。
!   乾いた浜の後退は安息角崩落が担う)、堤防エッジは遮断、河道幅の係数は水と同じ。
!   定着の τ*c は効かせない(砕波帯は常時湿潤で a = 0)。
!
!   河口の規則(wave_vmax ≥ 0 で有効): 流速 |V| > wave_vmax のセルは波の源にも砕波帯にも
!   しない(露出度は 0 = 陰)。河川の流下水深が h_b を超える河道が源になって波が河道を
!   遡り、河道内の砂州に沿岸漂砂が働いて発散するのを防ぐ。しきい値は河川の流下流速と
!   汀線帯の流速の間(利用者が直接与える。§84.15)。自セルの vv だけ読む = ハロ不要。
!
!   時計(wave_clock): 時系列の時刻は 1 = 地形時間(s%t × morfac。波候。既定)、
!   0 = 水理時間(嵐の継続時間を水理時間で与える)。流束は dts(地形時間)で適用。
!
!   MPI: 平滑化・流束ベクトル・露出度は自帯 js..je で計算してハロ交換(3+1 回)、
!   エッジ流束は calc_repose と同じ 2 ループ(書き手一意、je+1 行の冗長計算)。
!   collective なし。状態なし(与件と地形から毎回作る = save/restore 不要)。
!   近傍参照の範囲: 平滑化は h を ±wave_smooth(≤ ハロ幅 2)読むので呼び出し側が
!   h のハロを最新化する(ステップ頭の交換は ±1 行しか現ステップの値でない)。
!   全域の端は別問題: g%x の余白は 1 行、sw・h は余白なし(jsh = max(1, ·))なので、
!   核・風上参照・中央差分の 3 箇所は 1..nx, 1..ny を明示的に判定する(§84.15。
!   範囲外読みは未定義値 = 逐次と MPI で不一致になった実バグ)。
!   無効時は配列未確保・呼び出しなし(ゼロコスト)。
!======================================================================
submodule(m_geomorph) m_geomorph_wave
  use m_parallel, only : par_info, par_warn, par_stop, dcp, par_halo_cell
  use m_swflow_enc, only : chn
  use m_util, only : rtoa, itoa
  implicit none
  real, parameter :: deg = acos(-1.0) / 180.0

contains

!----------------------------------------------------------------------
module subroutine init_wave(gm, p, g, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_wave), intent(in) :: list
  integer :: k, n

  if (g%initialized) continue  ! 引数未使用の警告を抑制
  ! --- 与件(固定値または時系列)---
  n = 0
  do k = 1, ubound(list%wave_val, 2)
    if (list%wave_val(1,k) < 0.0) exit        ! 時刻列の番兵(-9999)で終端
    n = k
  end do
  if (n > 0) then
    allocate(gm%wav%val(1:4, 1:n))
    gm%wav%val(1, 1:n) = list%wave_val(1, 1:n) * 60.0    ! 分 → 秒
    gm%wav%val(2:4, 1:n) = list%wave_val(2:4, 1:n)
    do k = 1, n
      if (gm%wav%val(2,k) < 0.0) call par_stop("list_wave: wave_val H0 must be >= 0")
      if (gm%wav%val(2,k) > 0.0 .and. gm%wav%val(3,k) <= 0.0) then
        call par_stop("list_wave: wave_val T must be > 0 when H0 > 0")
      end if
      if (k > 1) then
        if (gm%wav%val(1,k) < gm%wav%val(1,k-1)) call par_stop("list_wave: wave_val times must be non-decreasing")
      end if
    end do
    call par_info("geomorph: wave series with " // itoa(n) // " entries")
  else
    if (list%wave_h0 <= 0.0) call par_stop("list_wave: wave_h0 must be > 0 (or give a wave_val series)")
    if (list%wave_t <= 0.0) call par_stop("list_wave: wave_t must be > 0")
    gm%wav%h0 = list%wave_h0
    gm%wav%tp = list%wave_t
    gm%wav%dir = list%wave_dir
  end if
  if (list%wave_clock < 0 .or. list%wave_clock > 1) call par_stop("list_wave: wave_clock must be 0 or 1")
  gm%wav%clock = list%wave_clock
  if (list%wave_k2 <= 0.0) call par_stop("list_wave: wave_k2 must be > 0")
  gm%wav%k2 = list%wave_k2
  if (list%wave_gamma <= 0.0 .or. list%wave_gamma > 1.0) call par_stop("list_wave: wave_gamma must be in (0,1]")
  gm%wav%gamma = list%wave_gamma
  if (list%wave_smooth < 1 .or. list%wave_smooth > 2) then
    call par_stop("list_wave: wave_smooth must be 1 or 2 (inside the halo width)")
  end if
  gm%wav%smooth = list%wave_smooth
  if (list%wave_smin <= 0.0) call par_stop("list_wave: wave_smin must be > 0")
  gm%wav%smin = list%wave_smin
  gm%wav%vmax = list%wave_vmax                            ! 負 = 無効(比較しない)
  if (gm%wav%vmax >= 0.0) then
    call par_info("geomorph: wave river-mouth rule on (cells with |V| > " // rtoa(gm%wav%vmax) &
                  // " m/s are neither a wave source nor surf zone)")
  end if

  ! --- 作業配列(有効時のみ確保 = 無効時ゼロコスト)---
  allocate(gm%wav%hs(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%wav%qx(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%wav%qy(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%wav%ex(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%wav%ex2(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)

  if (allocated(gm%wav%val)) then
    call par_info("geomorph: wave-driven longshore transport on (K2 = " // rtoa(gm%wav%k2) &
                  // ", gamma = " // rtoa(gm%wav%gamma) // ", clock = " // itoa(gm%wav%clock) // ")")
  else
    call par_info("geomorph: wave-driven longshore transport on (H0 = " // rtoa(gm%wav%h0) &
                  // " m, T = " // rtoa(gm%wav%tp) // " s, dir = " // rtoa(gm%wav%dir) &
                  // " deg, K2 = " // rtoa(gm%wav%k2) // ", gamma = " // rtoa(gm%wav%gamma) // ")")
  end if
end subroutine


!----------------------------------------------------------------------
! 時系列の現在値(線形補間。範囲外は端値)
!----------------------------------------------------------------------
subroutine eval_series(gm, tw)
  type(t_geomorph), intent(inout) :: gm
  real, intent(in) :: tw
  integer :: n, k
  real :: f
  n = ubound(gm%wav%val, 2)
  if (tw <= gm%wav%val(1,1)) then
    gm%wav%h0 = gm%wav%val(2,1); gm%wav%tp = gm%wav%val(3,1); gm%wav%dir = gm%wav%val(4,1)
    return
  end if
  if (tw >= gm%wav%val(1,n)) then
    gm%wav%h0 = gm%wav%val(2,n); gm%wav%tp = gm%wav%val(3,n); gm%wav%dir = gm%wav%val(4,n)
    return
  end if
  do k = 2, n
    if (tw < gm%wav%val(1,k)) then
      f = (tw - gm%wav%val(1,k-1)) / max(gm%wav%val(1,k) - gm%wav%val(1,k-1), tiny(1.0))
      gm%wav%h0 = gm%wav%val(2,k-1) + f * (gm%wav%val(2,k) - gm%wav%val(2,k-1))
      gm%wav%tp = gm%wav%val(3,k-1) + f * (gm%wav%val(3,k) - gm%wav%val(3,k-1))
      gm%wav%dir = gm%wav%val(4,k-1) + f * (gm%wav%val(4,k) - gm%wav%val(4,k-1))
      return
    end if
  end do
end subroutine


!----------------------------------------------------------------------
! 沿岸漂砂のエッジ流束(calc_fluvial の後、calc_repose の前。z・sd・h のハロは
! 呼び出し側が最新化済み)
!----------------------------------------------------------------------
module subroutine calc_wave_longshore(gm, p, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt, a, b, r, ui, uj, nact, im, ip, jm, jp
  real :: tw, hb, hbd, dx, dy, dxv, dyv, wsum, sig2, w, hh, vmax
  logical :: usev
  real :: gx, gy, sl, nx, ny, tx, ty, cosa, sina, qs, wb, q
  real :: qe, gq, vlong
  logical :: okc, okbank

  ! --- 与件の現在値 ---
  if (allocated(gm%wav%val)) then
    tw = s%t
    if (gm%wav%clock == 1) tw = s%t * gm%morfac
    call eval_series(gm, tw)
  end if
  if (gm%wav%h0 <= 0.0 .or. gm%wav%tp <= 0.0) return     ! 凪: 何もしない
  ! 砕波波高(Komar & Gaughan 1972)と砕波水深
  hb = 0.39 * p%gg**0.2 * (gm%wav%tp * gm%wav%h0**2)**0.4
  hbd = hb / gm%wav%gamma
  gm%wav%hbd = hbd
  vmax = gm%wav%vmax
  usev = (vmax >= 0.0)                                   ! 河口の規則(wave_vmax。自セルの vv のみ参照)
  ! 進行方向の単位ベクトル(格子の i, j 成分。j は南向き正なので y 成分は −sin)
  dxv = cos(gm%wav%dir * deg)
  dyv = -sin(gm%wav%dir * deg)
  gm%wav%dvec(1) = dxv
  gm%wav%dvec(2) = dyv
  dx = g%dx
  dy = g%dy

  ! --- 露出度(Jacobi。風上 = 進行方向の逆を 8 方向に量子化)---
  ui = nint(-dxv / max(abs(dxv), abs(dyv)))
  uj = nint(-dyv / max(abs(dxv), abs(dyv)))
  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      gm%wav%ex2(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) <= p%dd) cycle
      if (usev) then
        if (s%vv(i,j) > vmax) cycle                ! 河口の規則: 河川流のセルは源にならず陰(0)
      end if
      if (s%h(i,j) > hbd) then
        gm%wav%ex2(i,j) = 1.0                      ! 砕波帯より深い = 源
      else if (i+ui < 1 .or. i+ui > g%nx .or. j+uj < 1 .or. j+uj > g%ny) then
        gm%wav%ex2(i,j) = 1.0                      ! 風上が全域の外 = 開境界の沖(露出)
      else
        gm%wav%ex2(i,j) = gm%wav%ex(i+ui, j+uj)    ! 風上の前回値(ハロ込み。域外 x<=0 は 0 = 陰)
      end if
    end do
  end do
  !$omp end parallel do
  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      gm%wav%ex(i,j) = gm%wav%ex2(i,j)
    end do
  end do
  !$omp end parallel do
  call par_halo_cell(gm%wav%ex)

  ! --- 平滑化した水深(ガウス核。乾いたセル・域外は深さ 0 = 陸)---
  r = gm%wav%smooth
  sig2 = 0.5 * r
  wsum = 0.0
  do b = -r, r
    do a = -r, r
      wsum = wsum + exp(-(a * a + b * b) / (2.0 * sig2))
    end do
  end do
  !$omp parallel do schedule(static) private(i, j, a, b, w, hh)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      gm%wav%hs(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      hh = 0.0
      do b = -r, r
        if (j+b < 1 .or. j+b > g%ny) cycle          ! 全域の外(x の余白は 1 行、sw・h は余白なし)
        do a = -r, r
          if (i+a < 1 .or. i+a > g%nx) cycle
          if (g%x(i+a, j+b) <= 0) cycle
          if (g%sw(i+a, j+b) > 0) cycle
          if (s%h(i+a, j+b) <= p%dd) cycle
          w = exp(-(a * a + b * b) / (2.0 * sig2))
          hh = hh + w * s%h(i+a, j+b)
        end do
      end do
      gm%wav%hs(i,j) = hh / wsum
    end do
  end do
  !$omp end parallel do
  call par_halo_cell(gm%wav%hs)

  ! --- 砕波帯セルの流束ベクトル ---
  nact = 0
  !$omp parallel do schedule(static) reduction(+: nact) &
  !$omp   private(i, j, im, ip, jm, jp, gx, gy, sl, nx, ny, tx, ty, cosa, sina, qs, wb, q)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      gm%wav%qx(i,j) = 0.0
      gm%wav%qy(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) <= p%dd .or. s%h(i,j) > hbd) cycle
      if (gm%wav%ex(i,j) < 0.5) cycle                   ! 陰・入り江・河道の内部
      if (usev) then
        if (s%vv(i,j) > vmax) cycle                     ! 河口の規則: 河川流のセルは砕波帯にしない
      end if
      im = max(i - 1, 1); ip = min(i + 1, g%nx)      ! 全域端は片側差分
      jm = max(j - 1, 1); jp = min(j + 1, g%ny)
      gx = (gm%wav%hs(ip,j) - gm%wav%hs(im,j)) / (real(ip - im) * dx)
      gy = (gm%wav%hs(i,jp) - gm%wav%hs(i,jm)) / (real(jp - jm) * dy)
      sl = sqrt(gx * gx + gy * gy)
      if (sl < gm%wav%smin) cycle                       ! 平坦 = 汀線方位が定義できない
      nx = gx / sl                                       ! 岸沖法線(沖向き = 深くなる向き)
      ny = gy / sl
      tx = -ny                                           ! 岸平行(法線を +90° 回す)
      ty = nx
      cosa = -(dxv * nx + dyv * ny)                      ! 岸向きの入射成分
      if (cosa <= 0.0) cycle                             ! 岸から離れる波 = 陰
      sina = dxv * tx + dyv * ty                         ! 岸平行成分(符号 = 漂砂の向き)
      qs = gm%wav%k2 * gm%wav%h0**2.4 * gm%wav%tp**0.2 * cosa**1.2 * sina   ! m3/s かさ
      wb = max(hbd / sl, dx)                             ! 砕波帯の幅
      q = qs / wb / gm%poroi                             ! 単位岸沖幅の固体流束 (m2/s)
      gm%wav%qx(i,j) = q * tx
      gm%wav%qy(i,j) = q * ty
      nact = nact + 1
    end do
  end do
  !$omp end parallel do
  gm%wav%nact = gm%wav%nact + nact
  call par_halo_cell(gm%wav%qx)
  call par_halo_cell(gm%wav%qy)

  ! --- エッジ流束(書き手一意。calc_repose と同じ 2 ループ)---
  vlong = 0.0
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) reduction(+: vlong) &
  !$omp   private(i, j, k, in, jn, okc, okbank, qe, gq)
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
            okbank = .true.
            if (g%bank_active) okbank = ((g%rw(i,j) > 0) .eqv. (g%rw(in,jn) > 0))
            if (okbank) then
              qe = 0.5 * (gm%wav%qx(i,j) + gm%wav%qx(in,jn)) * gm%flv%ex(k) &
                 + 0.5 * (gm%wav%qy(i,j) + gm%wav%qy(in,jn)) * gm%flv%ey(k)
              gq = qe * gm%flv%wl(k)
              ! 掃流砂と同じ規則(§84.2 R1・R2)
              if (gq > 0.0) then
                if (s%h(i,j) <= p%dd .or. s%z(in,jn) >= s%z(i,j) + s%h(i,j)) gq = 0.0
              else if (gq < 0.0) then
                if (s%h(in,jn) <= p%dd .or. s%z(i,j) >= s%z(in,jn) + s%h(in,jn)) gq = 0.0
              end if
              if (gq /= 0.0) then
                if (chn%have_frw) gq = gq * chn%frw(k, i+die(k), j+dje(k))
                if (chn%have_fwd) gq = gq * chn%fwd(k, i+die(k), j+dje(k))
                if (j <= dcp%je) vlong = vlong + abs(gq) * dts
              end if
            end if
          end if
        end if
        gm%wrk%q(k, i+die(k), j+dje(k)) = gq
      end do
      ! 域外(x<=0)に向く面スロットは 0
      do k = 5, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) gm%wrk%q(ke(k), i+die(k), j+dje(k)) = 0.0
      end do
    end do
  end do
  !$omp end parallel do
  gm%wav%vlong = gm%wav%vlong + vlong

  call apply_edge_flux(gm, g, s, dts)
end subroutine


!----------------------------------------------------------------------
module subroutine dispose_wave(gm)
  type(t_geomorph), intent(inout) :: gm
  call par_warn("geomorph: wave-driven longshore transport moved " // rtoa(gm%wav%vlong) &
                // " m3 (solid) through edges over " // itoa(gm%wav%nact) // " surf-zone cell-updates")
end subroutine

end submodule
