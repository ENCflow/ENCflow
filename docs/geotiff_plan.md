# GeoTIFF 対応の検討(自作ライブラリの実現可能性と実装形態)

status: GeoTIFF 本体は検討段階(実装未着手)。前提となる座標管理は
先行導入済み(§10)。合意後、決定事項は developer.md に転記し、
本文書は実装計画として消し込んでいく。

## 0. 結論(要約)

- **自作は現実的に可能**。GeoTIFF は「TIFF 6.0 + 位置情報タグ数個」であり、
  対象を「QGIS/ArcGIS 産の1バンド実数・整数ラスタ」に限定すれば、
  読み書き合わせて概ね 2,000〜2,500 行の規模。外部ライブラリは不要。
- **純 Fortran で完結できる**。必要なのは stream アクセス I/O、
  `transfer`・ビット演算・`iso_fortran_env` の固定 kind だけで、
  全て F2008 標準。対応コンパイラ全系列(ifx/gfortran/nvfortran/
  flang/nfort)で追加要件なし。C 案は保険(§4.3)に格下げでよい。
- **最大の山は Deflate(inflate)の実装**(約 500 行)。ArcGIS Pro の
  既定圧縮が LZ77(=Deflate)のため回避できない。ただし既知の
  アルゴリズムの素直な実装であり、テストベクタも容易に作れる。
- **実装形態は「src/ 直下に m_geotiff* を置き、同じ Makefile /
  libencflow.a に組み込む」を推奨**(案A)。別ディレクトリ+独立
  Makefile(案B)は PREC/ABI 整合とスタンプ機構を二重化することになり
  不利(§5)。
- 書き込みには格子原点座標と EPSG コードが必要。→ ESRI hdr ベースの
  座標管理を先行導入して解決済み(§7, §10)。

## 1. 要件の確定

- 読み込み: QGIS および ArcGIS(Pro)で作成された、1バンドの
  実数または整数のラスタが読めること。
- 書き込み: QGIS および ArcGIS で正しく読める(位置・値・nodata を含む)
  こと。
- あらゆる GeoTIFF への対応は不要。対象外のものは**明確なエラーメッセージで
  停止**する(黙って誤読しない)ことを対応範囲の定義とする。

## 2. 対応すべき仕様範囲の分析

### 2.1 TIFF 構造の要点(読み書き共通の土台)

- ヘッダ 8 バイト(バイト順 II/MM + magic 42 + 先頭 IFD オフセット)。
- IFD = タグの表(1 エントリ 12 バイト: tag, type, count, value/offset)。
- 画素データは strip(行帯)または tile(矩形)単位に分かれ、
  各断片のオフセットとバイト数がタグで示される。
- 構造自体は小さく、必要タグは 20 個弱(§6.2)。

### 2.2 読み込み側で実際に遭遇するバリエーション

QGIS/ArcGIS の出力は GDAL 経由であり、既定値と代表的な設定を
押さえれば実用上カバーできる。

| 項目 | 遭遇する範囲 | 対応方針 |
|---|---|---|
| 圧縮 | 無圧縮 / LZW / Deflate / PackBits。**ArcGIS Pro の既定は LZ77=Deflate**、QGIS の既定は無圧縮だが「高圧縮」プロファイルは Deflate、手動選択で LZW も頻出 | 4 方式とも対応(必須) |
| predictor | 1(なし)/ 2(水平差分)/ 3(浮動小数点) | 3 方式とも対応(復号後の後処理で小さい) |
| 配置 | strip / tile(ArcGIS Pro は tile が既定) | 両対応(必須) |
| 画素型 | Byte, Int16, UInt16, Int32, UInt32, Float32, Float64 | 全対応し、整数は既定 integer へ、実数は既定 real へ変換。unsigned は int64 経由でゼロ拡張 |
| バイト順 | ほぼ II(リトル)だが MM も規格内 | 両対応(読み時スワップ) |
| BigTIFF | 4GB 超で GDAL が自動生成(magic 43、オフセット 8 バイト) | 読みのみ対応(差分は小さい)。全国 100m 級を見据えると読みは必須 |
| 複数 IFD | 内部オーバービュー(ピラミッド)が後続 IFD に入ることがある | 先頭 IFD(最高解像度)のみ読む |
| スパース | GDAL は未書き込みタイルの offset=0 を許す | offset=0 は nodata 充填として扱う |
| 帯数・表色 | 1バンド・グレースケール以外(RGB, palette, JPEG, YCbCr 等) | 対象外。タグ検査で明示的にエラー |
| 付随ファイル | .ovr, .aux.xml, ワールドファイル | 無視してよい(位置情報は本体タグから取る) |
| nodata | GDAL_NODATA タグ(42113, ASCII) | 読み取ってメタ情報として返す |

