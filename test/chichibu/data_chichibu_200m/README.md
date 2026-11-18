# data_chichibu_200m — 200 m 格子の解像度比較用データ

tutorials/chichibu/data_chichibu の 200 m データ(filled / basin / river の
テキスト形式)の複製に、サブグリッド河道幅の分布を加えたもの。
test/chichibu/param200_*.txt が参照する(developer.md §68.24)。

| ファイル | 内容 |
|---|---|
| Chichibu_200m_filled.txt / _basin.txt / _river.txt | tutorials/chichibu/data_chichibu と同一 |
| Chichibu_200m_cond.txt | 河床を整えた標高。Chichibu_200m_filled.txt の河道セル(Chichibu_200m_river_flowline.txt の 1,473 セル)を、10 m 格子の標高の谷底に合わせて作り直したもの(手順は [data_chichibu の README](../data_chichibu/README.md) の「河床を整えた標高」と同じ)。河道セルは全て下がる(下げた量の中央値 37.4 m、最大 134.7 m)。流下先と同じ高さのつながりは 446 本 → 25 本、逆勾配のつながりと窪地は 0。両脇の最も低いセルと河床の差の中央値は 48 m(developer.md §111 の比較の計算が使う) |
| Chichibu_200m_river_flowline.txt | 河道マスク(2,327 セル)を標高の落水線に載せ直したもの(1,473 セル。utils/river_flowline。tutorials/chichibu/data_chichibu と同一) |
| width200_50.txt / width200_100.txt | 河道セルに一様 50 m / 100 m の河道幅(壁なしのサブグリッド河道)。元の河道マスクのセル |
| width200_50_flowline.txt | 載せ直した河道マスクのセルに一様 50 m の河道幅(tutorials/chichibu の補足の W = 50 の計算が使う) |
