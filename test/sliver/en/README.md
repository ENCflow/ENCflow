# test/sliver — Subgrid channel cells of near-zero width (slivers of a covered-fraction mask), the reassignment of openings and the conveyance ratio

> English mirror of test/sliver/README.md. The Japanese file is the master copy.

When the subgrid channel width (`fn_width` in `&list_channel`) is given from the fraction of each coarse cell covered by
the channel (the covered fraction) of a channel polygon or a high-resolution channel mask, cells appear that the channel
edge only grazes at a corner (slivers a few metres wide). The dynamic reassignment of openings (`f_opening_dynamic` in
`&list_enc`) counts an opening as blocked when the corner cell of the edge lies outside the computation, and hands that
share of the passage width back to the edge. The velocity of a cell with a subgrid channel width is converted back by
the mean width cap of its surrounding edges (the conveyance ratio). Counting a sliver as "open" keeps the passage width
from being handed back and lowers the conveyance ratio, so the conveyance of the channel drops. A channel cell whose
width is below 5 % of the width of the cell it is compared with (capped at the face length) counts as outside the
computation in the reassignment and the conveyance ratio (developer.md §137, Japanese). This is a verification-type
test without a reference; pass or fail is the exit code of `Run.sh` and `Run_MPI.sh`.

## What it checks

The same channel is computed with added channel cells 0.01 m wide (`tiny`) and without them (`none`), and the channel
levels are checked to agree. Cells 0.01 m wide carry almost no water, so physically the channel flow does not depend on
whether they are added.

- `dg`: a straight 45° channel represented by resolved cells, one per column (8-connected), with the corner cells of the
  diagonal steps (both sides) added. Checks the reassignment of diagonal edges (side cells that are slivers).
- `ax`: a row of slivers added along one side of a two-row resolved channel along a grid axis. Checks the reassignment
  of axis edges (diagonal neighbours that are slivers) and the conveyance ratio of cells next to slivers.

## Setup

| Item | Value |
|---|---|
| Grid | Δx = Δy = 100 m. Time step 2 s, 3 hours (output every hour) |
| Channel | Slope 1/1000, roughness 0.03. Segment inflow at the upstream end, the uniform-flow stage prescribed at the downstream end. Outside the channel is outside the domain |
| Width | Resolved cells 9999 m (`fn_width`; resolved cells with a width), slivers 0.01 m |

| Shape | Channel | Discharge | Cases |
|---|---|---|---|
| `dg` | A straight 45° channel of resolved cells, one per column (8-connected). 40 columns | 300 m³/s (uniform-flow depth 2.31 m with the natural diagonal width 70.7 m) | `dg_none`, `dg_tiny` (the corner cells of the diagonal steps on both sides made channel cells 0.01 m wide) |
| `ax` | A straight channel along a grid axis, two rows of resolved cells. 40 columns | 1,000 m³/s (uniform-flow depth 2.54 m for 200 m width) | `ax_none`, `ax_tiny` (one row on the north side made channel cells 0.01 m wide) |

| File | Content |
|---|---|
| `Run.sh` | Runs the 4 cases serially and judges them with `Check_sliver.py` (about 5 s with one thread) |
| `Run_MPI.sh [N]` | Runs all cases with N ranks (default 2; N ≤ 4; the `ax_*` cases, which compute only two or three rows, with at most 2 ranks) and judges them; `dg_tiny` and `ax_tiny` are also run with one rank (same executable) and Log.txt, water level E0003 and depth H0003 are compared byte by byte. The band boundaries cross the channel and the slivers |
| `Check_sliver.py` | Judgements: (1) the difference of the channel-cell levels of `dg` with and without slivers is 2 mm or less, (2) the difference over 20–80 % of the reach of `ax` is 1 % of the uniform-flow depth or less, (3) the channel level changes by 2 mm or less from 2 to 3 hours, (4) the depth in the middle of the reach without slivers is within 1 % of Manning's uniform-flow depth |
| `make_sliver.py` | Writes the input (ground, roughness, mask, initial depth, channel mask, channel width, boundary tables) and the settings `p_<case>.txt` |

## Results (2026-11-27; gfortran 13.3, -Ofast)

Difference of the channel-cell levels with and without the slivers (after 3 hours; with − without).

| Shape | Version before the rule (before §137) | With the rule |
|---|---:|---:|
| `dg` (45°; maximum over channel cells) | 1.216 m | 0.7 mm |
| `ax` (along an axis; maximum over 20–80 % of the reach) | 0.329 m | 17.5 mm |

The version before the rule counted the slivers as open, the passage width of the reassignment was not handed back,
and the level of the 45° channel rose by more than 1 m. The difference left in `ax` with the rule (about −15 mm in the
middle of the reach, 0.6 % of the uniform-flow depth) comes from the advection term counting the row of slivers as a wet
neighbour, and does not depend on the width of the slivers (the same −14.6 mm with 0.001 m; +37 mm with advection
scheme 1; developer.md §137.2). Without slivers the depth is within 0.05 % of Manning's uniform-flow depth (`dg` counted
with the natural diagonal width 70.7 m).

## What this case does not check

- Slivers of about 5 % width (the treatment jumps across the threshold; the sensitivity to where the threshold lies is
  in developer.md §137.3).
- What the advection term adds by counting slivers as wet neighbours (it is inside the tolerance of judgement (2);
  developer.md §137.6).
- Real oblique bands and bends made from the covered fraction (the no-cutoff cases of the example
  [examples/coarse_channel](../../../examples/coarse_channel/en/README.md)), slivers of real channel polygons, and places
  where a channel of extremely small width joins a resolved river.
