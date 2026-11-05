# test/slopefric — friction and sediment shear of thin flow on a steep slope (slope-parallel speed and bed-normal depth)

> English mirror of test/slopefric/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A verification case for the **uniform flow** of the steep-slope gravity
correction (`f_gravity_correction` in `&list_enc`).

- `f_gravity_correction = 1` (default): the effective gravity
  $`g_e = g\cos^2\theta`$ multiplies both the slope term and the friction and
  cancels, so uniform flow follows the classical horizontally projected Manning
  formula $`h = (n^2q^2/\tan\theta)^{3/10}`$ ($`h`$ is the vertical depth and
  $`q = h|\mathbf V|`$ the horizontal unit discharge; developer.md §91,
  docs/steep_slope_design.md §2.3).
- `f_gravity_correction = 2`: the friction and the sediment shear are evaluated
  from the slope-parallel speed and the bed-normal depth $`h\cos\theta`$
  (developer.md §93). Uniform flow then follows the along-slope equations,
  $`h\cos\theta = (n^2q^2/\sin\theta)^{3/10}`$ (Chow 1959; Van Emelen et al. 2014).

The case checks against analytic solutions that these two relations hold for
every combination of the slope direction (0°, 22.5° and 45° from the x axis of
the grid) and eight or four neighbours, and that with 2 the sediment shear (the
onset of bedload) follows the along-slope bed shear stress
$`\tau_b = \rho g\,h\cos\theta\,\sin\theta`$. Pass/fail is decided by the
self-check `Check_slopefric.py`, not by a reference comparison (the same type as
test/dbonset).

## Setup

| Item | Value |
|---|---|
| Terrain | A uniform slope 60 m square (slope angle 30°, gradient 0.5774, downslope direction φ). The upslope sides (west and south) are walls; the downslope sides (east, and north when φ > 0) are free outflow (`make_init.py` writes `d_<φ>/z.txt`) |
| Grid | 60 × 60 cells (Δx = 1 m). Eight neighbours (default `p_diagratio`) and four neighbours (`p_diagratio = 0`) |
| Flow | Constant rain of 300 mm/h over the whole slope, Manning's roughness 0.1, dt = 0.1 s, 20 minutes (about ten travel times; steady) |
| Cases | Flow: φ = 0°, 22.5°, 45° × eight/four neighbours × `f_gravity_correction` 1/2, 12 cases (a name such as `p22p5_n8_g2` = 22.5°, eight neighbours, 2). Sediment: φ = 0°, 45° × 1/2, 4 cases (eight neighbours; names end in `_sed`) |
| Sediment setup | Bedload on the same slope as the flow (`f_fluvial = 1`, Ashida–Michiue, τ*c = 0.05, s = 1.65, grain size 0.0515 m, movable layer 1 m). The grain size puts the onset of erosion with 2 at a horizontal downslope distance of 30 m. `morfac = 0.02` keeps the bed change small |

| File | Content |
|---|---|
| `make_init.py` | Writes the terrain `d_<φ>/z.txt` and the settings `p_<case>.txt` of all cases (argument `list` prints the case names). The constants and the analytic onset `sed_lc` pair with the check |
| `Check_slopefric.py` | Reads the last output of each case (H, u, v, Z) and judges (1)–(4) below (argument `table` also prints the values) |

Checks:

1. Uniform-flow relation: on cells at least 5 cells from the walls and the
   outflow sides and at least 8 mm deep, the mean of $`h/h_{analytic}(q)`$ from
   $`h`$ and $`q = h|\mathbf V|`$ is within 0.5 % of 1 and every cell within
   1.5 % (the classical formula for 1, the along-slope formula for 2)
2. Independent of direction and neighbours: (1) holds for every φ and
   neighbourhood
3. Discriminating power: the depth of 2 measured with the formula of 1 is
   $`\cos^{-13/10}30° = 1.206`$ times larger (the two formulas can be told apart)
4. Sediment shear: the horizontal downslope distance where erosion starts
   matches the position ℓ_c where the dimensionless shear stress reaches τ*c
   (1: classical $`\tau_* = h\tan\theta/(s\,d)`$, 25.37 m; 2: along-slope
   $`\tau_* = h\cos\theta\,\sin\theta/(s\,d)`$, 30.00 m). No erosion upslope of
   ℓ_c − 1.5 m, erosion on every cell at ℓ_c + 2 to 6 m (on the 45° slope the
   cells within 3 m of the flow line through the upper corner are left out)

The depth is printed with four decimals (0.1 mm), so (1) compares cells at least
8 mm deep, where the rounding stays below 1 %.

