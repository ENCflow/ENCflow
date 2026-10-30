# 規定底面運動の解説(規定底面運動の補足)

[規定底面運動の章へ](bedmotion.md) | [ユーザーガイド目次へ](../users_guide.md)

[規定底面運動の章](bedmotion.md)の背後にある定式 — 変位の時間補間と
地盤高の更新、断層変位場と初期水面、静水圧・非静水圧での短波の扱い、
動作の契約(再開・MPI)— と検証ケースをまとめます。実装は
`src/m_bedmotion.f90` と `utils/fault2disp` で、設計の経緯は
docs/bedmotion_plan.md と developer.md §70 にあります。

## 1. 変位の時間補間と地盤高の更新

```math
d(t) = d_k + \frac{t - t_k}{t_{k+1} - t_k}\left(d_{k+1} - d_k\right)\ (\texttt{f\_bminterp} = 1),
\qquad
z^{\,n+1} = z^{\,n} + \left[d(t_{n+1}) - d_{prev}\right],
\quad h\ \text{不変},\quad e = z + h
```

- 各ステップの頭で、そのステップ末尾の時刻の変位を補間し、前回適用した
  変位との**差分**を z に加えます。線形補間のとき底面速度はスナップ
  ショット間で一定で、境界で速度が跳びます。
- 階段補間(f_bminterp = 0)は、通常の時間進行で次のスナップショット時刻を
  **超えた**評価から次の値へ切り替えます。ちょうど等しい評価では直前の値を
  保持します(`m_bedmotion_calc` の進行条件)。章の図 (a) の階段線は補間
  方式の概念図で、切替点での左右どちらの値を使うかを示していません。
- 増分で与えるため、土砂・地形変化・動く底層・溶岩流が同じランで z を
  動かしていても衝突しません(各モジュールは自分の増分だけを加える)。
- 乾いたセル(h = 0)も同じ式で動きます。解像堤防の破堤(章の §5)は
  この性質を使い、乾いた天端セルの z を堤底まで下げて川の水を堤内地へ
  通します。変位ファイルの作り方は examples/levee_breach/make_breach.py。

## 2. 断層変位場と初期水面

utils/fault2disp は、断層の位置・走向・傾斜・すべり角・長さ・幅・すべり量
から弾性半無限体の解析解(Okada の式[^okada85])で地表変位を計算し、破壊
開始時刻と立ち上がり時間で時刻歴にします。海底が急な斜面のときは、鉛直
変位に水平変位と海底勾配の積を加えた

```math
\eta_0 = u_z + u_h\cdot\nabla z
```

を初期水面変位とみなす扱い[^tanioka96]が重要で、fault2disp は地盤高を
与えられたときにこれを計算します。

破壊過程を省いた瞬時変位(章のパターン C)との差は、震源近傍の到達時刻と
波高に現れます。例題では [examples/tsunami_fault](../../examples/tsunami_fault/) の
最高水位で 2〜3 %、[examples/tsunami_coast](../../examples/tsunami_coast/) の
湾口・棚で +24〜40 % です(各 README)。

## 3. 静水圧と非静水圧

静水圧計算では底面の持ち上げがそのまま水面に写ります。震源の幅が水深に
比べて十分広い海溝型地震はこれで十分です。震源の幅が水深と同程度の短い
変位(分岐断層、深海の狭い滑り、海底地滑り)では、水柱の慣性で短波が
減衰します(Kajiura のフィルタ $`1/\cosh kH`$[^kajiura63])。
[非静水圧補正](nonhydrostatic.md) §7 の f_nonhydrostatic=1 と f_nh_bottom=1 が
これを 1 層近似 $`1/(1 + \beta k^2)^2`$ で与えます(developer.md §69.10)。
このとき速度の跳びが加速度のパルスとして入るので、スナップショットを
細かく(fault2disp の nout を増やす。[test/nhbottom](../../test/nhbottom/) は
毎ステップ)出してください。[examples/tsunami_fault](../../examples/tsunami_fault/)
では非静水圧で沿岸の最高水位が −24 %(分散)、加速度項の寄与はさらに −2 % です。

## 4. 動作の契約(再開・MPI・API)

- 計算対象セル(x > 0、sw = 0)の z に増分を加え、h は変えず e = z + h を
  回復します。運動量は触りません。土層厚 sd は変えません(岩盤面 z − sd が
  変位します)。海域マスク(sw > 0)のセルは水位を規定される側なので、変位を
  与えても動きません。
