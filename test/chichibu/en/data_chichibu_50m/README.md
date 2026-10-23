# data_chichibu_50m — 50 m grid data for test/chichibu

> English mirror of test/chichibu/data_chichibu_50m/README.md. The Japanese file is the master copy.

[日本語](../../data_chichibu_50m/README.md)

Grid data of the Chichibu catchment in the upper Arakawa River basin,
1120×600 cells (dx = dy = 50 m) (the same catchment and the same domain
extent as the 100 m data of data_chichibu; the 2×2 block mean agrees with
the 100 m elevation with rms 0.86 m). Used for the resolution comparison of
developer.md §68.18 (schemes 1 and 3 × dynamic reallocation). See
param50_*.txt.

- `Chichibu_50m_filled.txt` — elevation (depression-filled)
- `Chichibu_50m_basin.txt` — catchment mask (285,843 cells)
- `Chichibu_50m_river.txt` — channel mask (19,714 cells; every 100 m channel cell
  contains a 50 m channel cell)

The source is the same as data_chichibu (provided by the user on 2026-10-03).

## 500 m data (data_chichibu_500m)

112×60 cells (dx = dy = 500 m) of the same domain. `Chichibu_500m_{filled,basin,river}.txt`
were provided by the user on 2026-10-03 (the elevation agrees with the 5×5
block mean with rms 4.5 m; catchment 2,870 cells). The provided channel mask
covers only the 192 cells of the downstream main stem and does not match the
extent of the 100 m and 200 m channel networks (which include transects 1–3),
so the resolution comparison uses `Chichibu_500m_river_from100m.txt`
(1,270 cells), which aggregates the 100 m channel mask by 5×5 blocks and takes
3 or more cells as channel (param500r_*.txt). The results with the provided
mask as is (param500_*.txt) treat the upstream part as slopes with roughness
0.15 and the peak drops to 1/3–1/6, so they are not used for the scheme
comparison.

The 200 m grid references tutorials/chichibu/data_chichibu through dir_data (param200_*.txt).
