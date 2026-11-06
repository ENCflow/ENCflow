# test/steepwave — check of the variable gravity g′ of the water-surface gradient term (f_gravity_correction = 3)

> English mirror of test/steepwave/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This is the verification case of the experimental option `f_gravity_correction = 3`
of the steep-slope gravity correction (`&list_enc`; developer.md §100, in Japanese;
docs/en/users_guide/steep_slope.md §2.6). In addition to 2 (the effective gravity
$`g_e = g\cos^2\theta`$ and the slope-parallel friction and sediment shear), 3 replaces
the $`g_e`$ of the water-surface gradient term with the variable gravity of eq. 42 of
Yuan et al. (2016) (for water)

```math
g' = \frac{g}{1 + |\nabla z|^2 + \nabla z\cdot\nabla h} = \frac{g}{1 + \nabla z\cdot\nabla\eta}
```

For a uniform depth it equals $`g_e`$, for a horizontal water surface it returns to
$`g`$ (deep water over a steep bed; option D), and around a uniform flow the
coefficient of the depth gradient downslope becomes the $`g\cos^4\theta`$ of the
thin-layer equations (option E). These three are checked with three configurations:
a lake at rest, a long wave crossing a steep lake bed, and a bump on a uniform layer on
a slope. Pass or fail is decided by the self-check `Check_steepwave.py`, not by a
reference comparison.

## Configuration

| Configuration | Content | Values compared |
|---|---|---|
| lake | 40 m square (Δx = 1 m, 8 neighbours). A planar bed of gradient 1 (45°) tilted 30° from the grid x axis, with a lake at level 0 and the dry shore slope. Manning roughness 0.03, 60 s | 2, 3 |
| wave | 800 m × 32 m (Δx = 2 m, 8 neighbours, walls on the north and south). A flat lake bed 40 m deep → a slope of gradient 0.5 (x = 400–472 m) → a shoal 4 m deep. A Gaussian hump of the water level, 2 cm high and 25 m wide, at x = 250 m; 40 s; no friction. Six probes (x = 381–551 m) | 0, 2, 3 |
| bump | 700 m × 2 m (Δx = 0.5 m, 4 neighbours, free outflow on the east). On a frictionless slope of gradient tan 30°, a uniform layer with a bed-normal thickness of 1 m and a bump 1 cm high (1 % of the thickness) and 4 m wide (along the slope); 6 s | 0, 2, 3 |

| File | Content |
|---|---|
| `make_init.py` | writes the terrain and initial water levels of all cases (`d_<configuration>/`) and the settings `p_<configuration>_g<value>.txt` (the argument `list` prints the case names). The description of the configurations and the constants are at the top, paired with the Check |
| `Check_steepwave.py` | judges (1)–(3) below (the argument `table` also prints the table of values) |

Checks:

1. **lake**: the lake stays at rest (the maxima of the velocity and of the change of
   the water level are at most 1e-12). With both 2 and 3 the force is proportional to
   the water-surface gradient, so it is exactly 0.
2. **wave**: the differences of the arrival times of the crest from probe 1 (on the
   flat part 40 m deep) to each probe agree, with 3, with no correction (0) within
   0.3 % and with the linear long-wave travel time $`\int dx/\sqrt{gh}`$ within 2 %. In
   deep water with a nearly horizontal surface the vertical hydrostatic pressure is
   correct and the uncorrected shallow water equations apply as they are.
3. **bump**: even though the whole layer accelerates at $`g\sin\theta`$, the bump splits
   into two, and their distance grows at $`2\sqrt{g\cos\theta\,h_n}\,t`$ in along-slope
   coordinates (in coordinates moving with the layer, the along-slope thin-layer
   equations are the shallow water equations with gravity $`g\cos\theta`$). The speed of
   growth obtained from the distances at 3 s and 6 s agrees, with 3, with the
   thin-layer equations within 2 %. Taking the difference of the distances cancels the
   motion of the layer.

The values of 2 and 0 are only shown in the table (in theory 2 is late in wave and
$`1/\cos\theta`$ times faster in bump, and 0 is $`1/\cos^2\theta`$ times faster in bump).

## Running

```bash
make            # links to the executables
./Run.sh        # runs the 8 cases and judges them (about 10 seconds with 4 threads)
./Run_MPI.sh 2  # MPI (if Run.sh has been run first, state.dat is compared byte by byte with the serial save)
```

## Results (2026-11-06)

| Configuration | Values | Result |
|---|---|---|
| lake | 2, 3 | 800 wet cells; the maxima of the change of the water level and depth and of the velocity are all 0 |

