!======================================================================
! m_geomorph の submodule: 斜面クリープ(f_creep)
!   親モジュールの型・定数(din/djn 等)・共有作業領域(crp/wrk)・
!   require_work にはホスト結合でアクセスする(単段参照。§13)。
!   dcp 等の実行コンテキストは submodule 側で直接 use する(§13)
!   creep_hstar > 0 では深さ依存クリープ(calc_creep_soil。§89.8)
!======================================================================
submodule(m_geomorph) m_geomorph_creep
  use m_parallel, only : par_info, par_stop, dcp, par_allreduce_max
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_creep(gm, p, g)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real :: dts, dt_lim, smax
  character(len=256) :: msg

  dts = p%dt * gm%idt_geomorph * gm%morfac
  if (gm%crp%diag > 0.0) then
    ! 8 近傍の 9 点(creep_diagratio = d > 0。§93): 軸エッジと斜めエッジの伝導度と、
    ! 壁で塞がれた斜めの配分を軸エッジへ振り替えた表を作る
    call init_creep_diag(gm, g, smax)
    ! 陽解法の安定条件(正値性 = 最大値原理): 自セルの係数 1 − D dts Σ_k cw_k / A >= 0。
    ! Σ_k cw_k は振り替え後の表のセルごとの和の全域の最大(allreduce。全ランク同一)。
    ! d = 0 の 5 点では下の式と同じ値になる
    dt_lim = 1.0 / (gm%creep_d * smax / (g%dx * g%dy))
    write(msg,'(a,f6.4,a)') "geomorph: creep on the 8-neighbour 9-point stencil (creep_diagratio = ", &
                            gm%crp%diag, ")"
    call par_info(trim(msg))
  else
    ! エッジ伝導度重み = 通過幅 / セル中心間距離(4近傍のみ)
    gm%crp%cw(1) = 0.0             ! 斜め(未使用)
    gm%crp%cw(2) = g%dx / g%dy     ! 法線 y 方向(通過幅 dx、距離 dy)
    gm%crp%cw(3) = 0.0             ! 斜め(未使用)
    gm%crp%cw(4) = g%dy / g%dx     ! 法線 x 方向(通過幅 dy、距離 dx)

    ! 陽解法(FTCS)の安定条件の静的検査: D*dts*(1/dx^2+1/dy^2) <= 1/2。
    ! D・格子・dts がすべて namelist 由来の静的量なので init で確定できる
    ! (判定は全ランク同一 → par_stop の collective 条件を満たす)
    dt_lim = 0.5 / (gm%creep_d * (1.0 / g%dx**2 + 1.0 / g%dy**2))
  end if
  write(msg,'(a,es10.3,a,es10.3,a)') "geomorph: creep stability dt limit = ", dt_lim, &
                                     " s (dts = ", dts, " s)"
  call par_info(trim(msg))
  if (dts > dt_lim) then
    call par_stop("list_geomorph: creep dts exceeds the explicit stability limit " &
                  // "(reduce dt_geomorph/morfac/creep_d)")
  end if

  call require_work(gm, g)
end subroutine


!----------------------------------------------------------------------
module subroutine calc_creep(gm, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt
  real :: gq, dv
  logical :: okc, use_tab

  use_tab = allocated(gm%crp%cwo)
  ! 深さ依存クリープ(creep_hstar > 0。§89.8)は別経路(従来の線形拡散のループは不変)
  if (gm%crp%hcinv > 0.0) then
    call calc_creep_soil(gm, g, s, dts)
    return
  end if

  ! --- ループ1: エッジ流量(各成分の書き手は一意なので競合しない) ---
  !   帯界面のエッジ成分 k=1..3(行 je)はハロ行 je+1 の書き手が担う
  !   (冗長計算。全域端では行が存在せず対象外)
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) private(i, j, k, in, jn, okc, gq)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        ! z は毎回変わるため、条件を満たさない場合も必ず 0 を代入する
        gq = 0.0
        if (gm%crp%cw(k) > 0.0 .and. okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            ! エッジ流量(書き手 c から k 近傍 n に向かい正)。d > 0 の 9 点は振り替え込みの
            ! 表の伝導度(§93)
            if (use_tab) then
              gq = gm%creep_d * (s%z(i,j) - s%z(in,jn)) * gm%crp%cwo(k, i+die(k), j+dje(k))
            else
              gq = gm%creep_d * (s%z(i,j) - s%z(in,jn)) * gm%crp%cw(k)
            end if
          end if
        end if
        gm%wrk%q(k, i+die(k), j+dje(k)) = gq
      end do
      ! 域外(x <= 0)の近傍に向く面スロット(k >= 5 は域外セルの所有成分)を 0 で上書きする
      ! (クリープは領域の外へ運ばない = 四周は壁)。共有スクラッチには先行の掃流砂が開境界の
      ! 流出を書いており、上書きしないとループ 2 がそれを再び集計して境界セルを掘り下げて
      ! いた(2026-10-27 実検出。§19.10。apply_edge_flux の書き手の契約と同じ)
      do k = 5, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) gm%wrk%q(ke(k), i+die(k), j+dje(k)) = 0.0
      end do
    end do
  end do
  !$omp end parallel do

  ! --- ループ2: 発散を取り z を更新 ---
  !   マスク・斜め成分のエッジは 0 が入っているため無条件に8近傍を
  !   集計できる(流出の総和が正)
  !$omp parallel do schedule(static) private(i, j, k, dv)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      dv = 0.0
      do k = 1, 8
        dv = dv + sign_e(k) * gm%wrk%q(ke(k), i+die(k), j+dje(k))
      end do
      s%z(i,j) = s%z(i,j) - dv * dts * gm%wrk%ainv
    end do
  end do
  !$omp end parallel do

end subroutine



!----------------------------------------------------------------------
! 深さ依存クリープ(creep_hstar > 0。§89.8。docs/mountain_stream_plan.md §5.1)
!   q = −D (1 − e^{−H_up/H_c}) ∇z(H_up は供給側 = 高い側のセルの土層厚 sd)。
!   Landlab の DepthDependentDiffuser の q = K H* (1 − e^{−H/H*}) S(Johnstone & Hilley
!   2015)と同じ形で、厚い土層の極限で従来の q = −D ∇z(D = creep_d = K H*)。土層だけが
!   動く(裸岩は動かない)ので、流量をかさ体積から固体体積に換算して共有の
!   apply_edge_flux に渡す(供給量制限・z と sd の共動更新・細粒分の帳簿・地下水容量の
!   整合を共有)。実効の拡散係数は D 以下なので init_creep の安定条件はそのまま成り立つ。
!   近傍の z・sd を読む(ハロは m_geomorph_calc の前回の末尾の交換で、先行のプロセスが
!   あればクリープの直前の交換で最新)
!----------------------------------------------------------------------
subroutine calc_creep_soil(gm, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt
  real :: gq
  logical :: okc, use_tab

  use_tab = allocated(gm%crp%cwo)
  ! --- エッジ流量(固体体積。各成分の書き手は一意。帯界面のエッジは行 je+1 の書き手が担う) ---
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) private(i, j, k, in, jn, okc, gq)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        gq = 0.0
        if (gm%crp%cw(k) > 0.0 .and. okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            ! かさ体積の流量(書き手 c から k 近傍 n に向かい正)に、供給側の土層の
            ! 利用可能率を掛けて固体体積に換算(apply_edge_flux が poroi を掛け戻す)。
            ! d > 0 の 9 点は振り替え込みの表の伝導度(§93)
            if (use_tab) then
              gq = gm%creep_d * (s%z(i,j) - s%z(in,jn)) * gm%crp%cwo(k, i+die(k), j+dje(k))
            else
              gq = gm%creep_d * (s%z(i,j) - s%z(in,jn)) * gm%crp%cw(k)
            end if
            if (gq > 0.0) then
              gq = gq * rock_avail(s%sd(i,j), gm%crp%hcinv) / gm%poroi
            else
              gq = gq * rock_avail(s%sd(in,jn), gm%crp%hcinv) / gm%poroi
            end if
          end if
        end if
        gm%wrk%q(k, i+die(k), j+dje(k)) = gq
      end do
      ! 域外の近傍に向く面スロットは 0(apply_edge_flux の書き手の契約。§19.10)
      do k = 5, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) gm%wrk%q(ke(k), i+die(k), j+dje(k)) = 0.0
      end do
    end do
  end do
  !$omp end parallel do

  ! --- 供給量制限 → 発散 → z と sd の共動更新(掃流砂と共有の適用経路) ---
  call apply_edge_flux(gm, g, s, dts)
end subroutine


!----------------------------------------------------------------------
! 8 近傍の 9 点の伝導度と振り替えの表(creep_diagratio = d > 0。§93)
!   通過幅の配分は m_swflow_enc の init_weights・m_gwflow_lateral_geom_init と同じ規則
!   (短い辺に d、長い辺は (Δmin/Δmax)² 倍。軸 lp、斜め ld の面長に対する割合)。伝導度 =
!   通過幅 / 中心間距離で、内部では任意の d・Δx ≠ Δy で f_xx・f_yy の係数が厳密に 1 の
!   整合な 9 点ラプラシアンになる(developer.md §20・§16.6)。
!   壁(領域外 x <= 0・海セル sw > 0。クリープの無流束境界)に接するセルでは、塞がれた
!   斜めの配分を同じ界面を横切る軸エッジへ振り替える(m_gwflow_lateral の build_opening・
!   §16.6 の f_gw_opening と同じ規則): 軸エッジの通過幅 = (lp + nb·ld)·面長、nb は界面を
!   横切る斜め 4 本(c 側 2 本・n 側 2 本)のうち塞がれた本数 × 0.5。振り替えないと壁沿いの
!   行の壁に平行な拡散係数が内部の 1 − d/2 倍(1 セル幅の帯で 1 − d 倍)になる。
!   マスクだけで決まる静的な表なので init で作る(ゾーン 2 の全域マスク。書き手ループと同じ
!   範囲 js..je+1・同じ格納規約)。smax はセルごとの伝導度の和(8 方向)の全域の最大
!----------------------------------------------------------------------
subroutine init_creep_diag(gm, g, smax)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  real, intent(out) :: smax
  integer :: i, j, k, in, jn, jt
  real :: d, lpx, lpy, ldx, ldy, dr, wd, nb, ss
  real :: w1(1)

  d = gm%crp%diag
  dr = sqrt(g%dx**2 + g%dy**2)
  if (g%dy > g%dx) then
    lpy = 1 - (g%dx / g%dy)**2 * d
    ldy = d / 2 * (g%dx / g%dy)**2
    lpx = 1 - d
    ldx = d / 2
  else
    lpy = 1 - d
    ldy = d / 2
    lpx = 1 - (g%dy / g%dx)**2 * d
    ldx = d / 2 * (g%dy / g%dx)**2
  end if
  wd = sqrt((ldy * g%dy)**2 + (ldx * g%dx)**2)    ! 斜めの通過幅 (m)
  gm%crp%cw(1) = wd / dr                          ! 斜め
  gm%crp%cw(2) = lpx * g%dx / g%dy                ! 法線 y 方向(通過幅 lpx·dx、距離 dy)
  gm%crp%cw(3) = wd / dr                          ! 斜め
  gm%crp%cw(4) = lpy * g%dy / g%dx                ! 法線 x 方向(通過幅 lpy·dy、距離 dx)

  allocate(gm%crp%cwo(1:4, dcp%ish-1:dcp%ieh, dcp%jsh-1:dcp%jeh), source = 0.0)
  jt = min(dcp%je + 1, dcp%jeh)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (crp_blocked(i, j)) cycle
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        if (crp_blocked(in, jn)) cycle
        select case (k)
        case (2)
          ! 北の軸エッジ(c → (i, j−1)): 界面を横切る斜めは c の北西・北東と n の南西・南東
          nb = 0.5 * real(count([crp_blocked(i-1, j-1), crp_blocked(i+1, j-1), &
                                 crp_blocked(i-1, j), crp_blocked(i+1, j)]))
          gm%crp%cwo(k, i+die(k), j+dje(k)) = (lpx + nb * ldx) * g%dx / g%dy
        case (4)
          ! 西の軸エッジ(c → (i−1, j)): 界面を横切る斜めは c の北西・南西と n の北東・南東
          nb = 0.5 * real(count([crp_blocked(i-1, j-1), crp_blocked(i-1, j+1), &
                                 crp_blocked(i, j-1), crp_blocked(i, j+1)]))
          gm%crp%cwo(k, i+die(k), j+dje(k)) = (lpy + nb * ldy) * g%dy / g%dx
        case default
          gm%crp%cwo(k, i+die(k), j+dje(k)) = gm%crp%cw(k)    ! 斜めは不変
        end select
      end do
    end do
  end do

  ! セルごとの伝導度の和(8 方向。ループ 2 と同じ集計)の最大
  smax = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (crp_blocked(i, j)) cycle
      ss = 0.0
      do k = 1, 8
        ss = ss + gm%crp%cwo(ke(k), i+die(k), j+dje(k))
      end do
      smax = max(smax, ss)
    end do
  end do
  w1(1) = smax
  call par_allreduce_max(w1)
  smax = max(w1(1), tiny(1.0))

contains

  ! クリープの無流束セル(領域外 x <= 0 か海セル sw > 0)。sw は全域(1:nx, 1:ny)なので
  ! x > 0 のときだけ読む(x は 0:nx+1 の枠つき。m_gwflow_lateral の lat_blocked と同じ)
  pure logical function crp_blocked(ii, jj)
    integer, intent(in) :: ii, jj
    crp_blocked = .true.
    if (g%x(ii,jj) > 0) crp_blocked = (g%sw(ii,jj) > 0)
  end function
end subroutine


!----------------------------------------------------------------------
! エッジ流量スクラッチの確保(プロセス間で共有。最初の要求者が確保)
!   j 範囲はセル j を挟むエッジが j-1 と j にあるため下限 jsh-1
!   (m_swflow_enc の uv/mn と同形)。確保時 0: マスク起因で書かれない
!   エッジは恒久 0(無フラックス)
!----------------------------------------------------------------------
module subroutine require_work(gm, g)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  if (allocated(gm%wrk%q)) return
  gm%wrk%ainv = 1.0 / (g%dx * g%dy)
  allocate(gm%wrk%q(1:4, dcp%ish-1:dcp%ieh, dcp%jsh-1:dcp%jeh), source = 0.0)
end subroutine

end submodule
