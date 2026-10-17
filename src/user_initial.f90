!======================================================================
! 初期条件のユーザールーチン集(m_state の submodule)
!
!   親モジュールへの公開面は入口の手続きのみ:
!     user_initial_defined : 識別名が登録済みかを返す(検証用。副作用なし)
!     user_initial_names   : 登録済み識別名の一覧文字列(エラー表示用)
!     user_initial_run     : 識別名で該当ルーチンを実行(全ランクで呼ばれる)
!   分岐(resolve)と識別名簿(routine_names)はこの submodule に閉じる。
!
!   ルーチンの追加手順(このファイルだけで完結する。利用者向けの丁寧な
!   説明は docs/users_guide/user_routines.md):
!     1. initial_template を複製して実装する。契約は「全域添字で、配列の
!        確保範囲の中に書く」: 受け取る s は窓形の全域一時状態 ts
!        (領域マスクの窓±ハロ。全域添字。developer.md §82)なので、
!        ループは lbound/ubound(s%h) で回す(窓が全域なら 1:nx, 1:ny と同じ)。
!        g%z も同じ窓形。マスク類 g%x, g%sw, g%rw は全域 (1:nx, 1:ny)。
!     2. routine_names に識別名を登録する(snake_case)
!     3. resolve の select case に分岐を1行追加する
!======================================================================
submodule(m_state) user_initial
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_parallel, only : par_abort
  implicit none

  ! ユーザールーチンの呼び出し規約
  abstract interface
    subroutine user_initial_if(p, g, s)
      import :: t_sysparam, t_geoinfo, t_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
    end subroutine
  end interface

  ! 識別名簿(エラー表示用の一覧)。名簿と resolve の分岐は同時に
  ! 更新すること(乖離は defined/run が「未定義名」として検出する)
  character(len=*), parameter :: routine_names(1:19) = [ character(len=32) :: &
      "wave_hump",        & ! 波例題: 円形コサイン型の初期水位
      "dambreak_step",    & ! ダム破壊例題: x 方向の段状初期水深(Stoker 解析解の検証用)
      "wave_standing_x",  & ! 定在波例題: 閉じた水槽の x 方向モード (4, 0)(分散関係の検証用)
      "wave_standing_xy", & ! 定在波例題: 閉じた水槽の対角モード (4, 4)(同上。45° 方向)
      "wave_solitary",    & ! 孤立波例題: x 方向に進む sech² 孤立波 a/H = 0.1(非静水圧の非線形検証用)
      "wave_solitary28",  & ! 孤立波例題: 同上で a/H = 0.28(Synolakis 1987 の砕波遡上ケース)
      "wave_solitary0185",& ! 孤立波例題: 同上で a/H = 0.0185(Synolakis 1987 の非砕波遡上ケース)
      "wave_solitary28_toe",& ! 孤立波例題: a/H = 0.28 を斜面の脚の近く x0 = 120 m に置く(平坦部の影響の切り分け用)
      "wave_solitary28_x145",& ! 孤立波例題: 同上で x0 = 145 m(脚の 5 m 手前。Titov & Synolakis 1995 の初期配置)
      "wave_solitary10_toe",& ! 孤立波例題: a/H = 0.10、x0 = 120 m(砕波遡上則の振幅系列。plan §15.5)
      "wave_solitary20_toe",& ! 孤立波例題: a/H = 0.20、x0 = 120 m(同上)
      "wave_solitary40_toe",& ! 孤立波例題: a/H = 0.40、x0 = 120 m(同上)
      "wave_bore",        & ! 長波例題: x < x0 を a/H = 0.1 だけ高くした段差(tanh 遷移)。右へ進む
                            !   単純波の流速。非静水圧では undular bore に分裂する(plan §11 Phase 5)
      "wave_bore20",      & ! 長波例題: 同上で a/H = 0.2
      "jet_gaussian",     & ! 拡散項例題: x 方向に一様なガウス形ジェット u(y)(渦動粘性による拡散の解析解検証用。test/diffusion)
      "gyre_smooth",      & ! 副格子例題: 閉じた水槽の 1 セル渦(流れ関数 sin·sin。test/sublattice の対照)
      "gyre_alternating", & ! 副格子例題: 同じ渦を (i+j) の偶奇で逆回転にした斜め副格子モード(test/sublattice)
      "gyre_mixed",       & ! 副格子例題: 滑らかな渦(振幅 1)に副格子モード(振幅 0.5)を重ねる(背景流下の線形減衰率)
      "template"          ] ! 新規ルーチンの雛形(空)

