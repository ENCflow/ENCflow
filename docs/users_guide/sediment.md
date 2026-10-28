# 土砂輸送と斜面・長期地形過程の解説(土砂・地形変化の補足)

[土砂・地形変化の章へ](geomorph.md) | [ユーザーガイド目次へ](../users_guide.md)

[土砂・地形変化の章](geomorph.md)のうち、水流で運ばれる土砂と斜面・
長期の過程 — 斜面クリープ、掃流砂、浮遊砂、斜面浸食、乾式斜面侵食、
基岩風化・隆起、地形時間の加速 — の式と既定値の根拠をまとめます。
土石流・斜面崩壊・動く底層は[土石流・斜面崩壊・動く底層の解説](massflow.md)
にあります。実装は `src/m_geomorph*.f90`(プロセスごとの submodule)です。

## 1. 共通の枠組み

**状態量。** 地盤高 $`z`$、侵食できる土層の厚さ $`s_d`$(`sd`。土層底
$`z - s_d`$ が基岩面)、水中の土砂を固体体積の柱状厚に換算した
$`h_s`$(`hs`)の 3 つです。河床が $`\Delta z`$ 動くとき $`s_d`$ も同じ
$`\Delta z`$ だけ動く(**共動更新**)ので、基岩面は侵食・堆積で動きません。
固体の総量 $`\sum h_s + (1-\lambda)\sum(z - z_0)`$ は機械精度で保存されます
($`\lambda`$ は河床の空隙率 `fluv_porosity`)。

**地形時間の加速(MORFAC)。** 地形の更新は $`n = \mathrm{NINT}(\texttt{dt\_geomorph}/\Delta t)`$
ステップごとに行い、地形過程には実効時間刻み

```math
\Delta t_s = n\,\Delta t\,\cdot\,\texttt{morfac}
```

を与えます。水理の時計は加速しません。これは沿岸・河川の形態動力学で
標準的な MORFAC 法[^roelvink06]で、1 回の計算が同じ水理イベント
`morfac` 回ぶんの地形変化を表すという解釈です。全プロセスで 1 個の
`morfac` を共有し(プロセスごとに変えると斜面からの供給と河道の堆積の
同時性が崩れる)、浮遊砂・斜面浸食では水柱との交換を加速しない
$`\Delta t_w = n\Delta t`$ で評価して河床側だけに `morfac` を掛けます。

**無次元掃流力。** 掃流砂・浮遊砂・斜面浸食は、Manning 則で閉じた
河床せん断応力 $`\tau = \rho g n^2 |\mathbf{V}|^2/h^{1/3}`$ を粒径
$`d`$ と水中比重 $`s`$(`fluv_sgrav`、既定 1.65)で無次元化した

```math
\tau_* = \frac{\tau}{\rho\, s\, g\, d} = \frac{n^2 |\mathbf{V}|^2}{s\, d\, h^{1/3}}
```

を共通に使います(重力加速度は分子分母で相殺)。限界値
$`\tau_{*c}`$ = 0.05 は Shields 曲線[^shields36]の粗砂〜礫の代表値です。

**海域マスクとの境界。** 海域マスク(fn_sw)の海セルでは地形を更新せず、
掃流砂・クリープ・動く底層は海セルとの間のエッジを通過しません(壁)。
浮遊砂・土石流の固体分は海セルへ流出すると系外へ消えます(海からの
流入は清水)。海底まで解く範囲は海域マスクでなく通常セル+初期水位で
表します([土砂・地形変化](geomorph.md)の「海域マスクと土砂の行き先」)。

## 2. 斜面クリープ(f_creep)

```math
\frac{\partial z}{\partial t} = D\,\nabla^2 z,
\qquad
D\,\Delta t_s\left(\frac{1}{\Delta x^2} + \frac{1}{\Delta y^2}\right) \le \frac{1}{2}
```

斜面の土壌匍行を線形拡散で表す古典的なモデル[^culling60]で、4 近傍の
保存形フラックス(5 点ラプラシアン)を陽解法で解きます。右の不等式が
陽解法の安定条件で、初期化時に検査して超えれば停止します。
$`z`$ だけを更新し $`s_d`$ は変えない(有限厚の土層を運ぶモデルではない)
ため、$`s_d = 0`$ でも作用し土層底も動きます。
既定 $`D`$ = 0.005 m²/yr は、斜面の拡散係数の文献域
0.001〜0.05 m²/yr[^fernandes97]の中央です。地形時間の量なので
`morfac` と組で解釈してください。
検証: [test/creep](../../test/creep/README.md)(ガウス丘の解析解に
最大誤差 7.8e-5 m、`morfac` = 2 の等価性 2.3e-4 m)。

**深さ依存クリープ(`creep_hstar` > 0)**:

```math
\mathbf{q} = -D\left(1 - e^{-H/H_c}\right)\nabla z,
\qquad
\frac{\partial z}{\partial t} = \frac{\partial s_d}{\partial t} = -\nabla\cdot\mathbf{q}
```

土層だけが動く形で、$`H`$ は各エッジの供給側(高い側)のセルの土層厚 $`s_d`$、
$`H_c`$ は輸送の減衰厚(`creep_hstar`)です。土層厚と勾配の両方に比例する輸送
[^johnstone15]を、Landlab の DepthDependentDiffuser と同じ $`K H_* (1 - e^{-H/H_*})`$ の
形で表したもので、$`D = K H_*`$ と読めば厚い土層の極限($`H \gg H_c`$)で上の線形拡散に
一致します($`D`$ = `creep_d` の意味は変えない)。$`z`$ と $`s_d`$ を同じ量だけ動かすので
岩盤面 $`z - s_d`$ は変わらず、裸岩($`s_d = 0`$)からは運びません。$`H`$ を供給側の
セルで評価すること、流量を固体体積に換算して掃流砂と共有の供給量制限(1 回の更新で
セルの土層厚を超えて出さない)に通すことは、本モデルの離散化の選択です。実効の
拡散係数は $`D`$ 以下なので、安定条件は上と同じです。
検証: [test/creep](../../test/creep/README.md) の深さ依存クリープの 4 構成(厚い土層で
従来の線形拡散と 1.8e-15 m で一致、岩盤面 $`z - s_d`$ の不変 4e-14 m、土層の総量の
保存、$`s_d \ge 0`$、裸岩で不変)。土層生成(§7)と組んだ定常斜面は、斜面の脚部に
渓流を置く連成の実験で確かめる予定です(docs/mountain_stream_plan.md §5)。

## 3. 掃流砂(f_fluvial)

**流砂量式。** エッジごとに両セル平均の $`\tau_*`$ から無次元流砂量
$`q_{b*}`$ を求め、$`q_b = q_{b*}\sqrt{s\,g\,d_{50}^3}`$(固体体積の
単位幅流砂量)にします。

