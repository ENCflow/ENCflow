module list_enc
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_enc
  public :: list_enc_read


  type t_list_enc
    integer :: f_gravity_correction = 2       ! 急勾配の補正(0: なし, 1: 有効重力 g cos²θ,
                                              !   2: 1 + 斜面に沿う摩擦・流砂のせん断 = 既定。
                                              !   2026-11-05 に 1 から変更。developer.md §93。
                                              !   3: 2 + 水面の勾配の項に Yuan ら 2016 の g′。試作。§100)
    integer :: f_exflux_reduction = 1         ! reduction of excessive flux
    integer :: f_hcap_upwind = 1              ! セル境界水深 (0:両側平均, 1:上流側水深で
                                              !   頭打ち(既定), 2:上流側水深そのもの)
    integer :: f_adaptive_runge = 1           ! 適応的ルンゲクッタ
    integer :: f_friction_fastmath = 0        ! 摩擦項計算の高速化 (0:厳密,
                                              !   1~5:テーブル近似。大きいほど粗く速い)
    integer :: f_advection_scheme = 3         ! 移流項のスキーム (1: セル中心勾配(旧既定。非保存形),
                                              !   2: 運動量保存形・1次風上, 3: 運動量保存形+MUSCL(既定。
                                              !   2026-10-03 に 1 から昇格。developer.md §68.19))
    integer :: f_scalar_scheme = 3            ! スカラー輸送(advect_scalar: 浮遊砂・水質・塩水層・
                                              !   流木・瓦礫)の移流スキーム (1: 1 次風上(旧既定),
                                              !   3: リンクごとの MUSCL + van Leer 面値再構成(既定。
                                              !   2026-10-13 に 1 から昇格。developer.md §78))
    integer :: f_advection_donor = 4          ! 運動量保存形移流(スキーム 2, 3)の風上供給元
                                              !   (0:線 k 上の湿潤セル(2026-11-09 までの既定),
                                              !   3(2026-11-09 に 0 から昇格。2026-11-21 までの
                                              !   既定):線 k 上の供給元の
                                              !   リンクが運ぶ水が、面のセルへの最大の流入リンクの
                                              !   p_adv_donor_eps 倍に満たず、供給元の水深も面の
                                              !   セルの水深の p_adv_donor_eps 倍に満たない(薄い)
                                              !   とき、その比に応じて風上値を u_e へ寄せる。側方面の平行リンク
                                              !   と開口率の乾湿判定も、dd 未満では水深に比例して
                                              !   中立へ寄せる連続な重みにする。河道マスク不要)。
                                              !   3 は供給元が河岸の薄い水膜のとき、その乾湿判定
                                              !   でハイドログラフが跳ねる問題の対策
                                              !   (developer.md §102。横流入・渦・壁の検定は 0 と
                                              !   同じ)。4(既定。2026-11-21 に 3 から昇格): 3 に
                                              !   加えて、面の流束を、面のセルへ
                                              !   入ってくる連結ごとの流れに分け、線 k 上の供給元の
                                              !   流速を、その連結が代表する流れの分だけに掛ける
                                              !   (供給元が、深くてもほとんど水を運ばない岸・淵の
                                              !   セルのとき、その遅い流速を面の全量に掛けない。
                                              !   test/stairbank。developer.md §113・§114。ENCflow
                                              !   独自。f_advection_bend = 2・f_advection_lateral = 2・
                                              !   f_dry_head_cap = 4 と組み合わせて使う)。
                                              !   1(河道セル間のエッジの供給元を河道セルに
                                              !   限る。§68.18)と 2(全流入リンクの流量で重み付け)
                                              !   は 2026-11-07 に廃止(指定すると停止)
    integer :: f_advection_bend = 2           ! 運動量保存形移流(スキーム 2, 3)で、流向面の風上側の
                                              !   供給元が壁・乾床(f_advection_donor = 3・4 では薄い
                                              !   水膜も)のときの風上値 (0:検査体積自身の流速 u_e
                                              !   (2026-11-15 までの既定。壁は運動量を供給しない。
                                              !   §68.8), 1:面のセルへ実際に流入する水が、この辺の
                                              !   幅で、流入時の水深のまま流れたときの流速(2026-11-15
                                              !   に 0 から昇格。2026-11-21 までの既定)。
                                              !   流入の線が面のセルの先の同じ水体へ続いている
                                              !   ときは、流入の水深をこの辺の水深で下から止めて
                                              !   数える)。0 は屈曲の直後の辺が上流の流れの運動量を
                                              !   受け取らず、屈曲が急な加速部(池の出口・段落ちの
                                              !   直前)に重なると流れが加速しすぎ、段落ちの足元に
                                              !   重なると落ちてきた流れの運動量を失う。1 は経路に
                                              !   沿う水深の変化の分の加減速を入れる(等流の屈曲は
                                              !   0 と同じ。ENCflow 独自。developer.md §110)。
                                              !   2(既定。2026-11-21 に 1 から昇格): 1 に加えて、
                                              !   同じ面で、辺の流速が「面のセルへ
                                              !   到着した水の速さ」を上回る分の加速を、エネルギー
                                              !   水頭を保存する形の移流項 (u_e² − a²)/(2L) で
                                              !   数える(経路の値の項とは、大きい方)。流入が
                                              !   合わさる面のセルや、流出の一部だけが出ていく辺が、
                                              !   入ってきた水のエネルギーを超えて加速しない
                                              !   (test/stairbank。developer.md §113・§114。ENCflow 独自)
    integer :: f_advection_lateral = 2        ! 運動量保存形移流(スキーム 2, 3。f_advection_donor = 3・4)の
                                              !   側方面で、横から入る水の扱い (0:平行リンクの流速
                                              !   (乾いていれば中立。dd 以上の水膜があれば、その
                                              !   流速。2026-11-16 までの既定), 1:平行リンクが、面を
                                              !   横切って入ってくる水に比べて p_adv_donor_eps 倍
                                              !   より薄い水膜のときは代表させず、辺の線に沿う
                                              !   流れへ別の向きから入る水の、辺の向きの運動量の
                                              !   不足 (1 − cos θ) u_e を数える。斜めエッジの
                                              !   側方面の開口率も、同じ薄さの判定で数える(2026-11-16
                                              !   に 0 から昇格。2026-11-21 までの既定))。
                                              !   0 は、合流の損失を、岸が濡れているときだけ数え、
                                              !   雨で濡れた岸に接する河道を減速する
                                              !   (test/tjunction・test/wetbank)。1 は、岸の濡れに
                                              !   よらず数える(直角の合流で、運動量の理論の
                                              !   6〜8 割の堰上げ。ENCflow 独自。developer.md
                                              !   §110.25)。2(既定。2026-11-21 に 1 から昇格): 1 に
                                              !   加えて、平行リンクの単位幅流量が、
                                              !   入ってくる水の出どころのセルの、辺の向きの単位幅
                                              !   流量の 2 倍を超えるとき、その比で、平行リンクの
                                              !   流速を使う度合いを下げる(速い平行リンクの運動量を、
                                              !   遅い水が入ってくる辺へ持ち込まない。developer.md
                                              !   §113・§114。ENCflow 独自)。f_advection_donor が 3・4 で
                                              !   なければ、1・2 は効かない(0 と同じ)
    integer :: f_dry_head_cap = 4             ! 高い地盤へ向かうエッジ水深のエネルギー頭による
                                              !   頭打ち (0:なし, 1:受け手が乾燥のとき(2026-11-13
                                              !   までの既定), 2:1 に加えて、受け手が濡れていても、
                                              !   その地盤が送り手の水位より高いとき(2026-11-16
                                              !   までの既定), 3:登る辺を、受け手の乾湿によらず、
                                              !   入ってくる流れを数えて頭打ち(2026-11-16 に 2 から
                                              !   昇格。2026-11-21 までの既定), 4:3 の入ってくる
                                              !   流れの速さを、送り手のセルの平均流速で止める(既定。
                                              !   2026-11-21 に 3 から昇格))。1・2 は
                                              !   he ≤ max(η + u_n²/2g − z_受け手, 0) とし、
                                              !   水面+速度水頭より高い地盤へは流さない
                                              !   (developer.md §68.16)。2 では、薄く濡れた河岸・
                                              !   谷壁へ、水位の低い河道の水が登らない(§108。
                                              !   水位が受け手の地盤のすぐ下にあるときは、頭打ちの
                                              !   値を、1 ステップで水位が境目をまたがない勾配で
                                              !   ゆるめる = §108.9)。3 は、登る辺(受け手の地盤が
                                              !   送り手の地盤より高い辺)を、受け手の乾湿によらず
                                              !   he ≤ max(w·調和平均, σ + v_h, 0) で頭打ち
                                              !   する(σ = 送り手の水位 − 受け手の地盤、v_h =
                                              !   辺の流速の速度水頭と、送り手へ同じ線に沿って入って
                                              !   くる流れの速度水頭(射流では、同じ流量の限界流の
                                              !   比エネルギーから送り手の水深を引いた分)の
                                              !   大きい方、w = clamp(σ/h_受, 0, 1)。河道の水が
                                              !   岸へあふれ始める時刻と量が時間刻みに依らない。
                                              !   ENCflow 独自。§110.24・§110.30)。4 は、3 の
                                              !   「送り手へ入ってくる流れ」の速さを、送り手のセルの
                                              !   平均流速の、辺の向きの成分で上から止める(1 セル
                                              !   幅の階段状の河道の対角の連結の流速を、そのまま
                                              !   速度水頭に数えると、乗り上げの高さを 2 倍に
                                              !   数える。一様な流れと、まっすぐな河道では 3 と同じ。
                                              !   test/stairbank。developer.md §113・§114。ENCflow 独自)
    integer :: f_opening_dynamic = 3          ! 塞がれた開口の動的振り替え (0:なし,
                                              !   1:河道セル間のエッジのみ(河道マスク fn_rw が
                                              !   なければ対象エッジがなく無効。2026-10-18 までの
                                              !   既定), 2:全エッジ(2026-10-31 までの既定。
                                              !   §68.38), 3:全エッジで、塞がりを局所の平面からの
                                              !   盛り上がりで測る(一様な斜面を壁と数えない。
                                              !   既定。§68.41))。水面より高い隣接地盤で塞がれた
                                              !   斜め/軸の通過幅シェアを開いたエッジへ毎ステップ
                                              !   振り替える(developer.md §68.14)
    integer :: f_inflow_edge = 0              ! 区間流入の外縁セルに接するエッジの扱い
                                              !   (0:接するエッジすべての移流項を 0(既定),
                                              !   1:区間の内側へ向かうエッジだけ移流項を 0,
                                              !   2:1 に加えて、そのエッジの流速を流入セルの
                                              !   エネルギー水頭で頭打ち)。1・2 は区間の端から
                                              !   横へ落ちる流れや流入直下のジェットがエネルギーを
                                              !   作るのを抑える(developer.md §68.40)
    integer :: f_rivermouth_drop = 0          ! 河口から海へ段落ち
    integer :: f_diffusion_term = 0           ! 拡散項の計算 (0:無効, 1:定数, 2:ゼロ方程式)
    real :: p_diagratio = 2 / (2 + sqrt(2.))  ! ratio of diagonal component
    real :: p_adv_upwind_index = 0.5          ! 移流項の風上化指数 (0~1。
                                              !   0:中心差分, 1:1次精度風上差分)
    real :: p_adv_donor_eps = 0.1             ! f_advection_donor = 3・4 のしきい値 ε (0 < ε ≤ 1。
                                              !   線 k の供給元のリンクの実流量が面のセルへの
                                              !   最大の流入リンクの ε 倍未満で、供給元の水深も
                                              !   面のセルの水深の ε 倍未満なら、重み
                                              !   max(r/ε, (h_d/h_c)/ε) で風上値を u_e へ寄せる。
                                              !   経験値。developer.md §102)。f_advection_bend = 1・2
                                              !   では、面のセルへの流入が流出の ε 倍未満のとき、
                                              !   その比で経路の値を u_e へ寄せるのにも、流入の線の
                                              !   先のセルが同じ水体か(水深が面のセルの ε 倍以上か)の
                                              !   判定にも使う(§110)。f_advection_donor = 4・
                                              !   f_advection_bend = 2・f_advection_lateral = 2 では、
                                              !   分ける元・比べる元の流量が取るに足らない大きさか
                                              !   (相手の流量の ε 倍に満たないか)のしきい値にも
                                              !   使う(§113.9)
    real :: p_adprunge_thresh = 1.5           ! threshold of adaptive Runge-Kutta (1.1~)
    real :: p_diffusion_nu = 0.0              ! 拡散項の動粘性係数 (m2/s。モデル2では
                                              !   加算のバックグラウンド粘性)
    real :: p_diffusion_alpha = 0.41 / 6      ! ゼロ方程式モデルの係数 α (ν=ν0+α·u*·h。
                                              !   既定はカルマン定数/6 = Elder 型)
    ! --- 非静水圧(1 層 NH)補正(研究用。docs/nonhydrostatic_plan.md、developer.md §69) ---
    integer :: f_nonhydrostatic = 0           ! 0: 静水圧(既定), 1: 1 層 NH 補正(β = h²/4)
    real :: nh_hmin = 0.1                     ! この水深未満のセルは静水圧に退化 (m)
    integer :: nh_solver = 2                  ! 反復ソルバ (1: Jacobi, 2: CG(既定))
    integer :: nh_itmax = 500                 ! 反復回数の上限
    real :: nh_tol = 1.0e-6                   ! 相対収束判定(Jacobi: 残差最大/右辺最大、CG: ||r||/||b||)
    integer :: f_nh_adaptive = 0              ! 活性集合 (0: NH マスク内全域で解く, 1: 検出セル+縁だけ)
    integer :: nh_detector = 1                ! 検出量 (1: 分散型 χ = |βDa*|/(|a*|+|βDa*|), 2: 絶対型 |βDa*|/g)
    real :: nh_chi_on = 0.06                  ! 検出の閾値(χ > nh_chi_on のセルが種)
    integer :: nh_margin = 0                  ! 種のまわりの縁の幅(セル数。0: 2H/Δx から自動)
    real :: nh_amin = 1.0e-5                  ! 検出の下限 |βDa*| (m/s²)。未満は種にしない(丸め誤差の前駆波を除く)
    real :: nh_arel = 1.0e-3                  ! 検出の相対下限: |βDa*| がそのステップの領域最大の nh_arel 倍未満なら種にしない
    integer :: f_nh_breaking = 0              ! 砕波スイッチ (0: なし, 1: 水面上昇速度 ∂η/∂t > α√(gh) のセルを静水圧に)
    real :: nh_break_alpha = 0.6              ! 砕波開始の閾値 α(SWASH の既定 0.6)
    real :: nh_break_beta = 0.3               ! 砕波セルに接するセルの閾値 β(前線の伝播。SWASH の既定 0.3)
    integer :: nh_break_type = 3              ! 砕波の判定量 (1: 水面上昇速度 ∂η/∂t/√(gh) > α, 2: フルード数 |V|/√(gh) > nh_break_fr,
                                              !   3: 水面勾配 |∇η| > nh_break_slope(既定))
    real :: nh_break_fr = 0.6                 ! フルード数判定の閾値
    real :: nh_break_slope = 0.3              ! 水面勾配判定の閾値(8 近傍の最大 |Δη|/距離)
    integer :: nh_break_margin = 0            ! 砕波セルの周りを静水圧にする縁の幅(セル数。0: 2H/Δx から自動)
    integer :: nh_bc_margin = 0               ! 強制境界(水位規定セル・区間流入/自由流出/放射の面)から静水圧のままにする
                                              !   セル数(0: 2H/Δx から自動)。規定流束と射影の干渉を避ける
    real :: nh_break_visc = 0.0               ! 砕波域の渦粘性係数 δ_b²(0: なし。1.44 = Kennedy et al. 2000 相当。
                                              !   ν_b = nh_break_visc·B·h·√(gh)·|∇η| を運動量の拡散項に加える。plan §15)
    real :: wf_break_visc = 0.0               ! 沿岸の波浪場の砕波による水平混合の係数 M(0: なし。1.0 = XBeach の nuhfac の
                                              !   既定)。ν_w = M·h·(D/ρ)^(1/3)(Battjes 1975。D はローラーの散逸)を運動量の
                                              !   拡散項に加える。fn_wavefield が必須(§90)
    integer :: f_nh_slope = 0                 ! 底面勾配項 (0: 平坦床の線形 NH(Version 1), 1: 底面の運動学条件 w_b = u·∇z_b と
                                              !   圧力項 (φ/h)∇(h+2z_b) を含む(Version 2))
    integer :: f_nh_bottom = 0                ! 動く底面の加速度項 (0: なし, 1: 底面の鉛直加速度 z̈_b を NH の源項に加える。
                                              !   bedslide・geomorph・lavaflow・API の z 更新に効く。plan §16)
  end type


