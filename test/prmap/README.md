# test/prmap — 降雨分布(prtype = 2・3)の時間の単位の検定

[English](en/README.md)

降雨分布ファイルの値が何分間の積算雨量か(`dt_mapunit(_c)`)と、分布ファイルの
時間間隔(`dt_maplist(_c)`)の解釈の検定です([ユーザーガイドの章](../../docs/users_guide/forcing.md)、
developer.md §88)。数値は分、単位付きの文字列 `_c` は単位どおり(単位を省いた
数値は分)、両方あれば `_c` が優先、どちらもなければ prtype = 2 は 24 時間の積算
(mm/day)・prtype = 3 はファイルの間隔、という仕様を `Check_prmap.py` で確かめます
(reference 比較なし)。

## 構成

4 × 8 セル(Δx = Δy = 10 m。np = 4 でもランクあたり 2 行)の平坦な閉領域に、
一様な雨を 1.5 h 与えます(dt = 10 s)。地表水は動かないので、Log の S(領域平均の
水深。`f_disp_debug = 1` で全有効桁)は降った雨の積算に等しくなります。prtype = 2 の
分布 `prmap.txt` は全セル 24 mm(倍率は 1 で一定)、prtype = 3 のリストは
`f1.txt`〜`f3.txt`(全セル 6、12、0 mm)です。

| 構成 | 指定 | 解釈 | 1.5 h の雨 |
|---|---|---|---|
| `param_p2_def.txt` | prtype = 2、指定なし | 24 時間の積算(mm/day)= 1 mm/h | 1.5 mm |
| `param_p2_min.txt` | `dt_mapunit = 60` | 60 分の積算 = 24 mm/h | 36 mm |
| `param_p2_c1h.txt` | `dt_mapunit_c = "1h"` | p2_min と同じ(Log がビット一致) | 36 mm |
| `param_p2_c60.txt` | `dt_mapunit_c = "60"` | 単位を省いた数値は分。p2_min と同じ | 36 mm |
| `param_p2_prio.txt` | `dt_mapunit = 60` と `dt_mapunit_c = "1d"` | `_c` が優先。p2_def と同じ | 1.5 mm |
| `param_p3_def.txt` | prtype = 3、`dt_maplist = 30` | 30 分ごとに切替、値は 30 分の積算 | 17.97 mm |
| `param_p3_c30.txt` | `dt_maplist_c = "30"` | 単位を省いた数値は分。p3_def と同じ | 17.97 mm |
| `param_p3_unit.txt` | `dt_maplist_c = "0.5h"`、`dt_mapunit = 60` | 30 分ごとに切替、値は 60 分の積算(mm/h) | 8.98 mm |

prtype = 3 のフレームの切替はステップの終わりの時刻で判定します(ステップ it は
時刻 it·dt を含むフレームを使う)。そのため最初のフレームだけ 1 ステップ短く
(1790 s)、p3_def の雨は 6 + 12 = 18 mm にわずかに届きません。

## 検定(Check_prmap.py)

- **S の積算**: 上の規則で各ステップの降水強度を積算した値と Log の S が相対 1e-9
  以内(Log の表示 14 桁の丸めは最小の S でも 3e-11。単位の取り違えは 24 倍・
  60 倍の差になる)。
- **別表現の一致**: 同じ時間を数値の分・単位付きの文字列・単位を省いた文字列で
  与えた構成、`_c` を優先させた構成の Log.txt が、対応する構成とビット一致。
- **採用値の表示**: 画面に `precip: dt_mapunit = 1440.00000 min (default)` などの
  採用値が出る。

## 実行

```bash
make
./Run.sh          # 逐次 8 構成 + 検定(数秒)
./Run_MPI.sh 4    # MPI(np ≤ 4)。検定に加え、全構成の Log.txt が逐次とバイト一致
```

## 検証記録(2026-10-27。gfortran 13.3 / Open MPI 4.1、Ubuntu 24.04)

修正前のコード(dt_mapunit を秒として扱う、dt_mapunit_c を既定値で上書きする、
dt_maplist_c がフレームの間隔に効かない)では、p2_min が 2160 mm(60 倍)、
p2_c1h・p2_c60 が 1.5 mm、p2_prio が 2160 mm、p3_c30 が 24.03 mm、p3_unit が
721 mm になり、表示の項目を含めて 21 項目が不合格。修正後は全項目が合格し、S の
最大の相対差は 2e-11(表示桁の丸め)。指定のない構成(p2_def・p3_def)の Log は
修正前とビット一致。MPI np = 1・2・4 の Log.txt は全構成で逐次とバイト一致。
