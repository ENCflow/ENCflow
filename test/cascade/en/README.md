# test/cascade — a steep stepped channel (check that the head of the flow does not exceed the water level at the upstream end)

English mirror of test/cascade/README.md

[日本語](../README.md)

This test looks at a steep channel in which drops and flat reaches alternate. A fast (supercritical) flow runs
up onto low banks directly ahead of the flow or on the inside of bends, and returns to the channel. The
discharge is given at the upstream-end cell with zero velocity, so the head of a nearly steady flow,
$`z + h + V^2/2g`$, should not exceed the water level in the cell where the discharge is given (energy does not
increase along the flow). The test looks at how far the "bed elevation plus the velocity head of the maximum
velocity over the run" in each cell exceeds the water level in the cell where the discharge is given. Its
subjects are the cap on the edge depth of the continuity equation (`f_dry_head_cap` in `&list_enc`) and the
treatment of water entering through side faces (`f_advection_lateral`)
([The cap on the edge depth toward higher ground](../../../docs/en/users_guide/dry_head_cap.md), §4.4 of
[Advection schemes](../../../docs/en/users_guide/advection.md), developer.md §110.29 and §110.30).

**With `f_dry_head_cap = 3` (the default) the excess is within 5 m, about the same as on a terrain whose banks are
turned into walls. With 2 (the default until 2026-11-16) the head exceeds it by 45 m when the banks are dry (recorded
as a limit of 2).**

## Setup

A 43 × 55-cell area, columns 603–645 and rows 364–418, is cut out of the 50 m grid data of
[test/chichibu](../../chichibu/en/README.md) (`make_cascade.py`). The roughness is 0.05 on the hillslopes and
0.02 in the river-mask cells (the hillslope value is that of
[tutorials/chichibu](../../../tutorials/chichibu/en/README.md), the channel value that of the regression case of
test/chichibu), and dt = 0.75 s. The channel is one cell (50 m) wide. The cell numbers in the table below are
(column, row) of the original grid.

| Reach | Cells | Bed (m) |
|---|---|---|
| The cell where the discharge is given and the flat reach downstream of it | (606, 415)–(617, 405) | 353.8, 350.8 |
| A reach of successive drops (35 m down over 11 cells) | (617, 404)–(621, 395) | 343.9 → 315.5 |
| A flat reach | (620, 394)–(615, 391) | 312.8 |
| A reach of successive drops | (614, 391)–(611, 385) | 309.0 → 302.5 |
| A flat reach (a hairpin and a reach oblique to the grid) | (612, 384)–(629, 371) | 293.8, 290.5 |
| A reach of successive drops | (630, 371)–(635, 369) | 280.9 → 268.7 |
| The downstream flat reach (to the east edge) | (636, 369)–(645, 367) | 267.9 |

Here and there along both banks lie cells only 10–15 m above the bed, and the supercritical flow runs up onto
them.

The discharge is given by a source in cell (606, 415): 2,000 m³/s is held until 20 min, then raised to
8,000 m³/s over 120 min and held for 30 min (the run is 170 min). The east edge is a free outflow (the outlet of
the main channel). The transect is column 626 (rows 368–378), crossing the reach with the bed at 290.5 m, and is
recorded every 10 seconds.

| Configuration | File | f_dry_head_cap | f_advection_lateral |
|---|---|---:|---:|
| c2 | `param_c2.txt` | 2 | 0 |
| c3 | `param_c3.txt` | 3 | 0 |
| c3j | `param_c3j.txt` | 3 | 1 |

## Check items (Check_cascade.py)

Items that are judged:

1. Mass balance (all three configurations): the mean discharge at the transect over the last 10 minutes is
   within ±1 % of the given discharge, 8,000 m³/s.
2. The maximum excess (c3 and c3j) is below 10 m. The excess is "bed elevation plus the velocity head of the
   maximum velocity over the run" in each cell minus the maximum water level over the run in the cell where the
   discharge is given (cells whose maximum depth over the run is at least 0.5 m, including cells outside the
   river mask). The depth is not counted, so this is a lower bound of the excess of the head. The limit of 10 m
   is set at a little under twice the value on the terrain whose banks are turned into walls (5.7 m, below); it
   is not derived from theory.

Items that are recorded:

- The maximum excess of c2 (a limit of 2).
- The largest maximum velocity over the run, and where it occurs.

## Values

