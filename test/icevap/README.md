# test/icevap — 降雨遮断・蒸発散の既定値の同値検定

降雨遮断(`fn_intercept`)と蒸発散(`fn_evap`)の物性値に既定を与えた
方針(developer.md §66)の検定です。3 つの構成で、最小入力(既定値を
省略)と既定値を明示した入力の save と Log.txt がバイト一致し、画面に
"(default)" が 3 行表示されることを検定します。
[test/gwdefault](../gwdefault/) と同じ型で、図はありません。

## 構成

共通: 40 × 20 セルの閉領域斜面(`z.txt`)、dt = 0.2 s、900 s。

| 構成 | 有効化 | 省略 → 既定が表示される値 |
|---|---|---|
| e | 固定遮断率(`f_icmodel = 1`)、降雨 36 mm/h | ic_alpha = 0.15 |
| f | 初期損失(`f_icmodel = 2`)、降雨 36 mm/h | ic_smax_mm = 1.5 mm |
| g | 一定蒸発散(`f_evmodel = 1`)、初期水 0.05 m | evap0 = 3.0 mm/day |

| ファイル | 内容 |
|---|---|
| `param_e.txt` / `param_ex.txt`、`param_f.txt` / `param_fx.txt`、`param_g.txt` / `param_gx.txt` | 最小入力 / 既定値の明示 |
| `Run.sh` | 3 対を実行し、`diff -r save_<tag> save_<tag>x`、`cmp Log.txt`、"(default)" 行数 = 3 を検定 |
| `Run_MPI.sh N` | 同じ対を N ランクで実行 |

## 実行

```bash
make
./Run.sh          # 6 ラン(数十秒)。すべてバイト一致で PASS
./Run_MPI.sh 4
```

## 所見

| 構成 | save / Log のバイト一致 | "(default)" 行 |
|---|---|---|
| e 固定遮断率 | 一致 | `intercept: ic_alpha = 0.1500 (default)` |
| f 初期損失 | 一致 | `intercept: ic_smax_mm = 1.5000 mm (default)` |
| g 一定蒸発散 | 一致 | `evap: evap0 = 3.0000 mm/day (default)` |

- 既定値の根拠(遮断率 0.15、初期損失 1.5 mm、蒸発散 3 mm/day)は
  developer.md §66 の表にあります。既定を変えるときは表と `param_*x.txt`
  を対で更新してください。
- 遮断・蒸発散の使い方は [tutorials/chichibu](../../tutorials/chichibu/README.md) の
  Step 5(降雨遮断と地下浸透)が教材です。

## 関連文書

- [docs/users_guide/forcing.md](../../docs/users_guide/forcing.md) — 降雨遮断・蒸発散の設定
- developer.md §62(既定値方針)、§66(intercept・evap・lavaflow の既定値と検証)
