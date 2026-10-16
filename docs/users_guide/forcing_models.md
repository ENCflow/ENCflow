# 降雨・気象のモデルの解説(降雨・気象の補足)

[降雨・気象の章へ](forcing.md) | [ユーザーガイド目次へ](../users_guide.md)

[降雨・気象の章](forcing.md)の各モデル — 降雨遮断(固定遮断率・初期損失)、
気温と降水の標高補正、可能蒸発散(Hamon・Thornthwaite)、度日法の
積雪・融雪 — の式と既定値の根拠をまとめます。実装は
`src/m_intercept*.f90`、`src/m_meteo.f90`、`src/m_evap.f90`、
`src/m_snow.f90` で、既定値の経緯は developer.md §65・§66 にあります。

## 1. 降雨遮断

**固定遮断率(f_icmodel = 1)。** 降水 $`P`$ の一定割合 $`\alpha`$ を損失として
取り除き、残りを後続の雨雪判定へ渡します。樹冠貯留は持ちません。

```math
P_{out} = (1 - \alpha)\,P
```

**初期損失(f_icmodel = 2)。** 降り始めの雨を最大貯留量 $`S_{\max}`$ まで
蓄え、満たされた後は素通しにします。毎ステップ、残容量まで保水して余りを
通します。

```math
\Delta S = \min\!\left(P\,\Delta t,\ S_{\max} - S\right),
\qquad
P_{out} = P - \frac{\Delta S}{\Delta t}
```

樹冠貯留 $`S_{\max}`$ で遮断を表す Rutter・Gash 系の貯留型モデル[^crockford00]の
最簡形で、排水と蒸発の時間発展は蒸発散モジュールに委ねます(`fn_evap` の
蒸発散で樹冠保水が減ると再び遮断できるようになり、蒸発散を使わなければ
空き容量は回復しません)。

**既定値の根拠。** $`\alpha`$ = 0.15、$`S_{\max}`$ = 1.5 mm は、Crockford &
Richardson のレビュー(遮断損失は針葉樹林 20〜40 %、広葉樹林 10〜25 %、
草地 5〜10 %。樹冠貯留 0.3〜3 mm)[^crockford00]の広葉樹・混交林の代表値で、
市街地の不透水面の窪地貯留(SWMM の慣用値 1.3〜2.5 mm[^rossman15])とも
同程度です。植生別の目安は章の表にあります。

## 2. 気温と降水の標高補正

一様な気温入力に `f_temp_lapse = 1` を指定すると、標高 $`z`$(m)に対して

```math
T = T_{\mathrm{input}} + \Delta T - \gamma\,(z - z_{T,\mathrm{ref}}),
\qquad
\gamma = \frac{\mathtt{temp\_lapse}}{100}
```

とします。$`z_{T,\mathrm{ref}}`$ は `temp_zref`、$`\Delta T`$ は `tempofs` の
値(省略時 0)です。減率 0.65 ℃/100 m、基準からの標高差 1000 m なら気温は
6.5 ℃ 下がります。分布気温 `fn_tempmap` に減率を重ねる設定は初期化時に
エラーになります(分布気温にも `tempofs` は加算します)。既定 0.65 ℃/100 m は
標準大気の値(経験値)です。

降水の標高補正(`f_prec_lapse = 1`)は、入力の `prec_lapse` を %/100 m から
1/m に換算し、降水の更新時(遮断より前)に次の倍率を掛けます。

```math
F_P = \max\!\left(0,\ 1 + \beta\,(z - z_{P,\mathrm{ref}})\right),
\qquad
\beta = \frac{\mathtt{prec\_lapse}}{10000}
```

$`z_{P,\mathrm{ref}}`$ は `prec_zref` です。10 %/100 m、標高差 500 m なら
倍率 1.5 で、負になる場合は 0 に制限されます。降水補正と積雪の気温評価は、
氷河が有効なら氷面 $`z + h_i`$ を標高に使い、蒸発散の気温評価は地盤高
$`z`$ を使います。

## 3. 可能蒸発散(Hamon・Thornthwaite)

モード 3・4 は、可照時間 $`N`$(時間。太陽赤緯は Cooper の近似)と日平均
気温 $`T`$(℃)から次の式で PET(mm/day)を推算します。

