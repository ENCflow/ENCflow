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

## テストの実行

    ./Run.sh        # ../../make.inc の設定でビルドして実行(逐次)

test_gtif_reader が data_gtif/ の全変種を読み、expected/ とのビット一致・
未対応形式のエラー停止・メタ情報(位置・CRS・nodata)を検査する。
Deflate 系(u16_deflate_tile 等)は Phase 2 まで「エラーになること」を
検査し、対応後に値比較へ切り替える。

## data_user/(QGIS / ArcGIS Pro の実出力。2026-08-01 受領)

ユーザー提供の実データ(約 1000m 格子の標高)。期待値は expected_user/ に
tifffile(参照実装)の読み戻しで生成し、同一格子の全変種が互いに値一致
することを検査済み。由来: `src/1000m.bil`(+hdr)が経緯度版の原本で、
d4326_f32 系の tif と全画素ビット一致(`src/D4326.txt` は 3 桁丸めの
書き出しなので厳密には一致しない)。D2451 系はその 9 系投影版。

| ファイル(改名後) | 元名 | 実態 |
|---|---|---|
| d2451_f32_arc_none | D2451_f32_Arcなし | f32 無圧縮 tile。GeoKey に 4612+2451 併記(ArcGIS 固有) |
| d2451_f32_arc_lzw | D2451_f32_ArcLZW | f32 LZW tile |
| d2451_f32_qgis_std | D2451_f32_QGIS標準 | f32 無圧縮 strip |
| d2451_f32_qgis_deflate | D4326_f32_QGIS高圧縮 | **中身は 2451 格子**のため改名。Deflate+pred2(Phase 2 で値比較へ) |
| d2451_i16_qgis_std | D2451_i16_QGIS標準 | i16。nodata が実数文字列(-3.4e38) |
| d4326_f32_arc_none / arc_lzw | D4326_f32_Arcなし/ArcLZW | f32 tile(EPSG:4326) |
| d4326_f32_qgis_std | D4326_f32_QGIS標準 | f32 無圧縮 strip |
| d4326_i16_arc_none / arc_lzw | D4326_i16_Arcなし/ArcLZW | i16 tile(arc_lzw は再アップロード版=LZW) |
| d4326_i8_arc_lzw | D4326_i8_ArcLZW | i8 LZW tile(再アップロードで追加) |
| d4326_i16_qgis_std / qgis_deflate | D4326_i16_QGIS標準/高圧縮 | i16 strip(高圧縮は Deflate+pred2) |
| d4326_i8_qgis_std | D4326_i8_QGIS標準 | i8(符号付き 8bit) |

よく使う CRS は JGD2000 平面直角 9 系(EPSG:2451)とのこと。
書き込み(Phase 3)の GeoKey 検証はこれを主対象にする。

## 未整備(Phase 2 以降で追加)

- Deflate 対応後、`*_deflate*` のテストを「エラー検査」から値比較へ切り替える。
- スパースタイル(タイルオフセット 0)、値が 2^31 を超える UInt32 の
  エラー経路、JPEG 等の対象外圧縮の停止メッセージ検査。
