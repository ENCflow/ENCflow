# data_chichibu_50m — test/chichibu の 50 m 格子データ

荒川上流・秩父流域の 1120×600 セル(dx = dy = 50 m)の格子データ
(data_chichibu の 100 m データと同じ流域・同じ領域範囲。2×2 のブロック平均が
100 m の標高と rms 0.86 m で一致する)。developer.md §68.18 の解像度比較
(スキーム 1・3 × 動的振り替え)に使う。param50_*.txt を参照。

- `Chichibu_50m_filled.txt` — 標高(窪地処理済み)
- `Chichibu_50m_basin.txt` — 流域マスク(285,843 セル)
- `Chichibu_50m_river.txt` — 河道マスク(19,714 セル。100 m の河道セルはすべて
  50 m の河道セルを含む)

出典は data_chichibu と同じ(2026-10-03 に利用者から提供)。

## 500 m データ(data_chichibu_500m)

同じ領域の 112×60 セル(dx = dy = 500 m)。`Chichibu_500m_{filled,basin,river}.txt`
は 2026-10-03 に利用者から提供(5×5 ブロック平均の標高と rms 4.5 m で一致、
流域 2,870 セル)。提供された河道マスクは下流本流の 192 セルのみで、
100 m・200 m の河道網(測線 1〜3 を含む)と範囲が揃わないため、解像度比較には
100 m の河道マスクを 5×5 ブロックごとに集計し 3 セル以上を河道とした
`Chichibu_500m_river_from100m.txt`(1,270 セル)を使う(param500r_*.txt)。
提供マスクのままの結果(param500_*.txt)は上流が粗度 0.15 の斜面扱いになり
ピークが 1/3〜1/6 に落ちるので、スキーム比較には使わない。

200 m は tutorials/chichibu/data_chichibu を dir_data で参照する(param200_*.txt)。
