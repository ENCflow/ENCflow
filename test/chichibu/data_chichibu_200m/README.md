# data_chichibu_200m — 200 m 格子の解像度比較用データ

tutorials/chichibu/data_chichibu の 200 m データ(filled / basin / river の
テキスト形式)の複製に、サブグリッド河道幅の分布を加えたもの。
test/chichibu/param200_*.txt が参照する(developer.md §68.24)。

| ファイル | 内容 |
|---|---|
| Chichibu_200m_filled.txt / _basin.txt / _river.txt | tutorials/chichibu/data_chichibu と同一 |
| Chichibu_200m_river_flowline.txt | 河道マスク(2,327 セル)を標高の落水線に載せ直したもの(1,473 セル。utils/river_flowline。tutorials/chichibu/data_chichibu と同一) |
| width200_50.txt / width200_100.txt | 河道セルに一様 50 m / 100 m の河道幅(壁なしのサブグリッド河道)。元の河道マスクのセル |
| width200_50_flowline.txt | 載せ直した河道マスクのセルに一様 50 m の河道幅(tutorials/chichibu の補足の W = 50 の計算が使う) |
