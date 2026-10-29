# 沿岸の波浪場の解説(沿岸の波浪場の補足)

[沿岸の波浪場の章へ](wavefield.md) | [ユーザーガイド目次へ](../users_guide.md)

[沿岸の波浪場の章](wavefield.md)の背後にある基礎式・数値解法・流れと土砂への作用の定式・遡上域の
経験式と、既定値の根拠をまとめます。§12 に、参考にした他モデル・研究と、ENCflow 独自の理論・実装を
分けて示します。本文でも、ENCflow 独自の定式・離散化には **独自** と記します(要素は既存の手法でも
組み合わせが独自のものは **独自の組み合わせ**、原典の式を簡略化したものは **独自の簡略化** と
書きます)。印のない式は、脚注の文献・他モデルの形に従っています。

実装は `src/m_wavefield.f90`(波浪場・流れへの作用・流れによる波の変化)、`src/m_geomorph.f90`・
`src/m_geomorph_fluvial.f90`・`src/m_geomorph_suspend.f90`(攪拌と輸送)、`src/m_geomorph_swash.f90`
(遡上域の輸送)、`src/m_swflow_enc*.f90`(外力・波・流れの摩擦・側方 Neumann の境界・浮遊砂の輸送)
です。設計の経緯と代替案の比較は docs/wavefield_plan.md、方針の例外(developer.md §0-5)と決定・
実装・検証の記録は developer.md §90 にあります。開発は段階に分けて行ったので、記録は段の名前で
書かれています(段 W1 = 波浪場、W2 = 流れへの作用、W3 = 流れによる波の変化、W4・W5 = 土砂への作用。
遡上域の輸送は §90.21)。

## 1. 位置づけと全体の構成

**モデルの階層。** 方向ビンごとのエネルギー(流れがあるときは作用量)の平衡を、代表周期 1 個・
位相平均で解きます。周波数の次元・風による発達・非線形相互作用を持たない、HISWA[^hiswa] →
XBeach の定常モード[^xbeach] → SnapWave[^snapwave] の系譜と同じ階層の概算です。目標はこれらの
専用モデルと精度で競うことではなく、同じ階層の概算を、流域・河川・洪水・津波・土砂と同じ格子・
同じ時間発展の中で動かすことです。単一波系の WKB・スペクトルモデル・位相解像モデルを採らなかった
理由は §12.1 にあります。

**作用の向き。** 波浪場と他のプロセスは、共有状態を介して次の量を受け渡します。どの作用も既定では
無効で、無効のときは配列も計算も加わりません。

| 作用 | 受け渡す量 | 節 |
|---|---|---|
| 波 → 流れ(`wf_flow`) | 放射応力の勾配(波 + ローラー)・Stokes 輸送・波・流れの摩擦の速さ・砕波の渦動粘性(`wf_break_visc`) | §6 |
| 流れ → 波(`f_wf_current`) | 浅水流の流速(ドップラー効果・流れによる屈折・流れによる輸送) | §7 |
| 波 → 土砂(`f_wfsed`) | 底面軌道流速・軌道の振幅・平均波向・岸向きの速度 u_a・Stokes 輸送(・底面の乱れ) | §8 |
| 遡上域(`f_wfswash`) | 入射波の波高・周期、汀線の近くの波高 | §9 |

**時間ループの中の位置。** 波浪場は各ステップで潮位の後・浅水流の前に更新するので、外力と摩擦は
同じステップの波浪場を使います。準定常(`wf_mode = 2`)は `dt_wave` ごとに定常解を求め、その間は
外力・Stokes 輸送・軌道流速を保ちます(波・流れの摩擦の速さは、保った軌道流速とそのステップの流速から
毎ステップ求めます)。非定常(`wf_mode = 1`)は毎ステップ進めます(§4.3)。

## 2. 基礎式

### 2.1 方向ビンのエネルギー平衡

方向ビン m(中心の向き θ_m)ごとのエネルギー密度 E_m [J/m²/rad] について

```math
\frac{\partial E_m}{\partial t} + \nabla\cdot\left(c_g\,\hat{\mathbf e}_m E_m\right)
+ \frac{\partial (c_\theta E_m)}{\partial \theta}
= -\left(D_w + D_f\right)\frac{E_m}{E},
\qquad E = \sum_m E_m\,\Delta\theta
```

を解きます。作用量の保存(Bretherton & Garrett 1968[^bg68])を SWAN[^swan] の形から周波数 1 個に
縮約したもので、HISWA・XBeach と同型です。流れがなければ周波数は一定なので、作用量とエネルギーの
保存は同じです(流れがあるときは §7.2 の作用量の平衡)。右辺の散逸 $`D_w`$(砕波)・$`D_f`$
(底面摩擦)は、全エネルギーに対する散逸を各ビンへ E_m/E に比例して配分します(XBeach と同じ)。

### 2.2 分散関係・群速度・屈折の速さ

群速度 $`c_g`$ と屈折の速さ $`c_\theta`$ は線形理論の分散関係から求めます。

```math
\sigma^2 = g\,k\tanh(kh),\qquad
c_g = \frac{\sigma}{2k}\left(1 + \frac{2kh}{\sinh 2kh}\right),\qquad
c_\theta = \frac{\sigma}{\sinh 2kh}\left(\sin\theta\,\frac{\partial h}{\partial x}
- \cos\theta\,\frac{\partial h}{\partial y}\right)
```

(σ = 2π/T、x は東・y は北。)$`c_\theta`$ は SnapWave と同じく |c_θ| ≤ σ/4 に制限し、急な地形での
過大な屈折を抑えます。水深の勾配は軸方向の中央差分で、隣が波浪セルでなければ片側差分にします。
分散関係は Fenton & McKee(1990)[^fm90] の陽な近似を初期値に Newton 法 3 回で解きます。

### 2.3 波高・平均波向・軌道流速

波高は不規則波で H_rms = (8E/ρg)^{1/2}、出力は有義波高 H_m0 = √2 H_rms(Rayleigh 分布)、
規則波で H = (8E/ρg)^{1/2} です(ρ = 1025 kg/m³)。平均波向は
atan2(Σ E_m sin θ_m, Σ E_m cos θ_m)、底面軌道流速は u_rms = H_rms σ/(2√2 sinh kh)(XBeach の定義)
です。

### 2.4 沖の波と方向分布

入射の辺の外にある沖の波のエネルギーは、不規則波で E_0 = ρgH_m0²/16、規則波で
ρgH²/8 です。方向の分布は cos^s(θ − θ_0)(|θ − θ_0| < 90°)で、指数 s は方向分散 σθ
から Kuik ら(1988)[^kuik88] の定義 σθ² = 2(1 − m_1)で逆算し、ビンで離散的に正規化
します(Σ D Δθ = 1。SWAN と同じ分布形)。σθ = 0 は θ_0 を挟む 2 ビンへ線形に配分します。
ビン数 N_θ は 8 の倍数に限り、x・y の軸と対角の向きが必ずビンの中心に乗ります。

代表周期は分散関係の σ = 2π/T にそのまま使います。不規則波の既定の解釈はエネルギー周期 T_m−1,0 で、
ピーク周期からの換算の目安 T_m−1,0 ≈ T_p/1.1(単峰のスペクトル)は EurOtop(2018)[^eurotop] によります。

## 3. 空間の輸送(2 リンク分解の風上法。独自)

ENC の 8 近傍格子で、ビン m の伝播速度 $`c_g\hat{\mathbf e}_m`$ を、その向きを挟む
**2 本の格子方向(軸と対角)へ非負に分解**し、それぞれのリンクで風上(送り手の
セルの値)へ運びます。格子で正規化した p_x = c_g cos θ/Δx、p_y = c_g sin θ/Δy に
ついて |p_x| ≥ |p_y| なら軸 x へ率 |p_x| − |p_y|、対角へ率 |p_y| です(逆も同様)。
傾斜流向の D∞(Tarboton 1997[^tarboton97])が流向を 8 近傍の 2 セルに角度で按分するのと
同じ発想を、波のエネルギーの流束に使う **独自** の離散化です。受け手が送り手から集める形で
書くので、計算はセルの処理順に依りません。

- **格子方向(軸・対角)の伝播では横断の数値拡散がありません。** 正方格子・一様な速度の
  1 次風上の修正方程式の主要項(ENCflow での導出)は

  ```math
  D_\perp = \frac{c\,\Delta}{2}\,(\cos\varphi - \sin\varphi)\sin\varphi\cos\varphi
  ```

  (φ は最寄りの軸からの角度、0 ≤ φ ≤ 45°)で、φ = 0°・45° で 0、最大は φ ≈ 21° の 0.096 cΔ です。
  ENC の通過幅による有限体積の 1 次風上は軸方向で 0.293 cΔ、4 近傍の 1 次風上は 45° で 0.354 cΔ です。
- **陰の縁はこの数値拡散でぼけます。** 一様な媒質で半平面を照らし 100 セル進めた定常解の陰の縁の
  幅(10〜90 %)は、軸・対角の向きで 1 セル未満(実質的に鋭い。test/wfshadow の aligned)、
  その間の向きで約 10〜12 セルでした(ENC の有限体積に MUSCL を組んだ形は格子方向でも 4.6〜6.0
  セル)。これは実際の回折(陰に回り込む波)とは別物で、位相平均のこのモデルは回折を扱いません。
  斜めの向きの縁を鋭くする高次の補正(リンク方向の van Leer)は試作で約 3 セルまで鋭くなりましたが、
  回折を持たないモデルで陰の縁だけを鋭くすると実際の回折のぼけより鋭い陰になるので採っていません
  (周期 8 s・水深 10 m の半平面回折の強度の 10〜90 % 幅は距離 1 km で約 220 m。1 次の 2 リンク分解の
  斜めの向きの幅は Δx = 10 m で 100〜120 m)。
