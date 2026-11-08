# 土石流・斜面崩壊・動く底層の解説(土砂・地形変化の補足)

[土砂・地形変化の章へ](geomorph.md) | [ユーザーガイド目次へ](../users_guide.md)

[土砂・地形変化の章](geomorph.md)の土石流(`f_debris`)、瞬時流動化
(`fn_dbinit`)、斜面安定判定(`f_slide`)、動く底層(`f_bedslide`)について、
方程式・抵抗則・侵食堆積則・発生条件の式と既定値の根拠、参考にした
他モデルをまとめます。掃流砂・浮遊砂・斜面侵食・長期地形過程は
[土砂輸送と斜面・長期地形過程の解説](sediment.md)にあります。
実装は `src/m_geomorph_debris.f90`、`src/m_geomorph_bedslide.f90` と、
抵抗則を運動方程式に合成する `src/m_swflow_enc.f90`(`calc_kth_flux`)です。
設計の経緯と文献照合の記録は docs/debris_plan.md、
docs/landslide_tsunami_plan.md にあります。Voellmy の定常速度と無限長斜面の安全率のグラフ、動く底層の
説明図は章の各節にあり、このページには単層混合体と交換、抵抗則の振る舞いの図を置いています。

## 1. 単層混合体モデル

土石流は地表水 $`h`$ と土砂柱状量 $`h_s`$(固体体積の厚さ換算)の
**単層混合体**として扱い、固体と水は同じ速度で動くとします。

```math
h_t = h + h_s,
\qquad
C = \frac{h_s}{h + h_s},
\qquad
C_* = 1 - \lambda,
\qquad
\frac{\rho_m}{\rho} = 1 + sC
```

$`h_t`$ が流動深、$`C`$ が混合体積濃度、$`C_*`$ が堆積層の固体濃度
(河床の空隙率 $`\lambda`$ = `fluv_porosity` から導く)、$`s`$ が土粒子の
水中比重(`fluv_sgrav`)です。運動方程式([ENC 格子の解説](encgrid.md) §5)
では、水面を $`z + h + h_s`$、摩擦に使う水深を $`h_t`$ に置き換え、
抵抗則(§2)で摩擦項を置換または合成します。土砂 $`h_s`$ の移流は
浮遊砂と同じステップ内輸送で、河床との交換(§3)が地形更新の時刻に
入ります。この水準は Kanako[^nakatani08]・Morpho2DH[^morpho2dh]と同じ
「SWE + 粒状体の抵抗則 + 侵食堆積則」の構成で、別層の土砂ソルバは
作りません(developer.md §0 の範囲)。

![単層混合体と河床との交換: 1 つのセルの状態・交換の簿記・平衡濃度へ向かう速さ](../figs/massflow_mixture.png)

図の (a) は 1 つのセルの状態で、水 $`h`$ と固体の厚さ換算 $`h_s`$ が同じ速度で動き、摩擦の深さは $`h_t`$、
水面は $`z + h + h_s`$ です。(b) は地形更新の時刻に行う河床との交換(§3)で、$`\Delta z = -\Delta h_s/C_*`$ を
$`z`$ と $`s_d`$ に同じだけ当てるので、基岩面は動きません。間隙水の連行(`f_dbwet`)と停止(`f_dbstop`)も
ここで働きます。(c) は §3 の 2 つの侵食・堆積則について、1 m 進む間の河床の変化を濃度に対して描いたもので、
どちらも同じ平衡濃度 $`C_\infty`$ に向かいます。f_dbed = 1 の速さは $`\delta_e`$・$`\delta_d`$ で決まり
(既定では堆積が侵食より速い)、f_dbed = 2 は係数を持たず、清水に近い流れは強く削ります。曲線は式を既定の
係数で評価したもので、計算結果ではありません。

## 2. 抵抗則(f_dbres)

抵抗はすべて減速度の形で半陰的に合成します(速度に依らない降伏項は
$`a_y/|\mathbf{V}|`$ として分母に入れ、低速かつ駆動力の大きさが $`a_y`$ 以下なら
明示的に静止させます。動き出しと停止が同じ式で表されます。下の「静止と動き出し」)。
$`g_e`$ は急勾配の有効重力 $`g\cos^2\theta`$([ENC 格子の解説](encgrid.md) §5)です。
表の式は水平の流速 $`|\mathbf{V}|`$・鉛直の深さ $`h_t`$ の形で、`f_gravity_correction` = 0・1 ではこのまま
使います。既定の 2 では、抵抗を斜面に沿う速さ $`|\mathbf{V}_s| = r|\mathbf{V}|`$ と地盤に直角な厚さ
$`h_t\cos\theta`$ で評価し直す倍率を掛けます: 降伏は $`1/(r\cos\theta)`$(最急勾配の向きの流れでは 1)、
速度の 2 乗の項(Voellmy の乱流項・江頭の層流則・高橋・中川の石礫型)は $`r/\cos^3\theta`$、掃流状集合流動は
$`r/\cos^2\theta`$ です。Voellmy の等流は RAMMS と同じ $`V_s^2 = \xi\,h_t\cos\theta\,(\sin\theta - \mu\cos\theta)`$
になり、RAMMS で校正した μ・ξ をそのまま使えます([急勾配の重力補正](steep_slope.md) §2.3、developer.md §101、
検証は [test/dbslope](../../test/dbslope/README.md))。

