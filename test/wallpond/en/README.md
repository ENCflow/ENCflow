# test/wallpond — a pond behind the virtual walls of channel levees and seawalls and the flow in front of the walls (neighbour checks of the advection term)

> English mirror of test/wallpond/README.md. The Japanese file is the master copy.

This case checks that, when channel levees are represented as virtual walls (`fn_bank` in `&list_channel`), the flow
in the channel does not change when the landside behind the walls is flooded. In the checks with which it reads the
state of a neighbour cell, the advection term counts a cell behind a virtual wall like a dry cell, even when it is wet
(developer.md §134). Without this treatment the velocity (0) of the still water behind the wall mixes into the momentum
of the channel, which slows the channel down artificially and raises its level. The virtual walls of seawalls
(`seawall0` and `fn_seawall` in `&list_geoinfo`) are treated the same way, and the dynamic reassignment of openings counts
the cells behind them as blocked (§134.9). It is a check-type case without a reference; the result is decided by the
exit codes of `Run.sh` and `Run_MPI.sh`.

## What is checked

The same channel is computed with a dry landside and with a still pond 1.5 m deep on the level ground of the
landside, and the channel levels must agree. The levee crest is the bed + 10 m and is never overtopped. The pond
behind the wall receives neither water nor momentum from the channel, so physically the flow in the channel does not
depend on whether the landside is wet.

There are three channel shapes. In a straight channel along a grid axis, the edges of a two-cell resolved channel
read the cells behind the wall as the upwind donor of a flow-direction face, the parallel link of a lateral face and
the opening of a diagonal edge. When a 45° channel is represented as a four-connected one-cell staircase (the same
type as the channel mask of tutorials/chichibu), the same happens at the steps. The staircase is run with three
combinations of the advection rules and with scheme 1 (cell-centre gradient), which pass through the branches of the
rules (`lateral_u`, `lateral_u_w`, `lateral_u_j`, the branches of `axis_open`, `bend_face`, `path_value` and the
gradient of scheme 1). For the seawalls the channels of `ax2` and `dg1` are replaced by strips of sea-side cells
and the channel levees by seawalls; besides the agreement of the dry and the ponded land, the case checks that the
dry land agrees with the configuration that does not compute the land (the reassignment of openings).

## Configuration

| Item | Value |
|---|---|
| Grid | Δx = Δy = 100 m. Time step 2 s, 3 hours (output every hour) |
| Channel | Slope 1/1000, roughness 0.03. Segment inflow at the upstream end, the stage of the uniform-flow depth prescribed at the downstream end |
| Landside | 300 m wide on both sides of the channel. Level ground (the bed at mid-reach + 1 m). The ponded configuration has a still pond 1.5 m deep |
| Levee | Virtual walls (`fn_bank`, `f_bank_datum = 2`). Crest at the bed + 10 m |

| Shape | Channel | Discharge | Cases |
|---|---|---|---|
| `ax2` | Straight along a grid axis, a two-cell (200 m wide) resolved channel. 4 km long | 1,000 m³/s (uniform-flow depth 2.55 m) | `mask` (landside not computed), `dry`, `wet`, `levee` (pond behind a one-cell resolved levee) |
| `ax1` | The same channel as a one-cell subgrid channel (80 m wide; `fn_width`) | 1,000 m³/s (uniform-flow depth 4.41 m) | `dry`, `wet` |
| `dg1` | A 45° straight line as a four-connected one-cell staircase (resolved), 40 columns from the west edge to the east edge | 300 m³/s | `dry` and `wet` for each of the configurations `o4`, `o3l0`, `o0` and `s1` |
| Seawall | The channels of `ax2` and `dg1` (configuration `o4`) as strips of sea-side cells (`fn_seaside`; ordinary cells, not `sw`), with seawalls (`seawall0 = 35` m, absolute elevation) on the land on both sides. `&list_channel` is not used | same as `ax2` and `dg1` | `ax2_sdry`, `ax2_swet`, `dg1_o4_sdry`, `dg1_o4_swet` |

Every advection configuration states the five switches of `&list_enc` explicitly (it does not rely on the defaults).
The values are, in order, `f_advection_scheme`, `f_advection_donor`, `f_advection_bend`, `f_advection_lateral` and
`f_dry_head_cap`.