行順について: TIFF の行 1 は北端であり、ESRI BIL / ASCII grid と同じ
並びである。既存の read の j ループ規約(j=1 が先頭行)とそのまま対応し、
**上下反転は不要**(既存 txt/bil 入力と同じ約束で格納される)。

### 2.3 書き込み側(こちらは大幅に簡単)

QGIS/ArcGIS(GDAL)は素直な TIFF なら何でも読むため、書きは最小構成で
確実に通る:

- 無圧縮・strip・1バンド、Float32(実数)/ Int32(整数)、リトルエンディアン。
- 位置情報は ModelPixelScaleTag(33550)+ ModelTiepointTag(33922)の
  2 タグ、CRS は GeoKeyDirectoryTag(34735)に EPSG コードを 3〜4 キー
  (ModelType, RasterType, ProjectedCSTypeGeoKey または
  GeographicTypeGeoKey)入れるだけでよい。
- nodata は GDAL_NODATA(42113)に ASCII で書く(QGIS/ArcGIS とも認識)。
- EPSG 未指定時は GeoKey を省略して書く(QGIS は「不明な CRS」として
  読み込め、表示・重ね合わせは手動指定で可能)。
- 書きは classic TIFF のみとし、4GiB を超える場合はエラーで停止
  (BigTIFF 書きは必要になってから。§8 Phase 4)。

## 3. 規模見積り

| 部品 | 内容 | 目安 |
|---|---|---|
| TIFF/IFD 読み | ヘッダ・IFD 解析、タグ検査、strip/tile 走査、型変換、エンディアン | 700〜1,000 行 |
| LZW 復号 | TIFF 版 LZW(可変長コード、ClearCode) | 200 行 |
| PackBits 復号 | 単純 RLE | 50 行 |
| Deflate 復号 | 固定/動的ハフマン+LZ77 窓(zlib ヘッダ含む) | 400〜600 行 |
| predictor 復元 | 水平差分・浮動小数点(byte-shuffle)の逆変換 | 100 行 |
| 書き込み | 無圧縮 strip + GeoKey 生成 | 300〜400 行 |
| 合計 | | 約 2,000〜2,500 行 |

参考: m_fileio.f90 が約 460 行、m_swflow_enc 系が数千行であり、
リポジトリ内の1機能モジュールとして異常な規模ではない。

## 4. 実現可能性の評価

### 4.1 純 Fortran で足りるか → 足りる

- バイト列アクセス: `access='stream'` + `int8` 配列読み。
- 型再解釈: `transfer`(real32/real64 ↔ 整数)。
- ビット演算: `iand/ior/ishft/ibits`(LZW・Deflate のビットリーダに十分)。
- unsigned 非対応の言語仕様は、int64 に拡張してから扱うことで回避
  (UInt32 最大値も int64 に収まる)。
- いずれも F2008 標準機能で、make.inc の全コンパイラ(NEC nfort 含む)で
  利用可能。コンパイラ依存の拡張は使わない。

### 4.2 リスク(難所)

1. **Deflate 実装の正しさ**: 最大の作業量。ただし入出力が完全に決定的で、
   `gdal_translate`/gzip で任意のテストベクタを量産できるため、
   検証は容易。実装は RFC 1951 の素直な逐次実装でよい
   (性能は初期読み込みのみなので二の次)。
2. **仕様の裾野**: 「QGIS/ArcGIS 産」でも設定次第で対象外
   (JPEG 圧縮等)はあり得る。→ 対応範囲外は必ず「タグ○○が値△△:
   未対応」と報告して停止する設計にし、実害を運用で回収する。