| f_dbres | 名称 | 降伏減速度 $`a_y`$ と速度依存項 | 追加パラメータ |
|---:|---|---|---|
| 0 | Manning のみ | — | — |
| 1 | クーロン + Manning | $`a_y = g_e\tan\phi\,\dfrac{sC}{1+sC}`$(水中固体重量の底面摩擦。Manning 則はそのまま) | db_phi |
| 2 | 江頭構成則[^egashira93] | $`a_y = g_e\tan\phi\,\dfrac{sC}{1+sC}\left(\dfrac{C}{C_*}\right)^{1/5}`$、速度項 $`\dfrac{f_b\,\lvert\mathbf{V}\rvert^2}{(1+sC)\,h_t}`$ | db_d50、db_erest |
| 3 | 高橋・中川 石礫型[^tn91] | $`a_y = g_e\cdot 0.45\,\dfrac{sC}{1+sC}`$、ダイラタント項 $`4\left(\dfrac{1-C}{C}\right)^{2/3}\left(\dfrac{d_L}{h_t}\right)^2\dfrac{\lvert\mathbf{V}\rvert^2}{(1+sC)h_t}`$ | db_d50 |
| 4 | Voellmy[^voellmy55] | $`a_y = g_e\,\mu + \dfrac{g_e\,\lvert\mathbf{V}\rvert^2}{\xi\,h_t}`$ | db_mu、db_xi |
| 5 | 一定停止応力 | $`a_y = \dfrac{\tau_y}{\rho_m h_t}`$ + Manning | db_tauy |

江頭構成則の抵抗係数は

```math
f_b = \frac{25}{4}\left\{k_f\frac{(1-C)^{5/3}}{C^{2/3}} + k_d\frac{\sigma}{\rho}(1-e^2)\,C^{1/3}\right\}\left(\frac{h_t}{d}\right)^{-2},
\qquad k_f = 0.16,\quad k_d = 0.0828
```

($`e`$ = 粒子の反発係数 `db_erest`、$`d`$ = `db_d50`)で、層流抵抗が
$`(h_t/d)^2`$ に反比例するため **粒径が mm 以下では抵抗が消えて発散**
します(細粒のスラリーには 4 か 1 を使う)。高橋・中川則は濃度
$`C \le 0.4C_*`$ で掃流状集合流動 $`(\rho_T/0.49)(d_L/h_t)|\mathbf{V}|^2`$ に、
$`C < c_{\min}`$(`db_cmin`、既定 2%)または $`h_t/d \ge 30`$ で
Manning 則に切り替わります(原著の泥流域の規定)。2・3・4・5 とも
$`C < c_{\min}`$ の希薄側は Manning 則に退化し、下流の清水域に降伏を
掛けません(数値的な閉じ)。

