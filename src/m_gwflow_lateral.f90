module m_gwflow_lateral
  ! ========= 側方流動モデル: 非線形 Boussinesq(2次元・8近傍 FV) =========
  ! 飽和帯の側方 Darcy 流(handoff_gwflow_tani.md §3.2b)。
  ! m_swflow_enc と同じ8近傍・エッジ流量4成分の構造(die/dje/ke/sign_e の
  ! 規約、p_diagratio 系の通過幅配分)を踏襲し、
  !   ループ1: 各セルが所有するエッジ成分 k=1..4 のフラックスを計算
  !   ループ2: 計算済みエッジ流量で連続式(発散)+飽和超過の引き渡し
  ! の2段で解く(2026-08-05 決定。4近傍・セル中心の旧実装から変更)。
  !
  ! 【層パラメータ化(2026-08-09。§16)】
  !   カーネル(lateral_core)は「どの層の水をどの係数で動かすか」を
  !   t_latlayer で受ける層非依存の実装である。
  !     - 土層(層1): gwflow_lateral_calc が従来どおりの公開口。
  !       水頭底 = z - sd、容量 = sd·sy0(動的)、地表湛水結合あり、
  !       飽和超過は s%h へ
  !     - 風化基岩層(層2): m_gwflow_layer2 が lateral_core を直接呼ぶ。
  !       水頭底 = z - sd - d2、容量 = d2·sy2(定数)、地表湛水結合なし、
  !       飽和超過は s%hg へ(層1の超過は層1側の既存機構が地表へ渡す)
  !   幾何(距離・通過幅)とエッジ作業領域は層間で共有
  !   (gwflow_lateral_geom_init。冪等)。安定条件の検査は層ごとに
  !   gwflow_lateral_dtcheck で行う
  !
  ! 【管路連続体層カーネル(2026-08-18。gwconduit_plan.md §10)】
  !   下水道網・岩盤亀裂網などを表す等価連続体管路層のための第2カーネル
  !   conduit_core を併設する(呼び手は m_gwflow_conduit)。lateral_core と
  !   同じ 8 近傍・エッジ規約・2 ループ構造・幾何/作業領域(glt)を共有する
  !   が、次の点が異なるため別カーネルとする(lateral_core は不変 =
  !   層1・層2 のビット一致は構造的に保証):
  !     - 水頭が折れ線(不圧 sy_c / 被圧 sy_slot の疑似スロット切替。
  !       conduit_head)。容量超過は排出せず層内に保持する(被圧化)
  !     - 通水係数がエッジ別配列(t_conduitlayer%cnd。8 方向異方)
  !     - 流束則が選択制(1:線形, 2:sqrt 乱流。sqrt は |ΔH| < eps_h で
  !       線形化し、実効拡散係数の発散を抑える)
  !     - 通水断面は飽和厚でなく充満率 fill = min(hgc/cap, 1) で縮小
  !   安定条件は gwflow_conduit_dtcheck(線形化枝が最大勾配)で検査する
  !
  ! 【水質の同伴輸送(§30 W3。2026-08-26)】
  !   水質(fn_wq)が地下質量プール s%cg を持つとき(f_wq_infil=1)、
  !   層1の lateral_core は水と同じエッジ流量で cg を同伴輸送する:
  !     - ループ1: 質量エッジフラックス qm = q・(1/R)・cg_up/hg_up を
  !       水流量と同時に計算する(風上濃度・時刻 n の cg/hg。1/R =
  !       s%cg_rginv は平衡吸着の遅延化係数 wq_rg の逆数)。cg・hg は
  !       柱状量同士なので比は体積濃度と同義
  !     - ループ2: cg に発散を適用し、飽和超過の引き渡しでは超過水量に
  !       同率移動 w = (1/R)・cg・fx/(hg+fx) を同伴して記録場 s%fxs へ
  !       移す(湧出還元。m_wq が読んで地表 cq へ還元しゼロ戻しする =
  !       fxg と同型の契約。基底換算・台帳は m_wq が担い、本モジュールは
  !       wq の意味論を知らない)
  !   有効判定は s%cg の allocated(呼び手 gwflow_lateral_calc)。未確保
  !   なら qm も確保せず経路は完全に従来どおり。層2・管路層は cg を
  !   渡さない(層2の cg2 は将来拡張。§30)。複数エッジ同時流出の
  !   微小な行き過ぎは水と同じく許容(cg の微小負値は風上ガードで
  !   自己回復する)
  !
  ! 【エッジ配列は一時作業領域(永続エッジ状態レスの原則は不変。§4a)】
  !   フラックスは無履歴なので、エッジ配列 q は calc 内で書いて読み切る
  !   スクラッチである: 二重バッファなし・save/restore 対象外・
  !   par_halo_edge / par_edge_merge 不要。時刻 n の hg 退避(旧 wk)は
  !   2ループ分離により不要になった。
  !   動的に変わるエッジ(乾湿)は毎回書き手が 0 を含めて必ず代入する。
  !   マスク起因で書かれないエッジは確保時 0 のまま=恒久無フラックス。
  !
  ! 【定式化】
  !   h_gw = hg / sy(飽和帯厚。hg は柱状換算水量)
  !   H    = (s%z - s%sd - dbot) + h_gw [+ s%h]   … 全水頭(同 §3.2.3)。
  !          sd は動的共有状態 s%sd(初期値は入力係数 g%sd。将来
  !          geomorph が z と共動更新する。geomorph_plan.md §2.5)。
  !          z と sd が同じ Δz で動くため帯水層底 (z - sd) は不変。
  !          dbot は層の底面までの追加深(層1 = 0、層2 = d2)。
  !          地表湛水 s%h の寄与は層1の飽和セル(hg >= cap)のみ。
  !          ENCflow は不飽和セルにも湛水が存在しうる(浸透途中の
  !          表面水)が、不飽和帯を介した湛水は地下水面と水圧的に
  !          連続でないため駆動力に含めない(§3.2.3 の実装細目)
  !   q_k  = K_sh * h_e * (H_c - H_n)/dr_k * l_k
  !          (書き手セル c から k 近傍 n へ向かい正の体積流量。
  !           h_e は算術平均を上流側(H の高い側)の h_gw でキャップ)
  !   dr_k は近傍中心間距離(w8dr 相当)、l_k は通過幅(l8 相当。
  !   gw_diagratio による対角/軸配分。既定は m_swflow_enc の
  !   p_diagratio と同値 2/(2+sqrt(2)))
  !
  ! 【数値安定化(§5)】
  !   - 両セル h_gw <= eps で流量ゼロ(乾燥判定)
  !   - 上流側 h_gw <= eps で流量ゼロ
  !   - 過大流出の抑制: 1エッジの流出で上流側が eps を割る場合は縮小
  !     (exflux_reduction 相当。複数エッジ同時流出での微小な行き過ぎは
  !      浅水側と同じく許容し、次ステップの乾燥判定で自己回復する)
  !   - 陽解法の安定条件は h_gw <= 層厚 の構造的上界から静的に評価できる:
  !     dt <= 0.5 * sy * dx*dy / (K_sh * 層厚上界 * Σ_k l_k/dr_k)。
  !     init で検査し、実効時間刻み dts が超えるときは par_stop
  !
  ! 【MPI(§4a)】
  !   calc 冒頭で対象層の hg と s%h のハロを交換する
  !   (鉛直モデルと引き渡しが帯のみ更新するため、末尾交換では古くなる)。
  !   s%z のハロは m_swflow_enc がステップ頭で毎ステップ交換済みのものに
  !   依存する(呼び出し順 swflow→gwflow が前提。順序を変えるなら再検討)。
  !   帯界面のエッジ(行 je の成分 k=1..3)は、書き手ループをハロ行 je+1
  !   まで延長して自ランクでも冗長計算する(エッジは無履歴なので、南北の
  !   両ランクが同一のセルハロ入力・同一の式・同一の格納向きからビット
  !   厳密に同じ値を得る。swflow の par_edge_merge に相当する通信は不要。
  !   §11「冗長計算=配布機構」)
  !
  ! 【地表流との結合】
  !   側方流入で飽和容量を超えたセルは、超過分を上位(層1は s%h、層2は
  !   s%hg)へ渡す(反対称適用。m_gwflow_bucket 契約(1)(2)と同型。
  !   ループ2に畳み込む: ループ1が時刻 n の s%h を読み終えているため)。
  !   海域セルとは無フラックス(海への地下水流出は当面扱わない)
  !
  ! 【リスタート】
  !   無履歴のためモデル私有状態なし(s%hg は m_state が保存)。契約5の
  !   私有ファイルは不要
  ! =====================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_parallel, only : par_info, par_stop, dcp, par_halo_cell, par_allreduce_max
  implicit none
  private
  public :: gwflow_lateral_init
  public :: gwflow_lateral_calc
  public :: gwflow_lateral_dispose
  public :: t_latlayer
  public :: gwflow_lateral_geom_init
  public :: gwflow_lateral_dtcheck
  public :: lateral_core
  public :: t_conduitlayer
  public :: conduit_head
  public :: conduit_core
  public :: conduit_build_cnd
  public :: gwflow_conduit_dtcheck
  public :: gwflow_lateral_geom_get
  public :: gwflow_lateral_layer1_get

  ! 8近傍の規約(m_swflow_enc と同一。din/djn=近傍、die/dje/ke/sign_e=
  ! エッジ成分の格納位置と向き。k=1..4 が所有成分、k=5..8 は近傍の所有)
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]
  integer, parameter :: die(1:8) = [ -1,  0,  0, -1,  0, -1,  0,  0]
  integer, parameter :: dje(1:8) = [ -1, -1, -1,  0,  0,  0,  0,  0]
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]

  ! 層パラメータ(lateral_core の引数。呼び手が init で構築する)
  type t_latlayer
    real :: ksh = 0.0                ! 側方飽和透水係数 (m/s)
    real :: sy = 0.0                 ! 比湧水量
    real :: syinv = 0.0              ! 1 / sy
    real :: dbot = 0.0               ! 水頭底の追加深 (m。層1=0、層2=d2)
    real :: cap_const = -1.0         ! 容量 (m)。負なら動的 sd·sy(層1)
    logical :: to_surface = .true.   ! 飽和超過の行き先(T: s%h、F: s%hg)。
                                     !   T では地表湛水の水頭結合も行う
  end type

  ! 管路連続体層のパラメータ・静的場(conduit_core の引数。呼び手 =
  ! m_gwflow_conduit が init で構築する。gwconduit_plan.md §10.4)
  type t_conduitlayer
    integer :: fluxlaw = 2           ! 流束則(1:線形, 2:sqrt 乱流)
    real, allocatable :: syinvc(:,:)     ! 不圧枝の 1/sy_c(セル別。§46.5 (5)。
                                         !   一様指定はスカラー値充填 = ビット一致)
    real, allocatable :: syinv_slot(:,:) ! 被圧(疑似スロット)枝の 1/sy_slot(同上)
    real :: eps = 1.0e-3             ! 乾燥判定・過大流出抑制の正則化量 (m 柱状)
    real :: eps_h = 1.0e-2           ! sqrt 則の線形化幅 (m 水頭差)
    real, allocatable :: zbot(:,:)   ! 水頭底標高 (m)。帯+ハロ
    real, allocatable :: cap(:,:)    ! 貯留容量 (m 柱状)。0 = 管路なし。帯+ハロ
    real, allocatable :: cnd(:,:,:)  ! エッジ別コンダクタンス(所有4成分。m3/s。
                                     !   q 配列と同形状・同格納規約。静的)
  end type

  ! 幾何・作業領域(層間で共有。単一インスタンス前提。developer.md §12)
  type t_gwlat
    real :: eps = 1.0e-3             ! 乾燥判定・過大流出抑制の正則化厚 (m)
    real :: ainv = 0.0               ! 1 / (dx*dy)
    real :: rdr(1:8) = 0.0           ! 1 / 近傍セル中心間距離
    real :: wl(1:8) = 0.0            ! k軸方向フラックスの通過幅 (m)
    real, allocatable :: q(:,:,:)    ! エッジ流量4成分 (m3/s)。一時作業領域
    real, allocatable :: qm(:,:,:)   ! 質量エッジフラックス4成分 (g/s = 水流量 q ×
                                     !   風上体積濃度 cg/hg。q と同形状・同格納規約。
                                     !   一時作業領域。s%cg 確保時のみ確保。§30 W3)
    logical :: geom_ready = .false.  ! 幾何・作業領域の初期化済み(冪等口)
    logical :: initialized = .false. ! 層1(土層)側方の有効化
  end type
  type(t_gwlat) :: glt
  type(t_latlayer) :: lay1           ! 層1(土層)の係数

