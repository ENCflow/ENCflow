# data_chichibu_200m — 200 m grid data for the resolution comparison

> English mirror of test/chichibu/data_chichibu_200m/README.md. The Japanese file is the master copy.

[日本語](../../data_chichibu_200m/README.md)

A copy of the 200 m data of tutorials/chichibu/data_chichibu (filled / basin /
river in text format) with the distribution of the sub-grid channel width
added. Referenced by test/chichibu/param200_*.txt (developer.md §68.24).

| File | Contents |
|---|---|
| Chichibu_200m_filled.txt / _basin.txt / _river.txt | Identical to tutorials/chichibu/data_chichibu |
| Chichibu_200m_cond.txt | Elevation with a conditioned channel bed. The channel cells of Chichibu_200m_filled.txt (the 1,473 cells of Chichibu_200m_river_flowline.txt) are rebuilt to follow the valley bottom of the 10 m grid elevation (the same procedure as "Elevation with a conditioned channel bed" in the [README of data_chichibu](../data_chichibu/README.md)). All channel cells are lowered (median lowering 37.4 m, maximum 134.7 m). The links at the same elevation as the downstream cell go from 446 to 25, and there are no links with a reverse slope and no depressions. The median difference between the lowest neighbouring cell and the bed is 48 m (used by the comparison computations of developer.md §111) |
| Chichibu_200m_river_flowline.txt | The channel mask (2,327 cells) moved onto the flow lines of the elevation (1,473 cells; utils/river_flowline; identical to tutorials/chichibu/data_chichibu) |
| width200_50.txt / width200_100.txt | Uniform channel width of 50 m / 100 m on the channel cells (wall-less sub-grid channel); cells of the original channel mask |
| width200_50_flowline.txt | Uniform channel width of 50 m on the cells of the moved channel mask (used by the W = 50 computations of the supplement of tutorials/chichibu) |