- 輸送は保存的で、エネルギーは負になりません。陽的な更新の安定条件(流出率 × Δt ≤ 1)は、群速度が
  浅水の波速 √(gh) を超えないので浅水流のクーラン条件に含まれます(超えるときはサブステップに
  します)。
- **対角リンクの両脇の 2 セルがともに非波浪セル(陸など)なら、その対角は閉じます(独自)。**
  角だけで接する 1 セル厚の斜めの堤を、波はすり抜けません(test/wfshadow の菱形の囲い)。
  1 セル幅の斜めの水路に水を通す浅水流の ENC とは意図的に違う規則で、水が通れることと
  短周期波が透過できることを区別しています。

## 4. 方向空間の屈折と時間進行

### 4.1 方向空間の屈折

セルごとに θ 方向の移流 ∂(c_θ E_m)/∂θ を、1 次風上の陰解法(周期境界の三重対角。M 行列なので
非負)で解き、van Leer の制限関数[^vanleer74]による 2 次の補正を前の値から足します(遅延補正。
準定常の収束時は制限つき 2 次の流束の釣り合いを満たします)。陰的な 1 次風上と制限関数はどちらも
標準的な手法で、この組み合わせ方は **独自の組み合わせ** です。1 次風上だけでは方向空間の数値拡散で
屈折が遅れ、中心差分と風上の混合(SWAN の CDD 型)は単一方向の入射で負のエネルギーが出て準定常の
反復が収束しなかったので採っていません。

屈折の誤差はビン幅に比例して小さくなります(1 次収束)。勾配 1/80 の平行等深線の海浜に 30° で
入る波では、水深 1 m までの平均波向の Snell の法則からのずれは N_θ = 40 で 1.5°、
N_θ = 80 で 0.6°、波高のずれは 0.5%・0.3% でした(test/wfshoal の refr)。

### 4.2 源項

砕波・底面摩擦・上限の散逸は、セル内で半陰的に解きます。前の値で D/E を評価し、陰的な減衰
E_new = E*/(1 + Δt D/E*) として掛けるので、エネルギーは負にならず、除いた量を台帳に記録します。

### 4.3 準定常と非定常(1 つの核と 2 つのモード)

1 回の更新は、空間の流入出(前の値から新しい値を作る陽的な Jacobi 型の更新)と、セル内の屈折と
源項(陰的)の組です。この 1 つの核を 2 つの使い方で回します(**独自の組み合わせ**。Jacobi 反復・
局所時間刻みはどちらも標準的な手法)。

- **準定常(`wf_mode = 2`)**: `dt_wave` ごとに、セルごとの擬似時間刻み Δτ = 1/(最大流出率)で
  反復して定常解に収束させます(前回の解から始める)。定常解は流入出と源項の釣り合いだけで決まり、
  Δτ に依りません。収束の判定(1 回の反復での波高の変化の最大 / 沖の波高 < `wf_tol`)は全ランクの
  最大で決めます。
- **非定常(`wf_mode = 1`)**: 物理時間の dt で毎ステップ進めます(流出率 × dt > 1 なら
  サブステップ)。波の前線は群速度で進みます(test/wfshoal の unst)。十分な時間の後は準定常と同じ
  定常解に達します。

どちらもセルの更新順に依らない形なので、MPI の分割数・スレッド数によらず結果はビット単位で
一致します。SWAN・SnapWave の掃引解法(風上側から順に処理し、1 回の掃引でその方向の定常解を得る)は
反復を大きく減らせますが、結果が処理の順に依存し、分割数によらないビット一致には並列の作り込みが
要るので採っていません(必要が実測で示されたときの性能の候補)。

### 4.4 境界と波浪セル

外縁の各辺は次のいずれかです。

| 型 | 格子の外の仮想の送り手が持つ値 | 使いどころ |
|---|---|---|
| 1 入射 | 沖の波のビン別エネルギー | 沖の辺 |
| 2 側方 Neumann | 境界の内側のセルの値 | 海岸に交わる左右の辺(外にも同じ海が続く。XBeach の側方境界と同じ考え方) |
| 0 吸収 | 0 | 外に海がない辺・陸側の辺 |

各リンクの送り手は 1 つなので、角で二重に注入しません。外へ出ていく波は自由に出ます(反射しません)。
角(x・y とも格子の外)の仮想の送り手は 入射 > 側方 Neumann > 吸収 の優先で辺の型を決めます
(**独自**。入射の辺の角の外を沖の波の領域とみなし、直線海岸で岸沿いに一様な解を崩さない)。

**波浪セル**は、領域内(x > 0)で、海域マスクの海セル(sw)でも吸収セルでもなく、
水深が `wf_hmin` を超えるセルです。陸・乾燥セル・海セル・吸収セルへ向かう波は
吸収されます(反射なし。台帳の「吸収」)。海セルは潮位を与える境界のセルで浅水流でも解かないので、
波浪の計算域からも外します(沖は「解く海」で表す)。**家屋の空隙率 gv < 1 のセル**と**サブグリッド
河道の幅・断面形のセル**は、波との関係をこの版では表さないので吸収セルとして明示し、その数を
開始時に表示します(未対応の組み合わせを黙って計算しない)。

## 5. 砕波・底面摩擦・上限

**不規則波**の砕波は、既定の Baldock ら(1998)[^baldock98]

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
水深による上限 H_rms ≤ γmax h をかけます(超えた分は台帳の「上限」に数えます)。式の形は XBeach の
マニュアルに従い、原典の形と照合しました。SnapWave の公開ソースの Baldock の式は係数 0.28・
H_b = γh で XBeach と違い、本実装は XBeach の形に従います。

**規則波**(`wf_wavetype = 2`)は H ≤ γh の飽和(飽和砕波)だけで、確率的な砕波は
入りません。理論解と比べる検定用です。

**底面摩擦**は D_f = c ρ f_w u_orb³、u_orb = πH_rms/(T sinh kh)(規則波は H)で、
c = 0.28(不規則波)・0.21(規則波)です(Guza & Thornton 1985[^gt85] の速度の 3 次
モーメントの係数。XBeach の定式)。既定は f_w = 0(摩擦なし。XBeach 定常モードの既定)です。

## 6. 流れへの作用(wf_flow)

### 6.1 放射応力と外力

方向ビンのエネルギーから放射応力(Longuet-Higgins & Stewart 1964[^lhs64])を

```math
S_{xx} = n\sum_m E_m\cos^2\theta_m\,\Delta\theta + \left(n - \tfrac12\right)E + E_r\cos^2\bar\theta,\qquad
S_{xy} = n\sum_m E_m\cos\theta_m\sin\theta_m\,\Delta\theta + E_r\cos\bar\theta\sin\bar\theta
```

(S_yy も同様。n = c_g/c、θ̄ は平均波向、E_r はローラーのエネルギー)で求め、波の外力
$`F_i = -\partial S_{ij}/\partial x_j`$ をセル中心で差分(両隣が波浪セルなら中央差分、片側なら片側差分)
します。直角に入る波では、砕波帯より沖で平均水位が下がり(set-down)、砕波帯で上がります(set-up。
Longuet-Higgins & Stewart 1962[^lhs64]、Bowen ら 1968[^bowen68])。斜めに入る波では、砕波で S_xy が
減る分が沿岸方向の外力になり、沿岸流を駆動します。

**面への射影(独自)。** 浅水流の各面には、両セルの外力の平均を面の向きへ射影して $`F_k/(\rho h)`$ を
加速度として足します。h は両セルの平均水深です。x 方向にだけ変わる 1 次元のセットアップでは、軸の面と
対角の面が同じ釣り合いの式になり(対角は両辺に同じ方向余弦が掛かるだけ)、面の間に偽の循環を作り
ません。面の水深に摩擦と同じ風上側の水深(流速の向きで切り替わる)を使うと、静止に近い釣り合いで
流速の符号が揺らぐたびに外力が切り替わり、行ごとに違う駆動が残って循環がゆっくり育ったので、
符号に依らない平均水深にしています。

### 6.2 ローラー

砕けた波のエネルギーは、いったん波頭の表面の渦(ローラー)に移ってから散逸します。
ローラーのエネルギー E_r(J/m²)は波の平均波向・位相速度 c(= σ/k)で運ばれ、

```math
\frac{\partial E_r}{\partial t} + \nabla\cdot\left(c\,\hat{\mathbf e}_{\bar\theta}E_r\right) = D_b - D_r,\qquad
D_r = \frac{2\beta g E_r}{c}
```

を解きます(Svendsen 1984[^svendsen84]、Reniers & Battjes 1997[^rb97]。D_b は砕波の散逸と
上限で除いた分)。ローラーの放射応力 E_r cos²θ̄ 等は Nairn ら(1990)[^nairn90] の近似で、
XBeach と同じ形です。ローラーは砕波の運動量をいったん蓄えて岸側で放すので、外力・セットアップ・
沿岸流の最大が岸側へずれます(砕波点の直後で流れが立ち上がる遅れ)。空間の輸送は平均波向の
2 リンク分解の風上法(§3)、散逸は半陰的で、準定常では定常解、非定常では同じ時間刻みで進めます。

### 6.3 GLM と波・流れの底面摩擦(wf_flow = 2)

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
大きく強めます。差し替えるのはマニング則の摩擦の速さだけで、家屋の抗力・土石流の降伏の項は
流れの速さのままです(作用する流速はどれもオイラー流速)。

### 6.4 砕波による水平混合(list_enc の wf_break_visc)

砕波の乱れは運動量を横方向にも混ぜ、沿岸流の岸沖分布をならします。`wf_break_visc` = M > 0 のとき、
波浪場が更新ごとに渦動粘性

```math
\nu_w = M\,h\left(\frac{D}{\rho}\right)^{1/3}
```