```math
PET_{\text{Hamon}} = 0.1651\,\frac{N}{12}\,\frac{216.7\,e_s}{T + 273.3},
\qquad
e_s = 6.108\,\exp\!\left(\frac{17.27\,T}{T + 237.3}\right)\ [\mathrm{hPa}]
```

```math
PET_{\text{Thornthwaite}} = \frac{16}{30}\left(\frac{10\,\max(T, 0)}{I}\right)^{a}\frac{N}{12},
\qquad
I = \sum_{m=1}^{12}\left(\frac{\max(T_m, 0)}{5}\right)^{1.514},
\quad
a = 6.75\times10^{-7}I^3 - 7.71\times10^{-5}I^2 + 1.792\times10^{-2}I + 0.49239
```

Hamon 式[^hamon61]は飽和水蒸気密度(Tetens 式)と可照時間だけで推算する
気温法、Thornthwaite 式[^thornthwaite48]は月平均気温の平年値から熱指数
$`I`$ を作る気候学的な式で、月の値を 30 で割って日割りにしています。
どちらも放射・風・湿度を使わない簡便法で、`evap_kc` で校正します。
モード 3・4 は暦日の先頭時刻の気温でその日の PET を評価し、日内は一定です
(日平均気温の系列を推奨)。

**適用順。** PET に `evap_kc` を掛け、mm/day を内部の m/s に換算して、各
ステップで $`PET\,\Delta t`$ に相当する水深を **樹冠保水(貯留型遮断のみ)→
地表水 $`h`$ → 貯留 $`h_{rs}`$(ため池・ダム／湖沼捕捉帯)→ 地下水 $`h_g`$** の
順に差し引きます。各段で存在する水量を上限とし、残った要求だけを次へ
渡します。供給制限以外の乾燥抑制や、SWE からの昇華は扱いません。地表流と
地下水計算の後の状態に作用します。

**既定値の根拠。** モード 1 の既定 3 mm/day は、温帯湿潤気候の暖候期の
基準蒸発散(FAO-56[^allen98] の $`ET_0`$ で 3〜5 mm/day)の下寄りで、日本の
年平均(2〜2.5 mm/day)より大きく夏季(4〜5)より小さい中庸です。季節を
通す計算ではモード 2〜4 を使ってください(月別値・緯度・平年気温は与件
なので既定はありません)。

## 4. 度日法の積雪・融雪

遮断後の降水を雨と雪へ分け、雪を積雪水量 SWE として蓄えます。
$`T \le`$ `snow_t_snow` は全雪、$`T \ge`$ `snow_t_rain` は全雨で、その間は
線形混合です(閾値は `snow_t_rain ≥ snow_t_snow`。同値ならその温度以下が
全雪、超えると全雨)。分離後の雨だけが降雨として地表へ入ります。

雪を加えた後の SWE を上限に、各ステップの融雪量(mm。$`\Delta t`$ は秒)は

```math
\Delta W_{\mathrm{melt}} = \min\left(\mathrm{SWE},\
\mathtt{snow\_ddf}\,\max(T - \mathtt{snow\_t\_melt},\,0)\,
\frac{\Delta t}{86400}\right)
```

です。度日法[^hock03]は気温だけで融雪を推算する簡便法で、放射・風・雨に
よる融解は度日係数に押し込みます。内部では m に換算し、空隙率と有効な
河道幅の面積換算を経て地表水 $`h`$ に直接加えます(融雪水は降雨強度
`pre` には含めません)。たとえば `snow_ddf` = 4、融雪閾値より 3 ℃ 高い
気温、$`\Delta t`$ = 3600 s なら融雪要求は 0.5 mm で、SWE が 0.2 mm しか
なければ融雪量は 0.2 mm です。再凍結、雪内の雨水保持、昇華は扱いません。

**既定値の根拠。** `snow_ddf` = 4 mm/℃/day は Hock の集計(雪 2.5〜6 が
多数。森林で小、開放地で大)[^hock03]の中央で、日本の山地流域の融雪出水の
慣用値 3〜5 の中庸です。雨雪の閾値 0〜2 ℃ は、湿球温度 1 ℃ 前後で雨雪が
切り替わる観測に基づく慣用値です。型別の目安は章の表にあります。

