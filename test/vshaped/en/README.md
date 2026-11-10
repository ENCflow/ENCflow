# test/vshaped — check of the rainfall runoff of a V-shaped catchment against the kinematic-wave theory (20 m grid, orientations 0° and 45°)

> English mirror of test/vshaped/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A V-shaped catchment in which two 800 m hillslopes drain into a 20 m wide channel (the standard
rainfall-runoff problem since Overton & Brakensiek 1973 and Di Giammarco et al. 1996; the validation
problem of Tada 2026, the original paper of the ENC grid) receives 10.8 mm/h of rain for 90 min, and
the discharges at the outlet and at the hillslope foot are compared with the kinematic-wave theory to
give a pass or fail. The case runs the two 20 m cases of
[examples/benchmark/v-shaped](../../../examples/benchmark/v-shaped/en/README.md) (the catchment at 0°
and at 45° to the grid) as an environment-independent check without a reference. All shallow-water
settings are the defaults.

## Set-up

| Item | Value |
|---|---|
| Terrain | hillslopes 2 × 800 m (slope 0.05 toward the channel, 0 along it, n = 0.015), channel 1000 m × 20 m (slope 0.02, n = 0.15; 1 m below the hillslope foot at the upstream end, 21 m at the outlet). Downstream of the catchment the same cross-section (hillslopes and channel, rained on) continues for 200 m, followed by 3 cells of channel extension and 3 sea cells (sink at elevation 0 m and depth 1 m). The channel depth rises in the few cells before the hillslopes end, and this section keeps the outlet face clear of that effect. Outside the rectangles of the catchment and the downstream section is outside the domain |
| Grid | Δx = 20 m. `param_r0.txt` has the channel along a grid axis (0°, 68 × 83); `param_r45.txt` has the catchment rotated by 45° (107 × 107; the channel is a single diagonal row of cells that touch only at their corners) |
| Rain and time | 10.8 mm/h everywhere for 90 min, 3 hours computed. dt = 2 s |
| Measurement | outlet: a transect across the downstream row of the catchment from ridge to ridge (edge-flux method, full width). Hillslope foot: the row of left-side hillslope cells next to the channel. Every minute. The depth probes (the outlet channel cell and the second hillslope cell from the channel) are not used in the verdict |
| Input generation | `make_init.py` (standard library only) evaluates the equations in the catchment coordinates at the cell centres and writes `data_r0/` and `data_r45/`. An implementation independent of the examples' `make_inputs.py` (NumPy), with identical output |

Theory (computed by `Check_vshaped.py` with the standard library only): the closed-form kinematic
wave on the hillslope (equilibrium reached at 29.4 min, equilibrium 2.40 m³/s), and the kinematic wave
with lateral inflow in the channel integrated numerically along characteristics (wide channel; outlet
peak 4.86 m³/s = i (2BL + WL), half of the peak reached at 39 min). The equations are explained in the
README of examples/benchmark/v-shaped.

## Running

```bash
make
./Run.sh          # generate inputs → run the 2 cases (7 s each) → Check_vshaped.py (PASS when both pass)
./Run_MPI.sh 2    # MPI with 2 ranks: the comparison with the theory plus a byte comparison of the transect CSVs with the serial result (result_serial)
```

## Verdict (Check_vshaped.py)

| Measure | Guide value |
|---|---|
| NRMSE of the outlet discharge (root-mean-square error from the theory / theoretical peak 4.86 m³/s) | ≤ 0.04 |
| NRMSE of the hillslope-foot discharge (/ 2.40 m³/s) | ≤ 0.04 |
| grid ratio = outlet peak / (rainfall intensity × catchment area on the grid) | 1 ± 0.01 |
| t50 = time at which half of the theoretical peak is first reached | theory (39 min) ± 3 min |
| balance = (water through the outlet + water left in the catchment at the end) / rain on the catchment | 1 ± 0.01 |

The grid ratio uses the catchment area on the grid because at 45° the area assigned by cell centres is
0.8 % larger than 1.62 km² and the peak scales with it.

## Findings (gfortran 13.3, serial with 4 threads)

| Case | NRMSE outlet | NRMSE hillslope | peak (m³/s) | grid ratio | t50 (min) | balance | verdict |
|---|---|---|---|---|---|---|---|
| 0° (`param_r0.txt`) | 0.019 | 0.021 | 4.860 | 1.000 | 40 | 0.998 | PASS |
| 45° (`param_r45.txt`) | 0.020 | 0.025 | 4.898 | 1.000 | 37 | 0.999 | PASS |

- In both orientations the outlet discharge follows the theory, and rotating the catchment by 45° does
  not change the result (the diagonal edges of the eight neighbours connect the single diagonal row of
  channel cells). The NRMSE of 0.02 comes from a shift of the rise by 1 to 2 min (late at 0°, early at 45°)
  and from the approximation on the theory side (kinematic wave).
- With four neighbours (`p_diagratio = 0`) at 45° the channel cells touch only at corners and the runoff
  is zero. That property is shown by the comparison cases of examples/benchmark/v-shaped (it is not part
  of this check).

What it does not do: the theory is the kinematic-wave approximation, not an exact solution of the
shallow-water equations, so the guide values check that the difference from the theory stays below this
level. Depths (1.3 times the theory in the single diagonal row of channel cells, 1.5 to 1.8 times in the
first hillslope cell next to the channel) are not part of the verdict. Grid convergence, the governing
equations, four neighbours and the sub-grid channel width are examined on the examples side.

## Related

- [examples/benchmark/v-shaped](../../../examples/benchmark/v-shaped/en/README.md): grids of 20, 10 and 5 m, four
  neighbours, governing equations, figures; the equations and sources of the theory.
- [test/hillslope](../../hillslope/en/README.md): the kinematic wave on a uniform plane slope and a V-shaped catchment on coarse grids.
- [Passage-width adjustment](../../../docs/en/users_guide/passage_width.md), [Diagonal share](../../../docs/en/users_guide/diagratio.md).