```math
q_{b*} = 17\,\tau_*^{3/2}\left(1 - \frac{\tau_{*c}}{\tau_*}\right)\left(1 - \sqrt{\frac{\tau_{*c}}{\tau_*}}\right)
\quad(\texttt{f\_qbform} = 1,\ 芦田・道上),
\qquad
q_{b*} = 8\,(\tau_* - \tau_{*c})^{3/2}
\quad(\texttt{f\_qbform} = 2,\ \text{MPM})
```

芦田・道上式[^ashida72]は日本の河床変動計算の標準、Meyer-Peter &
Müller 式[^mpm48]は国際的に最も使われる式で、どちらも
$`\tau_* \le \tau_{*c}`$ で 0 です。エッジ流砂量は流向のエッジ法線への
射影 $`u_e/|\mathbf{V}|_e`$ と通過幅 $`L_k`$([ENC 格子の解説](encgrid.md) §2)を
掛けた $`Q_k = q_b\,(u_e/|\mathbf{V}|_e)\,L_k`$ です。掃流砂の適応距離は
格子スケールで平衡が成り立つとみなし(浮遊砂は輸送方程式で扱う、
という分担)、平衡流砂量を直接使います。

![流砂量式と平衡濃度](../figs/sediment_laws.png)

図 (a) が 2 つの流砂量式($`\tau_{*c}`$ = 0.05)、図 (b) は
[土石流の解説](massflow.md) §3 の平衡濃度です。

**Exner 式。** 河床は流砂の収支で動きます。

```math
(1 - \lambda)\frac{\partial z}{\partial t} = -\nabla\cdot\mathbf{q}_b
\quad\Longrightarrow\quad
\Delta z_{i,j} = -\frac{\Delta t_s}{(1-\lambda)\,\Delta x\,\Delta y}\sum_{k=1}^{8} Q_k
```

Exner の河床連続式[^exner25]そのものです。数値的な行き過ぎは次の順に
防ぎます: (1) 風上セルの土層厚 $`s_d`$ を超える侵食はエッジ単位で
起こさない、(2) 1 更新の河床変動を `fluv_dzmax`(既定 0.05 m)で制限する
(地形波のクーラン条件に相当。発動回数は終了時に表示)、(3) 複数エッジの
同時流出の合計が土層厚を超えるセルでは、そのセルを風上とする全エッジの
流砂量を同じ比率で縮小する(供給量制限。土砂体積は厳密に保存され、
発動セル数を終了時に表示)、(4) それでも丸め誤差で岩盤面を割った分は
最終的に切り捨て、失った体積を表示します(通常は出ません)。開境界では
流出側は常に容量輸送、流入側は `fluv_bcfeed = 1` のとき容量給砂(流入面の
供給 = 流入セルの正味流出 × `fluv_bcfeed_fac`。倍率 1 で入口の河床が固定)
です。区間流入には掃流砂の流砂量時系列 `inflow_qb`(河床への源泉)と浮遊砂の
平衡濃度給砂 `inflow_cs_eq` もあります([境界条件](boundary.md))。
掃流砂は河床面を転がるものとして、乾いたセルは供給せず、供給セルの水面
より高い地盤(河岸面)へは運びません(developer.md §84.2)。

**流砂の向き(湾曲部の補正)。** 既定の向きは水深平均流向 $`\hat{\mathbf t}`$
です。`fluv_slope = 1` と `f_secflow = 1` を入れると

```math
\mathbf{q}_b = q_b\left(\hat{\mathbf t} + r\,\hat{\mathbf n} - \gamma\nabla z\right),\qquad
\gamma = \sqrt{\frac{\tau_{*c}}{\mu_s\mu_k\tau_*}},\qquad
r = N_* h\,\kappa
```

となります。$`\hat{\mathbf n}`$ は流向の左法線、$`\kappa`$ は水深平均流速場の
流線曲率(左曲がり正。$`\kappa\hat{\mathbf n}`$ は曲率中心向きなので
$`r\hat{\mathbf n}`$ は常に湾曲内側)、$`\gamma\nabla z`$ は斜面を下る向きの
流砂(長谷川 1981 型。Nays2DH の河床勾配補正と同形)、$`r\hat{\mathbf n}`$ は
河床近傍の二次流が湾曲内側へ向く効果(Engelund 型の平衡二次流)です。
二次流が内岸へ運び、形成された横断斜面を勾配項が下へ戻す釣合いで、
横断勾配 $`\partial z/\partial n \approx r/\gamma`$ の外岸深・内岸浅の断面が
できます。曲率は 4 近傍がすべて湿潤のセルでだけ評価し(河岸沿い・境界列は
$`r = 0`$)、河岸面の段差は $`\nabla z`$ に入れません。係数の既定は $`\mu_s = 1.0, \mu_k = 0.45`$(Asahi ら 2013 式 (22)、Hasegawa
1984)、$`N_* = 7.0`$(Engelund 1974)です(文献照合 §84.12)。`fluv_taufac` は
流砂量式に渡す $`\tau_*`$ を全抵抗の $`\tau_*`$ の一定比にする簡略な
有効掃流力の分離です。検証: [test/bendsed](../../test/bendsed/README.md)。

**河岸の後退と崩落。** 河岸面(湿潤セル w の水面 $`z_w + h_w`$ 以上の地盤を
もつ隣接セル b)は `f_berode = 1` で

```math
E_b = K_b\,\max\!\left(\frac{\tau_{*w}}{\tau_{*c,b}} - 1,\,0\right)^{m},\qquad
Q_{b\to w} = (1-\lambda)\,E_b\,h_w\,L_k
```

の速度で後退します($`\tau_{*w}`$ は脚部セルの無次元掃流力、$`h_w`$ は
水没河岸高 = 脚部の水深、$`L_k`$ は通過幅)。削った体積は脚部セルに積み、
以後の掃流砂が運びます(エッジ流量として同じ保存形で適用。土層厚の供給量
制限が河岸の可動層にも効きます)。`f_repose = 1` の安息角崩落は、隣接セル
間の高さ差が $`\tan\phi_r \cdot d_k`$ を超えた分 $`e`$ について、1 更新に
$`\mathrm{relax}\cdot e/16`$ の高さを高い側から低い側へ移します(8 方向
同時でも行き過ぎない保存形の緩和。1 更新 1 スイープ)。検証:
[test/berode](../../test/berode/README.md)、
[test/repose](../../test/repose/README.md)。

**定着。** `f_fixation = 1` のセル定着度 $`a`$ は、乾燥(h ≤ dd)の間

```math
a \leftarrow 1 - (1 - a)\,e^{-\Delta t_m / T_\mathrm{fix}}
```

で育ち($`\Delta t_m`$ は地形時間の更新間隔 = morfac 込み)、湿潤中は定着面
(最後に乾いていたときの地盤高。堆積で押し上がる)からの累積浸食深が
`fix_dzreset` を超えた時点で 0 に戻ります。効果は、そのセルを供給側とする
掃流砂の閾値と流砂量式、およびそのセルを河岸とする側岸侵食の
$`\tau_{*c}`$ を $`\tau_{*c}(1 + c_\tau a)`$ に置き換えること、浮遊砂の
浸食項を同じ比で減らすこと(超過掃流力線形式は $`\tau_{*c,s}(1 + c_\tau a)`$、
板倉・岸式は $`C_{eq}/(1 + c_\tau a)`$。沈降項は不変)、および `fix_cn` > 0 の
とき流れの摩擦項の Manning n を $`n(1 + c_n a)`$ にすることです(流砂の
$`\tau_*`$ は元の n で評価。標高・体積には触れない)。検証:
[test/fixation](../../test/fixation/README.md)。

