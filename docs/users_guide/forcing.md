# 降雨・気象(&list_precip / intercept / meteo / evap / snow)

[ユーザーガイド目次へ](../users_guide.md)

水文計算の駆動力となる5つの機能をまとめて説明します。それぞれ独立に
有効化でき、組み合わせると次の流れで作用します。

```
降水(fn_precip)
  → 樹冠遮断で減損(fn_intercept)
  → 気温による雨・雪の判定(fn_snow ← 気温は fn_meteo)
      雪は積雪として貯留され、融雪で地表へ
  → 地表水へ
地表の水は蒸発散(fn_evap)で失われる
```

**降水(fn_precip)は水収支への質量入力**、**気象強制場(fn_meteo)は
気温などの背景場**という役割の違いで分かれています。雨だけの計算に
fn_meteo は不要です。

## 気象入力を1枚のファイルにまとめる(推奨書式)

各 fn_\* には同じファイル名を指定できるので、気象系の入力は1枚に
まとめられます。

```
&list_sysparam
  ...
  fn_precip = "forcing.txt"
  fn_meteo  = "forcing.txt"
  fn_snow   = "forcing.txt"
/
```

```
! ---- forcing.txt ----
&list_precip
  prtype = 1
  prval(:,1) = 0, 10        ! (時刻(min), 雨量強度(mm/h))
  prval(:,2) = 1440, 10
/
&list_meteo
  temp0 = 2.0               ! 一様気温 (℃)
/
&list_snow
  snow_ddf = 3.0            ! 度日係数 (mm/℃/day)
/
```

## 降水(&list_precip)

雨の与え方は `prtype` で選びます。

| prtype | 与え方 | 使うパラメータ |
|---|---|---|
| 0(既定) | 降水なし(一時無効化) | — |
| 1 | 一様な時系列 | prval |
| 2 | 固定の分布 × 時系列倍率 | fn_prmap、prval(倍率) |
| 3 | 時系列の分布ファイル群(レーダー雨量等) | fn_maplist、dt_maplist |

| パラメータ | 既定値 | 意味 |
|---|---|---|
| prval | — | 時系列 `(時刻(min), 値)` の組。値は prtype=1 で雨量強度 (mm/h)、prtype=2 で倍率。最後の時刻以降は最後の値で継続 |
| dt_prupdate | 1 | 降雨の更新間隔 (min)(prtype=1, 2) |
| fn_prmap | "" | 降水分布ファイル(prtype=2) |
| fn_maplist | "" | 分布ファイル名のリスト(1行1ファイル。prtype=3)。**リスト中のパスも dir_data 起点**(リストファイルからの相対ではない) |
| dt_maplist(_c) | 60 | 分布ファイルの時間間隔 (min)(prtype=3) |
| dt_mapunit(_c) | 0 | 分布ファイルの値が「何分間の積算雨量 (mm)」かの指定。0(既定)なら prtype=2 は1日(= mm/day)、prtype=3 はファイル間隔(dt_maplist 間の積算 mm。間隔1時間なら mm/h と同値) |
| runoff_rate | 1.0 | 降水に乗じる流出率(粗い流出解析で浸透分を差し引く簡便法。地下水計算を使うなら 1.0 のまま) |

```
&list_precip                ! 例: 10分から24時間、15 mm/h の一様雨
  prtype = 1
  prval(:,1) =    0,  0
  prval(:,2) =   10, 15
  prval(:,3) = 1440, 15
  prval(:,4) = 1450,  0
/
```

書式の実例は [examples/List_samples/list_precip.txt](../../examples/List_samples/list_precip.txt)
に4タイプ分あります。降雨強度の分布は `f_out_pre = 1` で `Pr0001` と
して出力できます。

## 降雨遮断(&list_intercept)

樹冠などによる降雨の損失を、地表に届く前の減損として与えます。

| パラメータ | 既定値 | 意味 |
|---|---|---|
| f_icmodel | 0 | 0: なし(一時無効化)、1: 固定遮断率、2: 初期損失(貯留型) |

モデル固有の設定は同じファイル内の専用グループに書きます。

**固定遮断率(f_icmodel = 1、&list_intercept_fixed)** — 降雨の一定
割合 α を遮断し、有効雨量 (1−α)P を地表に与えます。`ic_alpha`
(一様値)または `fn_icalpha`(分布。指定時は ic_alpha 不使用)。

