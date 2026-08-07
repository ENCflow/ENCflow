submodule(m_swflow_enc) m_swflow_enc_diff
  use m_state, only : t_state
  use m_parallel, only : dcp, par_info   ! 親経由のホスト結合は nvfortran バグ回避のため直接 use
  implicit none

  ! 拡散項の設計(developer.md §20)
  !   セル中心のラプラシアンは「2点勾配のエッジフラックスをセル面積で
  !   発散」する有限体積形で評価する:
  !     ∇²f|(i,j) ≒ (1/(dx·dy)) Σ_k l8(k)·(f_k − f_0)/w8dr(k)
  !   既存の通過幅 l8 と距離 w8dr の組は、任意の p_diagratio・dx≠dy で
  !   fxx, fyy の係数が厳密に 1、fxy と奇数次が 0 になる(整合な9点
  !   ラプラシアン。証明は §20)。全重み非負なので離散最大値原理も成立。
  !   勾配(get_diff)と違い swでの再正規化はしない: 欠けたエッジ=
  !   そのエッジの拡散フラックスがゼロ(no-flux 閉鎖)が物理的に正しい
  type t_enc_diff
    ! セル中心での拡散項(第1添字は1:2でx,y成分)
    real, allocatable :: td(:,:,:)
    ! 方向別係数 l8(k)/(w8dr(k)·dx·dy)(diff_init が設定)
    real :: wd8(1:8) = 0.0
  end type
  type(t_enc_diff) :: td_mod

contains
!----------------------------------------------------------------------
! 拡散項の内部場の確保と安定条件の検査
!----------------------------------------------------------------------
module subroutine diff_init(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  integer :: k
  real :: dt_lim
  character(len=256) :: msg

  if (f_diffusion_term <= 0) return
  allocate(td_mod%td(1:2,1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  forall(k=1:8) td_mod%wd8(k) = l8(k) / (w8dr(k) * g%dx * g%dy)

  ! 陽解法の安定条件の目安を検査する(Gershgorin による上界:
  ! dt ≦ 1/(ν·Σ_k wd8(k))。超えていても停止はしない=発散は momentum の
  ! 発散チェックが検出する)
  dt_lim = 1.0 / (p_diffusion_nu * sum(td_mod%wd8(1:8)))
  if (p%dt > dt_lim) then
    write(msg, '(a,g0.4,a,g0.4,a)') &
      "WARNING: 拡散項の安定条件を超過 dt=", p%dt, " > ", dt_lim, " (s)"
    call par_info(trim(msg))
  end if
end subroutine


!----------------------------------------------------------------------
! 拡散項の内部場を計算
!----------------------------------------------------------------------
module subroutine diff_prepare(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s

  integer :: i, j
  real :: lu, lv

  if (f_diffusion_term <= 0) return

  !$omp parallel do schedule(dynamic) private(i, j, lu, lv)
  ! 全域窓の端でのみ1行縮める(dcp%js+1 とはしないこと)。
  ! td はハロ行 js-1/je+1 でも再計算する(taxy と同じ案A。ステンシル
  ! 幅1なので u,v の交換幅2の内側に収まり、追加のハロ交換は不要)
  do j = max(dcp%js - 1, dcp%jw1 + 1), min(dcp%je + 1, dcp%jw2 - 1)
    do i = g%wx(1,j)+1, g%wx(2,j)-1
      ! 乾湿遷移で前ステップの値が残らないよう毎回クリアする
      td_mod%td(1:2,i,j) = 0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) < p%dd) cycle
      call get_laplacian(s%u, s%v, s%h, p%dd, td_mod%wd8, g%x, i, j, lu, lv)
      ! 拡散項は粘性力なので lm は乗じない(重力項と同様、エッジでの
      ! dtl = dt/lme の除算=付加質量による減衰をそのまま受ける。
      ! 移流項の lm 乗算は輸送項が力でないための相殺であり流儀が異なる)
      td_mod%td(1,i,j) = p_diffusion_nu * lu
      td_mod%td(2,i,j) = p_diffusion_nu * lv
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! k番目の境界上の拡散項を計算(両側セル平均の法線投影。移流項と同型)
!----------------------------------------------------------------------
module function diff_edge(i, j, k, in, jn) result(td_e)
  integer, intent(in) :: i, j, k, in, jn
  real :: td_e

  real :: tdxe, tdye

  tdxe = (td_mod%td(1,i,j) + td_mod%td(1,in,jn)) / 2  ! 拡散項(x方向, 符合は座標軸方向が正)
  tdye = (td_mod%td(2,i,j) + td_mod%td(2,in,jn)) / 2  ! 拡散項(y方向, 符合は座標軸方向が正)
  td_e = tdxe * n8x(k) + tdye * n8y(k)  ! 拡散項(符合は中心セルから近傍セルに向かい正)
end function


!----------------------------------------------------------------------
! 拡散項用の内部場の破棄
!----------------------------------------------------------------------
module subroutine diff_dispose()
  if (allocated(td_mod%td)) deallocate(td_mod%td)
end subroutine


!----------------------------------------------------------------------
! 変数u, vのラプラシアン(エッジフラックス発散形)
!----------------------------------------------------------------------
subroutine get_laplacian(u, v, h, dd, wd, x, i, j, lu, lv)
  ! 帯確保の配列を渡すダミーは assumed-shape+下限指定(§12)
  real, intent(in) :: u(1:, dcp%jsh:)
  real, intent(in) :: v(1:, dcp%jsh:)
  real, intent(in) :: h(1:, dcp%jsh:)
  real, intent(in) :: dd
  real, intent(in) :: wd(1:8)
  integer, intent(in) :: x(0:, dcp%jsh-1:)
  integer, intent(in) :: i, j
  real, intent(out) :: lu, lv

  integer :: in, jn, k

  lu = 0
  lv = 0
  do k = 1, 8
    in = i + din(k)
    jn = j + djn(k)
    ! 無効セル・移動限界未満の近傍はエッジごと欠落させる(no-flux 閉鎖。
    ! 勾配計算と違い残りの重みで再正規化しないこと)
    if (x(in,jn) <= 0) cycle
    if (h(in,jn) < dd) cycle
    lu = lu + wd(k) * (u(in,jn) - u(i,j))
    lv = lv + wd(k) * (v(in,jn) - v(i,j))
  end do

end subroutine


end submodule