(Battjes 1975[^battjes75]。D はローラーがあればその散逸 D_r、なければ砕波の散逸 D_w、
ρ = 1025 kg/m³)を求め、[拡散項](diffusion.md)の ν に足します(`f_diffusion_term = 0` でも
拡散項が計算されます)。式は XBeach の nuhfac と同じ形で、M = 1 が XBeach の既定です[^xbeach]
(Battjes 1975 の原論文は照合していません)。XBeach での背景の粘性との組み合わせ方は照合して
いないので、本実装は非静水圧の砕波の渦粘性 `nh_break_visc` と同じく和(ν = ν_model + ν_b + ν_w)
にしています(**独自の組み合わせ**)。準定常では波浪場の更新の間 ν_w を保ちます。test/wfcurrent の
海浜で ν_w の最大は砕波帯の中の 0.54 m²/s、沿岸流の最大は 3.3% 下がり、分布の広がりは 3.8% 増えます。

### 6.5 外力の立ち上げ

準定常の波浪場は開始時に全域で満値になるので、急に加わる外力が汀線付近の振動(副振動)を
起こします。外力と Stokes 輸送に、時間軸の起点 t0 から線形に増える係数
r = min(1, (t − t0)/`wf_tramp`) を掛けます(XBeach の taper と同じ考え方)。勾配 1/80 の海浜で、
立ち上げなしでは開始 2 分の汀線の流速が 0.2 m/s に達し、600 s の立ち上げで 0.03 m/s でした。

### 6.6 側方 Neumann の境界(f_bc = 3。独自)

沿岸流のための側方 Neumann(外にも同じ海岸・同じ流れが続く = 法線方向の勾配 0)の辺は、境界面の
運動方程式を、枠外の相手を辺の法線方向に枠内へ寄せたセル(鏡像セル)として、内部の面と同じ式で
解きます(**独自**)。岸沿いに一様な流れで境界の行が内部の行と同じ解になるよう、次をそろえています。

- **乾湿と抑制**: 両側が乾いたときだけ閉じ、適応的ルンゲクッタの判定・過大な流出の抑制を内部の面と
  同じにします(流入は鏡像セルが送り手)。
- **塞がれた開口の通過幅の振り替え**: 枠外を鏡像セルで判定し、境界面の係数は一つ内側の面から写します
  (枠外を壁とみなすと、境界の行の軸の面だけに斜めの分の通過幅が上乗せされる)。
- **移流項**: 境界面の検査体積を、内部の面と同じ式で、枠外の位置を鏡像セルで読んで求めます。枠外から
  入る流れの流入面の寄与は 0 なので、辺から入る流れを移流が加速しません。岸沿いに一様な場では、
  一つ内側の面の検査体積を平行移動したものと式の上で同じになります。
- **拡散項**: 辺に接するセルの拡散を、枠外の近傍を鏡像セルに置き換えて求め、境界面には自セルと
  鏡像セルの拡散の平均を足します。
- **土砂**: 浮遊砂などのスカラーは鏡像セルの濃度で流入し(MUSCL の再構成も枠外を鏡像の値で読む)、
  掃流砂は辺の法線方向に一つ内側の面の流束を写します。

test/wfcurrent の海浜の沿岸流で、境界の行を含む全行の差は流速の最大の約 0.03 % です。採らなかった
形として、境界面の流速・流量を一つ内側の面からそのまま写す形は、境界の行の水位と流量の正帰還で
発散しました。境界面の移流項を一つ内側の面から写す形(最初の版)は、岸沿いに一様でない流れの
流入側の辺で流入が強まり続けることがあったので、上の検査体積の形に改めました(developer.md §90.16・
§90.19)。

## 7. 流れによる波の変化(f_wf_current)

### 7.1 ドップラー効果と阻止

流れ $`\mathbf U`$ の上の波の分散関係は、方向ビン m の向き $`\hat{\mathbf e}_m`$ の流速成分
$`U_m = \mathbf U\cdot\hat{\mathbf e}_m`$ を使って

```math
(\omega - k U_m)^2 = g k \tanh kh
```

です(Bretherton & Garrett 1968[^bg68])。ω は沖の波の角周波数で、流れが定常なら波の山の数の
保存により変わりません。セルとビンごとにこの式を U_m → 0 で連続な枝で解き、固有角周波数
$`\sigma_m = \omega - k_m U_m`$ と固有の群速度 c_g,m = n σ_m/k_m を求めます。流れなしの根から
Newton 法で解き、σ_0(k) + kU_m − ω が上に凸なので、根を越えずに単調に近づきます。逆流
(U_m < 0)では k_m が大きく σ_m > ω、順流では逆です。逆流が強く、群速度と流れが打ち消し
合う(c_g,m + U_m ≤ 0)か根がなくなると、そのビンの波は**阻止**され、届いた作用量は
台帳の blocked に記録して除きます。

XBeach は波数を Eikonal 式で時間発展させますが、定常な流れでは同じ根になります。単一の代表周波数
では、定常な流れの中で絶対角周波数 ω が一定なので、ω を固定して方向ビンごとに波数を直接解く形が
整合します(**独自**)。時間変化する流れによる ω の変化は入れません(**独自の簡略化**)。

### 7.2 作用量の平衡

流れがあると波のエネルギーは保存しませんが、**波の作用量 N = E/σ** は保存します
(Bretherton & Garrett 1968)。

```math
\frac{\partial N_m}{\partial t} + \nabla\cdot\left[(c_{g,m}\hat{\mathbf e}_m + \mathbf U)N_m\right]
+ \frac{\partial (c_\theta N_m)}{\partial\theta} = -\frac{D_m}{\sigma_m}
```

空間の輸送は、速さ $`c_{g,m}\hat{\mathbf e}_m + \mathbf U`$ をセルとビンごとに §3 と同じ
2 リンク分解の風上法で運びます(送り手ごとに分解が違うので、受け手は 8 近傍の送り手を調べて
集めます)。方向空間の屈折の速さには、流れの速さの勾配による項を足します(x 東・y 北。SWAN[^swan]・
XBeach[^xbeach] と同じ形。勾配は §2.2 と同じ規則)。

```math
c_\theta = \frac{\sigma}{\sinh 2kh}\left(\frac{\partial h}{\partial x}\sin\theta - \frac{\partial h}{\partial y}\cos\theta\right)
+ \cos\theta\left(\sin\theta\frac{\partial u}{\partial x} - \cos\theta\frac{\partial u}{\partial y}\right)
+ \sin\theta\left(\sin\theta\frac{\partial v}{\partial x} - \cos\theta\frac{\partial v}{\partial y}\right)
```

砕波・底面摩擦・上限は、エネルギー $`E_m = \sigma_m N_m`$ とエネルギー重みの平均の波数・
固有角周波数で、§5 と同じ式で評価します。作用量は時間変化する流れの中でも保存する量
(断熱不変量)なので、計算の状態は作用量で持ち、流れが変わってもそのまま引き継ぎます
(非定常の台帳も流れの時間変化の間に閉じます)。台帳の量は作用量 × ω です。

使う流速は浅水流の流速そのものです(`wf_flow = 2` では Lagrangian 平均流速 u^L。XBeach の
wci と同じ[^xbeach])。ローラーも流れで運ばれ(速さ c ê + U、c = σ̄/k̄)、放射応力と Stokes 輸送には
ビンごとの固有の n_m・c_m を使います。

### 7.3 沖の格子規模の縞の仕組み

流れによる屈折の速さは流れの勾配を中央差分で求めるので、その応答は波長 4 セルの流れの縞で最大に
なります。波による流れ(`wf_flow = 2`)と組むと、流れの縞が波を屈折させ、波高の縞が外力の縞を生み、
それが流れの縞を強める正帰還になり、沖の静かな水域に波長 3〜4 セルの斜めの縞が時間とともに育つことが
あります(地形の変化がなくても育ちます)。作用量の平衡は、媒質(水深・流れ)が波長に比べてゆっくり
変わる前提(WKB)の式で、波長(水深 2 m・周期 6 s で約 27 m)より短い格子規模(examples/delta で
約 17 m)の流れの変化を波に効かせるのは、その前提の外にあります。

対策は、設定で背景粘性を足す形にしました(章の「沖の格子規模の縞と背景粘性」)。examples/delta の
wfsed の構成(固定床にして切り分け)で、背景粘性 ν0 = 0.05 m²/s で縞が育たず、汀線から 3 セル以内の
流速の平均は変わらず、河口の噴流の最大は −1 % でした(0.2 m²/s では −6 %)。波に渡す流れから波長より
短い規模を除く構造の対策は、試作で縞が止まりましたが、設定で止まることと、ならす幅の決め方の議論が
要ることから採っていません(developer.md §90.20)。

### 7.4 計算量と収束

流れがあると、更新ごとにセルとビンごとの分散関係と輸送の分解を求め直し、ビンごとの量(波数・
固有角周波数・流出率と流出先・屈折の速さ)を持ちます(メモリは章の「計算量と収束」)。阻止の近くでは
群速度と流れが打ち消し合うビンの作用量の移動が遅く、岸沿いに一様な場で側方 Neumann の辺を通って
循環する成分はほとんど減衰しないので、準定常の反復の収束が遅くなります。ビンごとの擬似時間刻み
(遅いビンを速める)は、前の値で評価する非線形の砕波と組み合わさって振動し、収束しなかったので
採っていません。

## 8. 土砂への作用(f_wfsed)

### 8.1 攪拌(波・流れの底面せん断)

波の底面の軌道流速の振幅 u_w = √2 u_rms(Soulsby の不規則波の代表振幅。u_rms は出力 Wu)と軌道の
振幅 A = u_w/σ̄(σ̄ は固有角周波数)から、波の底面せん断と、流れのせん断との合成を
Soulsby(1997)[^soulsby97] の式で求めます。