- 再開: 私有の変位履歴は保存しません。モード 1 で保存ステップ `it0 > 0`
  から再開すると、同じ表から再開時刻の変位を求めて「適用済み」とします。
  ただし階段補間では、初期化が再開時刻に達したスナップショットを含めて
  選ぶ条件と、通常進行の切替条件が異なるため、切替時刻ちょうどで保存・
  再開する場合の厳密一致は保証されません。モード 2 は履歴 0 から始めるため、
  保存地形に含まれる変位を二重に与えない系列を用意します
  ([中断と再開](restart.md))。
- ENC 専用です。STG で有効にすると初期化時に停止します。ライブラリ API の
  set_value('z') は fn_bedmotion 有効時に拒否されます(z の生産者は一人)。
- MPI: 各ランクが変位ファイル全体を読み、自分の帯を切り出します(読み込みは
  冗長、適用は帯ごと)。窓付きファイルでも、保持する変位配列と時間補間の
  作業範囲は各 MPI 帯全体です。再現性の条件は[並列実行](parallel.md)。

## 5. パラメータと既定値の根拠

根拠欄の分類語の意味は[既定値の根拠の読み方](../users_guide.md#既定値の根拠の読み方)を参照してください。

| パラメータ | 既定 | 意味 | 根拠 |
|---|---:|---|---|
| fn_bmlist | (必須) | スナップショット表 | **与件** 断層モデル(utils/fault2disp)か自作の変位場 |
| f_bminterp | 1 | スナップショット間の時間補間 | **方式** 線形が既定。階段(0)は瞬時変位・破堤の時刻を厳密に切りたいとき |
| bm_tscale | 1.0 | 表の時刻の単位 (s) | **与件** 60 で分、3600 で時 |
| 断層パラメータ(fault2disp) | — | 位置・走向・傾斜・すべり角・長さ・幅・すべり量・立ち上がり時間 | **与件** 震源モデルの公表値。変位場は Okada の解析解[^okada85]、水平変位の寄与は Tanioka & Satake[^tanioka96] |

**既定値を見直すときの手がかり**

- 断層パラメータは気象庁・地震調査研究推進本部・USGS の震源モデル
  (有限断層モデル)の公表値を使います。立ち上がり時間は破壊継続時間
  (M8 級で数十秒〜百数十秒)を目安にします。
- 短い波長の変位(幅が水深と同程度)では[非静水圧補正](nonhydrostatic.md) §7 の
  f_nh_bottom を有効にし、スナップショットを細かく出してください(§3)。

## 6. 検証ケース

- [test/nhbottom](../../test/nhbottom/) 構成 3: 水深 10 m の水路で |x − x_c| < 20 m を 1 s で 0.2 m
持ち上げる Hammack 型の隆起を、毎ステップのスナップショット表で与え、
ライブラリ API で同じ運動を与えたドライバの結果と一致します(Log の
全有効桁の体積列の最終桁を除いて同一)。再開(0.5 s で save → restore)
も中断なしの計算と一致(静水圧。非静水圧の f_nh_bottom では加速度項の
1 ステップ分だけ異なります)、海底地滑り(f_bedslide)との同居では
Σ(z − z0) = Σ d(底層の内部移転は総和 0)が出力精度の範囲で成り立ちます。
- [examples/tsunami_fault](../../examples/tsunami_fault/README.md): 静水圧 / 瞬時変位 / 非静水圧 + 加速度項の比較。
- [examples/tsunami_coast](../../examples/tsunami_coast/README.md): 沿岸の沈降・隆起と沖の津波の時間差。
- [examples/levee_breach](../../examples/levee_breach/README.md): 越水による解像堤防の破堤と、堤内地の氾濫・家屋の流失(補足に仮想壁面の &list_channel_breach との比較)。

## 参考文献

[^okada85]: Okada, Y. (1985): Surface deformation due to shear and tensile faults in a half-space. *Bull. Seismol. Soc. Am.*, 75, 1135–1154.
[^tanioka96]: Tanioka, Y. and Satake, K. (1996): Tsunami generation by horizontal displacement of ocean bottom. *Geophys. Res. Lett.*, 23, 861–864.
[^kajiura63]: Kajiura, K. (1963): The leading wave of a tsunami. *Bull. Earthq. Res. Inst. Univ. Tokyo*, 41, 535–571.