## 5. パラメータと既定値の根拠

根拠欄の分類語の意味は[既定値の根拠の読み方](../users_guide.md#既定値の根拠の読み方)を参照してください。

| パラメータ | 既定 | 意味 | 根拠 |
|---|---:|---|---|
| ic_alpha | 0.15 | 固定遮断率 $`\alpha`$ | **文献値** 広葉樹・混交林の遮断損失 10〜25 %[^crockford00] |
| ic_smax_mm | 1.5 mm | 初期損失の最大貯留 $`S_{\max}`$ | **文献値** 樹冠貯留 0.3〜3 mm[^crockford00]。市街地の窪地貯留 1.3〜2.5 mm[^rossman15]と同程度 |
| temp_lapse | 0.65 ℃/100 m | 気温減率 | **慣用値** 標準大気の気温減率 |
| prec_lapse | 0 | 降水の増率 | **与件** 既定は補正なし |
| evap0 | 3 mm/day | 一定 PET | **文献値** 温帯湿潤の暖候期 $`ET_0`$ 3〜5 の下寄り[^allen98] |
| evap_kc | 1 | PET の換算係数 | **校正量** パン係数・作物係数に相当 |
| snow_t_snow / snow_t_rain | 0 / 2 ℃ | 雨雪判定の閾値 | **慣用値** 湿球温度 1 ℃ 前後で切り替わる観測に基づく慣用の範囲 |
| snow_t_melt | 0 ℃ | 融雪の閾値 | **慣用値** 度日法の標準 |
| snow_ddf | 4 mm/℃/day | 度日係数 | **文献値** 雪 2.5〜6 の中央[^hock03]。日本の山地流域の慣用値 3〜5 の中庸 |

**既定値を見直すときの手がかり**

- 遮断率・樹冠貯留は林相(針葉樹・広葉樹・落葉期)で変わります。
  Crockford & Richardson のレビュー[^crockford00]に林相別の範囲が
  あります。
- 気温減率は近傍の気象官署・アメダス 2 地点の標高差から直接求められ
  ます(季節で 0.5〜0.7 ℃/100 m)。
- 一定 PET は FAO-56[^allen98]の Penman–Monteith を月平均気象で評価した
  値に、Hamon・Thornthwaite(§3)を使うなら係数 evap_kc で水収支
  (年流出高)に合わせます。
- 度日係数は、積雪深計・衛星の積雪域の消長に合わせて校正するのが
  常道で、Hock のレビュー[^hock03]に地域別の値の集計があります。

## 6. 検証ケース

- [test/icevap](../../test/icevap/): 固定遮断率・初期損失・一定蒸発散について、最小入力と既定値を明示した入力の同値を検定。
- [test/frost](../../test/frost/): 一定気温による凍結指数の増加と浸透抑制を解析値と比較。
- [test/chichibu](../../test/chichibu/): 実地形流域への一様降雨の回帰ケース。

## 参考文献

[^crockford00]: Crockford, R. H. and Richardson, D. P. (2000): Partitioning of rainfall into throughfall, stemflow and interception: effect of forest type, ground cover and climate. *Hydrol. Process.*, 14, 2903–2920.
[^rossman15]: Rossman, L. A. (2015): Storm Water Management Model User's Manual Version 5.1. US EPA, EPA/600/R-14/413b.(窪地貯留の慣用値)
[^hamon61]: Hamon, W. R. (1961): Estimating potential evapotranspiration. *J. Hydraul. Div. ASCE*, 87(HY3), 107–120.
[^thornthwaite48]: Thornthwaite, C. W. (1948): An approach toward a rational classification of climate. *Geogr. Rev.*, 38, 55–94.
[^allen98]: Allen, R. G., Pereira, L. S., Raes, D. and Smith, M. (1998): Crop Evapotranspiration: Guidelines for Computing Crop Water Requirements. *FAO Irrigation and Drainage Paper*, 56.
[^hock03]: Hock, R. (2003): Temperature index melt modelling in mountain areas. *J. Hydrol.*, 282, 104–115.