| Configuration | Values | Rules passed through |
|---|---|---|
| `o4` | 3, 4, 2, 2, 4 (default) | upwind donor of the flow-direction face with the per-stream weight, `lateral_u_j` on the lateral faces, `open_rep` in the opening ratio, the bend rule |
| `o3l0` | 3, 3, 1, 0, 3 | `lateral_u_w` on the lateral faces, the continuous-weight branch of the opening ratio |
| `o0` | 3, 0, 1, 0, 3 | `lateral_u` on the lateral faces, the wet/dry branch of the opening ratio |
| `s1` | 1, 4, 2, 2, 4 | the cell-centre gradient of scheme 1 |

| File | Content |
|---|---|
| `Run.sh` | Runs the 18 cases serially and judges them with `Check_wallpond.py` (about 35 s with one thread) |
| `Run_MPI.sh [N]` | Runs all cases with N ranks (default 2; N ≤ 4; `ax2_mask`, which computes only two rows, with at most 2 ranks) and judges them, and runs the six ponded cases (`ax2_wet`, `ax1_wet`, `dg1_o4_wet`, `dg1_s1_wet`, `ax2_swet`, `dg1_o4_swet`) also with one rank (same executable), comparing Log.txt, the water level E0003 and the depth H0003 byte by byte. The band boundaries cross the channel and the levees |
| `Check_wallpond.py` | Judgement: (1) the channel level differs by at most 1 mm between the ponded and the dry landside, (2) the channel level of `ax2` with a dry landside differs by at most 1 mm from `mask`, `levee` and `sdry` (seawall with dry land), (3) the pond level stays within 1 mm of its initial value and does not change from 2 to 3 hours, (4) the channel level changes by at most 2 mm from 2 to 3 hours, (5) the depth at mid-reach of `ax2` and `ax1` is within 1 % of the Manning uniform-flow depth |
| `make_wallpond.py` | Writes the input (ground, roughness, mask, initial depth, channel mask, channel width, crest, sea-side mask, boundary tables) and the settings `p_<case>.txt` |

## Results (2026-11-26; gfortran 13.3, -Ofast)

Maximum difference of the water level over the channel cells between the ponded and the dry landside (after 3 hours).

| Case | Version whose advection did not look at the virtual walls (just before the fix) | After the fix |
|---|---:|---:|
| `ax2` (two-cell resolved) | 0.186 m | 0.000 m |
| `ax1` (one-cell subgrid) | 0.000 m | 0.000 m |
| `dg1_o4` (staircase, default) | 0.138 m | 0.000 m |
| `dg1_o3l0` | 0.155 m | 0.000 m |
| `dg1_o0` | 0.155 m | 0.000 m |
| `dg1_s1` (scheme 1) | 0.073 m | 0.000 m |
| `ax2_s` (seawall, two-cell strip) | 0.354 m | 0.000 m |
| `dg1_o4_s` (seawall, staircase) | 0.133 m | 0.000 m |

The version just before the fix fails judgement (1) in these seven cases (for the two coastal-levee cases, the version
before the seawalls were included in the advection term and the reassignment of openings; §134.9). In that version
`ax2` with a seawall and dry land also differed by 0.252 m from the configuration that does not compute the land
(conveyance width 0.919 times, because there was no reassignment of openings for seawalls) and failed judgement (2). In the ponded `ax2` case the conveyance
width back-calculated from the uniform-flow depth and the surface slope was 0.919 times the channel width (1.000
after the fix). A straight one-cell subgrid channel was not affected in the first place. After the fix the channel
level of the ponded cases agrees with the dry landside, with the configuration that does not compute the landside and
with the resolved levee to the output digits (0.1 mm).

## What this case does not check

- Overtopped levees and deeply submerged levees (not counting the cells behind the wall does not depend on the water
  level; over a deeply submerged levee it is an approximation that does not count the lateral momentum exchange
  across the wall. developer.md §134.6).
- Breaches (a breach site is judged by its effective crest, and an opened breach is not counted as a wall). The
  comparison of a virtual-wall breach with a resolved levee is in the supplement of examples/levee_breach.
- A pond behind the wall that flows (the cell further upwind in MUSCL is counted even behind the wall; it only enters
  the ratio of the second-order limiter and is not used for switching to first order).
- A comparison of the 45° staircase with a seawall and with a channel levee of the same shape (the seawall
  reassigns the openings blocked by the wall through the dynamic reassignment, the channel levee through the static
  opening correction; the rules differ slightly and the channel level differs by 1.5 mm (2.6 mm with scheme 1); not
  judged).
- A fine grid (Δx = 20 m, a ten-cell channel). In the design groundwork the conveyance width was 0.936 times with
  the version just before the fix and 1.000 times after the fix (developer.md §134.4).
