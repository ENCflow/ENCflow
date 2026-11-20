# test/stageside — water leaving a column of cells given as a boundary, and lateral Neumann sides

English mirror of test/stageside/README.md

[日本語](../README.md)

This test covers layouts in which a column of stage-prescribed cells (cells forced to a prescribed water level;
`&list_bound_stage`) or a column of cells where the discharge is given as a source (`&list_bound_source`)
touches lateral Neumann sides (`f_bc_n = 3` and the like). Among the advection rules, the combination of four
values for deep, slow neighbouring cells (`f_advection_donor = 4`, `f_advection_bend = 2`,
`f_advection_lateral = 2`, `f_dry_head_cap = 4`;
[Advection schemes](../../../docs/en/users_guide/advection.md) §4.4) does not charge water leaving these
"cells given as a boundary" with the acceleration from rest. The test checks that this treatment gives the same
result as the combination of old values, and that it is the same on the faces inside the frame of the domain
and on the lateral Neumann boundary faces (developer.md §113.9).

- **With the combination of old values (3, 1, 1, 3) and with the combination of four values alike, the run
  completes, becomes steady and is uniform alongshore.**
- **The results of the two combinations agree** (differences in depth and velocity of 1e-6 or less). In a
  channel where the flow only varies gradually, the rules of the four values give the same values as the old
  ones.
- The energy head of the water leaving the column of stage-prescribed cells is higher than the prescribed
  level by the velocity head (0.021 m). This is the same with both combinations, and it is a limitation when
  stage-prescribed cells are used in place of a still pond.

## Settings

A channel 600 m long and 40 m wide (120 × 8 cells, Δx = 5 m). The bed rises uniformly from −3 m at the west
end to −1.5 m at the east end (`make_stageside.py`; the same shape as the channel of
[test/wfdoppler](../../wfdoppler/en/README.md)). Manning's roughness coefficient is 0.02 and dt = 0.5 s.

| Side or cells | Condition |
|---|---|
| The easternmost column (8 cells) | Stage-prescribed cells (prescribed level +0.2 m), or a source (48 m³/s = 1.2 m²/s per unit width; raised over 10 minutes and then constant) |
| East side | Wall (behind the easternmost column) |
| West side | Long-wave radiation (reference level 0) |
| North and south sides | Lateral Neumann (uniform alongshore) |

The run starts from still water (level 0) and covers 60 minutes. Water flows from the easternmost column
toward the west and becomes steady within 20 minutes.

| Configuration | Easternmost column | Advection rules (`f_advection_donor`, `f_advection_bend`, `f_advection_lateral`, `f_dry_head_cap`) |
|---|---|---|
| `s3` | Stage-prescribed cells | Combination of old values (3, 1, 1, 3) |
| `s4` | Stage-prescribed cells | Combination of four values (4, 2, 2, 4) |
| `q3` | Source | Combination of old values (3, 1, 1, 3) |
| `q4` | Source | Combination of four values (4, 2, 2, 4) |

The grid has 8 rows, so with MPI np = 2 the north side (row 1) and the south side (row 8) belong to different
ranks.

## Check items (Check_stageside.py)

Items judged for each of the four configurations:

1. The run completes (it does not diverge and stop).
2. Steady: the largest difference in velocity between 40 and 60 minutes is below 1e-5 m/s.
3. Uniform alongshore: in columns 6–120, the largest differences between rows in velocity and depth and the
   largest magnitude of the alongshore velocity are below 1e-6 (m/s, m). The columns just inside the west side
   (columns 1–5) are excluded, because the corner between the long-wave radiation side and the lateral Neumann
   sides leaves an alongshore velocity of 1e-5 m/s there.

Item judged by comparing the two configurations that differ in the rules (`s4` with `s3`, and `q4` with `q3`):

4. The depth and velocity of the configuration with the four values agree with those of the configuration
   with the old values (largest differences below 1e-5; m, m/s).

The criteria are regression bounds with a margin over the present values (table below), not values derived
from theory. The binary (single-precision) output is read.

