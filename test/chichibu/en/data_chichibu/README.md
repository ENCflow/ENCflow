# data_chichibu — real-terrain data for test/chichibu

> English mirror of test/chichibu/data_chichibu/README.md. The Japanese file is the master copy.

[日本語](../../data_chichibu/README.md)

Grid data of the Chichibu catchment in the upper Arakawa River basin,
560×300 cells (dx = dy = 100 m) (the same catchment and the same source as
the 200 m data of [tutorials/chichibu](../../../../tutorials/chichibu/en/README.md),
at a different resolution).

- `Chichibu_100m.txt` — elevation (original data)
- `Chichibu_100m_filled2.txt` — elevation (depression-filled; used in the computation)
- `Chichibu_100m_cond.txt` — elevation with a conditioned channel bed. Only the channel cells of
  `Chichibu_100m_filled2.txt` (the 6,515 cells of `Chichibu_100m_river_flowline.txt`) are rebuilt to follow
  the valley bottom of a 10 m grid elevation of the same catchment ("Elevation with a conditioned channel bed"
  below; used by the regression case test/chichibu_cond and by the supplement of tutorials/chichibu)
- `Chichibu_100m_basin.txt` — catchment mask
- `Chichibu_100m_river.txt` — channel mask (the original data; 9,582 cells; used by the param_*.txt of the
  derived experiments of developer.md §68)
- `Chichibu_100m_river_flowline.txt` — the channel mask moved onto the flow lines of the depression-filled
  elevation (6,515 cells; [utils/river_flowline](../../../../utils/river_flowline/en/README.md); used by the
  regression case param.txt and by test/chichibu_icmap)
- `width_chichibu50.txt` / `width_chichibu100.txt` — uniform channel width of 50 m / 100 m on the cells of the
  original channel mask (used by the derived sub-grid channel experiments param_w*.txt)
- `width_chichibu50_flowline.txt` — uniform channel width of 50 m on the cells of the moved channel mask (used
  by the W = 50 computations of the supplement of tutorials/chichibu)

Origin of the data: the elevation data (and the catchment mask) were made
from the Fundamental Geospatial Data digital elevation model of the
Geospatial Information Authority of Japan, and the channel mask from the
channel-order data
([DOI:10.3178/jjshwr.36.1812](https://doi.org/10.3178/jjshwr.36.1812))
made from the National Land Numerical Information river data. In the channel mask rasterized from the
channel-order data, 38 % of the cells are valley-wall cells off the valley line (flow line) of the
elevation, and the mask is interrupted on the valley line at 529 cells (developer.md §109).

## Elevation with a conditioned channel bed (`Chichibu_100m_cond.txt`)

Depression filling raises the hollows of a valley bottom to a flat level, so it leaves flat reaches in the
channel, each followed by a step at its downstream end (in `Chichibu_100m_filled2.txt`, 1,294 of the 6,514
links between channel cells have the same elevation as their downstream cell). A flat reach delays the
flood wave and, under some conditions, makes the discharge oscillate (developer.md §111).
`Chichibu_100m_cond.txt` rebuilds only the elevation of the channel cells by the following steps (the cells
other than channel cells are the same as in `Chichibu_100m_filled2.txt`).

1. Make the reference elevation: for each 100 m cell, take the minimum of the 10 m grid elevation
   (depression-filled) inside it (the level of the valley bottom).
2. Set each channel cell to the lower of the reference and the depression-filled elevation.
3. From upstream to downstream, take the lower of the cell and its inflowing cell with the largest
   contributing area (this cuts the bumps where a 100 m cell misses the valley bottom).
4. From downstream to upstream, raise each cell that is lower than its downstream cell to the level of that
   cell.
5. Regrade each remaining flat reach to a uniform slope down to the foot of the step downstream of it.

The channel cells on the two water surfaces seen in the 10 m elevation (a reservoir at 395.0 m and a reach
taken to be the pool above a dam at 519.8 m) are set to flat surfaces at those levels (86 cells). The links
between channel cells (flow lines) are those determined from the depression-filled elevation.

| Item | Value |
|---|---|
| Channel cells lowered | 6,478 (99.4 %); median lowering 22.0 m, maximum 76.9 m |
| Channel cells raised | 9 (the 519.8 m water surface; at most 1.78 m) |
| Links at the same elevation as the downstream cell | 1,294 → 86 (the kept water surfaces and their upstream ends) |
| Links with a reverse slope, depressions | 0 |

Because the bed is now the level of the valley bottom inside the cell and not the cell-mean elevation, the
height difference from the cells beside the channel becomes larger (the median difference between the lowest
neighbouring cell and the bed is 24 m).

Origin and limits: the 10 m grid elevation (made from the Fundamental Geospatial Data digital elevation model
of the Geospatial Information Authority of Japan) is not in the repository because of its size. There is no
utility for this procedure yet (the procedure and the check computations are recorded in developer.md
§111.13 and §111.16). The `*_cond.txt` of 200 m (data_chichibu_200m) and 50 m (data_chichibu_50m) are made
from the same 10 m elevation by the same procedure, and the levels of the kept water surfaces are the same
in the three grids.
