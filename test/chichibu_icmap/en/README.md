# test/chichibu_icmap — Regression case for a windowed domain mask plus a map file

> English mirror of test/chichibu_icmap/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The same Chichibu basin 100 m grid as [test/chichibu](../../chichibu/en/README.md)
(560 × 300; the window of the basin mask is columns 76..501 and part of the
rows) is given the **interception-ratio map of the fixed-interception-ratio
model** `Chichibu_100m_icalpha.txt` (a gradient in the x direction,
α(i) = 0.8 (i−1)/(nx−1)), and 1 hour is computed with rainfall of
200 mm/h × 30 minutes.

## Purpose

This is a regression case that confirms that, when the window of the domain
mask does not start at the grid origin (1,1), **the pathway that distributes
a map file read temporarily over the whole domain to the bands**
(`par_scatter_cell`; the interception ratio, initial snow, ice thickness,
conduits, Green-Ampt, salt water, water quality, meteorology, driftwood,
debris and BMI set_value all share this pattern) is not shifted by the origin
of the window. When the windowing of the allocated extent on 2026-10-16
(developer.md §82) changed the lower bounds of the source dummy arguments,
this pathway alone was left behind, introducing a regression in which the
bands received a map shifted by (ish−1, jwh1−1); no existing case combined
"window + map file", so it was not detected (end of §82; §12). The
interception ratio is a gradient rather than a uniform value so that a shift
changes the result (S changes by about 20%).

## Running

```bash
make
./Run.sh            # serial. Compare Log.txt with the reference (ULP = 1)
./Run_MPI.sh 2      # MPI
```

The reference is created and updated with `./Run.sh -u` after a person has
confirmed the results (absolute rule 1 of CLAUDE.md). Expected behaviour as a
guide: at 1 hour, S ≈ 0.0568 m, h_max ≈ 7.3 m, Q_max ≈ 28 m²/s (smaller than
chichibu without interception).
