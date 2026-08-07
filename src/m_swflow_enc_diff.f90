submodule(m_swflow_enc) m_swflow_enc_diff
  use m_state, only : t_state
  use m_parallel, only : dcp, par_info   ! 親経由のホスト結合は nvfortran バグ回避のため直接 use
  implicit none

  ! 拡散項の設計(developer.md §20)
  !   セル中心の拡散項は「2点勾配のエッジフラックスをセル面積で発散」する
  !   有限体積形で評価する(変係数の保存形 ∇·(ν∇u)):
  !     ∇·(ν∇f)|(i,j) ≒ (1/(dx·dy)) Σ_k l8(k)·ν_e·(f_k − f_0)/w8dr(k)
  !     (ν_e = 両セルの ν の算術平均)
  !   既存の通過幅 l8 と距離 w8dr の組は、任意の p_diagratio・dx≠dy で
  !   fxx, fyy の係数が厳密に 1、fxy と奇数次が 0 になる(整合な9点
  !   ラプラシアン。証明は §20)。全重み非負なので離散最大値原理も成立。
  !   勾配(get_diff)と違い再正規化はしない: 欠けたエッジ=そのエッジの
  !   拡散フラックスがゼロ(no-flux 閉鎖)が物理的に正しい。
  !   渦動粘性 ν のモデル(f_diffusion_term):
  !     1: 定数 ν = p_diffusion_nu(init で場を埋め、以後静的)
  !     2: ゼロ方程式 ν = ν0 + α·u*·h(毎ステップ更新。u* は Manning 則
  !        から u* = √g·n·|V|·h^(-1/6)、α = p_diffusion_alpha、
  !        ν0 = p_diffusion_nu はバックグラウンド粘性)。
  !        陽解法の安定上界 nu_max でセルごとにクランプする
  type t_enc_diff
    ! セル中心での拡散項(第1添字は1:2でx,y成分)
    real, allocatable :: td(:,:,:)
    ! セル中心での渦動粘性係数 (m2/s)
    real, allocatable :: nu(:,:)
    ! 方向別係数 l8(k)/(w8dr(k)·dx·dy)(diff_init が設定)
    real :: wd8(1:8) = 0.0
    ! 陽解法の安定上界 1/(dt·Σwd8)(diff_init が設定)
    real :: nu_max = 0.0
    ! ゼロ方程式モデルの係数 α·√g(diff_init が設定)
    real :: cnu = 0.0
    ! 安定上界クランプの警告を表示済みか(初回のみ表示)
    logical :: clamp_warned = .false.
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
  character(len=256) :: msg

  if (f_diffusion_term <= 0) return
  allocate(td_mod%td(1:2,1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(td_mod%nu(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  forall(k=1:8) td_mod%wd8(k) = l8(k) / (w8dr(k) * g%dx * g%dy)

  ! 陽解法の安定上界(Gershgorin による目安): dt ≦ 1/(ν·Σ_k wd8(k))
  td_mod%nu_max = 1.0 / (p%dt * sum(td_mod%wd8(1:8)))
  td_mod%cnu = p_diffusion_alpha * sqrt(p%gg)

  if (f_diffusion_term == 1) then
    ! 定数モデル: ν 場は静的(ハロ行を含む全確保範囲を埋める)
    td_mod%nu(:,:) = p_diffusion_nu
    if (p_diffusion_nu > td_mod%nu_max) then
      write(msg, '(a,g0.4,a,g0.4,a)') &
        "WARNING: 拡散項の安定条件を超過 nu=", p_diffusion_nu, &
        " > ", td_mod%nu_max, " (m2/s)"
      call par_info(trim(msg))
    end if
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
  logical :: any_clamp
  real, parameter :: r56 = 5.0 / 6.0
  character(len=256) :: msg

  if (f_diffusion_term <= 0) return

  ! ゼロ方程式モデル: ν 場を毎ステップ更新する
  !   td の計算はセル±1近傍の ν を読むため、ν はハロ幅2まで構築する
  !   (rn は帯+ハロ2、h/vv は交換幅2で手元にある=追加のハロ交換なし)
  if (f_diffusion_term == 2) then
    any_clamp = .false.
    !$omp parallel do schedule(dynamic) private(i, j) reduction(.or.:any_clamp)
    do j = max(dcp%jw1, dcp%js - 2), min(dcp%jw2, dcp%je + 2)
      do i = g%wx(1,j), g%wx(2,j)
        ! 乾湿遷移で前ステップの値が残らないよう毎回クリアする
        td_mod%nu(i,j) = 0
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        if (s%h(i,j) < p%dd) cycle
        ! ν = ν0 + α·u*·h = ν0 + α·√g·n·|V|·h^(5/6)
        td_mod%nu(i,j) = p_diffusion_nu &
                       + td_mod%cnu * g%rn(i,j) * s%vv(i,j) * s%h(i,j)**r56
        ! 陽解法の安定上界でクランプする(発動は極端な条件のみ)
        if (td_mod%nu(i,j) > td_mod%nu_max) then
          td_mod%nu(i,j) = td_mod%nu_max
          any_clamp = .true.
        end if
      end do
    end do
    !$omp end parallel do
    if (any_clamp .and. .not. td_mod%clamp_warned) then
      write(msg, '(a,g0.4,a)') &
        "WARNING: 拡散項の渦動粘性を安定上界 ", td_mod%nu_max, &
        " (m2/s) でクランプしました(以後の発生は表示しない)"
      call par_info(trim(msg))
      td_mod%clamp_warned = .true.
    end if
  end if

  !$omp parallel do schedule(dynamic) private(i, j)
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
      call get_diffusion(s%u, s%v, s%h, td_mod%nu, p%dd, td_mod%wd8, g%x, &
                         i, j, td_mod%td(1,i,j), td_mod%td(2,i,j))
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
  if (allocated(td_mod%nu)) deallocate(td_mod%nu)
  td_mod%clamp_warned = .false.
end subroutine


!----------------------------------------------------------------------
! 変数u, vの拡散項 ∇·(ν∇u)(エッジフラックス発散形。ν_e は両セル平均)
!----------------------------------------------------------------------
subroutine get_diffusion(u, v, h, nu, dd, wd, x, i, j, tdx, tdy)
  ! 帯確保の配列を渡すダミーは assumed-shape+下限指定(§12)
  real, intent(in) :: u(1:, dcp%jsh:)
  real, intent(in) :: v(1:, dcp%jsh:)
  real, intent(in) :: h(1:, dcp%jsh:)
  real, intent(in) :: nu(1:, dcp%jsh:)
  real, intent(in) :: dd
  real, intent(in) :: wd(1:8)
  integer, intent(in) :: x(0:, dcp%jsh-1:)
  integer, intent(in) :: i, j
  real, intent(out) :: tdx, tdy

  real :: wnu
  integer :: in, jn, k

  tdx = 0
  tdy = 0
  do k = 1, 8
    in = i + din(k)
    jn = j + djn(k)
    ! 無効セル・移動限界未満の近傍はエッジごと欠落させる(no-flux 閉鎖。
    ! 勾配計算と違い残りの重みで再正規化しないこと)
    if (x(in,jn) <= 0) cycle
    if (h(in,jn) < dd) cycle
    wnu = wd(k) * (nu(i,j) + nu(in,jn)) / 2
    tdx = tdx + wnu * (u(in,jn) - u(i,j))
    tdy = tdy + wnu * (v(in,jn) - v(i,j))
  end do

end subroutine


end submodule
