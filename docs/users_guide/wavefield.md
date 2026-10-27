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

**段階的に実装中です。** 現在(段 W1)は**固定床・流れの影響なしの波浪場**で、
波高などを計算して出力するだけです。**流れと地形には作用しません**
(`fn_wavefield` を書いても書かなくても浅水流の結果は同じです)。波による沿岸流・
セットアップ(段 W2)、流れによる波の変化(段 W3)、沿岸漂砂・岸沖の侵食と堆積
(段 W4・W5)は以降の段で追加します(docs/wavefield_plan.md §9)。

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
| `f_wf_outdiag` | 0 | 1: 底面軌道流速 Wu・砕波散逸 Wb も分布出力 |

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

## 出力・確認

**分布**(出力時刻ごと。[入出力の形式](io.md))

| 記号 | 内容 | 単位 |
|---|---|---|
| Wh | 波高(不規則波は H_m0、規則波は H) | m |
| Wa | 平均波向(進む向き。x 軸から反時計回り。無波セルは −9999) | deg |
| Wu | 底面軌道流速 u_rms = H_rms σ/(2√2 sinh kh)(XBeach の定義)。`f_wf_outdiag = 1` | m/s |
| Wb | 砕波散逸 D_w(不規則波)。`f_wf_outdiag = 1` | W/m² |

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

準定常の imbalance は最後の反復での貯留の変化率で、`wf_tol` を小さくすると 0 に
近づきます。非定常の imbalance は(貯留の変化)−(正味の入力)で、丸め誤差の規模です。
大きな値が出たら不具合なので報告してください。

## 適用範囲と併用の制限

- **位相平均・代表周期 1 個**です。回折・反射・周波数の広がり・風による発達・非線形の
  波の相互作用は扱いません。陰の縁のぼけは数値拡散で、回折ではありません。
- **段 W1 は流れ・地形に作用しません。** 波による沿岸流・セットアップ・漂砂は後の段です。
  流れ(河川流・潮流・津波)による波の変化(ドップラー効果・阻止)もまだ入りません。
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

分散関係は Fenton & McKee(1990)[^fm90] の陽な近似を初期値に Newton 法 3 回で解きます。

## 検証・例題

- [test/wfshoal](../../test/wfshoal/README.md): 勾配 1/80 の海浜断面。規則波の浅水変形と
  飽和砕波(線形理論と一致)、屈折(Snell の法則と方向ビンの 1 次収束)、不規則波の砕波
  (Baldock・Janssen & Battjes。Python で独立に書いた散逸式による離散解と一致、細かい刻みの
  エネルギー式との差 1%)、非定常の前線の到達と定常解、台帳の閉合、再開の継続のバイト一致、
  波浪場の有無で流れが同じこと、沖の波の時系列の補間。
- [test/wfshadow](../../test/wfshadow/README.md): 防波堤と斜めの壁の囲い。独立に実装した
  掃引解との一致、斜めの壁の遮断、格子方向に揃った波の陰が厳密に鋭いこと。
- どちらも MPI の np = 1・2・4 で逐次とビット一致します。

## 参考文献

[^baldock98]: Baldock, T. E., Holmes, P., Bunker, S. & Van Weert, P. (1998) Cross-shore hydrodynamics within an unsaturated surf zone. Coastal Engineering 34, 173–196.
[^bg68]: Bretherton, F. P. & Garrett, C. J. R. (1968) Wavetrains in inhomogeneous moving media. Proc. R. Soc. Lond. A 302, 529–554.
[^eurotop]: EurOtop (2018) Manual on wave overtopping of sea defences and related structures, 2nd ed. Van der Meer, J. W., Allsop, N. W. H., Bruce, T., De Rouck, J., Kortenhaus, A., Pullen, T., Schüttrumpf, H., Troch, P. & Zanuttigh, B. www.overtopping-manual.com
[^fm90]: Fenton, J. D. & McKee, W. D. (1990) On calculating the lengths of water waves. Coastal Engineering 14, 499–513.
[^gt85]: Guza, R. T. & Thornton, E. B. (1985) Velocity moments in nearshore. J. Waterway, Port, Coastal, Ocean Eng. 111(2), 235–256.
[^hiswa]: Holthuijsen, L. H., Booij, N. & Herbers, T. H. C. (1989) A prediction model for stationary, short-crested waves in shallow water with ambient currents. Coastal Engineering 13, 23–54.
[^jb07]: Janssen, T. T. & Battjes, J. A. (2007) A note on wave energy dissipation over steep beaches. Coastal Engineering 54, 711–716. 砕波波高 H_b の形は Battjes, J. A. & Janssen, J. P. F. M. (1978) Energy loss and set-up due to breaking of random waves. Proc. 16th ICCE, 569–587 の Miche 型(XBeach の定式と同じ)。
[^kuik88]: Kuik, A. J., van Vledder, G. Ph. & Holthuijsen, L. H. (1988) A method for the routine analysis of pitch-and-roll buoy wave data. J. Phys. Oceanogr. 18, 1020–1034.
[^snapwave]: Roelvink, D., van Ormondt, M., Reyns, J. & van der Lugt, M. (2025) SnapWave: fast, implicit wave transformation from offshore to nearshore. Geosci. Model Dev. 18, 9469–9495. doi:10.5194/gmd-18-9469-2025(既定値は公開ソースによる)
[^swan]: Booij, N., Ris, R. C. & Holthuijsen, L. H. (1999) A third-generation wave model for coastal regions: 1. Model description and validation. J. Geophys. Res. 104(C4), 7649–7666.
[^tarboton97]: Tarboton, D. G. (1997) A new method for the determination of flow directions and upslope areas in grid digital elevation models. Water Resour. Res. 33(2), 309–319.
[^vanleer74]: van Leer, B. (1974) Towards the ultimate conservative difference scheme. II. Monotonicity and conservation combined in a second-order scheme. J. Comput. Phys. 14, 361–370.
[^xbeach]: Roelvink, D., Reniers, A., van Dongeren, A., van Thiel de Vries, J., McCall, R. & Lescinski, J. (2009) Modelling storm impacts on beaches, dunes and barrier islands. Coastal Engineering 56, 1133–1152. 定式と既定値は XBeach マニュアル(xbeach.readthedocs.io)と公開ソース(params.F90)による。
