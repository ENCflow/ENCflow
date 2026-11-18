# test/river_flowline — Check of the preprocessing that moves a channel mask onto the flow lines

> English mirror of test/river_flowline/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of the preprocessing program [utils/river_flowline](../../../utils/river_flowline/en/README.md) (which
moves a channel mask onto the flow lines of the elevation data). No computation is run (encflow is not
used). It checks that the program can rebuild, from the original masks, the moved channel masks placed with
the Chichibu data.

```bash
./Run.sh        # builds utils/river_flowline and runs it (a few seconds)
```

## Check items

1. **Reproduction of the placed masks (text; the four grids of 50, 100, 200 and 500 m).** The mask moved
   from the elevation, the catchment mask and the original channel mask (`…_river.txt`) in the
   `data_chichibu*/` directories of test/chichibu is byte-identical to the placed `…_river_flowline.txt`.
2. **Catchment area.** The largest catchment area of the flow lines (number of cells) equals the number of
   cells of the domain (all four grids have one end point, and every cell drains to it).
3. **bil and GeoTIFF (the 200 m grid; `data_chichibu/` of tutorials/chichibu).** The printed breakdown
   (domain, cells without a lower neighbour, end points, cells of the original and of the moved mask,
   cells that were on the flow lines, removed and added) is the same as for text. The breakdown obtained
   by reading the written file back as the original channel mask and moving it once more is also the same
   as doing the same with text (a check of the content of the written raster).
4. **bil output.** It is byte-identical to the placed `Chichibu_200m_river_flowline.bil`.

## Results

| Grid | Original channel mask → moved mask | Comparison with the placed mask | Largest catchment area = cells of the domain |
|---|---|---|---:|
| 50 m | 19,714 → 14,361 cells | byte-identical | 285,843 |
| 100 m | 9,582 → 6,515 cells | byte-identical | 71,486 |
| 200 m | 2,327 → 1,473 cells | byte-identical (text, bil) | 17,885 |
| 500 m | 192 → 123 cells | byte-identical | 2,870 |

The breakdown of the 200 m grid with bil and GeoTIFF is the same as with text (first pass: 2,327 → 1,473
cells; moving that output once more gives 1,473 → 1,333 cells).

## How to read it, and limits

- It is not a check that compares the correctness of the procedure itself (D8 and Priority-Flood) with
  another implementation. It checks that the placed masks stay identical to the output of the program
  (the same input always gives the same mask).
- The GeoTIFF output is not compared pixel by pixel (it is checked through the breakdown).
- Checked with the default double-precision build (`PREC=double`).

## Related documents

- [utils/river_flowline](../../../utils/river_flowline/en/README.md) — usage, procedure and limits of the program
- [Geographic information](../../../docs/en/users_guide/geoinfo.md) — channel mask `fn_rw`
- developer.md §109 — why and how the channel masks were moved onto the flow lines, and the results
