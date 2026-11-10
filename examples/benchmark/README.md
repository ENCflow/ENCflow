# benchmark — 降雨流出の基準問題(理論解との比較と、格子の向き・近傍の数の確認)

[English](en/README.md)

浅水流と降雨だけを使い、既定の設定のまま、よく知られた形の流域に一様な雨を降らせる
2 題です。他の例題のように現象を見せるものではなく、**計算の基本的な精度と ENC 格子の
性質を数字で確かめる**ための例題で、どちらも格子間隔 20・10・5 m、格子に対する流域の
向き 0° と 45°、ENC の 8 近傍(既定)と 4 近傍(`p_diagratio = 0`)を比べます。

| ケース | 内容 | 比べるもの |
|---|---|---|
| [v-shaped/](v-shaped/) | 幅 20 m の水路に両側 800 m の斜面が集まる V 字流域(1000 m)に 10.8 mm/h の雨を 90 分。Tada (2026) の検証問題で、Overton & Brakensiek (1973)・Di Giammarco ら (1996) 以来、多くの 2 次元モデルの検証に使われてきた降雨流出の標準問題 | 出口と斜面の脚の流量を運動学的波の理論解と比べる(`analytic.py` が計算、`check.py` が合否を付ける)。補足で力学波・拡散波・運動波の違い |
| [v-valley/](v-valley/) | 水路のない V 字谷(谷の勾配 0.02、斜面の勾配 0.01〜0.04、幅 1620 m × 長さ 1000 m)に 10.8 mm/h の雨を 60 分 | 向き 0° の結果を基準に、45° に傾けた格子の流出を比べる。4 近傍では谷底のセルの 4 つの隣がすべて高い疑似窪地ができて流出が遅れる(その深さは (√2/2)(S_S − S_V) Δx) |

どちらも入力(地形・粗度・マスク)は `make` が Python で生成し、ケースごとの設定ファイルは
注釈付きの雛形 `param.txt` から生成します。実行の型は他の例題と同じです。

```bash
cd examples/benchmark/v-shaped     # または v-valley
make                               # リンク・入力・設定(v-shaped は理論解も)
make run                           # 全ケース(v-shaped 19 ケース 40 分ほど、v-valley 19 ケース 25 分ほど。4 スレッド)
python3 check.py                   # 理論解・基準との差と水収支の表(合否つき)
python3 plot_results.py            # 図 figs/*.png(引数 en で英語版を en/figs/ に)
```

できないこと: この 2 題は浅水流 + 降雨の核だけを見ます。浸透・遮断・河道の機能・構造物・土砂は
使いません。理論解は運動学的波の近似(水路は特性曲線の数値積分)で、浅水方程式の厳密解では
ありません。実際の流域の観測との照合は含みません。回帰テストの reference は持たず、合否は
`check.py` の目安(理論解との正規化二乗平均平方根誤差など)で判定します。

関連: 一様平面斜面の運動学的波との比較と粗い格子の V 字集水域は [test/hillslope](../../test/hillslope/)、
通過幅の調整(開口の振り替え)の検定の一覧は[通過幅の調整](../../docs/users_guide/passage_width.md)、
ENC 格子の原論文は Tada (2026)[^tada26]。

[^tada26]: Tada, T. (2026): An eight-neighborhood connected collocated grid scheme for overland flow simulation. *Hydrological Research Letters*, 20(2), 113–118. doi:10.3178/hrl.25-00052.