3. **エンディアン・型変換のバグ**: 小さな reference tiff 一式
   (型×圧縮×配置の組合せ)をコミットして回帰テスト化する(§8)。

### 4.3 C 言語案の位置づけ → 保険に格下げ

C で書く(または miniz 等の実装をベンダリングする)利点は Deflate を
既製コードで済ませられる点のみ。一方で

- make.inc に C コンパイラの系列(ifx↔icx, nfort↔ncc, …)と
  Fortran/C 混合リンクの流儀が加わり、ビルド構成の複雑さが恒久的に増す。
- iso_c_binding 境界の分だけテスト・デバッグ面も増える。

ため、**基本は純 Fortran とし、万一 Deflate の自作が行き詰まった場合の
撤退先として「miniz をベンダリングして inflate のみ C に置き換える」を
予備案に置く**。モジュール分割(§6.1)で inflate を独立させておけば、
この差し替えは局所で済む。

## 5. 実装形態の比較と推奨

- **案A: src/ 直下に m_geotiff*.f90 を置き、src/Makefile(LIBOBJS)に
  追加する** — 推奨。
- 案B: src/ 下または ENCflow 直下に別ディレクトリ+独立 Makefile を作り、
  ライブラリとしてリンクする。

判断理由:

1. **PREC/ABI 整合**。公開インターフェースは m_fileio と同様に既定
   real/integer で切る(§6.3)ため、本体と同一の RFLAG でコンパイル
   しなければならない。案A なら src/Makefile のスタンプ機構
   (MODE/PREC 切替検出)がそのまま効く。案B は同じ仕組みを別 Makefile に
   複製することになり、make.inc 冒頭の「.mod/ABI 互換のため PREC を含めて
   必ず同一に」という注意点の違反を作り込みやすい。
2. **再利用**。utils/ 群は libencflow.a をリンクする既存経路があるため、
   案A なら追加の配管なしで前処理ユーティリティからも GeoTIFF を使える。
3. **既存様式との一致**。「1モジュール=1ファイル、src/ にフラットに置き、
   依存は Makefile に手書き」という現行様式(developer.md §3)の範囲内で
   済み、新しいビルド規約を導入しない。
4. 案B の利点(単体で切り出せる・名前空間の分離)は、モジュール名接頭辞
   m_geotiff* と「ENCflow 本体に依存しない」設計(§6.1)で実質的に
   達成できる。

将来他プロジェクトへ切り出したくなった場合も、依存ゼロの 3 ファイルを
コピーするだけなので、案A が障害になることはない。

## 6. モジュール構成と API 案

### 6.1 ファイル構成(3 ファイル、相互依存は一方向)

```
src/m_geotiff.f90          公開 API。ヘッダ/IFD の解析・検査、strip/tile
                           走査、型変換、書き込み(GeoKey 生成含む)
src/m_geotiff_codec.f90    PackBits・LZW の復号、predictor 復元
src/m_geotiff_inflate.f90  Deflate(zlib/raw)の復号のみ
```

- **ENCflow 本体のどのモジュールにも依存しない**(m_parallel にも
  依存しない)。エラーは stat とメッセージ文字列で返し、abort するか
  どうかは呼び出し側(m_fileio)が決める。これは list_*/m_* の層契約
  (developer.md §12)と同じ発想で、rank0 以外から呼ばれても安全になり、
  utils からの再利用も阻害しない。

### 6.2 対応タグ(読みの検査対象)

ImageWidth(256), ImageLength(257), BitsPerSample(258), Compression(259),
PhotometricInterpretation(262), StripOffsets(273), SamplesPerPixel(277),
RowsPerStrip(278), StripByteCounts(279), PlanarConfiguration(284),
Predictor(317), TileWidth/TileLength/TileOffsets/TileByteCounts(322–325),
SampleFormat(339), ModelPixelScaleTag(33550), ModelTiepointTag(33922),
GeoKeyDirectoryTag(34735), GeoDoubleParams(34736), GeoAsciiParams(34737),
GDAL_NODATA(42113)。未知タグは無視、既知タグの未対応値はエラー。

### 6.3 公開 API 案

