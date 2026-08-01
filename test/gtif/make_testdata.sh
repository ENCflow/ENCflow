#!/bin/bash
# =====================================================================
# GeoTIFF リーダー用テスト資産の生成(docs/geotiff_plan.md Phase 0)
#
#   data/     読みテスト対象の .tif 一式(型×圧縮×配置×エンディアン等)
#   expected/ 期待値行列(ENCflow のテキスト行列と同じ「1行=1格子行」形式。
#             実数は f32/f64 の正確な往復桁数で印字)
#
#   生成には gdal_translate と python3 + tifffile が必要。
#   資産はコミット済みなので、通常は再実行不要。組合せを増やすときに
#   このスクリプトへ追記して再生成・再コミットする。
#
#   値のソースは test/chichibu の地形(実データの切り出し 60x48)。
#   位置・CRS はテスト用の便宜値(経緯度=EPSG:6668 4秒格子、
#   投影=EPSG:6677 100m 格子)で、実在の場所とは対応しない。
# =====================================================================
set -eu
cd "$(dirname "$0")"

SRC=../chichibu/data_chichibu/Chichibu_100m_filled2.txt
ROW0=100    # 切り出し開始(0 始まり)
COL0=240
NX=60
NY=48

rm -rf data expected work
mkdir -p data expected work

# --- ソース行列の切り出しと AAIGrid 化(gdal_translate の入力) -------
python3 - "$SRC" $ROW0 $COL0 $NX $NY <<'EOF'
import sys
import numpy as np

src, row0, col0, nx, ny = sys.argv[1], *map(int, sys.argv[2:])
z = np.loadtxt(src)[row0:row0+ny, col0:col0+nx]

def write_asc(fn, a, xll, yll, cs, fmt):
    # NODATA_value は書かない(書くと全変種に nodata タグが伝播する。
    # nodata 付きの変種は gdal_translate の -a_nodata で明示的に作る)
    with open(fn, "w") as f:
        f.write(f"ncols {a.shape[1]}\nnrows {a.shape[0]}\n")
        f.write(f"xllcorner {xll}\nyllcorner {yll}\ncellsize {cs}\n")
        for r in a:
            f.write(" ".join(fmt % v for v in r) + "\n")

zi = np.rint(z).astype(np.int64)
write_asc("work/f_prj.asc", z, -20000.0, -80000.0, 100.0, "%.4f")
write_asc("work/f_geo.asc", z, 138.625, 35.90, 1.0/900.0, "%.4f")
write_asc("work/i_prj.asc", zi, -20000.0, -80000.0, 100.0, "%d")
write_asc("work/u16_prj.asc", zi + 40000, -20000.0, -80000.0, 100.0, "%d")
write_asc("work/u8_prj.asc", np.clip(np.rint(z / 8), 0, 255).astype(np.int64),
          -20000.0, -80000.0, 100.0, "%d")
EOF

# --- gdal_translate で変種を生成 -------------------------------------
T="gdal_translate -q -of GTiff"
PRJ="-a_srs EPSG:6677 work/f_prj.asc"
PRJI="-a_srs EPSG:6677 work/i_prj.asc"

# Float32(投影 100m 格子)
$T -ot Float32 $PRJ data/f32_none_strip.tif
$T -ot Float32 $PRJ -co TILED=YES -co BLOCKXSIZE=32 -co BLOCKYSIZE=32 data/f32_none_tile.tif
$T -ot Float32 $PRJ -co COMPRESS=LZW data/f32_lzw_strip.tif
$T -ot Float32 $PRJ -co COMPRESS=LZW -co PREDICTOR=3 data/f32_lzw_pred3_strip.tif
$T -ot Float32 $PRJ -co COMPRESS=DEFLATE data/f32_deflate_strip.tif
$T -ot Float32 $PRJ -co COMPRESS=DEFLATE -co PREDICTOR=3 \
   -co TILED=YES -co BLOCKXSIZE=32 -co BLOCKYSIZE=32 data/f32_deflate_pred3_tile.tif
