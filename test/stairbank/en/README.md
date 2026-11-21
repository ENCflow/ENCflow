# test/stairbank — a one-cell-wide channel oblique to the grid and higher cells beside it (shelves and corner cells)

English mirror of test/stairbank/README.md

[日本語](../README.md)

This test has a one-cell-wide channel oblique to the grid (8-connected, the same type as a D8 flow line) with
cells higher than the bed beside it, onto which water spills when the water level rises. It looks at how the
momentum-conservative advection term (`f_advection_scheme = 3` in `&list_enc`;
[Advection schemes](../../../docs/en/users_guide/advection.md)) treats cells beside the channel that are wet but
hardly flowing. The same shapes are computed with the combination of the old values (`f_advection_donor = 3`,
`f_advection_bend = 1`, `f_advection_lateral = 1`, `f_dry_head_cap = 3`) and with a combination of four values in
`&list_enc` (`f_advection_donor = 4`, `f_advection_bend = 2`, `f_advection_lateral = 2`, `f_dry_head_cap = 4`;
[Advection schemes](../../../docs/en/users_guide/advection.md) §4.4). Every configuration states all four switches
(none depends on the defaults).

- **A channel whose banks are all walls that water cannot reach is judged with both sets of rules.** The flow is
  steady, mass is balanced, and the depth is the same when the discharge is raised and when it is lowered. The
  combination of the four values gives the same depths as the combination of the old values.
- **For a channel with shelves or corner cells beside it, the values with the combination of the old values are
  recorded as limits of those rules (not judged).** Three things appear: two depths at the same discharge, a large
  backwater just after a stair caused by a single corner cell, and a violent oscillation with a gain of energy caused
  by two corner cells.
- **With the combination of the four values, the test judges that these three do not appear.** The depth is the
  same on the rising and falling stages, the maximum velocity does not exceed that of the walls-only channel, and
  water does not climb onto wall cells. A difference in depth from the walls-only channel remains and is recorded
  as a limit.

## Setup

Δx = 50 m, bed slope 0.0065, roughness 0.04 in channel cells and 0.05 elsewhere, dt = 0.75 s. Cells that are not
channel cells are walls 60 m above the bed of the nearest channel cell (water does not reach them). Shelves and
corner cells are cells 10 m above the bed. The discharge is given as a source in the second channel cell from the
upstream end and is held for 30 minutes each at 2,000 → 4,000 → 6,000 → 8,000 → 10,000 → 8,000 → 6,000 → 4,000 →
2,000 m³/s (5 minutes for each change; only the last 2,000 m³/s is held for 90 minutes; 330 minutes in total). The
last stage is long because the water on the shelves takes about an hour to drain back into the channel. The east
side is a free outflow. The inputs are made by `make_stairbank.py`.

| Shape | Grid | Course | Beside the channel |
|---|---|---|---|
| `zw` | 66 × 31 | staircase (8 cells eastward at the entrance, east and northeast alternating 24 times, 8 cells at the exit) | walls only |
| `zs` | 66 × 33 | same | all 8 neighbours of the channel cells are shelves (bed + 10 m) |
| `dw` | 52 × 41 | diagonal (8 cells at the entrance, 34 cells to the northeast, 8 cells at the exit) | walls only |
| `ds` | 52 × 43 | same | shelves |
| `sw` | 51 × 8 | a single stair (24 cells east, 1 cell northeast, 24 cells east) | walls only |
| `sa` | 51 × 8 | same | only corner cell A is open |
| `sab` | 51 × 8 | same | corner cells A and B are open |

There are 14 configurations: the 7 shapes × 2 sets of rules. A configuration with the combination of the old
values has the name of the shape itself (`zs`); one with the combination of the four values has a 4 appended
(`zs4`).

In the single-stair shape, call the channel cell before the stair P and the cell just after it Q. Corner cell A
is north of P (= west of Q), and B is east of P (= south of Q). A is the neighbour on the upstream side of the
line of the edge leaving Q eastward, and B lies straight ahead of the edge entering P eastward.

