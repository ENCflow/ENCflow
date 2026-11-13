# data_chichibu — test/chichibu 用の実地形データ

荒川上流・秩父流域の 560×300 セル(dx = dy = 100 m)の格子データです
([tutorials/chichibu](../../../tutorials/chichibu/) の 200 m データと
同じ流域・同じ出典で、解像度が異なります)。

- `Chichibu_100m.txt` — 標高(原データ)
- `Chichibu_100m_filled2.txt` — 標高(窪地処理済み。計算に使用)
- `Chichibu_100m_basin.txt` — 流域マスク
- `Chichibu_100m_river.txt` — 河道マスク(元のデータ。9,582 セル。developer.md §68 の派生実験の
  param_*.txt が使う)
- `Chichibu_100m_river_flowline.txt` — 河道マスクを、窪地処理済みの標高の落水線に載せ直したもの
  (6,515 セル。[utils/river_flowline](../../../utils/river_flowline/README.md)。回帰ケース param.txt と
  test/chichibu_icmap が使う)
- `width_chichibu50.txt` / `width_chichibu100.txt` — 元の河道マスクのセルに一様 50 m / 100 m の河道幅
  (サブグリッド河道の派生実験 param_w*.txt が使う)
- `width_chichibu50_flowline.txt` — 載せ直した河道マスクのセルに一様 50 m の河道幅(tutorials/chichibu の
  補足の W = 50 の計算が使う)

データの由来: 標高データ(および流域マスク)は国土地理院の基盤地図情報
数値標高モデルより作成、河道マスクは国土数値情報河川データから作成された
河道位数データ
([DOI:10.3178/jjshwr.36.1812](https://doi.org/10.3178/jjshwr.36.1812))
より作成しています。河道位数データをラスタにした河道マスクは、セルの 38 % が標高の谷線(落水線)から
外れた谷壁のセルで、谷線の上で切れている所が 529 セルあります(developer.md §109)。
