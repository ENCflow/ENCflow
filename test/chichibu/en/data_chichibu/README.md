# data_chichibu — real-terrain data for test/chichibu

> English mirror of test/chichibu/data_chichibu/README.md. The Japanese file is the master copy.

[日本語](../../data_chichibu/README.md)

Grid data of the Chichibu catchment in the upper Arakawa River basin,
560×300 cells (dx = dy = 100 m) (the same catchment and the same source as
the 200 m data of [tutorials/chichibu](../../../../tutorials/chichibu/en/README.md),
at a different resolution).

- `Chichibu_100m.txt` — elevation (original data)
- `Chichibu_100m_filled2.txt` — elevation (depression-filled; used in the computation)
- `Chichibu_100m_basin.txt` — catchment mask
- `Chichibu_100m_river.txt` — channel mask

Origin of the data: the elevation data (and the catchment mask) were made
from the Fundamental Geospatial Data digital elevation model of the
Geospatial Information Authority of Japan, and the channel mask from the
channel-order data
([DOI:10.3178/jjshwr.36.1812](https://doi.org/10.3178/jjshwr.36.1812))
made from the National Land Numerical Information river data.