The depth is taken in a channel cell in the middle of the course for `zw`, `zs`, `dw` and `ds`, and in the cell Q
just after the stair for `sw`, `sa` and `sab`. The discharge is taken on a transect crossing that place from
south to north.

## Checks (Check_stairbank.py)

Items judged for the three walls-only shapes (`zw`, `dw`, `sw`) with both sets of rules:

1. Steadiness: over the last 10 minutes of each stage, the range of the depth is below 0.2 m and the standard
   deviation of the transect discharge is below 1 % of the given discharge.
2. Mass balance: the mean transect discharge over the last 10 minutes of each stage is within ±0.5 % of the
   given discharge.
3. The depths at the same discharge when the discharge is raised and when it is lowered differ by less than
   0.02 m.

Items recorded for the four shapes with shelves or corner cells (`zs`, `ds`, `sa`, `sab`) computed with the
combination of the old values (not judged):

4. The difference in depth at the same discharge between the rising and falling stages, and the difference from
   the walls-only shape.
5. The largest standard deviation of the transect discharge over the stages.
6. The backwater in the cell just after the stair caused by the corner cells (the difference in depth from `sw`).
7. The maximum velocity in the domain (as a ratio to the walls-only shape) and the largest depth left on wall
   cells at the end of the run.

Items judged with the combination of the four values (configuration names ending in 4):

8. The walls-only shapes (`zw4`, `dw4`, `sw4`) have the same depths as with the combination of the old values (difference below
   0.02 m).
9. In the shapes with shelves or corner cells (`zs4`, `ds4`, `sa4`, `sab4`), the depths at the same discharge on
   the rising and falling stages differ by less than 0.5 m (no two depths at the same discharge).
10. In the same shapes, energy is not gained: the maximum velocity in the domain is at most 1.1 times that of the
    walls-only shape, and no water is left on wall cells at the end of the run (below 0.01 m).
11. In the same shapes, the standard deviation of the transect discharge in each stage is below 5 % of the given
    discharge.

The thresholds of items 9–11 are regression bounds set with a margin over the present values (the table below);
they are not derived from theory.

## Values

Depth (m) over the last 10 minutes of each stage. ↑ is a rising stage and ↓ a falling stage. The three walls-only
shapes have the same values with the combination of the four values (difference below 0.001 m), so each is shown
in one row.