wave (differences of the arrival times of the crest from probe 1; the lower rows are
ratios to the long-wave travel time):

| x of the probe (m) | 421 | 441 | 461 | 491 | 551 |
|---|---:|---:|---:|---:|---:|
| Depth (m) | 29.5 | 19.5 | 9.5 | 4.0 | 4.0 |
| $`\int dx/\sqrt{gh}`$ (s) | 2.101 | 3.398 | 5.103 | 9.520 | 19.103 |
| 0 (s) | 2.133 | 3.429 | 5.154 | 9.537 | 19.207 |
| 2 (s) | 2.238 | 3.690 | 5.617 | 10.167 | 19.830 |
| 3 (s) | 2.133 | 3.429 | 5.154 | 9.537 | 19.207 |
| Ratio, 0 and 3 | 1.015 | 1.009 | 1.010 | 1.002 | 1.005 |
| Ratio, 2 | 1.065 | 1.086 | 1.101 | 1.068 | 1.038 |

bump (speed at which the distance between the bumps grows; ratio to
$`2\sqrt{g\cos\theta\,h_n}`$ = 5.8265 m/s of the thin-layer equations):

| Value | Distance at 3 s (m) | Distance at 6 s (m) | Speed (m/s) | Ratio | Theory |
|---|---:|---:|---:|---:|---:|
| 0 | 23.479 | 47.130 | 7.884 | 1.353 | $`1/\cos^2\theta`$ = 1.333 |
| 2 | 20.207 | 40.415 | 6.736 | 1.156 | $`1/\cos\theta`$ = 1.155 |
| 3 | 17.417 | 35.026 | 5.870 | 1.007 | 1 |

## Findings

- The wave in deep water over the steep lake bed arrives, with 3, at the same times as
  with no correction in the printed digits, and with 2 it is late over the slope (10 %
  beyond the top of the slope, 4–7 % after it has reached the shoal). The departures of
  0.2–1.5 % of the ratio of 0 and 3 from 1 are common to 0 and 3, and we think they come
  from the change of the shape of the crest (shoaling and reflection from the slope)
  and from numerical dispersion.
- The speed of the waves on the uniform layer on the slope agrees with the thin-layer
  equations within 0.7 % with 3, and 2 and 0 are close to $`1/\cos\theta`$ and
  $`1/\cos^2\theta`$ times as in theory (we think the departure of 1.5 % of 0 is because
  with 0 the acceleration of the layer is also too large, the flow is faster and the
  numerical error is larger).
- During the prototyping we also tried to compare a dam break on a frictionless slope
  (on a dry and on a wet slope) with along-slope analytic solutions (Mangeney et al.
  2000, and the Stoker solution moved to the slope), but in computations where the whole
  layer accelerates beyond 100 km/h the numerical errors around the front and the bore
  were about 10 %, and the difference between 2 and 3 (15 % in theory) could not be
  distinguished, so they are not used in the check (developer.md §100).

## What it cannot do and limits

- 3 is experimental and is not the default (2). At steep fronts and bores the limit
  on $`\nabla z\cdot\nabla h`$ ($`[-|\nabla z|^2, |\nabla z|^2]`$) acts, and the result
  departs from both the thin-layer equations and the formula of Yuan et al. This check
  only looks at smooth flows where the limit does not act (a lake at rest, small
  waves).
- No correction is added on boundary edges. The combination with the non-hydrostatic
  model (`fn_nh`) has not been verified.
- bump is a one-dimensional computation with 4 neighbours. With 8 neighbours the
  diagonal edges are missing on the rows along the north and south walls and fast
  flows get transverse disturbances, so it is not used (rest and waves are checked with
  8 neighbours in lake and wave).

## Related documents

- docs/en/users_guide/steep_slope.md §2.6 (the formula and properties of 3) and §6.2
  (limits); developer.md §100 (design and verification; in Japanese)
- [test/slopefric](../../slopefric/en/README.md) (friction and sediment shear of thin
  flow; 3 also follows the same uniform flow as 2) and
  [test/dbonset](../../dbonset/en/README.md) (rigid sliding on a slope)

## References

- Yuan, L., Liu, W., Zhai, J., Wu, S. F., Patra, A. K. and Pitman, E. B. (2016): Refinement on
  non-hydrostatic shallow granular flow model in a global Cartesian coordinate system.
  arXiv:1602.03299v2 [physics.geo-ph].
- Mangeney, A., Heinrich, P. and Roche, R. (2000): Analytical solution for testing debris avalanche
  numerical models. *Pure Appl. Geophys.*, 157, 1081–1096.
