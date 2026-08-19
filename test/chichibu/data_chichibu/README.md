# data_chichibu — test/chichibu 用の実地形データ

荒川上流・秩父流域の 560×300 セル(dx = dy = 100 m)の格子データです
([tutorials/chichibu](../../../tutorials/chichibu/) の 200 m データと
同じ流域・同じ出典で、解像度が異なります)。

- `Chichibu_100m.txt` — 標高(原データ)
- `Chichibu_100m_filled2.txt` — 標高(窪地処理済み。計算に使用)
- `Chichibu_100m_basin.txt` — 流域マスク
- `Chichibu_100m_river.txt` — 河道マスク

データの由来: 標高データ(および流域マスク)は国土地理院の基盤地図情報
数値標高モデルより作成、河道マスクは国土数値情報河川データから作成された
河道位数データ
([DOI:10.3178/jjshwr.36.1812](https://doi.org/10.3178/jjshwr.36.1812))
より作成しています。