```math
\tau_w = \tfrac12 \rho f_w u_w^2,\quad f_w = \min\left(1.39\,(A/z_0)^{-0.52},\ 0.3\right),\quad z_0 = d_{50}/12
```

```math
\tau_m = \tau_c\left[1 + 1.2\left(\frac{\tau_w}{\tau_c + \tau_w}\right)^{3.2}\right],\quad
\tau_{max} = \sqrt{(\tau_m + \tau_w|\cos\varphi|)^2 + (\tau_w\sin\varphi)^2}
```

τ_c は流れだけのせん断(既存の Manning の閉じ τ* = n² V²/(s d h^{1/3}) で、V は §8.3 の Euler 平均
流速 u^E の速さ)、φ は流れと平均波向のなす角、τ_max は波の周期の中の最大のせん断です。
掃流砂の流砂量式(`f_qbform`)と浮遊砂の平衡濃度式(`f_esform`)の無次元掃流力に τ*_max を
使います(閾値の判定も。Soulsby が τ_max を閾値と巻き上げに勧めることに合わせる)。z0 は粒子の
粗さ(k_s = 2.5 d50 の z0 = k_s/30)、上限 0.3 は小さな A での Swart(1974)[^swart74] の値です。
波がなければ τ*_max = τ*_c で、`f_wfsed = 0` と同じ式です。

### 8.2 砕波の乱れによる攪拌(f_wfsed_turb)

砕波の乱れが底面まで届く汀線側では、軌道運動のほかに乱れも砂を巻き上げます。ローラーの散逸 D_r が
つくる表面の乱れ k_s = (D_r/ρ)^{2/3}(Battjes 1975[^battjes75])を、ローラーの厚さ
L_mix = √(2E_r T/(ρc))(Svendsen 1984[^svendsen84]。T は代表周期)の指数で底面へ減衰させ
(Roelvink & Stive 1989[^rs89])、

```math
k_b = \frac{k_s}{\exp(h/L_{mix}) - 1},\qquad u_{rms,2} = \sqrt{u_{rms}^2 + 1.45\,k_b}
```

§8.1 の u_w を √2 u_rms,2 にします(van Thiel de Vries 2009[^vtdv09]。XBeach の `turb` =
wave_averaged と同じ形[^xbeach])。ローラーなし(`f_wf_roller = 0`)では k_s = (D_w/ρ)^{2/3}、
L_mix = H_rms です。軌道の振幅 A と岸向きの速度 u_a、波・流れの底面摩擦は乱れを含まない u_rms の
ままで(XBeach と同じ)、u_w への上乗せだけが **独自の簡略化** です(XBeach は平衡濃度式の
速度に足す)。乱れはローラーの厚さが水深に比べて大きい汀線の近くで効きます(test/wfsed の海浜で
攪拌の速さが汀線のセルで 1.10 倍、砕波の散逸の最大のセルで 1.01 倍、沿岸漂砂は 1.9% 増)。

### 8.3 輸送速度(Euler 平均流速と岸向きの速度)

砂を運ぶ速度は u_s = u^E + u_a ê_θ です(ê_θ は平均波向の単位ベクトル)。

- **Euler 平均流速 u^E = u^L − u^S**: `wf_flow = 2` の浅水流の流速は Lagrangian 平均 u^L(水の
  質量輸送)で、Stokes 輸送 u^S は波の谷より上に集中します。浮遊砂は底近くに多いので、
  砂は Stokes 輸送を除いた Euler 平均流速で動きます(Reniers ら 2004[^reniers04]、XBeach と
  同じ[^xbeach])。砕波帯では u^E が沖向きの戻り流れになり、砂を沖へ運びます。溶存物質(水質・塩水)は
  鉛直に一様なので u^L のままです。
- **岸向きの速度 u_a**: 浅い所の波は山が尖り(歪度 S_k)前傾する(非対称 A_s)ので、岸向きの
  軌道流速が強く、砂は正味で岸へ運ばれます。XBeach と同じく van Thiel de Vries(2009)[^vtdv09]の
  u_a = (f_Sk S_k − f_As A_s) u_rms を使い、S_k・A_s は Ruessink ら(2012)[^ruessink12]の
  Ursell 数 Ur = (3/8)√2 H_rms k/(kh)³ によるパラメータ化で求めます
  (S_k = B cos ψ、A_s = B sin ψ、B = p₂/(1 + exp((p₃ − log₁₀ Ur)/p₄))、ψ = −90° + 90° tanh(p₅/Ur^{p₆}))。
  f_Sk・f_As(`wfsed_facsk`・`wfsed_facas`)は校正の係数で、既定 0.1 は XBeach の既定(facua)です。

**Ruessink ら(2012)との照合。** 式の形(論文の式 (6)〜(10))と Ursell 数の定義(a_w = 0.5√2 H_rms、
k は周期 T = T_m−1,0 の線形理論の波数。本モデルの代表周期の既定の解釈と同じ)は論文と一致します。
係数は XBeach と同じ値 p₂ = 0.7939・p₃ = −0.6065・p₄ = 0.3539・p₅ = 0.6373・p₆ = 0.5995(XBeach の
公開ソース morphevolution.F90)を使っていて、論文の最適値 p₂ = 0.857 ± 0.016・p₃ = −0.471 ± 0.025・
p₄ = 0.297 ± 0.021・p₅ = 0.815 ± 0.055・p₆ = 0.672 ± 0.073(p₁ = 0。± は 95 % 信頼区間)とは違います
(どれも信頼区間の外)。XBeach のソースの注記の式番号と誤差も出版された論文と合わず、XBeach の値の
出典は確認できていません。論文の値にすると、u_a は Ur ≈ 0.1〜0.3(砕波帯より沖)で 0.6〜0.8 倍、
Ur ≈ 1 でほぼ同じ、Ur ≈ 2〜20(砕波帯)で約 1.1 倍になります(f_Sk = f_As のとき)。

論文のパラメータ化は、方向に広がった波の多い現地観測(H_s 0.05〜3.99 m、T 3.1〜13.9 s、水深
0.25〜11.2 m、Ur 0.004〜24.8、海底勾配はおおむね 1/30 より緩い。遡上域を含まない)に当てはめた
もので、方向の狭いうねりや一方向の室内実験の波では歪度を過小に見積もる可能性があり、1/30 より急な
海底では使わないよう勧められています。

**浜の侵食と回復**は、沖向きの戻り流れ u^E と岸向きの u_a の釣り合いで決まります。高波浪では
戻り流れが勝って砂が沖へ運ばれ(砂州ができる)、低波浪・長周期のうねりでは砕波帯より沖で u_a が
勝って砂が岸へ戻ります(test/wfsed の storm・calm)。

### 8.4 浮遊砂と掃流砂の輸送の形

浮遊砂は浅水流の面流束から h(u^S − u_a ê_θ)(両セルの平均)を引いた流束で運びます(水と違う速度で
動く)。水の流量が 0 の面(壁・閉じた開口・堤防)では差し引きも行いません(土砂だけが壁を抜けない)。
掃流砂は

```math
q_b = q^*(\tau^*_{max})\sqrt{\tau^*_s/\tau^*_{max}}\,\sqrt{s g d^3}
```

を u_s の向きに運びます(τ*_s は u_s の速さの Manning のせん断)。τ*_max の流れが運ぶ掃流の量を
u_s の速さで運ぶ形で、波がなければ既存の式に一致し、流れがなく波だけなら u_a の向きに、
波が流れより強ければ流砂量は u_s の速さに比例します(XBeach の「平衡濃度 × 輸送速度」と同じ考え方)。
この組み合わせは **独自の組み合わせ** なので、Soulsby(1997)の波・流れの掃流砂の式と比べました。
test/wfsed の掃流砂の条件(水深 2.2 m・流れ 0.45 m/s・H_m0 0.5 m・T 6 s・φ = 30°)で、モデルの
無次元流砂量 Φ = 0.92 に対し Soulsby の式は 0.98 です(流れだけの MPM は 0.41)。

### 8.5 CERC との比較

test/wfsed の直線海岸(H_m0 = 1 m、T = 8 s、20°)の沿岸漂砂量(Qby・Qsy の岸沖方向の積分)は、
モデルの砕波点の波から求めた CERC(Komar & Inman 1970[^ki70])の 1.6 倍程度で、桁が合います
(CERC の係数も過程の漂砂の係数も校正の量です)。局所の波を CERC の式に入れる経路を選択肢として
持つことは、過程の漂砂と同じ輸送を二重に数える危険があるので採っていません(波を解かない簡易な
沿岸漂砂は fn_wave)。

## 9. 遡上域の輸送(f_wfswash)

位相平均の波浪場は汀線の手前で止まり(波浪セルは水深 `wf_hmin` 以上)、遡上の流れを持たないので、
§8 の輸送には、浅瀬の砂を汀線より上(遡上の届く高さ)へ積み上げる過程がありません。汀線の面
(湿ったセルと、地盤の高い乾いたセルの間)に、遡上の 1 周期で積分した正味の輸送の経験式を与えます。
式は原論文で照合しました。

### 9.1 岸沖(Larson ら 2004)

摩擦のない弾道の遡上(遡上の初速 u_s、遡上高 R = u_s²/2g)の上で、流速の 3 乗に比例し斜面で
上げ下げが非対称になる掃流の輸送(Madsen の式)を、遡上の 1 周期で積分した正味の輸送
(Larson, Kubota & Erikson 2004[^larson04] 式 (8)。正 = 沖向き。かさ体積の単位幅):

```math
q_c = K_c\, 2\sqrt{2g}\, R^{3/2}\left(1 - \frac{z}{R}\right)^2 \frac{\tan\phi_m}{\tan^2\phi_m - \tan^2\beta}\,(\tan\beta - \tan\beta_e)
```

