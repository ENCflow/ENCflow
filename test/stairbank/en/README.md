# test/stairbank — a one-cell-wide channel oblique to the grid and higher cells beside it (shelves and corner cells)

English mirror of test/stairbank/README.md

[日本語](../README.md)

This test has a one-cell-wide channel oblique to the grid (8-connected, the same type as a D8 flow line) with
cells higher than the bed beside it, onto which water spills when the water level rises. It looks at how the
momentum-conservative advection term (`f_advection_scheme = 3` in `&list_enc`;
[Advection schemes](../../../docs/en/users_guide/advection.md)) treats cells beside the channel that are wet but
hardly flowing.

- **A channel whose banks are all walls that water cannot reach is judged.** The flow is steady, mass is
  balanced, and the depth is the same when the discharge is raised and when it is lowered.
- **For a channel with shelves or corner cells beside it, the values are recorded as limits of the present rules
  (not judged).** Three things appear: two depths at the same discharge, a large backwater just after a stair
  caused by a single corner cell, and a violent oscillation with a gain of energy caused by two corner cells.
  The test serves as a marker for revising the rules of the advection term (developer.md §112).

## Setup

Δx = 50 m, bed slope 0.0065, roughness 0.04 in channel cells and 0.05 elsewhere, dt = 0.75 s. Cells that are not
channel cells are walls 60 m above the bed of the nearest channel cell (water does not reach them). Shelves and
corner cells are cells 10 m above the bed. The discharge is given as a source in the second channel cell from the
upstream end and is held for 30 minutes each at 2,000 → 4,000 → 6,000 → 8,000 → 10,000 → 8,000 → 6,000 → 4,000 →
2,000 m³/s (5 minutes for each change; 270 minutes in total). The east side is a free outflow. The inputs are
made by `make_stairbank.py`.

| Configuration | Grid | Course | Beside the channel |
|---|---|---|---|
| `zw` | 66 × 31 | staircase (8 cells eastward at the entrance, east and northeast alternating 24 times, 8 cells at the exit) | walls only |
| `zs` | 66 × 33 | same | all 8 neighbours of the channel cells are shelves (bed + 10 m) |
| `dw` | 52 × 41 | diagonal (8 cells at the entrance, 34 cells to the northeast, 8 cells at the exit) | walls only |
| `ds` | 52 × 43 | same | shelves |
| `sw` | 51 × 8 | a single stair (24 cells east, 1 cell northeast, 24 cells east) | walls only |
| `sa` | 51 × 8 | same | only corner cell A is open |
| `sab` | 51 × 8 | same | corner cells A and B are open |

In the single-stair shape, call the channel cell before the stair P and the cell just after it Q. Corner cell A
is north of P (= west of Q), and B is east of P (= south of Q). A is the neighbour on the upstream side of the
line of the edge leaving Q eastward, and B lies straight ahead of the edge entering P eastward.

The depth is taken in a channel cell in the middle of the course for `zw`, `zs`, `dw` and `ds`, and in the cell Q
just after the stair for `sw`, `sa` and `sab`. The discharge is taken on a transect crossing that place from
south to north.

## Checks (Check_stairbank.py)

Items judged for the three walls-only configurations (`zw`, `dw`, `sw`):

1. Steadiness: over the last 10 minutes of each stage, the range of the depth is below 0.2 m and the standard
   deviation of the transect discharge is below 1 % of the given discharge.
2. Mass balance: the mean transect discharge over the last 10 minutes of each stage is within ±0.5 % of the
   given discharge.
3. The depths at the same discharge when the discharge is raised and when it is lowered differ by less than
   0.02 m.

Items recorded for the four configurations with shelves or corner cells (`zs`, `ds`, `sa`, `sab`; not judged):

4. The difference in depth at the same discharge between the rising and falling stages, and the difference from
   the walls-only configuration.
5. The largest standard deviation of the transect discharge over the stages.
6. The backwater in the cell just after the stair caused by the corner cells (the difference in depth from `sw`).
7. The maximum velocity in the domain (as a ratio to the walls-only configuration) and the largest depth left on
   wall cells at the end of the run.

## Values

Depth (m) over the last 10 minutes of each stage. ↑ is a rising stage and ↓ a falling stage.