Voellmy 則は雪崩のために作られた抵抗則で、雪崩実務モデル
RAMMS[^christen10]、火山流動の Titan2D[^pitman03]・VolcFlow[^kelfoun05]が
同じ形(μ-ξ)を使います。駆動も抵抗も加速度形で密度が相殺するため、
雪・岩屑・火砕物に同じ式が使えます。既定 μ = 0.2、ξ = 1000 m/s² は
RAMMS の雪崩の慣用域(0.15〜0.3 / 1000〜3000)の中庸で、岩屑なだれは
μ 0.05〜0.15・ξ 200〜500 と小さめ、一定停止応力の既定 10 kPa は
VolcFlow 系の火砕流適用例 5〜50 kPa の下寄りです(型ごとの値は
[章末の推奨値](geomorph.md#パターン別の推奨値))。

**静止と動き出し。** 低速のエッジ(両側のセルの速さの平均が `db_vstop` 未満)では、
駆動の大きさを $`a_y`$ と比べ、$`a_y`$ 以下なら静止させます。駆動の大きさは、エッジの
法線方向の駆動(移流と重力)と、流動面の勾配(両側のセルの平均)をエッジの接線方向へ
射影した成分を合わせたものなので、斜面が格子に斜めでも、動き出す勾配は $`a_y/g_e`$ の
ままです(既定の 2 の降伏の倍率は駆動の向きで決め、一様な斜面では 1)。検証は [test/dbonset](../../test/dbonset/README.md)(一様な斜面で、閾値と滑りの
速さ・向きが、斜面の向き 0°・22.5°・45° と 8・4 近傍によらず、剛体の滑りの解析解に 0.4%
以内で一致)。降伏項を半陰的に入れるため、静止からの動き出しは時間刻みに比例して遅れます
(勾配が降伏の 1.1 倍の斜面の 2 秒後の速さが、dt = 0.01 s で解析解の 0.8 倍、0.002 s で
0.96 倍)。2026-11-04 より前は法線方向の駆動だけで比べていたため、斜面に斜めのエッジが
止められて、動き出しが遅れるか起きず(勾配が降伏の 1.3 倍でも動かない組があった)、
その程度が斜面の向きと近傍の数で変わりました(developer.md §28.16)。

**曲率項(f_dbcurv)。** 地形の曲率による遠心加速度を垂直応力に加え、
降伏項に倍率を掛けます。

```math
a_y \leftarrow a_y\,\max\!\left(0,\ 1 + \frac{a_c}{g_n}\right),
\qquad
a_c = \frac{\mathbf{u}^{\mathsf T}\mathbf{H}\mathbf{u}}{\sqrt{1 + |\nabla z|^2}},
\qquad g_n = \sqrt{g\,g_e}
```

$`\mathbf{H}`$ は $`z`$ の Hessian(3×3 中心差分)で、$`a_c`$ は地表面の
流向法線曲率と表面速度の積です。凹地形で減速、凸地形で摩擦低下、
地面から浮く条件では摩擦ゼロです。RAMMS に Fischer らが入れた
曲率項[^fischer12]と同じ扱いで、RAMMS で校正された μ・ξ を使う比較では
有効にします。検証: [test/curvature](../../test/curvature/README.md)
(定常 1 次元常微分方程式との比較。円弧上の厚化 on − off が ODE の 1.03 倍)。

![混合体の抵抗則の振る舞い: 止まる勾配と濃度・粒径と定常速度・曲率項](../figs/massflow_resist.png)

図の (a) は表の降伏減速度から求めた、流れが止まる(静止した混合体が動き出さない)勾配
$`\tan\theta_y = a_y/g_e`$ を濃度に対して描いたものです。則 1〜3 は濃度とともに上がるので希薄な流れほど
緩い勾配でも流れ、則 4 は濃度によらず μ、則 5 は流動深で決まります。則 1 の線は §3 の江頭・芦田の平衡勾配
$`\theta_e`$ と同じ式です。(b) は勾配 20° の等流の速さ(test/dbslope と同じ釣り合い)を粒径に対して描いたもので、
江頭構成則は粒径が小さいほど抵抗が消えて速度が発散し、高橋・中川則は $`h_t/d \ge 30`$ で Manning 則に
切り替わります。(c) は曲率項の倍率です。曲線は式を説明用の値で評価したもので、計算結果ではありません。

## 3. 侵食・堆積則(f_dbed)

河床との交換は固体柱状量の増分 $`\Delta h_s`$ とし、
$`\Delta z = -\Delta h_s/C_*`$ を $`z`$・$`s_d`$ に共動適用します。可動層
(侵食 $`\le s_d`$)と浮遊量(堆積 $`\le h_s`$)でクランプし、乾いたセルは
全量を河床に戻します。可動層を剥がした後の岩盤は、この交換では削りません。岩盤の侵食は
`f_rockinc` の土石流の項(`rock_kdb`。[地形変化の章](geomorph.md#土石流による岩盤侵食rock_kdb))で
扱います。

![平衡濃度と流砂量式](../figs/sediment_laws.png)

図 (b) が本節の平衡濃度 $`C_\infty(\tan\theta)`$(φ = 35°、s = 1.65、C* = 0.6)、
図 (a) は[土砂輸送の解説](sediment.md) §3 の流砂量式です。

**f_dbed = 1: 平衡濃度への緩和(高橋型)。** 勾配 $`\theta`$(地形の最急
勾配。下の「最急勾配」)の平衡濃度に向かって、速度に比例する率で侵食・堆積します
[^takahashi07]。

```math
C_\infty = \frac{\tan\theta}{s(\tan\phi - \tan\theta)}\ (\tan\theta > 0.138),
\quad
6.7\,C_\infty^{\,2}\ (0.03 < \tan\theta \le 0.138),
\quad
0\ (\tan\theta \le 0.03),
\qquad C_\infty \le 0.9\,C_*
```

```math
\Delta h_s = C_*\,i\,\Delta t,
\qquad
i = \delta_e\,\frac{C_\infty - C}{C_* - C_\infty}\,|\mathbf{V}|\ (C < C_\infty),
\qquad
i = \delta_d\,\frac{C_\infty - C}{C_*}\,|\mathbf{V}|\ (C > C_\infty)
```

石礫型の $`C_\infty`$ は力の釣り合いからの導出式で、未成熟土石流の
係数 6.7 と勾配の閾値 0.138・0.03、上限 $`0.9C_*`$ は高橋理論の慣用値
(原典照合は debris_plan.md §1 の残作業)。$`\delta_e`$(`db_delte`、既定
0.0007)は Takahashi の一般値、$`\delta_d`$(`db_deltd`、既定 0.05)は
Kanako 系の慣用値で、どちらも**到達距離の校正係数**です。
[test/debris](../../test/debris/README.md) の構成 7 が、斜面等流の濃度が 4 つの領域の
$`C_\infty`$ に収束することを、自由流出の辺の行まで含めて検定しています。

**最急勾配。** f_dbed = 1 の $`C_\infty`$、f_dbed = 2・3 で速さ 0 のセルの停止の判定に使う
$`C_\infty`$、斜面安定判定(f_slide)の $`\theta`$ は、地形(時間刻みの頭の $`z`$)の最急勾配で、
流向によらず速さ 0 でも決まります。自セルと、軸方向の近傍 1 つ・それに隣り合う斜めの近傍 1 つで
作る 8 つの三角形の面ごとに、面内の下り向きの最大勾配を求め、その最大をとります
(D∞[^tarboton97])。平面では最急勾配の向きによらず厳密です(2026-11-04 の修正。それまでの
8 方向の勾配の最大は、最急勾配の向きが 8 方向の間にあると最大で cos 22.5° = 0.92 倍に小さく出て、
安全率が 8 % 大きく、$`\tan\theta`$ = 0.3 の $`C_\infty`$ が 13 % 小さく出ていました。
developer.md §92。[test/dbonset](../../test/dbonset/README.md) が 0°・22.5°・45° の斜面の安全率で
検定)。曲がった斜面や、谷底と谷壁の境のような折れでは面ごとの平面の近似で、格子より細かい
地形は表しません。開いた辺(自由流出・長波放射・区間流入など)の外の近傍の標高は、辺の法線方向に
内側の 2 セルから線形外挿して補うので、辺の行でも内部と同じ勾配になります(2026-10-30 の
修正。それまでは外の近傍を除いたため辺の行で勾配が 0 になり、$`C_\infty = 0`$ として
人工的な堆積ができていました。developer.md §28.15)。不透過の辺・領域外・海の近傍は除きます
(面の片方の近傍だけが除かれるときは、残る近傍への勾配を使います)。

**f_dbed = 2: 江頭・芦田。** 侵食と堆積が 1 本の式で連続します
(Morpho2DH の式(5)–(7)[^morpho2dh])。追加パラメータはありません。

```math
\frac{E}{|\mathbf{V}|} = C_*\tan(\theta - \theta_e),
\qquad
\tan\theta_e = \frac{sC}{sC + 1}\tan\phi
```

$`\theta`$ は流向の河床勾配で、$`\theta_e`$ は濃度 $`C`$ の平衡勾配です
(その逆関数が石礫型の $`C_\infty`$ と一致します。f_dbed = 1 と 2 の交換の向きと速さの比較は §1 の図)。$`\theta`$ は各セルで、流向の下流側の
近傍との片側差分で求めます(中央差分は 2 セル周期の凹凸を見ないため。developer.md §89.24)。

**f_dbed = 3: 高橋・中川(1991)。** 単一粒径・飽和床の形で、侵食は
$`\delta_e\,\dfrac{C_\infty - C}{C_* - C_\infty}\,\dfrac{q_T}{d_L}`$、堆積は
慣性係数つきの $`\delta_d\left(1 - \dfrac{|\mathbf{V}|}{p\,v_c}\right)^4\dfrac{C_\infty - C}{C_*}\dfrac{q_T}{d_L}`$
($`q_T = |\mathbf{V}| h_t`$、$`p = 1/3`$、限界速度 $`v_c`$ は原著式(15))です[^tn91]。
流速が $`p\,v_c`$ を超える間は堆積せず慣性で走り、遷緩点で扇状に堆積します。
`db_d50`($`d_L`$)が必須です。

**f_dbed = 4: 速度比例連行。** $`E = \delta_e|\mathbf{V}|`$(連行のみ。堆積は
`f_dbstop` が担う)。雪崩・岩屑なだれが走路の雪や崩積土を取り込んで
成長する過程の簡易則で、連行可能な層は土層厚 $`s_d`$ で与えます。
$`C \ge c_{\min}`$ の密な流動体だけが連行します(希薄な裾の暴走防止)。
土石流の実務で広く使われる Hungr の経験的な連行則[^hungr95]は $`E = E_r\,h\,|\mathbf{V}|`$
(DAN3D など。$`E_r`$ は 1 m 進むごとの体積の増加率で、連行域に入る体積 $`V_0`$ と出る体積
$`V_f`$、連行域の長さ $`L`$ から $`E_r = \ln(V_f/V_0)/L`$ と見積もる[^qiao23])で、流動深の
因子を持ちます。f_dbed = 4 は侵食深が流動深によらず走行距離に比例するのに対し、Hungr の則では
流動深に比例し、体積が走行距離に対して指数的に増えます。f_dbed = 4 で近い連行量を与えるなら
$`\delta_e \approx E_r \times`$(代表の流動深)が目安です。
**f_dbed = 0** は交換なし(等価流体)です。

**停止(f_dbstop = 1)。** $`|\mathbf{V}| < v_{stop}`$ かつ $`C > C_\infty`$ の
セルで、超過濃度分を率 $`w_{stop}`$(m/s、河床深さ換算)で河床に固定
します。停止した土砂は $`z`$ に残り天然ダムの地形になります(数値的な
閉包で文献式ではありません)。

**間隙水の連行(f_dbwet = 1)。** 侵食で $`\Delta z < 0`$ のとき
$`h \mathrel{+}= \lambda\,s_b|\Delta z|`$、堆積で $`h \mathrel{-}= \lambda\,s_b\Delta z`$
($`s_b`$ = `db_satbed`、堆積層の飽和度)。高橋・中川の全容積連続式の
源泉項[^tn91]に相当し、侵食卓越の渓床で正味の増水(bulking)を与える
一次効果です。地下水計算とは排他です。

**地下水計算と併用する間隙水(f_dbwet = 2)。** 地下水計算(`fn_gwflow`)では
河床の間隙水は地下貯留 $`h_g`$(容量 $`s_d\,s_y`$)として扱われます。
`f_dbwet = 2` は河床の変化に合わせて地表水と地下貯留の間で水を移します。堆積
($`\Delta z > 0`$)では増えた容量をその場の地表水で直ちに満たし
($`\Delta h = \min(s_y\,\Delta z,\ s_d s_y - h_g,\ h)`$ を $`h`$ から $`h_g`$ へ。
流れの下に積もった土砂は飽和する)、侵食($`\Delta z < 0`$)では削られた層の
間隙水 $`\min(s_y|\Delta z|,\ h_g)`$ を $`h_g`$ から $`h`$ へ戻します(地下貯留は
上から満たされるので、削られるのは濡れた上部から)。どちらも独自の簡略化で、
水の総量は保存され、堆積と侵食が入れ替わっても往復で水が偏りません。
`f_dbwet = 0` のまま地下水計算と併用すると、堆積物の間隙は空のまま地形が上がるので、
水たまりの中の堆積はその間隙の分だけ水を押し出します。

**今後の課題(実装予定): Hungr の連行則。** 上の f_dbed = 4 の段落で触れた Hungr の
経験的な連行則[^hungr95] $`E = E_r\,h_t\,|\mathbf{V}|`$ を、既定を変えずに f_dbed の選択肢として
足す予定です。

- **効果**: DAN3D など欧州・北米の実務で使われるモデルと同じ形になり、既往の校正値
  (Cancia 2015 の $`E_r \approx 0.001`$ /m など[^qiao23])をそのまま使えます。連行率 $`E_r`$ は
  連行域に入る体積と出る体積、連行域の長さから $`E_r = \ln(V_f/V_0)/L`$ と見積もれるので、
  事前・事後の地形測量や堆積量の調査で校正できます。厚い流れほど深く削り、流れの体積が
  走行距離に対して指数的に増える形です(f_dbed = 4 は侵食深が流動深によらないので、体積の
  増え方は流れが覆う面積で決まります)。追加するパラメータは $`E_r`$(1/m)の 1 個です(無次元の
  $`\delta_e`$ とは単位が違うので共用しません)。
- **実装で備えること**: 連行だけで堆積は `f_dbstop` が担う、連行できる層は土層厚 $`s_d`$
  (連行域は $`s_d`$ の分布で与える)、$`C \ge c_{\min}`$ の密な流動体だけが連行する、という
  扱いは f_dbed = 4 と同じにします。流動深には混合流動深 $`h_t = h + h_s`$ を使います。Hungr の
  定義では取り込んだ土砂が間隙水ごと(かさ体積で)流れに加わるので、体積の増え方をそれに
  合わせるには間隙水の連行(`f_dbwet = 1`、飽和度 1)と組みます。検定ケースは、一様な斜面を
  一定の速さで進む流れの体積が走行距離 $`x`$ に対して $`V_0\,e^{E_r x}`$ で増えること(固体の
  台帳の閉合と合わせて)です。
- **時期**: 欧州の実務のモデルとの比較や、連行の大きい土石流の実事例(Cancia 2015 など。
  地形データの入手が前提)を扱う段で入れます(developer.md §28.8)。

## 4. 発生条件

**瞬時流動化(fn_dbinit)。** 崩壊深 $`D`$ の分布を与え、`db_reltime` に

```math
h_s \mathrel{+}= (1-\lambda)D,\qquad z \mathrel{-}= D,\qquad s_d \mathrel{-}= D,\qquad
h \mathrel{+}= \lambda\,r_{sat}\,D
```

と転換します($`r_{sat}`$ = `db_relsat`。地下水計算が有効ならその水を
使います)。固体の台帳は構造的に閉じます。

**斜面安定判定(f_slide)。** 無限長斜面の安全率を毎更新評価し、
$`F_s < 1`$ のセルの土層を流動化します(`f_slide = 2` は判定のみ)。

```math
F_s = \frac{c' + (\gamma_t s_d - \gamma_w h_w)\cos^2\theta\,\tan\phi_s}{\gamma_t s_d\sin\theta\cos\theta},
\qquad
h_w = \min\!\left(\frac{h_g}{s_y},\ s_d\right)
```

有効応力と斜面平行浸透の古典的な式で、$`\theta`$ は地形の最急勾配(上の「最急勾配」)、
地下水位 $`h_w`$ は地下水計算の飽和厚 $`h_g`$ から取ります(降雨 → 地下水位上昇 → 崩壊 →
土石流が 1 つの時間発展でつながる)。セル独立(側方支持なし)・浅層限定の近似は
SHALSTAB[^montgomery94]などの分布型安定解析と同じ水準です。既定
$`\phi_s`$ = 30°、$`\gamma_t`$ = 18 kN/m³ は表層崩壊の安定解析の慣用値、
$`c'`$ = 0 は保守側です。

## 5. 動く底層(f_bedslide)

崩壊土塊を地形 $`z`$ と土層 $`s_d`$ の**内数**として動く底層 $`h_b`$ で表し、
慣性のない Voellmy 流として陸上から水中まで走らせます。底層が動くと
$`z`$ が上下し、水深 $`h`$ を保つので水面 $`z + h`$ が変位します
(**移動海底方式**の津波源[^tinti06][^harbitz06])。水域は海域マスク
(fn_sw)を使わない「解く海」(通常セル+初期水位 f_htype=2、辺は長波放射)で
表します。海域マスクの海セルには底層は入らず、海セルとの間のエッジを
通過しません。

```math
\Phi = z + r\,h,\quad r = \frac{\rho_w}{\rho_s},
\qquad
b = 1 - r\,w,\quad w = \min\!\left(1, \frac{h}{h_b}\right),
\qquad
s_y = S_c - \mu\,b,
\qquad
V = \sqrt{\xi\,h_b\,s_y}\ (s_y > 0)
```

$`\Phi`$ は駆動水頭(乾燥で $`z`$、平らな水面の下では勾配が $`(1-r)\nabla z`$)、
$`S_c`$ はその 8 近傍最急降下勾配、$`b`$ は浸水率 $`w`$ による浮力の係数
(浮力で駆動と摩擦が同時に減る)です。速度は慣性なしの Voellmy 等流解
(§2 の則 4 と同じ $`\tan`$ 形)で、$`0 < s_y < \varepsilon_S`$(`bs_eps_s`)は
線形化、$`s_y \le 0`$ は停止です。流量はエッジへ

```math
q_k = h_b\,V\,\frac{\Delta\Phi_k/\Delta s_k}{S_c}\,L_k
```

と配分します(ENC 本体の「射影速度 × 通過幅」と同じ形。`bs_diagratio`
= 0 で 4 近傍)。速度をセルの勾配で一度だけ決めるので、斜めエッジの
勾配低下が降伏に効く歪みを避けられます。底層は水の時間刻みの中で
安定条件(`bs_cfl`)に従うサブサイクルで進み、$`V < v_{stop}`$ が
`bs_tstop` 秒続いたセルの $`h_b`$ を 0 にして地形に固定します(質量は
既に $`z`$ にあるので不可逆)。

**混合体からの引き渡し(bs_hplunge)。** 陸上を土石流モデルで流下した
$`h_s`$ を、滞水深 $`h \ge`$ `bs_hplunge` のセルでかさ体積
$`h_s/(1-\lambda)`$ として底層に移します(運動量は失われる)。
`f_bsvplunge = 1` は混合体の速度が底層の終端速度以下に落ちてから
渡す条件、`f_bsplunge = 1` は静水時の水深で判定する条件です。

**既定値。** $`\rho_s`$ = 2000 kg/m³(飽和土塊・岩屑の代表値。$`r = 0.5`$)、
μ = 0.15、ξ = 500 m/s²(慣性なし底層の校正値。
[examples/landslide_tsunami](../../examples/landslide_tsunami/) と
[test/bedslide](../../test/bedslide/README.md)の全構成が使う値)、
$`v_{stop}`$ = 0.05 m/s。混合体の μ・ξ とは慣性の有無で校正値が異なる
ため別名です。慣性がないので発火直後から終端速度で動き、近地波は
水中発火で過大側、陸上からの高速突入で過小側に偏ります(引き渡し経路と
`f_bsvplunge = 1` で緩和)。

## 6. パラメータと既定値の根拠

根拠欄の分類語の意味は[既定値の根拠の読み方](../users_guide.md#既定値の根拠の読み方)を参照してください。

| パラメータ | 既定 | 意味 | 根拠 |
|---|---:|---|---|
| f_dbres | 1 | 抵抗則(§2) | **方式** 1: クーロン + Manning(経験定数なし) |
| db_phi | 35° | 内部摩擦角 $`\phi`$ | **文献値** 礫質土砂の代表(tanφ ≈ 0.7)[^takahashi07] |
| db_d50 | 0.05 m | 代表粒径(則 2・3、E-D 3) | **慣用値** 石礫型の $`d_L`$ の代表(数 cm〜dm) |
| db_erest | 0.85 | 反発係数 $`e`$(則 2) | **文献値** 江頭系の慣用値[^egashira93] |
| db_cmin | 0.02 | 粒状体則を適用する濃度下限 | **文献値** 高橋・中川の泥流域の規定[^tn91] |
| db_mu / db_xi | 0.2 / 1000 m/s² | Voellmy の μ・ξ(則 4) | **文献値** RAMMS の雪崩の中庸[^christen10]。岩屑は小さめ |
| db_tauy | 10 kPa | 一定停止応力(則 5) | **文献値** VolcFlow 系の火砕流適用例の下寄り[^kelfoun05] |
| f_dbcurv | 0 | 曲率項(§2) | **方式** Fischer ら[^fischer12]。RAMMS 校正値の比較で 1 |
| f_dbed | 1 | 侵食・堆積則(§3) | **方式** 1: 高橋型緩和、2: 江頭・芦田、3: 高橋・中川、4: 速度比例、0: なし |
| db_delte / db_deltd | 0.0007 / 0.05 | 侵食・堆積の速度係数 | **校正量** Takahashi の一般値 / Kanako 系の慣用値 |
| f_dbstop / db_vstop / db_wstop | 0 / 0.05 m/s / 0.05 m/s | 低速凝集の停止条件 | **数値設定** vstop は降伏判定の閾値も兼ねる |
| f_dbwet / db_satbed | 0 / 1.0 | 間隙水の連行 / 堆積層の飽和度(1: 連行、2: 地下水計算と併用) | **方式** 高橋・中川の全容積連続式[^tn91](1)。2 は地表水と地下貯留の間の間隙水の授受(独自) |
| db_reltime / db_relsat | 0 / 1.0 | 流動化の時刻 / 土塊の飽和度(§4) | **与件** |
| slide_c / slide_phi / slide_gamma | 0 / 30° / 18 kN/m³ | 安定解析の強度定数(§4) | **慣用値** 表層崩壊の慣用値。c' = 0 は保守側 |
| bs_rho | 2000 kg/m³ | 土塊のかさ密度(§5) | **慣用値** 飽和土塊・岩屑の代表値 |
| bs_mu / bs_xi | 0.15 / 500 m/s² | 底層の Voellmy μ・ξ | **検証ケース** 慣性なし底層の校正値([test/bedslide](../../test/bedslide/)) |
| bs_vstop / bs_tstop | 0.05 m/s / 0 s | 停止判定の速度と持続時間 | **数値設定** 水域突入では tstop 10〜15 s(離水の継続時間以上) |
| bs_eps_s / bs_cfl / bs_nsubmax | 0.02 / 0.4 / 10000 | 線形化幅 / サブサイクルの安全係数と上限 | **数値設定** サブサイクル過多は eps_s を大きく |
| bs_hplunge / f_bsvplunge / f_bsplunge | 0 / 0 / 0 | 引き渡しの滞水深と条件 | **方式** 陸上からの高速突入では vplunge = 1 |

**既定値を見直すときの手がかり**

- 内部摩擦角・粒径は現地の堆積物の粒度試験・安息角から、強度定数
  (c′, φ′, γ)は土質試験か近傍の崩壊事例の逆算から与えます。
- Voellmy の μ・ξ は到達距離と堆積形状の既往事例に合わせて校正する
  のが通例で、RAMMS の校正値集[^christen10]に地形・規模別の表が
  あります。土石流の実務値は高橋[^takahashi07]にまとまっています。
  土石流の校正例として、イタリア・ドロミテの Cancia の 2015 年の土石流
  (初期 4,400 m³ が流下中の連行で 28,850 m³ に。流路 2.2 km、勾配は上流 27°・
  下流 13°)の逆算では、連行を入れた 2 つのモデル(DAN3D と差分法のモデル)で
  同じ μ = 0.11、ξ = 450 m/s² が最良でした(Hungr の連行則で E_r ≈ 0.001 /m。
  連行を入れないと全量を上流から流すことになり、実際にはなかった越流が起きた)
  [^qiao23]。
- 侵食・堆積の係数は、既往の土石流の流下痕跡(侵食深・堆積厚)を
  再現するように動かします(到達距離と堆積量の両方を見ること)。

## 7. 検証ケース

| ケース | 内容 | 要点 |
|---|---|---|
| [test/debris](../../test/debris/README.md) | 4 つの構成則(簡易・江頭・高橋中川・間隙水)、斜面等流の平衡濃度 | 固体総量 1e-13、np=1,2,4 一致、平衡濃度が高橋型の C∞ に 1e-11 以内 |
| [test/slide](../../test/slide/README.md) | 瞬時流動化と安定判定 | 保存則・水収支の自己検定 |
| [test/volcano](../../test/volcano/README.md) | Voellmy 定常等流と τ_y ランアウト | 等流深の解析解(既定の 2 は斜面に沿う式)に 0.0%(4 近傍) |
| [test/dbslope](../../test/dbslope/README.md) | 30° の斜面の等流(Voellmy・江頭・高橋中川の石礫型と掃流状集合流動)、急勾配の重力補正 1・2 | 4 つとも、2 は斜面に沿う式、1 は水平の式の解析解に 0.03% 以内(2 と 1 の深さの比 1.11〜1.21) |
| [test/curvature](../../test/curvature/README.md) | 曲率項の定常 1 次元検定 | 円弧上の厚化が ODE の 1.03 倍 |
| [test/dbonset](../../test/dbonset/README.md) | 降伏による静止と動き出し(一様な斜面、勾配が降伏の 0.9・1.1・1.3 倍、斜面の向き 0°・22.5°・45°、8・4 近傍、急勾配の重力補正なし・あり)と斜面安定判定の安全率(同じ斜面、c' = 0・地下水なし) | 閾値と速さ・向きが向きと近傍によらず、剛体の滑りの解析解(重力補正ありは g cos²θ)に 0.4% 以内。安全率が向きによらず tanφs/tanθ に 0.1% 以内 |
| [test/avalanche](../../test/avalanche/README.md) | 雪崩(Voellmy + 速度比例連行) | 連行で放出量の約 3.4 倍に成長して停止。台帳は機械精度 |
| [test/bedslide](../../test/bedslide/README.md) | 底層の速度の解析値、45° 斜面、湖への突入 | 内部セルの $`V`$ が解析値に 0.5% |
| [examples/landslide_tsunami](../../examples/landslide_tsunami/) | 岩屑なだれ・引き渡し・海底地滑り | 4 パターンの比較 |
| [examples/ashfall_lahar](../../examples/ashfall_lahar/) | 降灰 → 降雨 → 泥流、砂防堰堤 | ラハールの設定の型(浸透能・f_dbwet=2) |
| [examples/debris_fan](../../examples/debris_fan/) | 斜面崩壊 → 谷 → 扇状地の住宅地(高橋・中川の石礫型)。格子間隔 40〜2.5 m・谷の向き 0°・22.5°・45°、4 近傍の対照 | 格子への依存。8 近傍は谷の向きによる差が 5 m で数 %、谷底より粗い 40 m でも土砂が扇状地に届く。4 近傍は 20 m 以上で斜めの谷に土砂が残る |

## 参考文献

[^nakatani08]: Nakatani, K., Wada, T., Satofuka, Y. and Mizuyama, T. (2008): Development of "Kanako 2D (Ver.2.00)", a user-friendly one- and two-dimensional debris flow simulator equipped with a graphical user interface. *Int. J. Erosion Control Eng.*, 1(2), 62–72.
[^morpho2dh]: 竹林洋史: Morpho2DH ver.2 Solver Manual. iRIC Project.(江頭モデルの支配方程式と既定値)
[^takahashi07]: Takahashi, T. (2007): *Debris Flow: Mechanics, Prediction and Countermeasures*. Taylor & Francis, Leiden.(平衡濃度・侵食速度係数)
[^tn91]: 高橋保・中川一 (1991): 石礫型土石流の予測法. 新砂防, 44(3), 12–19.
[^egashira93]: 江頭進治 (1993): 土石流の停止・堆積のメカニズム(2). 新砂防, 46(2).(江頭ら(1989)の構成則と降伏応力の原式)
[^voellmy55]: Voellmy, A. (1955): Über die Zerstörungskraft von Lawinen. *Schweizerische Bauzeitung*, 73, 159–165, 212–217, 246–249, 280–285.
[^hungr95]: Hungr, O. (1995): A model for the runout analysis of rapid flow slides, debris flows, and avalanches. *Can. Geotech. J.*, 32, 610–623. doi:10.1139/t95-063(連行則の形は Qiao ら 2023 の式 (14)・(15) による。原論文は未読)
[^qiao23]: Qiao, Z., Li, T., Simoni, A., Gregoretti, C., Bernard, M., Wu, S., Shen, W. and Berti, M. (2023): Numerical modelling of an alpine debris flow by considering bed entrainment. *Front. Earth Sci.*, 10, 1059525. doi:10.3389/feart.2022.1059525(Cancia 2015 の土石流。Voellmy の μ・ξ と連行率の校正値は表 2・表 3)
[^christen10]: Christen, M., Kowalski, J. and Bartelt, P. (2010): RAMMS: Numerical simulation of dense snow avalanches in three-dimensional terrain. *Cold Reg. Sci. Technol.*, 63, 1–14.
[^fischer12]: Fischer, J.-T., Kowalski, J. and Pudasaini, S. P. (2012): Topographic curvature effects in applied avalanche modeling. *Cold Reg. Sci. Technol.*, 74–75, 21–30.
[^pitman03]: Pitman, E. B., Nichita, C. C., Patra, A., Bauer, A., Sheridan, M. and Bursik, M. (2003): Computing granular avalanches and landslides. *Phys. Fluids*, 15, 3638–3646.(Titan2D)
[^kelfoun05]: Kelfoun, K. and Druitt, T. H. (2005): Numerical modeling of the emplacement of Socompa rock avalanche, Chile. *J. Geophys. Res.*, 110, B12202.(VolcFlow)
[^tarboton97]: Tarboton, D. G. (1997): A new method for the determination of flow directions and upslope areas in grid digital elevation models. *Water Resour. Res.*, 33(2), 309–319.(D∞。面の向きの判定は atan2 を使わない同値な比較にした。developer.md §92)
[^montgomery94]: Montgomery, D. R. and Dietrich, W. E. (1994): A physically based model for the topographic control on shallow landsliding. *Water Resour. Res.*, 30, 1153–1171.(SHALSTAB)
[^tinti06]: Tinti, S., Pagnoni, G. and Zaniboni, F. (2006): The landslides and tsunamis of the 30th of December 2002 in Stromboli analysed through numerical simulations. *Bull. Volcanol.*, 68, 462–479.
[^harbitz06]: Harbitz, C. B., Løvholt, F., Pedersen, G. and Masson, D. G. (2006): Mechanisms of tsunami generation by submarine landslides: a short review. *Norw. J. Geol.*, 86, 255–264.
