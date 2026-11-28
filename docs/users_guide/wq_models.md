# 水質モデルの解説(水質・負荷流出の補足)

[水質の章へ](wq.md) | [ユーザーガイド目次へ](../users_guide.md)

[水質・負荷流出の章](wq.md)の各過程 — 輸送、発生源、一次減衰、沈降、
Kd 二相分配、浸透同伴と地下水経由の輸送、表面蓄積と洗い出し、貯水池、
下水噴出、水平の混合、蒸発による濃縮と析出・溶解 — の式と代表値の根拠をまとめます。実装は `src/m_wq.f90`
(発生源・鉛直交換・台帳)と、輸送を担う `src/m_swflow_enc.f90`
(`advect_scalar`)・`src/m_gwflow_lateral.f90`(地下の同伴輸送)で、
設計の経緯は developer.md §30・§139 と docs/wq_metal_plan.md にあります。

## 1. 状態量と輸送

地表水の物質は**柱状量** $`c_q`$(g/m²。セル内質量 = $`c_q\,g_v\,w\,A`$)で
持ち、濃度は $`C = c_q/v_h`$(mg/L = g/m³。$`v_h`$ は断面形 σ を考慮した
矩形換算水深)です。水平輸送は浮遊砂と同じ保存輸送カーネルで、
浅水流計算のステップ内に水と同じエッジ流量で風上輸送します
([ENC 格子の解説](encgrid.md) §3)。一様濃度は一様のまま、質量は
機械精度で保存されます。1 次風上なので数値拡散があり、縦断に
$`D \approx u\,\Delta x\,(1 - Cr)/2`$(浅水流の dt では Cr = uΔt/Δx が
0.1〜0.2 なので実質 $`u\Delta x/2`$。u = 1 m/s・Δx = 10 m で 4 m²/s)、
横断には流れがなくても 8 方向リンクの斜め配分による
$`D_y \approx 0.29\,u\,\Delta y`$ が生じます([test/tracer](../../test/tracer/README.md)
で計測。理論値と 5 % 以内)。既定の `f_scalar_scheme = 3`(リンクごとの
MUSCL。[移流項](advection.md) §7)はこれを縦断で 1/3〜1/5、横断で 1/14 に
抑えます。濃度フロントの到達時刻やピーク濃度を見る用途で足りなければ
格子幅を細かくしてください。総量・積分量には効きません。地下の質量プール $`c_g`$(幾何面積基底)、
表面蓄積プール $`B`$(g/m²)、貯水池プール、ため池プールが地表水と
やりとりします。発生源(点源 g/s、面源・分布 kg/ha/day、降雨中濃度
mg/L、境界流入濃度)はすべて加算的で重ね合わせられます。
海域マスク(fn_sw)の海セルは質量を持たず(初期濃度の海域はゼロ化)、
海から陸への流入は既定では清水です(`wq_sea_conc` を与えると、海セルを供給元とする面の
濃度をその値にします。1 次風上。入った量は台帳の `in_sea_g`)。海セルは輸送の受け手にならないので、海セルへ
流れ込んだ質量はそのまま系外へ出ます。海セルへの流出と開いた辺の出入りは、
輸送カーネルが面ごとに、濃度の更新と同じ流束 × 供給元濃度で数え、台帳の
`out_sea_g`・`out_edge_g`・`in_edge_g` 列に積みます(台帳が閉じる。浮遊砂など
ほかの輸送物質には列がなく、収支残差として扱います。[土砂・地形変化](geomorph.md))。
水位規定セル([境界条件](boundary.md))も系外の水で、毎ステップ柱状量を境界濃度
(`wq_stage_conc`。既定 0)× 矩形換算水深に戻し、そのときの出入りを `out_stage_g`・
`in_stage_g` 列に積みます。

## 2. 一次減衰

```math
c^{\,n+1} = c^{\,n}\,e^{-k\,\Delta t},
\qquad
k = \frac{\ln 2}{T_{1/2}}\ (\texttt{wq\_thalf})
\quad\text{または}\quad
k = \texttt{wq\_k20}
```

