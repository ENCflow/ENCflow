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
treatment of water entering through side faces (`f_advection_lateral`) (§4.4 and §5 of
[Advection schemes](../../../docs/en/users_guide/advection.md), developer.md §110.29).

**With the present rules the head exceeds the water level at the upstream end in every configuration (by
14–64 m).** The excess is only recorded; what is judged is the mass balance.

## Setup

A 43 × 55-cell area, columns 603–645 and rows 364–418, is cut out of the 50 m grid data of
[test/chichibu](../../chichibu/en/README.md) (`make_cascade.py`). The roughness is the same as in the 50 m grid
runs of [tutorials/chichibu](../../../tutorials/chichibu/en/README.md) (hillslopes 0.05, river-mask cells 0.02),
and dt = 0.75 s. The channel is one cell (50 m) wide. The cell numbers in the table below are (column, row) of
the original grid.

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

Items that are judged (all three configurations):

1. Mass balance: the mean discharge at the transect over the last 10 minutes is within ±1 % of the given
   discharge, 8,000 m³/s.

Items that are recorded:

2. The maximum excess: the maximum of "bed elevation plus the velocity head of the maximum velocity over the
   run" in each cell minus the maximum water level over the run in the cell where the discharge is given (cells
   whose maximum depth over the run is at least 0.5 m, including cells outside the river mask). The depth is not
   counted, so this is a lower bound of the excess of the head.
3. The largest maximum velocity over the run, and where it occurs.

## Values

| Configuration | Discharge at the end (m³/s) | Maximum water level in the cell where the discharge is given (m) | Maximum excess (m) | Its cell (bed, velocity) | Maximum velocity (m/s) |
|---|---:|---:|---:|---|---:|
| c2 (cap 2, side faces 0) | 7,998 | 368.3 | +45.1 | (629, 371) (290.5 m, 49.1 m/s) | 49.1 |
| c3 (cap 3, side faces 0) | 7,997 | 368.3 | +14.0 | (623, 375) (293.8 m, 41.7 m/s) | 41.7 |
| c3j (cap 3, side faces 1) | 7,996 | 368.2 | +63.9 | (624, 374) (293.8 m, 52.1 m/s) | 52.1 |

- **In all three configurations the head exceeds the water level at the upstream end.** It does so in the part
  of the flat reach with the bed at 290.5–293.8 m that runs obliquely to the grid. The drop from the water level
  at the upstream end to the bed of this reach is 75–78 m, so even without any loss the velocity should be at
  most 38–39 m/s, but 42–52 m/s appears.
- **When the bank cells are turned into walls, the excess becomes small.** On a terrain where the cells outside
  the river mask are raised by 300 m (no run-up onto banks), the maximum excess is +5.7 m (cell (620, 399) at
  the foot of the reach of successive drops; 33.5 m/s), the same for c2 and c3j (this run is not included in
  Run.sh). The excess appears where the supercritical flow runs up onto low banks and returns to the channel.
- **When the banks are wet from rain, c2 does not exceed it.** With rain (20 mm/h) added to the same run, the
  maximum velocity of c2 is 24 m/s and there is no excess (`f_advection_lateral = 0` uses the slow velocity of
  the water film on the banks as the velocity of the water entering from the side, which brakes the flow in the
  channel; the same holds for c3). `f_advection_lateral = 1` does not count the water film, so c3j exceeds it
  even with rain (maximum velocity 47 m/s, excess +36 m). This run is not included in Run.sh either.

## Limits and how to read the results

- This is a test on one reach cut out of a real terrain. It does not imply that no excess appears on other
  terrains.
- Why the excess arises (which term adds the momentum) has not been identified. What is known is that its size
  changes with how the run-up onto banks is counted (developer.md §110.29).
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
  (`f_advection_lateral`) are ENCflow's own (§4.4 and §5 of
  [Advection schemes](../../../docs/en/users_guide/advection.md) in the users guide). That the head of a
  steady flow with losses does not increase along the flow (Bernoulli's theorem and head loss) is standard
  open-channel hydraulics.