**既定値。** `fluv_d50` = 0.01 m は砂床(0.5 mm)と山地礫床(5 cm)の
幾何平均付近で、砂床・礫床の目安は章末の推奨値にあります。`fluv_porosity`
= 0.4、`fluv_sgrav` = 1.65 は砂礫の標準値です。検証:
[test/fluvial](../../test/fluvial/README.md)(固体総量 4.6e-16、共動更新
1.2e-14)、[test/sedinflow](../../test/sedinflow/README.md)(境界からの
土砂供給の台帳閉合)。

## 4. 浮遊砂(f_suspend)

**輸送。** 濃度 $`C = h_s/h`$ は水の体積あたりの固体体積で、水柱の
移流は浅水流計算のステップ内で水と同じエッジ流量により輸送されます
(スキームは[移流項の解説](advection.md) §7 の `f_scalar_scheme`。既定は
リンクごとの MUSCL。一様濃度は一様のまま、という性質が式の形で保証されます)。
河床との交換は地形更新の時刻に、セルごとに

```math
\Delta h_s = w_f\left(C_{eq} - \beta\,C\right)\Delta t_w,
\qquad
\Delta z = -\frac{\texttt{morfac}}{1-\lambda}\,\Delta h_s
```

で評価します。第 1 項が巻き上げ $`E = w_f C_{eq}`$、第 2 項が沈降
$`D = w_f\,\beta\,C`$(底面濃度係数 $`\beta`$ = `susp_beta`、既定 1)です。
乾いたセル($`h \le d_d`$)では浮遊分を全量河床に戻します。断面形 σ を
使う河道セルでは交換量に湿潤幅率 $`\sigma(h)`$ が掛かります。

**平衡濃度。** `f_esform` = 1 は校正用の簡易式
$`C_{eq} = \texttt{susp\_esa}\,(\tau_*/\tau_{*c} - 1)`$ で、`f_esform` = 2 は
板倉・岸の巻き上げ量式[^itakura80]です。

```math
C_{eq} = \frac{\max(q_{su}, 0)}{w_f},
\qquad
q_{su} = K\left[\frac{\alpha_*}{s+1}\,\frac{s\,g\,d}{u_*}\,\Omega - w_f\right],
\qquad
\Omega = \frac{\tau_*}{B_*}\,\frac{e^{-a'^2}}{\sqrt{\pi}\,\mathrm{erfc}(a')} + \frac{\tau_*}{B_*\eta_0} - 1,
\quad a' = \frac{B_*}{\tau_*} - \frac{1}{\eta_0}
```

$`K`$ = 0.008、$`\alpha_*`$ = 0.14、$`B_*`$ = 0.143、$`\eta_0`$ = 0.5 は
原式の定数で、$`u_* = \sqrt{\tau_* s g d}`$ です。校正パラメータなしに
砂の巻き上げを与えるので、砂の計算では 2 を推奨します。

**沈降速度。** `susp_wf` = 0 なら Rubey 式[^rubey33]で粒径から導きます。

```math
w_f = \left[\sqrt{\frac{2}{3} + \frac{36\nu^2}{s g d^3}} - \sqrt{\frac{36\nu^2}{s g d^3}}\right]\sqrt{s g d},
\qquad \nu = 10^{-6}\ \mathrm{m^2/s}
```

粘土・シルトのフロックには Rubey 式は使えないので、泥では実効沈降
速度を `susp_wf` に直接与え、簡易式 $`E = w_f\,\texttt{esa}\,(\tau_*/\tau_{*c} - 1)`$
を Partheniades 型の侵食式[^partheniades65] $`E = M(\tau/\tau_{ce} - 1)`$ と
同型とみなして `susp_esa`・`susp_tausc` を校正します。

**既定値。** `susp_d50` = 0.2 mm は細砂(浮遊砂の代表粒径)、
`susp_esa` = 1e-4 は文献値のない簡易式の係数で
[test/suspend](../../test/suspend/README.md)の校正値です(**経験値**)。
検証: 同テストで 2 つの平衡濃度式の固体総量保存 2.2e-15。

## 5. 斜面浸食(f_wash)

湿潤($`h > d_d`$)で河道外($`r_w = 0`$)のセルから、雨滴侵食と面状
侵食で土砂を剥離し、浮遊砂 $`h_s`$ に注入します(`f_suspend` が必須)。

```math
E = k_r\,P + k_f\,\max\!\left(\frac{\tau_*}{\tau_{*c}} - 1,\ 0\right)
\qquad[\mathrm{m/s},\ 固体体積]
```

$`P`$ は地表到達降雨強度、$`k_r`$(`wash_kr`、無次元)は雨量あたりの
剥離体積、$`k_f`$(`wash_kf`、m/s)は超過せん断に線形な面状侵食の
係数で、$`\tau_*`$ は浮遊砂の粒径で評価します。USLE 系の経験則を
格子の物理量で書き直した形で、既定 0.01 / 1e-5 m/s は
[test/wash](../../test/wash/README.md)の値(**経験値、校正前提**)です。
剥離分は $`z`$・$`s_d`$ から共動で差し引かれ、$`s_d = 0`$ で岩盤露出
として止まります。非河道セルでは浮遊砂の巻き上げ $`E`$ と $`k_f`$ 項が
概念的に重なるため、両方を使うときは係数の校正で管理してください。

**幅のスケール(`wet_lw`)。** 面状侵食も巻き上げも $`\tau_*`$ に比例し、
流れが集まった 1 セルだけを削る正帰還に長さスケールがないため、ガリーの幅と
間隔が格子幅で決まります。`wet_lw` $`= \ell_w`$ を与えると、セルごとに評価した
剥離深 $`e_j`$ を標準偏差 $`\ell_w`$ のガウス核 $`K`$ で配ってから河床に適用します
($`\Delta z_i = -\sum_j K_{ij}\,e_j`$。核は対称で、領域外・海セルへの分は自セルに
戻すので $`\sum_i \Delta z_i = -\sum_j e_j`$ = 固体の総量が保存)。浮遊砂 $`h_s`$ は
源セル $`j`$ に入ります。$`\ell_w`$ はリル(流路)の幅で、幅が流量に依らない
固定値の近似です。

## 6. 乾式斜面侵食(f_splash)

表面流のない高透水斜面(バッドランド、火砕丘の崖)の谷形成を、
乾燥($`h \le d_d`$)で河道外のセルに働くサブグリッド過程として
パラメータ化します。

```math
E = P\left[k_r\,(1 + c_a\,\kappa) + k_t\,(1 + c_b\,\kappa)\,S^{h}\right],
\qquad
S = |\nabla z|,\quad \kappa = \max(\nabla^2 z, 0)
```

