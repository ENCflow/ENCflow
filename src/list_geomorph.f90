module list_geomorph
  ! 地形変化条件設定ファイル(namelist)の読み込み。
  ! この層は生の値(未指定 = 型宣言のデフォルトが番兵)を運ぶだけで、
  ! 解釈・補完・検証は m_geomorph が行う(list_* 層の共通契約)
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_geomorph
  public :: list_geomorph_read

  integer, parameter :: nspstmax = 64  ! 水平層理の表 spl_strata の最大層数

  type t_list_geomorph
    ! --- 実行制御 ---
    real :: dt_geomorph = 0.0        ! 地形変化の更新時間間隔 (s)。0なら毎ステップ
    real :: morfac = 1.0             ! 加速係数(地形時間の加速。全プロセス共通)

    ! --- プロセス別フラグ(排他選択ではなく重ね合わせ。0:無効) ---
    ! 各プロセスは独立に有効化でき、calc は有効なものを順に適用する
    integer :: f_creep = 0           ! 斜面クリープ(線形拡散)(0:無効, 1:有効)
    real :: creep_d = 0.0            ! クリープ拡散係数 (m2/s)。0 = 既定 0.005 m2/yr(§62)

    integer :: f_fluvial = 0         ! 掃流砂 Exner(河床の浸食・堆積)(0:無効, 1:有効)
    integer :: f_qbform = 1          ! 流砂量式(1:芦田・道上, 2:MPM)
    real :: fluv_d50 = 0.0           ! 代表粒径 (m)。0 = 既定 0.01(§62)
    real :: fluv_tausc = 0.05        ! 限界無次元掃流力 τ*c
    real :: fluv_porosity = 0.4      ! 河床の空隙率 λ
    real :: fluv_sgrav = 1.65        ! 土粒子の水中比重 s = (ρs - ρ)/ρ
    real :: fluv_dzmax = 0.05        ! 1エッジ・1更新の河床変動上限 (m)
    real :: fluv_diagratio = 0.5857864376  ! 斜め方向の通過幅配分(= 2/(2+√2)。
                                     ! m_swflow_enc の p_diagratio と同値の既定)
    integer :: fluv_bcfeed = 0       ! 開境界の掃流砂給砂(0:流入は無給砂,
                                     ! 1:平衡給砂。流出は常に容量輸送)
    real :: fluv_bcfeed_fac = 1.0    ! 容量給砂の倍率(fluv_bcfeed = 1 のとき。0 = 無給砂、0.5 = 半給砂、
                                     ! >1 = 過給砂。流出側には掛けない。§84.9)
    real :: fluv_taufac = 1.0        ! 有効掃流力の比 f_τ(流砂量式に渡す τ* =
                                     ! f_τ × 全抵抗の τ*。砂堆・植生の形状抵抗を
                                     ! 除く簡略分離。1 = 分離なし。§84.3)
    integer :: fluv_slope = 0        ! 河床勾配による流砂方向補正(0:なし, 1:長谷川型
                                     ! q⃗ = q_b(t̂ − γ∇z)、γ = √(τ*c/(μs μk τ*))。§84.3)
    real :: fluv_mus = 1.0           ! 静止摩擦係数 μs(既定 1.0 = Asahi ら 2013 式 (22)、
                                     ! Hasegawa 1984 に拠る。2026-10-21 照合 §84.12)
    real :: fluv_muk = 0.45          ! 動摩擦係数 μk(既定 0.45 = 同上。Hasegawa 1989 は
                                     ! 概算に 0.7 を用いる)
    integer :: f_secflow = 0         ! 二次流による流砂方向補正(0:なし, 1:平衡型
                                     ! r = N* h κ、κ は流速場の流線曲率。§84.3)
    real :: sec_nstar = 7.0          ! N*(Engelund 型の河床近傍横断流速比の係数。既定
                                     ! 7.0 = Engelund 1974 / Asahi ら 2013 式 (18)。§84.12)
    real :: sec_rmax = 1.0           ! |r| の上限(急湾曲での h/R 比例則の打ち切り)
    real :: sec_vmin = 0.01          ! 曲率を評価する最小流速 (m/s)(未満は r = 0)

    integer :: f_berode = 0          ! 側岸侵食(0:無効, 1:有効。f_fluvial=1 が必須)。
                                     ! 湿潤セルの水面より高い隣接セル(河岸面)を、
                                     ! 脚部セルの掃流力で後退させ、削った土砂を脚部へ
                                     ! 保存的に移す(以後の掃流砂が運ぶ)。§84.4
    real :: berode_kb = 0.0          ! 河岸の侵食速度係数 K_b (m/s)(必須 > 0。
                                     ! 後退速度 E_b = K_b (τ*/τ*c,b − 1)^m。校正値。
                                     ! 既定は置かない)
    real :: berode_tausc = 0.05      ! 河岸の限界無次元掃流力 τ*c,b
    real :: berode_m = 1.0           ! 超過掃流力のべき指数 m
    integer :: f_repose = 0          ! 安息角崩落(0:無効, 1:有効)。隣接セル間の勾配が
                                     ! tanφ_r を超えた分を高い側から低い側へ移す
                                     ! (保存形。乾湿を問わない。1 更新 1 スイープ)。§84.4
    real :: repose_phi = 0.0         ! 安息角 φ_r (deg)。0 = 既定 30(§62。slide_phi と同じ)
    real :: repose_relax = 0.5       ! 1 更新で緩和する超過勾配の割合(0〜1)
    integer :: f_rockfall = 0        ! 崩落と崖錐(0:無効, 1:有効。§48.7)。隣接セル間の高さ差
                                     ! (自由面)が rf_hc を超えた分を高い側から低い側へ移し
                                     ! (崩落。保存形)、低い側に崖錐の厚さ ht(出力 Ht)として
                                     ! 積む。崖錐は安息角 rf_phi で広がり、覆われたセルの乾式
                                     ! 侵食 f_splash を rf_ftalus 倍に抑える(崖錐の保護)
    real :: rf_hc = 0.0              ! 自由面(崖)の限界高さ H_c (m)(必須 > 0)
    real :: rf_phi = 0.0             ! 崖錐の安息角 (deg)。0 = 既定 35
    real :: rf_relax = 0.5           ! 1 更新で緩和する超過高さの割合(0〜1)
    real :: rf_ftalus = 0.0          ! 崖錐に覆われたセルの乾式侵食の倍率(> 0。崖錐の除去速度 =
                                     ! 崖の後退速度を律する)。0 = 既定 0.3
    real :: rf_hmin = 0.0            ! 崖錐が安息角で動く最小厚さ h_min (m)(薄い崖錐はその場に
                                     ! 留まる = 微量の崖錐が斜面中に散らばる人工物を防ぐ)。0 = 既定 0.01
    real :: rf_fface = -1.0          ! 崖錐に支えられた面(崖錐律速の後退)の方式(§48.7)。0 以上で有効
                                     ! (rf_rc > 0 が前提): 安息角より急な落差の先(脚部)が崖錐 ht >= h_min
                                     ! に覆われたセルの乾式侵食 E を rf_fface 倍にし、崩落を「面の頂の柱が
                                     ! 脚部まで落ちる」形(柱の崩落)にする = 垂直な面が 1 セルずつ後退し、
                                     ! 崖錐の除去が後退を律する。負 = 無効(既定。窓版の崩落)
    real :: rf_uc = 0.0              ! 限界張り出し量 u_c (m)(§48.7。支え方式と spl_strata が前提)。正なら、
                                     ! 面の頂の柱は、柱より軟らかい脚部(安息角より急な落差の先。層理の倍率が
                                     ! 柱より大きい)の岩盤が前回の埋没以降に乾式侵食で u_c 以上削られたときも
                                     ! 崩れる(H_w > H_c に加えて)= 下の軟層の削り込みでキャップが張り出して
                                     ! 落ちる形。0 = 無効(既定)
    real :: rf_rc = 0.0              ! 自由面の高さを測る窓の半径 r_c (m)。0 = 隣接セル間の段差
                                     ! (従来。Δx に依存)。正なら nint(r_c/Δx) セルの正方形窓内の最低点
                                     ! との落差 H_w を自由面の高さとし、崖錐の安息角より急なエッジで
                                     ! H_w > H_c の超過分(そのエッジの安息角超過を上限)を移す
    integer :: f_fixation = 0        ! 定着(0:無効, 1:有効)。乾いたセルの定着度 a が
                                     ! 1 − exp(−t/T_fix) で育ち、供給側の限界掃流力を
                                     ! τ*c (1 + c_τ a) に上げる(標高・体積には触れない)。§84.6
    real :: fix_tfix = 0.0           ! 定着時間 T_fix (h。地形時間 = morfac 込み)(必須 > 0。
                                     ! 文献に標準値なし: Asahi ら 2013 の T_Land は出水の回帰
                                     ! 時間との比 0.025〜0.5 で蛇行、1 で発達せず。§84.12)
    real :: fix_ctau = 0.0           ! 定着時の限界掃流力の増分比 c_τ(必須 > 0。文献に標準値
                                     ! なし。Asahi ら 2013 は陸地化セルを領域から外す = c_τ → ∞)
    real :: fix_dzreset = 0.0        ! 定着面からの累積浸食深がこれを超えると a = 0 (m)。
                                     ! 0 = 既定 0.1(根系層の厚さの目安)
    real :: fix_cn = 0.0             ! 定着時の粗度(Manning n)の増分比 c_n。流れの摩擦項の n を
                                     ! n (1 + c_n a) にする(流砂の τ* は変えない。形状抵抗の分離)。
                                     ! 0 = 粗度に効かせない(既定)。§84.8
    real :: fix_tdec = 0.0           ! 冠水時の定着の減衰時間 T_dec (h。地形時間)。湿潤(h > dd)の間
                                     ! a ← a exp(−t/T_dec)(植生の枯死・表層の軟化)。0 = 減衰なし
                                     ! (既定 = 露出した砂州は浸食でしか定着を失わない)。§84.13
    real :: fix_ctau_bank = -1.0     ! 河岸侵食(f_berode)の河岸セルに効かせる定着の増分比 c_τ,b。
                                     ! 負 = fix_ctau と同じ(既定)、0 = 河岸には効かせない。§84.13

    integer :: f_suspend = 0         ! 浮遊砂(移流+浸食・沈降)(0:無効, 1:有効)
    integer :: f_esform = 1          ! 平衡濃度式(1:超過掃流力線形(簡易), 2:板倉・岸)
    real :: susp_d50 = 0.0           ! 浮遊砂の代表粒径 (m)。0 = 既定 0.0002(§62)
    real :: susp_wf = 0.0            ! 沈降速度 (m/s)。0 なら Rubey 式で d50 から導出
    real :: susp_tausc = 0.05        ! 浮遊の限界無次元掃流力 τ*c
    real :: susp_beta = 1.0          ! 沈降の底面濃度係数(c_b = β・C)
    real :: susp_esa = 0.0           ! 平衡濃度係数(C_eq = esa・(τ*/τ*c - 1))。
                                     ! f_suspend=1 で必須(体積濃度スケール)

    integer :: f_bedfines = 0        ! 河床の細粒分の帳簿(0:無効, 1:有効。f_suspend が必須。§84.10)
                                     ! 浮遊砂の浸食を河床に在庫する細粒分 s%sf(出力 Sf)に限り、
                                     ! 掃流砂の浸食で解放された細粒分はその場で懸濁する
    real :: fines_la = 0.0           ! 交換層厚 L_a (m)。利用可能率 f = min(1, sf/L_a)。f_bedfines=1 で必須
    real :: fines_frac0 = 0.0        ! 初期の細粒分割合(sf = fines_frac0 × sd。0 = 粗粒のみ、1 = 細粒のみ)

    integer :: f_wash = 0            ! 斜面浸食(雨滴+面状。f_suspend が必須)(0:無効, 1:有効)
    real :: wash_kr = 0.0            ! 雨滴侵食係数(無次元。E_r = kr・降雨強度)
    real :: wash_kf = 0.0            ! 面状侵食係数 (m/s)(E_f = kf・(τ*/τ*c - 1))
    real :: wash_tausc = 0.05        ! 面状侵食の限界無次元掃流力 τ*c
    real :: wet_lw = 0.0             ! 湿潤侵食(f_suspend の巻き上げ・f_wash の剥離)の
                                     ! 剥離深を横方向に広げる相関長 ℓ_w (m)(0 = 無効)。
                                     ! 流路の流れは幅 ℓ_w の帯(リル幅)から削る =
                                     ! 1 セル幅の流路への集中に長さスケールを与え、
                                     ! ガリー間隔の格子収束を得る(§84.16)

    integer :: f_splash = 0          ! 乾式斜面侵食(無流水: 雨滴・サブグリッドリル)
                                     ! (0:無効, 1:有効)。乾燥セル(h <= dd)対象で
                                     ! f_wash(湿潤セル)と相補。剥離土砂は系外排出
                                     ! (開いた系。バッドランド・海食崖向け。§48)
    real :: spl_kr = 0.0             ! 雨滴(スプラッシュ)侵食係数(無次元。
                                     ! E1 = kr・(1 + ca・κ)・P。P: 地表到達降雨強度)
    real :: spl_ca = 0.0             ! 雨滴項の凹地形増幅長 (m)(κ = max(∇²z, 0))
    real :: spl_kt = 0.0             ! サブグリッドリル侵食係数(無次元。
                                     ! E2 = kt・(1 + cb・κ)・S^h・P)
    real :: spl_cb = 0.0             ! リル項の凹地形増幅長 (m)
    real :: spl_h = 1.0              ! リル項の勾配べき指数 h
    real :: spl_dzmax = 0.0          ! 1セル・1更新の侵食上限 (m)(0=無効。
                                     ! 正のフィードバック暴走の安全弁)
    real :: spl_lc = 0.0             ! 曲率 κ を評価する相関長 ℓ (m)(0 = 格子の 5 点
                                     ! ラプラシアン)。正なら z を標準偏差 ℓ のガウス核で
                                     ! 平滑化してから κ を取る(サブグリッドリルの集水
                                     ! スケール。谷間隔の選択と格子収束を与える。§48.3)
    real :: spl_zbase = -9999.0      ! 侵食基準面の標高 (m)(-9000 以下 = なし)。
                                     ! 崖下が海のとき海面を与える(z がこれを下回らない)
    integer :: spl_sgrad = 1         ! 勾配 S の評価(1: 最急降下 = 8 近傍への下り勾配の最大
                                     ! = 既定。稜線の頂のセルも両面の勾配で削れる。
                                     ! 0: 中央差分 = 2026-10-19 以前の挙動。§48.4)
    real :: spl_ksat = 0.0           ! 凹地形増幅の飽和曲率 κ_s (1/m)(§48.6)。正なら有効曲率
                                     ! κ̃ = κ / (1 + κ/κ_s) を増幅項 1 + c κ̃ に使う(κ ≪ κ_s で
                                     ! 従来と同じ、κ ≫ κ_s で 1 + c κ_s に飽和)。0 = 飽和なし(既定)
    real :: spl_strata(1:2,1:nspstmax) = -9999.0
                                     ! 水平層理(硬軟差)の表(§48.5)。列 k = (層の下端標高
                                     ! z_k [m], 侵食性倍率 f_k)。z_k は昇順、f_k >= 0
                                     ! (0 = 削れない硬層)。地表標高 z が z_k <= z < z_{k+1}
                                     ! の層にあるセルの E を f_k 倍する。最下層より下は 1。
                                     ! 番兵(z <= -9000)の手前までが有効。未指定 = 層理なし

    integer :: f_debris = 0          ! 土石流 E-D(高橋型平衡濃度)(0:無効, 1:有効)。
                                     ! f_suspend と排他(同一 hs 上の E-D 二重計上防止)。
                                     ! morfac=1 必須(イベント計算)。debris_plan.md §2.2
    real :: db_phi = 0.0             ! 土砂の内部摩擦角 (deg)。f_dbed>=1 または
                                     ! f_dbres=1,2 で必須(等価流体構成
                                     ! f_dbed=0 + f_dbres=4,5 では不使用)
    real :: db_delte = 0.0007        ! 侵食速度係数 δe(既定は Takahashi 2007 の一般値
                                     ! 【要文献照合】debris_plan.md §1)
    real :: db_deltd = 0.05          ! 堆積速度係数 δd(Kanako 系の慣用値【要文献照合】)
    integer :: f_dbstop = 0          ! 停止条件の切替 (0:なし(E-D の ∝|V| のみ),
                                     ! 1:低速凝集 — vv<db_vstop で超過濃度を河床へ)
    real :: db_vstop = 0.05          ! 停止判定の速度閾値 (m/s)。f_dbstop=1 の凝集と
                                     ! f_dbres=1 の降伏判定(静止維持)が共有する
    real :: db_wstop = 0.0           ! 低速凝集の河床転換レート (m/s)。f_dbstop=1 で使用。0 = 既定 0.05
    integer :: f_dbres = 1           ! 抵抗則 (0:マニングのみ, 1:クーロン+マニング合成,
                                     ! 2:江頭構成則(降伏応力+粒子衝突・間隙流体の
                                     ! 層流抵抗。江頭ら1989 式(25)/Morpho2DH 式(17)(19)),
                                     ! 3:高橋・中川1991 石礫型(降伏 tanα'=0.45 +
                                     ! ダイラタント項 A'=4。濃度・相対水深で
                                     ! 石礫型/掃流状/泥流(マニング)を自動切替),
                                     ! 4:Voellmy 等価流体(降伏 μ + 乱流項 gV²/(ξh)。
                                     ! 岩屑なだれ・火砕流の実務標準(RAMMS/Titan2D 系)),
                                     ! 5:一定停止応力 τ_y + マニング合成(VolcFlow 型。
                                     ! 火砕流のランアウト・堆積形状の再現に実績))
    integer :: f_dbed = 1            ! E-D 式 (0:交換なし(等価流体モード: 移流・停止
                                     ! のみ。河床侵食を持たない火砕流・岩屑なだれ用),
                                     ! 1:高橋型平衡濃度への緩和(δe/δd。簡易形),
                                     ! 2:江頭・芦田1992 — E = |V|・C*・tan(θ−θe)。
                                     ! 流向勾配・パラメータ追加なし。Morpho2DH 式(5)-(7),
                                     ! 3:高橋・中川1991 式(12)(27) — 飽和床侵食+
                                     ! 慣性係数付き堆積。レートは δe/δd・q_T/d_L,
                                     ! 4:速度比例連行 E = δe・|V| — 雪崩・岩屑なだれの
                                     ! 走路連行(連行のみ。堆積は f_dbstop。連行可能層は
                                     ! sd(雪崩では雪の厚さ)。C >= db_cmin のセルのみ))
    real :: db_d50 = 0.0             ! 代表粒径 (m)。f_dbres=2,3 / f_dbed=3 で使用。0 = 既定 0.05
    real :: db_erest = 0.0           ! 粒子の反発係数 e(0〜1)。f_dbres=2 で使用。0 = 既定 0.85
                                     ! (材料固有値。文献に既定値なし)
    real :: db_cmin = 0.02           ! 江頭層流則を適用する濃度下限(これ未満は
                                     ! マニング則 = 希薄側の閉じ。層流則は C→0 で
                                     ! 発散するため必要な数値的切替。既定 2% は
                                     ! 高橋・中川1991 の泥流域判定(濃度2%以下)と整合)
    integer :: f_dbwet = 0           ! 間隙水の連行 (0:無視(水相は独立に保存。従来),
                                     ! 1:飽和床の連行 — 侵食で λ・s_b・Δz の間隙水を
                                     ! 地表水 h へ放出、堆積で埋没(高橋・中川1991
                                     ! 式(5)の源泉 i{c*+(1−c*)s_b} 形。Kanako 式(1)は
                                     ! s_b=1 の特別形)。gwflow とは併用不可
                                     ! (容量超過引き渡しと役割重複))
    real :: db_satbed = 1.0          ! 堆積層の飽和度 s_b(0〜1)。f_dbwet=1 で使用
                                     ! (高橋・中川1991 式(5)の記号。洞谷適用値は
                                     ! 勾配 21°以上で 0.8、以下で 1.0)
    real :: db_mu = 0.0              ! Voellmy 摩擦係数 μ(無次元)。f_dbres=4 で使用。0 = 既定 0.2
                                     ! (雪崩 0.1〜0.3、岩屑なだれは体積とともに低下。
                                     ! 見かけ摩擦 H/L を直接与える — 体積依存式は
                                     ! 内蔵しない(§0: 物理量は直接与える))
    real :: db_xi = 0.0              ! Voellmy 乱流係数 ξ (m/s²)。f_dbres=4 で使用。0 = 既定 1000
                                     ! (雪崩・土石流の慣用範囲 200〜1000)
    real :: db_tauy = 0.0            ! 一定停止応力 τ_y (Pa)。f_dbres=5 で使用。0 = 既定 10000
                                     ! (火砕流の適用例 5〜50 kPa(VolcFlow 系文献))
    integer :: f_dbcurv = 0          ! 曲率項(遠心加速度による垂直応力の増減を
                                     ! 降伏項に乗じる。0:なし, 1:有効。f_dbres=1〜4
                                     ! で使用(5 の τ_y は垂直応力に依らないため不可)。
                                     ! RAMMS(Fischer ら 2012)と同じ扱い。developer.md §28.10
    character(len=256) :: fn_dbinit = ""  ! 瞬時流動化の崩壊深分布ファイル (m)。
                                     ! 指定で f_release 有効(fn_* の有無の慣例)。
                                     ! f_debris=1 が必須。debris_plan.md §2.5
    real :: db_reltime = 0.0         ! 流動化の発生時刻 (s)。t0 以前なら最初の
                                     ! geomorph 更新で発火(1回だけ。リスタート安全)
    real :: db_relsat = 1.0          ! 崩壊土塊の飽和度 0〜1(gwflow 無効時の
                                     ! 間隙水付与 h += λ・relsat・D に使用。
                                     ! gwflow 有効時は容量超過引き渡しが担い不使用)
    integer :: f_slide = 0           ! 無限長斜面安定判定による自動流動化
                                     ! (0:無効, 1:有効)。f_debris=1 必須。
                                     ! Fs < 1 のセルの土層 sd を全層流動化する。
                                     ! 間隙水圧は gwflow の飽和厚 hg/sy0 から
                                     ! (gwflow 無効なら 0)。debris_plan.md §2.5
    real :: slide_c = 0.0            ! 有効粘着力 c' (Pa)。f_slide=1 で必須(0 可)
    real :: slide_phi = 0.0          ! 土のせん断抵抗角 φs (deg)。0 = 既定 30(§62)
    real :: slide_gamma = 0.0        ! 飽和単位体積重量 γt (N/m3)。0 = 既定 18000(§62)
    integer :: f_wthr = 0            ! 基岩風化=土層生成(0:無効, 1:有効。§32)
    real :: wthr_p0 = -9999.0        ! 裸岩での土層生成速度 (mm/kyr)。未指定 = 既定 50(§62)
    real :: wthr_sdstar = 0.5        ! 生成の減衰深 sd* (m)
    integer :: f_uplift = 0          ! 隆起(0:無効, 1:有効。§32)
    real :: uplift0 = -9999.0        ! 隆起速度 (mm/yr)。未指定 = 既定 1.0(§62)
                                     ! (例: 18000〜20000。湿潤・飽和の区別は
                                     ! 一律 γt の近似)

    integer :: f_bedslide = 0        ! 動く底層(地滑り土塊の底層すべり。z・sd の内数
                                     ! hb を慣性なし摩擦支配流で動かし、移動海底として
                                     ! 水面を変位させる = 地滑り津波)(0:無効, 1:有効)。
                                     ! docs/landslide_tsunami_plan.md
    character(len=256) :: fn_bsinit = ""  ! 底層の崩壊深分布ファイル (m)。指定で発火機構が
                                     ! 有効(f_bedslide=1 では必須)
    real :: bs_reltime = 0.0         ! 底層の発火時刻 (s)。t0 以前なら最初の更新で発火
    real :: bs_rho = 0.0             ! 土塊のかさ密度 ρs (kg/m3。間隙込み)。0 = 既定
                                     ! 2000(飽和土塊・岩屑の代表値。r = 0.5。init が
                                     ! 有効値を表示)。浮力 r = ρw/ρs、ρw = 1000 固定
    integer :: f_bsres = 1           ! 底層の抵抗則(1:Voellmy(慣性なし。速度
                                     ! V = √(ξ hb (S − μ b))), 2:Bingham〔予約〕)
    real :: bs_mu = 0.0              ! Voellmy 摩擦係数 μ。0 = 既定 0.15(慣性なし底層の
                                     ! 校正値。examples/landslide_tsunami と同じ)
    real :: bs_xi = 0.0              ! Voellmy 乱流係数 ξ (m/s²)。0 = 既定 500
    real :: bs_vstop = 0.0           ! 停止判定の速度閾値 (m/s)。0 = 既定 0.05(db_vstop と
                                     ! 同じ)。未満で hb を z に固定
    real :: bs_eps_s = 0.02          ! 降伏近傍の線形化幅(無次元勾配。安定条件の上限を決める)
    real :: bs_diagratio = 0.5857864376  ! 8方向配分の対角比(0 = 4近傍。p_diagratio と同義)
    real :: bs_cfl = 0.4             ! サブサイクルの安全係数
    integer :: bs_nsubmax = 10000    ! サブサイクル数の上限(超過は停止)
    real :: bs_tstop = 0.0           ! 停止(固定)に要求する低速の持続時間 (s)。V < bs_vstop が
                                     ! この時間続いたセルだけ hb を地形に固定する。0 = 即時
                                     ! (突入時の一時的な失速で誤固定しないための閉じ)
    integer :: f_bsplunge = 0        ! 引き渡し判定の水深(0: 現在の水深 h、1: 静水時の水深 =
                                     ! 初期水面 − 現在の底面 z。初期に湿潤だったセルのみ。
                                     ! 突入で一時的に離水した汀線帯でも引き渡す)
    integer :: f_bsvplunge = 0       ! 引き渡しの速度条件(0: 滞水深だけで即時、1: 混合体の速度が
                                     ! 底層の終端速度以下に落ちてから。高速突入の運動量を
                                     ! 混合体(SWE)のまま水柱に渡してから底層へ移す)
    real :: bs_hplunge = 0.0         ! 混合体(hs)から底層への引き渡し(プランジ)の滞水深
                                     ! 閾値 (m)。h >= bs_hplunge のセルの hs をかさ体積で
                                     ! hb・z・sd へ移す。0 = 引き渡しなし。f_debris=1 が必要

    ! 将来のプロセス追加はここにフラグとパラメータを足す
    ! (例: f_badland 崩壊性浸食)
  end type

contains


!----------------------------------------------------------------------
! 地形変化条件設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_geomorph_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_geomorph), intent(out) :: list
  integer :: un, ios

  real :: dt_geomorph
  real :: morfac
  integer :: f_creep
  real :: creep_d
  integer :: f_fluvial
  integer :: f_qbform
  real :: fluv_d50
  real :: fluv_tausc
  real :: fluv_porosity
  real :: fluv_sgrav
  real :: fluv_dzmax
  real :: fluv_diagratio
  integer :: fluv_bcfeed
  real :: fluv_bcfeed_fac
  real :: fluv_taufac, fluv_mus, fluv_muk, sec_nstar, sec_rmax, sec_vmin
  integer :: fluv_slope, f_secflow
  integer :: f_berode, f_repose
  real :: berode_kb, berode_tausc, berode_m, repose_phi, repose_relax
  integer :: f_rockfall
  real :: rf_hc, rf_phi, rf_relax, rf_ftalus, rf_hmin, rf_rc, rf_fface, rf_uc
  integer :: f_fixation
  real :: fix_tfix, fix_ctau, fix_dzreset, fix_cn, fix_tdec, fix_ctau_bank
  integer :: f_suspend
  integer :: f_esform
  real :: susp_d50
  real :: susp_wf
  real :: susp_tausc
  real :: susp_beta
  real :: susp_esa
  integer :: f_bedfines
  real :: fines_la, fines_frac0
  integer :: f_wash
  real :: wash_kr
  real :: wash_kf
  real :: wash_tausc
  real :: wet_lw
  integer :: f_splash
  real :: spl_kr, spl_ca, spl_kt, spl_cb, spl_h, spl_dzmax, spl_lc, spl_zbase
  integer :: spl_sgrad
  real :: spl_ksat
  real :: spl_strata(1:2,1:nspstmax)
  integer :: f_debris
  real :: db_phi
  real :: db_delte
  real :: db_deltd
  integer :: f_dbstop
  real :: db_vstop
  real :: db_wstop
  integer :: f_dbres
  integer :: f_dbed
  real :: db_d50
  real :: db_erest
  real :: db_cmin
  integer :: f_dbwet
  real :: db_satbed
  real :: db_mu
  real :: db_xi
  real :: db_tauy
  integer :: f_dbcurv
  character(len=256) :: fn_dbinit
  real :: db_reltime
  real :: db_relsat
  integer :: f_slide
  real :: slide_c
  real :: slide_phi
  real :: slide_gamma
  integer :: f_wthr
  real :: wthr_p0, wthr_sdstar
  integer :: f_uplift
  real :: uplift0
  integer :: f_bedslide, f_bsres, bs_nsubmax, f_bsplunge, f_bsvplunge
  character(len=256) :: fn_bsinit
  real :: bs_reltime, bs_rho, bs_mu, bs_xi, bs_vstop, bs_eps_s, bs_diagratio, bs_cfl
  real :: bs_hplunge, bs_tstop

  namelist /list_geomorph/ dt_geomorph, morfac, f_creep, creep_d, &
                           f_fluvial, f_qbform, fluv_d50, fluv_tausc, &
                           fluv_porosity, fluv_sgrav, fluv_dzmax, fluv_diagratio, &
                           fluv_bcfeed, fluv_bcfeed_fac, fluv_taufac, fluv_slope, fluv_mus, fluv_muk, &
                           f_secflow, sec_nstar, sec_rmax, sec_vmin, &
                           f_berode, berode_kb, berode_tausc, berode_m, &
                           f_repose, repose_phi, repose_relax, &
                           f_rockfall, rf_hc, rf_phi, rf_relax, rf_ftalus, rf_hmin, rf_rc, rf_fface, rf_uc, &
                           f_fixation, fix_tfix, fix_ctau, fix_dzreset, fix_cn, fix_tdec, fix_ctau_bank, &
                           f_suspend, f_esform, susp_d50, susp_wf, susp_tausc, &
                           susp_beta, susp_esa, f_bedfines, fines_la, fines_frac0, &
                           f_wash, wash_kr, wash_kf, wash_tausc, wet_lw, &
                           f_splash, spl_kr, spl_ca, spl_kt, spl_cb, spl_h, spl_dzmax, &
                           spl_lc, spl_zbase, spl_sgrad, spl_ksat, spl_strata, &
                           f_debris, db_phi, db_delte, db_deltd, f_dbstop, db_vstop, db_wstop, f_dbres, &
                           f_dbed, db_d50, db_erest, db_cmin, f_dbwet, db_satbed, &
                           db_mu, db_xi, db_tauy, f_dbcurv, &
                           fn_dbinit, db_reltime, db_relsat, &
                           f_slide, slide_c, slide_phi, slide_gamma, &
                           f_wthr, wthr_p0, wthr_sdstar, f_uplift, uplift0, &
                           f_bedslide, fn_bsinit, bs_reltime, bs_rho, f_bsres, bs_mu, bs_xi, &
                           bs_vstop, bs_eps_s, bs_diagratio, bs_cfl, bs_nsubmax, bs_hplunge, bs_tstop, f_bsplunge, f_bsvplunge

  ! 型宣言のデフォルトを namelist 変数の初期値にする
  dt_geomorph = list%dt_geomorph
  morfac = list%morfac
  f_creep = list%f_creep
  creep_d = list%creep_d
  f_fluvial = list%f_fluvial
  f_qbform = list%f_qbform
  fluv_d50 = list%fluv_d50
  fluv_tausc = list%fluv_tausc
  fluv_porosity = list%fluv_porosity
  fluv_sgrav = list%fluv_sgrav
  fluv_dzmax = list%fluv_dzmax
  fluv_diagratio = list%fluv_diagratio
  fluv_bcfeed = list%fluv_bcfeed
  fluv_bcfeed_fac = list%fluv_bcfeed_fac
  fluv_taufac = list%fluv_taufac
  fluv_slope = list%fluv_slope
  fluv_mus = list%fluv_mus
  fluv_muk = list%fluv_muk
  f_secflow = list%f_secflow
  sec_nstar = list%sec_nstar
  sec_rmax = list%sec_rmax
  sec_vmin = list%sec_vmin
  f_berode = list%f_berode
  berode_kb = list%berode_kb
  berode_tausc = list%berode_tausc
  berode_m = list%berode_m
  f_repose = list%f_repose
  repose_phi = list%repose_phi
  repose_relax = list%repose_relax
  f_rockfall = list%f_rockfall
  rf_hc = list%rf_hc
  rf_phi = list%rf_phi
  rf_relax = list%rf_relax
  rf_ftalus = list%rf_ftalus
  rf_hmin = list%rf_hmin
  rf_rc = list%rf_rc
  rf_fface = list%rf_fface
  rf_uc = list%rf_uc
  f_fixation = list%f_fixation
  fix_tfix = list%fix_tfix
  fix_ctau = list%fix_ctau
  fix_dzreset = list%fix_dzreset
  fix_cn = list%fix_cn
  fix_tdec = list%fix_tdec
  fix_ctau_bank = list%fix_ctau_bank
  f_suspend = list%f_suspend
  f_esform = list%f_esform
  susp_d50 = list%susp_d50
  susp_wf = list%susp_wf
  susp_tausc = list%susp_tausc
  susp_beta = list%susp_beta
  susp_esa = list%susp_esa
  f_bedfines = list%f_bedfines
  fines_la = list%fines_la
  fines_frac0 = list%fines_frac0
  f_wash = list%f_wash
  wash_kr = list%wash_kr
  wash_kf = list%wash_kf
  wash_tausc = list%wash_tausc
  wet_lw = list%wet_lw
  f_splash = list%f_splash
  spl_kr = list%spl_kr
  spl_ca = list%spl_ca
  spl_kt = list%spl_kt
  spl_cb = list%spl_cb
  spl_h = list%spl_h
  spl_dzmax = list%spl_dzmax
  spl_lc = list%spl_lc
  spl_zbase = list%spl_zbase
  spl_sgrad = list%spl_sgrad
  spl_ksat = list%spl_ksat
  spl_strata = list%spl_strata
  f_debris = list%f_debris
  db_phi = list%db_phi
  db_delte = list%db_delte
  db_deltd = list%db_deltd
  f_dbstop = list%f_dbstop
  db_vstop = list%db_vstop
  db_wstop = list%db_wstop
  f_dbres = list%f_dbres
  f_dbed = list%f_dbed
  db_d50 = list%db_d50
  db_erest = list%db_erest
  db_cmin = list%db_cmin
  f_dbwet = list%f_dbwet
  db_satbed = list%db_satbed
  db_mu = list%db_mu
  db_xi = list%db_xi
  db_tauy = list%db_tauy
  f_dbcurv = list%f_dbcurv
  fn_dbinit = list%fn_dbinit
  db_reltime = list%db_reltime
  db_relsat = list%db_relsat
  f_slide = list%f_slide
  slide_c = list%slide_c
  slide_phi = list%slide_phi
  slide_gamma = list%slide_gamma
  f_wthr = list%f_wthr
  wthr_p0 = list%wthr_p0
  wthr_sdstar = list%wthr_sdstar
  f_uplift = list%f_uplift
  uplift0 = list%uplift0
  f_bedslide = list%f_bedslide
  fn_bsinit = list%fn_bsinit
  bs_reltime = list%bs_reltime
  bs_rho = list%bs_rho
  f_bsres = list%f_bsres
  bs_mu = list%bs_mu
  bs_xi = list%bs_xi
  bs_vstop = list%bs_vstop
  bs_eps_s = list%bs_eps_s
  bs_diagratio = list%bs_diagratio
  bs_cfl = list%bs_cfl
  bs_nsubmax = list%bs_nsubmax
  bs_hplunge = list%bs_hplunge
  bs_tstop = list%bs_tstop
  f_bsplunge = list%f_bsplunge
  f_bsvplunge = list%f_bsvplunge

  call par_info("reading list_geomorph in " // trim(p%fn_geomorph))
  open(newunit=un, file=trim(p%fn_geomorph), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_geomorph: cannot open " // trim(p%fn_geomorph))
  read(un, nml=list_geomorph, iostat=ios)
  if (ios /= 0) call par_stop("list_geomorph: cannot read namelist")
  close(un)

  list%dt_geomorph = dt_geomorph
  list%morfac = morfac
  list%f_creep = f_creep
  list%creep_d = creep_d
  list%f_fluvial = f_fluvial
  list%f_qbform = f_qbform
  list%fluv_d50 = fluv_d50
  list%fluv_tausc = fluv_tausc
  list%fluv_porosity = fluv_porosity
  list%fluv_sgrav = fluv_sgrav
  list%fluv_dzmax = fluv_dzmax
  list%fluv_diagratio = fluv_diagratio
  list%fluv_bcfeed = fluv_bcfeed
  list%fluv_bcfeed_fac = fluv_bcfeed_fac
  list%fluv_taufac = fluv_taufac
  list%fluv_slope = fluv_slope
  list%fluv_mus = fluv_mus
  list%fluv_muk = fluv_muk
  list%f_secflow = f_secflow
  list%sec_nstar = sec_nstar
  list%sec_rmax = sec_rmax
  list%sec_vmin = sec_vmin
  list%f_berode = f_berode
  list%berode_kb = berode_kb
  list%berode_tausc = berode_tausc
  list%berode_m = berode_m
  list%f_repose = f_repose
  list%repose_phi = repose_phi
  list%repose_relax = repose_relax
  list%f_rockfall = f_rockfall
  list%rf_hc = rf_hc
  list%rf_phi = rf_phi
  list%rf_relax = rf_relax
  list%rf_ftalus = rf_ftalus
  list%rf_hmin = rf_hmin
  list%rf_rc = rf_rc
  list%rf_fface = rf_fface
  list%rf_uc = rf_uc
  list%f_fixation = f_fixation
  list%fix_tfix = fix_tfix
  list%fix_ctau = fix_ctau
  list%fix_dzreset = fix_dzreset
  list%fix_cn = fix_cn
  list%fix_tdec = fix_tdec
  list%fix_ctau_bank = fix_ctau_bank
  list%f_suspend = f_suspend
  list%f_esform = f_esform
  list%susp_d50 = susp_d50
  list%susp_wf = susp_wf
  list%susp_tausc = susp_tausc
  list%susp_beta = susp_beta
  list%susp_esa = susp_esa
  list%f_bedfines = f_bedfines
  list%fines_la = fines_la
  list%fines_frac0 = fines_frac0
  list%f_wash = f_wash
  list%wash_kr = wash_kr
  list%wash_kf = wash_kf
  list%wash_tausc = wash_tausc
  list%wet_lw = wet_lw
  list%f_splash = f_splash
  list%spl_kr = spl_kr
  list%spl_ca = spl_ca
  list%spl_kt = spl_kt
  list%spl_cb = spl_cb
  list%spl_h = spl_h
  list%spl_dzmax = spl_dzmax
  list%spl_lc = spl_lc
  list%spl_zbase = spl_zbase
  list%spl_sgrad = spl_sgrad
  list%spl_ksat = spl_ksat
  list%spl_strata = spl_strata
  list%f_debris = f_debris
  list%db_phi = db_phi
  list%db_delte = db_delte
  list%db_deltd = db_deltd
  list%f_dbstop = f_dbstop
  list%db_vstop = db_vstop
  list%db_wstop = db_wstop
  list%f_dbres = f_dbres
  list%f_dbed = f_dbed
  list%db_d50 = db_d50
  list%db_erest = db_erest
  list%db_cmin = db_cmin
  list%f_dbwet = f_dbwet
  list%db_satbed = db_satbed
  list%db_mu = db_mu
  list%db_xi = db_xi
  list%db_tauy = db_tauy
  list%f_dbcurv = f_dbcurv
  list%fn_dbinit = fn_dbinit
  list%db_reltime = db_reltime
  list%db_relsat = db_relsat
  list%f_slide = f_slide
  list%f_wthr = f_wthr
  list%wthr_p0 = wthr_p0
  list%wthr_sdstar = wthr_sdstar
  list%f_uplift = f_uplift
  list%uplift0 = uplift0
  list%slide_c = slide_c
  list%slide_phi = slide_phi
  list%slide_gamma = slide_gamma
  list%f_bedslide = f_bedslide
  list%fn_bsinit = fn_bsinit
  list%bs_reltime = bs_reltime
  list%bs_rho = bs_rho
  list%f_bsres = f_bsres
  list%bs_mu = bs_mu
  list%bs_xi = bs_xi
  list%bs_vstop = bs_vstop
  list%bs_eps_s = bs_eps_s
  list%bs_diagratio = bs_diagratio
  list%bs_cfl = bs_cfl
  list%bs_nsubmax = bs_nsubmax
  list%bs_hplunge = bs_hplunge
  list%bs_tstop = bs_tstop
  list%f_bsplunge = f_bsplunge
  list%f_bsvplunge = f_bsvplunge

end subroutine

end module
