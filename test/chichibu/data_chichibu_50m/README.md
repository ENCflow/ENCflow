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
