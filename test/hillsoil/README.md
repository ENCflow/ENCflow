# test/hillsoil — 斜面の土層(風化による土層生成)の検定

[English](en/README.md)

地形変化モジュールの基岩風化 = 土層生成(`&list_geomorph` の `f_wthr = 1`、
[ユーザーガイドの地形変化の章](../../docs/users_guide/geomorph.md)、式は
[解説 §7](../../docs/users_guide/sediment.md#7-基岩風化と隆起f_wthr--f_uplift))と、
その生成速度の倍率の分布 `fn_wthr`(developer.md §88.13)の検証ケースです。
土層厚 sd は dsd/dt = W exp(−sd/sd*)(W = W0 × 倍率)で増え、z は変わりません
(岩盤面 z − sd が下がる)。更新式は指数の厳密積分なので、解析解

  sd(T) = sd* ln(e^{sd0/sd*} + W T/sd*)

と刻みによらず丸めの水準で一致します。reference は持たず、解析解・バイト一致・停止の
表示で判定します。斜面の定常形(風化・深さ依存クリープ・隆起の釣り合い。
docs/mountain_stream_plan.md §11 の C2)は後で同じケースに足します。

台地は水のない平らな 8 × 12 セル(Δx = 1 m、z = 10 m)。W0 = 50 mm/kyr(既定値)、
sd* = 0.5 m、dt = 1 s を 100 ステップ、毎ステップの地形更新 × morfac 1e10(dts = 1e10 s)で
地形の時間 1e12 s(約 3.2 万年)。

| 構成 | ファイル | 内容 | 判定 |
|---|---|---|---|
| W1 一様 | `param_wthr_none.txt` | fn_wthr なし(全セル W = W0。従来の式) | 全セルで解析解と相対 1e-12、z が不変 |
| W1 分布 | `param_wthr_map.txt` | 倍率 m = 0.25 ((i + 4j) mod 9)(0〜2。`wmap.txt`。並びが 9 行周期でずれるので、帯の配布の行ずれを検出できる)、初期の土層厚 0〜0.3 m(`sdinit.txt`) | 全セルで解析解と相対 1e-12、倍率 0 のセルの土層厚と全セルの z が不変 |
| リスタート往復 | `param_wthr_map_rt1.txt` → `param_wthr_map_rt2.txt` | 分布の構成を 50 s で保存し 100 s まで継続(倍率の分布は再開時に読み直す) | 通し計算と state.dat がバイト一致 |
| 入力の誤り | `param_wthr_bad.txt` / `param_wthr_nof.txt` | 1 セル(i = 4, j = 11)だけ負の倍率(`wmap_bad.txt`)/ f_wthr なしで fn_wthr を与える | 初期化で「fn_wthr must be >= 0」/「fn_wthr requires f_wthr=1」で停止 |

| ファイル | 内容 |
|---|---|
| `make_init.py` | 倍率の分布・負の倍率の分布・初期の土層厚の生成(定数は `param*.txt`・`Check_hillsoil.py` と対で保守) |
| `Check_hillsoil.py wthr` | 上の判定(z・sd は save の state.dat から倍精度で読む) |
| `Run.sh` / `Run_MPI.sh N` | 全構成の実行と検定。MPI は逐次の save(`save_*_serial`)とバイト比較。負の倍率のセルは最後の行の帯にあり、そのランクだけが検出しても全ランクが停止することを見る |

## 実行

```bash
make
python3 make_init.py wmap > wmap.txt   # 入力の再生成(同梱。変更したときだけ)
./Run.sh            # 逐次(1 秒未満)
./Run_MPI.sh 4      # MPI(Run.sh の後に。save_*_serial とバイト比較)
```

## 検証記録(2026-10-27。gfortran 13.3 / Open MPI 4.1、既定の -Ofast ビルド)

- W1: 解析解との max 相対誤差は分布 1.6e-15・一様 6.2e-16(許容 1e-12)。倍率 0 の
  11 セルは土層厚が不変、全セルで z が不変。
- リスタート往復はバイト一致。入力の誤りの 2 構成は初期化で停止。
- np = 1, 2, 4 で逐次とバイト一致、同じ検定に PASS。-fcheck=all の np = 2 も PASS。
- fn_wthr を与えない経路は、fn_wthr の追加の前の実行ファイルと state.dat がバイト一致
  (-O2)。全セル 1 の分布も未指定とバイト一致(-O2。規格の保証ではないので検定には入れない)。