指数の厳密係数を毎ステップ、地表 $`c_q`$・地下 $`c_g`$・表面プール
$`B`$・貯水池・ため池のすべてに掛けます(無条件安定)。温度補正
$`k(T) = k_{20}\,\theta^{T-20}`$ は未実装で、20 ℃ 基準の値を与えます。
代表値の根拠: BOD の脱酸素係数 0.1〜0.5 /day は Streeter–Phelps 系
[^streeter25][^chapra97]、大腸菌の死滅は $`k = \ln 10/T_{90}`$ で
$`T_{90}`$ 0.5〜2 日(日射・水温に依存)、Cs-137 の半減期 30.17 年、
農薬の半減期は農薬物性データベース[^wauchope92]によります。

## 3. 沈降

**単相(wq_vs)。** 地表水の全物質量を速度 $`v_s`$ で沈めます。

```math
\Delta c_q = -\,c_q\,\min\!\left(\frac{v_s\,\Delta t}{v_h},\ 1\right),
\qquad v_s = \frac{\texttt{wq\_vs}}{86400}
```

$`v_h \le d_d`$(乾燥)のセルでは沈みません。行き先は `f_wq_settle`
(0: 河床へ消失、1: 表面蓄積プールへ)で、どちらでも台帳 `settle_g` に
計上します。粒子の代表値は Stokes 則 $`v_s = (\rho_s - \rho)g d^2/(18\mu)`$
から(粘土 2 µm で 0.3 m/day、シルト 10 µm で 8 m/day)。

**Kd 二相分配(wq_kd)。** 浮遊砂(`f_suspend`)の質量濃度
$`C_{ss} = \rho_s h_s/v_h`$(kg/m³)と平衡分配係数 $`K_d`$ から溶存率を
毎ステップ求め、粒子態だけを浮遊砂の沈降速度 $`w_f`$ で沈めます。

```math
f_d = \frac{1}{1 + K_d\,C_{ss}},
\qquad K_d\,[\mathrm{m^3/kg}] = 10^{-3}\,\texttt{wq\_kd}\,[\mathrm{L/kg}],
\qquad
\Delta c_q = -\,(1 - f_d)\,c_q\,\min\!\left(\frac{w_f\,\Delta t}{v_h},\ 1\right)
```

輸送する状態は $`c_q`$ 一本のまま(両相とも水と同じ速度で動き、差は
鉛直交換だけに現れる)という最小構成です。$`(1 - f_d)c_q w_f/v_h`$ は
「金属/砂の質量比 × 砂の沈着フラックス $`w_f C_{ss}`$」と恒等で、
粒子態のグロス沈着を表します。河床からの再懸濁は表面蓄積プール +
せん断洗い出し(§5)が担うので、`f_wq_settle = 1` を推奨します。
$`K_d`$ の文献値(Pb 10⁴〜10⁶、Cu・Zn・Cd 10³〜10⁵、As 10¹〜10³ L/kg、
Cs 10³〜10⁴)は Sheppard & Thibault[^sheppard90]、IAEA TRS-472[^iaea10]、
US EPA[^epa99]の編集値で、対象流域の懸濁態/溶存態比から逆算するのが
確実です。

![Kd 分配の溶存率と表面蓄積・洗い出し](../figs/wq_models.png)

## 4. 浸透同伴と地下水経由の輸送

**浸透同伴(f_wq_infil = 1)。** 地下水モデルの浸透量 $`f_x`$ に
柱状量を同率で同伴させます(Kd 有効時は溶存分 $`f_d`$ だけ)。

```math
\Delta c_q = -\,f_d\,c_q\,\frac{f_x}{h + f_x},
\qquad c_g \mathrel{+}= -\Delta c_q\,g_v\,w
```

**地下の輸送と湧出(f_gwlateral = 1 のとき自動)。** 地下水の側方流量
$`q`$ に風上の体積濃度を掛けた質量フラックスを同時に運び、飽和超過の
湧出 $`f_s`$ に同率で同伴して地表へ戻します。遅延化係数 $`R`$(`wq_rg`)は
土中の平衡吸着による遅れをまとめた係数で、物質は地下水の $`1/R`$ の
速度で動きます。

```math
q_m = \frac{1}{R}\,\frac{c_{g,up}}{h_{g,up}}\,q,
\qquad
\Delta c_g^{\,seep} = -\frac{1}{R}\,c_g\,\frac{f_s}{h_g + f_s},
\qquad
R = 1 + \frac{\rho_b K_d}{\theta}
```

