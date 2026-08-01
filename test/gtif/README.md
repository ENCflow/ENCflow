# GeoTIFF リーダー用テスト資産(Phase 0)

docs/geotiff_plan.md の Phase 0 で整備した読みテスト用の GeoTIFF 一式。
Phase 1 で追加するリーダーの回帰テストが、ここの `data_gtif/*.tif` を読んで
`expected/*.txt` と比較する。

## 生成方法

    ./make_testdata.sh      # gdal_translate と python3 + tifffile が必要

値のソースは test/chichibu の実地形の切り出し(60x48)。位置・CRS は
テスト用の便宜値で、実在の場所とは対応しない。資産はコミット済みなので
通常は再実行不要。組合せを増やすときはスクリプトに追記して再生成する。

## data_gtif/ の内訳(17 ファイル)

ファイル名の規則: `<型>_<圧縮>[_pred<N>]_<配置>[_be|_geo|_bigtiff].tif`

| 軸 | カバーする値 |
|---|---|
| 画素型 | f32, f64, u8(Byte), i16, u16, i32, u32 |
| 圧縮 | none, LZW, Deflate, PackBits |
| predictor | 1(なし), 2(水平差分・整数), 3(浮動小数点) |
| 配置 | strip(60x34), tile(32x32。60x48 に対し端数タイルあり) |
| バイト順 | II(リトル), MM(ビッグ。`_be`) |
| 形式 | classic TIFF, BigTIFF(`_bigtiff`) |
| CRS | EPSG:6677(投影 100m 格子), EPSG:6668(経緯度 4 秒格子。`_geo`) |
| nodata | `f32_none_strip_geo.tif` のみ GDAL_NODATA=-9999 を持つ |

同じ型の変種はすべて同一の画素値を持つ(make_testdata.sh が自己検証)。

## expected/ の期待値(型ごとに 1 ファイル)

- ENCflow のテキスト行列と同じ「1 行 = 1 格子行」形式。
- 実数は %.17g で印字してある。f32→f64 の拡張は正確なので、この値を
  倍精度として読めば「リーダーが返すべき値(f32 を既定 real へ拡張した
  もの)」とビット同値になる(PREC=double の場合)。
- 整数は u8/i16/u16/i32/u32 それぞれの期待値(u16 は +40000 の
  オフセット入りで、符号なし 16bit のゼロ拡張を検査できる)。

## 未整備(Phase 1 以降で追加)

- **QGIS / ArcGIS の実出力サンプル**(ユーザー提供待ち)。提供され次第
  `data_qgis/`, `data_arcgis/` に期待値とともに追加する。ここの GDAL 生成分は
  QGIS 出力(GDAL 経由)の近似にはなるが、ArcGIS 固有のタグ構成は
  実物でしか検査できない。
- スパースタイル(タイルオフセット 0)、値が 2^31 を超える UInt32 の
  エラー経路、JPEG 等の対象外圧縮の停止メッセージ検査。