$T -ot Float32 $PRJ -co COMPRESS=PACKBITS data/f32_packbits_strip.tif
$T -ot Float32 $PRJ -co BIGTIFF=YES -co COMPRESS=DEFLATE data/f32_deflate_bigtiff.tif
gdal_translate -q -of GTiff -ot Float32 $PRJ --config GDAL_TIFF_ENDIANNESS BIG \
   data/f32_none_strip_be.tif

# Float32(経緯度 4 秒格子、nodata タグ付き。画素値は投影版と同一)
$T -ot Float32 -a_srs EPSG:6668 -a_nodata -9999 work/f_geo.asc data/f32_none_strip_geo.tif

# Float64
$T -ot Float64 $PRJ data/f64_none_strip.tif

# 整数系(投影 100m 格子)
$T -ot Byte   -a_srs EPSG:6677 work/u8_prj.asc  data/u8_none_strip.tif
$T -ot Int16  $PRJI -co COMPRESS=LZW -co PREDICTOR=2 data/i16_lzw_pred2_strip.tif
$T -ot Int16  $PRJI --config GDAL_TIFF_ENDIANNESS BIG data/i16_none_strip_be.tif
$T -ot UInt16 -a_srs EPSG:6677 work/u16_prj.asc -co COMPRESS=DEFLATE \
   -co TILED=YES -co BLOCKXSIZE=32 -co BLOCKYSIZE=32 data/u16_deflate_tile.tif
$T -ot Int32  $PRJI data/i32_none_strip.tif
$T -ot UInt32 $PRJI -co COMPRESS=LZW data/u32_lzw_strip.tif

# --- 期待値行列の生成と全変種の自己検証 -------------------------------
python3 - <<'EOF'
import glob
import numpy as np
import tifffile

# 期待値: 実際の tif(型変換済みの値)から書き出す。
# 実数は「その値へ正確に往復する最短桁」でなく余裕を持った桁数で印字
# (f32→倍精度の拡張は正確なので、%.17g を倍精度として読めばビット同値)
def dump(fn, a, fmt):
    with open(fn, "w") as f:
        for r in a:
            f.write(" ".join(fmt % v for v in r) + "\n")

ref = {}
for name, fmt in [("f32", "%.17g"), ("f64", "%.17g"), ("u8", "%d"),
                  ("i16", "%d"), ("u16", "%d"), ("i32", "%d"), ("u32", "%d")]:
    src = {"f32": "data/f32_none_strip.tif", "f64": "data/f64_none_strip.tif",
           "u8": "data/u8_none_strip.tif", "i16": "data/i16_lzw_pred2_strip.tif",
           "u16": "data/u16_deflate_tile.tif", "i32": "data/i32_none_strip.tif",
           "u32": "data/u32_lzw_strip.tif"}[name]
    a = tifffile.imread(src)
    ref[name] = a
    dump(f"expected/{name}.txt", a.astype(np.float64) if name in ("f32", "f64") else a, fmt)

# 全変種が dtype ごとの参照と値一致することを確認(生成ミスの検出)
kind = {"f32": "f32", "f64": "f64", "u8": "u8", "i16": "i16",
        "u16": "u16", "i32": "i32", "u32": "u32"}
for fn in sorted(glob.glob("data/*.tif")):
    name = fn.split("/")[1].split("_")[0]
    a = tifffile.imread(fn)
    assert a.shape == (48, 60), (fn, a.shape)
    assert np.array_equal(a, ref[kind[name]]), fn
    with tifffile.TiffFile(fn) as t:
        p = t.pages[0]
        print(f"{fn.split('/')[1]:28s} {str(a.dtype):8s} comp={p.compression.name.lower():8s}"
              f" pred={p.predictor.value if hasattr(p.predictor,'value') else p.predictor}"
              f" {'tile' if p.is_tiled else 'strip':5s}"
              f" {'MM' if t.byteorder=='>' else 'II'} {'bigtiff' if t.is_bigtiff else 'classic'}")
print("self-check OK")
EOF

rm -rf work
echo "done: $(ls data | wc -l) tif files, $(ls expected | wc -l) expected files"
