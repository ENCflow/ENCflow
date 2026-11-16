# test/chutepool — flow plunging into a pool below a drop (check that the discharge does not oscillate, and record of the limit of f_dry_head_cap = 3)

English mirror of test/chutepool/README.md

[日本語](../README.md)

This test looks at a place in a steep channel where a fast (supercritical) flow that has fallen over a drop
turns and plunges into a deep pool. Directly ahead of the flow in the cell below the drop lies a hillslope cell
higher than the water level. The test checks that the discharge at a transect in the pool matches the given
discharge and does not oscillate. Its subject is the cap on the edge depth of the continuity equation
(`f_dry_head_cap` in `&list_enc`; §5 of [Advection schemes](../../../docs/en/users_guide/advection.md),
developer.md §110.24 and §110.26).

**With the default `f_dry_head_cap = 2`, the discharge in the pool does not oscillate. With
`f_dry_head_cap = 3`, the discharge in the pool oscillates with a period of about one minute while the
discharge is being raised.** The test runs the same computation with 2 and 3 and judges, for 2, that there is
no oscillation. For 3 it is displayed as "the limit of 3" (not judged).

## Setup

The 32 × 21 cells of columns 285–316 and rows 194–214 are cut out of the data of
[test/chichibu](../../chichibu/en/README.md) (100 m grid) by `make_chutepool.py`. The roughness is the same as in
test/chichibu (hillslopes 0.15, channel-mask cells 0.02), and dt = 2.5 s. The cell numbers in the table below
are (column, row) of the original grid.

| Place | Cell | Ground (m) |
|---|---|---|
| Top of the drop | (292, 208) | 393.1 |
| Below the drop (the flow enters eastward and turns north-east) | (293, 208) | 380.1 |
| Hillslope directly ahead of the flow in the cell below the drop | (294, 208) | 391.3 |
| Entrance of the pool | (294, 207) | 370.5 |
| Pool (depth 6–13 m at a discharge of 5,000 m³/s) | (296, 206)–(309, 204) | 369.0–360.4 |
| Drop at the outlet of the pool | (309, 203)–(309, 201) | 360.4 → 348.5 |

The discharge is given as a source in the channel cell (285, 200) at the west end of the cut-out. It is held at
2,500 m³/s until 40 minutes, then raised to 5,000 m³/s over 150 minutes and held for 20 minutes (the run is
210 minutes). The north side is a free outflow (the outlet of the main channel). The transect is column 296 in
the pool (rows 204–207, the same position as transect 3 of test/chichibu) and is recorded every 10 seconds.

At a discharge of 4,000 m³/s, the flow in the cell below the drop has a depth of 2.6 m and a velocity of
15 m/s (Froude number 3.0, velocity head 12 m; computed with 2). The ground of the hillslope cell ahead is
8.6 m above the water level of this cell.

| Configuration | File | f_dry_head_cap |
|---|---|---:|
| c2 | `param_c2.txt` | 2 |
| c3 | `param_c3.txt` | 3 |

## Check items (Check_chutepool.py)

Item judged with both 2 and 3:

1. Mass balance: the mean discharge at the transect over the last 5 minutes is within ±1 % of the given
   discharge of 5,000 m³/s.

Item judged with 2 and displayed with 3 (the limit of 3):

2. The discharge at the transect does not oscillate after 45 minutes: the largest deviation of the 10-second
   values from their 1-minute moving average (7 points) is below 80 m³/s, and there are no consecutive changes
   in opposite directions (both exceeding 20 m³/s).

Item displayed:

3. The maximum depth, over the run, of the hillslope cell directly ahead of the flow in the cell below the drop.

## Values

| Configuration | Final discharge (m³/s) | Largest deviation from the 1-minute moving average (m³/s) | Consecutive changes in opposite directions | Maximum depth of the hillslope cell (m) |
|---|---:|---:|---|---:|
| c2 (`f_dry_head_cap = 2`) | 4,993.5 | 34 | none | 0.00 |
| c3 (`f_dry_head_cap = 3`) | 4,993.2 | 323 (at 141 min) | 121 (46–146 min) | 1.93 |

- **2 does not let water climb the hillslope ahead, which is higher than the water level.** The discharge at
  the transect increases smoothly, following the rise of the given discharge.
- **With 3, the discharge in the pool oscillates while the given discharge is between 2,600 and 4,300 m³/s
  (46–146 minutes).** 3 counts water as able to climb the high cell ahead by the velocity head of the flow
  entering the cell below the drop (the depth of the hillslope cell reaches 1.9 m). That velocity head is taken
  from "the unit-width discharge of the entering edge divided by the depth of this cell", so in a supercritical
  flow a slight rise in depth lowers the velocity head greatly (for the same discharge, the gradient of the
  specific energy $`h + q^2/2gh^2`$ with respect to depth is $`1 - Fr^2`$, which is −8 at a Froude number
  of 3). The amount of water climbing the hillslope changes greatly with slight changes in the depth of the
  cell below the drop, the water entering the pool by way of the hillslope increases and decreases, and the
  oscillation of the discharge in the pool continues (developer.md §110.26).

## Limits and how to read the results

- The test is a cut-out of one place in real terrain. Item 2 means "no oscillation for this terrain and this
  way of raising the discharge"; it does not mean that there is no oscillation in other terrain.
- The roughness of 0.02 for the channel-mask cells is small for a mountain stream with successive drops, and
  the velocity (15 m/s) is larger than in reality. Whether the oscillation appears depends on the size of the
  velocity head this velocity produces.
- The hydraulic jump, the air entrainment and the splash onto the hillslope ahead where the flow that has
  fallen over the drop enters the pool cannot be represented by depth-averaged equations.
- Item 2 is not judged for 3, so the test passing does not mean that the discharge does not oscillate with 3.

## Running

```bash
make
./Run.sh          # serial (2 configurations; a few seconds)
./Run_MPI.sh 2    # MPI (with np = 2 and 4 a band boundary passes the north end of the pool)
```

## References

- The terrain is part of the data of [test/chichibu](../../chichibu/en/README.md) (100 m grid; for the origin of
  the elevation data see [tutorials/chichibu](../../../tutorials/chichibu/en/README.md)).
- The rule of the cap on the edge depth (`f_dry_head_cap`) is ENCflow's own (§5 of
  [Advection schemes](../../../docs/en/users_guide/advection.md) in the users guide). The relation between
  specific energy and critical flow is standard open-channel hydraulics.
