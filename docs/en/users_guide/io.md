# Input and Output Formats

> English mirror of docs/users_guide/io.md (based on commit 3089f8a). The Japanese file is the master copy.

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
  hdr, the file is read as int32.
- Specifying the grid geometry: for txt and bil without hdr, `nx, ny`
  and `dx, dy` (or `lx, ly`) must be given in the namelist. For bil
  with hdr and GeoTIFF this is basically unnecessary (the values are
  filled in from the file), except that a geographic (lat/lon) grid
  requires `dx, dy` (m) — see
  [the coordinate systems chapter](coordinates.md).
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

> **GeoTIFF output is uncompressed** (4 bytes per cell; unlike
> reading, compressed writing is not supported). If you output many
> time steps for an animation and the data volume matters, compress
> in post-processing (requires [GDAL](https://gdal.org/) — bundled
> with QGIS, or installable via apt / conda):
>
> ```bash
> for f in result/*.tif; do
>   gdal_translate -q -co COMPRESS=DEFLATE -co PREDICTOR=3 "$f" "${f%.tif}_c.tif"
> done
> ```
>
> Even floating-point fields typically shrink to 1/2–1/4. The
> compressed GeoTIFFs open in GIS as usual, and are **also directly
> usable as ENCflow input (f_input_mode=4) and by utils/out2vtk**
> (reading Deflate with predictor 3 is supported, and agreement with
> real GDAL outputs is checked in the regression tests — test/gtif).
> Running out2vtk right after the compression is fine (it assembles
> exact file names, so the `_c` files are ignored and the originals
> are used). If you delete the originals to save space and keep only
> the `_c` files, set `outfn_suffix = "_c"` in the out2vtk namelist
> to convert directly from the compressed files.

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
| f_out_h | 1 | H | depth (m) (with the fresh/salt layers enabled, the surface salt-layer thickness Hss is also written) |
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
| f_out_hg | 0 | Hg | subsurface storage depth (m) (when fn_gwflow is enabled; also Hg2 with the weathered bedrock layer, Hgc with the conduit continuum layer, and Hgs with the fresh/salt layers) |
| f_out_hrs | 0 | Hrs | pond depth (m) (when fn_reservoir is enabled) |
| f_out_hs | 0 | Hs | sediment column (m) (requires an active sediment process; for visualizing the concentration C = hs/(h+hs)) |
| f_out_hd | 0 | Hd | floating driftwood volume (m³/m²) (requires [Driftwood](driftwood.md)) |
| f_out_wd | 0 | Wd / Wd9999 | deposited driftwood (m³/m²) and the maximum arrival max(floating+deposited) over the run (the driftwood hazard map) |
| f_out_fs | 0 | Fs / Fs9999 | slope safety factor Fs distribution and its period minimum (requires f_slide = 1 or 2; -1 = not evaluated; see [Sediment and landform change](geomorph.md)) |
| f_out_hmax | 1 | H9999 | maximum depth |
| f_out_hmaxt | 0 | Ht9999 | time of maximum depth |
| f_out_vvmax | 0 | V9999 | maximum velocity |
| f_out_qqmax / f_out_qqmaxt / f_out_qqmaxd | 0 | Q9999 / Qt9999 / Qd9999 | maximum discharge and its time / direction |
| f_out_dmax / f_out_dmaxt | 0 | D9999 / Dt9999 | maximum flow depth h+hs and its time (requires an active sediment process; for debris and volcanic flows the true "inundation depth" is the mixture depth) |
| f_out_fmax | 0 | F9999 | maximum fluid force (ρm/ρw)·(h+hs)·V² (m³/s²; normalized by the freshwater density, so for water-only runs it equals the conventional u²h; for mixtures the density ratio 1+sC is included; multiply by ρw (1000) for the force per unit width in N/m) (a standard indicator for building damage) |
| — (with fn_swi) | — | Swi / Swi9999 / Swit9999 | Soil Water Index (mm) distribution, period maximum, and its time ([Soil Water Index](swi.md); automatic) |
| — (always) | — | X0000 | domain mask (0: outside, 1: land, 2: sea); for visualization and checking the active domain in GIS |

In addition, `Log.txt` (identical to the on-screen log) and a copy of
the parameter file used are always saved.

Distributed outputs can be opened directly in GIS (QGIS / ArcGIS), and
**utils/out2vtk** converts them to VTK files for ParaView — 3D terrain
views, time-animated water surfaces, and draping of satellite imagery
(see [utils/out2vtk/README.md](../../../utils/out2vtk/README.md),
in Japanese).
If outputting many GeoTIFFs for an animation makes the data volume a
concern, see the post-processing compression note in
[the output format section](#output-format-f_output_mode).

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