```fortran
type :: t_gtif_info                  ! 読み取りメタ情報
  integer :: nx, ny
  logical :: is_real                 ! 実数系か整数系か
  logical :: has_nodata
  real    :: nodata
  logical :: has_georef
  real(real64) :: x0, y0, csx, csy   ! 北西隅セル外縁と セル寸法
  integer :: epsg                    ! 0 = 不明/未記載
end type

! 検査+メタ取得(読み込み前の格子整合チェック用)
subroutine gtif_inquire(fname, info, stat, msg)
! 全域読み(a は既定 real / 既定 integer の総称)
subroutine gtif_read(fname, nx, ny, a, stat, msg [, info])
! 全域書き(実数は Float32、整数は Int32 で格納)
subroutine gtif_write(fname, nx, ny, a, georef, nodata, stat, msg)
```

### 6.4 m_fileio / m_sysparam への組み込み

- m_fileio に `e_fmt_gtif` を追加し、fileio_read_matrix /
  fileio_write_matrix の select case に分岐を足す(既存シグネチャ不変。
  gtif_read のエラーはここで par_abort に変換)。
- m_sysparam の f_input_mode / f_output_mode の namelist 文字列に
  "gtif" を追加。出力は e_fmt_both 同様の組合せ指定も検討
  (txt+gtif 等が要るかは運用で判断)。
- 読み時は info%nx, ny を namelist の nx, ny と突き合わせ、不一致は
  エラーにする(txt/bil には無かった自己記述性の利点)。
- fileio_un_open / fileio_un_read_matrix(precip の逐次読み)は
  当面 gtif 対象外とし、指定されたらエラー(§8 Phase 4 で multi-IFD
  読みとして拡張可能)。

## 7. 地理参照情報の追加(書き込みの前提)

**→ §10 の座標管理の先行導入で解決済み。** 原点座標は入力(ESRI hdr、
将来は GeoTIFF タグ)から取得して t_geoinfo%gr(t_georef)が保持し、
CRS は namelist の `epsg`(導入済み。既定 0=不明)で与える。
座標未管理のまま GeoTIFF 出力を指定した場合は警告して停止する仕様
(§10 条件1)。テキスト入力に namelist で原点座標(xll/yll 等)を
与える口は現状なし。必要になった時点で追加を検討する。

## 8. 段階的実装計画と検証

各フェーズは独立にコミット・検証できる。全フェーズ共通の合否判定は
「機能追加 → gtif を使わない設定で既存 reference とビット一致」
(CLAUDE.md 規律2)。gtif は入出力の末端のみで計算経路に一切触れない
ため、無効時等価は構造的に自明に保てる。

- **Phase 0: テスト資産の整備**。gdal_translate で test/wave の地形等から
  小さな reference tiff 一式(型×圧縮×strip/tile×エンディアンの代表
  組合せ、数 KB×十数個)を生成してコミット。読みの回帰テストは
  「tiff を読んで既存 txt reference と一致」で機械判定できる。
- **Phase 1: 読み(無圧縮+PackBits+LZW、strip/tile、全画素型、
  両エンディアン、classic TIFF)**。m_geotiff + m_geotiff_codec を追加し、
  e_fmt_gtif の入力側を開通。
- **Phase 2: Deflate と predictor 2/3**。m_geotiff_inflate を追加。
  これで ArcGIS Pro 既定(LZ77)と QGIS 高圧縮プロファイルをカバーし、
  読み要件が完成。
- **Phase 3: 書き(無圧縮 strip、Float32/Int32、GeoKey+nodata)**。
  位置情報と EPSG は座標管理(§10)の t_georef から取る。
  検証は (a) 自前 reader での往復一致、
  (b) gdalinfo/QGIS/ArcGIS での目視確認(位置・値・nodata)を一度、
  以後は (a) を回帰テスト化。
- **Phase 4(必要になってから)**: BigTIFF 読み(全国 100m 級で必須化
  する見込み)、precip 逐次読みの multi-IFD 対応、Deflate/LZW 書き、
  BigTIFF 書き。

## 9. 実装前に合意が必要な点(未決事項)

1. ~~namelist 項目名と省略時挙動(§7)~~ → 座標管理の先行導入で解決(§10)。
2. 出力の画素型固定(実数=Float32)でよいか。倍精度のまま出したい
   量があるなら Float64 書きのオプションを Phase 3 に含めるか。
