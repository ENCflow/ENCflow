# test/gwdefault — 地下水モジュールの既定値の同値検定

地下水モジュール(`&list_gwflow` 系)の物性・校正値に既定値を与えた
方針(developer.md §64)の検定です。4 つの構成それぞれについて、
**最小入力**(既定値を省略した `param_<tag>.txt`)と**既定値をすべて明示**
した `param_<tag>x.txt` を実行し、save の全ファイル(state.dat と各
モジュールの私有ファイル)と Log.txt がバイト一致すること、画面に
"(default)" が期待どおりの行数(18 行)表示されることを検定します。
図はありません(同一性の検定)。

## 構成

共通: 40 × 20 セルの閉領域斜面(`z.txt`)、初期水 0.05 m、dt = 0.2 s、900 s。

| 構成 | 有効化 | 省略 → 既定が表示される値 |
|---|---|---|
| a | バケツ(`f_gwvertical = 1`) | gw_infil_mmh = 10 mm/h、gw_capacity = 0.2 m |
| b | Green-Ampt + 側方流動 + 風化基岩層(`f_gwlayer2 = 1`) | sd0 = 1 m、gw_ksv_mmh = 10、gw_psif = 0、gw_ksh_mmh = 360、gw2_depth = 3 m、gw2_sy = 0.05、gw2_infil_mmh = 1 |
| c | Green-Ampt + 凍土(`f_gwfrost = 1`、`fn_meteo`) | sd0、gw_ksv_mmh、gw_psif、fro_fifull = 20 ℃·day |
| d | Green-Ampt + 管路連続体層(`f_gwconduit = 1`、浸入水 `gwc_leak_layer = 1`) | sd0、gw_ksv_mmh、gw_psif、gwc_cap = 0.01 m、gwc_depth = 3 m、gwc_sy = 0.05、gwc_slot_sy = 1e-3、gwc_leak_mmh = 10 |

構成 d では `gwc_inlet`(枡密度)と `gwc_cnd_m2s`(通水能密度)は与件です
(0 が「側方なし」「交換なし」の明示になるため既定を置かない)。

| ファイル | 内容 |
|---|---|
| `Run.sh` | 4 構成 × 2 を実行し、`diff -r save_<tag> save_<tag>x` と `cmp Log.txt`、"(default)" 行数 = 18 を検定 |
| `Run_MPI.sh N` | 同じ対を N ランクで実行して同じ比較(np = 2, 4 でバイト一致) |

## 実行

```bash
make
./Run.sh          # 8 ラン(数十秒)。すべてバイト一致で PASS
./Run_MPI.sh 4
```

## 所見

| 構成 | save / Log のバイト一致 | "(default)" 行 |
|---|---|---|
| a バケツ | 一致 | 2 |
| b Green-Ampt + 側方 + 層 2 | 一致 | 7 |
| c Green-Ampt + 凍土 | 一致 | 4 |
| d Green-Ampt + 管路層 | 一致 | 5 |
| 合計 | PASS | 18(期待 18) |

- 既定値の根拠(土性別の Green-Ampt パラメータ、森林土壌の土層厚、
  Stefan 式の凍結深など)は developer.md §64 の表にまとめられています。
  既定値を変えるときは、この表と `param_<tag>x.txt` の明示値を対で
  更新してください。
- 既存の reference はすべて明示指定なので、既定値の導入では不変です。
- 同じ型の検定: [test/icevap](../icevap/)(遮断・蒸発散)、[test/lava](../lava/)
  構成 3、[test/glacier](../glacier/) 構成 3、[test/tide](../tide/) 構成 2、
  [test/driftwood](../driftwood/) / [test/bldgdebris](../bldgdebris/) の構成 4 / 5。

## 関連文書

- [docs/users_guide/gwflow.md](../../docs/users_guide/gwflow.md) — 「とりあえず動かしてみる(最小入力)」と各パラメータの既定
- developer.md §62(既定値方針)、§64(gwflow の既定値の表と検証)
