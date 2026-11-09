# test/wetbank — rain-wetted banks and an oblique raster channel (a check of the artificial brake from the upwind donors of the advection term)

> English mirror of test/wetbank/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This verification case checks that the thin film of water on rain-wetted banks does not change the depth of the
channel next to them. Physically, rain on the banks only adds a little to the channel discharge, and the channel
depth changes only by that amount (with Manning's uniform flow, as the 0.6th power of the discharge).

A channel that runs obliquely to the grid becomes, on a raster, a staircase with steps where the channel shifts one cell
sideways (a 4-connected staircase one cell wide; the same kind as the river mask of tutorials/chichibu). At a step, the
upwind value at the inflow face of the momentum-conservative advection (f_advection_scheme = 3) is taken from the
upstream link on the line along the channel direction, which here is a link of the bank film. The flux of the deep
channel cell multiplied by the slow film velocity makes an artificial brake, which does not occur when the bank is dry
(depth below the threshold depth dd; developer.md §102). This case measures how much extra depth the brake gives the
channel, varying the channel orientation, the grid spacing and the number of cells across the channel. It also measures
how much `f_advection_donor = 3` in `&list_enc` (treat thin donors that carry almost no water as neutral) removes. Pass
or fail is decided by the self-check `Check_wetbank.py`, not by a reference comparison.

## Setup

| Item | Value |
|---|---|
| Channel | From the west edge: an eastward inlet reach (300 m or more) → a straight oblique reach at angle θ to the grid (4 km long) → an eastward outlet reach to the free outflow at the east edge. Bed slope 0.0044, roughness 0.035. Channel cells are those within the band of thickness ω = N·Δx·(cos θ + sin θ) around the centre line (N = 1 gives the 4-connected one-cell staircase) |
| Banks | A 250 m strip on each side of the channel. Ground at bed + 6 m (high enough not to overflow), with a 2 % cross slope towards the channel (rainwater enters the channel at once). Outside is outside the domain |
| Flow | A constant inflow Q0 = 6 m²/s × N·Δx at the upstream end (about 2 m deep in a grid-aligned one-cell channel). Rain cases get a constant 20 mm/h over the whole domain. 3 hours (steady after 1.5 h) |
| Geometries (9) | θ = 0°, 10°, 22.5°, 30°, 45° with Δx = 50 m and one cell; θ = 22.5° one cell with Δx = 100 and 25 m (the channel width is also Δx); θ = 22.5° with a 100 m wide channel resolved by 2 and 4 cells (Δx = 50 and 25 m) |
| Cases (36) | geometry × dry banks (no rain) or rain 20 mm/h × `f_advection_donor` = 0, 3. Names like `a22p5_dx50_n1_r20_o3` = 22.5°, Δx 50 m, one cell, rain 20 mm/h, option 3 |

| File | Contents |
|---|---|
| `make_init.py` | Writes the terrain `d_<geometry>/` (z, domain mask, river mask, distance s along the centre line, info) and the settings `p_<case>.txt` of all cases (the argument `list` prints the case names) |
| `Check_wetbank.py` | Makes the checks below from the last depth output of each case (the argument `table` also prints the table for this README) |

## Checks

The mean depth h of the channel cells in the middle half of the oblique reach is compared between the rain case and the
dry-bank case with the same `f_advection_donor`, and

$$E = \frac{h_{rain}}{h_{dry}} - 1 - 0.6\left(\frac{Q}{Q_0} - 1\right)$$

is taken as the extra depth caused by the wet banks. Q is the discharge at the middle of the reach (the upstream inflow
plus the domain area up to there times the rain intensity), and 0.6 (Q/Q0 − 1) is the depth increase from the rain
inflow. The theoretical value is E = 0.

Pass or fail:

1. Steady: the mean depth of the channel cells of the measured reach changes by less than 1 mm between the last two
   outputs (in the 30° staircase with dry banks, the depth of individual cells keeps fluctuating by about 1 cm, but the
   mean stays within 0.1 mm)
2. Confined to the channel: the depth on the bank cells of the measured reach is below 0.1 m (an assumption of the check)
3. With dry banks, `f_advection_donor` = 0 and 3 give the same depth in every cell
4. In the grid-aligned channel (θ = 0°), |E| ≤ 1 % with either `f_advection_donor`
5. `f_advection_donor = 3` is not worse than 0: E(3) ≤ E(0) + 0.5 % (every geometry)

How far E departs from 0 in the oblique channels (table below) is shown as a limitation and is not used for pass or fail.

## Results

| Orientation θ | Δx | Channel width | Depth with dry banks h (m) | h / h_n | Increase from rain inflow | E(0) | E(3) |
|---|---|---|---|---|---|---|---|
| 0° | 50 m | 1 cell | 1.997 | 0.969 | 1.5 % | 0.2 % | 0.2 % |
| 10° | 50 m | 1 cell | 2.201 | 1.175 | 1.4 % | 13.7 % | 8.5 % |
| 22.5° | 50 m | 1 cell | 2.030 | 1.169 | 1.4 % | 32.4 % | 10.9 % |
| 30° | 50 m | 1 cell | 1.730 | 1.025 | 1.4 % | 37.9 % | 17.0 % |
| 45° | 50 m | 1 cell | 1.554 | 0.941 | 1.4 % | 9.6 % | 8.6 % |
| 22.5° | 100 m | 1 cell | 1.865 | 1.085 | 0.8 % | 23.1 % | 10.4 % |
| 22.5° | 25 m | 1 cell | 2.413 | 1.362 | 2.7 % | 40.4 % | 5.9 % |
| 22.5° | 50 m | 2 cells | 1.811 | 1.054 | 0.8 % | 18.7 % | 8.4 % |
| 22.5° | 25 m | 4 cells | 1.755 | 1.021 | 0.8 % | 12.2 % | 6.6 % |

h_n is Manning's uniform-flow depth of a rectangular section of width ω.

- In the grid-aligned channel, wetting the banks changes the depth only by the rain inflow (E = 0.2 % with both 0 and 3).
- In the oblique channels, `f_advection_donor = 0` makes the channel 10–40 % too deep. The amount depends on the
  orientation (largest around 30°) and grows when the grid is refined with the channel kept one cell wide (at 22.5°,
  23, 32 and 40 % for Δx = 100, 50 and 25 m, because the number of steps per km grows inversely with Δx and the whole
  discharge passes every step). Resolving the same 100 m wide channel with 2 and 4 cells reduces it slowly, to 19 and
  12 %.
- `f_advection_donor = 3` reduces this to 6–17 %, smaller than 0 in every geometry, but not to zero. The main remaining
  cause is the side faces: when the parallel neighbouring link is a bank film (at or above dd), its slow velocity
  becomes the inflow value of the side face (on the side faces, option 3 only smooths the wet/dry switching of films
  thinner than dd). A work build that also
  applies the thin-donor test to the side faces gave 3.6 % or less in every geometry (developer.md §102; not in the
  model).
- The rain intensity hardly matters. Once the banks are wet above dd, rain of 2 mm/h (bank film about 3 mm) gives almost
  the same E as 20 mm/h (about 1 cm): at 22.5° and Δx 50 m, 32.1 / 32.4 % with 0 and 9.1 / 10.9 % with 3
  (developer.md §102). Setting dd to 0.1 mm gives the same values (the films are thicker than dd), so this case does not
  look at the effect of the dd value.

## Limitations

- Even with dry banks, the depth of an oblique one-cell staircase differs from that of a grid-aligned channel
  (h / h_n = 0.94–1.36; at 22.5° it becomes deeper when the grid is refined with the channel kept one cell wide). This is
  a difference in conveyance of the raster staircase itself, independent of `f_advection_donor`, and outside the scope of
  this case.
- Rain falls uniformly on the banks and the channel, and the rainwater on the banks enters the channel at once. The
  momentum exchange when the banks carry flow as a floodplain (an inundated valley floor) is not covered.

## Running

```bash
make         # links to the executables
./Run.sh     # runs the 36 cases and checks them (about 6 minutes with one thread)
```

Related: developer.md §102 (the formulation of f_advection_donor and the results of this case),
[docs/en/users_guide/advection_donor.md](../../../docs/en/users_guide/advection_donor.md), and [test/bendloss](../../bendloss/en/README.md) for 90° bends.
