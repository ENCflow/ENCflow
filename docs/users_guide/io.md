# 入出力の形式

[ユーザーガイド目次へ](../users_guide.md)

分布データ(地形・粗度・結果など)の入出力は3形式に対応しています。
いずれも `&list_sysparam` で選びます。

## ラスタの共通規約

- 行列の並びは**先頭行が北端**(行=y 方向・北→南、列=x 方向・西→東)。
  GIS のラスタや紙の地図と同じ向きです。
- 全形式で同じ並び・同じ値です(形式はコンテナの違いにすぎません)。

## 入力形式(f_input_mode)

| 値 | 形式 |
|---|---|
| 1(既定) | 行列テキスト(空白区切り) |
| 2 | bil(生バイナリ+ESRI hdr) |
| 4 | GeoTIFF |

- bil は同名の `.hdr` があれば画素型(int8/int16/int32・符号の有無)を
  読み分けます。hdr がなければ従来の int32 として読みます。
- GeoTIFF は無圧縮・LZW・Deflate(predictor 付き含む)、ストリップ・
  タイル配置に対応し、QGIS / ArcGIS / GDAL の実出力で検証済みです。
  外部ライブラリは使っていません(自前実装)。
- 入力形式は1つを選びます(出力と違いビット和ではありません)。

## 出力形式(f_output_mode)

**ビット和**で複数形式を同時に出せます。

| 値 | 出力される形式 |
|---|---|
| 1(既定) | テキストのみ |
| 2 | bil のみ |
| 3 | テキスト+bil |
| 4 | GeoTIFF のみ |
| 7 | テキスト+bil+GeoTIFF |

座標系を管理していると、bil には `.hdr` が併記され、GeoTIFF には CRS が
埋め込まれます([座標系の章](coordinates.md))。

## 出力ファイルの体系

出力は `dir_result`(既定 `result/`)に、**接頭辞+4桁番号**の名前で
書き出されます。

**番号の意味**

| 番号 | 意味 |
|---|---|
| 0000 | このランの開始状態(再開ランでは復元された状態) |
| 0001〜 | dt_file ごとの連番(時刻との対応表が `FILENUMBER.csv`) |
| 9998 | 最終タイムステップの状態 |
| 9999 | 計算期間を通じた最大値などの統計 |

**接頭辞と出力フラグ**(`f_out_XXX = 1` で有効化。既定で出るのは
H・H9999 と、地盤高の初期値 Z0000 のみ)

| フラグ | 既定 | ファイル | 内容 |
|---|---|---|---|
| f_out_h | 1 | H | 水深 (m) |
| f_out_e | 0 | E | 水位(標高基準)(m) |
| f_out_z | 0 | Z | 地盤高 (m)(off でも Z0000 は常に出力。地形変化計算の時間発展に) |
| f_out_u / f_out_v | 0 | u / v | x / y 方向流速 (m/s) |
| f_out_vv | 0 | V | 流速絶対値 (m/s) |
| f_out_m / f_out_n | 0 | m / n | x / y 方向線流量 (m²/s) |
| f_out_qq | 0 | Q | 流量絶対値 (m²/s) |
| f_out_qc | 0 | Qc | 積算流量 |
| f_out_qd | 0 | Qd | 流向(utils/rerecord で必要) |
| f_out_ddd / f_out_dda | 0 | Ddd / Dda | 卓越/全流下方向(utils/rmdepress_river で必要) |
| f_out_pre | 0 | Pr | 降雨強度 (mm/h) |
| f_out_fr / f_out_cn | 0 | Fr / Cn | フルード数 / クーラン数 |
| f_out_hg | 0 | Hg | 地下貯留水深 (m)(fn_gwflow 有効時) |
| f_out_hrs | 0 | Hrs | ため池水深 (m)(fn_reservoir 有効時) |
| f_out_hmax | 1 | H9999 | 最大水深 |
| f_out_hmaxt | 0 | Ht9999 | 最大水深の発生時刻 |
| f_out_vvmax | 0 | V9999 | 最大流速 |
| f_out_qqmax / f_out_qqmaxt / f_out_qqmaxd | 0 | Q9999 / Qt9999 / Qd9999 | 最大流量とその発生時刻・流向 |

このほか、`Log.txt`(画面表示と同一のログ)と、使用したパラメータ
ファイルの控えが常に保存されます。

分布出力は GIS(QGIS / ArcGIS)でそのまま開けるほか、
**utils/out2vtk** で ParaView 用の VTK 形式に変換すると、地形の 3D
表示・水面の時系列アニメーション・衛星写真のドレープができます
(手順は [utils/out2vtk/README.md](../../utils/out2vtk/README.md))。

## 画面・ログの表示列(f_disp_\*)

時刻・保存量 S・Runge・ex_flux は常に表示され、場の最大値の列は
選択できます: `f_disp_h`(h_max。既定 on)・`f_disp_vv`(V_max。
既定 on)・`f_disp_cn`(Cn_max。既定 on)・`f_disp_qq`(Q_max。
既定 off)。`f_disp_debug = 1` は S 列を全有効桁で表示します
(収支のデバッグ・回帰テスト用)。列の読み方は
[チュートリアル Step 1](../../tutorials/wave/README.md#実行) を
参照してください。

## ディレクトリとファイル名の調整

| パラメータ | 既定値 | 意味 |
|---|---|---|
| dir_data | "." | 入力データファイルの基点ディレクトリ |
| dir_result | "result" | 結果出力ディレクトリ |
| dir_save | "save" | 状態保存([中断と再開](restart.md))のディレクトリ |
| fn_log | "Log.txt" | ログファイル名 |
| outfn_suffix | "" | 出力ファイル名の末尾に付く文字列(シナリオを同じディレクトリで並走させるときの衝突回避) |