## Running

```bash
make            # links to the executables
./Run.sh        # runs the 16 cases and checks them (about 5 minutes on four threads)
./Run_MPI.sh 2  # MPI (run Run.sh first to compare state.dat byte by byte with the serial save)
```

The byte comparison with MPI is meaningful when both the serial and the MPI
executables are built with -O2 (strict math). With the default -Ofast build, the
difference between the serial and the MPI builds can change the last digits of
some cases (the sediment cases with 2) (developer.md §28.3, §93).

## Results (2026-11-05)

| Case | φ | Neighbours | f_gravity_correction | Cells | mean of $`h/h_{analytic}`$ | min | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| p0_n8_g1 | 0° | 8 | 1 | 1350 | 1.0033 | 1.0007 | 1.0061 |
| p0_n4_g1 | 0° | 4 | 1 | 1350 | 1.0033 | 1.0007 | 1.0061 |
| p22p5_n8_g1 | 22.5° | 8 | 1 | 1275 | 1.0033 | 1.0007 | 1.0085 |
| p22p5_n4_g1 | 22.5° | 4 | 1 | 1261 | 1.0026 | 0.9994 | 1.0063 |
| p45_n8_g1 | 45° | 8 | 1 | 1213 | 1.0033 | 1.0007 | 1.0070 |
| p45_n4_g1 | 45° | 4 | 1 | 1198 | 1.0022 | 0.9998 | 1.0052 |
| p0_n8_g2 | 0° | 8 | 2 | 1700 | 1.0035 | 1.0011 | 1.0071 |
| p0_n4_g2 | 0° | 4 | 2 | 1700 | 1.0035 | 1.0011 | 1.0071 |
| p22p5_n8_g2 | 22.5° | 8 | 2 | 1706 | 1.0040 | 1.0009 | 1.0105 |
| p22p5_n4_g2 | 22.5° | 4 | 2 | 1694 | 1.0030 | 0.9998 | 1.0077 |
| p45_n8_g2 | 45° | 8 | 2 | 1661 | 1.0040 | 1.0008 | 1.0087 |
| p45_n4_g2 | 45° | 4 | 2 | 1644 | 1.0025 | 1.0001 | 1.0066 |

| Case | φ | f_gravity_correction | ℓ_c (m) | Onset of erosion (m) | Eroded upslope | Not eroded in the downslope band |
|---|---:|---:|---:|---:|---:|---:|
| p0_n8_g1_sed | 0° | 1 | 25.37 | 25.50 | 0 / 950 | 0 / 200 |
| p45_n8_g1_sed | 45° | 1 | 25.37 | 26.16 | 0 / 948 | 0 / 180 |
| p0_n8_g2_sed | 0° | 2 | 30.00 | 31.50 | 0 / 1200 | 0 / 200 |
| p45_n8_g2_sed | 45° | 2 | 30.00 | 30.41 | 0 / 1140 | 0 / 106 |

## Findings

- For the same discharge, 2 gives a vertical depth 1.206 times larger and a
  smaller horizontal velocity than 1 (30°). The small departure of the ratio from
  1 (+0.2 to 0.4 %) comes from the depth gradient and advection, which make the
  local balance not exactly that of uniform flow, and from the rounding of the
  printed depth.
- Erosion starts at 30 m with 2 and at 25 m with 1, which shows the different
  evaluation of the sediment shear directly. Without the slope factor of the
  sediment shear, erosion with 2 would start at about 52 m (an estimate: the
  dimensionless shear stress becomes $`\cos^{7/3}30° = 0.715`$ times smaller).
- With `morfac = 1` over 20 minutes the downstream bed changes by tens of times
  the flow depth and headcuts and deposits appear, so `morfac = 0.02` is used to
  look only at the position of the onset.
- On the 45° slope, near the flow line through the upper corner (where the flow
  lines from the west and south walls meet) the flow is shallower because of
  lateral spreading and erosion starts one cell later. This is a property of the
  test terrain, so these cells are left out of the check.

## What it does not cover, and limits

- Only uniform flow on a uniform slope is tested. The centrifugal acceleration
  on slopes whose gradient changes (convex or concave), deep water over a steep
  bed and the coefficient of the pressure term (wave speed) are not covered
  (docs/steep_slope_design.md §6).
- The factor of 2 does not apply to the resistance laws of mixture flows
  (debris flows and others; developer.md §93).
- Flow down steps (walls, kerbs, steps in the DEM) is not covered. On a step of a
  single edge the field gradient (minmod) is nearly zero, so 2 is treated as 1
  there (developer.md §93).
