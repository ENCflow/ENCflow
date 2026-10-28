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
  !   砕波域の渦粘性(nh_break_visc > 0。plan §15): 親の nh_nub(前ステップの
  !   nh_project が書いて halo 交換済み)を ν に加える。f_diffusion_term = 0
  !   でも nh_break_visc > 0 なら拡散項を計算する(have_diff)。
  !   沿岸の波浪場の砕波による水平混合(wf_break_visc > 0。§88): 波浪場が更新ごとに
  !   書く ν_w = M h (D/ρ)^(1/3)(s%wvnub。帯±ハロ)を diff_wave_visc が ν に加えて
  !   拡散を求め直す(diff_prepare の後に親が呼ぶ)。
  ! 私有状態 t_enc_diff / td_mod は親モジュールに置く(§13 の様式。文脈の付け替えの対象)

contains
!----------------------------------------------------------------------
! 拡散項の内部場の確保と安定条件の検査
!----------------------------------------------------------------------
module subroutine diff_init(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  integer :: k
  character(len=256) :: msg

  if (.not. opt%have_diff) return
  allocate(td_mod%td(1:2, dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(td_mod%nu(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  forall(k=1:8) td_mod%wd8(k) = geo%l8(k) / (geo%w8dr(k) * g%dx * g%dy)

  ! 陽解法の安定上界(Gershgorin による目安): dt ≦ 1/(ν·Σ_k wd8(k))
  td_mod%nu_max = 1.0 / (p%dt * sum(td_mod%wd8(1:8)))
  td_mod%cnu = opt%p_diffusion_alpha * sqrt(p%gg)

  if (opt%f_diffusion_term == 1) then
    ! 定数モデル: ν 場は静的(ハロ行を含む全確保範囲を埋める)
    td_mod%nu(:,:) = opt%p_diffusion_nu
    if (opt%p_diffusion_nu > td_mod%nu_max) then
      write(msg, '(a,g0.4,a,g0.4,a)') &
        "list_enc: p_diffusion_nu=", opt%p_diffusion_nu, &
        " exceeds the diffusion stability limit ", td_mod%nu_max, " (m2/s)"
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

  if (.not. opt%have_diff) return

  ! ゼロ方程式モデル: ν 場を毎ステップ更新する
  !   td の計算はセル±1近傍の ν を読むため、ν はハロ幅2まで構築する
  !   (rn は帯+ハロ2、h/vv は交換幅2で手元にある=追加のハロ交換なし)
  if (opt%f_diffusion_term == 2) then
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
        td_mod%nu(i,j) = opt%p_diffusion_nu &
                       + td_mod%cnu * g%rn(i,j) * s%vv(i,j) * s%h(i,j)**r56
        ! 陽解法の安定上界でクランプする(発動は極端な条件のみ)
        if (td_mod%nu(i,j) > td_mod%nu_max) then
          td_mod%nu(i,j) = td_mod%nu_max
          any_clamp = .true.
        end if
      end do
    end do
    !$omp end parallel do
  end if

  ! 砕波域の渦粘性 ν_b を加える(ν = ν_model + ν_b。定数モデルは静的な ν 場を
  ! 毎ステップ基底値から作り直す。範囲は td の近傍 ±1 が読むハロ 2 まで)
  if (nhp%nh_break_visc > 0.0) then
    if (opt%f_diffusion_term /= 2) any_clamp = .false.
    !$omp parallel do schedule(dynamic) private(i, j) reduction(.or.:any_clamp)
    do j = max(dcp%jw1, dcp%js - 2), min(dcp%jw2, dcp%je + 2)
      do i = g%wx(1,j), g%wx(2,j)
        if (opt%f_diffusion_term == 1) td_mod%nu(i,j) = opt%p_diffusion_nu
        if (opt%f_diffusion_term == 0) td_mod%nu(i,j) = 0
        if (nhp%nh_nub(i,j) <= 0.0) cycle
        td_mod%nu(i,j) = td_mod%nu(i,j) + nhp%nh_nub(i,j)
        if (td_mod%nu(i,j) > td_mod%nu_max) then
          td_mod%nu(i,j) = td_mod%nu_max
          any_clamp = .true.
        end if
      end do
    end do
    !$omp end parallel do
  end if

  if (opt%f_diffusion_term == 2 .or. nhp%nh_break_visc > 0.0) then
    if (any_clamp .and. .not. td_mod%clamp_warned) then
      write(msg, '(a,g0.4,a)') &
        "swflow: diffusion eddy viscosity clamped to the stability limit ", td_mod%nu_max, &
        " (m2/s), further occurrences are not reported"
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
! 側方 Neumann の辺に接するセルの拡散項(§88。diff_prepare の後に親が呼ぶ)
!   diff_prepare の主ループは、窓の端を 1 行・1 列縮める定型(§11)のため格子の枠に接する
!   セルを計算しない(0 のまま)。側方 Neumann の辺は「外に同じ地形・流れが続く」扱いなので、
!   その辺に接するセルも、枠外の近傍を鏡像セル(bc_neumann_cell)に置き換えて get_diffusion と
!   同じ式で求める(勾配 0)。0 のままだと岸沿いに一様な沿岸流でも辺の行だけ拡散が欠けて
!   一様性が崩れ、流入側の辺から発散した(段 W2 の側方 Neumann と拡散項の併用。§88.12)。
!   側方 Neumann の辺に接しない枠のセル(他の境界型の辺)は従来どおり 0。主ループとは
!   扱うセルが重ならない。主ループと同じく帯±1 行を冗長に計算する(鏡像は帯±2 行の中)。
!   diff_prepare の中で呼ぶと、側方 Neumann のない拡散項の計算(test/diffusion)が -Ofast で
!   最終桁でずれたので、diff_prepare は変えずに別の手続きにする
!----------------------------------------------------------------------
module subroutine diff_neumann(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: i, j, k, in, jn, im, jm
  logical :: ok, edge
  real :: wnu, tdx, tdy
  !$omp parallel do schedule(dynamic) private(i, j, k, in, jn, im, jm, ok, edge, wnu, tdx, tdy)
  do j = max(dcp%js - 1, dcp%jw1), min(dcp%je + 1, dcp%jw2)
    do i = g%wx(1,j), g%wx(2,j)
      if (i > 1 .and. i < dcp%nx_g .and. j > 1 .and. j < dcp%ny_g) cycle   ! 格子の辺に接しない
      td_mod%td(1:2,i,j) = 0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) < p%dd) cycle
      edge = .false.
      tdx = 0
      tdy = 0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        im = in
        jm = jn
        if (in < 1 .or. in > dcp%nx_g .or. jn < 1 .or. jn > dcp%ny_g) then
          call bc_neumann_cell(in, jn, ok, im, jm)
          if (.not. ok) cycle
          edge = .true.
        end if
        if (g%x(im,jm) <= 0) cycle
        if (s%h(im,jm) < p%dd) cycle
        wnu = td_mod%wd8(k) * (td_mod%nu(i,j) + td_mod%nu(im,jm)) / 2
        tdx = tdx + wnu * (s%u(im,jm) - s%u(i,j))
        tdy = tdy + wnu * (s%v(im,jm) - s%v(i,j))
      end do
      if (.not. edge) cycle
      td_mod%td(1,i,j) = tdx
      td_mod%td(2,i,j) = tdy
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 沿岸の波浪場の砕波による水平混合(wf_break_visc > 0。§88。diff_prepare の後に親が呼ぶ)
!   波浪場が更新ごとに書く ν_w = M h (D/ρ)^(1/3)(s%wvnub。帯±ハロ)を ν に足し、
!   diff_prepare の主ループと同じ範囲・同じ式でセルの拡散を求め直す。定数・なしのモデルの ν は
!   毎ステップ基底値から作り直してから足す(nh_break_visc の塊が作り直したときはその上に足す)。
!   範囲は td の近傍 ±1 が読むハロ 2 まで。diff_prepare を変えず、式も get_diffusion を呼ばずに
!   書く(拡散の手続きの命令列や展開の判断が変わると、波を使わない拡散項の計算が -Ofast で
!   最終桁でずれる。§88.12)
!----------------------------------------------------------------------
module subroutine diff_wave_visc(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: i, j, k, in, jn
  logical :: rebase, wclamp
  real :: wnu, tdx, tdy
  character(len=256) :: msg

  rebase = (nhp%nh_break_visc <= 0.0)
  wclamp = .false.
  !$omp parallel do schedule(dynamic) private(i, j) reduction(.or.:wclamp)
  do j = max(dcp%jw1, dcp%js - 2), min(dcp%jw2, dcp%je + 2)
    do i = g%wx(1,j), g%wx(2,j)
      if (rebase) then
        if (opt%f_diffusion_term == 1) td_mod%nu(i,j) = opt%p_diffusion_nu
        if (opt%f_diffusion_term == 0) td_mod%nu(i,j) = 0
      end if
      if (s%wvnub(i,j) <= 0.0) cycle
      td_mod%nu(i,j) = td_mod%nu(i,j) + s%wvnub(i,j)
      if (td_mod%nu(i,j) > td_mod%nu_max) then
        td_mod%nu(i,j) = td_mod%nu_max
        wclamp = .true.
      end if
    end do
  end do
  !$omp end parallel do
  if (wclamp .and. .not. td_mod%clamp_warned) then
    write(msg, '(a,g0.4,a)') &
      "swflow: diffusion eddy viscosity clamped to the stability limit ", td_mod%nu_max, &
      " (m2/s), further occurrences are not reported"
    call par_info(trim(msg))
    td_mod%clamp_warned = .true.
  end if

  ! セルの拡散を求め直す(diff_prepare の主ループと同じ範囲・同じ式)
  !$omp parallel do schedule(dynamic) private(i, j, k, in, jn, wnu, tdx, tdy)
  do j = max(dcp%js - 1, dcp%jw1 + 1), min(dcp%je + 1, dcp%jw2 - 1)
    do i = g%wx(1,j)+1, g%wx(2,j)-1
      td_mod%td(1:2,i,j) = 0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) < p%dd) cycle
      tdx = 0
      tdy = 0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle
        if (s%h(in,jn) < p%dd) cycle
        wnu = td_mod%wd8(k) * (td_mod%nu(i,j) + td_mod%nu(in,jn)) / 2
        tdx = tdx + wnu * (s%u(in,jn) - s%u(i,j))
        tdy = tdy + wnu * (s%v(in,jn) - s%v(i,j))
      end do
      td_mod%td(1,i,j) = tdx
      td_mod%td(2,i,j) = tdy
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
  td_e = tdxe * geo%n8x(k) + tdye * geo%n8y(k)  ! 拡散項(符合は中心セルから近傍セルに向かい正)
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
  real, intent(in) :: u(dcp%ish:, dcp%jsh:)
  real, intent(in) :: v(dcp%ish:, dcp%jsh:)
  real, intent(in) :: h(dcp%ish:, dcp%jsh:)
  real, intent(in) :: nu(dcp%ish:, dcp%jsh:)
  real, intent(in) :: dd
  real, intent(in) :: wd(1:8)
  integer, intent(in) :: x(dcp%ish-1:, dcp%jsh-1:)
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
