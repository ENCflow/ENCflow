!======================================================================
! m_geomorph の submodule: 乾式斜面侵食(f_splash。無流水の雨滴・
! サブグリッドリル侵食。developer.md §48)
!
!   表面流も地下水も存在しない高透水斜面(バッドランド・火砕丘の
!   海食崖など)で、雨滴の衝突とサブグリッドスケールのリル・転動
!   (DEM に表現されない微地形の集水)が谷を刻む過程の
!   パラメータ化。凹地形(谷)で侵食効率が増大する正のフィードバックが
!   核心で、「移流(表面流)なしの谷形成」を表す。
!
!   浸食レート(m/s。固体体積。P = 地表到達降雨強度 s%pre [m/s]):
!     E = P・[ spl_kr・(1 + spl_ca・κ) + spl_kt・(1 + spl_cb・κ)・S^spl_h ]
!       κ = max(∇²z, 0): 凹(谷)で正の曲率 (1/m)。5点ラプラシアン
!       S = |∇z|: 勾配の大きさ(中央差分)
!       第1項: 雨滴(スプラッシュ)侵食。S→0 の台地上でも生じる(加算)
!       第2項: サブグリッドリル・転動の集中。S→0 で消える(乗算構造)
!   適用範囲: 陸の乾燥セル(h <= dd)のみ = f_wash(湿潤セル)と相補で
!   二重計上しない。河道セル(rw > 0)は対象外(wash と同じ意味論)。
!   海セルの z は勾配・曲率の近傍としては読む(海食崖の縁がまさに対象)。
!
!   剥離土砂は**系外排出**(開いた系): hs に注入せず(無流水なので
!   移流できない)、体積を台帳 spl%vout に積んで dispose で報告する。
!   z と sd は共動更新(帯水層底 z − sd 不変)+ gwflow 容量引き渡しは
!   wash と同一規約。sd=0 で岩盤露出・停止(風化 f_wthr と収支が閉じる)。
!
!   2パス構造(MPI 規約): eval_splash が時刻 n の z(近傍参照)から
!   侵食深 spl%fx を評価し(debris の適用より前に呼ぶ=全プロセスが
!   時刻 n の z を見る)、apply_splash が局所適用する(debris の後)。
!   これにより帯界面でランク数に依存しない。
!
!   積み残し(§48。Phase 2: 風向依存の雨滴項 Φ_A(θ_wind)、
!   Phase 3: 容量式の堆積 D = max(0, ΣQs − Qc)/δ²(D8 経路))
!======================================================================
submodule(m_geomorph) m_geomorph_splash
  use m_parallel, only : par_stop, dcp
  implicit none

contains

!----------------------------------------------------------------------
! 乾式斜面侵食の初期化(検証・係数コピー・評価配列の確保)
!----------------------------------------------------------------------
module subroutine init_splash(gm, g, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_list_geomorph), intent(in) :: list

  if (list%spl_kr < 0.0) call par_stop("list_geomorph: spl_kr must be >= 0")
  if (list%spl_kt < 0.0) call par_stop("list_geomorph: spl_kt must be >= 0")
  if (list%spl_kr <= 0.0 .and. list%spl_kt <= 0.0) then
    call par_stop("list_geomorph: f_splash requires spl_kr > 0 or spl_kt > 0")
  end if
  if (list%spl_ca < 0.0) call par_stop("list_geomorph: spl_ca must be >= 0")
  if (list%spl_cb < 0.0) call par_stop("list_geomorph: spl_cb must be >= 0")
  if (list%spl_h <= 0.0) call par_stop("list_geomorph: spl_h must be > 0")
  if (list%spl_dzmax < 0.0) call par_stop("list_geomorph: spl_dzmax must be >= 0")

  gm%skr = list%spl_kr
  gm%sca = list%spl_ca
  gm%skt = list%spl_kt
  gm%scb = list%spl_cb
  gm%shexp = list%spl_h
  gm%sdzmax = list%spl_dzmax

  if (.not. allocated(spl%fx)) then
    allocate(spl%fx(1:g%nx, dcp%js:dcp%je), source = 0.0)
  end if
end subroutine