| Configuration | 2,000↑ | 4,000↑ | 6,000↑ | 8,000↑ | 10,000 | 8,000↓ | 6,000↓ | 4,000↓ | 2,000↓ | Largest standard deviation of the discharge (m³/s) | Maximum velocity (m/s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `zw`, `zw4` | 6.60 | 10.00 | 12.76 | 15.17 | 17.34 | 15.17 | 12.76 | 10.00 | 6.60 | 0 | 13.7 |
| `dw`, `dw4` | 7.39 | 11.21 | 14.29 | 16.98 | 19.39 | 16.98 | 14.29 | 11.21 | 7.39 | 0 | 16.6 |
| `sw`, `sw4` | 6.19 | 9.39 | 11.97 | 14.21 | 16.23 | 14.21 | 11.97 | 9.39 | 6.19 | 22 | 13.9 |
| `zs` | 8.05 | 11.97 | 12.87 | 13.78 | 14.60 | 13.78 | 12.87 | 11.97 | 10.37 | 100 | 13.9 |
| `zs4` | 6.60 | 12.20 | 13.46 | 14.58 | 15.60 | 14.58 | 13.46 | 12.22 | 6.60 | 10 | 13.3 |
| `ds` | 7.39 | 12.47 | 13.65 | 14.46 | 15.54 | 14.46 | 13.67 | 12.54 | 7.40 | 277 | 13.8 |
| `ds4` | 7.39 | 11.91 | 14.07 | 14.71 | 15.98 | 14.72 | 14.07 | 12.21 | 7.40 | 69 | 13.2 |
| `sa` | 6.19 | 9.39 | 19.41 | 23.59 | 27.45 | 23.60 | 19.42 | 14.73 | 6.22 | 53 | 12.7 |
| `sa4` | 6.19 | 9.39 | 13.86 | 17.75 | 21.15 | 17.75 | 13.88 | 9.39 | 6.19 | 290 | 12.9 |
| `sab` | 6.19 | 11.42 | 14.53 | 25.74 | 29.01 | 25.92 | 22.43 | 18.09 | 6.25 | 1,222 | 29.5 |
| `sab4` | 6.19 | 11.38 | 15.18 | 18.26 | 21.11 | 18.26 | 15.18 | 11.38 | 6.19 | 13 | 12.9 |

With the combination of the old values:

- **A walls-only channel is steady and has the same depth on the rising and falling stages** (items 1–3). The
  diagonal channel is deeper than the staircase channel because the passage width of a diagonal link is 0.707
  times the grid spacing ([ENC grid](../../../docs/en/users_guide/encgrid.md)).
- **The staircase channel with shelves (`zs`) has two depths at the same 2,000 m³/s.** With walls only it is
  6.60 m, but when the discharge is lowered it stays at 10.37 m even after 90 minutes (the water on the shelves is
  about 1 m deep). The 8.05 m on the rising stage is a value taken while the deep state is still spreading from
  upstream. At 4,000 m³/s, too, it is 2 m deeper than with walls only (10.00 m, where the water level is at the
  height of the shelves). In the diagonal channel with shelves (`ds`) the discharge keeps oscillating at
  6,000 m³/s (standard deviation 277 m³/s).
- **A single corner cell (`sa`) makes the cell just after the stair 7–11 m deeper** (6,000–10,000 m³/s). Corner
  cell A is 3–8 m deep and hardly flowing. At 4,000 m³/s the depth differs between the rising stage (9.39 m) and
  the falling stage (14.73 m).
- **With two corner cells (`sab`) the flow starts to oscillate violently when the discharge is raised to
  8,000 m³/s, and energy is gained.** The oscillation continues until the discharge is lowered to 4,000 m³/s (the
  standard deviation of the discharge is 1,222 m³/s at most). The maximum velocity in the domain reaches 29.5 m/s
  (13.9 m/s with walls only), and water climbs onto wall cells 60 m above the bed (up to 6.3 m of water is left
  on wall cells at the end of the run). The energy head of the flow upstream (a depth of 16 m plus a velocity
  head of 8 m) cannot reach that height.

With the combination of the four values:

- **Every shape has the same depth on the rising and falling stages** (item 9). `zs4` at 2,000 m³/s is 6.60 m on
  both (the same as with walls only). The largest difference is 0.30 m in `ds4` at 4,000 m³/s, where the water
  level is at the height of the shelves and the depth over the last 10 minutes of the rising stage moves within a
  range of 1.9 m.
- **Energy is not gained** (item 10). The maximum velocity is 0.79–0.97 times that of the walls-only shape, and no
  water is left on wall cells.
- **The backwater caused by corner cells is less than half as large, but it remains.** The difference in depth
  from the walls-only shape is +1.9 to 4.9 m in `sa4` (6,000–10,000 m³/s; +7.4 to 11.2 m with the old values) and
  +2.0 to 4.9 m in `sab4` (4,000–10,000 m³/s; +2.0 to 12.8 m with the old values). `zs4` is 2.2 m deeper at
  4,000 m³/s, where the water level is at the height of the shelves, and 1.7 m shallower at 10,000 m³/s by the
  flow over the shelves. In `sa4` the discharge keeps oscillating with a standard deviation of 1.5–2.9 % of the
  given discharge (6,000–10,000 m³/s; 0.5 % in `sa` with the old values).

## What is happening

The momentum-conservative advection term takes the velocity of the water entering the control volume around an
edge (the upwind value) from the velocity of the link on the upstream side of the line of the edge. When the flow
is resolved by the grid, this counts it correctly. At a stair of a one-cell-wide channel, most of the water at
the face comes through a diagonal link, and the link on the upstream side of the line leads only to a bank or a
corner cell. With the combination of the old values:

- If the cell on the upstream side of the line is a wall or dry, the advection term is neutral (no loss at a
  bend). If it is wet and at least a tenth as deep as the face cell, the slow velocity of that link is applied to
  the whole discharge passing the face (`f_advection_donor = 3` in §4.4 of
  [Advection schemes](../../../docs/en/users_guide/advection.md)). This switch becomes an artificial brake when
  shelves or corner cells get wet, and because the brake strengthens as the water deepens, two depths arise at
  the same discharge (`zs`, `sa`).
- An edge leaving a corner cell has a wall on the upstream side of its line, so no inertia is counted for it. It
  flows at the velocity set by the water-surface slope and friction alone, so once water starts circulating among
  the two corner cells and the channel cells, the velocity rises without the bound set by energy (`sab`).
- A diagonal link of the staircase is narrower, so its velocity is 1.41 times that of the channel. The cap on the
  edge depth of climbing edges (`f_dry_head_cap = 3`) counts this velocity as it is in the velocity head, so water
  gets onto a shelf lying ahead of the diagonal link before the water level reaches it (`zs` at 2,000 m³/s).

The two depths at the same discharge (`zs`) appear with any of `f_advection_lateral = 0`, `f_advection_donor = 0`
and scheme 1. The oscillation with two corner cells (`sab`) stops with `f_advection_lateral = 0`, but the
backwater just after the stair (4 m deeper than with walls only at 8,000 m³/s) and a large maximum velocity
(29.8 m/s) remain (the values in this paragraph come from runs outside the configurations of this test;
developer.md §112.1 and §112.2). The same mechanism was also involved in the ups and downs of the transect
discharge at high discharge on the 50 m grid of the Chichibu basin with the old combination of the
advection settings (they do not appear with the current defaults, developer.md §114.7; developer.md §111.14).

Each of the four values changes the following (the formulas are in §4.4 of
[Advection schemes](../../../docs/en/users_guide/advection.md) and in
[The cap on the edge depth toward higher ground](../../../docs/en/users_guide/dry_head_cap.md)).

- `f_advection_donor = 4`: the discharge at the face is split into the streams of the links entering the face
  cell, and the velocity of the link on the upstream side of the line is applied only to the streams that link
  represents.
- `f_advection_bend = 2`: for the part where no inertia is counted, the acceleration from the arrival speed of the
  water is counted by an advection term in energy-head form.
- `f_advection_lateral = 2`: on the lateral faces, the velocity of a parallel link that is faster than the
  entering water is used with a weight reduced by the ratio of the discharges.
- `f_dry_head_cap = 4`: the velocity counted in the velocity head of the cap is limited from above by the mean
  velocity of the cell.

The backwater that remains is the acceleration, up to the velocity of the main stream, of water that passes
slowly through a corner cell and returns to the channel (in `sa4` at 8,000 m³/s, 5–9 % of the discharge passes
through corner cell A at about 1 m/s, while the channel flows at 9–13 m/s). This is a limit of counting the
exchange of momentum between a one-cell-wide channel and the wet cells beside it by rules for each link of the
grid; the values are not those of a real flow.

## Running

```bash
./Run.sh           # serial (14 configurations; about 2 minutes on 4 threads)
./Run_MPI.sh 2     # MPI
```

An oblique channel with thinly wet banks is checked by [test/wetbank](../../wetbank/en/README.md), the loss at a
confluence by [test/tjunction](../../tjunction/en/README.md), and the loss at a bend by
[test/bendloss](../../bendloss/en/README.md).