$`R`$ の式は線形平衡吸着の遅延係数の標準形[^freeze79]で、乾燥かさ密度
$`\rho_b`$、有効間隙率 $`\theta`$ から前処理で見積もって与えます
(重金属・Cs では 10²〜10⁴)。減衰は地下プールにも働きます。
質量を同伴するのは層 1 の側方流・飽和湧出と揚水(湧出と同じ形で系外へ。
§6)で、風化基岩層への浸透・管路層への浸入水は水だけが動き質量は層 1 に
残ります(層 1 の濃度が見かけ上高くなり、層 2・管路経由の戻り水は清水に
なる)。検証:
[test/gwseep](../../test/gwseep/README.md)(浸透 → 側方 → 湧出 → 再浸透の
循環で台帳 to_gw − seep = mass_gw が閉合、$`R`$ = 1e12 で不動)。

## 5. 表面蓄積と洗い出し(buildup–washoff)

晴天時の蓄積と降雨時の洗い出しで、流量と負荷の非線形な L–Q 関係と
ファーストフラッシュを機構的に表します(都市排水モデル SWMM の
buildup–washoff[^rossman15]と同じ枠組み)。

```math
\frac{dB}{dt} = r\left(1 - \frac{B}{B_{\max}}\right)
\quad(\texttt{wq\_bd\_max} 省略で\ dB/dt = r),
\qquad
\lambda = k_r\,P + k_f\,\max\!\left(\frac{\tau}{\tau_c} - 1,\ 0\right),
\qquad
\Delta B = B\left(1 - e^{-\lambda\Delta t}\right) \to c_q
```

$`r`$ は蓄積レート(`wq_bd_rate` または分布 `fn_wq_map` の `f_wq_map = 1`)、
$`P`$ は地表到達降雨強度、$`\tau = \rho g n^2 |\mathbf{V}|^2/h^{1/3}`$ は
Manning 則で閉じた河床せん断応力(N/m²)です。蓄積の更新は指数の
厳密形で無条件安定、洗い出しは湿潤セルだけに働きます。雨滴項は SWMM の
指数型洗い出し(指数 1)と $`k_r\,[1/\mathrm{m}] = 1000\,c_1\,[1/\mathrm{mm}]`$
で互換で、超線形性(指数 > 1 相当)はせん断項が担います。
放射性核種の沈着マップは「レート 0 + 初期プール `fn_wq_bd0` + 洗い出し +
減衰」で表せます。

## 6. 貯水池・ため池・下水噴出

**貯水池(完全混合)。** [構造物](structure.md)のダム・湖沼に捕捉された
質量 $`M`$ は貯水量 $`V`$ の完全混合プールに貯まり、放流水(スピルを含む)
には $`M/V`$ の濃度が同伴します。池内の沈降は未実装です。水位固定湖沼に
入った質量は水と同じく系外へ出ます(台帳 `to_dam_g`)。ため池
(`rscap`)が吸収した質量はセル別プールに貯まり、戻り経路はありません
(蒸発では水だけが抜けて濃縮)。検証: [test/damwq](../../test/damwq/README.md)
(解析解との全桁一致)。