**初期損失(f_icmodel = 2、&list_intercept_initloss)** — 降り始めの
雨を最大貯留量まで蓄え、満たされた後は素通しにします。`ic_smax_mm`
(一様値 mm)または `fn_icsmax`(分布)。

## 気象強制場(&list_meteo)

気温を一元管理し、蒸発散・融雪・水質などへ提供します。入力は
**3通りのいずれか1つ**です。

| パラメータ | 既定値 | 意味 |
|---|---|---|
| temp0 | — | 一様な定数 (℃) |
| tempval | — | 一様な時系列 `(経過日数, ℃)`。時刻は t=0 からの経過**日** |
| fn_tempmap | "" | 気温分布ファイルのリスト(1行1ファイル、dt_tempmap_c 間隔で順次適用・終端保持) |
| dt_tempmap_c | "1 day" | 分布ファイルの時間間隔 |
| f_temp_lapse | 0 | 1: 標高による気温減率を有効化(一様入力のみ) |
| temp_lapse | 0.65 | 減率 (℃/100 m) |
| temp_zref | 領域最低標高 | 基準標高 (m)。T(z) = T − 減率×(z − temp_zref) |

気温減率を使うと、一様気温の入力でも山地の気温が標高に応じて下がり、
融雪計算では**雪線が自動的に現れます**。

## 蒸発散(&list_evap)

可能蒸発散(PET)の与え方を `f_evmodel` で選びます。

| f_evmodel | 方法 | 必要なもの |
|---|---|---|
| 0(既定) | なし(一時無効化) | — |
| 1 | 一定速度 evap0 (mm/day) | — |
| 2 | 月別気候値 evap_monthly (mm/day ×12) | 暦(date0_c) |
| 3 | Hamon 式(気温と可照時間から推算) | 暦・気温(fn_meteo)・緯度 lat |
| 4 | Thornthwaite 式 | 3 に加えて月平均気温の平年値 temp_normal(×12) |

| パラメータ | 既定値 | 意味 |
|---|---|---|
| evap0 | — | モード1: PET (mm/day) |
| evap_monthly | — | モード2: 月別 PET (mm/day)。12ヶ月分 |
| evap_kc | 1.0 | 換算係数(パン係数・校正用。全モード共通) |
| lat | — | 代表緯度 (deg)。モード3, 4 で必須 |
| temp_normal | — | 月平均気温の平年値 (℃)。モード4 で必須 |

蒸発散は地表の水(供給制限つき)から差し引かれ、集計が結果
ディレクトリの `evap.csv` に出力されます。必要条件が揃っていない
設定(暦なしのモード2など)は初期化時に何が足りないかを示して
停止します。

## 積雪・融雪(&list_snow)

度日法による積雪・融雪です。**気温(fn_meteo)が必須**です。

| パラメータ | 既定値 | 意味 |
|---|---|---|
| f_snow | 1 | 0 でファイルを残したまま一時無効化 |
| snow_t_snow | 0.0 | すべて雪になる気温閾値 (℃) |
| snow_t_rain | 2.0 | すべて雨になる気温閾値 (℃)。間は雨雪が線形に混合 |
| snow_t_melt | 0.0 | 融雪の気温閾値 (℃) |
| snow_ddf | — | 度日係数 (mm/℃/day)。**必須** |
| snow_swe0 / fn_snow_swe0 | — / "" | 初期積雪水量 (mm)(一様値 / 分布。排他) |

降雪は積雪水量(SWE)として蓄えられ、気温が snow_t_melt を超えた
度日分だけ融けて地表水になります。気温減率(&list_meteo)と併用
すると標高帯ごとの積雪・融雪が表現されます。

## 併用の条件まとめ

| 機能 | 必要な他機能 |
|---|---|
| 降水 | なし(単独で使える) |
| 遮断 | 降水 |
| 気象強制場 | なし(消費側の機能と組で使う) |
| 蒸発散(モード1) | なし |
| 蒸発散(モード2〜4) | 暦 date0_c(3, 4 は気象強制場・緯度も) |
| 積雪・融雪 | 降水+気象強制場 |

設定書式の実例は [examples/List_samples/](../../examples/List_samples/)
の list_precip / list_intercept / list_meteo / list_evap / list_snow を
参照してください。