第 1 項は雨滴の飛散(台地上でも働く)、第 2 項は雨滴に転がされる
粒子集合体[^trottet25]やサブグリッドのリルによる勾配依存の侵食で、
凹地形($`\kappa > 0`$)で効率が上がる正のフィードバック(`spl_ca`、
`spl_cb`)が谷を成長させます。剥離土砂は流水がなく運べないため
**系外へ排出**し(総量を終了時に表示)、$`z`$・$`s_d`$ を共動で減らします。
平滑化のない凹地形フィードバックは最短波長が最速で成長する
(Smith & Bretherton の無限波数問題[^smith72])ため、格子の κ(`spl_lc` = 0)
では谷間隔が 2〜3 Δx に張り付きます(拡散項を足しても成長の有無(符号)が
変わるだけで間隔は選ばれません。増幅も拡散も $`k^2`$ に比例するためで、
クリープは力学的モデルでもないので併用しません)。
κ を相関長 $`\ell`$(`spl_lc`。サブグリッドリルの集水スケール)で平滑化した
$`z`$ から取ると、擾乱の成長率が

```math
\sigma(k) = D_a\,k^2\,e^{-\ell^2 k^2/2},\qquad
D_a = P\,k_t\,c_b\,S^{h}
```

となって有限の波数 $`k^* = \sqrt{2}/\ell`$ で極大を持ち、谷間隔は
$`\lambda^* = 2\pi\ell/\sqrt{2} \approx 4.4\,\ell`$ と $`\ell`$ だけで決まります
(Perron らの $`\lambda \propto \sqrt{K_s/K}`$[^perron09]が増幅と拡散の比で
間隔を決めるのに対し、ここでは平滑化のスケールそのものが間隔を決めます)。
V 字谷底の κ も $`\sim 2S/\ell`$ に有界になります(ただし谷壁が垂直化する
深い段階の速さは勾配 $`S`$ が格子で決まるため格子依存が残ります。
examples/badland)。`spl_zbase` は侵食基準面(崖下が海なら海面)、
`spl_dzmax` は暴走の安全弁です。`spl_ksat` を与えると増幅項の $`\kappa`$ を
有効曲率 $`\tilde\kappa = \kappa/(1 + \kappa/\kappa_s)`$ に置き換え、強い凹部
(崖の基部)での増幅を $`1 + c\,\kappa_s`$ で飽和させます(線形段階の間隔選択は
不変。検証は [test/splashsat](../../test/splashsat/README.md))。水平層理 `spl_strata`(層の下端標高と
侵食性倍率の表)を与えると、セルの地表標高が属する層の倍率を $`E`$ に掛けます
(硬軟互層の縞・段・キャップロック。倍率 0 の層は削れません。検証は
[test/splashstrata](../../test/splashstrata/README.md))。既定 $`k_r`$ = 0.0005、$`k_t`$ = 0.05 は
テストの中央値(**経験値**)で、検証は
[test/splash](../../test/splash/README.md)(増幅なしの解析形
$`\Delta z = P(k_r + k_t S)T`$ に全桁一致、排出台帳が解析和に一致)と
[test/splashslide](../../test/splashslide/README.md)(固結・未固結の
崖の対照)です。詳しい根拠と試行の記録は docs/splash_plan.md にあります。

## 7. 基岩風化と隆起(f_wthr / f_uplift)

**土層生成。** 風化は $`z`$ を保って $`s_d`$ を増やし(基岩面が下がる)、
土層が厚いほど遅くなる指数則[^heimsath97]に従います。

```math
\frac{d s_d}{dt} = W_0\,e^{-s_d/s_*}
\quad\Longrightarrow\quad
s_d^{\,n+1} = s_d + s_*\ln\!\left(1 + \frac{W_0\,\Delta t_s}{s_*}\,e^{-s_d/s_*}\right)
```

右の更新式は常微分方程式の厳密解の伝播子なので、`morfac` が大きくても
無条件に安定です。$`W_0`$(`wthr_p0`、既定 50 mm/kyr)は裸岩での
土層生成速度 0.01〜0.1 mm/yr の中央、$`s_*`$(`wthr_sdstar`、既定 0.5 m)は
減衰深の代表値です。`fn_wthr` を与えると、セルごとの倍率の分布を掛けた
$`W_0 f_w`$ になります(岩質の違い。倍率 0 のセルは風化しません。渓流の岩盤のように、
岩盤面を風化でなく流水の下刻で下げたい場所に使います)。倍率は生成速度だけに掛かり、
減衰深 $`s_*`$ は全域で共通です。

**隆起。** $`z \mathrel{+}= U\,\Delta t_s`$($`s_d`$ 不変 = 基岩ごと上昇)。
$`U`$(`uplift0`、既定 1 mm/yr)は造山帯の代表値の下限で、負値は沈降です。
海域マスクのセルは侵食基準面として対象外です。`fn_uplift` を与えると、セルごとの
倍率の分布を掛けた $`U f_u`$ になります(出口のセルを 0 にすれば基準面の固定、
負にすれば基準面の低下。断層ブロックの差別隆起も表せます)。
長期の地形発達は「代表水文の反復 × MORFAC × リスタート連鎖」で
地形時間を稼ぐ CAESAR-Lisflood 型[^coulthard13]の実行様式を想定して
います(developer.md §32)。

### 石灰岩の溶食(f_dissol)

**化学的削剥。** 石灰岩が水に溶けて消える過程は、風化の対(z を下げ
$`s_d`$ を保つ)として、岩に入る水の量に比例させます[^white84][^gabrovsek09]:

```math
\frac{dz}{dt} = -\,k_d\, f_{\rm sol}\,(q_{\rm r} + f_{\rm sink}\, q_{\rm sink}),
\qquad k_d = \frac{c_{\rm eq}}{\rho_{\rm r}}
```

$`q_{\rm r}`$ は面的な涵養フラックス(浸透量 `dissol_src = 1`、地上降雨量
`dissol_src = 2`、または浸透量に裸岩で発生する流出水 $`f_{\rm surf}\,
f_b\,(P - I)`$ を加えたもの `dissol_src = 3`。$`f_b = \max(0, 1 - s_d/s_{\rm surf})`$
は裸岩の割合)、$`q_{\rm sink}`$ は管路連続体層の吸込穴への
流入フラックス(`dissol_sink = 1`)、$`f_{\rm sol}`$ はセル別の可溶率
(`fn_dissol`)です。1 回の地形更新では、更新間隔に積算された水量
$`F`$ (m) に morfac を掛けて $`w = k_d f_{\rm sol} F \cdot \texttt{morfac}`$
を溶かし、不溶性残渣の体積率 $`f_{\rm res}`$(`dissol_fres`)だけ土層に
残します: $`z \leftarrow z - (1 - f_{\rm res}) w`$、
$`s_d \leftarrow s_d + f_{\rm res} w`$。局所・線形で無条件に安定です。