contains

!======================================================================
!===================== 入口(親モジュールへ公開)=====================
!======================================================================

!----------------------------------------------------------------------
! 識別名が登録済みかを返す(検証用)
!----------------------------------------------------------------------
module function user_initial_defined(name) result(res)
  character(len=*), intent(in) :: name
  logical :: res
  procedure(user_initial_if), pointer :: fp
  fp => resolve(name)
  res = associated(fp)
end function

!----------------------------------------------------------------------
! 登録済み識別名の一覧文字列(エラー表示用)
!----------------------------------------------------------------------
module function user_initial_names() result(names)
  character(len=:), allocatable :: names
  integer :: i
  names = ""
  do i = 1, size(routine_names)
    if (i > 1) names = names//", "
    names = names//trim(routine_names(i))
  end do
end function

!----------------------------------------------------------------------
! 識別名で該当ルーチンを実行する(全ランクで冗長に呼ばれる)
!   名前の検証は呼び出し側が済ませている前提。ここでの不一致は
!   名簿と resolve の乖離(プログラミングエラー)なので abort
!----------------------------------------------------------------------
module subroutine user_initial_run(p, g, s, name)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  character(len=*), intent(in) :: name
  procedure(user_initial_if), pointer :: fp
  fp => resolve(name)
  if (.not. associated(fp)) call par_abort("state: user routine listed but not resolved: "//trim(name))
  call fp(p, g, s)
end subroutine

!======================================================================
!======================= 分岐(submodule 私有)=======================
!======================================================================

!----------------------------------------------------------------------
! 識別名 → 手続きポインタ(未定義名は null)
!----------------------------------------------------------------------
function resolve(name) result(fp)
  character(len=*), intent(in) :: name
  procedure(user_initial_if), pointer :: fp
  select case (trim(name))
    case ("wave_hump")
      fp => initial_wave_hump
    case ("dambreak_step")
      fp => initial_dambreak_step
    case ("wave_standing_x")
      fp => initial_wave_standing_x
    case ("wave_standing_xy")
      fp => initial_wave_standing_xy
    case ("wave_solitary")
      fp => initial_wave_solitary
    case ("wave_solitary28")
      fp => initial_wave_solitary28
    case ("wave_solitary0185")
      fp => initial_wave_solitary0185
    case ("wave_solitary28_toe")
      fp => initial_wave_solitary28_toe
    case ("wave_solitary28_x145")
      fp => initial_wave_solitary28_x145
    case ("wave_solitary10_toe")
      fp => initial_wave_solitary10_toe
    case ("wave_solitary20_toe")
      fp => initial_wave_solitary20_toe
    case ("wave_solitary40_toe")
      fp => initial_wave_solitary40_toe
    case ("wave_bore")
      fp => initial_wave_bore
    case ("wave_bore20")
      fp => initial_wave_bore20
    case ("jet_gaussian")
      fp => initial_jet_gaussian
    case ("gyre_smooth")
      fp => initial_gyre_smooth
    case ("gyre_alternating")
      fp => initial_gyre_alternating
    case ("gyre_mixed")
      fp => initial_gyre_mixed
    case ("template")
      fp => initial_template
    case default
      fp => null()
  end select
end function

!======================================================================
!========================== ユーザールーチン ==========================
!======================================================================

!----------------------------------------------------------------------
! 波例題: 円形コサイン型の初期水位
!----------------------------------------------------------------------
subroutine initial_wave_hump(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s

  integer :: i, j
  real, parameter :: ll = 30., hh = 0.5
  real :: xx, yy, rr, dx, dy, eta
  real :: lx, ly
  real :: pi
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  pi = acos(-1.0)   ! 宣言時初期化は暗黙 SAVE になるため実行文で代入(Phase 0a)
  lx = g%lx
  ly = g%ly

  dx = g%dx
  dy = g%dy

  !s%h = 1.0

  do j = lbound(s%h, 2), ubound(s%h, 2)
    do i = lbound(s%h, 1), ubound(s%h, 1)
      xx = (i - 0.5) * dx - lx / 2
      yy = (j - 0.5) * dy - lx / 2
      rr = sqrt(xx**2 + yy**2)
      !rr = abs(xx)
      if (rr < ll / 2) then
        eta = hh * cos(rr / ll * 2 * pi) + hh
      else
        eta = 0.0
      end if
      !if (x(i,j) > 0) then
        s%h(i,j) = max(s%h(i,j) + eta - g%z(i,j), 0.0)
      !else
      !  d(i,j) = 0.0
      !end if
    end do
  end do

end subroutine


!----------------------------------------------------------------------
! ダム破壊例題: x 方向の段状初期水深(湿潤床。Stoker 解析解の検証用)
!   x < lx/2 を上流側水深 hl、それ以外を下流側水深 hr とする。
!   h0 等の namelist 値は使わず固定値(wave_hump と同じ流儀)。
!   nx が偶数なら段差はセル境界に厳密に一致する。
!   解析解との比較は test/dambreak/Check_stoker.py(hl, hr は同期して
!   変更すること)
!----------------------------------------------------------------------
subroutine initial_dambreak_step(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s

  integer :: i, j
  real, parameter :: hl = 10.0, hr = 1.0
  real :: xx
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  do j = lbound(s%h, 2), ubound(s%h, 2)
    do i = lbound(s%h, 1), ubound(s%h, 1)
      xx = (i - 0.5) * g%dx
      if (xx < g%lx / 2) then
        s%h(i,j) = max(hl - g%z(i,j), 0.0)
      else
        s%h(i,j) = max(hr - g%z(i,j), 0.0)
      end if
    end do
  end do

end subroutine


!----------------------------------------------------------------------
! 定在波例題: 閉じた矩形水槽の固有モードの初期水位(初期流速 0)
!   η = a·cos(m π x/lx)(x モード)、η = a·cos(m π x/lx)·cos(m π y/ly)
!   (対角モード)。m = 4 固定、振幅 a = 1e-3 × 初期水深(線形波)。
!   セル中心 x = (i − 1/2)Δx の余弦は C 格子の離散 Neumann 固有関数
!   なので、壁で反射しても形を保つ定在波になる。水深 h0(namelist)を
!   変えると水深 H と kH が変わり、格子は不変のまま分散関係を走査できる
!   (test/nhwave。docs/nonhydrostatic_plan.md §11 Phase 1)
!----------------------------------------------------------------------
subroutine initial_wave_standing_x(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  integer, parameter :: m = 4
  real, parameter :: arel = 1.0e-3
  real :: xx, pi
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  pi = acos(-1.0)
  do j = lbound(s%h, 2), ubound(s%h, 2)
    do i = lbound(s%h, 1), ubound(s%h, 1)
      xx = (i - 0.5) * g%dx
      s%h(i,j) = s%h(i,j) * (1.0 + arel * cos(m * pi * xx / g%lx))
    end do
  end do
end subroutine

subroutine initial_wave_standing_xy(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  integer, parameter :: m = 4
  real, parameter :: arel = 1.0e-3
  real :: xx, yy, pi
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  pi = acos(-1.0)
  do j = lbound(s%h, 2), ubound(s%h, 2)
    do i = lbound(s%h, 1), ubound(s%h, 1)
      xx = (i - 0.5) * g%dx
      yy = (j - 0.5) * g%dy
      s%h(i,j) = s%h(i,j) * (1.0 + arel * cos(m * pi * xx / g%lx) * cos(m * pi * yy / g%ly))
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 孤立波例題: x 方向に進む Boussinesq 型の孤立波(docs/nonhydrostatic_plan.md
!   §11 Phase 5。test/nhsolitary、test/nhbreak)
!   η = a·sech²(k_s (x − x0)),  k_s = √(3a/(4H³)),  u = c·η/(H + η),
!   c = √(g(H + a))。H = h0(静水面の標高。地盤 z = 0 基準)、x0 = 50 m
!   固定。地盤 z のあるセルは h = max(H + η − z, 0)(wave_hump と同じ
!   流儀。斜面上は静水のまま)。
!   静水圧(f_nonhydrostatic=0)では分散がなく前面が急峻化して段波になり、
!   1 層 NH では形を保って c で進む(KdV の解は 1 層モデルの厳密解では
!   ないので、わずかな形の調整と後続波が出る)
!----------------------------------------------------------------------
subroutine initial_wave_solitary(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call solitary_profile(p, g, s, 0.1)
end subroutine

subroutine initial_wave_solitary28(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call solitary_profile(p, g, s, 0.28)
end subroutine

subroutine initial_wave_solitary28_toe(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call solitary_profile_x0(p, g, s, 0.28, 120.0)
end subroutine

subroutine initial_wave_solitary28_x145(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call solitary_profile_x0(p, g, s, 0.28, 145.0)
end subroutine

subroutine initial_wave_solitary10_toe(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call solitary_profile_x0(p, g, s, 0.10, 120.0)
end subroutine

subroutine initial_wave_solitary20_toe(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call solitary_profile_x0(p, g, s, 0.20, 120.0)
end subroutine

subroutine initial_wave_solitary40_toe(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call solitary_profile_x0(p, g, s, 0.40, 120.0)
end subroutine

!----------------------------------------------------------------------
! 長波の段差(undular bore の初期条件): η = (a/2)(1 − tanh((x − x0)/L))、
!   x < x0 が a だけ高い。流速は右へ進む単純波のリーマン不変量
!   u = 2(√(g(H+η)) − √(gH))(前面は右へ進み、分散で波列に分裂する)。
!   H = h0(静水面の標高 = 平坦部の水深)、x0 = 100 m、遷移幅 L = 4 m。
!----------------------------------------------------------------------
subroutine initial_wave_bore(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call bore_profile(p, g, s, 0.1)
end subroutine

subroutine initial_wave_bore20(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call bore_profile(p, g, s, 0.2)
end subroutine

subroutine bore_profile(p, g, s, arel)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: arel
  integer :: i, j
  real, parameter :: x0 = 100.0, lt = 4.0
  real :: hh, aa, xx, eta
  do j = lbound(s%h, 2), ubound(s%h, 2)
    do i = lbound(s%h, 1), ubound(s%h, 1)
      hh = s%h(i,j)
      aa = arel * hh
      xx = (i - 0.5) * g%dx - x0
      eta = 0.5 * aa * (1.0 - tanh(xx / lt))
      s%h(i,j) = max(hh + eta - g%z(i,j), 0.0)
      if (s%h(i,j) > 0.0) then
        s%u(i,j) = 2.0 * (sqrt(p%gg * (hh + eta)) - sqrt(p%gg * hh))
      else
        s%u(i,j) = 0.0
      end if
      s%v(i,j) = 0.0
    end do
  end do
end subroutine

subroutine initial_wave_solitary0185(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call solitary_profile(p, g, s, 0.0185)
end subroutine

subroutine solitary_profile(p, g, s, arel)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: arel
  integer :: i, j
  real, parameter :: x0 = 50.0
  real :: hh, aa, ks, cc, xx, eta
  do j = lbound(s%h, 2), ubound(s%h, 2)
    do i = lbound(s%h, 1), ubound(s%h, 1)
      hh = s%h(i,j)                 ! h0 = 静水面の標高(z = 0 基準)
      aa = arel * hh
      ks = sqrt(3.0 * aa / (4.0 * hh**3))
      cc = sqrt(p%gg * (hh + aa))
      xx = (i - 0.5) * g%dx - x0
      eta = aa / cosh(ks * xx)**2
      s%h(i,j) = max(hh + eta - g%z(i,j), 0.0)
      if (s%h(i,j) > 0.0) then
        s%u(i,j) = cc * eta / (hh + eta)
      else
        s%u(i,j) = 0.0
      end if
      s%v(i,j) = 0.0
    end do
  end do
end subroutine


! 同上で波頂位置 x0 (m) を引数にとる(砕波遡上の原因切り分け用。既存の
! solitary_profile を触らないのは、-Ofast のコード生成が変わって reference との
! ビット一致が崩れるのを避けるため。developer.md §69.6)
subroutine solitary_profile_x0(p, g, s, arel, x0)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: arel, x0
  integer :: i, j
  real :: hh, aa, ks, cc, xx, eta
  do j = lbound(s%h, 2), ubound(s%h, 2)
    do i = lbound(s%h, 1), ubound(s%h, 1)
      hh = s%h(i,j)
      aa = arel * hh
      ks = sqrt(3.0 * aa / (4.0 * hh**3))
      cc = sqrt(p%gg * (hh + aa))
      xx = (i - 0.5) * g%dx - x0
      eta = aa / cosh(ks * xx)**2
      s%h(i,j) = max(hh + eta - g%z(i,j), 0.0)
      if (s%h(i,j) > 0.0) then
        s%u(i,j) = cc * eta / (hh + eta)
      else
        s%u(i,j) = 0.0
      end if
      s%v(i,j) = 0.0
    end do
  end do
end subroutine

!----------------------------------------------------------------------
! x 方向に一様なガウス形ジェット(拡散項の解析解ベンチマーク。test/diffusion)
!   u(y) = U0 exp(−(y − yc)²/(2σ²))、v = 0、水深は不変(h0 のまま)。
!   yc = 水路の中央(ly/2)、σ = 10 m、U0 = 0.05 m/s。粗度 0・平坦床なら
!   運動方程式は ∂u/∂t = ∇·(ν∇u) だけになり、定数 ν の解析解
!     u(y, t) = U0 σ/√(σ² + 2νt) exp(−(y − yc)²/(2(σ² + 2νt)))
!   と比較できる(x 方向の壁からの波が届く前の時間・中央列で評価)。
!   U0・σ は test/diffusion/Check_analytic.py と対で保守すること。
!----------------------------------------------------------------------
subroutine initial_jet_gaussian(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real, parameter :: u0 = 0.05, sigma = 10.0
  real :: yc, yy
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  yc = 0.5 * g%ny * g%dy
  do j = lbound(s%h, 2), ubound(s%h, 2)
    yy = (j - 0.5) * g%dy - yc
    do i = lbound(s%h, 1), ubound(s%h, 1)
      if (s%h(i,j) > 0.0) then
        s%u(i,j) = u0 * exp(-yy**2 / (2.0 * sigma**2))
      else
        s%u(i,j) = 0.0
      end if
      s%v(i,j) = 0.0
    end do
  end do
end subroutine

!----------------------------------------------------------------------
! 閉じた水槽の 1 セル渦(斜め副格子モードの減衰率ベンチマーク。test/sublattice)
!   流れ関数 ψ = A sin(πx/lx) sin(πy/ly)、u = ∂ψ/∂y、v = −∂ψ/∂x(壁で法線
!   流速ゼロ)、最大流速 V0 = 0.2 m/s(A = V0·lx/π)。水深は不変(h0 のまま)。
!   gyre_alternating は同じ渦に (−1)^(i+j) を乗じ、偶数・奇数の副格子で
!   逆回転にする: 法線エッジの初期流速(両セル平均)は 0、斜めエッジだけが
!   副格子ごとの渦を持つ = 移流項が作用しない斜め副格子モード
!   (developer.md §68.36)。V0・形は test/sublattice/Check_sublattice.py と
!   対で保守すること。
!----------------------------------------------------------------------
subroutine initial_gyre_smooth(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call gyre(p, g, s, 1.0, 0.0)
end subroutine

subroutine initial_gyre_alternating(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call gyre(p, g, s, 0.0, 1.0)
end subroutine

subroutine initial_gyre_mixed(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  call gyre(p, g, s, 1.0, 0.5)
end subroutine

! 渦の重ね合わせ: 係数 = a_smooth + a_alt·(−1)^(i+j)
!   smooth = (1, 0)、alternating = (0, 1)、mixed = (1, 0.5)
subroutine gyre(p, g, s, a_smooth, a_alt)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: a_smooth, a_alt
  integer :: i, j
  real, parameter :: v0 = 0.2
  real, parameter :: pi = 3.14159265358979323846
  real :: lx, ly, xx, yy, aa, sg
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  lx = g%nx * g%dx
  ly = g%ny * g%dy
  aa = v0 * lx / pi
  do j = 1, g%ny
    yy = (j - 0.5) * g%dy
    do i = 1, g%nx
      xx = (i - 0.5) * g%dx
      if (mod(i + j, 2) == 0) then
        sg = a_smooth + a_alt
      else
        sg = a_smooth - a_alt
      end if
      if (s%h(i,j) > 0.0) then
        s%u(i,j) =  sg * aa * (pi / ly) * sin(pi * xx / lx) * cos(pi * yy / ly)
        s%v(i,j) = -sg * aa * (pi / lx) * cos(pi * xx / lx) * sin(pi * yy / ly)
      else
        s%u(i,j) = 0.0
        s%v(i,j) = 0.0
      end if
    end do
  end do
end subroutine

!----------------------------------------------------------------------
! 新規ルーチンの雛形(空。複製して使う)
!----------------------------------------------------------------------
subroutine initial_template(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (s%initialized) continue  ! 引数未使用の警告を抑制
end subroutine

end submodule
