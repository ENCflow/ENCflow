# test/wetbank — rain-wetted banks and an oblique raster channel (a check of the artificial brake from the upwind donors and the lateral faces of the advection term)

> English mirror of test/wetbank/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This verification case checks that the thin film of water on rain-wetted banks does not change the depth of the
channel next to them. Physically, rain on the banks only adds a little to the channel discharge, and the channel
depth changes only by that amount (with Manning's uniform flow, as the 0.6th power of the discharge).

A channel that runs obliquely to the grid becomes, on a raster, a staircase with steps where the channel shifts one cell
sideways (a 4-connected staircase one cell wide; the same kind as the river mask of tutorials/chichibu). At a step, the
momentum-conservative advection (f_advection_scheme = 3) applies the slow velocity of the bank film to the flux of the
deep channel cell in two places. Neither occurs when the bank is dry (depth below the threshold depth dd;
developer.md §102 and §110.25).

- **The upwind donor of the flow-direction faces.** The upwind value at the inflow face is taken from the upstream link
  on the line along the channel direction, which here is a link of the bank film. `f_advection_donor = 3` in `&list_enc`
  (the default) treats thin donors that carry almost no water as neutral.
- **The lateral faces.** The velocity of the water entering from the side is taken from the parallel neighbouring link
  (the bank film). `f_advection_lateral = 1` (the default) does not let a link of a film that is thin compared with the
  entering water represent it.

This case measures how much extra depth the brake gives the channel, varying the channel orientation, the grid spacing
and the number of cells across the channel, and judges that it is small with the default combination. Pass or fail is
decided by the self-check `Check_wetbank.py`, not by a reference comparison.

## Setup

| Item | Value |
|---|---|
| Channel | From the west edge: an eastward inlet reach (300 m or more) → a straight oblique reach at angle θ to the grid (4 km long) → an eastward outlet reach to the free outflow at the east edge. Bed slope 0.0044, roughness 0.035. Channel cells are those within the band of thickness ω = N·Δx·(cos θ + sin θ) around the centre line (N = 1 gives the 4-connected one-cell staircase) |
| Banks | A 250 m strip on each side of the channel. Ground at bed + 6 m (high enough not to overflow), with a 2 % cross slope towards the channel (rainwater enters the channel at once). Outside is outside the domain |
| Flow | A constant inflow Q0 = 6 m²/s × N·Δx at the upstream end (about 2 m deep in a grid-aligned one-cell channel). Rain cases get a constant 20 mm/h over the whole domain. 3 hours (steady after 1.5 h) |
| Geometries (9) | θ = 0°, 10°, 22.5°, 30°, 45° with Δx = 50 m and one cell; θ = 22.5° one cell with Δx = 100 and 25 m (the channel width is also Δx); θ = 22.5° with a 100 m wide channel resolved by 2 and 4 cells (Δx = 50 and 25 m) |
| Cases (54) | geometry × dry banks (no rain) or rain 20 mm/h × three configurations of the advection term. The configurations are `o0` = `f_advection_donor = 0`, `o3` = 3 (lateral faces at the default `f_advection_lateral = 1`; the default combination) and `o3l0` = 3 with `f_advection_lateral = 0` set. Names like `a22p5_dx50_n1_r20_o3` = 22.5°, Δx 50 m, one cell, rain 20 mm/h, o3 |

| File | Contents |
|---|---|
| `make_init.py` | Writes the terrain `d_<geometry>/` (z, domain mask, river mask, distance s along the centre line, info) and the settings `p_<case>.txt` of all cases (the argument `list` prints the case names) |
| `Check_wetbank.py` | Makes the checks below from the last depth output of each case (the argument `table` also prints the table for this README) |

## Checks

The mean depth h of the channel cells in the middle half of the oblique reach is compared between the rain case and the
dry-bank case with the same configuration, and

$$E = \frac{h_{rain}}{h_{dry}} - 1 - 0.6\left(\frac{Q}{Q_0} - 1\right)$$

is taken as the extra depth caused by the wet banks. Q is the discharge at the middle of the reach (the upstream inflow
plus the domain area up to there times the rain intensity), and 0.6 (Q/Q0 − 1) is the depth increase from the rain
inflow. The theoretical value is E = 0.

Pass or fail:

1. Steady: the mean depth of the channel cells of the measured reach changes by less than 1 mm between the last two
   outputs (in the 30° staircase with dry banks, the depth of individual cells keeps fluctuating by about 1 cm, but the
   mean stays within 0.1 mm)
2. Confined to the channel: the depth on the bank cells of the measured reach is below 0.1 m (an assumption of the check)
3. With dry banks, o0 and o3l0 give the same depth in every cell (`f_advection_donor = 3` itself does not change the
   flow with dry banks)
4. In the grid-aligned channel (θ = 0°), |E| ≤ 1 % with every configuration
5. `f_advection_donor = 3` is not worse than 0: E(o3l0) ≤ E(o0) + 0.5 % and E(o3) ≤ E(o0) + 0.5 % (every geometry)
6. With dry banks, the reach-mean depth of the default (o3) agrees with o0 within ±0.1 % (the largest difference in a
   single cell is recorded)
7. With the default (o3) the extra depth caused by wet banks is small: |E(o3)| ≤ 5 % in every geometry

How far E departs from 0 with o0 and o3l0 (table below) is shown as a limitation and is not used for pass or fail. The
0.1 % of item 6 and the 5 % of item 7 are regression bounds set with a margin above the present values (below 0.001 %,
and −0.4 to 3.7 %); they are not derived from theory (the theoretical value is 0).

## Results

| Orientation θ | Δx | Channel width | Depth with dry banks h (m) | h / h_n | Increase from rain inflow | E(0) | E(3, lateral 0) | E(3) = default |
|---|---|---|---|---|---|---|---|---|
| 0° | 50 m | 1 cell | 1.997 | 0.969 | 1.5 % | 0.2 % | 0.2 % | 0.2 % |
| 10° | 50 m | 1 cell | 2.224 | 1.186 | 1.4 % | 12.5 % | 7.4 % | -0.2 % |
| 22.5° | 50 m | 1 cell | 2.024 | 1.166 | 1.4 % | 32.7 % | 10.2 % | 1.4 % |
| 30° | 50 m | 1 cell | 1.718 | 1.018 | 1.4 % | 38.9 % | 17.2 % | 3.7 % |
| 45° | 50 m | 1 cell | 1.554 | 0.941 | 1.4 % | 9.6 % | 8.6 % | 2.4 % |
| 22.5° | 100 m | 1 cell | 1.853 | 1.078 | 0.8 % | 23.9 % | 10.3 % | 2.3 % |
| 22.5° | 25 m | 1 cell | 2.427 | 1.369 | 2.7 % | 39.6 % | 4.3 % | -0.4 % |
| 22.5° | 50 m | 2 cells | 1.807 | 1.051 | 0.8 % | 18.9 % | 8.4 % | 1.4 % |
| 22.5° | 25 m | 4 cells | 1.754 | 1.021 | 0.8 % | 12.3 % | 6.6 % | 0.8 % |

h_n is Manning's uniform-flow depth of a rectangular section of width ω. E(0) is the value of o0, E(3, lateral 0) of
o3l0 and E(3) of o3.

- In the grid-aligned channel one cell wide, wetting the banks changes the depth only by the rain inflow (E = 0.2 %
  with every configuration). Even when grid-aligned, in channels 2 and 4 cells wide (Δx = 50 and 25 m) E is 7.5 and
  9.9 % with 0, 4.6 and 4.7 % with 3 and lateral 0, and 1.8 and 1.3 % with the default (these two geometries are not
  included in Run.sh).
- In the oblique channels, `f_advection_donor = 0` makes the channel 10–40 % too deep. The amount depends on the
  orientation (largest around 30°) and grows when the grid is refined with the channel kept one cell wide (at 22.5°,
  24, 33 and 40 % for Δx = 100, 50 and 25 m, because the number of steps per km grows inversely with Δx and the whole
  discharge passes every step). Resolving the same 100 m wide channel with 2 and 4 cells reduces it slowly, to 19 and
  12 %.
- `f_advection_donor = 3` combined with `f_advection_lateral = 0` for the lateral faces reduces this to 4–17 %, but not
  to zero. The main remaining cause is the lateral faces: when the parallel neighbouring link is a bank film (at or
  above dd), its slow velocity becomes the inflow value of the lateral face (on the lateral faces, option 3 only
  smooths the wet/dry switching of films thinner than dd).
- **With the default combination (3 and `f_advection_lateral = 1`) it is −0.4 to 3.7 %.** A link of a film that is thin
  compared with the entering water is not used as the inflow value of the lateral face. The dilution of the
  main-stream momentum by water entering from the side at a confluence is counted by a separate term that does not
  depend on the wetness of the banks ([test/tjunction](../../tjunction/en/README.md)).
- With dry banks, the reach-mean depth of the default combination is the same as with `f_advection_donor = 0` (the
  difference is below 0.001 %). The depth of individual cells differs by up to 0.05, 0.03 and 0.02 m in the 45°
  staircase and in the channels 2 and 4 cells wide (because `f_advection_lateral = 1` also acts on the lateral faces
  between channel cells). In the other 6 geometries every cell agrees to the printed digits.
- The rain intensity hardly matters. Once the banks are wet above dd, rain of 2 mm/h (bank film 2 mm on average and
  4 mm at most) gives almost the same E as 20 mm/h (6 mm on average and 11 mm at most): at 22.5° and Δx 50 m, 32.5 /
  32.7 % with 0, 8.3 / 10.2 % with 3 and lateral 0, and 0.5 / 1.4 % with the default (the 2 mm/h runs are not included
  in Run.sh). Setting dd to 0.1 mm gives the same values with 0 and with 3 (lateral 0) (the films are thicker than dd;
  developer.md §102), so this case does not look at the effect of the dd value.

## Limitations

- Even with dry banks, the depth of an oblique one-cell staircase differs from that of a grid-aligned channel
  (h / h_n = 0.94–1.37; at 22.5° it becomes deeper when the grid is refined with the channel kept one cell wide). This is
  a difference in conveyance of the raster staircase itself, independent of the configuration of the advection term,
  and outside the scope of this case.
- Rain falls uniformly on the banks and the channel, and the rainwater on the banks enters the channel at once. The
  momentum exchange when the banks carry flow as a floodplain (an inundated valley floor) is not covered.

## Running

```bash
make         # links to the executables
./Run.sh     # runs the 54 cases and checks them (about 9 minutes with one thread)
```

Related: developer.md §102 (the formulation of f_advection_donor) and §110.25 (the formulation of
f_advection_lateral), [docs/en/users_guide/advection_donor.md](../../../docs/en/users_guide/advection_donor.md),
§4.4 of [Advection schemes](../../../docs/en/users_guide/advection.md), and [test/bendloss](../../bendloss/en/README.md) for 90° bends.