z は静水面からの高さ、tanβ は前浜の勾配、tanβ_e は平衡勾配、φ_m は動く粒子の摩擦角です。前浜が
平衡より緩いと岸向き、急だと沖向き、平衡勾配で 0 です。K_c の既定 1.6×10⁻³ は、Larson らが
波崎海岸(細砂 0.18 mm)の現地実験の 4 例で較正した値の平均です(細砂の代表値。各例は
1.0〜2.3×10⁻³)。式は緩い前浜と、遡上の周期が入射波の周期と同程度(Iribarren 数 ξ0 ≳ 1)を
前提とします。

### 9.2 沿岸(Larson & Wamsley 2007)

斜めに入る波の遡上は沿岸方向の初速 v_s = u_s tanθ(θ = 汀線の法線と波向のなす角)を持ち、

```math
q_l = K_l \frac{\tan\phi_m}{\tan^2\phi_m - \tan^2\beta}\,\frac{u_o^2 v_o}{g}\,\frac{t_o}{T},\qquad
u_o = u_s\sqrt{1 - z/R},\quad \frac{t_o}{T} = \sqrt{1 - z/R},\quad v_o = v_s
```

(Larson & Wamsley 2007[^lw07] 式 (4)・(6)・(7))を遡上域の幅 R/tanβ で積分した量を汀線に沿って
運びます。K_l の既定は K_c と同じ値です(Larson & Wamsley の仮定。移動床の大型平面水槽 LSTF の
実験(Wang ら 2002)の遡上域の沿岸漂砂と合うことが示されています)。平均波向が汀線の法線から 80° 以上
なら沿岸の輸送はありません。

### 9.3 遡上高と露出度

Stockdon ら(2006)[^stockdon06] 式 (19) の 2 % 超過の遡上 R2 = 1.1 (⟨η⟩ + S/2)、
S = √(H0 L0 (0.563 β² + 0.004)) のうち、setup ⟨η⟩ は流れが解いて汀線のセルの水位に入っているので、
振れ幅の R = 1.1 S/2 をその水位から測ります。H0 は沖の境界の入射波高(深海へ逆算しない)、
L0 = gT²/2π(T は代表周期 `wf_trep` か `wf_val` の周期の列)、β は汀線のセルの前浜の勾配です。

デルタの陰や河道の内部のように波が届きにくい汀線では、汀線の ±2 セルの波浪セルの波高と、飽和した
波高 min(H_inc, γ_s h)(γ_s = 不規則波 √2 `wf_gammax`、規則波 `wf_gamma`)の比の最大(露出度 E。
1 で頭打ち)を H0 に掛けます(**独自**)。開けた海浜の汀線では波高が水深で飽和して E = 1 です。
近くに波浪セルがなければ遡上はありません。

Larson らは R を Mayer & Kriebel(1994)・Hunt(1959)の式(有義波高)で求めて K_c を較正しており、
Stockdon らの振れ幅と組むのは **独自の組み合わせ** です(R の定義の違いの分、K_c の値の意味は
ずれ得ます)。

### 9.4 格子への当てはめ(独自)

経験式を ENCflow の格子に当てはめる次の規則は、すべて **独自** です。

- 汀線のセル = 4 近傍(東西南北)に地盤の高い乾いたセルを持つ湿ったセル。岸沖の流束は、その
  4 近傍の面ごとに、面の両側のセルの勾配(中央差分)の平均 G を前浜の勾配とし(tanβ = |G|)、
  q_c の沖向きのベクトルの面の向きへの射影 × セルの辺の長さで与えます。湿った領域と乾いた領域の
  境は 4 近傍の面の階段なので、平面の海浜なら汀線の向きによらず単位長さあたり q_c になります
  (test/wfswash の diag で 45° の汀線を確認。斜めの面も使うと、粗い格子で 45° の汀線が 1/√2 に
  なります)。
- z は乾いたセルの地盤の汀線のセルの水位からの高さで、z ≥ R なら流束はありません = 堆積は遡上の
  上限 η + R を越えません。掃流砂の規則(土砂は水面より上へ登らない・乾いたセルは土砂を出さない)
  の例外として、乾いたセルへ積もり、乾いたセルから削ります。1 回の地形更新の 1 面の堆積は遡上の
  上限までの余裕と `fluv_dzmax` で縮めます(流量の段階なので保存則は保ちます)。
- 沿岸の流束は汀線のセルの 1 セル幅の帯に置き、帯を通る総量が遡上域の沿岸の輸送の総量になるよう
  帯の幅を汀線の向きから決め、fn_wave の沿岸漂砂(CERC 型)と同じ射影で 8 方向の面に流します。遡上域が汀線を
  挟むので、遡上の届く高さの乾いたセルとの面も通します。遡上の届く高さの乾いたセルが隣(4 近傍)に
  ない汀線のセル(遡上の届かない崖・護岸の前)には遡上域がないので、沿岸の流束も置きません(置くと、
  帯が崖に沿って砂を遠くまで運ぶベルトになります。test/wfswash の cliff)。
- 水の流路の幅の係数(サブグリッド河道の幅・塞がれた開口の振り替え)は掛けません(遡上域の流束は
  面の幅ではなく汀線の長さと帯の幅で決めているため)。

## 10. パラメータと既定値の根拠