!----------------------------------------------------------------------
! 侵食深の評価(時刻 n の z から。書き込みは spl%fx のみ)
!   帯の全セルの fx を 0 を含めて必ず上書きする(wrk%q と同じ契約)。
!   近傍 z の読み: x 方向は配列範囲と x>0 を検査(範囲外・領域外は
!   自セル値で鏡像=寄与ゼロ)、y 方向はハロ行(常に確保済み)。
!   海セル(sw>0)の z は実地形として読む(海食崖の縁の勾配が対象)
!----------------------------------------------------------------------
module subroutine eval_splash(gm, p, g, s, dts)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, intent(in) :: dts       ! 実効時間刻み(morfac 込み)
  integer :: i, j, nclip
  real :: zc, ze, zw, zn, zs, kap, sx, sy, ss, er, fx
  real :: dxi, dyi, dx2i, dy2i

  dxi = 0.5 / g%dx
  dyi = 0.5 / g%dy
  dx2i = 1.0 / (g%dx * g%dx)
  dy2i = 1.0 / (g%dy * g%dy)
  nclip = 0

  !$omp parallel do schedule(static) reduction(+:nclip) &
  !$omp   private(i, j, zc, ze, zw, zn, zs, kap, sx, sy, ss, er, fx)
  do j = dcp%js, dcp%je
    spl%fx(:,j) = 0.0
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (g%rw(i,j) > 0) cycle          ! 河道セルは対象外(wash と同じ意味論)
      if (s%h(i,j) > p%dd) cycle        ! 湿潤セルは f_wash の管轄(相補)
      if (s%pre(i,j) <= 0.0) cycle      ! 侵食は降雨イベント駆動
      if (s%sd(i,j) <= 0.0) cycle       ! 岩盤露出セルは停止
      ! 近傍 z(範囲外・領域外は鏡像 = 寄与ゼロ)
      zc = s%z(i,j)
      ze = zc; zw = zc; zn = zc; zs = zc
      if (i < g%nx) then
        if (g%x(i+1,j) > 0) ze = s%z(i+1,j)
      end if
      if (i > 1) then
        if (g%x(i-1,j) > 0) zw = s%z(i-1,j)
      end if
      if (g%x(i,j+1) > 0) zn = s%z(i,j+1)
      if (g%x(i,j-1) > 0) zs = s%z(i,j-1)
      ! 曲率(凹で正)と勾配
      kap = max((ze + zw - 2.0 * zc) * dx2i + (zn + zs - 2.0 * zc) * dy2i, 0.0)
      sx = (ze - zw) * dxi
      sy = (zn - zs) * dyi
      ss = sqrt(sx * sx + sy * sy)
      ! 浸食レート(固体体積 m/s)
      er = gm%skr * (1.0 + gm%sca * kap)
      if (gm%skt > 0.0 .and. ss > 0.0) then
        er = er + gm%skt * (1.0 + gm%scb * kap) * ss**gm%shexp
      end if
      er = er * s%pre(i,j)
      if (er <= 0.0) cycle
      ! 河床変化量へ換算し、可動層(sd)と侵食上限でクランプ
      fx = er * dts * gm%poroi
      if (gm%sdzmax > 0.0 .and. fx > gm%sdzmax) then
        fx = gm%sdzmax
        nclip = nclip + 1
      end if
      fx = min(fx, s%sd(i,j))
      spl%fx(i,j) = fx
    end do
  end do
  !$omp end parallel do
  spl%nclip = spl%nclip + nclip
end subroutine


!----------------------------------------------------------------------
! 侵食の適用(局所。z・sd の共動更新+系外排出台帳+gwflow 引き渡し)
!   排出体積の集計は行別部分和 → 逐次総和(スレッド数によらず決定的)
!----------------------------------------------------------------------
module subroutine apply_splash(gm, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: fx, cap, fxg
  real :: rsum(dcp%js:dcp%je)

  !$omp parallel do schedule(static) private(i, j, fx, cap, fxg)
  do j = dcp%js, dcp%je
    rsum(j) = 0.0
    do i = g%wx(1,j), g%wx(2,j)
      fx = spl%fx(i,j)
      if (fx <= 0.0) cycle
      ! 共動更新(z と sd が同じ Δz で動く → 帯水層底 z − sd 不変)
      s%z(i,j) = s%z(i,j) - fx
      s%sd(i,j) = s%sd(i,j) - fx
      rsum(j) = rsum(j) + fx
      ! 浸食で地下水容量が現在の貯留を下回ったら、超過分を地表水へ渡す
      ! (calc_wash と同じ整合)
      if (s%gw_active) then
        cap = s%sd(i,j) * g%sy0
        if (s%hg(i,j) > cap) then
          fxg = s%hg(i,j) - cap
          s%hg(i,j) = cap
          s%h(i,j) = s%h(i,j) + fxg
        end if
      end if
    end do
  end do
  !$omp end parallel do

  ! 系外排出の台帳(固体体積 = 河床変化 × (1−λ) × セル面積)
  do j = dcp%js, dcp%je
    spl%vout = spl%vout + rsum(j) * g%dx * g%dy / gm%poroi
  end do
end subroutine

end submodule
