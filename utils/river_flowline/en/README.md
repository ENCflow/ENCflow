# river_flowline — Move a channel mask onto the flow lines of the elevation data

> English mirror of utils/river_flowline/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A preprocessing program that moves a channel mask ([fn_rw](../../../docs/en/users_guide/geoinfo.md)) onto the
flow lines of the elevation data (the drainage paths determined by the elevation). It is written in Fortran,
uses the same read and write procedures as the main program, and handles text, bil and GeoTIFF.

A channel mask made by rasterizing river centre lines is in places one cell off the valley line of the
elevation data. The cells that are off are valley-wall cells: the channel roughness (`rn0_rw`) and the
carving (`depth_rw`) are applied to the valley wall, and not to the valley-line cells where the water
actually flows. This program follows the flow line from each cell of the channel mask and makes the cells
passed the new channel mask.

```bash
make install               # in the ENCflow top directory (builds src and utils and puts them in bin/)
bin/river_flowline parameterfile zfile maskfile riverfile outfile [accfile]
```

| Argument | Content |
|---|---|
| `parameterfile` | The system parameter file used for the computation. `f_input_mode` (the input/output format) and `nx`, `ny` via `fn_geoinfo` are read with the same interpretation as the main program |
| `zfile` | Elevation (depressions filled; same as `fn_z`) |
| `maskfile` | Domain mask (values greater than 0 are computed cells; same as `fn_mask`). `-` to use the whole grid |
| `riverfile` | Original channel mask (values greater than 0 are channel cells; same as `fn_rw`) |
| `outfile` | Output file of the moved channel mask (0 / 1) |
| `accfile` | Output file of the catchment area of the flow lines (number of cells, including the cell itself; optional; for checking and plotting) |

Files are read and written at the paths as given (`dir_data` is not prepended). When `fn_geoinfo` of the
parameter file points to another file, run the program where that file is visible (the case directory), as
for a computation.

The input/output format follows `f_input_mode`.

| `f_input_mode` | Format | Grid size | Output |
|---:|---|---|---|
| 1 | text | `nx`, `ny` of `&list_geoinfo` are required | one row per line, values separated by one blank |
| 2 | bil | taken from the hdr next to `riverfile` if there is one (checked against `nx`, `ny` when they are also given) | 4-byte integers; an hdr is also written when the coordinates are known from the hdr |
| 4 | GeoTIFF | read from `riverfile` (as above) | the georeference tags of `riverfile` are carried over (the program stops if there are none) |

The program prints how many cells of the original channel mask were on the flow lines, how many were
removed and how many were added.

```
domain 71486 cells, cells without a lower neighbour 1468 (2.05 %), flowline end points 1
original channel mask 9582 cells -> re-mapped channel mask 6515 cells
  on the flowlines 5986 (62 % of the original), removed 3596 (median 24.6 m above the receiving cell), added 529
```

## Procedure

1. **Determine the flow lines.** The receiver of each cell is the steepest of its 8 neighbours (D8;
   O'Callaghan & Mark 1984). For cells without a lower neighbour (flats left by the depression filling,
   remaining depressions) the receiver is the neighbour taken out first by Priority-Flood (Barnes et al.
   2014), which takes cells out in ascending order of elevation starting from the cells on the edge of
   the domain and spreads to their neighbours. Edge cells without a lower neighbour are the end points
   (outlets) of the flow lines.
2. **Move the channel mask.** The flow line is followed from each cell of the original channel mask to
   its end point, and the cells passed become channel cells. The starting cell itself becomes a channel
   cell only when the flow line from another channel cell passes through it. Cells off the valley line
   leave the channel, and cells on the valley line where the original mask was interrupted enter it.

When several neighbours have the same slope, the first one in the order north-west to east, north to
south is taken. Cells of the same elevation are taken out in the order in which they entered
Priority-Flood. The same input always gives the same mask.

The flow-line procedure is the same as in `make_catchment.py` of the example
[source_area](../../../examples/source_area/en/README.md) (source_area keeps the cells of the original mask
and only joins the interruptions along the flow lines).

## Results for the Chichibu data

Results for the channel masks of test/chichibu and tutorials/chichibu (made from the rivers of the
National Land Numerical Information). The moved masks are placed next to the original files under the
name `…_river_flowline`.

| Grid | Original channel mask | Moved channel mask | Cells that were on the flow lines | Cells removed (median height above the receiver) | Cells added |
|---|---:|---:|---:|---:|---:|
| 50 m | 19,714 | 14,361 | 12,691 (64 %) | 7,023 (11.9 m) | 1,670 |
| 100 m | 9,582 | 6,515 | 5,986 (62 %) | 3,596 (24.6 m) | 529 |
| 200 m | 2,327 | 1,473 | 1,424 (61 %) | 903 (28.6 m) | 49 |
| 500 m | 192 | 123 | 110 (57 %) | 82 (23.8 m) | 13 |

The 100 m mask can be made with the following command (the other grids can be made in the same way from the
elevation, catchment mask and channel mask of their directories;
[test/river_flowline](../../../test/river_flowline/en/README.md) checks that the result is byte-identical to
the masks placed in the repository for the four grids).

```bash
cd test/river_flowline
T=../chichibu/data_chichibu
../../bin/river_flowline param_100m.txt $T/Chichibu_100m_filled2.txt $T/Chichibu_100m_basin.txt \
    $T/Chichibu_100m_river.txt wrk_100m.txt
```

In a computation that gives the channel a smaller roughness than the slopes, the results change with the
move. In the regression case of test/chichibu (100 m; slopes n = 0.15, channel n = 0.02) the peak discharges
at the four transects of the main stem became 2–9 % smaller and 1–19 min later (the valley-wall cells that
carried the channel roughness return to the slope roughness).

## Limits of accuracy and what it cannot do

- The flow lines are determined by the elevation alone and are one cell wide (lines connected through
  the 8 neighbours). For channels wider than the grid spacing and for lakes, only the cells passed by
  flow lines become channel cells (where the original mask is painted as an area, the range passed by
  the flow lines from its cells remains).
- On the flats left by the depression filling the flow lines follow the order in which Priority-Flood
  takes the cells out and carry no information about the terrain (on the 100 m grid of Chichibu the
  cells without a lower neighbour are 2 % of the domain; nine tenths of them are cells of the original
  channel mask).
- The uppermost cell of each channel leaves the channel, because no flow line from another channel cell
  passes through it. Moving an already moved mask once more shortens each channel head by one more cell.
  Apply the program once, to the original mask.
- The program also runs on elevation data with remaining depressions, but inside a depression the flow
  lines run against the slope toward the spill point. Use elevation data with the depressions filled.
- Where the line of the channel mask is two or more cells away from the valley, the flow line on the
  slope from that cell down to the valley enters the channel. Check the result by overlaying it on the
  original mask and the elevation in a GIS or similar.
- Channel cells move by one cell in places, so for settings that place probes or transects on channel
  cells, check their positions with the moved mask.
- The masks placed in the repository are the output of a double-precision build (the default
  `PREC=double`). It has not been checked that a single-precision build (which reads the elevation in
  single precision) gives the same masks.

## References

- Barnes, R., Lehman, C. and Mulla, D. (2014): Priority-flood: An optimal depression-filling
  and watershed-labeling algorithm for digital elevation models. Computers & Geosciences, 62,
  117–127.
- O'Callaghan, J. F. and Mark, D. M. (1984): The extraction of drainage networks from digital
  elevation data. Computer Vision, Graphics, and Image Processing, 28(3), 323–344.