## Values

| Configuration | Velocity (m/s; columns 1, 60, 119, 120) | Depth (m; same columns) | Velocity difference between 40 and 60 minutes (m/s) | Differences between rows (velocity m/s, depth m) and alongshore velocity (m/s) |
|---|---|---|---|---|
| `s3` | −0.3452, −0.4492, −0.6420, −0.3221 | 3.1903, 2.4534, 1.7184, 1.7062 | 8.3e-7 | 1.2e-7, 0, 6.1e-8 |
| `s4` | −0.3452, −0.4492, −0.6420, −0.3221 | 3.1903, 2.4534, 1.7184, 1.7062 | 9.5e-7 | 1.2e-7, 0, 6.1e-8 |
| `q3` | −0.3748, −0.4869, −0.6935, −0.3480 | 3.2078, 2.4709, 1.7363, 1.7242 | 8.9e-8 | 1.2e-7, 2.4e-7, 7.9e-8 |
| `q4` | −0.3748, −0.4869, −0.6935, −0.3480 | 3.2078, 2.4709, 1.7363, 1.7242 | 1.5e-7 | 1.2e-7, 0, 9.4e-8 |

The largest differences between `s4` and `s3` are 0 m in depth and 6.0e-8 m/s in velocity, and those between
`q4` and `q3` are 2.4e-7 m in depth and 1.5e-7 m/s in velocity (all of them one unit in the last place of the
single-precision output). Column 120 is the easternmost column, and its velocity is the cell mean (the east
face is a wall and the flow passes only through the west face).

In `s3` and `s4`, the energy head (water level + velocity head) in the column just inside the east end
(column 119) is +0.2207 m, 0.0207 m above the prescribed level (+0.2 m); the velocity head is 0.0210 m. In
`q3` and `q4`, the water level of the source column (column 120) is +0.2179 m and differs from that of the next
column (+0.2176 m) by 0.0004 m; the velocity head in column 119 is 0.0245 m.

## What is happening

`f_advection_bend = 2` of the combination of four values charges water leaving a cell without inflow with the
acceleration from rest (an advection term in a form that conserves the energy head). Stage-prescribed cells
and cells where the discharge is given as a source are mostly used where water that has flowed in from outside
the domain enters, so they are not charged (the same treatment as sea cells and the faces of an inflow
section). `f_advection_lateral = 2` likewise does not reduce by the similarity of discharge when the source of
the inflow is one of these cells.

If source cells were charged with the acceleration from rest, the source column of `q4` would be deeper than
that of `q3` by the velocity head of its outflow (0.015 m; item 4).

At a position outside a lateral Neumann side, this mark of "being a cell given as a boundary" is read from the
mirror cell (the cell moved into the frame along the normal of the side). If it were not read and the position
were treated as "not a given cell", then at the corner where the column of given cells touches the lateral
Neumann side the faces inside the frame would be "not charged" while the boundary faces would be "charged".
From this mismatch an alongshore flow forms in the corner rows, and in `s4` the velocity keeps increasing
until the run stops at 13 minutes (item 1).

When stage-prescribed cells or a source are used in place of a still pond, the water flowing out is not
charged with the acceleration from rest and takes the velocity at which the water-surface slope and friction
balance. With stage-prescribed cells, the energy head of the water that has flowed out is therefore higher
than the prescribed level by the velocity head (the values above). This is the same with the combination of
old values. To account for the acceleration of water leaving a pond, include the pond in the domain as
computed water instead of representing it by stage-prescribed cells or a source.

## Running

```bash
./Run.sh           # serial (4 configurations; about 1 minute on 1 thread)
./Run_MPI.sh 2     # MPI
```

The non-hydrostatic test in which a wave on a uniform current is maintained by stage-prescribed cells at both
ends is [test/nhcurrent](../../nhcurrent/en/README.md); the rules for the edges adjacent to the outer cells of
an inflow section are checked by [test/inflowadv](../../inflowadv/en/README.md).
