!======================================================================
! m_geomorph の submodule: 斜面クリープ(f_creep)
!   親モジュールの型・定数(din/djn 等)・共有作業領域(crp/wrk)・
!   require_work にはホスト結合でアクセスする(単段参照。§13)。
!   dcp 等の実行コンテキストは submodule 側で直接 use する(§13)
!   creep_hstar > 0 では深さ依存クリープ(calc_creep_soil。§88.8)
!======================================================================
submodule(m_geomorph) m_geomorph_creep
  use m_parallel, only : par_info, par_stop, dcp
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_creep(gm, p, g)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real :: dts, dt_lim
  character(len=256) :: msg

  ! エッジ伝導度重み = 通過幅 / セル中心間距離(4近傍のみ)
  gm%crp%cw(1) = 0.0             ! 斜め(未使用)
  gm%crp%cw(2) = g%dx / g%dy     ! 法線 y 方向(通過幅 dx、距離 dy)
  gm%crp%cw(3) = 0.0             ! 斜め(未使用)
  gm%crp%cw(4) = g%dy / g%dx     ! 法線 x 方向(通過幅 dy、距離 dx)

  ! 陽解法(FTCS)の安定条件の静的検査: D*dts*(1/dx^2+1/dy^2) <= 1/2。
  ! D・格子・dts がすべて namelist 由来の静的量なので init で確定できる
  ! (判定は全ランク同一 → par_stop の collective 条件を満たす)
  dts = p%dt * gm%idt_geomorph * gm%morfac
  dt_lim = 0.5 / (gm%creep_d * (1.0 / g%dx**2 + 1.0 / g%dy**2))
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
  logical :: okc

  ! 深さ依存クリープ(creep_hstar > 0。§88.8)は別経路(従来の線形拡散のループは不変)
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
            ! エッジ流量(書き手 c から k 近傍 n に向かい正)
            gq = gm%creep_d * (s%z(i,j) - s%z(in,jn)) * gm%crp%cw(k)
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
! 深さ依存クリープ(creep_hstar > 0。§88.8。docs/mountain_stream_plan.md §5.1)
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
  logical :: okc

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
            ! 利用可能率を掛けて固体体積に換算(apply_edge_flux が poroi を掛け戻す)
            gq = gm%creep_d * (s%z(i,j) - s%z(in,jn)) * gm%crp%cw(k)
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