contains


!----------------------------------------------------------------------
! 幾何(距離・通過幅)とエッジ作業領域の初期化(冪等。層間共有)。
! diagratio は最初の呼び手の値を採用する(層1・層2で同一が前提)
!----------------------------------------------------------------------
subroutine gwflow_lateral_geom_init(g, diagratio, eps)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: diagratio
  real, intent(in) :: eps
  integer :: k
  real :: lpx, lpy, ldx, ldy, dr
  real :: l8x(1:8), l8y(1:8), w8dr(1:8)

  if (glt%geom_ready) return
  glt%eps = eps
  glt%ainv = 1.0 / (g%dx * g%dy)

  ! 8近傍の距離と通過幅(m_swflow_enc の init_weights と同一の配分則)
  dr = sqrt(g%dx**2 + g%dy**2)
  w8dr(1:8) = [ dr, g%dy, dr, g%dx, g%dx, dr, g%dy, dr ]
  forall(k=1:8) glt%rdr(k) = 1.0 / w8dr(k)
  if (g%dy > g%dx) then
    lpy = 1 - (g%dx / g%dy)**2 * diagratio
    ldy = diagratio / 2 * (g%dx / g%dy)**2
    lpx = 1 - diagratio
    ldx = diagratio / 2
  else
    lpy = 1 - diagratio
    ldy = diagratio / 2
    lpx = 1 - (g%dy / g%dx)**2 * diagratio
    ldx = diagratio / 2 * (g%dy / g%dx)**2
  end if
  l8y(1:8) = [ ldy, 0.0, ldy, lpy, lpy, ldy, 0.0, ldy ]
  l8x(1:8) = [ ldx, lpx, ldx, 0.0, 0.0, ldx, lpx, ldx ]
  forall(k=1:8) glt%wl(k) = sqrt((l8y(k) * g%dy)**2 + (l8x(k) * g%dx)**2)

  ! エッジ流量4成分(一時作業領域)。j 範囲はセル j を挟むエッジが
  ! j-1 と j にあるため下限 jsh-1(m_swflow_enc の uv/mn と同形)。
  ! 確保時 0: マスク起因で書かれないエッジは恒久 0(無フラックス)
  allocate(glt%q(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
  glt%geom_ready = .true.
end subroutine


!----------------------------------------------------------------------
! 幾何(距離・通過幅・面積逆数)の公開口(m_saltwater 等、glt を持たない
! モジュールが同一の 8 近傍幾何で独自カーネルを書くための読み取り口。
! geom_init 済みであること)
!----------------------------------------------------------------------
subroutine gwflow_lateral_geom_get(rdr, wl, ainv)
  real, intent(out) :: rdr(1:8)
  real, intent(out) :: wl(1:8)
  real, intent(out) :: ainv
  if (.not. glt%geom_ready) call par_stop("gwflow_lateral_geom_get: geometry is not initialized")
  rdr(1:8) = glt%rdr(1:8)
  wl(1:8) = glt%wl(1:8)
  ainv = glt%ainv
end subroutine


!----------------------------------------------------------------------
! 層1(土層)側方流の有効状態と係数の公開口(m_saltwater の塩水 zone が
! 同一媒体の K_sh・sy を使うため。gwflow_lateral_init より後に呼ぶこと)
!----------------------------------------------------------------------
subroutine gwflow_lateral_layer1_get(active, ksh, sy)
  logical, intent(out) :: active
  real, intent(out) :: ksh
  real, intent(out) :: sy
  active = glt%initialized
  ksh = lay1%ksh
  sy = lay1%sy
end subroutine


!----------------------------------------------------------------------
! 陽解法の安定条件の静的検査(層ごと。ヘッダ参照。h_gw <= 層厚上界)
!   thick_max: 層厚の上界(層1 = max(sd) の allreduce、層2 = d2)
!----------------------------------------------------------------------
subroutine gwflow_lateral_dtcheck(g, label, ksh, sy, thick_max, dts)
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: label
  real, intent(in) :: ksh, sy, thick_max, dts
  real :: sum_ldr, dt_lim
  integer :: k
  character(len=256) :: msg

  sum_ldr = 0.0
  do k = 1, 8
    sum_ldr = sum_ldr + glt%wl(k) * glt%rdr(k)
  end do
  if (ksh * thick_max * sum_ldr > 0.0) then
    dt_lim = 0.5 * sy * g%dx * g%dy / (ksh * thick_max * sum_ldr)
    write(msg,'(a,es10.3,a,es10.3,a)') label // ": dt limit = ", dt_lim, &
                                       " s (dts = ", dts, " s)"
    call par_info(trim(msg))
    if (dts > dt_lim) then
      call par_stop(label // ": dts exceeds the explicit stability limit " &
                    // "(reduce dt/dt_gwflow or K_sh)")
    end if
  end if
end subroutine


!----------------------------------------------------------------------
! Boussinesq 側方流の初期化(層1=土層。固有グループを自分で読む)。
! g%sd は m_gwflow_init が m_geoinfo_require_sd で確保済み。
! dts は実効時間刻み(安定条件の静的検査に使う)
!----------------------------------------------------------------------
subroutine gwflow_lateral_init(p, g, s, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: un, ios, i, j
  real :: gw_ksh_mmh, gw_eps, gw_diagratio
  real :: sdmax(1)
  namelist /list_gwflow_lateral/ gw_ksh_mmh, gw_eps, gw_diagratio

  if (s%initialized) continue  ! 引数未使用の警告を抑制

  gw_ksh_mmh = 0.0
  gw_eps = 1.0e-3
  gw_diagratio = 2.0 / (2.0 + sqrt(2.0))   ! m_swflow_enc の p_diagratio と同値

  call par_info("reading list_gwflow_lateral in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_lateral: cannot open " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow_lateral, iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_lateral: cannot read namelist")
  close(un)

  if (gw_ksh_mmh <= 0.0) call par_stop("list_gwflow_lateral: gw_ksh_mmh must be > 0")
  if (gw_eps <= 0.0) call par_stop("list_gwflow_lateral: gw_eps must be > 0")
  if (gw_diagratio < 0.0 .or. gw_diagratio > 1.0) then
    call par_stop("list_gwflow_lateral: gw_diagratio must be in [0,1]")
  end if
  if (g%sy0 <= 0.0 .or. g%sy0 > 1.0) then
    call par_stop("list_geoinfo: sy0 must be in (0,1] for gwflow lateral")
  end if
  ! 遅延確保口の呼び忘れ(m_gwflow_init の needs_sd)をここで検出する
  if (.not. allocated(g%sd)) call par_stop("gwflow_lateral: g%sd (soil depth) is not allocated")

  lay1%ksh = gw_ksh_mmh / 1000.0 / 3600.0   ! mm/h -> m/s
  lay1%sy = g%sy0
  lay1%syinv = 1.0 / g%sy0
  lay1%dbot = 0.0
  lay1%cap_const = -1.0                     ! 動的 sd·sy0
  lay1%to_surface = .true.

  call gwflow_lateral_geom_init(g, gw_diagratio, gw_eps)

  ! 水質の同伴輸送(§30 W3): s%cg があるときだけ質量エッジ配列を確保する
  ! (m_wq_init は本 init より先に走る。未確保なら経路は完全に従来どおり)
  if (allocated(s%cg) .and. .not. allocated(glt%qm)) then
    allocate(glt%qm(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
  end if

  ! 層1の安定条件(層厚上界 = max(sd) の allreduce = 決定的)
  sdmax(1) = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      sdmax(1) = max(sdmax(1), s%sd(i,j))
    end do
  end do
  call par_allreduce_max(sdmax)
  call gwflow_lateral_dtcheck(g, "gwflow_lateral", lay1%ksh, lay1%sy, sdmax(1), dts)

  glt%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! Boussinesq 側方流の計算(層1=土層。従来どおりの公開口)
!----------------------------------------------------------------------
subroutine gwflow_lateral_calc(p, g, s, it, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  real, intent(in) :: dts

  if (it < 0) continue  ! 引数未使用の警告を抑制(独自周期を持つモデル用に供給)
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  ! ステップ頭のハロ交換(ヘッダ【MPI】参照)
  call par_halo_cell(s%hg)
  call par_halo_cell(s%h)

  if (allocated(s%cg)) then
    ! 水質の同伴輸送(§30 W3)。帯界面エッジの冗長計算が風上 cg を
    ! ハロから読むため、cg も毎回交換する
    call par_halo_cell(s%cg)
    call lateral_core(g, s, s%hg, lay1, dts, cg=s%cg, rginv=s%cg_rginv)
  else
    call lateral_core(g, s, s%hg, lay1, dts)
  end if
end subroutine


!----------------------------------------------------------------------
! Boussinesq 側方流のカーネル(層非依存。1回の呼び出しで dts ぶんの更新)
!   ループ1: エッジ流量(時刻 n の状態から。書き手はハロ行 je+1 まで)
!   ループ2: 連続式+飽和超過の引き渡し(lay%to_surface で行き先分岐)
!   呼び手の責務: 対象層 hg(と to_surface 層では s%h)のハロ交換を
!   済ませてから呼ぶこと
!----------------------------------------------------------------------
subroutine lateral_core(g, s, hg, lay, dts, cg, rginv)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(inout) :: hg(1:, dcp%jsh:)
  type(t_latlayer), intent(in) :: lay
  real, intent(in) :: dts
  real, intent(inout), optional :: cg(1:, dcp%jsh:)  ! 同伴輸送するスカラー柱状量
                                                     !   (地下質量プール s%cg。§30 W3。
                                                     !   ハロ交換は呼び手の責務)
  real, intent(in), optional :: rginv                ! 移流分担率 1/R(省略時 1.0)
  integer :: i, j, k, in, jn, jt
  real :: hgwc, hgwn, hc0, hn0, hgw_up, hgw_e, gq, dh_up, dhg, capc, capn, fx
  real :: qmv, dcm, wm, rgi
  logical :: do_cg

  do_cg = present(cg)
  rgi = 1.0
  if (present(rginv)) rgi = rginv

  ! --- ループ1: エッジ流量(各成分の書き手は一意なので競合しない) ---
  !   帯界面のエッジ成分 k=1..3(行 je)はハロ行 je+1 の書き手が担う
  !   (冗長計算。全域端では行が存在せず対象外)
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) &
  !$omp   private(i, j, k, in, jn, hgwc, hgwn, hc0, hn0, hgw_up, hgw_e, gq, dh_up, capc, capn, qmv)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      ! 書き手セルの飽和帯厚と全水頭(地表湛水は層1の飽和セルのみ寄与)
      hgwc = hg(i,j) * lay%syinv
      hc0 = s%z(i,j) - s%sd(i,j) - lay%dbot + hgwc
      if (lay%to_surface) then
        capc = merge(lay%cap_const, s%sd(i,j) * lay%sy, lay%cap_const >= 0.0)
        if (hg(i,j) >= capc) hc0 = hc0 + s%h(i,j)
      end if
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        ! 乾湿は動的なので、条件を満たさない場合も必ず 0 を代入する
        gq = 0.0
        if (g%sw(i,j) <= 0 .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            hgwn = hg(in,jn) * lay%syinv
            if (hgwc > glt%eps .or. hgwn > glt%eps) then   ! 両側乾燥なら 0
              hn0 = s%z(in,jn) - s%sd(in,jn) - lay%dbot + hgwn
              if (lay%to_surface) then
                capn = merge(lay%cap_const, s%sd(in,jn) * lay%sy, lay%cap_const >= 0.0)
                if (hg(in,jn) >= capn) hn0 = hn0 + s%h(in,jn)
              end if
              if (hc0 /= hn0) then                          ! 勾配ゼロなら 0
                ! 上流側(全水頭の高い側)の飽和帯厚
                if (hc0 > hn0) then
                  hgw_up = hgwc
                else
                  hgw_up = hgwn
                end if
                if (hgw_up > glt%eps) then                  ! 上流側乾燥なら 0
                  ! 界面飽和帯厚: 算術平均を上流側でキャップ(correct_he 相当)
                  hgw_e = min(0.5 * (hgwc + hgwn), hgw_up)
                  ! エッジ流量(書き手 c から k 近傍 n に向かい正)
                  gq = lay%ksh * hgw_e * (hc0 - hn0) * glt%rdr(k) * glt%wl(k)
                  ! 過大流出の抑制: このエッジの流出で上流側が eps を
                  ! 割るなら縮小(exflux_reduction 相当。§5.1)
                  dh_up = abs(gq) * dts * glt%ainv * lay%syinv
                  if (hgw_up - dh_up <= glt%eps) then
                    gq = gq * (max(hgw_up - glt%eps, 0.0) / dh_up)
                  end if
                end if
              end if
            end if
          end if
        end if
        glt%q(k, i+die(k), j+dje(k)) = gq
        ! 質量エッジフラックス(同伴輸送。§30 W3): 風上セルの体積濃度
        ! cg/hg(時刻 n。柱状量同士の比)× 水流量 × 1/R。水が動かない
        ! エッジ(gq=0)や風上の質量が空のときは 0(動的エッジなので
        ! 必ず代入する)。gq /= 0 なら風上 hg > eps·sy > 0 が保証される
        if (do_cg) then
          qmv = 0.0
          if (gq > 0.0) then
            if (cg(i,j) > 0.0) qmv = gq * rgi * cg(i,j) / hg(i,j)
          else if (gq < 0.0) then
            if (cg(in,jn) > 0.0) qmv = gq * rgi * cg(in,jn) / hg(in,jn)
          end if
          glt%qm(k, i+die(k), j+dje(k)) = qmv
        end if
      end do
    end do
  end do
  !$omp end parallel do

  ! --- ループ2: 連続式+飽和超過分の引き渡し ---
  !   マスク・乾燥エッジは 0 が入っているため無条件に8近傍を集計できる。
  !   引き渡しは反対称適用と水位の回復(契約(1)(2)相当)
  !$omp parallel do schedule(static) private(i, j, k, dhg, capc, fx, dcm, wm)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      ! 8近傍の流出入を集計(中心から近傍に向かい正 → 流出の総和)
      dhg = 0.0
      do k = 1, 8
        dhg = dhg + sign_e(k) * glt%q(ke(k), i+die(k), j+dje(k))
      end do
      hg(i,j) = hg(i,j) - dhg * dts * glt%ainv
      ! 同伴輸送の発散(§30 W3。水と同じ反対称集計 = 柱状量の総和保存。
      ! 複数エッジ同時流出の微小な行き過ぎは水と同じく許容 — 微小負値は
      ! 次ステップの風上ガード(cg > 0)で自己回復する)
      if (do_cg) then
        dcm = 0.0
        do k = 1, 8
          dcm = dcm + sign_e(k) * glt%qm(ke(k), i+die(k), j+dje(k))
        end do
        cg(i,j) = cg(i,j) - dcm * dts * glt%ainv
      end if
      ! 飽和超過分の引き渡し(層1: s%h へ=§3.2.1/§8 決定。層2: s%hg へ。
      ! 層2超過で層1も溢れる場合は層1の容量判定が次の機会に地表へ渡す
      ! のではなく、ここで直列に処理して湧出の連鎖を同一ステップで閉じる)
      capc = merge(lay%cap_const, s%sd(i,j) * lay%sy, lay%cap_const >= 0.0)
      if (hg(i,j) > capc) then
        fx = hg(i,j) - capc
        hg(i,j) = capc
        ! 湧出同伴(§30 W3): 超過水量 fx に同率移動 ×1/R を同伴して
        ! 記録場 s%fxs へ移す(m_wq が読んで地表 cq へ還元しゼロ戻し。
        ! 分母は超過処理前の貯留 = capc + fx。柱状量同士の同率移動)
        if (do_cg) then
          if (cg(i,j) > 0.0) then
            wm = rgi * cg(i,j) * (fx / (capc + fx))
            cg(i,j) = cg(i,j) - wm
            s%fxs(i,j) = s%fxs(i,j) + wm
          end if
        end if
        if (lay%to_surface) then
          s%h(i,j) = s%h(i,j) + fx
          s%e(i,j) = s%z(i,j) + s%h(i,j)
        else
          s%hg(i,j) = s%hg(i,j) + fx
          ! 層1の容量超過は地表へ(層1と同じ規則)
          capc = s%sd(i,j) * g%sy0
          if (s%hg(i,j) > capc) then
            fx = s%hg(i,j) - capc
            s%hg(i,j) = capc
            s%h(i,j) = s%h(i,j) + fx
            s%e(i,j) = s%z(i,j) + s%h(i,j)
          end if
        end if
      end if
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! 管路連続体層の水頭(折れ線。ヘッダ【管路連続体層カーネル】参照)
!   不圧枝: H = zbot + hgc/sy_c(hgc <= cap)
!   被圧枝: H = zbot + cap/sy_c + (hgc - cap)/sy_slot(疑似スロット)
!   交換項(m_gwflow_conduit)からも使うため公開の純関数とする
!----------------------------------------------------------------------
pure real function conduit_head(hgcv, capv, zbotv, syic, syis)
  real, intent(in) :: hgcv           ! 貯留水量 (m 柱状)
  real, intent(in) :: capv           ! 貯留容量 (m 柱状)
  real, intent(in) :: zbotv          ! 水頭底標高 (m)
  real, intent(in) :: syic           ! 不圧枝の 1/sy_c(セル別値。§46.5 (5))
  real, intent(in) :: syis           ! 被圧枝の 1/sy_slot(同上)
  if (hgcv <= capv) then
    conduit_head = zbotv + hgcv * syic
  else
    conduit_head = zbotv + capv * syic + (hgcv - capv) * syis
  end if
end function


!----------------------------------------------------------------------
! 管路連続体層の側方流カーネル(1回の呼び出しで dts ぶんの更新)
!   構造は lateral_core と同一(ループ1: 所有エッジ 4 成分、書き手は
!   ハロ行 je+1 まで冗長計算 / ループ2: 発散)。相違はヘッダ参照。
!   cap <= 0 のセル(管路なし)はエッジ 0 を書き、貯留も更新しない。
!   呼び手の責務: hgc のハロ交換を済ませてから呼ぶこと
!----------------------------------------------------------------------
subroutine conduit_core(g, hgc, cl, dts)
  type(t_geoinfo), intent(in) :: g
  real, intent(inout) :: hgc(1:, dcp%jsh:)
  type(t_conduitlayer), intent(in) :: cl
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt
  real :: capc, capn, hc0, hn0, fillc, filln, fill_e, fill_up, hg_up
  real :: cndk, dh, gq, dh_up, dhg

  ! --- ループ1: エッジ流量(各成分の書き手は一意なので競合しない) ---
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) &
  !$omp   private(i, j, k, in, jn, capc, capn, hc0, hn0, fillc, filln, &
  !$omp           fill_e, fill_up, hg_up, cndk, dh, gq, dh_up)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      capc = cl%cap(i,j)
      if (capc > 0.0) then
        hc0 = conduit_head(hgc(i,j), capc, cl%zbot(i,j), &
                           cl%syinvc(i,j), cl%syinv_slot(i,j))
        fillc = min(hgc(i,j) / capc, 1.0)
      else
        hc0 = 0.0
        fillc = 0.0
      end if
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        ! 乾湿は動的なので、条件を満たさない場合も必ず 0 を代入する
        ! (q は層間共有スクラッチ。前の層の値を残してはならない)
        gq = 0.0
        if (capc > 0.0 .and. g%sw(i,j) <= 0 .and. g%x(in,jn) > 0) then
          capn = cl%cap(in,jn)
          if (g%sw(in,jn) <= 0 .and. capn > 0.0) then
            cndk = cl%cnd(k, i+die(k), j+dje(k))
            if (cndk > 0.0) then
              if (hgc(i,j) > cl%eps .or. hgc(in,jn) > cl%eps) then  ! 両側乾燥なら 0
                hn0 = conduit_head(hgc(in,jn), capn, cl%zbot(in,jn), &
                                   cl%syinvc(in,jn), cl%syinv_slot(in,jn))
                if (hc0 /= hn0) then                                ! 勾配ゼロなら 0
                  filln = min(hgc(in,jn) / capn, 1.0)
                  ! 上流側(水頭の高い側)の貯留量と充満率
                  if (hc0 > hn0) then
                    hg_up = hgc(i,j)
                    fill_up = fillc
                  else
                    hg_up = hgc(in,jn)
                    fill_up = filln
                  end if
                  if (hg_up > cl%eps) then                          ! 上流側乾燥なら 0
                    ! 界面充満率: 算術平均を上流側でキャップ(correct_he 相当)
                    fill_e = min(0.5 * (fillc + filln), fill_up)
                    dh = hc0 - hn0
                    ! エッジ流量(書き手 c から k 近傍 n に向かい正)
                    if (cl%fluxlaw == 2) then
                      if (abs(dh) >= cl%eps_h) then
                        gq = cndk * fill_e * sign(sqrt(abs(dh) * glt%rdr(k)), dh)
                      else
                        ! 線形化枝(|ΔH| < eps_h。eps_h で連続接続)
                        gq = cndk * fill_e * dh * sqrt(glt%rdr(k) / cl%eps_h)
                      end if
                    else
                      gq = cndk * fill_e * dh * glt%rdr(k)
                    end if
                    ! 過大流出の抑制: このエッジの流出で上流側が eps を
                    ! 割るなら縮小(lateral_core と同じ)
                    dh_up = abs(gq) * dts * glt%ainv
                    if (hg_up - dh_up <= cl%eps) then
                      gq = gq * (max(hg_up - cl%eps, 0.0) / dh_up)
                    end if
                  end if
                end if
              end if
            end if
          end if
        end if
        glt%q(k, i+die(k), j+dje(k)) = gq
      end do
    end do
  end do
  !$omp end parallel do

  ! --- ループ2: 連続式(発散)---
  !   容量超過はクランプ・排出せず層内に保持する(水頭関数の被圧枝が
  !   立ち上がる = Preissmann スロット連続体版。飽和超過の引き渡しなし)
  !$omp parallel do schedule(static) private(i, j, k, dhg)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (cl%cap(i,j) <= 0.0) cycle
      dhg = 0.0
      do k = 1, 8
        dhg = dhg + sign_e(k) * glt%q(ke(k), i+die(k), j+dje(k))
      end do
      hgc(i,j) = hgc(i,j) - dhg * dts * glt%ainv
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! セル別コンダクタンス密度 dens (m2/s。帯+ハロ) からエッジ別
! コンダクタンス cl%cnd を構築する(通過幅配分は側方 Darcy 流と同一の
! diagratio 規約。gwflow_lateral_geom_init の後に呼ぶこと)
!   cnd_k = min(両セルの密度) · wl_k
!   min 規約: 管路は両セルに存在して初めて連続する(片側 0 なら無結合)。
!   将来の GIS 前処理(4 成分エッジマップの直接入力)はこの構築を
!   置き換える形で追加する(gwconduit_plan.md §9)。
!   書き手はループ1と同じ jt = je+1 まで(所有エッジの完全被覆。
!   dens は帯+ハロ jsh:jeh に有効値が要る = par_scatter_cell の配布規約)
!----------------------------------------------------------------------
subroutine conduit_build_cnd(g, dens, cl)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: dens(1:, dcp%jsh:)
  type(t_conduitlayer), intent(inout) :: cl
  integer :: i, j, k, in, jn, jt
  real :: cv

  if (.not. glt%geom_ready) call par_stop("conduit_build_cnd: geometry is not initialized")
  if (.not. allocated(cl%cnd)) then
    allocate(cl%cnd(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
  end if
  jt = min(dcp%je + 1, dcp%jeh)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        cv = 0.0
        if (g%sw(i,j) <= 0 .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            cv = min(dens(i,j), dens(in,jn)) * glt%wl(k)
          end if
        end if
        cl%cnd(k, i+die(k), j+dje(k)) = cv
      end do
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 陽解法の安定条件の静的検査(管路連続体層)
!   水頭勾配の最大感度は sqrt 則では線形化枝(dq/dΔH = C·sqrt(rdr/eps_h))、
!   線形則では C·rdr。充満率 <= 1、水頭感度 dH/dhgc <= max(1/sy) より
!     dt <= 0.5 * dx*dy / (max(1/sy) * max_cell Σ_k cnd_k · fac_k)
!   cnd はエッジ別なのでセルごとに 8 近傍の入射エッジ係数を集計し、
!   最大値を allreduce_max(順序不変で決定的)する
!----------------------------------------------------------------------
subroutine gwflow_conduit_dtcheck(g, label, cl, dts, nsub)
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: label
  type(t_conduitlayer), intent(in) :: cl
  real, intent(in) :: dts
  integer, intent(out) :: nsub       ! dts を安定に消化するサブサイクル数
                                     ! (§46.5 (4)。dt_lim は allreduce_max
                                     !  由来で全ランク同一 → nsub も同一)
  integer :: i, j, k
  real :: fac(1:8), sums, summax(1), dt_lim
  character(len=256) :: msg

  do k = 1, 8
    if (cl%fluxlaw == 2) then
      fac(k) = sqrt(glt%rdr(k) / cl%eps_h)
    else
      fac(k) = glt%rdr(k)
    end if
  end do
  summax(1) = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (cl%cap(i,j) <= 0.0) cycle
      sums = 0.0
      do k = 1, 8
        sums = sums + cl%cnd(ke(k), i+die(k), j+dje(k)) * fac(k)
      end do
      ! セル別の水頭感度 max(1/sy) を掛けてから最大化する(§46.5 (5)。
      ! 一様 sy では乗算の単調性により旧「全域 max(1/sy)×max Σ」と
      ! ビット同一。不均質では過大にペアリングしない分だけ上界が緩む)
      sums = sums * max(cl%syinvc(i,j), cl%syinv_slot(i,j))
      summax(1) = max(summax(1), sums)
    end do
  end do
  call par_allreduce_max(summax)
  nsub = 1
  if (summax(1) > 0.0) then
    dt_lim = 0.5 * g%dx * g%dy / summax(1)
    ! dts が上界を超える場合は par_stop でなくサブサイクル数を返す
    ! (§46.5 (4)。上限の検査は呼び手 = namelist を持つ側が行う)
    if (dts > dt_lim) nsub = ceiling(dts / dt_lim)
    write(msg,'(a,es10.3,a,es10.3,a,i0,a)') label // ": dt limit = ", dt_lim, &
        " s (dts = ", dts, " s, subcycles = ", nsub, ")"
    call par_info(trim(msg))
  end if
end subroutine


!----------------------------------------------------------------------
! Boussinesq 側方流の破棄(無履歴のため私有保存なし。ヘッダ【リスタート】)
!----------------------------------------------------------------------
subroutine gwflow_lateral_dispose(p)
  type(t_sysparam), intent(in) :: p
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (allocated(glt%q)) deallocate(glt%q)
  if (allocated(glt%qm)) deallocate(glt%qm)
  glt%geom_ready = .false.
  glt%initialized = .false.
end subroutine

end module