**側方溶食**(`dissol_lat` = $`p`$)。湛水セル w の溶解能 $`W_w`$ のうち
$`p`$ を、w の水面 $`e_w`$ より床が高い 8 近傍の陸セル n(岩壁)へ接触幅
$`L_k`$(軸 Δx、斜め Δx·2/(2+√2))に比例して配り、残り $`1-p`$ を床へ
配ります(壁のないセルは床に全量):

```math
\Delta z_n = -\,f_{{\rm sol},n}\, p\, W_w \frac{L_k}{\sum_{m\in{\rm walls}(w)} L_m},
\qquad \Delta z_w = -\,f_{{\rm sol},w}(1-p)\,W_w
```

総溶解能は不変(配分)で、壁の後退は壁セルの z の低下で表します。
$`p`$ は床と壁の溶ける比で、`dissol_lat = −1` なら濡れ面の面積比
$`p_w = h_w \sum L / (h_w \sum L + \Delta x \Delta y)`$ でセルごとに決めます
(推奨。深い湛水ほど壁の分け前が増える)。固定値を与えるなら湛水深と
格子幅の比から(h = 5 m・Δx = 10 m で約 0.8)。

$`c_{\rm eq}`$(`dissol_ceq`、既定 100 mg/L CaCO₃ 換算)は**有効溶解能**
で、平衡溶解度から流入水の既存濃度を引いた「1 m³ の水が溶かす岩の質量」
です。炭酸平衡は解かず、土壌 CO₂・温度の効果はこの 1 個に畳みます
(裸岩の雨水 50〜80、土層下 100〜300 mg/L)。$`\rho_{\rm r}`$(`dissol_rho`、
既定 2500 kg/m³)と合わせて $`k_d`$ = 4×10⁻⁵ m/m、涵養 1 m/yr で
40 mm/kyr となり、カルストの化学的削剥速度の文献域 20〜100 mm/kyr
[^gabrovsek09]に入ります。水は常に $`c_{\rm eq}`$ ぶん溶かす(未飽和
一定率)ので、流下に伴う飽和の減衰は表しません。洞窟(管路)の成長は
別の段階として未実装です(docs/karst_plan.md §5)。

### 流水による岩盤下刻(f_rockinc)

**剥離・研磨と被覆。** 岩盤面 $`R = z - s_d`$ を流水の剥離と、運ばれる礫の
研磨(tools 効果)で下げ、可動層 $`H = s_d`$ が露出率 $`e^{-H/H_*}`$ で下刻を
抑えます:

```math
\tau_b = \frac{\rho_w g n^2 |V|^2}{h_e^{1/3}},\qquad
E_{p0} = f_r\,k_p \max\!\left(\frac{\tau_b}{\tau_c} - 1,\ 0\right)^{m},\qquad
E_{a0} = f_r\,\beta\,q_c\,F_s(H)
```

```math
\frac{dR}{dt} = -(E_{p0} + E_{a0})\,e^{-H/H_*},\qquad \frac{dH}{dt} = E_{p0}\,e^{-H/H_*}
```

$`\tau_b`$ は掃流砂と同じ Manning 閉じ($`h_e = \max(h, d_v)`$)、$`f_r`$ は
侵食性倍率(`fn_rock`)です。剥離項は、岩盤河道の侵食速度を底面せん断応力で
表す型[^howard83]の超過せん断応力形 $`E = k_e(\tau_b - \tau_c)^m`$ を
$`k_p = k_e \tau_c^m`$ と置いた比形で、$`k_p`$ は「$`\tau_b = 2\tau_c`$ での
裸岩の下刻速度」(m/s)になります(閾値つきの形の典拠は照合中)。被覆を層厚の
指数関数で表す形は SPACE[^shobe17] と Landlab の GravelBedrockEroder と同じです。
剥離した岩の厚さは同じ厚さの可動層になり($`z`$ は不変)、膨張は $`k_p`$ に
吸収します(風化と同じ 1:1 の換算。**独自の簡略化**)。研磨項の $`q_c`$ はセルの
掃流砂容量(単位幅の固体流砂量)、$`q_c F_s`$ はそのセルから出る掃流砂で、これを
床を叩く礫の量とみなします(GravelBedrockEroder の「研磨 = β × 流砂量 × 露出率」と
同じ形)。研磨で削れた分は細粒分として系外へ出し($`z`$ が下がる)、被覆には
加えません。

**薄層の輸送。** 掃流砂のエッジ流量に、供給側セルの利用可能率
$`F_s = 1 - e^{-H/H_*}`$ を掛けます。一様な容量 $`q_c`$ と一定の流砂量 $`q_s`$
の定常では $`F_s = q_s/q_c`$ となり、露出率は $`1 - q_s/q_c`$、つまり供給比で
書いた被覆[^sklar04][^turowski07]に一致し、研磨による下刻速度は
$`E = \beta q_s (1 - q_s/q_c)`$ の山形になります($`q_s/q_c = 1/2`$ で最大、
1 以上で全被覆の 0。Sklar & Dietrich の saltation–abrasion 模型の線形化と同じ形)。被覆を沖積層の厚さと河床の
起伏の比で決める考え方[^zhang15]を、露出率と利用可能率に同じ $`H_*`$ を使う
閉包で書いたもので、この組合せと有次元化は**独自**です
(docs/mountain_stream_plan.md §4.3)。剥離物が下流で流砂に加わる定常は、
セルごとに $`q_i = q_{i-1} + (1-\lambda)\Delta x\,E_{p0}(1 - q_i/q_c)`$ を
解けば得られます(test/rockinc の T3)。

**時間積分。** 水理を更新の頭で固定し、露出率を厳密に積分します:

```math
H^{n+1} = H^n + B_p,\qquad
B_p = H_*\ln\!\left(1 + \frac{E_{p0}\,\Delta t_s}{H_*}\,e^{-H^n/H_*}\right),\qquad
B_a = \frac{E_{a0}}{E_{p0}}\,B_p
```

(風化の伝播子と同じ形。研磨の $`F_s`$ は更新の頭の値で固定し、
$`E_{p0} = 0`$ では $`B_a = E_{a0}\,\Delta t_s\,e^{-H^n/H_*}`$)。更新間隔・`morfac` を変えても同じ結果になり、
無条件に安定です。薄い層の排出は陽的で、時間尺度は
$`H_*(1-\lambda)\Delta x / q_c`$ です。

**土石流による岩盤侵食(rock_kdb)。** 土石流のイベント計算(`f_debris = 1`)では、流れる
混合体の準静的な駆動応力で岩盤を削ります:

```math
\tau_d = \rho_w (1 + sC)\,g_e\,h_t \tan\theta_f,\qquad
E_{d0} = f_r\,k_d \max\!\left(\frac{\tau_d}{\tau_{cd}} - 1,\ 0\right)^{m_d},\qquad
\frac{dR}{dt} = -E_{d0}\,e^{-H/H_*},\qquad \frac{dH}{dt} = E_{d0}\,e^{-H/H_*}
```