| Configuration | 2,000↑ | 4,000↑ | 6,000↑ | 8,000↑ | 10,000 | 8,000↓ | 6,000↓ | 4,000↓ | 2,000↓ | Largest standard deviation of the discharge (m³/s) | Maximum velocity (m/s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `zw` | 6.60 | 10.00 | 12.76 | 15.17 | 17.34 | 15.17 | 12.76 | 10.00 | 6.60 | 0 | 13.7 |
| `zs` | 8.05 | 11.97 | 12.87 | 13.78 | 14.60 | 13.78 | 12.87 | 11.97 | 10.38 | 100 | 13.9 |
| `dw` | 7.39 | 11.21 | 14.29 | 16.98 | 19.39 | 16.98 | 14.29 | 11.21 | 7.39 | 0 | 16.6 |
| `ds` | 7.39 | 12.47 | 13.65 | 14.46 | 15.54 | 14.46 | 13.67 | 12.54 | 7.94 | 277 | 13.8 |
| `sw` | 6.19 | 9.39 | 11.97 | 14.21 | 16.23 | 14.21 | 11.97 | 9.39 | 6.19 | 22 | 13.9 |
| `sa` | 6.19 | 9.39 | 19.41 | 23.59 | 27.45 | 23.60 | 19.42 | 14.73 | 6.29 | 53 | 12.7 |
| `sab` | 6.19 | 11.42 | 14.53 | 25.74 | 29.01 | 25.92 | 22.43 | 18.09 | 6.34 | 1,222 | 29.5 |

- **A walls-only channel is steady and has the same depth on the rising and falling stages** (items 1–3). The
  diagonal channel is deeper than the staircase channel because the passage width of a diagonal link is 0.707
  times the grid spacing ([ENC grid](../../../docs/en/users_guide/encgrid.md)).
- **The staircase channel with shelves (`zs`) has two depths at the same 2,000 m³/s.** With walls only it is
  6.60 m, but when the discharge is lowered it stays at 10.38 m (the water on the shelves is about 1 m deep). The
  8.05 m on the rising stage is a value taken while the deep state is still spreading from upstream. At
  4,000 m³/s, too, it is 2 m deeper than with walls only (10.00 m, where the water level is at the height of the
  shelves). In the diagonal channel with shelves (`ds`) the discharge keeps oscillating at 6,000 m³/s (standard
  deviation 277 m³/s).
- **A single corner cell (`sa`) makes the cell just after the stair 7–11 m deeper** (6,000–10,000 m³/s). Corner
  cell A is 3–8 m deep and hardly flowing. At 4,000 m³/s the depth differs between the rising stage (9.39 m) and
  the falling stage (14.73 m).
- **With two corner cells (`sab`) the flow oscillates violently at 8,000 m³/s and above, and energy is gained.**
  The standard deviation of the discharge is 1,222 m³/s, the maximum velocity in the domain reaches 29.5 m/s
  (13.9 m/s with walls only), and water climbs onto wall cells 60 m above the bed (up to 6.3 m of water is left
  on wall cells at the end of the run). The energy head of the flow upstream (a depth of 16 m plus a velocity
  head of 8 m) cannot reach that height.

## What is happening (limits of the present rules)

The momentum-conservative advection term takes the velocity of the water entering the control volume around an
edge (the upwind value) from the velocity of the link on the upstream side of the line of the edge. When the flow
is resolved by the grid, this counts it correctly. At a stair of a one-cell-wide channel, most of the water at
the face comes through a diagonal link, and the link on the upstream side of the line leads only to a bank or a
corner cell.

- If the cell on the upstream side of the line is a wall or dry, the advection term is neutral (no loss at a
  bend). If it is wet and at least a tenth as deep as the face cell, the slow velocity of that link is applied to
  the whole discharge passing the face (`f_advection_donor = 3` in §4.4 of
  [Advection schemes](../../../docs/en/users_guide/advection.md)). This switch becomes an artificial brake when
  shelves or corner cells get wet, and because the brake strengthens as the water deepens, two depths arise at
  the same discharge (`zs`, `sa`).
- An edge leaving a corner cell has a wall on the upstream side of its line, so no inertia is counted for it. It
  flows at the velocity set by the water-surface slope and friction alone, so once water starts circulating among
  the two corner cells and the channel cells, the velocity rises without the bound set by energy (`sab`).

The two depths at the same discharge (`zs`) appear with any of `f_advection_lateral = 0`, `f_advection_donor = 0`
and scheme 1. The oscillation with two corner cells (`sab`) stops with `f_advection_lateral = 0`, but the
backwater just after the stair (4 m deeper than with walls only at 8,000 m³/s) and a large maximum velocity
(29.8 m/s) remain (the values in this paragraph come from runs outside the configurations of this test;
developer.md §112.1 and §112.2). The same mechanism is also involved in the ups and downs of the transect
discharge at high discharge on the 50 m grid of the Chichibu basin
([supplement of the chichibu tutorial](../../../tutorials/chichibu/en/README.md); developer.md §111.14).

## Running

```bash
./Run.sh           # serial (about 1 minute for the 7 configurations)
./Run_MPI.sh 2     # MPI
```

An oblique channel with thinly wet banks is checked by [test/wetbank](../../wetbank/en/README.md), the loss at a
confluence by [test/tjunction](../../tjunction/en/README.md), and the loss at a bend by
[test/bendloss](../../bendloss/en/README.md).
