# Test assets for the GeoTIFF reader (Phase 0)

> English mirror of test/gtif/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A set of GeoTIFF files for read tests, prepared in Phase 0 of
docs/geotiff_plan.md. The regression test of the reader added in Phase 1 reads
`data_gtif/*.tif` here and compares them with `expected/*.txt`.

## How to generate

    ./make_testdata.sh      # requires gdal_translate and python3 + tifffile

The source of the values is a cutout (60x48) of the real terrain of
test/chichibu. The position and CRS are convenience values for testing and do
not correspond to a real place. The assets are committed, so re-running is
normally unnecessary. To add combinations, append to the script and
regenerate.

## Contents of data_gtif/ (17 files)

File-name convention: `<type>_<compression>[_pred<N>]_<layout>[_be|_geo|_bigtiff].tif`

| Axis | Values covered |
|---|---|
| Pixel type | f32, f64, u8 (Byte), i16, u16, i32, u32 |
| Compression | none, LZW, Deflate, PackBits |
| predictor | 1 (none), 2 (horizontal differencing, integer), 3 (floating point) |
| Layout | strip (60x34), tile (32x32; partial tiles at the edges for 60x48) |
| Byte order | II (little), MM (big; `_be`) |
| Format | classic TIFF, BigTIFF (`_bigtiff`) |
| CRS | EPSG:6677 (projected 100 m grid), EPSG:6668 (geographic 4-second grid; `_geo`) |
| nodata | only `f32_none_strip_geo.tif` has GDAL_NODATA=-9999 |

All variants of the same type have identical pixel values (make_testdata.sh
verifies this itself).

## Expected values in expected/ (one file per type)

- The same "1 line = 1 grid row" format as ENCflow's text matrices.
- Real numbers are printed with %.17g. Since the f32→f64 extension is exact,
  reading these values as double precision gives values bit-identical to "the
  values the reader should return (f32 extended to the default real)" (for
  PREC=double).
- Integers are the expected values for each of u8/i16/u16/i32/u32 (u16 carries
  an offset of +40000 so that the zero extension of unsigned 16-bit can be
  checked).

## Running the test

    ./Run.sh        # build with the settings of ../../make.inc and run (serial)

test_gtif_reader reads all variants in data_gtif/ and data_user/ and checks
bit identity with the expected values, error stops on unsupported formats, and
the metadata (position, CRS, nodata). Deflate has been supported since Phase 2
(value comparison). Only BigTIFF is checked for "giving an error" (support
planned in Phase 4).
Writing (Phase 3) is checked by four round trips — projected / geographic /
integer / without coordinates (write → read with bit-identical values plus a
metadata round trip). The wrk_*.tif that the test outputs are disposable
(covered by .gitignore).

**Note: the coordinates of wrk_f32_prj / wrk_f32_geo / wrk_i32_prj /
wrk_f32_nogeo are convenience values for testing** (origin -12345 etc.), so in
QGIS they are displayed at a non-existent position (nogeo is displayed in pixel
coordinates). That is normal.
**For visual checks in QGIS / ArcGIS, use wrk_d2451_real.tif /
wrk_d4326_real.tif**. These are the real outputs of data_user read and written
back with the same georeferencing; overlaid on the original tif they should
match exactly in both position and values (the agreement of position, extent
and pixels in gdalinfo has been confirmed).

## data_user/ (real outputs of QGIS / ArcGIS Pro; received 2026-08-01)

Real data provided by a user (elevation on a grid of about 1000 m). The
expected values were generated in expected_user/ by reading back with tifffile
(the reference implementation), and it has been checked that all variants on
the same grid agree with each other in value. Provenance: `src/1000m.bil`
(+hdr) is the original of the geographic version and is bit-identical in all
pixels to the d4326_f32 tifs (`src/D4326.txt` is written out rounded to 3
digits, so it does not agree strictly). The D2451 series is its projection to
zone 9.

| File (after renaming) | Original name | What it is |
|---|---|---|
| d2451_f32_arc_none | D2451_f32_Arcなし | f32 uncompressed tile. The GeoKey lists both 4612+2451 (ArcGIS-specific) |
| d2451_f32_arc_lzw | D2451_f32_ArcLZW | f32 LZW tile |
| d2451_f32_qgis_std | D2451_f32_QGIS標準 | f32 uncompressed strip |
| d2451_f32_qgis_deflate | D4326_f32_QGIS高圧縮 | Renamed because **the content is the 2451 grid**. Deflate+pred2 |
| d2451_i16_qgis_std | D2451_i16_QGIS標準 | i16. nodata is a real-number string (-3.4e38) |
| d4326_f32_arc_none / arc_lzw | D4326_f32_Arcなし/ArcLZW | f32 tile (EPSG:4326) |
| d4326_f32_qgis_std | D4326_f32_QGIS標準 | f32 uncompressed strip |
| d4326_i16_arc_none / arc_lzw | D4326_i16_Arcなし/ArcLZW | i16 tile (arc_lzw is the re-uploaded version = LZW) |
| d4326_i8_arc_lzw | D4326_i8_ArcLZW | i8 LZW tile (added with the re-upload) |
| d4326_i16_qgis_std / qgis_deflate | D4326_i16_QGIS標準/高圧縮 | i16 strip (the high-compression one is Deflate+pred2) |
| d4326_i8_qgis_std | D4326_i8_QGIS標準 | i8 (signed 8-bit) |
| d4326_i8_qgis_deflate | D4326_i8_QGIS高圧縮 | i8 Deflate+pred2 (added in the third delivery) |
| d2451_i8_qgis_std / qgis_deflate | D2451_i8_QGIS標準/高圧縮 | i8 (added in the third delivery; the high-compression one is Deflate+pred2) |

The CRS in common use is reportedly JGD2000 plane rectangular zone 9
(EPSG:2451). The GeoKey verification of writing (Phase 3) targets this
primarily.

## Not yet covered

- Sparse tiles (tile offset 0), the error path for UInt32 values exceeding
  2^31, and checks of the stop messages for unsupported compressions such as
  JPEG.