contains
 
!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! ENC設定ファイルを読み込む　
!----------------------------------------------------------------------
subroutine list_enc_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_enc), intent(inout) :: list
  integer :: f_gravity_correction       ! 重力の補正
  integer :: f_exflux_reduction         ! reduction of excessive flux
  integer :: f_hcap_upwind              ! 上流側水深によるセル境界水深の制限
  integer :: f_adaptive_runge           ! 適応的簡易ルンゲクッタ
  integer :: f_friction_fastmath        ! 摩擦項計算の高速化
  integer :: f_advection_scheme         ! 移流項のスキーム
  integer :: f_opening_dynamic          ! 塞がれた開口の動的振り替え (0:なし, 1:河道, 2:全域)
  integer :: f_dry_head_cap             ! 乾燥セルへのエッジ水深のエネルギー頭による頭打ち (0〜4。
                                        !   4(既定):3 の入ってくる流れの速さを送り手の平均流速で止める)
  integer :: f_advection_donor          ! 運動量保存形移流の風上供給元 (0:線 k 上の湿潤セル,
                                        !   3:線 k の薄い供給元を u_e へ寄せ、側方面の乾湿判定を連続に,
                                        !   4(既定):3 + 流れごとの重み。1・2 は廃止)
  integer :: f_advection_bend           ! 供給元が壁・乾床の流向面の風上値 (0:u_e, 1:経路の値。§110,
                                        !   2(既定):1 + 到着した水の速さからのエネルギー形の加速。§113)
  integer :: f_advection_lateral        ! 側方面で横から入る水の扱い (0:平行リンクの流速, 1:代表性と
                                        !   合流の不足分。§110.25, 2(既定):1 + 流量の比。§113)
  integer :: f_inflow_edge              ! 区間流入の外縁セルに接するエッジの扱い (0/1/2)
  integer :: f_scalar_scheme            ! スカラー輸送の移流スキーム (1:1次風上, 3:MUSCL)
  integer :: f_rivermouth_drop          ! 河口から海へ段落ち
  integer :: f_diffusion_term           ! 拡散項の計算 (0:無効, 1:定数, 2:ゼロ方程式)
  real :: p_diagratio                   ! ratio of diagonal component
  real :: p_adv_upwind_index            ! upwind index of advection term
  real :: p_adv_donor_eps               ! f_advection_donor = 3・4 のしきい値 ε
  real :: p_adprunge_thresh             ! threshold of adaptive Runge-Kutta (1.1~)
  real :: p_diffusion_nu                ! 拡散項の動粘性係数 (m2/s)
  real :: p_diffusion_alpha             ! ゼロ方程式モデルの係数 α
  integer :: f_nonhydrostatic           ! 非静水圧補正 (0:静水圧, 1:1 層 NH)
  real :: nh_hmin                       ! NH を適用する最小水深 (m)
  integer :: nh_solver                  ! NH の反復ソルバ (1:Jacobi, 2:CG)
  integer :: nh_itmax                   ! NH の反復回数上限
  real :: nh_tol                        ! NH の相対収束判定
  integer :: f_nh_adaptive              ! NH の活性集合 (0:全域, 1:検出セル+縁)
  integer :: nh_detector                ! NH の検出量 (1:分散型 χ, 2:絶対型)
  real :: nh_chi_on                     ! NH の検出閾値
  integer :: nh_margin                  ! NH の縁の幅(セル数。0:自動)
  real :: nh_amin                       ! NH の検出下限 (m/s²)
  real :: nh_arel                       ! NH の検出の相対下限
  integer :: f_nh_breaking              ! NH の砕波スイッチ (0/1)
  real :: nh_break_alpha                ! 砕波開始の閾値
  real :: nh_break_beta                 ! 砕波前線の伝播の閾値
  integer :: nh_break_type              ! 砕波の判定量 (1:∂η/∂t, 2:フルード数)
  real :: nh_break_fr                   ! フルード数判定の閾値
  real :: nh_break_slope                ! 水面勾配判定の閾値
  integer :: nh_break_margin            ! 砕波セルの縁の幅(セル数)
  real :: nh_break_visc                 ! 砕波域の渦粘性係数 δ_b²
  real :: wf_break_visc                 ! 波浪場の砕波による水平混合の係数 M
  integer :: nh_bc_margin               ! 強制境界から静水圧のままにするセル数
  integer :: f_nh_slope                 ! NH の底面勾配項 (0/1)
  integer :: f_nh_bottom                ! NH の動く底面の加速度項 (0/1)
  integer :: un
  integer :: ios
  character(len=1024) :: iom

  namelist /list_enc/ f_gravity_correction, f_exflux_reduction, f_hcap_upwind, &
                      f_friction_fastmath, f_advection_scheme, &
                      f_rivermouth_drop, f_opening_dynamic, f_dry_head_cap, f_advection_donor, &
                      f_advection_bend, f_advection_lateral, f_inflow_edge, f_scalar_scheme, &
                      f_adaptive_runge, p_diagratio, p_adv_upwind_index, p_adv_donor_eps, p_adprunge_thresh, &
                      f_diffusion_term, p_diffusion_nu, p_diffusion_alpha, &
                      f_nonhydrostatic, nh_hmin, nh_solver, nh_itmax, nh_tol, &
                      f_nh_adaptive, nh_detector, nh_chi_on, nh_margin, nh_amin, nh_arel, &
                      f_nh_breaking, nh_break_alpha, nh_break_beta, nh_break_type, nh_break_fr, &
                      nh_break_slope, nh_break_margin, nh_break_visc, nh_bc_margin, f_nh_slope, &
                      f_nh_bottom, wf_break_visc

  f_gravity_correction = list%f_gravity_correction 
  f_exflux_reduction = list%f_exflux_reduction 
  f_hcap_upwind = list%f_hcap_upwind 
  f_adaptive_runge = list%f_adaptive_runge 
  f_friction_fastmath = list%f_friction_fastmath 
  f_advection_scheme = list%f_advection_scheme
  f_rivermouth_drop = list%f_rivermouth_drop
  f_opening_dynamic = list%f_opening_dynamic
  f_dry_head_cap = list%f_dry_head_cap
  f_advection_donor = list%f_advection_donor
  f_advection_bend = list%f_advection_bend
  f_advection_lateral = list%f_advection_lateral
  f_inflow_edge = list%f_inflow_edge
  f_scalar_scheme = list%f_scalar_scheme
  f_diffusion_term = list%f_diffusion_term
  p_diffusion_alpha = list%p_diffusion_alpha
  p_diagratio = list%p_diagratio
  p_adv_upwind_index = list%p_adv_upwind_index
  p_adv_upwind_index = list%p_adv_upwind_index
  p_adv_donor_eps = list%p_adv_donor_eps
  p_adprunge_thresh = list%p_adprunge_thresh
  p_diffusion_nu = list%p_diffusion_nu
  f_nonhydrostatic = list%f_nonhydrostatic
  nh_hmin = list%nh_hmin
  nh_solver = list%nh_solver
  nh_itmax = list%nh_itmax
  nh_tol = list%nh_tol
  f_nh_adaptive = list%f_nh_adaptive
  nh_detector = list%nh_detector
  nh_chi_on = list%nh_chi_on
  nh_margin = list%nh_margin
  nh_amin = list%nh_amin
  nh_arel = list%nh_arel
  f_nh_breaking = list%f_nh_breaking
  nh_break_alpha = list%nh_break_alpha
  nh_break_beta = list%nh_break_beta
  nh_break_type = list%nh_break_type
  nh_break_fr = list%nh_break_fr
  nh_break_slope = list%nh_break_slope
  nh_break_margin = list%nh_break_margin
  nh_break_visc = list%nh_break_visc
  wf_break_visc = list%wf_break_visc
  nh_bc_margin = list%nh_bc_margin
  f_nh_slope = list%f_nh_slope
  f_nh_bottom = list%f_nh_bottom

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  call par_info("reading list_enc in "//trim(p%fn_enc))
  open(newunit=un, file=trim(p%fn_enc), status='old')
  read(un, nml=list_enc, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_enc: failed to read namelist: "//trim(iom))
  close(un)

  list%f_gravity_correction = f_gravity_correction 
  list%f_exflux_reduction = f_exflux_reduction 
  list%f_hcap_upwind = f_hcap_upwind 
  list%f_adaptive_runge = f_adaptive_runge 
  list%f_friction_fastmath = f_friction_fastmath 
  list%f_advection_scheme = f_advection_scheme
  list%f_rivermouth_drop = f_rivermouth_drop
  list%f_opening_dynamic = f_opening_dynamic
  list%f_dry_head_cap = f_dry_head_cap
  list%f_advection_donor = f_advection_donor
  list%f_advection_bend = f_advection_bend
  list%f_advection_lateral = f_advection_lateral
  list%f_inflow_edge = f_inflow_edge
  list%f_scalar_scheme = f_scalar_scheme
  list%f_diffusion_term = f_diffusion_term
  list%p_diagratio = min(max(p_diagratio, 0.0), 1.0)                ! 値を0.0~1.0に制限
  list%p_adv_upwind_index = min(max(p_adv_upwind_index, 0.0), 1.0)  ! 値を0.0~1.0に制限
  list%p_adv_donor_eps = p_adv_donor_eps                            ! 範囲の検査は m_swflow_enc の init
  list%p_adprunge_thresh = max(p_adprunge_thresh, 1.1)              ! 値を1.1以上に制限
  list%p_diffusion_nu = max(p_diffusion_nu, 0.0)                    ! 値を0.0以上に制限
  list%p_diffusion_alpha = max(p_diffusion_alpha, 0.0)              ! 値を0.0以上に制限
  list%f_nonhydrostatic = f_nonhydrostatic
  list%nh_hmin = nh_hmin
  list%nh_solver = nh_solver
  list%nh_itmax = nh_itmax
  list%nh_tol = nh_tol
  list%f_nh_adaptive = f_nh_adaptive
  list%nh_detector = nh_detector
  list%nh_chi_on = nh_chi_on
  list%nh_margin = nh_margin
  list%nh_amin = nh_amin
  list%nh_arel = nh_arel
  list%f_nh_breaking = f_nh_breaking
  list%nh_break_alpha = nh_break_alpha
  list%nh_break_beta = nh_break_beta
  list%nh_break_type = nh_break_type
  list%nh_break_fr = nh_break_fr
  list%nh_break_slope = nh_break_slope
  list%nh_break_margin = nh_break_margin
  list%nh_break_visc = nh_break_visc
  list%wf_break_visc = wf_break_visc
  list%nh_bc_margin = nh_bc_margin
  list%f_nh_slope = f_nh_slope
  list%f_nh_bottom = f_nh_bottom

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
