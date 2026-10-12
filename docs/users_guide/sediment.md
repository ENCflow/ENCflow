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

Exner の河床連続式[^exner25]そのものです。3 層のクランプで数値的な
行き過ぎを防ぎます: (1) 風上セルの土層厚 $`s_d`$ を超える侵食は
エッジ単位で起こさない、(2) 1 更新の河床変動を `fluv_dzmax`(既定
0.05 m)で制限する(地形波のクーラン条件に相当。発動回数は終了時に
表示)、(3) 複数エッジの同時流出で岩盤面を割った分は最終的に切り捨て、
失った体積を表示します。開境界では流出側は常に容量輸送、流入側は
`fluv_bcfeed = 1` のとき平衡給砂です。

**既定値。** `fluv_d50` = 0.01 m は砂床(0.5 mm)と山地礫床(5 cm)の
幾何平均付近で、砂床・礫床の目安は章末の推奨値にあります。`fluv_porosity`
= 0.4、`fluv_sgrav` = 1.65 は砂礫の標準値です。検証:
[test/fluvial](../../test/fluvial/README.md)(固体総量 4.6e-16、共動更新
1.2e-14)、[test/sedinflow](../../test/sedinflow/README.md)(境界からの
土砂供給の台帳閉合)。

## 4. 浮遊砂(f_suspend)

**輸送。** 濃度 $`C = h_s/h`$ は水の体積あたりの固体体積で、水柱の
移流は浅水流計算のステップ内で水と同じエッジ流量により風上輸送されます
(一様濃度は一様のまま、という性質が式の形で保証されます)。
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
(Smith & Bretherton の無限波数問題[^smith72])ため、谷間隔を選ぶには
弱い `f_creep` の併用が要り、間隔は増幅 $`c_b`$ と拡散 $`D`$ の比で決まります
(Perron らの $`\lambda \propto \sqrt{K_s/K}`$ と同じ構図[^perron09])。
`spl_dzmax` は暴走の安全弁です。既定 $`k_r`$ = 0.0005、$`k_t`$ = 0.05 は
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
減衰深の代表値です。

**隆起。** $`z \mathrel{+}= U\,\Delta t_s`$($`s_d`$ 不変 = 基岩ごと上昇)。
$`U`$(`uplift0`、既定 1 mm/yr)は造山帯の代表値の下限で、負値は沈降です。
海域マスクのセルは侵食基準面として対象外です。
長期の地形発達は「代表水文の反復 × MORFAC × リスタート連鎖」で
地形時間を稼ぐ CAESAR-Lisflood 型[^coulthard13]の実行様式を想定して
います(developer.md §32)。

## 8. パラメータと既定値の根拠

| パラメータ | 既定 | 意味 | 根拠 |
|---|---:|---|---|
| dt_geomorph / morfac | 0 / 1 | 地形更新間隔 (s) / 地形時間の加速(§1) | MORFAC 法[^roelvink06]。イベント計算は 1 |
| creep_d | 0.005 m²/yr | クリープ拡散係数 $`D`$(§2) | 文献域 0.001〜0.05 m²/yr の中央[^fernandes97] |
| f_qbform | 1 | 流砂量式(§3) | 1: 芦田・道上[^ashida72]、2: MPM[^mpm48] |
| fluv_d50 | 0.01 m | 掃流砂の代表粒径 | 砂床〜礫床の幾何平均付近(経験値) |
| fluv_tausc / susp_tausc / wash_tausc | 0.05 | 限界無次元掃流力(§1) | Shields 曲線の粗砂〜礫の代表値[^shields36] |
| fluv_porosity / fluv_sgrav | 0.4 / 1.65 | 河床の空隙率 / 水中比重 | 砂礫の標準値 |
| fluv_dzmax | 0.05 m | 1 更新の河床変動上限(§3) | 数値的安全弁(地形波のクーラン条件相当) |
| fluv_bcfeed | 0 | 開境界の給砂(§3) | 0: 無給砂、1: 平衡給砂 |
| f_esform | 1 | 平衡濃度式(§4) | 1: 簡易(校正用)、2: 板倉・岸(砂では推奨)[^itakura80] |
| susp_d50 / susp_wf | 0.2 mm / 0 | 浮遊砂の粒径 / 沈降速度 | 細砂の代表。0 なら Rubey[^rubey33] |
| susp_beta | 1.0 | 底面濃度係数 $`\beta`$ | 1 = 鉛直一様の近似 |
| susp_esa | 1e-4 | 簡易式の係数 | test/suspend の校正値(経験値) |
| wash_kr / wash_kf | 0.01 / 1e-5 m/s | 雨滴 / 面状侵食係数(§5) | test/wash の値(経験値、校正前提) |
| spl_kr / spl_kt / spl_h | 5e-4 / 0.05 / 1 | 乾式侵食の係数と勾配指数(§6) | テストの中央値(経験値) |
| spl_ca / spl_cb | 0 / 0 m | 凹地形増幅長 | 0 = 増幅なし。谷の成長には数 m〜数十 m |
| spl_dzmax | 0 | 1 更新の侵食上限 | 0 = 無効。暴走の安全弁 |
| wthr_p0 / wthr_sdstar | 50 mm/kyr / 0.5 m | 土層生成速度 / 減衰深(§7) | Heimsath 型[^heimsath97]の文献域の中央 |
| uplift0 | 1 mm/yr | 隆起速度 | 造山帯の代表値の下限 |

## 9. 検証ケース

| ケース | 内容 | 要点 |
|---|---|---|
| [test/creep](../../test/creep/README.md) | ガウス丘の拡散 | 解析解に最大誤差 7.8e-5 m、morfac 等価性 |
| [test/fluvial](../../test/fluvial/README.md) | 閉領域の段波と河床変動 | 固体総量・共動更新が機械精度 |
| [test/suspend](../../test/suspend/README.md) | 2 つの平衡濃度式 | 固体総量 2.2e-15 |
| [test/sedinflow](../../test/sedinflow/README.md) | 境界からの土砂供給 | 流入総量の台帳閉合 ~1e-16 |
| [test/wash](../../test/wash/README.md) | 降雨 + 段波の斜面浸食 | 固体総量 1.7e-13 |
| [test/splash](../../test/splash/README.md) | 遷緩点斜面の乾式侵食 | 解析形に全桁一致、排出台帳一致 |
| [test/splashslide](../../test/splashslide/README.md) | 固結 / 未固結の崖 | 起伏の成長率 ×1.34 / ×0.77 |
| [examples/badland](../../examples/badland/) | 台地と崖の谷形成 | 表面流ゼロのまま崖縁から谷が成長 |

## 参考文献

[^roelvink06]: Roelvink, J. A. (2006): Coastal morphodynamic evolution techniques. *Coastal Eng.*, 53, 277–287.(MORFAC 法)
[^shields36]: Shields, A. (1936): Anwendung der Ähnlichkeitsmechanik und der Turbulenzforschung auf die Geschiebebewegung. Mitt. Preuss. Versuchsanst. Wasserbau Schiffbau, 26, Berlin.
[^culling60]: Culling, W. E. H. (1960): Analytical theory of erosion. *J. Geol.*, 68, 336–344.(斜面の線形拡散モデル)
[^fernandes97]: Fernandes, N. F. and Dietrich, W. E. (1997): Hillslope evolution by diffusive processes: The timescale for equilibrium adjustments. *Water Resour. Res.*, 33, 1307–1318.(拡散係数の文献域)
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
