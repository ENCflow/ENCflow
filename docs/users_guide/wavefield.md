# 沿岸の波浪場(fn_wavefield)

[ユーザーガイド目次へ](../users_guide.md)

沿岸の短周期の波(風波・うねり)の波高と波向を、浅水流と同じ格子・同じ時間発展の中で
求める機能です。沖の波(波高・周期・進行方向・方向分散)を領域の外縁の辺から入れ、
浅水変形(水深による波高の変化)・屈折(浅い側へ曲がる)・砕波・底面摩擦・
防波堤や島の背後の陰を計算します。

波は**位相平均**(1 波ずつの水面の上下は解かず、波のエネルギーの分布を解く)で、
**代表周期 1 個**、進行方向を **N_θ 個の方向ビン**に分けたエネルギーの平衡式を
解きます。HISWA[^hiswa]・XBeach の定常モード[^xbeach]・SnapWave[^snapwave] と同じ
階層の概算で、周波数の広がり・風による発達・波どうしの非線形相互作用は扱いません。

**段階的に実装しました。** 現在は段 W5 までで、**波浪場**(段 W1)、
**波による流れ(セットアップ・沿岸流。段 W2)**、**流れによる波の変化(ドップラー効果・
流れによる屈折・阻止。段 W3)**、**土砂の攪拌と輸送(沿岸漂砂・浜の侵食と回復。段 W4・W5)**を
計算します。流れへの作用は `wf_flow`、流れの波への作用は `f_wf_current`、土砂への作用は
[土砂・地形変化](geomorph.md)の `f_wfsed` で有効にします(どれも既定 0 = 作用なし。
`wf_flow = 0` かつ `f_wfsed = 0` なら `fn_wavefield` を書いても書かなくても浅水流と地形の
結果は同じです。[流れへの作用](#流れへの作用wf_flow段-w2)・
[流れによる波の変化](#流れによる波の変化f_wf_current段-w3)・[土砂への作用](#土砂への作用f_wfsed段-w4w5))。
研究的な拡張(段 W6)は docs/wavefield_plan.md §9。

[土砂・地形変化の章](geomorph.md)の「波浪による沿岸漂砂」(`fn_wave`。沖波を与件に
汀線帯の沿岸漂砂を CERC 型の式で与える簡易モード)とは別の機能です。

設計の経緯・代替案の比較・判断事項は docs/wavefield_plan.md、方針 5 の例外と
決定・実装・検証の記録は developer.md §0-5・§88 にあります。

## 有効化と設定

`&list_sysparam` で `fn_wavefield` を指定します(`"-"` なら同じパラメータファイル)。

```
&list_sysparam
  fn_wavefield = '-'
/
&list_wavefield
  wf_bc_side = 1, 0, 2, 2   ! 辺 W, E, N, S の型(0 吸収 / 1 入射 / 2 側方 Neumann)
  wf_hm0 = 1.5              ! 沖の波高 (m。不規則波は有義波高 H_m0)
  wf_trep = 8.0             ! 代表周期 (s)
  wf_dir = 0.0              ! 進行方向 (deg。x 軸 = 東から反時計回り、北 = 90)
  wf_spread = 20.0          ! 方向分散 σθ (deg)
/
```

**向きは「進む向き」です**(来る向きではありません)。x 軸(東)から反時計回りに
測り、北へ進む波が 90°、西へ進む波が 180° です。[土砂・地形変化の章](geomorph.md)の
`wave_dir` と同じ規約で、SWAN・XBeach の「来る向き」(nautical)とは 180° 違います。

**周期は代表周期 1 個です。** `wf_trep`(と `wf_val` の周期の列)は分散関係の
σ = 2π/T にそのまま使います。不規則波ではエネルギー周期 T_m−1,0 を与えるのを既定の
解釈とします(developer.md §88.1 D7)。ピーク周期 T_p しか分からないときは、単峰の
スペクトルで T_m−1,0 ≈ T_p/1.1 が目安です(EurOtop 2018[^eurotop])。

| パラメータ | 既定 | 意味 |
|---|---|---|
| `f_wavefield` | 1 | 0 で書いたまま一時無効化 |
| `wf_ntheta` | 40 | 方向ビン数(8 の倍数、8〜360)。ビン幅 360°/N_θ(既定 9°)。軸と対角の向きがビンの中心に乗る |
| `wf_mode` | 2 | 1: 非定常(物理時間で毎ステップ進める)/ 2: 準定常(`dt_wave` ごとに定常解を求める) |
| `dt_wave` | 3600 s | 準定常の更新間隔(時間刻み `dt` の整数倍に丸める) |
| `wf_itmax` | 4 max(nx, ny) | 準定常の反復の上限 |
| `wf_tol` | 1e-4 | 準定常の収束判定: 1 回の反復での波高の変化の最大 / 沖の波高(不規則波は H_rms で比べる) |
| `f_wf_init` | 1 | 1: 開始時に準定常解を求める / 0: 静穏(波なし)から始める |
| `wf_bc_side(1:4)` | 0, 0, 0, 0 | 辺 W・E・N・S の型。0 吸収 / 1 入射 / 2 側方 Neumann。**入射の辺が 1 つ以上必要** |
| `wf_wavetype` | 1 | 1: 不規則波(波高は H_m0、砕波は確率モデル)/ 2: 規則波(波高 H、H ≤ γh の飽和砕波。検定用) |
| `wf_hm0`・`wf_trep`・`wf_dir` | — | 沖の波(固定値。`wf_val` を使わないときは必須)。`wf_trep` は代表周期(不規則波は T_m−1,0 の解釈) |
| `wf_spread` | 20°(規則波 0°) | 方向分散 σθ(0 = 単一方向、上限 48.8° = 半平面で一様) |
| `wf_val(1:5, k)` | — | 沖の波の時系列: 時刻 (min)・波高 (m)・周期 (s)・方向 (deg)・方向分散 (deg)。行の間は線形補間(方向は短い向きの差で補間)。方向分散を省略した行は既定 |
| `wf_clock` | 0 | 時系列の時計 0: 水理時間 / 1: 地形時間(MORFAC 倍。[土砂・地形変化](geomorph.md)) |
| `wf_break` | 1 | 砕波 1: Baldock ら(1998)/ 2: Janssen & Battjes(2007)(不規則波のみ) |
| `wf_gamma` | 0.78 | 砕波指標 γ |
| `wf_alpha` | 1.0 | 砕波の散逸係数 α(不規則波) |
| `wf_gammax` | 0.6 | 水深による上限 H_rms ≤ γmax h(不規則波) |
| `wf_fw` | 0 | 底面摩擦係数 f_w(0 = 摩擦なし) |
| `wf_hmin` | 0.1 m | 波浪セルの最小水深 |
| `f_wf_outdiag` | 0 | 1: 底面軌道流速 Wu・砕波散逸 Wb も分布出力(`wf_flow` ≥ 1 なら外力 Wfx・Wfy、Stokes 輸送 Wsx・Wsy、ローラー Wr も) |
| `wf_flow` | 0 | 流れへの作用。0: なし / 1: 波の外力だけ / 2: 外力 + GLM の Stokes 輸送 + 波・流れの底面摩擦(推奨)。[流れへの作用](#流れへの作用wf_flow段-w2) |
| `f_wf_roller` | 1 | 1: ローラーのエネルギー平衡を解く(`wf_flow` ≥ 1) |
| `wf_beta` | 0.1 | ローラーの散逸係数 β |
| `wf_tramp` | 100 s | 外力の立ち上げ時間(時間軸の起点から 0 → 1 倍へ線形)。0 で立ち上げなし |
| `f_wf_current` | 0 | 1: 流れの波への作用(ドップラー効果・流れによる屈折と輸送・阻止)。[流れによる波の変化](#流れによる波の変化f_wf_current段-w3) |

採用した既定値は画面に `(default)` を付けて表示します。

## とりあえず動かしてみる(最小入力)

必要なのは**入射の辺**と**沖の波**(`wf_hm0`・`wf_trep`・`wf_dir`)だけです。

1. **沖は「解く海」にします。** 海底地形を z に与え、初期水位で水を張ります
   (`f_htype = 2` など。[初期条件](initial.md))。**海域マスクの海セル(sw)の帯は波が
   通りません**(潮位を与える境界のセルで、浅水流でも計算しないセルです。[潮位・海面](tide.md))。
   入射の辺に接するセルが開始時に 1 つも波浪セルでなければ、警告を表示します。
2. **沖の辺を入射(1)にします。** 直線的な海岸なら、海岸に交わる左右の辺を
   **側方 Neumann(2)**にします。Neumann は「境界の外にも同じ海が岸沿いに続く」という
   扱いで、左右の辺の近くに偽の陰ができません。吸収(0)にすると、外から斜めに
   入るはずの波がなくなり、辺の近くに陰ができます(閉じた湾の奥の辺など、外に海が
   ない辺に使います)。陸側の辺は何でも構いません。
3. **方向ビン数・砕波の係数は既定のまま**で始め、結果(Wh・Wa)を見てから必要なら
   変えます。

**使い方の型**

| 型 | 構成 | 見るもの |
|---|---|---|
| 海浜の波高分布・砕波帯の位置 | `wf_mode = 2`(準定常。既定)、沖の波は固定値 | Wh(波高)・Wb(砕波散逸。`f_wf_outdiag = 1`) |
| 防波堤・島の背後の陰 | 同上。方向分散は既定 20° | Wh・Wa(平均波向) |
| 波候の時間変化(地形変化と組む準備) | `wf_val` の時系列、`dt_wave` で更新間隔、`wf_clock = 1` で地形時間 | `wavefield.csv`(更新ごとの台帳) |
| 波の前線の到達(津波・洪水と同時に進める) | `wf_mode = 1`(非定常)、`f_wf_init = 0` | Wh の時間変化 |
| 波によるセットアップ・沿岸流 | `wf_flow = 2`、海岸に交わる左右の辺を波・流れとも側方 Neumann(`wf_bc_side` = 2、`f_bc_*` = 3) | E(水位)・u・v(流速)・Wfx・Wfy(外力) |
| 河口・潮流・離岸流の上の波(遡上の阻止・急峻化) | `f_wf_current = 1`(波と流れの双方向なら `wf_flow = 2` も) | Wh・Wa、台帳の blocked |
| 沿岸漂砂・浜の侵食と回復(地形の変化) | `wf_flow = 2` と fn_geomorph の掃流砂・浮遊砂に `f_wfsed = 1` | Z(地盤高)・Qby・Qsy(沿岸漂砂。`f_wf_outdiag = 1`) |

## 計算のしくみ

### 基礎式

方向ビン m(中心の向き θ_m)ごとのエネルギー密度 E_m [J/m²/rad] について

```math
\frac{\partial E_m}{\partial t} + \nabla\cdot\left(c_g\,\hat{\mathbf e}_m E_m\right)
+ \frac{\partial (c_\theta E_m)}{\partial \theta}
= -\left(D_w + D_f\right)\frac{E_m}{E},
\qquad E = \sum_m E_m\,\Delta\theta
```

を解きます。作用量の保存(Bretherton & Garrett 1968[^bg68])を SWAN[^swan] の形から
周波数 1 個に縮約したもので、流れがない段 W1 では周波数が一定なので作用量と
エネルギーの保存は同じです。群速度 $`c_g`$ と屈折の速さ $`c_\theta`$ は線形理論の
分散関係から求めます。

```math
\sigma^2 = g\,k\tanh(kh),\qquad
c_g = \frac{\sigma}{2k}\left(1 + \frac{2kh}{\sinh 2kh}\right),\qquad
c_\theta = \frac{\sigma}{\sinh 2kh}\left(\sin\theta\,\frac{\partial h}{\partial x}
- \cos\theta\,\frac{\partial h}{\partial y}\right)
```

(σ = 2π/T、x は東・y は北。$`c_\theta`$ は SnapWave と同じく |c_θ| ≤ σ/4 に制限)。
右辺の散逸 $`D_w`$(砕波)・$`D_f`$(底面摩擦)は、全エネルギーに対する散逸を
各ビンへ E_m/E に比例して配分します(XBeach と同じ)。

波高は不規則波で H_rms = (8E/ρg)^{1/2}、出力は有義波高 H_m0 = √2 H_rms(Rayleigh 分布)、
規則波で H = (8E/ρg)^{1/2} です(ρ = 1025 kg/m³)。平均波向は
atan2(Σ E_m sin θ_m, Σ E_m cos θ_m) です。

### 沖の波と方向ビン

入射の辺の外にある沖の波のエネルギーは、不規則波で E_0 = ρgH_m0²/16、規則波で
ρgH²/8 です。方向の分布は cos^s(θ − θ_0)(|θ − θ_0| < 90°)で、指数 s は方向分散 σθ
から Kuik ら(1988)[^kuik88] の定義 σθ² = 2(1 − m_1)で逆算し、ビンで離散的に正規化
します(Σ D Δθ = 1。SWAN と同じ分布形)。σθ = 0 は θ_0 を挟む 2 ビンへ線形に配分します。
ビン数 N_θ は 8 の倍数に限り、x・y の軸と対角の向きが必ずビンの中心に乗ります。

### 空間の輸送(2 リンク分解の風上法)

ENC の 8 近傍格子で、ビン m の伝播速度 $`c_g\hat{\mathbf e}_m`$ を、その向きを挟む
**2 本の格子方向(軸と対角)へ非負に分解**し、それぞれのリンクで風上(送り手の
セルの値)へ運びます。格子で正規化した p_x = c_g cos θ/Δx、p_y = c_g sin θ/Δy に
ついて |p_x| ≥ |p_y| なら軸 x へ率 |p_x| − |p_y|、対角へ率 |p_y| です(逆も同様)。
傾斜流向の D∞(Tarboton 1997[^tarboton97])と同じ発想を波のエネルギーに使う、
本プロジェクト独自の離散化です。

- **格子方向(軸・対角)の伝播では横断の数値拡散がありません。** 軸や対角に揃った
  波の陰は厳密に鋭く出ます(test/wfshadow の aligned)。
- その間の向きでは横断の数値拡散があり、最大 0.096 c_g Δx(格子方向の間の中央付近)です
  (ENC の通過幅による 1 次風上は軸方向で 0.293 c_g Δx)。**陰の縁はこの数値拡散で
  ぼけます。** これは実際の回折(陰に回り込む波)とは別物で、位相平均のこのモデルは
  回折を扱いません。
- 輸送は保存的で、エネルギーは負になりません。
- **対角リンクの両脇の 2 セルがともに非波浪セル(陸など)なら、その対角は閉じます。**
  角だけで接する 1 セル厚の斜めの堤を、波はすり抜けません(水の ENC とは意図的に
  違う規則。test/wfshadow の菱形の囲い)。

### 方向空間の屈折

セルごとに θ 方向の移流 ∂(c_θ E_m)/∂θ を、1 次風上の陰解法(周期境界の三重対角)で
解き、van Leer の制限関数[^vanleer74]による 2 次の補正を前の値から足します
(遅延補正。準定常の収束時は制限つき 2 次の流束の釣り合いを満たします)。
1 次風上だけでは方向空間の数値拡散で屈折が遅れ、中心差分は単一方向の入射で
負のエネルギーを生むため採りません(developer.md §88)。

屈折の誤差はビン幅に比例して小さくなります。勾配 1/80 の平行等深線の海浜に 30° で
入る波では、水深 1 m までの平均波向の Snell の法則からのずれは N_θ = 40 で 1.5°、
N_θ = 80 で 0.6°、波高のずれは 0.5%・0.3% でした(test/wfshoal の refr)。

### 砕波・底面摩擦・上限

**不規則波**の砕波は、Baldock ら(1998)[^baldock98](既定)

```math
D_w = \frac{\alpha}{4}\,\rho g f\,Q_b\left(H_b^2 + H_{rms}^2\right),\qquad
Q_b = \exp\!\left[-\left(\frac{H_b}{H_{rms}}\right)^2\right]
```

または Janssen & Battjes(2007)[^jb07]

```math
D_w = \frac{3\sqrt\pi}{16}\,\alpha\rho g f\,\frac{H_{rms}^3}{h}\,Q_b,\qquad
Q_b = 1 + \frac{4}{3\sqrt\pi}\left(R^3 + \frac{3}{2}R\right)e^{-R^2} - \mathrm{erf}(R),\quad R = \frac{H_b}{H_{rms}}
```

で、どちらも砕波波高 H_b = (0.88/k) tanh(γkh/0.88)(Battjes & Janssen 1978 の
Miche 型)、f = 1/T です(XBeach 定常モードと同じ形)。加えて XBeach・SnapWave と同じく、
水深による上限 H_rms ≤ γmax h をかけます(超えた分は台帳の「上限」に数えます)。

**規則波**(`wf_wavetype = 2`)は H ≤ γh の飽和(飽和砕波)だけで、確率的な砕波は
入りません。理論解と比べる検定用です。

**底面摩擦**は D_f = c ρ f_w u_orb³、u_orb = πH_rms/(T sinh kh)(規則波は H)で、
c = 0.28(不規則波)・0.21(規則波)です(Guza & Thornton 1985[^gt85] の速度の 3 次
モーメントの係数。XBeach の定式)。既定は f_w = 0(摩擦なし。XBeach 定常モードの既定)です。

散逸はセル内で半陰的に解きます(前の値で D/E を評価し、陰的な減衰として掛ける)。

### 境界と波浪セル

外縁の各辺は次のいずれかです。

| 型 | 格子の外の仮想の送り手が持つ値 | 使いどころ |
|---|---|---|
| 1 入射 | 沖の波のビン別エネルギー | 沖の辺 |
| 2 側方 Neumann | 境界の内側のセルの値 | 海岸に交わる左右の辺(外にも同じ海が続く) |
| 0 吸収 | 0 | 外に海がない辺・陸側の辺 |

各リンクの送り手は 1 つなので、角で二重に注入しません。角(x・y とも格子の外)の
仮想の送り手は 入射 > 側方 Neumann > 吸収 の優先で辺の型を決めます(入射の辺の角の
外は沖の波の領域とみなし、直線海岸で岸沿いに一様な解を崩しません)。
外へ出ていく波は自由に出ます(反射しません)。

**波浪セル**は、領域内(x > 0)で、海域マスクの海セル(sw)でも吸収セルでもなく、
水深が `wf_hmin` を超えるセルです。陸・乾燥セル・海セル・吸収セルへ向かう波は
吸収されます(反射なし。台帳の「吸収」)。この版では、**家屋の空隙率 gv < 1 のセル**と
**サブグリッド河道の幅・断面形のセル**も吸収セルとして扱い、その数を開始時に表示します。

### 準定常と非定常

1 回の更新は、空間の流入出(前の値から新しい値を作る陽的な更新)と、セル内の屈折と
源項(陰的)の組です。この 1 つの核を 2 つの使い方で回します。

- **準定常(`wf_mode = 2`。既定)**: `dt_wave` ごとに、セルごとの擬似時間刻み
  Δτ = 1/(最大流出率)で反復して定常解に収束させます(前回の解から始める)。
  定常解は Δτ に依りません。地形変化の計算のように、波の伝播時間より長い時間で
  条件が変わる用途向けです。
- **非定常(`wf_mode = 1`)**: 物理時間の dt で毎ステップ進めます(流出率 × dt > 1 なら
  サブステップ)。波の前線は群速度で進みます(test/wfshoal の unst)。十分な時間の後は
  準定常と同じ定常解に達します。

どちらもセルの更新順に依らない形なので、MPI の分割数・スレッド数によらず結果は
ビット単位で一致します。

## 流れへの作用(wf_flow。段 W2)

`wf_flow` を 1 か 2 にすると、波浪場が浅水流に作用し、**波によるセットアップ
(汀線付近の平均水位の上昇)・沖のセットダウン・沿岸流**が生じます。既定の 0 では
段 W1 と同じく流れに作用しません(`fn_wavefield` を書いても浅水流の結果は同じ)。

```
&list_wavefield
  ...
  wf_flow = 2              ! 0 作用なし(既定)/ 1 外力 / 2 外力 + GLM + 波・流れの摩擦
/
&list_bound_edge
  f_bc_n = 3               ! 海岸に交わる左右の辺は側方 Neumann(沿岸流が通り抜ける)
  f_bc_s = 3
/
```

**どれを使うか。** 沿岸流・離岸流・河口の流れとの相互作用を見るなら **2** を
使ってください。2 は、波が運ぶ質量(Stokes 輸送)とその戻り流れ(底層の離岸方向の
流れ)、波の軌道流速で強まる底面摩擦を含みます。1 は放射応力の勾配だけを外力として
加える簡略形(セットアップの古典理論と同じ扱い)で、摩擦は流れの流速だけで決まります。
1 では静止に近い流れの摩擦が弱く、始動時の振動が長く残ります(下の「始動」)。

### 外力(放射応力の勾配)

方向ビンのエネルギーから放射応力(Longuet-Higgins & Stewart 1964[^lhs64])を

```math
S_{xx} = n\sum_m E_m\cos^2\theta_m\,\Delta\theta + \left(n - \tfrac12\right)E + E_r\cos^2\bar\theta,\qquad
S_{xy} = n\sum_m E_m\cos\theta_m\sin\theta_m\,\Delta\theta + E_r\cos\bar\theta\sin\bar\theta
```

(S_yy も同様。n = c_g/c、θ̄ は平均波向)で求め、波の外力
$`F_i = -\partial S_{ij}/\partial x_j`$ をセル中心で差分(両隣が波浪セルなら中央差分)
します。直角に入る波では、砕波帯より沖で平均水位が下がり(set-down)、砕波帯で
上がります(set-up。Longuet-Higgins & Stewart 1962[^lhs64]、Bowen ら 1968[^bowen68])。
斜めに入る波では、砕波で S_xy が減る分が沿岸方向の外力になり、沿岸流を駆動します。

浅水流の各辺には、両セルの外力の平均を辺の向きへ射影して $`F_k/(\rho h)`$ を
加速度として足します(h は両セルの平均水深)。

### ローラー

砕けた波のエネルギーは、いったん波頭の表面の渦(ローラー)に移ってから散逸します。
ローラーのエネルギー E_r(J/m²)は波の平均波向・位相速度 c で運ばれ、

```math
\frac{\partial E_r}{\partial t} + \nabla\cdot\left(c\,\hat{\mathbf e}_{\bar\theta}E_r\right) = D_b - D_r,\qquad
D_r = \frac{2\beta g E_r}{c}
```

を解きます(Svendsen 1984[^svendsen84]、Reniers & Battjes 1997[^rb97]。D_b は砕波の散逸と
上限で除いた分)。ローラーの放射応力 E_r cos²θ̄ 等は Nairn ら(1990)[^nairn90] の近似で、
XBeach と同じ形です。ローラーは砕波の運動量をいったん蓄えて岸側で放すので、
**外力・セットアップ・沿岸流の最大が岸側へずれます**(砕波点の直後で流れが立ち上がる
遅れ)。空間の輸送は波と同じ 2 リンク分解の風上法で、準定常では定常解、非定常では
同じ時間刻みで進めます。

### GLM と波・流れの底面摩擦(wf_flow = 2)

浅水流の流速を **Lagrangian 平均流速 u^L**(水の粒子が 1 周期に進む距離の平均。
質量の輸送を表す)と読み、底面摩擦は**オイラー流速** u^E = u^L − u^S に作用させます
(深さ平均の GLM。Andrews & McIntyre 1978[^am78]、Walstra ら 2000[^walstra00]。XBeach と
同じ)。Stokes 輸送の速さは

```math
\mathbf u^S = \frac{\sum_m E_m\hat{\mathbf e}_m\,\Delta\theta + 2E_r\,\hat{\mathbf e}_{\bar\theta}}{\rho h c}
```

(右辺第 2 項はローラーの質量輸送 2E_r/c。Svendsen 1984)です。閉じた海浜では正味の
岸沖の流量が 0(u^L ≈ 0)になり、オイラー流速 u^E = −u^S が**戻り流れ**(底層の
離岸方向の流れ)を表します。摩擦の速さは波の軌道流速を含め

```math
\tau_b = \rho\,\frac{g n_m^2}{h^{1/3}}\,\sqrt{|\mathbf u^E|^2 + (1.16\,u_{rms})^2}\;\mathbf u^E
```

(Ruessink ら 2001[^ruessink01]。n_m はマニングの粗度)で、砕波帯では軌道流速が摩擦を
大きく強めます。

### 始動(外力の立ち上げ)

準定常の波浪場は開始時に全域で満値になるので、急に加わる外力が汀線付近の振動
(副振動)を起こします。`wf_tramp`(既定 100 s。XBeach の taper の既定)の間、外力と
Stokes 輸送を 0 から線形に増やします。立ち上げは時間軸の起点 t0 から数えるので、
再開(`f_state_restore = 1`)では続きの値になります。保存した状態を初期条件として
使う(`f_state_restore = 2`)ときは新しい時間軸で立ち上げ直すので、すでに釣り合った
状態から続けるなら `wf_tramp = 0` にしてください。

### 側方の境界(f_bc = 3)

海岸に交わる左右の辺は、**波を側方 Neumann(`wf_bc_side` = 2)、流れを側方 Neumann
(`f_bc_*` = 3。[境界条件](boundary.md))**にします。流れの側方 Neumann は「境界の外にも
同じ海岸が続く」扱いで、沿岸流が辺を通り抜けます(壁にすると沿岸流がせき止められて
辺に偽の循環ができます)。岸沿いに一様な海岸では、境界の行も内部の行と同じ解になります
(test/wfcurrent で全行の差が流速の最大の約 0.03%)。地形が辺の近くで岸沿いに変わる
場合は、辺の外もその地形が続く扱いになるので、見たい区域を辺から離してください。
土砂も同じ扱いで、浮遊砂(と水質・塩水などのスカラー)は鏡像セルの濃度で流入し、
掃流砂は辺の法線方向に一つ内側の面の流束を写します(どれも勾配 0。地形が変わっても
岸沿いに一様な海岸は一様のまま。test/wfsed)。

## 流れによる波の変化(f_wf_current。段 W3)

`f_wf_current = 1` にすると、浅水流の流れ(河川流・潮流・離岸流・沿岸流・津波の流れ)が
波を変えます。逆流(波と向き合う流れ)では波長が縮んで波高が増し、強い逆流では波が流れを
遡れなくなります(**阻止**)。順流では波長が伸びて波高が下がります。流れの速さが場所で
変わると波の向きも曲がります(流れによる屈折)。河口の噴流が沖からの波の遡上を止める
現象や、離岸流・潮流の上での波の急峻化を表します。

```
&list_wavefield
  ...
  f_wf_current = 1         ! 0 なし(既定)/ 1 流れの波への作用
/
```

波による流れ(`wf_flow`)と組むと、波と流れの双方向の連成になります(沿岸流が波を変え、
その波が沿岸流を起こす)。

### ドップラー効果と阻止

流れ $`\mathbf U`$ の上の波の分散関係は、方向ビン m の向き $`\hat{\mathbf e}_m`$ の流速成分
$`U_m = \mathbf U\cdot\hat{\mathbf e}_m`$ を使って

```math
(\omega - k U_m)^2 = g k \tanh kh
```

です(Bretherton & Garrett 1968[^bg68])。ω は沖の波の角周波数で、流れが定常なら波の山の数の
保存により変わりません。セルとビンごとにこの式を U_m → 0 で連続な枝で解き(Newton 法)、
固有角周波数 $`\sigma_m = \omega - k_m U_m`$ と固有の群速度 c_g,m を求めます。逆流
(U_m < 0)では k_m が大きく σ_m > ω、順流では逆です。逆流が強く、群速度と流れが打ち消し
合う(c_g,m + U_m ≤ 0)か根がなくなると、そのビンの波は**阻止**され、届いた作用量は
台帳の blocked に記録して除きます。

### 作用量の平衡

流れがあると波のエネルギーは保存しませんが、**波の作用量 N = E/σ** は保存します
(Bretherton & Garrett 1968)。

```math
\frac{\partial N_m}{\partial t} + \nabla\cdot\left[(c_{g,m}\hat{\mathbf e}_m + \mathbf U)N_m\right]
+ \frac{\partial (c_\theta N_m)}{\partial\theta} = -\frac{D_m}{\sigma_m}
```

空間の輸送は、速さ $`c_{g,m}\hat{\mathbf e}_m + \mathbf U`$ をセルとビンごとに W1 と同じ
2 リンク分解の風上法で運びます。方向空間の屈折の速さには、流れの速さの勾配による項を足します
(x 東・y 北。SWAN[^swan]・XBeach[^xbeach] と同じ形)。

```math
c_\theta = \frac{\sigma}{\sinh 2kh}\left(\frac{\partial h}{\partial x}\sin\theta - \frac{\partial h}{\partial y}\cos\theta\right)
+ \cos\theta\left(\sin\theta\frac{\partial u}{\partial x} - \cos\theta\frac{\partial u}{\partial y}\right)
+ \sin\theta\left(\sin\theta\frac{\partial v}{\partial x} - \cos\theta\frac{\partial v}{\partial y}\right)
```

砕波・底面摩擦・上限は、エネルギー $`E_m = \sigma_m N_m`$ とエネルギー重みの平均の波数・
固有角周波数で、W1 と同じ式で評価します。作用量は時間変化する流れの中でも保存する量
(断熱不変量)なので、計算の状態は作用量で持ち、流れが変わってもそのまま引き継ぎます
(非定常の台帳も流れの時間変化の間に閉じます)。

使う流速は浅水流の流速そのものです(`wf_flow = 2` では Lagrangian 平均流速 u^L。XBeach の
wci と同じ[^xbeach])。ローラー(`wf_flow` ≥ 1)も流れで運ばれます(速さ c ê + U、
c = σ̄/k̄)。

### 計算量と収束

流れがあると、更新ごとにセルとビンごとの分散関係と輸送の分解を求め直し、ビンごとの量
(波数・固有角周波数・流出率・屈折の速さ)を持ちます。メモリは波浪場の分で約 3 倍
(N_θ = 40 で 1 セルあたり約 2.4 kB)です。非定常(`wf_mode = 1`)では毎ステップ求め直す
ので重くなります。阻止の近くでは群速度と流れが打ち消し合うビンの作用量の移動が遅く、
準定常の反復の収束が遅くなります(test/wfdoppler の河口の噴流で約 2000 回、阻止される
水路で約 7000 回)。収束しない旨の表示が出たら `wf_itmax` を上げてください。

## 土砂への作用(f_wfsed。段 W4・W5)

[土砂・地形変化](geomorph.md)の掃流砂(`f_fluvial`)・浮遊砂(`f_suspend`)に、`&list_geomorph`
の `f_wfsed = 1` を加えると、波浪場が土砂を動かします。波の軌道運動が海底の砂を攪拌して
(巻き上げと掃流の量を増やし)、波による流れ(沿岸流・戻り流れ)と波の歪度・非対称による
岸向きの速度が砂を運びます。沿岸漂砂(汀線に沿う砂の移動)と、浜の侵食(高波浪の戻り流れで
砂が沖へ)・回復(低波浪の非対称で砂が岸へ)を、地形変化と同じ時間発展で求めます。

```
&list_geomorph
  f_fluvial = 1             ! 掃流砂(攪拌の粒径は fluv_d50)
  f_suspend = 1             ! 浮遊砂(攪拌の粒径は susp_d50)
  f_wfsed = 1               ! 波浪場による攪拌と輸送
  !wfsed_facsk = 0.1        ! 歪度の係数 f_Sk(既定 0.1。0 で岸向きの速度の歪度の項なし)
  !wfsed_facas = 0.1        ! 非対称の係数 f_As(既定 0.1)
/
```

`fn_wavefield` が必要です。波による流れ(`wf_flow = 2`)と組むのが基本の使い方です(沿岸流と
戻り流れが砂を運ぶ。`wf_flow = 0` では流れが波で起きないので、攪拌と岸向きの速度だけが
効きます)。[fn_wave の沿岸漂砂](geomorph.md)(CERC 型)とは同時に使えません(同じ輸送を
二重に数えないため、開始時に停止します)。土石流(`f_debris`)とも併用できません。

### 攪拌(波・流れの底面せん断)

波の底面の軌道流速の振幅 u_w = √2 u_rms(u_rms は出力 Wu)と軌道の振幅 A = u_w/σ̄
(σ̄ は固有角周波数)から、波の底面せん断と、流れのせん断との合成を Soulsby(1997)[^soulsby97]
の式で求めます。

```math
\tau_w = \tfrac12 \rho f_w u_w^2,\quad f_w = \min\left(1.39\,(A/z_0)^{-0.52},\ 0.3\right),\quad z_0 = d_{50}/12
```

```math
\tau_m = \tau_c\left[1 + 1.2\left(\frac{\tau_w}{\tau_c + \tau_w}\right)^{3.2}\right],\quad
\tau_{max} = \sqrt{(\tau_m + \tau_w|\cos\varphi|)^2 + (\tau_w\sin\varphi)^2}
```

τ_c は流れだけのせん断(既存の Manning の閉じ τ* = n² V²/(s d h^{1/3}) で、V は下の Euler 平均
流速 u^E の速さ)、φ は流れと平均波向のなす角、τ_max は波の周期の中の最大のせん断です。
掃流砂の流砂量式(`f_qbform`)と浮遊砂の平衡濃度式(`f_esform`)の無次元掃流力に τ*_max を
使います(閾値の判定も)。z0 は粒子の粗さ(k_s = 2.5 d50 の z0 = k_s/30)、上限 0.3 は小さな A
での Swart(1974)の値です。波がなければ τ*_max = τ*_c で、`f_wfsed = 0` と同じ式です。

### 輸送(Euler 平均流速と岸向きの速度)

砂を運ぶ速度は u_s = u^E + u_a ê_θ です(ê_θ は平均波向の単位ベクトル)。

- **Euler 平均流速 u^E = u^L − u^S**: `wf_flow = 2` の浅水流の流速は Lagrangian 平均 u^L(水の
  質量輸送)で、Stokes 輸送 u^S は波の谷より上に集中します。浮遊砂は底近くに多いので、
  砂は Stokes 輸送を除いた Euler 平均流速で動きます(Reniers ら 2004[^reniers04]、XBeach と
  同じ[^xbeach])。砕波帯では u^E が沖向きの戻り流れになり、砂を沖へ運びます。
- **岸向きの速度 u_a**: 浅い所の波は山が尖り(歪度 S_k)前傾する(非対称 A_s)ので、岸向きの
  軌道流速が強く、砂は正味で岸へ運ばれます。XBeach と同じく van Thiel de Vries(2009)[^vtdv09]の
  u_a = (f_Sk S_k − f_As A_s) u_rms を使い、S_k・A_s は Ruessink ら(2012)[^ruessink12]の
  Ursell 数 Ur = (3/8)√2 H_rms k/(kh)³ によるパラメータ化で求めます
  (S_k = B cos ψ、A_s = B sin ψ、B = p₂/(1 + exp((p₃ − log₁₀ Ur)/p₄))、ψ = −90° + 90° tanh(p₅/Ur^{p₆})。
  係数 p₂〜p₆ は XBeach の公開ソースの値)。f_Sk・f_As(`wfsed_facsk`・`wfsed_facas`)は校正の
  係数で、既定 0.1 は XBeach の既定(facua)です。

浮遊砂は浅水流の面流束から h(u^S − u_a ê_θ) を引いた流束で運び(水と違う速度で動く)、
掃流砂は

```math
q_b = q^*(\tau^*_{max})\sqrt{\tau^*_s/\tau^*_{max}}\,\sqrt{s g d^3}
```

を u_s の向きに運びます(τ*_s は u_s の速さの Manning のせん断)。τ*_max の流れが運ぶ掃流の量を
u_s の速さで運ぶ形で、波がなければ既存の式に一致し、流れがなく波だけなら u_a の向きに、
波が流れより強ければ流砂量は u_s の速さに比例します(XBeach の「平衡濃度 × 輸送速度」と
同じ考え方。この組み合わせは独自)。

**浜の侵食と回復**は、沖向きの戻り流れ u^E と岸向きの u_a の釣り合いで決まります。高波浪では
戻り流れが勝って砂が沖へ運ばれ(砂州ができる)、低波浪・長周期のうねりでは砕波帯より沖で u_a が
勝って砂が岸へ戻ります(test/wfsed の storm・calm)。どちらが勝つかは f_Sk・f_As に敏感なので、
地形の変化を合わせたい場合はこの 2 つで校正します。

### 沿岸漂砂の出力と CERC との比較

`f_wf_outdiag = 1` で、掃流砂の推定 Qbx・Qby と浮遊砂の輸送量 Qsx・Qsy(固体体積の単位幅
輸送量 m²/s。向きは流速 u・v と同じ)、岸向きの速度 Wua(m/s)を出力します。海岸に沿う
成分を岸沖方向に積分すると沿岸漂砂量になります。test/wfsed の直線海岸(H_m0 = 1 m、
T = 8 s、20°)では CERC(Komar & Inman 1970[^ki70])の 1.6 倍程度で、桁が合います
(CERC の係数も過程の漂砂の係数も校正の量です)。

直線海岸の左右の辺を側方 Neumann(`f_bc_*` = 3)にすると、浮遊砂は鏡像セルの濃度で流入し
(勾配 0)、掃流砂は辺の法線方向に一つ内側の面の流束を写します(外に同じ海岸が続く扱い。
[側方の境界](#側方の境界f_bc--3))。

## 出力・確認

**分布**(出力時刻ごと。[入出力の形式](io.md))

| 記号 | 内容 | 単位 |
|---|---|---|
| Wh | 波高(不規則波は H_m0、規則波は H) | m |
| Wa | 平均波向(進む向き。x 軸から反時計回り。無波セルは −9999) | deg |
| Wu | 底面軌道流速 u_rms = H_rms σ/(2√2 sinh kh)(XBeach の定義)。`f_wf_outdiag = 1` | m/s |
| Wb | 砕波散逸 D_w(不規則波)。`f_wf_outdiag = 1` | W/m² |
| Wfx・Wfy | 波の外力 F = −∇·S(セル中心。ローラーを含む)。`wf_flow` ≥ 1 かつ `f_wf_outdiag = 1` | N/m² |
| Wsx・Wsy | Stokes 輸送の速さ u^S。`wf_flow = 2` かつ `f_wf_outdiag = 1` | m/s |
| Wr | ローラーのエネルギー E_r。`f_wf_roller = 1` かつ `f_wf_outdiag = 1` | J/m² |
| Qbx・Qby | 掃流砂の輸送量の推定(固体体積の単位幅。fn_geomorph の `f_wfsed = 1`・`f_fluvial = 1`)。`f_wf_outdiag = 1` | m²/s |
| Qsx・Qsy | 浮遊砂の輸送量 hs·u_s(同、`f_suspend = 1`)。`f_wf_outdiag = 1` | m²/s |
| Wua | 波の歪度・非対称による岸向きの輸送速度 u_a(平均波向の向きが正。`f_wfsed = 1`)。`f_wf_outdiag = 1` | m/s |

**y の成分(Wfy・Wsy・Qby・Qsy)は流速 v と同じ向き(行の増える向き = 南が正)です。** 波向の
規約(北が正)とは逆なので注意してください。`wf_flow = 2` の流速 u・v は Lagrangian
平均流速 u^L で、底面の流れ(オイラー流速)は u − Wsx、v − Wsy です。

**台帳** `result/wavefield.csv`。準定常は更新ごとに収束時の率(W)を、非定常は
計測間隔(`dt_recrd`)ごとに累積量(J)を書きます。

| 列 | 内容 |
|---|---|
| iter・residual(準定常)/ nsub(非定常) | 反復回数と最後の残差 / サブステップ数 |
| H_bc・T_bc・dir_bc | その時刻の沖の波 |
| in・out | 境界からの流入・境界への流出(側方 Neumann の辺の出入りを含む) |
| absorbed | 陸・乾燥・吸収セルへ向かって失われた分 |
| breaking・friction | 砕波・底面摩擦の散逸 |
| limit | 上限(不規則波の H_rms ≤ γmax h、規則波の飽和)で除いた分 |
| dry | 水深が `wf_hmin` 以下になったセルから除いた分(量 J) |
| trunc | 数値的な切り捨て(負値の 0 化で足した分。通常は 0 か丸め誤差の規模) |
| imbalance・storage | 収支の残差・波浪場の貯留(Σ E A) |
| blocked(`f_wf_current = 1`) | 阻止で除いた分 |

`f_wf_current = 1` では台帳の量は作用量 × ω(流れがなければエネルギーと同じ)です。
準定常の imbalance は最後の反復での貯留の変化率で、`wf_tol` を小さくすると 0 に
近づきます。非定常の imbalance は(貯留の変化)−(正味の入力)で、丸め誤差の規模です。
大きな値が出たら不具合なので報告してください。

## 適用範囲と併用の制限

- **位相平均・代表周期 1 個**です。回折・反射・周波数の広がり・風による発達・非線形の
  波の相互作用は扱いません。陰の縁のぼけは数値拡散で、回折ではありません。
- **土砂への作用(`f_wfsed`)**: 攪拌は底面の軌道流速だけで、砕波の乱れによる巻き上げは
  入りません。浮遊砂の水平拡散はありません。遡上域(swash)の輸送は表しません(位相平均の
  波は汀線の手前で止まります。砂丘の崩れは安息角崩落 `f_repose`)。代表粒径は掃流砂・
  浮遊砂それぞれ 1 つです。浜の侵食と回復を分ける戻り流れと岸向きの速度の釣り合いは
  係数 f_Sk・f_As に敏感です(校正の量)。
- **阻止された波は作用量を除くだけ**で、阻止の点での反射(短い波への変換)は表しません。
  代表周期 1 個なので、阻止はすべてのエネルギーに同時に起こります(実際の波はスペクトルの
  短い成分から阻止されます)。阻止の手前の急峻化による砕波は表します。
- 流れが時間変化しても、沖の波の角周波数 ω は一定とします(流れの時間変化による ω の変化は
  入れません)。
- **流れの急な変化**(湧き出しの近く・噴流の縁)では、単一方向の波が流れによる屈折で隣の
  ビンへ数 % 広がります(方向空間の 1 次風上の数値拡散。ビン幅の 2 乗で小さくなります)。
- **砕波による横方向の混合(渦粘性)は入りません。** 沿岸流の分布は、ENC の斜めの面の
  移流による数値的な横混合でならされます(砕波の始まりの外縁に最大の数 % の流れが出ます)。
  浅水流の水平拡散([拡散項](diffusion.md) の `f_diffusion_term`)を併用することは
  できますが、波による混合の定式(Battjes 1975 型)ではありません。
- **方向分散 0 の単一方向の波(規則波を含む)は、屈折が Snell の法則より遅れます**
  (N_θ = 40、入射 20° で砕波点の向きが約 1.5° 大きい)。沿岸方向の放射応力 S_xy は
  向きに敏感なので、砕波帯より沖に偽の沿岸方向の外力が出ます(砕波帯の外力の約 5%。
  方向分散 20° では約 1%)。沿岸流を見るときは方向分散を与えるか、ビン数を増やして
  ください。
- **側方 Neumann の辺**は「外にも同じ海岸が続く」扱いです。地形が辺の近くで岸沿いに
  変わる場合や、構造物が辺に接する場合は、見たい区域を辺から十分離してください。
- **海域マスクの海セル(sw)は波浪の計算域外**です。沖は海底地形を持つ通常のセルで表し、
  入射の境界は外縁の辺に置きます。
- **STG 格子・ネストとは併用できません**(開始時に停止します)。
- 家屋の空隙率 gv < 1 のセル、サブグリッド河道の幅・断面形のセルは波を吸収します。
- 計算量: 方向ビン数 N_θ 個の面を持ち、1 回の更新は N_θ 回のスカラー輸送とセルごとの
  三重対角です。準定常の 1 回の解は数百回の反復です(100 × 100 セル・40 ビンで
  367 回・約 2 秒、4 スレッド)。非定常で毎ステップ解くと浅水流本体より重くなることが
  あります。

## パラメータと既定値の根拠

| パラメータ | 既定 | 根拠 |
|---|---|---|
| `wf_gamma` | 0.78 | **文献値**: XBeach 定常モードの既定[^xbeach](孤立波の砕波限界に由来する慣用の値) |
| `wf_alpha` | 1.0 | **文献値**: XBeach 定常モードの既定[^xbeach] |
| `wf_gammax` | 0.6 | **文献値**: XBeach 定常モードの既定[^xbeach](H_rms の水深に対する上限)。SnapWave[^snapwave] も同じ形・同じ値の上限を持つ |
| `wf_fw` | 0 | **校正量**: 既定 0(摩擦なし)は XBeach の既定[^xbeach]。岩礁などでは流れの摩擦係数より 1 桁以上大きいことがある(XBeach マニュアル) |
| 摩擦の係数 c | 0.28・0.21 | **文献値**: Guza & Thornton(1985)[^gt85] の速度モーメント(XBeach の定式)。設定項目ではない |
| `wf_break` | 1 | **方式**: XBeach 定常モードの既定と同じ Baldock ら(1998)。急な海浜では Janssen & Battjes(2007)が散逸の過大を補正する |
| `wf_mode` | 2 | **方式**: 地形変化と組む用途(条件の変化が波の伝播時間より遅い)を既定にした |
| `wf_hmin` | 0.1 m | **数値設定**: SnapWave の既定[^snapwave] |
| `dt_wave` | 3600 s | **数値設定**: SnapWave の既定の更新間隔[^snapwave] |
| `wf_ntheta` | 40(9°) | **数値設定**: XBeach・SnapWave の既定 10° に近い 8 の倍数。屈折の誤差は上の実測(ビン幅に比例) |
| `wf_tol` | 1e-4 | **数値設定**: 独自(波高の相対変化。検定では 1e-6〜1e-8 で解の差を確かめた) |
| `wf_spread` | 20° | **経験値**: 本プロジェクトの目安(独自)。風波〜うねりの代表的な広がりの中間として置いた値で、地点の波浪観測があればその方向分散を与える |
| ρ | 1025 kg/m³ | **慣用値**: 海水の密度(XBeach の既定)。設定項目ではない |
| `wf_flow` | 0 | **方式**: 既定は流れに作用しない(段 W1 と同じ結果)。使うときは 2 を推奨(XBeach と同じ GLM と波・流れの摩擦) |
| `f_wf_roller` | 1 | **方式**: XBeach の既定[^xbeach](roller = 1)。外力の最大を岸側へずらす効果は観測と合う(Reniers & Battjes 1997[^rb97]) |
| `wf_beta` | 0.1 | **文献値**: XBeach の既定[^xbeach](範囲 0.05〜0.3)。Reniers & Battjes(1997)[^rb97] の 0.1 |
| `wf_tramp` | 100 s | **数値設定**: XBeach の taper の既定[^xbeach](定常の波浪場を全域で一度に与える同じ状況の始動) |
| `f_wf_current` | 0 | **方式**: 既定は流れの作用なし(段 W2 までと同じ結果)。式は Bretherton & Garrett(1968)[^bg68] の作用量の平衡で、流れによる屈折の式と使う流速(Lagrangian 平均)は XBeach の wci[^xbeach] と同じ。分散関係を方向ビンごとに直接解く点は独自(XBeach は Eikonal 式で波数を時間発展させる) |
| 摩擦の速さの係数 | 1.16 | **文献値**: Ruessink ら(2001)[^ruessink01] の波・流れの摩擦(XBeach の定式)。設定項目ではない |
| `f_wfsed`(&list_geomorph) | 0 | **方式**: 既定は土砂に作用しない。攪拌は Soulsby(1997)[^soulsby97] の波・流れのせん断の合成(f_w の上限 0.3 は Swart 1974[^swart74])、浮遊砂を Euler 平均流速で運ぶのは Reniers ら(2004)[^reniers04]・XBeach[^xbeach] と同じ。掃流砂の「τ*_max の量 × u_s の速さ」の組み合わせは独自(Soulsby 1997 の波・流れの掃流砂の式と同じ桁であることを test/wfsed の条件で確認) |
| `wfsed_facsk`・`wfsed_facas`(&list_geomorph) | 0.1 | **校正量**: 既定は XBeach の facua[^xbeach]。式は van Thiel de Vries(2009)[^vtdv09]、S_k・A_s は Ruessink ら(2012)[^ruessink12] のパラメータ化(係数 p₂〜p₆ は XBeach の公開ソースの値で、原論文の表とは照合していない) |

分散関係は Fenton & McKee(1990)[^fm90] の陽な近似を初期値に Newton 法 3 回で解きます。

## 検証・例題

- [test/wfshoal](../../test/wfshoal/README.md): 勾配 1/80 の海浜断面。規則波の浅水変形と
  飽和砕波(線形理論と一致)、屈折(Snell の法則と方向ビンの 1 次収束)、不規則波の砕波
  (Baldock・Janssen & Battjes。Python で独立に書いた散逸式による離散解と一致、細かい刻みの
  エネルギー式との差 1%)、非定常の前線の到達と定常解、台帳の閉合、再開の継続のバイト一致、
  波浪場の有無で流れが同じこと、沖の波の時系列の補間。
- [test/wfshadow](../../test/wfshadow/README.md): 防波堤と斜めの壁の囲い。独立に実装した
  掃引解との一致、斜めの壁の遮断、格子方向に揃った波の陰が厳密に鋭いこと。
- [test/wfcurrent](../../test/wfcurrent/README.md): 流れへの作用(段 W2)。セットアップの
  面ごとの離散の釣り合い・沖の set-down(Longuet-Higgins & Stewart)・砕波帯の勾配
  (Bowen ら)、一様水深の沿岸流と戻り流れの摩擦の閉じた形との一致、海浜の沿岸流の
  運動量の積分の釣り合い・ローラーの収支と岸側へのずれ、側方 Neumann の辺の岸沿いの
  一様性、90° 回した格子との一致、再開の継続のバイト一致。
  流れの波への作用(段 W3)を加えた双方向の連成の釣り合いと収支も確かめます。
- [test/wfdoppler](../../test/wfdoppler/README.md): 流れによる波の変化(段 W3)。逆流・順流の
  上の作用量の流束の保存(独立に解いた分散関係)、逆流による阻止の位置と台帳、流れの作用の
  有無、非定常(流れの立ち上がりの間も作用量の台帳が閉じる)、河口の噴流が波の遡上を止める
  こと、再開の継続のバイト一致。
- [test/wfsed](../../test/wfsed/README.md): 土砂への作用(段 W4・W5)。攪拌による浮遊砂の
  平衡濃度と掃流砂の流砂量(独立に組み立てた Soulsby 1997 の式と一致)、海浜の沿岸漂砂の向き・
  岸沖分布・岸沿いの一様性・CERC(Komar & Inman 1970)と同じ桁、岸向きの速度 u_a
  (Ruessink ら 2012 の式と一致)、高波浪の侵食と低波浪の回復の向き、閉じた海盆の土砂の保存、
  再開の継続のバイト一致。
- いずれも MPI の np = 1・2・4 で逐次とビット一致します。

## 参考文献

[^am78]: Andrews, D. G. & McIntyre, M. E. (1978) An exact theory of nonlinear waves on a Lagrangian-mean flow. J. Fluid Mech. 89, 609–646.
[^baldock98]: Baldock, T. E., Holmes, P., Bunker, S. & Van Weert, P. (1998) Cross-shore hydrodynamics within an unsaturated surf zone. Coastal Engineering 34, 173–196.
[^bg68]: Bretherton, F. P. & Garrett, C. J. R. (1968) Wavetrains in inhomogeneous moving media. Proc. R. Soc. Lond. A 302, 529–554.
[^bowen68]: Bowen, A. J., Inman, D. L. & Simmons, V. P. (1968) Wave 'set-down' and set-up. J. Geophys. Res. 73(8), 2569–2577.
[^eurotop]: EurOtop (2018) Manual on wave overtopping of sea defences and related structures, 2nd ed. Van der Meer, J. W., Allsop, N. W. H., Bruce, T., De Rouck, J., Kortenhaus, A., Pullen, T., Schüttrumpf, H., Troch, P. & Zanuttigh, B. www.overtopping-manual.com
[^fm90]: Fenton, J. D. & McKee, W. D. (1990) On calculating the lengths of water waves. Coastal Engineering 14, 499–513.
[^gt85]: Guza, R. T. & Thornton, E. B. (1985) Velocity moments in nearshore. J. Waterway, Port, Coastal, Ocean Eng. 111(2), 235–256.
[^hiswa]: Holthuijsen, L. H., Booij, N. & Herbers, T. H. C. (1989) A prediction model for stationary, short-crested waves in shallow water with ambient currents. Coastal Engineering 13, 23–54.
[^ki70]: Komar, P. D. & Inman, D. L. (1970) Longshore sand transport on beaches. J. Geophys. Res. 75(30), 5914–5927.
[^jb07]: Janssen, T. T. & Battjes, J. A. (2007) A note on wave energy dissipation over steep beaches. Coastal Engineering 54, 711–716. 砕波波高 H_b の形は Battjes, J. A. & Janssen, J. P. F. M. (1978) Energy loss and set-up due to breaking of random waves. Proc. 16th ICCE, 569–587 の Miche 型(XBeach の定式と同じ)。
[^kuik88]: Kuik, A. J., van Vledder, G. Ph. & Holthuijsen, L. H. (1988) A method for the routine analysis of pitch-and-roll buoy wave data. J. Phys. Oceanogr. 18, 1020–1034.
[^lhs64]: Longuet-Higgins, M. S. & Stewart, R. W. (1964) Radiation stresses in water waves; a physical discussion, with applications. Deep-Sea Research 11, 529–562. 沖の set-down は Longuet-Higgins, M. S. & Stewart, R. W. (1962) Radiation stress and mass transport in gravity waves, with application to 'surf beats'. J. Fluid Mech. 13, 481–504。
[^nairn90]: Nairn, R. B., Roelvink, J. A. & Southgate, H. N. (1990) Transition zone width and implications for modelling surfzone hydrodynamics. Proc. 22nd ICCE, 68–81.
[^rb97]: Reniers, A. J. H. M. & Battjes, J. A. (1997) A laboratory study of longshore currents over barred and non-barred beaches. Coastal Engineering 30, 1–22.
[^reniers04]: Reniers, A. J. H. M., Roelvink, J. A. & Thornton, E. B. (2004) Morphodynamic modeling of an embayed beach under wave group forcing. J. Geophys. Res. 109, C01030.
[^ruessink01]: Ruessink, B. G., Miles, J. R., Feddersen, F., Guza, R. T. & Elgar, S. (2001) Modeling the alongshore current on barred beaches. J. Geophys. Res. 106(C10), 22451–22463.
[^ruessink12]: Ruessink, B. G., Ramaekers, G. & van Rijn, L. C. (2012) On the parameterization of the free-stream non-linear wave orbital motion in nearshore morphodynamic models. Coastal Engineering 65, 56–63.
[^snapwave]: Roelvink, D., van Ormondt, M., Reyns, J. & van der Lugt, M. (2025) SnapWave: fast, implicit wave transformation from offshore to nearshore. Geosci. Model Dev. 18, 9469–9495. doi:10.5194/gmd-18-9469-2025(既定値は公開ソースによる)
[^soulsby97]: Soulsby, R. L. (1997) Dynamics of Marine Sands: A Manual for Practical Applications. Thomas Telford, London. 波の摩擦係数(式 62a)、波・流れのせん断の合成(式 69・70)。
[^svendsen84]: Svendsen, I. A. (1984) Wave heights and set-up in a surf zone. Coastal Engineering 8, 303–329.
[^swan]: Booij, N., Ris, R. C. & Holthuijsen, L. H. (1999) A third-generation wave model for coastal regions: 1. Model description and validation. J. Geophys. Res. 104(C4), 7649–7666.
[^swart74]: Swart, D. H. (1974) Offshore sediment transport and equilibrium beach profiles. Delft Hydraulics Laboratory, Publication No. 131.
[^tarboton97]: Tarboton, D. G. (1997) A new method for the determination of flow directions and upslope areas in grid digital elevation models. Water Resour. Res. 33(2), 309–319.
[^vanleer74]: van Leer, B. (1974) Towards the ultimate conservative difference scheme. II. Monotonicity and conservation combined in a second-order scheme. J. Comput. Phys. 14, 361–370.
[^vtdv09]: van Thiel de Vries, J. S. M. (2009) Dune erosion during storm surges. PhD thesis, Delft University of Technology.
[^walstra00]: Walstra, D. J. R., Roelvink, J. A. & Groeneweg, J. (2000) Calculation of wave-driven currents in a 3D mean flow model. Proc. 27th ICCE, 1050–1063.
[^xbeach]: Roelvink, D., Reniers, A., van Dongeren, A., van Thiel de Vries, J., McCall, R. & Lescinski, J. (2009) Modelling storm impacts on beaches, dunes and barrier islands. Coastal Engineering 56, 1133–1152. 定式と既定値は XBeach マニュアル(xbeach.readthedocs.io)と公開ソース(params.F90)による。