根拠欄の分類語の意味は[既定値の根拠の読み方](../users_guide.md#既定値の根拠の読み方)を参照してください。

| パラメータ | 既定 | 意味 | 根拠 |
|---|---|---|---|
| `wf_gamma` | 0.78 | 砕波指標 γ | **文献値**: XBeach 定常モードの既定(孤立波の砕波限界に由来する慣用の値)[^xbeach] |
| `wf_alpha` | 1.0 | 砕波の散逸係数 α | **文献値**: XBeach 定常モードの既定[^xbeach] |
| `wf_gammax` | 0.6 | 水深による上限 H_rms ≤ γmax h | **文献値**: XBeach 定常モードの既定(H_rms の水深に対する上限)[^xbeach]。SnapWave[^snapwave] も同じ形・同じ値の上限を持つ |
| `wf_break` | 1 | 砕波の式(1: Baldock ら / 2: Janssen & Battjes) | **方式**: XBeach 定常モードの既定と同じ Baldock ら(1998)。急な海浜では Janssen & Battjes(2007)が散逸の過大を補正する |
| `wf_fw` | 0 | 底面摩擦係数 f_w | **校正量**: 既定 0(摩擦なし)は XBeach の既定[^xbeach]。岩礁などでは流れの摩擦係数より 1 桁以上大きいことがある(XBeach マニュアル) |
| 摩擦の係数 c | 0.28・0.21 | 底面摩擦の散逸の係数(不規則波・規則波) | **文献値**: Guza & Thornton(1985)[^gt85] の速度モーメント(XBeach の定式)。設定項目ではない |
| `wf_hmin` | 0.1 m | 波浪セルの最小水深 | **数値設定**: SnapWave の既定[^snapwave] |
| `wf_mode` | 2 | 1: 非定常 / 2: 準定常 | **方式**: 地形変化と組む用途(条件の変化が波の伝播時間より遅い)を既定にした |
| `dt_wave` | 3600 s | 準定常の更新間隔 | **数値設定**: SnapWave の既定の更新間隔[^snapwave] |
| `wf_ntheta` | 40(9°) | 方向ビン数 | **数値設定**: XBeach・SnapWave の既定 10° に近い 8 の倍数。屈折の誤差は §4.1 の実測(ビン幅に比例) |
| `wf_tol` | 1e-4 | 準定常の収束判定 | **数値設定**: 独自(波高の相対変化。検定では 1e-6〜1e-8 で解の差を確かめた) |
| `wf_spread` | 20° | 方向分散 σθ | **経験値**: 本プロジェクトの目安(独自)。風波〜うねりの代表的な広がりの中間として置いた値で、地点の波浪観測があればその方向分散を与える |
| ρ | 1025 kg/m³ | 海水の密度 | **慣用値**: 海水の密度(XBeach の既定)。設定項目ではない |
| `wf_flow` | 0 | 流れへの作用(0 なし / 1 外力 / 2 外力 + GLM + 波・流れの摩擦) | **方式**: 既定は流れに作用しない(波浪場を書いても流れは不変)。使うときは 2 を推奨(XBeach と同じ GLM と波・流れの摩擦) |
| `f_wf_roller` | 1 | ローラーのエネルギー平衡を解く | **方式**: XBeach の既定(roller = 1)[^xbeach]。外力の最大を岸側へずらす効果は観測と合う(Reniers & Battjes 1997[^rb97]) |
| `wf_beta` | 0.1 | ローラーの散逸係数 β | **文献値**: XBeach の既定(範囲 0.05〜0.3)[^xbeach]。Reniers & Battjes(1997)[^rb97] の 0.1 |
| `wf_tramp` | 100 s | 外力の立ち上げ時間 | **数値設定**: XBeach の taper の既定(定常の波浪場を全域で一度に与える同じ状況の始動)[^xbeach] |
| 摩擦の速さの係数 | 1.16 | 波・流れの摩擦の速さの u_rms の係数 | **文献値**: Ruessink ら(2001)[^ruessink01] の波・流れの摩擦(XBeach の定式)。設定項目ではない |
| `wf_break_visc`(&list_enc) | 0 | 砕波の渦動粘性の係数 M | **校正量**: 既定 0(混合なし)。M = 1 は XBeach の nuhfac の既定[^xbeach]。式は Battjes 1975[^battjes75] |
| `f_wf_current` | 0 | 流れの波への作用 | **方式**: 既定は流れの作用なし。式は Bretherton & Garrett(1968)[^bg68] の作用量の平衡で、流れによる屈折の式と使う流速(Lagrangian 平均)は XBeach の wci[^xbeach] と同じ。分散関係を方向ビンごとに直接解く点は独自(XBeach は Eikonal 式で波数を時間発展させる) |
| `f_wfsed`(&list_geomorph) | 0 | 波浪場による攪拌と輸送 | **方式**: 既定は土砂に作用しない。攪拌は Soulsby(1997)[^soulsby97] の波・流れのせん断の合成(f_w の上限 0.3 は Swart 1974[^swart74])、浮遊砂を Euler 平均流速で運ぶのは Reniers ら(2004)[^reniers04]・XBeach[^xbeach] と同じ。掃流砂の「τ*_max の量 × u_s の速さ」の組み合わせは独自(§8.4) |
| `wfsed_facsk`・`wfsed_facas`(&list_geomorph) | 0.1 | 岸向きの速度の歪度・非対称の係数 f_Sk・f_As | **校正量**: 既定は XBeach の facua[^xbeach]。式は van Thiel de Vries(2009)[^vtdv09]、S_k・A_s は Ruessink ら(2012)[^ruessink12] のパラメータ化(係数 p₂〜p₆ は XBeach の公開ソースの値で、論文の式 (9)・(10) の値とは違う。§8.3) |
| `f_wfsed_turb`(&list_geomorph) | 0 | 砕波の乱れによる攪拌 | **互換**: 既定 0(乱れなし = 乱れを入れる前と同じ結果)。1 は XBeach の `turb` = wave_averaged(Ruessink の波形での XBeach の既定[^xbeach])の形。係数 1.45 は van Thiel de Vries(2009)[^vtdv09] |
| `f_wfswash`(&list_geomorph) | 0 | 遡上域の輸送 | **方式**: 既定は遡上域の輸送なし。岸沖は Larson ら(2004)[^larson04] 式 (8)、沿岸は Larson & Wamsley(2007)[^lw07] 式 (4)、遡上高は Stockdon ら(2006)[^stockdon06] 式 (19) の振れ幅の部分。露出度、格子への当てはめ(4 近傍の面・沿岸の帯)、R に Stockdon らの振れ幅を使う組み合わせは独自(§9.3・§9.4) |
| `wfswash_kc`(&list_geomorph) | 1.6×10⁻³ | 岸沖の輸送係数 K_c | **校正量**: Larson ら(2004)の波崎海岸(細砂 0.18 mm)の 4 例の較正の平均(各例 1.0〜2.3×10⁻³。遡上域の海側端の輸送量との回帰では 3×10⁻³)。粒径と遡上の波どうしの干渉に依存する |
| `wfswash_kl`(&list_geomorph) | = K_c | 沿岸の輸送係数 K_l | **校正量**: Larson & Wamsley(2007)の仮定 K_l ≈ K_c(LSTF の実験で 10⁻³ が合う) |
| `wfswash_tanbe`(&list_geomorph) | (必須) | 前浜の平衡勾配 tanβ_e | **与件**: 利用者が与える(方針 §0 の「計算で使う物理量は直接与える」)。波崎の細砂では 0.035〜0.057(Larson ら 2004 の表 1) |
| `wfswash_phim`(&list_geomorph) | 30° | 動く粒子の摩擦角 φ_m | **文献値**: Larson ら(2004)の動く粒子の摩擦角 |

**既定値を見直すときの手がかり**

- 砕波の係数(`wf_gamma`・`wf_alpha`・`wf_gammax`)は XBeach の既定で、まず変えずに使います。砕波帯の
  位置や波高の減り方が観測と合わないときに調べる量です。急な海浜では先に `wf_break = 2` を試します。
- 方向分散 `wf_spread` は、地点の波浪観測(方向スペクトル)があればその方向分散を与えます。
- 浜の侵食と回復の向きと速さは `wfsed_facsk`・`wfsed_facas` に敏感です。断面の観測(侵食期の沖向きの
  移動・静穏期の回復)に合わせて校正します。
- 前浜の平衡勾配 `wfswash_tanbe` は現地の前浜の勾配の観測から与えます(粒径が大きいほど急)。係数
  `wfswash_kc` は細砂の現地観測の値なので、粒径が違えば感度を確かめてください。
- 砕波による水平混合の強さ `wf_break_visc` は、沿岸流の岸沖分布の観測があればそれに合わせます。

## 11. 検証ケース

| ケース | 内容 | 要点 |
|---|---|---|
| [test/wfshoal](../../test/wfshoal/README.md) | 勾配 1/80 の海浜断面 | 規則波の浅水変形と飽和砕波(線形理論と一致)、屈折(Snell の法則と方向ビンの 1 次収束)、不規則波の砕波(Baldock・Janssen & Battjes。Python で独立に書いた散逸式による離散解と一致、細かい刻みのエネルギー式との差 1%)、非定常の前線の到達と定常解、台帳の閉合、再開の継続のバイト一致、波浪場の有無で流れが同じこと、沖の波の時系列の補間 |
| [test/wfshadow](../../test/wfshadow/README.md) | 防波堤と斜めの壁の囲い | 独立に実装した掃引解との一致、斜めの壁の遮断、格子方向に揃った波の陰が厳密に鋭いこと |
| [test/wfcurrent](../../test/wfcurrent/README.md) | 流れへの作用 | セットアップの面ごとの離散の釣り合い・沖の set-down(Longuet-Higgins & Stewart)・砕波帯の勾配(Bowen ら)、一様水深の沿岸流と戻り流れの摩擦の閉じた形との一致、海浜の沿岸流の運動量の積分の釣り合い・ローラーの収支と岸側へのずれ、側方 Neumann の辺の岸沿いの一様性、90° 回した格子との一致、再開の継続のバイト一致。流れの波への作用を加えた双方向の連成の釣り合いと収支、砕波による水平混合(ν_w の式との一致・岸沿いの一様性・運動量の積分の釣り合い)と側方 Neumann の辺の拡散 |
| [test/wfdoppler](../../test/wfdoppler/README.md) | 流れによる波の変化 | 逆流・順流の上の作用量の流束の保存(独立に解いた分散関係)、逆流による阻止の位置と台帳、流れの作用の有無、非定常(流れの立ち上がりの間も作用量の台帳が閉じる)、河口の噴流が波の遡上を止めること、再開の継続のバイト一致 |
| [test/wfsed](../../test/wfsed/README.md) | 土砂への作用 | 攪拌による浮遊砂の平衡濃度と掃流砂の流砂量(独立に組み立てた Soulsby 1997 の式と一致)、海浜の沿岸漂砂の向き・岸沖分布・岸沿いの一様性・CERC(Komar & Inman 1970)と同じ桁、岸向きの速度 u_a(Ruessink ら 2012 の式と一致)、高波浪の侵食と低波浪の回復の向き、閉じた海盆の土砂の保存、砕波の乱れによる攪拌(k_b の式との一致・沿岸漂砂の増加)、再開の継続のバイト一致 |
| [test/wfswash](../../test/wfswash/README.md) | 遡上域の輸送 | 1 回の地形更新の量が Larson ら(2004)の式と倍精度で一致、45° の汀線で単位長さあたりの量が軸に沿う汀線と同じ、平衡勾配で不変、緩い前浜の積み上げ(バーム)と急な前浜の後退が平衡勾配へ向かって越えない、堆積が遡上の上限を越えない、斜め入射の沿岸の総量が Larson & Wamsley(2007)の式と一致、遡上の届かない崖の前では動かない、閉じた海盆の連成での土砂の保存、再開の継続のバイト一致 |
| [examples/delta](../../examples/delta/README.md) | 河川デルタ(wfsed) | 波浪場・過程の漂砂・遡上域の輸送・背景粘性を組んだ地形 1500 h の計算と、遡上域の輸送の有無の比較 |

いずれも MPI の np = 1・2・4 で逐次とビット一致します。

## 12. 参考にした他モデルと ENCflow 独自の部分

本機能の概念に新規性は主張していません。波浪場は、代表周期・方向分割の位相平均の作用量平衡という
既存の階層(HISWA・XBeach の定常モード・SnapWave)に乗せたもので、砕波・摩擦・ローラー・GLM・
波・流れの摩擦・攪拌・輸送速度の定式と既定値の多くは XBeach の定式に、遡上域の輸送は Larson らと
Stockdon らの経験式に従います。ENCflow 固有なのは、8 方向の ENC 格子へ載せるための離散化
(2 リンク分解の風上法・対角の遮断・外力の面への射影・側方 Neumann の鏡像)、分割数によらずビット
一致する解法の構成、ENCflow の既存の土砂の式との接続(掃流砂の輸送の形・乱れの入れ方)、遡上域の
経験式を格子に当てはめる規則、そして浅水流・土砂と同じ格子・同じ時間発展の中で動かし、無効時に
ゼロ追加となる組み込み方です。

### 12.1 参考にした他モデル・研究

| モデル・研究 | 本実装が参考にした点 | 違い |
|---|---|---|
| **HISWA**[^hiswa] | 周波数を分割しない方向ビンの作用量平衡で、流れのある浅海の波を求める階層(この系譜の出発点) | 本実装は代表周期 1 個(ω を固定)で、非定常にも使う |
| **XBeach の定常モード**[^xbeach] | 砕波(Baldock ら・Janssen & Battjes、H_b の Miche 型)・水深による上限・底面摩擦の式と係数、散逸のビンへの配分(E_m/E)、既定値(γ・α・γmax・f_w) | XBeach の surfbeat(波群・長周期波)と非静水圧モードに当たる機能は持たない |
| **XBeach の流れ・土砂の定式**[^xbeach] | ローラー(Nairn ら 1990 の放射応力の近似・β・既定の有効化)、深さ平均の GLM、波・流れの摩擦の速さ(1.16)、外力の立ち上げ(taper)、流れによる屈折の式と使う流速(wci)、砕波の渦動粘性(nuhfac)、砕波の乱れ(turb = wave_averaged)、Euler 平均流速による浮遊砂の輸送、岸向きの速度(facua と Ruessink ら 2012 の係数) | 波数は Eikonal 式でなく方向ビンごとに分散関係を直接解く(§7.1)。乱れは平衡濃度式でなく Soulsby の波のせん断の速度に入れる(§8.2)。土砂の量は ENCflow の既存の流砂量式・平衡濃度式を τ*_max で使う(§8.1・§8.4)。渦動粘性は背景の粘性と和にする(§6.4) |
| **SnapWave**[^snapwave] | 方向空間の屈折をセルごとの三重対角で陰的に解く構成、屈折の速さの上限 \|c_θ\| ≤ σ/4、既定値(最小水深 0.1 m・更新間隔 3600 s) | SnapWave は風上の 2 点からの距離重みの補間を 4 方向の掃引で解く(公開ソース)。本実装は保存形の 2 リンク分解(§3)を Jacobi 型の反復で解く(§4.3)。砕波の式は SnapWave の公開ソースの形(係数 0.28・H_b = γh)でなく XBeach の形(§5)。流れの作用(§7)を持つ |
| **SWAN**[^swan] | 作用量の平衡の形(周波数 1 個へ縮約)、方向分布 cos^s の形、流れによる屈折の速さの式 | 周波数の次元・風・非線形相互作用は持たない。方向空間の中心差分と風上の混合(CDD 型)と掃引解法は採らない(§4.1・§4.3) |
| D∞(Tarboton 1997)[^tarboton97] | 流向を 8 近傍の 2 セルに角度で按分する発想 | 地形の流向でなく、方向ビンの伝播速度の流束を 2 本の格子方向へ非負に分解する(§3) |
| Bretherton & Garrett(1968)[^bg68] | 作用量の保存と、流れの上の分散関係 | — |
| Kuik ら(1988)[^kuik88]、Fenton & McKee(1990)[^fm90]、van Leer(1974)[^vanleer74] | 方向分散の定義、分散関係の陽な近似、制限関数 | 近似は Newton 法の初期値に、制限関数は方向空間の遅延補正に使う(§2.2・§4.1) |
| Longuet-Higgins & Stewart(1962・1964)[^lhs64]、Bowen ら(1968)[^bowen68] | 放射応力、セットダウン・セットアップ | 方向ビンで積分し、セル中心で差分して面へ射影する(§6.1) |
| Svendsen(1984)[^svendsen84]、Reniers & Battjes(1997)[^rb97]、Nairn ら(1990)[^nairn90] | ローラーのエネルギー平衡・散逸・質量輸送・放射応力 | — |
| Andrews & McIntyre(1978)[^am78]、Walstra ら(2000)[^walstra00]、Ruessink ら(2001)[^ruessink01] | Lagrangian 平均流と深さ平均の GLM、波・流れの摩擦の速さ | — |
| Battjes(1975)[^battjes75] | 砕波の渦動粘性、表面の乱れ | 式の形は XBeach の実装による(原論文は未照合) |
| Soulsby(1997)[^soulsby97]、Swart(1974)[^swart74] | 波の摩擦係数と波・流れのせん断の合成 | — |
| Reniers ら(2004)[^reniers04] | 浮遊砂を Euler 平均流速で運ぶ | — |
| van Thiel de Vries(2009)[^vtdv09]、Ruessink ら(2012)[^ruessink12]、Roelvink & Stive(1989)[^rs89] | 岸向きの速度 u_a と歪度・非対称のパラメータ化、乱れの係数 1.45、乱れの底面への減衰 | 係数 p₂〜p₆ は XBeach の公開ソースの値で、論文の最適値とは違う(§8.3) |
| Larson ら(2004)[^larson04] | 遡上域の岸沖の輸送の式 (8)、K_c・φ_m の値 | 遡上高に Stockdon らの振れ幅を使う(§9.3) |
| Larson & Wamsley(2007)[^lw07] | 遡上域の沿岸の輸送の式 (4)、K_l ≈ K_c | 汀線の帯に置き、8 方向の面に流す(§9.4) |
| Stockdon ら(2006)[^stockdon06] | 遡上高の振れ幅の部分 R = 1.1 S/2 | setup は流れが解くので振れ幅だけを使い、露出度を掛ける(§9.3) |
| CERC(Komar & Inman 1970)[^ki70] | 沿岸漂砂量の桁の確認(検定) | モデルには入れない(§8.5) |
| 単一波系の WKB(ROMS/CROCO。Uchiyama ら 2010[^uchiyama10]) | 流れによる波数・周波数の変化を波数ベクトルで追う考え方(将来の併用の候補) | **不採用**: 砂州・島・河口の背後で波線が交差すると波数場が多価になり、方向分散と波向の時間変化を持てない |
| 渦力形式(McWilliams ら 2004[^mcwilliams04]、Uchiyama ら 2010) | 波と流れの相互作用の別の定式 | **不採用**: 深さ平均では GLM と同じ物理を表し、ENC の運動方程式の構造(面ごとの外力と摩擦)には GLM が素直に載る |
| スペクトルモデル(SWAN など) | — | **不採用**: 周波数 × 方向の数百〜千の未知量は、全プロセスを同じ格子で回す用途には重い。必要なら外部の結果を読む |
| 位相解像モデル(SWASH[^zijlema11]・FUNWAVE-TVD[^shi12]・XBeach の非静水圧モード) | — | **不採用**: 格子が波長の 1/20 程度・時間刻みが桁違いで、地形変化の時間尺度に向かない。長波の分散は[非静水圧補正](nonhydrostatic.md)が担う |
| 周波数も分割するエネルギー平衡と回折項(CMS-Wave。Mase 2001[^mase01]) | 回折の近似(将来の候補) | **不採用**(現時点): 本実装より上の階層。回折の近似は優先度が低い |
| ENC の有限体積 + リンク方向 MUSCL(浅水流・スカラー輸送と同じ形) | — | **不採用**: 陰の縁の幅の試験で格子方向に 2 リンク分解より劣り、斜めの向きでも費用に見合わない(§3) |

### 12.2 ENCflow 独自の理論・実装

| 独自の部分 | 内容 | 理由 | 確かめたこと |
|---|---|---|---|
| 2 リンク分解の風上法(§3) | 伝播速度を挟む 2 本の格子方向への非負の分解で、方向ビンを 8 方向の ENC 格子に載せる | 格子方向で横断の数値拡散がなく、保存・正値 | 陰の縁の幅の比較、test/wfshadow(独立の掃引解・格子方向の陰が鋭い)、test/wfshoal |
| 対角の遮断(§3) | 両脇がともに非波浪セルの対角は閉じる | 1 セル厚の斜めの堤を波がすり抜けない | test/wfshadow の菱形の囲い |
| 方向空間の解き方(§4.1) | 陰的 1 次風上 + van Leer の制限つき 2 次の遅延補正(独自の組み合わせ) | 屈折の遅れを減らし、負のエネルギーを出さない | test/wfshoal の refr(Snell の法則・1 次収束) |
| 1 つの核と 2 つのモード(§4.3) | Jacobi 型の更新を、局所の擬似時間刻みの準定常と物理時間の非定常で共用(独自の組み合わせ) | 分割数・スレッド数によらないビット一致 | 全検定の np = 1・2・4 のビット一致、test/wfshoal の unst |
| 境界の角・吸収セル(§4.4) | 角の仮想の送り手は 入射 > 側方 Neumann > 吸収。家屋空隙・サブグリッド河道のセルは吸収セル、海セルは計算域外 | 直線海岸の一様性を保ち、未対応の組み合わせを黙って計算しない | test/wfshoal(岸沿いの一様性) |
| 外力の面への射影(§6.1) | セル中心の外力を両セル平均で面へ射影し、両セルの平均水深で割る | 軸と対角の面が同じ釣り合いになり、偽の循環を作らない。流速の符号で外力が切り替わらない | test/wfcurrent(面ごとの離散の釣り合い・90° 回した格子との一致) |
| 側方 Neumann の辺(§6.6) | 鏡像セルで、境界面の運動方程式・移流の検査体積・拡散・土砂の流入を内部と同じ式で求める | 外に同じ海岸が続く扱いで、沿岸流が辺を通り抜け、流入を加速しない | test/wfcurrent・test/wfsed(岸沿いの一様性) |
| 渦動粘性の組み合わせ(§6.4) | 背景の粘性との和 | XBeach の組み合わせ方は未照合。既存の砕波の渦粘性と同じ扱い | test/wfcurrent の mix |
| ビンごとの分散関係(§7.1) | ω を固定し、方向ビンごとに流れの上の分散関係を直接解く(時間変化する流れでの ω の変化は入れない = 独自の簡略化) | 代表周期 1 個の作用量平衡と整合し、波数場を持たない | test/wfdoppler(独立に解いた分散関係・阻止の位置) |
| 格子規模の縞への対処(§7.3) | 流れ→波と波→流れの格子規模の正帰還の特定と、背景粘性による対処 | WKB の前提の外の格子規模の応答を止める | examples/delta での切り分け(developer.md §90.20) |
| 掃流砂の輸送の形(§8.4) | τ*_max の量を u_s の速さで運ぶ(独自の組み合わせ) | 既存の流砂量式に波をつなぎ、波がなければ既存の式に一致 | Soulsby(1997)の波・流れの掃流砂の式と同じ桁(test/wfsed の条件で 0.92 対 0.98) |
| 乱れの入れ方(§8.2) | 底面の乱れを Soulsby の波のせん断の速度に足す(独自の簡略化) | 既存の攪拌の経路をそのまま使う | test/wfsed の turb(k_b の式との一致) |
| 遡上高と露出度(§9.3) | Stockdon らの振れ幅に露出度 E を掛け、Larson らの式と組む(独自の組み合わせ) | setup は流れが解く。波の届きにくい汀線の遡上を小さくする | test/wfswash(式との一致) |
| 遡上域の格子への当てはめ(§9.4) | 汀線のセル、4 近傍の面の岸沖の流束、汀線の帯の沿岸の流束、遡上域の条件、乾いたセルへの堆積と遡上の上限 | 汀線の向きによらず単位長さあたりの量を保ち、崖の前で砂を運ばない | test/wfswash(diag・eq・mild・steep・obl・cliff・flow) |
| 組み込み(§1) | 浅水流・土砂と同じ格子・同じ時間発展、共有状態を介した結合、無効時のゼロ追加、地形時間(MORFAC)の時計の選択 | 統合モデルとして他のプロセスと同時に回す | 機能を使わない既存のケースの結果が変わらないこと(reference との比較) |

### 12.3 扱わない過程と拡張の検討

回折・反射・周波数の広がり・風による発達・非線形相互作用、時間変化する流れによる周波数の変化は
扱いません。拡張の候補(波数場の併用・回折の近似・風による発達・掃引解法)と判断は
docs/wavefield_plan.md §9 と developer.md §90.17 にあります。書誌と原典との照合の状況は
docs/wavefield_plan.md §11・§12 と developer.md §90 にあります。

## 参考文献

[^am78]: Andrews, D. G. & McIntyre, M. E. (1978) An exact theory of nonlinear waves on a Lagrangian-mean flow. J. Fluid Mech. 89, 609–646.
[^baldock98]: Baldock, T. E., Holmes, P., Bunker, S. & Van Weert, P. (1998) Cross-shore hydrodynamics within an unsaturated surf zone. Coastal Engineering 34, 173–196.
[^battjes75]: Battjes, J. A. (1975) Modeling of turbulence in the surf zone. Proc. Symposium on Modeling Techniques, ASCE, San Francisco, 1050–1061.(砕波の渦動粘性 ν = M h (D/ρ)^{1/3}。式の形は XBeach の nuhfac の実装による。原論文は未照合)
[^bg68]: Bretherton, F. P. & Garrett, C. J. R. (1968) Wavetrains in inhomogeneous moving media. Proc. R. Soc. Lond. A 302, 529–554.
[^bowen68]: Bowen, A. J., Inman, D. L. & Simmons, V. P. (1968) Wave 'set-down' and set-up. J. Geophys. Res. 73(8), 2569–2577.
[^eurotop]: EurOtop (2018) Manual on wave overtopping of sea defences and related structures, 2nd ed. Van der Meer, J. W., Allsop, N. W. H., Bruce, T., De Rouck, J., Kortenhaus, A., Pullen, T., Schüttrumpf, H., Troch, P. & Zanuttigh, B. www.overtopping-manual.com
[^fm90]: Fenton, J. D. & McKee, W. D. (1990) On calculating the lengths of water waves. Coastal Engineering 14, 499–513.
[^gt85]: Guza, R. T. & Thornton, E. B. (1985) Velocity moments in nearshore. J. Waterway, Port, Coastal, Ocean Eng. 111(2), 235–256.
[^hiswa]: Holthuijsen, L. H., Booij, N. & Herbers, T. H. C. (1989) A prediction model for stationary, short-crested waves in shallow water with ambient currents. Coastal Engineering 13, 23–54.
[^ki70]: Komar, P. D. & Inman, D. L. (1970) Longshore sand transport on beaches. J. Geophys. Res. 75(30), 5914–5927.
[^jb07]: Janssen, T. T. & Battjes, J. A. (2007) A note on wave energy dissipation over steep beaches. Coastal Engineering 54, 711–716. 砕波波高 H_b の形は Battjes, J. A. & Janssen, J. P. F. M. (1978) Energy loss and set-up due to breaking of random waves. Proc. 16th ICCE, 569–587 の Miche 型(XBeach の定式と同じ)。
[^kuik88]: Kuik, A. J., van Vledder, G. Ph. & Holthuijsen, L. H. (1988) A method for the routine analysis of pitch-and-roll buoy wave data. J. Phys. Oceanogr. 18, 1020–1034.
[^larson04]: Larson, M., Kubota, S. & Erikson, L. (2004) Swash-zone sediment transport and foreshore evolution: field experiments and mathematical modeling. Marine Geology 212, 61–79. doi:10.1016/j.margeo.2004.08.004(式 (5)・(8)。K_c の較正は 6 章・8 章)
[^lw07]: Larson, M. & Wamsley, T. V. (2007) A formula for longshore sediment transport in the swash. Proc. Coastal Sediments '07, ASCE.(式 (3)・(4)・(6)・(7))
[^lhs64]: Longuet-Higgins, M. S. & Stewart, R. W. (1964) Radiation stresses in water waves; a physical discussion, with applications. Deep-Sea Research 11, 529–562. 沖の set-down は Longuet-Higgins, M. S. & Stewart, R. W. (1962) Radiation stress and mass transport in gravity waves, with application to 'surf beats'. J. Fluid Mech. 13, 481–504。
[^mase01]: Mase, H. (2001) Multi-directional random wave transformation model based on energy balance equation. Coastal Engineering Journal 43(4), 317–337.
[^mcwilliams04]: McWilliams, J. C., Restrepo, J. M. & Lane, E. M. (2004) An asymptotic theory for the interaction of waves and currents in coastal waters. J. Fluid Mech. 511, 135–178.
[^nairn90]: Nairn, R. B., Roelvink, J. A. & Southgate, H. N. (1990) Transition zone width and implications for modelling surfzone hydrodynamics. Proc. 22nd ICCE, 68–81.
[^rb97]: Reniers, A. J. H. M. & Battjes, J. A. (1997) A laboratory study of longshore currents over barred and non-barred beaches. Coastal Engineering 30, 1–22.
[^reniers04]: Reniers, A. J. H. M., Roelvink, J. A. & Thornton, E. B. (2004) Morphodynamic modeling of an embayed beach under wave group forcing. J. Geophys. Res. 109, C01030.
[^rs89]: Roelvink, J. A. & Stive, M. J. F. (1989) Bar-generating cross-shore flow mechanisms on a beach. J. Geophys. Res. 94(C4), 4785–4800.(砕波の乱れの底面への指数の減衰。式の形は XBeach の turb の実装による)
[^ruessink01]: Ruessink, B. G., Miles, J. R., Feddersen, F., Guza, R. T. & Elgar, S. (2001) Modeling the alongshore current on barred beaches. J. Geophys. Res. 106(C10), 22451–22463.
[^ruessink12]: Ruessink, B. G., Ramaekers, G. & van Rijn, L. C. (2012) On the parameterization of the free-stream non-linear wave orbital motion in nearshore morphodynamic models. Coastal Engineering 65, 56–63.(式 (6)〜(10)。係数の最適値は p. 58)
[^shi12]: Shi, F., Kirby, J. T., Harris, J. C., Geiman, J. D. & Grilli, S. T. (2012) A high-order adaptive time-stepping TVD solver for Boussinesq modeling of breaking waves and coastal inundation. Ocean Modelling 43–44, 36–51.
[^stockdon06]: Stockdon, H. F., Holman, R. A., Howd, P. A. & Sallenger, A. H. Jr. (2006) Empirical parameterization of setup, swash, and runup. Coastal Engineering 53, 573–588. doi:10.1016/j.coastaleng.2005.12.005(式 (9)〜(12)・(19))
[^snapwave]: Roelvink, D., van Ormondt, M., Reyns, J. & van der Lugt, M. (2025) SnapWave: fast, implicit wave transformation from offshore to nearshore. Geosci. Model Dev. 18, 9469–9495. doi:10.5194/gmd-18-9469-2025(既定値と解法は公開ソースによる)
[^soulsby97]: Soulsby, R. L. (1997) Dynamics of Marine Sands: A Manual for Practical Applications. Thomas Telford, London. 波の摩擦係数(式 62a)、波・流れのせん断の合成(式 69・70)。
[^svendsen84]: Svendsen, I. A. (1984) Wave heights and set-up in a surf zone. Coastal Engineering 8, 303–329.
[^swan]: Booij, N., Ris, R. C. & Holthuijsen, L. H. (1999) A third-generation wave model for coastal regions: 1. Model description and validation. J. Geophys. Res. 104(C4), 7649–7666.
[^swart74]: Swart, D. H. (1974) Offshore sediment transport and equilibrium beach profiles. Delft Hydraulics Laboratory, Publication No. 131.
[^tarboton97]: Tarboton, D. G. (1997) A new method for the determination of flow directions and upslope areas in grid digital elevation models. Water Resour. Res. 33(2), 309–319.
[^uchiyama10]: Uchiyama, Y., McWilliams, J. C. & Shchepetkin, A. F. (2010) Wave–current interaction in an oceanic circulation model with a vortex-force formalism: Application to the surf zone. Ocean Modelling 34, 16–35. doi:10.1016/j.ocemod.2010.04.002
[^vanleer74]: van Leer, B. (1974) Towards the ultimate conservative difference scheme. II. Monotonicity and conservation combined in a second-order scheme. J. Comput. Phys. 14, 361–370.
[^vtdv09]: van Thiel de Vries, J. S. M. (2009) Dune erosion during storm surges. PhD thesis, Delft University of Technology.
[^walstra00]: Walstra, D. J. R., Roelvink, J. A. & Groeneweg, J. (2000) Calculation of wave-driven currents in a 3D mean flow model. Proc. 27th ICCE, 1050–1063.
[^xbeach]: Roelvink, D., Reniers, A., van Dongeren, A., van Thiel de Vries, J., McCall, R. & Lescinski, J. (2009) Modelling storm impacts on beaches, dunes and barrier islands. Coastal Engineering 56, 1133–1152. 定式と既定値は XBeach マニュアル(xbeach.readthedocs.io)と公開ソース(params.F90)による。
[^zijlema11]: Zijlema, M., Stelling, G. and Smit, P. (2011) SWASH: An operational public domain code for simulating wave fields and rapidly varied flows in coastal waters. Coastal Engineering 58, 992–1012.
