# Input and Output Formats

> English mirror of docs/users_guide/io.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Input and output of distributed data (topography, roughness, results,
etc.) supports three formats. All of them are selected in
`&list_sysparam`.

## Common raster conventions

- The matrix order puts the **first row at the northern edge** (rows =
  y direction, north to south; columns = x direction, west to east).
  This is the same orientation as GIS rasters and paper maps.
- All formats use the same order and the same values (the format is
  merely a difference of container).

## Input format (f_input_mode)

| Value | Format |
|---|---|
| 1 (default) | matrix text (whitespace-separated) |
| 2 | bil (raw binary + ESRI hdr) |
| 4 | GeoTIFF |

- For bil, if a `.hdr` with the same base name exists, the pixel type
  (int8/int16/int32, signed or unsigned) is read from it. Without an
  hdr, the file is read as conventional int32.
- GeoTIFF supports uncompressed, LZW, and Deflate (including with
  predictor), in both strip and tile layouts, and has been verified
  against real outputs from QGIS / ArcGIS / GDAL. No external library
  is used (in-house implementation).
- The input format is a single choice (unlike output, it is not a
  bit sum).

## Output format (f_output_mode)

Multiple formats can be written at once as a **bit sum**.

| Value | Formats written |
|---|---|
| 1 (default) | text only |
| 2 | bil only |
| 3 | text + bil |
| 4 | GeoTIFF only |
| 7 | text + bil + GeoTIFF |

When the coordinate system is managed, a `.hdr` is written alongside
bil output, and the CRS is embedded in GeoTIFF output
(see [the coordinate systems chapter](coordinates.md)).

## Output file scheme

Outputs are written to `dir_result` (default `result/`) with names of
the form **prefix + 4-digit number**.

**Meaning of the number**

| Number | Meaning |
|---|---|
| 0000 | state at the start of this run (in a restart run, the restored state) |
| 0001- | sequential numbers every dt_file (the mapping to times is in `FILENUMBER.csv`) |
| 9998 | state at the final time step |
| 9999 | statistics such as maxima over the whole computation period |

**Prefixes and output flags** (enabled with `f_out_XXX = 1`. By
default only H, H9999, and the initial ground elevation Z0000 are
written.)

| Flag | Default | File | Contents |
|---|---|---|---|
| f_out_h | 1 | H | depth (m) |
| f_out_e | 0 | E | water level (relative to datum) (m) |
| f_out_z | 0 | Z | ground elevation (m) (even when off, Z0000 is always written; for the time evolution of landform-change runs) |
| f_out_u / f_out_v | 0 | u / v | velocity in the x / y direction (m/s) |
| f_out_vv | 0 | V | velocity magnitude (m/s) |
| f_out_m / f_out_n | 0 | m / n | unit-width discharge in the x / y direction (m2/s) |
| f_out_qq | 0 | Q | discharge magnitude (m2/s) |
| f_out_qc | 0 | Qc | cumulative discharge |
| f_out_qd | 0 | Qd | flow direction (needed by utils/rerecord) |
| f_out_ddd / f_out_dda | 0 | Ddd / Dda | dominant / all downstream directions (needed by utils/rmdepress_river) |
| f_out_pre | 0 | Pr | rainfall intensity (mm/h) |
| f_out_fr / f_out_cn | 0 | Fr / Cn | Froude number / Courant number |
| f_out_hg | 0 | Hg | subsurface storage depth (m) (when fn_gwflow is enabled) |
| f_out_hrs | 0 | Hrs | pond depth (m) (when fn_reservoir is enabled) |
| f_out_hmax | 1 | H9999 | maximum depth |
| f_out_hmaxt | 0 | Ht9999 | time of maximum depth |
| f_out_vvmax | 0 | V9999 | maximum velocity |
| f_out_qqmax / f_out_qqmaxt / f_out_qqmaxd | 0 | Q9999 / Qt9999 / Qd9999 | maximum discharge and its time / direction |

In addition, `Log.txt` (identical to the on-screen log) and a copy of
the parameter file used are always saved.

Distributed outputs can be opened directly in GIS (QGIS / ArcGIS), and
**utils/out2vtk** converts them to VTK files for ParaView — 3D terrain
views, time-animated water surfaces, and draping of satellite imagery
(see [utils/out2vtk/README.md](../../../utils/out2vtk/README.md),
in Japanese).

## Screen and log display columns (f_disp_\*)

The time, the conserved quantity S, Runge, and ex_flux are always
displayed; the columns of field maxima are selectable: `f_disp_h`
(h_max, default on), `f_disp_vv` (V_max, default on), `f_disp_cn`
(Cn_max, default on), `f_disp_qq` (Q_max, default off).
`f_disp_debug = 1` displays the S column with all significant digits
(for balance debugging and regression tests). For how to read the
columns, see [Tutorial Step 1](../../../tutorials/wave/en/README.md#running).

## Adjusting directories and file names

| Parameter | Default | Meaning |
|---|---|---|
| dir_data | "." | base directory of input data files |
| dir_result | "result" | result output directory |
| dir_save | "save" | directory for state files ([Suspend and Restart](restart.md)) |
| fn_log | "Log.txt" | log file name |
| outfn_suffix | "" | string appended to output file names (to avoid collisions when running scenarios side by side in the same directory) |
