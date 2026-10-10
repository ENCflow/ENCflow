# test/nest_identity — 比 1:1 の自己ネストの恒等テスト

ネスティング(docs/users_guide/nest.md、docs/nesting_plan.md)の検証の要。
子を親の部分領域と同じ格子(比 1:1、dt 同一)にすると、帯の補間は恒等写像
(親の値をそのまま置く)になり、**子の内部(帯を除く)は親の同じセルと
ビット一致**するはずである。これを `nestcheck`(nestcheck.f90。m_main を使う
検証ドライバ)が毎ステップ・全セルで検査する。双方向(nest_fb ≥ 1)では
置換も恒等になるので、加えて**ルートの最終状態が単独ランとバイト一致**する
こと(save の state.dat / swflow_enc.dat の cmp)を見る。格子の取り違え・行順・
ハロ・時間補間・置換のバグは、ここで ULP 0 の不一致として機械的に現れる。

![恒等ケースの構成](figs/identity.png)

## 実行

```
./Run.sh            # 逐次
./Run_MPI.sh 2      # MPI 2 ランク(np=1, 2, 4 とも逐次と同じ結果になること)
```

本体は Run_nest.sh(nestcheck をビルドし、ケースを順に走らせる)。

## ケース

| ケース | 親 / 子 | 何を見るか | 判定 |
|---|---|---|---|
| wave_s1 / wave | wave 385²、子 121²(親セル 133..253)。移流スキーム 1(帯 2)/ 3(帯 3) | 一方向の帯 Dirichlet。初期水深は単独格子から切り出す(`nestcheck cut`) | 子の内部 == 親(ULP 0) |
| restart | wave_s1 を t = 4 s で保存・再開(格子ごとに dir_save) | ネスト系の save/restore | 再開後も恒等。Log の行が中断なしランと字句同一 |
| chichibu | 実地形 500 m、112×60、子 60×40(親セル 20..79 × 10..49)、1 時間 | 乾湿・流出・河道のある地形での帯 | 子の内部 == 親 |
| wave_tw / chichibu_tw | 上の 2 構成を双方向(nest_fb = 2)に | 置換の恒等 | 子の内部 == 親、かつルートの最終状態 == 単独ラン(cmp) |
| wave_fb3 / chichibu_fb3 | 保存修正(nest_fb = 3) | 比 1 では修正量が厳密に 0 | 同上 |
| chichibu_gw | 地下水バケツを親子で有効に | 場の表(hg 等)の帯と置換 | 同上 |
| flather | 親は静水(385²)、子 201²(親セル 93..293)に自前の水の山、4 辺が放射(f_bc_* = 2)、一方向 | Flather(nest_bc = 3)の退化: 親が静水なら η_e = 基準・u_n,e = 0 で現行の放射境界に一致 | 子の Log == 単独ラン(放射境界のみ)の Log(cmp) |
| nh | 親子とも非静水圧(CG、nh_tol = 1e-12、全域解)、一方向 | 帯のセルを親の φ の既知セルに(nest_nh = 1) | 子の内部 == 親、許容差 1e-10(CG の反復列が領域依存のためビット一致ではない。実測 2e-13 m) |
| nh0(対照) | 同上で nest_nh = 0(帯 + 余白を静水圧) | 一致しないことの確認(表示のみ) | 実測 max|dh| 1.4e-2 m |
| nha(表示のみ) | 子だけ活性集合(f_nh_adaptive = 1)、親は全域解 | 活性集合の切り捨て誤差(帯に接するセルは親の φ で種に加わる) | 実測 max|dh| 3.0e-4 m |

- nestcheck の引数: `run <root param> <i0> <j0> <nb> [tol]`。`cut <single param> <i0> <j0> <nxc> <nyc> <out>` は単独格子の初期水深から子の初期水深ファイルを切り出す。chichibu の地形類は cut_chichibu.py で切り出す(data_chichibu_child/)。
- 図は `./Fig.py` で figs/identity.png に生成する(模式図。データ不要)。
- BMI 越しの同じ恒等(格子の区別・置換・再 initialize)は test/bmi_nest。
