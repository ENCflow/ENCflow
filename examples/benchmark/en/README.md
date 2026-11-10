# benchmark — reference problems of rainfall runoff (comparison with theory, and the check of grid orientation and neighbour count)

> English mirror of examples/benchmark/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Two problems that use only the shallow-water flow and rainfall, with the default settings,
on well-known idealised catchments under uniform rain. Unlike the other examples they do not
show a phenomenon; they **check the basic accuracy of the computation and the properties of
the ENC grid in numbers**. Both compare grid spacings of 20, 10 and 5 m, catchment orientations
of 0° and 45° to the grid, and the ENC eight neighbours (default) against four neighbours
(`p_diagratio = 0`).

| Case | Contents | What is compared |
|---|---|---|
| [v-shaped/](../v-shaped/en/README.md) | A V-shaped catchment (1000 m) in which two 800 m hillslopes drain into a 20 m wide channel, under 10.8 mm/h of rain for 90 min. The validation problem of Tada (2026), and a standard rainfall-runoff problem used to validate many two-dimensional models since Overton & Brakensiek (1973) and Di Giammarco et al. (1996) | The discharges at the outlet and at the hillslope foot against the kinematic-wave theory (computed by `analytic.py`, judged by `check.py`). As a supplement, the differences between the dynamic, diffusive and kinematic wave equations; as an addendum, the effect of the sub-grid channel width on a 40 m grid coarser than the channel |
| [v-valley/](../v-valley/en/README.md) | A V-shaped valley without a channel (valley slope 0.02, hillslope slopes 0.01 to 0.04, 1620 m wide × 1000 m long) under 10.8 mm/h of rain for 60 min | The runoff on a grid rotated by 45°, with the 0° result as the reference. With four neighbours the valley-floor cells become pseudo-depressions whose four neighbours are all higher, and the runoff is delayed (their depth is (√2/2)(S_S − S_V) Δx) |

In both cases `make` generates the inputs (terrain, roughness, masks) with Python, and the
parameter files of the individual cases are generated from the annotated template `param.txt`.
The way of running is the same as in the other examples.

```bash
cd examples/benchmark/v-shaped     # or v-valley
make                               # links, inputs, parameter files (and the theory for v-shaped)
make run                           # all cases (v-shaped: 23 cases, about 40 min; v-valley: 19 cases, about 75 min; 4 threads)
python3 check.py                   # tables of the differences from the theory or the reference and of the water balance (with pass/fail)
python3 plot_results.py            # figures figs/*.png (the argument en writes the English versions to en/figs/)
```

What they do not do: the two problems look only at the core of shallow-water flow plus
rainfall. Infiltration, interception, structures and sediment are not used, and of the channel
features only the sub-grid channel width of the v-shaped addendum. The theory is the kinematic-wave approximation (the channel is integrated numerically
along characteristics), not an exact solution of the shallow-water equations. There is no
comparison with observations of a real catchment. The cases hold no regression reference;
pass or fail is judged by the guide values of `check.py` (such as the normalised root-mean-square
error against the theory).

Related: the two 20 m cases of v-shaped run as a pass/fail check in [test/vshaped](../../../test/vshaped/en/README.md),
also in CI. The comparison of a uniform plane slope with the kinematic wave and the coarse-grid
V-shaped catchment are in [test/hillslope](../../../test/hillslope/en/README.md); the list of
checks of the passage-width adjustment (reassignment of blocked openings) is in
[Passage-width adjustment](../../../docs/en/users_guide/passage_width.md); the original paper
of the ENC grid is Tada (2026)[^tada26].

[^tada26]: Tada, T. (2026): An eight-neighborhood connected collocated grid scheme for overland flow simulation. *Hydrological Research Letters*, 20(2), 113–118. doi:10.3178/hrl.25-00052.