**下水噴出(wq_gwc_conc)。** [管路連続体層](gwflow_models.md#6-管路連続体層f_gwconduit--1)
からの噴出・陸側吐口の放流量 $`q_{out}`$ に固定濃度 $`C_{sew}`$ を掛けた
負荷 $`q_{out}C_{sew}`$ を地表に投入する**供給側固定濃度近似**です。
管内の収支・希釈は解きません。枡に飲まれた負荷は `f_wq_gwc_in = 1` で
管路側へ除去されます(台帳 `to_gwc_g`)。大腸菌は「g = 10⁶ CFU」と
読み替えて $`C`$ [単位/m³] × 100 = CFU/100 mL です。下水の大腸菌
10⁵〜10⁷ CFU/100 mL、合流式越流で 1 桁低い値、$`T_{90}`$ 数時間〜数日は
[章の代表値表](wq.md#代表値の目安設定の出発点)にあり、ふん便性指標の
死滅速度の水準は水浴場・衛生工学の標準教科書[^chapra97]の範囲です。
検証: [test/sewer_wq](../../test/sewer_wq/README.md)。

**構造物・取水(同率移動)。** [構造物](structure.md)のポンプ・カルバート・
分水と内部ソースの吸い込みが水深 $`h`$ のセルから $`\Delta h`$ を汲むとき、
柱状量の同じ割合(Kd 有効時は溶存分 $`f_d`$ だけ)を取り出し、その質量を
水と同じセル数等分で送り先の柱状量へ足します(送り先のない取水は系外 =
台帳 `out_intake_g`)。

```math
\Delta c_q = -\,f_d\,c_q\,\frac{\Delta h}{h},
\qquad m = -\Delta c_q\,g_v\,w\,A
```

ため池から汲む分はため池プール、管路から汲むポンプ(`f_pump_src = 1`)は
固定濃度 `wq_gwc_conc` の水、井戸揚水は §4 の湧出と同じ形
$`\Delta c_g = -(1/R)\,c_g\,f/h_g`$($`f`$ は汲んだ水深)で系外へ出します。
取水セル内の完全混合を仮定する独自の簡略化で(浸透同伴と同じ同率移動)、
管内の到達時間・混合・沈降は表しません。粒子態は浮遊砂と一緒に取水側に
残ります(構造物は土砂を運ばない)。同じステップにため池が吸収した水・
降った雨の物質はステップの後に加わるため、そのステップの取水には乗りません
(相対で 1 ステップの流入量 / 貯留量の偏り)。検証:
[test/wqstruct](../../test/wqstruct/README.md)。

## 7. 水平の混合

`wq_diff`(混合係数 $`D`$ [m²/s])を与えると、移流に加えて、濃度の勾配に比例する拡散の流束を
水深で積分した形で足します。

```math
\frac{\partial (v_h C)}{\partial t} + \nabla\!\cdot(\boldsymbol{q}\,C)
 = \nabla\!\cdot\left(D\,v_h\,\nabla C\right)
```

離散化は移流と同じ 8 近傍のリンクで、リンク $`k`$(通過幅 $`l_k`$、中心間距離 $`\Delta r_k`$)の流束を
$`D\,h_e\,(C_i - C_n)\,l_k/\Delta r_k`$ とします。界面の水深 $`h_e`$ は両側の矩形換算水深の浅い方、
通過幅係数は移流と同じ(堤防の仮想壁面と閉じた開口は通さない)で、両側とも水のある陸のセルの間に
だけ働きます。流束は両側のセルから同じ値で数えるので質量を保存し、一様な濃度は一様のままです。
8 近傍の通過幅の配分(斜めの配分比 $`d`$)によらず、静水の中の分布の分散は各方向に
$`2Dt`$ ずつ増え、共分散は増えません([test/wqsalt](../../test/wqsalt/README.md) の mix。丸めの範囲で
一致)。陽解法の安定条件は

```math
D\,\Delta t \sum_{k=1}^{8} \frac{l_k}{\Delta r_k} \le \Delta x\,\Delta y
```

で(正方形の格子で $`\sum l_k/\Delta r_k = 4 - 2d`$。$`d`$ = 0.59 なら $`D \le 0.35\,\Delta x^2/\Delta t`$)、
超える値は初期化で止めます。サブグリッド河道幅・断面形のセルと家屋の空隙率が 1 より小さいセルでは、
リンクの面積に両側の平面積率・空隙率の小さい方を掛けます(リンクの開いている割合の目安。独自の
簡略化で、上の安定条件はこの場合も足ります。質量の保存と、濃度が一様になることは
[test/wqsalt](../../test/wqsalt/README.md) の mixgv・mixwd)。

$`D`$ は風・渦・二次流・流速分布のずれによる混合を 1 つの係数に代表させた校正量です。目安として、
川の横断方向の混合は $`\varepsilon_t \approx 0.15\,h\,u_*`$(直線の水路)〜 $`0.6\,h\,u_*`$(緩く蛇行する
自然河川。±50 %。$`u_*`$ は摩擦速度)[^fischer79]、湖・海の水平の混合は広がりの大きさ $`\ell`$ とともに増え、
染料の拡散実験をまとめた経験則 $`K_a = 0.0103\,\ell^{1.15}`$(cm²/s、$`\ell`$ は cm)[^okubo71]では
1 km で 0.6 m²/s、10 km で 8 m²/s、100 km で 100 m²/s 程度です。数値拡散(§1)より小さい値は
効きません。風による吹送流・密度による循環は解かないので、湖の全体が混ざる速さは $`D`$ の与え方で
決まります。

## 8. 蒸発による濃縮と、析出・溶解

蒸発散は水だけを抜きます(地表水・ため池・地下水のどれからも)。物質は残るので、水深 $`h`$ の水柱の
濃度は $`C = c_q/h`$ のまま上がります。`wq_csat`(溶解度 $`C_s`$)を与えると、毎ステップ、
セルごとに次を行います(析出物は表面蓄積プール $`B`$ に置く)。

```math
\text{析出:}\quad c_q > C_s v_h \ \Rightarrow\ B \leftarrow B + (c_q - C_s v_h),\quad c_q \leftarrow C_s v_h
```

```math
\text{溶解:}\quad c_q < C_s v_h,\ B > 0 \ \Rightarrow\
\Delta c_q = \min\!\left[(C_s v_h - c_q)\left(1 - e^{-k\,\Delta t/v_h}\right),\ B\right]
```

干上がったセル($`v_h \le`$ 限界水深 dd)では、水柱の物質をすべて $`B`$ へ移します。溶解の式は、
物質移動係数 $`k`$(`wq_kdis`)の一次の溶解 $`dC/dt = (k/v_h)(C_s - C)`$ を、ステップの中で厳密に
解いたものです(`wq_kdis` を与えなければ $`k \to \infty`$ = 飽和まで瞬時。固体の表面からの溶解を、
飽和濃度との差に比例する流束で表すのは溶解の標準的な扱いです[^noyes1897])。水深と析出物が一定なら
$`C(t) = C_s(1 - e^{-kt/h})`$ で、数値解は時間刻みによらずこれに一致します([test/wqsalt](../../test/wqsalt/README.md) の disk)。

地面にしみ込む水は、析出物を通るときに飽和までの余地の分だけ溶かして、地下の質量プールへ運びます。

```math
\Delta c_g = \min\!\left[(C_s - C_{inf})\,f_x\left(1 - e^{-k\,\Delta t/f_x}\right),\ B\right]
```

$`f_x`$ はそのステップの浸透量、$`C_{inf}`$ は浸透する水の濃度(浸透の前の地表水。乾いた地面に
しみ込む雨なら 0)です。地下では、水と一緒に動く濃度(側方流・湧出・井戸揚水の同伴。§4)を
$`\min(c_g/h_g,\ C_s)`$ にします(蒸発で水だけが抜けて溶解度を超えた分は土に残ります)。

析出の判定を水柱の濃度と溶解度の比較だけで行うこと、干上がりの判定に限界水深を使うこと、浸透水が
飽和まで溶かすとみなすことは、本モデルの簡略化です(独自)。溶解度の代表値は、塩化ナトリウムが
水 1 kg に約 360 g(25 ℃。温度による変化は小さい)[^haynes14]、石膏(硫酸カルシウム二水和物)が水 1 L に
2〜2.6 g 程度(25 ℃。資料によって幅があります)です。濃度は水の体積あたりの質量で、溶けた物質による体積の増加は数えません。
干上がる湖では、溶解度の小さい順に炭酸塩 → 石膏 → 芒硝 → 岩塩と析出し、アラル海の湖底の析出物は
石膏と芒硝が大半と見積もられています[^zavialov10]。この順序や物質の間の作用は表さないので、
物質ごとに溶解度を変えた別の計算にします。

## 9. パラメータと既定値の根拠

根拠欄の分類語の意味は[既定値の根拠の読み方](../users_guide.md#既定値の根拠の読み方)を参照してください。 水質は物質ごとに物性が桁で異なるため**物性には既定値を置きません**
(減衰・沈降・分配を書かなければ保存性トレーサ)。既定「—」の行の根拠欄は
代表値の出典です。

| パラメータ | 既定 | 意味 | 根拠 |
|---|---:|---|---|
| wq_c0 / fn_wq_c0 | 0 / — | 初期濃度 (mg/L)。一様な値か分布 | **与件** |
| wq_thalf / wq_k20 | — | 半減期 (day) / 一次減衰係数 (1/day)(§2) | **文献値** BOD 0.1〜0.5 /day[^streeter25][^chapra97]、大腸菌 $`\ln 10/T_{90}`$、Cs-137 11019 day、農薬 10〜60 day[^wauchope92] |
| wq_vs | — | 単相の沈降速度 (m/day)(§3) | **導出** Stokes 則: 粘土 2 µm 0.3、シルト 10 µm 8 m/day |
| wq_kd | — | 平衡分配係数 (L/kg)(§3。要 f_suspend) | **文献値** Pb 10⁴〜10⁶、Cu・Zn・Cd 10³〜10⁵、Cs 10³〜10⁴[^sheppard90][^iaea10][^epa99] |
| f_wq_settle | 0 | 沈降先。0: 消失、1: 表面プール | **方式** Kd と洗い出しを併用するなら 1 |
| f_wq_infil | 1 | 浸透同伴。1: 溶存態、0: 地表残留(§4) | **方式** 粒子態・病原指標は 0 |
| wq_rg | 1 | 地下輸送の遅延化係数 $`R`$(§4) | **導出** $`1 + \rho_b K_d/\theta`$[^freeze79]。重金属・Cs 10²〜10⁴ |
| wq_bd_rate / wq_bd_max / wq_bd0 | — | 蓄積レート (kg/ha/day)・上限・初期プール (kg/ha)(§5) | **文献値** SWMM の buildup の値域[^rossman15]。核種の沈着量マップは bd0 |
| wq_wash_kr | — | 雨滴洗い出し係数 (1/m) | **文献値** SWMM の指数型洗い出し $`c_1`$ [1/mm] × 1000[^rossman15] |
| wq_wash_kf / wq_wash_tauc | — | せん断洗い出し係数 (1/s)・限界せん断応力 (N/m²) | **校正量** 普遍値なし |
| wq_gwc_conc / f_wq_gwc_in | — / 1 | 噴出水の固定濃度 (mg/L)・枡流入の除去(§6) | **慣用値** 下水 10⁵〜10⁷ CFU/100 mL(章の表) / **方式** |
| wq_rain_conc / wq_in_conc | — | 降雨中濃度・境界流入濃度 (mg/L) | **与件** |
| wq_sea_conc | — | 海から陸へ入る水の濃度 (mg/L) | **与件** 海水の塩分は約 35 g/L |
| wq_diff | — | 水平の混合係数 $`D`$ (m²/s)(§7) | **校正量** 川の横断方向 0.15〜0.6 $`h u_*`$[^fischer79]、湖・海は広がり 1〜100 km で 0.6〜100 m²/s[^okubo71] |
| wq_csat | — | 溶解度 (mg/L)(§8) | **文献値** 塩化ナトリウム 3.6×10⁵[^haynes14]、石膏 2〜2.6×10³ |
| wq_kdis | —(瞬時) | 析出物の溶解の物質移動係数 (m/day)(§8) | **校正量** 普遍値なし。固まった・覆われた析出物を遅らせるときに与える |

**既定値を見直すときの手がかり**

- 減衰係数・分配係数は物質ごとのデータベースから引きます: 農薬は
  Wauchope ら[^wauchope92]、核種の Kd は IAEA の技術報告[^iaea10]と
  Sheppard & Thibault[^sheppard90]、重金属は EPA のレビュー[^epa99]。
  Kd は土壌の pH・有機物量・粘土含量で 1〜2 桁変わるため、対象流域の
  土壌条件に近い値を選び、上下限のケースで挟みます。
- 蓄積・洗い出しの係数は SWMM のユーザーマニュアル[^rossman15]の
  土地利用別の例と、対象地の L-Q 観測(降雨イベントの負荷量—流量)に
  よる校正が出発点です。
- 下水の濃度・T90 の代表値と読み替えは章の表(下水噴出の節)に
  まとめています。

## 10. 検証ケース

| ケース | 内容 | 要点 |
|---|---|---|
| [test/damwq](../../test/damwq/README.md) | ダム(完全混合)とため池 | 台帳が解析解に全桁一致 |
| [test/kdpart](../../test/kdpart/README.md) | Kd 分配と粒子態沈降 | 台帳の閉合と Kd 増加時の単調性 |
| [test/gwseep](../../test/gwseep/README.md) | 浸透 → 地下側方 → 湧出 | to_gw − seep = mass_gw、$`R`$ = 1e12 で不動 |
| [test/sewer_wq](../../test/sewer_wq/README.md) | 下水噴出の衛生リスク | 噴出 → 氾濫 → 拡散 → 減衰の台帳検算 |
| [test/tracer](../../test/tracer/README.md) | 1 次風上の数値拡散 | 清水前線の広がり D = u·Δx·(1−Cr)/2、定常プルームの横断分散 Dy = 0.29·u·Δy が理論値の 5 % 以内 |
| [test/wqstruct](../../test/wqstruct/README.md) | 構造物・取水の同率移動 | 濃度 1 mg/L の水がどの区画でも 1 のまま、台帳の閉合、out_intake_g = 系外へ出た水の体積 × 濃度 |
| [test/wqsalt](../../test/wqsalt/README.md) | 水平の混合、析出と溶解、海の濃度、初期濃度の分布 | 分散の増分 = 2·D·t、蒸発による析出が式に一致、溶解が $`C_s(1 - e^{-kt/h})`$ に一致、浸透水の溶解と地下の濃度の上限、台帳の閉合 |

## 参考文献

[^streeter25]: Streeter, H. W. and Phelps, E. B. (1925): A study of the pollution and natural purification of the Ohio River. *Public Health Bulletin*, 146, U.S. Public Health Service.
[^chapra97]: Chapra, S. C. (1997): *Surface Water-Quality Modeling*. McGraw-Hill.(減衰係数・死滅速度・沈降の標準教科書)
[^wauchope92]: Wauchope, R. D., Buttler, T. M., Hornsby, A. G., Augustijn-Beckers, P. W. M. and Burt, J. P. (1992): The SCS/ARS/CES pesticide properties database for environmental decision-making. *Rev. Environ. Contam. Toxicol.*, 123, 1–155.
[^sheppard90]: Sheppard, M. I. and Thibault, D. H. (1990): Default soil solid/liquid partition coefficients, Kds, for four major soil types: a compendium. *Health Phys.*, 59, 471–482.
[^iaea10]: IAEA (2010): Handbook of Parameter Values for the Prediction of Radionuclide Transfer in Terrestrial and Freshwater Environments. *Technical Reports Series*, 472.
[^epa99]: US EPA (1999): Understanding Variation in Partition Coefficient, Kd, Values. EPA 402-R-99-004A.
[^freeze79]: Freeze, R. A. and Cherry, J. A. (1979): *Groundwater*. Prentice-Hall.(線形平衡吸着の遅延係数)
[^rossman15]: Rossman, L. A. (2015): Storm Water Management Model User's Manual Version 5.1. US EPA, EPA/600/R-14/413b.(buildup–washoff)
[^fischer79]: Fischer, H. B., List, E. J., Koh, R. C. Y., Imberger, J. and Brooks, N. H. (1979): *Mixing in Inland and Coastal Waters*. Academic Press.(川の横断方向の混合係数)
[^okubo71]: Okubo, A. (1971): Oceanic diffusion diagrams. *Deep-Sea Res.*, 18, 789–802.(広がりの大きさと見かけの拡散係数の経験則)
[^noyes1897]: Noyes, A. A. and Whitney, W. R. (1897): The rate of solution of solid substances in their own solutions. *J. Am. Chem. Soc.*, 19, 930–934.(溶解の速さが飽和濃度との差に比例する)
[^haynes14]: Haynes, W. M. (ed.) (2014): *CRC Handbook of Chemistry and Physics*, 95th ed. CRC Press.(無機化合物の水への溶解度。塩化ナトリウムは 25 ℃ で水 100 g に 36.0 g)
[^zavialov10]: Zavialov and Zavialov (2010): アラル海の湖底の析出物の量の見積もり。EGU General Assembly 2010 の要旨 EGU2010-15141(<https://meetingorganizer.copernicus.org/EGU2010/EGU2010-15141.pdf>。2026-11-28 に Web 検索の結果の要約で確認。本文は未読)。