| Configuration | Discharge at the end (m³/s) | Maximum water level in the cell where the discharge is given (m) | Maximum excess (m) | Its cell (bed, velocity) | Maximum velocity (m/s) |
|---|---:|---:|---:|---|---:|
| c2 (cap 2, side faces 0) | 7,998 | 368.3 | +45.1 | (629, 371) (290.5 m, 49.1 m/s) | 49.1 |
| c3 (cap 3, side faces 0) | 7,979 | 369.5 | +4.4 | (615, 408) (372.4 m, 5.4 m/s) | 36.5 |
| c3j (cap 3, side faces 1) | 7,980 | 368.8 | +4.9 | (618, 400) (336.1 m, 27.1 m/s) | 38.4 |

- **With 2, when the banks are dry, the head exceeds the water level at the upstream end by a large amount.**
  It does so in the reaches with the bed at 290.5–312.8 m, where 7 cells exceed it by 10 m or more. The drop
  from the water level at the upstream end to the reach with the bed at 290.5 m is 78 m, so even without any
  loss the velocity should be at most 39 m/s, but 49 m/s appears.
- **With 3 it hardly exceeds it.** Four cells have a positive excess: cells in the reach of successive drops
  ((618, 400) and (617, 404); +1.8 to 4.9 m), a bank cell whose bed is above the water level at the upstream end
  ((615, 408); bed 372.4 m; 0.6 m of water climbs onto it; +4.4 to 4.8 m), and one cell beside the upstream flat
  reach (+0.1 to 0.6 m). The maximum velocity in the reach with the bed at 290.5–293.8 m is 36–38 m/s, with no
  excess.
- **Even when the bank cells are turned into walls, it exceeds it by 5.7 m.** On a terrain where the cells
  outside the river mask are raised by 300 m (no run-up onto banks), the maximum excess is +5.7 m in all three
  configurations (cell (620, 399) at the foot of the reach of successive drops; 33.5 m/s). The values of 3 are
  about the same as this value (this run is not included in Run.sh). The large excess of 2 appears where the
  supercritical flow runs up onto low banks and returns to the channel.
- **When the banks are wet from rain, 2 does not exceed it either.** With rain (20 mm/h) added to the same run,
  the maximum velocity of c2 is 24 m/s and there is no excess (`f_advection_lateral = 0` uses the slow velocity
  of the water film on the banks as the velocity of the water entering from the side, which brakes the flow in
  the channel; the same holds for c3). c3j (`f_advection_lateral = 1`, which does not count the water film) has
  a maximum velocity of 36 m/s and no excess even with rain. When `f_advection_lateral = 1` is combined with
  2, there is no brake of the water film, so the head exceeds it by +22 m even with rain (44 m/s; +53 m with
  dry banks). These runs are not included in Run.sh either.
- **The difference between 2 and 3 is how the run-up onto banks is counted.** 2 takes the velocity head of the
  cap from the velocity of the edge toward the bank itself. 3 also counts the flow entering the sending cell
  (for a supercritical flow, up to the specific energy of the critical flow of the same discharge). The more
  strongly the run-up is restricted, the larger the excess becomes (in a form that restricts the part of the
  entering flow to half the depth, c3 gives +14 m and c3j +64 m; developer.md §110.29).

## Limits and how to read the results

- This is a test on one reach cut out of a real terrain. It does not imply that no excess appears on other
  terrains.
- Why the excess arises when the run-up onto banks is restricted strongly (which term adds the momentum) has
  not been identified. What is known is that its size changes with how the run-up is counted
  (developer.md §110.29).
- The roughness of 0.02 for river-mask cells is small for a mountain stream with successive drops, and the
  velocity is larger than in reality. The size of the excess depends on this velocity.
- The hydraulic jump at the foot of a drop, the air entrainment and the splash onto the banks cannot be
  represented by depth-averaged equations.

## Running

```bash
make
./Run.sh          # serial (3 configurations; about 20 seconds)
./Run_MPI.sh 2    # MPI (with np = 2 and 4 a band boundary crosses the channel)
```

## References

- The terrain is part of the 50 m grid data of [test/chichibu](../../chichibu/en/README.md) (for the origin of
  the elevation data see [tutorials/chichibu](../../../tutorials/chichibu/en/README.md)).
- The rule of the cap on the edge depth (`f_dry_head_cap`) and the treatment of side faces
  (`f_advection_lateral`) are ENCflow's own
  ([The cap on the edge depth toward higher ground](../../../docs/en/users_guide/dry_head_cap.md) and §4.4 of
  [Advection schemes](../../../docs/en/users_guide/advection.md) in the users guide). That the head of a
  steady flow with losses does not increase along the flow (Bernoulli's theorem and head loss) is standard
  open-channel hydraulics.
