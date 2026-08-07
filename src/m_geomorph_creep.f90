!======================================================================
! m_geomorph の submodule: 斜面クリープ(f_creep)
!   親モジュールの型・定数(din/djn 等)・共有作業領域(crp/wrk)・
!   require_work にはホスト結合でアクセスする(単段参照。§13)。
!   dcp 等の実行コンテキストは submodule 側で直接 use する(§13)
!======================================================================
submodule(m_geomorph) m_geomorph_creep
  use m_parallel, only : par_info, par_stop, dcp
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_creep(gm, p, g)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real :: dts, dt_lim
  character(len=256) :: msg

  ! エッジ伝導度重み = 通過幅 / セル中心間距離(4近傍のみ)
  crp%cw(1) = 0.0             ! 斜め(未使用)
  crp%cw(2) = g%dx / g%dy     ! 法線 y 方向(通過幅 dx、距離 dy)
  crp%cw(3) = 0.0             ! 斜め(未使用)
  crp%cw(4) = g%dy / g%dx     ! 法線 x 方向(通過幅 dy、距離 dx)

  ! 陽解法(FTCS)の安定条件の静的検査: D*dts*(1/dx^2+1/dy^2) <= 1/2。
  ! D・格子・dts がすべて namelist 由来の静的量なので init で確定できる
  ! (判定は全ランク同一 → par_stop の collective 条件を満たす)
  dts = p%dt * gm%idt_geomorph * gm%morfac
  dt_lim = 0.5 / (gm%creep_d * (1.0 / g%dx**2 + 1.0 / g%dy**2))
  write(msg,'(a,es10.3,a,es10.3,a)') "geomorph creep: dt limit = ", dt_lim, &
                                     " s (dts = ", dts, " s)"
  call par_info(trim(msg))
  if (dts > dt_lim) then
    call par_stop("geomorph creep: dts exceeds the explicit stability limit " &
                  // "(reduce dt_geomorph/morfac/creep_d)")
  end if

  call require_work(g)
end subroutine


!----------------------------------------------------------------------
module subroutine calc_creep(gm, g, s, dts)
  type(t_geomorph), intent(in) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt
  real :: gq, dv
  logical :: okc

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
        if (crp%cw(k) > 0.0 .and. okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            ! エッジ流量(書き手 c から k 近傍 n に向かい正)
            gq = gm%creep_d * (s%z(i,j) - s%z(in,jn)) * crp%cw(k)
          end if
        end if
        wrk%q(k, i+die(k), j+dje(k)) = gq
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
        dv = dv + sign_e(k) * wrk%q(ke(k), i+die(k), j+dje(k))
      end do
      s%z(i,j) = s%z(i,j) - dv * dts * wrk%ainv
    end do
  end do
  !$omp end parallel do

end subroutine



!----------------------------------------------------------------------
! エッジ流量スクラッチの確保(プロセス間で共有。最初の要求者が確保)
!   j 範囲はセル j を挟むエッジが j-1 と j にあるため下限 jsh-1
!   (m_swflow_enc の uv/mn と同形)。確保時 0: マスク起因で書かれない
!   エッジは恒久 0(無フラックス)
!----------------------------------------------------------------------
module subroutine require_work(g)
  type(t_geoinfo), intent(in) :: g
  if (allocated(wrk%q)) return
  wrk%ainv = 1.0 / (g%dx * g%dy)
  allocate(wrk%q(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
end subroutine

end submodule