$`h_t = h + h_s`$ は混合流動深、$`C`$ は混合体積濃度、$`\theta_f`$ は流向の河床勾配(下りだけ。
各セルで流向の下流側の近傍との片側差分。中央差分では 2 セル周期の凹凸が勾配に現れず、凸部で
浅い流れが凸部を削り残して段差が育つ。developer.md §89.23・§89.24)、
$`g_e`$ は運動方程式と同じ有効重力($`g\cos^2\theta_f`$。`f_gravity_correction = 0` なら $`g`$)です。
$`\tau_d`$ は定常の等流で抵抗則の底面せん断に等しく、抵抗則の選び方によりません。働くのは
濃い混合体($`C \ge c_{\min}`$ = `db_cmin`)が流れている($`|V| \ge v_{stop}`$ = `db_vstop`)
セルだけで、生成物は剥離と同じく 1:1 で可動層に入ります($`z`$ は不変)。取り込むか被覆として
残るかは侵食・堆積式が決めます。時間積分は剥離と同じ伝播子で、E-D を適用した後の $`H`$ を
使います。

土石流が急勾配の谷の岩盤を削る主な担い手であることは、勾配–面積関係[^stock03]と侵食ピンの
観測[^stock05]から示されています。機構は粒子の衝突とされ、慣性応力に基づく則[^stock06]や
回転ドラムの実験[^hsu08]があります。単層混合体は衝突が集中する巨礫の前縁を分けて表さないため、
単一イベントの比較(docs/mountain_stream_plan.md §12.4)で頑健だった準静的応力の超過形を
採りました。流動深と勾配の関数の侵食則[^mcguire23]と同じ種類で、形と係数の組合せは**独自**です。
同じ比較では、閾値 1 kPa で侵食がほぼ勾配 0.2 以上の区間に集まりました。厚さ約 5 cm の堆積物が
衝突から床を守るという観測[^mccoy13]は、$`H_*`$ の目安になります。

## 8. パラメータと既定値の根拠