3. f_output_mode の組合せ仕様("gtif" 単独か、txt/bil との併用形か)。
4. Phase 0 のテスト tiff を test/ 下のどこに置くか(test/gtif/ 新設案)。
5. nodata の値の規約(入力 nodata をどの内部表現に落とすか。現状の
   txt/bil 入力には nodata 概念がなく、sw マスク等で代替している)。

## 10. 座標管理の先行導入(実装済み・2026-08-01)

GeoTIFF 実装に先立ち、ESRI hdr ベースの座標管理を導入した(m_georef.f90)。
仕様と決定事項:

1. **テキスト入力では地理座標を管理しない**(従来動作のまま。出力で bil を
   指定しても hdr は出さない)。将来 GeoTIFF 出力を指定した場合は座標
   未管理なら警告して停止する(GeoTIFF 実装時に組み込む)。
2. **bil 入力では、地盤高(fn_z)の bil と同じ場所に .hdr があれば読んで
   座標管理を有効化**する。無ければテキスト入力と同じ扱い。
   hdr の正本は地盤高のもののみで、他の入力 bil の hdr は読まない。
3. **hdr がある場合、nx, ny, dx, dy は namelist 省略可**。namelist にも
   指定がある場合は無言でどちらかを優先せず整合を検査し、矛盾なら停止
   (resolve_geometry の過剰指定と同じ流儀)。一致する場合は namelist の
   値を保持する(既存設定に hdr を後付けしても計算はビット同値)。
4. **出力で bil を指定し座標管理が有効なら、各 .bil に GDAL EHdr 互換の
   .hdr を併記**する(real は PIXELTYPE FLOAT、integer は SIGNEDINT。
   いずれも 32bit。hdr は圧縮対象外)。
5. **CRS は namelist の epsg(整数。既定 0 = 不明)で導入済み**。hdr には
   CRS が無いため常に namelist 由来。現状は保持のみで、GeoTIFF の
   GeoKey 出力(および将来 .prj 出力)で使う。
6. 座標値は PREC に依存させず **real64 固定**で保持する(単精度ビルドでも
   投影座標・経緯度の精度を落とさない)。内部の正本は「北西隅セルの外縁」
   (ESRI hdr の ULXMAP/ULYMAP=セル中心とは読み書き時に相互変換)。
   GeoTIFF の ModelTiepoint と同じ表現。
7. 対応する hdr は 1 バンド・32bit・LAYOUT=BIL・BYTEORDER=I のみ。
   範囲外(NBITS≠32 等)は黙って誤読せず明確なメッセージで停止する。
   NODATA キーは読み取って保持する(現状は未使用。GeoTIFF で使用予定)。
8. **経緯度(度単位)の bil にも対応する(2026-08-01 拡張)**。
   国土数値情報・基盤地図情報由来の経緯度格子を「dx=dy=100m, 250m」等の
   慣習的近似で使う既存運用を前提とした仕様:
   - 経緯度かどうかは hdr の数値から推測する(セル寸法 < 0.1 度かつ
     ULXMAP/ULYMAP が経緯度の値域内。hdr は CRS を持たないため)。
     GeoTIFF 実装後は CRS タグから確定的に判定する。
   - 経緯度格子では **namelist の dx, dy(m)の明示指定を必須**とする
     (XDIM/YDIM は度なので dx, dy に流用できない)。
   - WGS84 の度あたり弧長近似(領域中央緯度)で XDIM/YDIM をメートルに
     概算し、**指定値と概算値の両方を常に画面表示**する。相対差が
     30% を超える場合は格子の取り違えとみなして停止する
     (慣習的近似の差は日本周辺で高々 20% 程度、取り違えは倍半分)。
   - 出力 hdr の座標は度のまま往復する(内部の xul/yul/csx/csy は
     入力の単位を保持し、変換しない)。

実装箇所: m_georef.f90(新規)、m_geoinfo(t_geoinfo%gr 成分と probe)、
m_output(bil 書き出し 3 箇所に hdr 併記)、list_geoinfo(epsg)。
hdr の探索・読み込みは全ランクが冗長に読む(他の入力読みと同じ方式)ため
collective の追加はない。

以上。