根拠欄の分類語の意味は[既定値の根拠の読み方](../users_guide.md#既定値の根拠の読み方)を参照してください。

| パラメータ | 既定 | 意味 | 根拠 |
|---|---:|---|---|
| dt_geomorph / morfac | 0 / 1 | 地形更新間隔 (s) / 地形時間の加速(§1) | **方式** MORFAC 法[^roelvink06]。イベント計算は 1 |
| creep_d | 0.005 m²/yr | クリープ拡散係数 $`D`$(§2) | **文献値** 文献域 0.001〜0.05 m²/yr の中央[^fernandes97] |
| creep_hstar | 0(従来の線形拡散) | 深さ依存クリープの減衰厚 $`H_c`$ (m)(§2) | **校正値** 標準値がない。厚い土層では結果によらない |
| f_qbform | 1 | 流砂量式(§3) | **方式** 1: 芦田・道上[^ashida72]、2: MPM[^mpm48] |
| fluv_d50 | 0.01 m | 掃流砂の代表粒径 | **経験値** 砂床〜礫床の幾何平均付近 |
| fluv_tausc / susp_tausc / wash_tausc | 0.05 | 限界無次元掃流力(§1) | **文献値** Shields 曲線の粗砂〜礫の代表値[^shields36] |
| fluv_porosity / fluv_sgrav | 0.4 / 1.65 | 河床の空隙率 / 水中比重 | **慣用値** 砂礫の標準値 |
| fluv_dzmax | 0.05 m | 1 更新の河床変動上限(§3) | **数値設定** 安全弁(地形波のクーラン条件相当) |
| fluv_bcfeed | 0 | 開境界の給砂(§3) | **方式** 0: 無給砂、1: 容量給砂(流入セルの正味流出 × 倍率) |
| fluv_bcfeed_fac | 1.0 | 容量給砂の倍率 | 1 = 入口の河床固定、0 = 無給砂 |
| f_esform | 1 | 平衡濃度式(§4) | **方式** 1: 簡易(校正用)、2: 板倉・岸(砂では推奨)[^itakura80] |
| susp_d50 / susp_wf | 0.2 mm / 0 | 浮遊砂の粒径 / 沈降速度 | **慣用値** 細砂の代表 / **導出** 0 なら Rubey 式[^rubey33] |
| susp_beta | 1.0 | 底面濃度係数 $`\beta`$ | **方式** 1 = 鉛直一様の近似 |
| susp_esa | 1e-4 | 簡易式の係数 | **検証ケース** [test/suspend](../../test/suspend/) の校正値(根拠は弱い) |
| f_bedfines / fines_la / fines_frac0 | 0 / 必須 / 0 | 河床の細粒分の帳簿(§4) | **方式** 2 成分の在庫。L_a は数値的な混合厚(数 cm〜0.1 m)、割合は与件 |
| wash_kr / wash_kf | 0.01 / 1e-5 m/s | 雨滴 / 面状侵食係数(§5) | **経験値** [test/wash](../../test/wash/) の値。校正前提 |
| wet_lw | 0 m | 剥離深の横方向拡散の相関長 $`\ell_w`$(§5) | **与件** 0 = なし。リル(流路)の幅の目安。Δx ≤ ℓ_w/2 で谷間隔が格子によらない([test/wetlw](../../test/wetlw/)) |
| spl_kr / spl_kt / spl_h | 5e-4 / 0.05 / 1 | 乾式侵食の係数と勾配指数(§6) | **経験値** テストの中央値 |
| spl_ca / spl_cb | 0 / 0 m | 凹地形増幅長 | **与件** 0 = 増幅なし。谷の成長には数 m〜数十 m |
| spl_dzmax | 0 | 1 更新の侵食上限 | **数値設定** 0 = 無効。暴走の安全弁 |
| spl_lc | 0 m | 曲率の相関長 $`\ell`$ | **与件** 0 = 格子の κ(間隔が格子依存)。谷間隔のおよそ 1/5(examples/badland) |
| spl_zbase | なし | 侵食基準面 | **与件** 崖下が海なら海面 |
| spl_ksat | 0 | 増幅の飽和曲率 $`\kappa_s`$ | **与件** 0 = 飽和なし。崖の基部の段を残すには 0.05〜0.2 1/m(examples/mesa) |
| spl_strata | なし | 水平層理の(下端標高, 侵食性倍率)表 | **与件** 層序の硬軟差。倍率 0 = キャップロック |
| wthr_p0 / wthr_sdstar | 50 mm/kyr / 0.5 m | 土層生成速度 / 減衰深(§7) | **文献値** Heimsath 型の文献域の中央[^heimsath97] |
| fn_wthr | なし(全域 1) | 土層生成速度の倍率の分布 | **与件** 岩質の違い、風化しないセル(0。渓流の岩盤など) |
| uplift0 | 1 mm/yr | 隆起速度 | **慣用値** 造山帯の代表値の下限 |
| fn_uplift | なし(全域 1) | 隆起速度の倍率の分布 | **与件** 基準面の固定(0)・低下(負)、断層ブロック |
| dissol_ceq / dissol_rho | 100 mg/L / 2500 kg/m³ | 有効溶解能 / 岩の密度(§7) | **文献値** 石灰岩地域の涵養水の CaCO₃ 濃度の代表[^white84]と石灰岩の密度。k_d = 4e-5 m/m → 涵養 1 m/yr で 40 mm/kyr(文献域 20〜100)[^gabrovsek09] |
| dissol_src / dissol_sink | 1 / 0 | 水量の源 / 吸込穴項 | **方式** 1: 浸透量、2: 地上降雨量、3: 浸透量 + 裸岩の流出水。吸込穴項は管路連続体層の枡流入 |
| dissol_fsurf / dissol_sdsurf | 0.3 / 0.1 m | 表面流源の流出水の溶解能の比 / 裸岩とみなす土層厚 | **文献値** 裸岩の雨水 50〜80 mg/L と土層下の涵養水 100〜300 の比 / **数値設定** |
| dissol_dzmax | 0 | 1 セル・1 更新の溶食量の上限 | **数値設定** 0 = 無効。fluv_dzmax と同型の安全弁(超過は飽和として捨てる) |
| dissol_fsink / dissol_fres | 1.0 / 0 | 吸込穴流入水の溶解能の比 / 残渣率 | **経験値** 校正前提 / **与件** 0 = 残渣なし |
| dissol_lat | 0 | 側方溶食の配分割合 p | **方式** 0 = 床のみ、−1 = 濡れ面の面積比で自動(推奨)。固定値は湛水深/格子幅の比から |
| rock_kp / rock_tauc | 0(剥離なし)/ なし | 剥離の速度係数 (m/s) / 閾値 (Pa)(§7 の岩盤下刻) | **校正値** 標準値がない。k_p は τ_b = 2τ_c での裸岩の下刻速度 |
| rock_m | 1 | 剥離のべき指数 | **慣用値** 線形(側岸侵食の berode_m と同じ) |
| rock_beta | 0(研磨なし) | 研磨係数 β (1/m) | **校正値** 標準値がない。研磨による下刻速度の最大(被覆率 1/2)は β q_c / 4 |
| rock_hstar | なし | 被覆の長さ H* | **与件** 岩盤面の起伏・礫径の目安(数 cm〜数十 cm)。露出率と利用可能率に共用 |
| rock_kdb / rock_taucdb | 0(土石流の項なし)/ なし | 土石流による岩盤侵食の速度係数 (m/s) / 閾値 (Pa) | **校正値** 標準値がない。k_d は τ_d = 2τ_cd での裸岩の低下速度。1 回の土石流で mm〜cm の低下が目安[^stock05][^mccoy13] |
| rock_mdb | 1 | 土石流の項のべき指数 | **慣用値** 線形(rock_m と同じ) |
| fn_rock | なし(全域 1) | 岩盤の侵食性倍率 | **与件** 岩質の差。0 = 侵食しない |

**既定値を見直すときの手がかり**

- 粒径(d50)・空隙率・比重は河床材料調査(粒度試験)で直接得られ、
  限界無次元掃流力は Shields 曲線[^shields36]を粒径レイノルズ数で引き
  ます(砂〜礫では 0.03〜0.06)。
- 流砂量式は、対象河川の実測流砂量があればそれで式と係数を選びます。
  なければ砂礫床では芦田・道上[^ashida72]、粗い礫床では MPM[^mpm48]が
  常用です。
- クリープ・土層生成・隆起は長期地形の量で、宇宙線生成核種による
  侵食速度・土層生成速度の文献[^heimsath97]と、地域の隆起速度
  (水準測量・段丘面の年代)で与えます。
- 面状侵食・乾式侵食の係数は普遍値がなく、土砂流出の観測(濁度・
  貯水池堆砂)か既往事例の地形変化量に合わせて校正します。

## 9. 検証ケース

| ケース | 内容 | 要点 |
|---|---|---|
| [test/creep](../../test/creep/README.md) | ガウス丘の拡散 | 解析解に最大誤差 7.8e-5 m、morfac 等価性。深さ依存クリープの岩盤面の不変・土層の保存・裸岩で不変 |
| [test/fluvial](../../test/fluvial/README.md) | 閉領域の段波と河床変動 | 固体総量・共動更新が機械精度 |
| [test/suspend](../../test/suspend/README.md) | 2 つの平衡濃度式 | 固体総量 2.2e-15 |
| [test/sedinflow](../../test/sedinflow/README.md) | 境界からの土砂供給 | 流入総量の台帳閉合 ~1e-16 |
| [test/wash](../../test/wash/README.md) | 降雨 + 段波の斜面浸食 | 固体総量 1.7e-13 |
| [test/splash](../../test/splash/README.md) | 遷緩点斜面の乾式侵食 | 解析形に全桁一致、排出台帳一致 |
| [test/splashslide](../../test/splashslide/README.md) | 固結 / 未固結の崖 | 起伏の成長率 ×1.34 / ×0.77 |
| [examples/badland](../../examples/badland/) | 台地と崖の谷形成 | 表面流ゼロのまま崖縁から谷が成長 |
| [test/rockinc](../../test/rockinc/README.md) | 流水による岩盤下刻 | 自己被覆の解析解 9e-8、被覆の準定常 4e-4、研磨の山形 7e-4、閉じた箱の保存(台帳と 9 桁)、谷頭の給砂の下の定常勾配が準解析解と 1.5 % 以内・土砂収支 4e-10 |
| [examples/bedrock_cover](../../examples/bedrock_cover/README.md) | 岩盤河道の被覆効果 | 3 モデルの定常の下刻速度が理論と 2.3 % 以内、同じ総量の一定給砂とパルス給砂、初期の被覆、段差の後退 |
| [examples/mountain_valley](../../examples/mountain_valley/README.md) | V 字谷の斜面と渓流の連成 | 定常の斜面が斜面だけの予測と 0.14 %、渓流の勾配が渓流だけの式に斜面の供給を足した予測と 1.1 % 以内。基準面の低下への応答。同じ平均のパルス給砂で研磨だけの渓流は 1.40 倍急 |
| [test/hillsoil](../../test/hillsoil/README.md) | 風化による土層生成と定常斜面 | 一様・分布(fn_wthr)の解析解に 1.6e-15、倍率 0 のセルの不変。隆起・風化・深さ依存クリープの定常斜面で土層厚が H_ss と 0.12 %、横断の曲率が −U/D_eff と 1.1 % |

## 参考文献

[^roelvink06]: Roelvink, J. A. (2006): Coastal morphodynamic evolution techniques. *Coastal Eng.*, 53, 277–287.(MORFAC 法)
[^shields36]: Shields, A. (1936): Anwendung der Ähnlichkeitsmechanik und der Turbulenzforschung auf die Geschiebebewegung. Mitt. Preuss. Versuchsanst. Wasserbau Schiffbau, 26, Berlin.
[^culling60]: Culling, W. E. H. (1960): Analytical theory of erosion. *J. Geol.*, 68, 336–344.(斜面の線形拡散モデル)
[^fernandes97]: Fernandes, N. F. and Dietrich, W. E. (1997): Hillslope evolution by diffusive processes: The timescale for equilibrium adjustments. *Water Resour. Res.*, 33, 1307–1318.(拡散係数の文献域)
[^johnstone15]: Johnstone, S. A. and Hilley, G. E. (2015): Lithologic control on the form of soil-mantled hillslopes. *Geology*, 43(1), 83–86. doi:10.1130/G36052.1(要旨で確認: 輸送が勾配と土層厚の両方に比例すると、岩質が土層に覆われた斜面の形に現れる。式の形と doi は Landlab の DepthDependentDiffuser の説明による)
[^ashida72]: 芦田和男・道上正規 (1972): 移動床流れの抵抗と掃流砂量に関する基礎的研究. 土木学会論文報告集, 206, 59–69.
[^mpm48]: Meyer-Peter, E. and Müller, R. (1948): Formulas for bed-load transport. *Proc. 2nd Meeting IAHSR*, Stockholm, 39–64.
[^exner25]: Exner, F. M. (1925): Über die Wechselwirkung zwischen Wasser und Geschiebe in Flüssen. *Sitzungsber. Akad. Wiss. Wien, Math.-Naturwiss. Kl.*, 134, 165–204.
[^itakura80]: Itakura, T. and Kishi, T. (1980): Open channel flow with suspended sediments. *J. Hydraul. Div. ASCE*, 106(HY8), 1325–1343.(実装の形は iRIC「実践河川水理学」第 4 章の式(3)–(5)による)
[^rubey33]: Rubey, W. W. (1933): Settling velocities of gravel, sand, and silt particles. *Am. J. Sci.*, 25, 325–338.
[^partheniades65]: Partheniades, E. (1965): Erosion and deposition of cohesive soils. *J. Hydraul. Div. ASCE*, 91(HY1), 105–139.
[^trottet25]: Trottet, B., Noto, D., Jerolmack, D. J. and Ulloa, H. N. (2025): Sandball genesis from raindrops. *Proc. Natl. Acad. Sci. USA*, 122(52), e2519392122.(雨滴による粒子集合体の転動)
[^smith72]: Smith, T. R. and Bretherton, F. P. (1972): Stability and the conservation of mass in drainage basin evolution. *Water Resour. Res.*, 8, 1506–1529.
[^perron09]: Perron, J. T., Kirchner, J. W. and Dietrich, W. E. (2009): Formation of evenly spaced ridges and valleys. *Nature*, 460, 502–505.
[^heimsath97]: Heimsath, A. M., Dietrich, W. E., Nishiizumi, K. and Finkel, R. C. (1997): The soil production function and landscape equilibrium. *Nature*, 388, 358–361.
[^coulthard13]: Coulthard, T. J., Neal, J. C., Bates, P. D., Ramirez, J., de Almeida, G. A. M. and Hancock, G. R. (2013): Integrating the LISFLOOD-FP 2D hydrodynamic model with the CAESAR model: implications for modelling landscape evolution. *Earth Surf. Process. Landforms*, 38, 1897–1906.
[^white84]: White, W. B. (1984): Rate processes: chemical kinetics and karst landform development. In: La Fleur, R. G. (ed.) *Groundwater as a Geomorphic Agent*, Allen & Unwin, 227–248.(最大削剥速度 D = (P − E) c_eq/ρ)
[^gabrovsek09]: Gabrovšek, F. (2009): On concepts and methods for the estimation of dissolutional denudation rates in karst areas. *Geomorphology*, 106, 9–14.
[^howard83]: Howard, A. D. and Kerby, G. (1983): Channel changes in badlands. *Geol. Soc. Am. Bull.*, 94, 739–752.(岩盤河道の侵食速度を出水時の底面せん断で表す。要旨で確認)
[^shobe17]: Shobe, C. M., Tucker, G. E. and Barnhart, K. R. (2017): The SPACE 1.0 model. *Geosci. Model Dev.*, 10, 4577–4604. doi:10.5194/gmd-10-4577-2017(被覆の指数形は Landlab のソースで確認)
[^sklar04]: Sklar, L. S. and Dietrich, W. E. (2004): A mechanistic model for river incision into bedrock by saltating bed load. *Water Resour. Res.*, 40, W06301. doi:10.1029/2003WR002496
[^turowski07]: Turowski, J. M., Lague, D. and Hovius, N. (2007): Cover effect in bedrock abrasion. *J. Geophys. Res.*, 112, F04006. doi:10.1029/2006JF000697
[^zhang15]: Zhang, L., Parker, G., Stark, C. P., Inoue, T., Viparelli, E., Fu, X. and Izumi, N. (2015): Macro-roughness model of bedrock–alluvial river morphodynamics. *Earth Surf. Dynam.*, 3, 113–138. doi:10.5194/esurf-3-113-2015(要旨で確認)
[^stock03]: Stock, J. D. and Dietrich, W. E. (2003): Valley incision by debris flows: Evidence of a topographic signature. *Water Resour. Res.*, 39(4), 1089. doi:10.1029/2001WR001057(要旨で確認: 勾配–面積の逆べき則は勾配 0.03〜0.10 より急な所にほとんど延びない)
[^stock05]: Stock, J. D., Montgomery, D. R., Collins, B. D., Dietrich, W. E. and Sklar, L. S. (2005): Field measurements of incision rates following bedrock exposure: Implications for process controls on the long profiles of valleys cut by rivers and debris flows. *Geol. Soc. Am. Bull.*, 117(1–2), 174–194. doi:10.1130/B25560.1(要旨で確認: 弱い岩の谷の侵食ピンで最大 cm/年。土石流の谷では間欠的な土石流が主な担い手)
[^stock06]: Stock, J. D. and Dietrich, W. E. (2006): Erosion of steepland valleys by debris flows. *Geol. Soc. Am. Bull.*, 118(9/10), 1125–1148.(要旨と紹介で確認: 粒子衝突の慣性垂直応力に基づく侵食則。式の形は未照合)
[^hsu08]: Hsu, L., Dietrich, W. E. and Sklar, L. S. (2008): Experimental study of bedrock erosion by granular flows. *J. Geophys. Res.*, 113, F02001. doi:10.1029/2007JF000778(要旨と紹介で確認)
[^mccoy13]: McCoy, S. W., Tucker, G. E., Kean, J. W. and Coe, J. A. (2013): Field measurement of basal forces generated by erosive debris flows. *J. Geophys. Res. Earth Surf.*, 118, 589–602. doi:10.1002/jgrf.20041(要旨で確認: 岩盤の床が観測期間に 36〜64 mm 低下。厚さ約 5 cm の堆積物が衝突から床を守る)
[^mcguire23]: McGuire, L. A. ほか (2023): Steady-state forms of channel profiles shaped by debris flow and fluvial processes. *Earth Surf. Dynam.*, 11, 1117–1143. doi:10.5194/esurf-11-1117-2023(要旨で確認: 流動深と勾配の関数の侵食則の族。共著者の一覧は未照合)
