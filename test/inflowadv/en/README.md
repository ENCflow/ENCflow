# test/inflowadv — Advection and the velocity cap on the edges touching a segment inflow

> English mirror of test/inflowadv/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The momentum-conserving advection (schemes 2 and 3) sets the advection term to zero on the edges
that run from an outer cell with the normal face of a segment inflow (an inflow cell) into the
section (the normal edges from the inflow face inwards and the diagonal edges within the width of
the section). The edges along the inflow face (both ends inflow cells) and the edges that leave
the section at its two ends keep their advection term. On the edges into the section, which have
no advection term, the velocity is capped at the speed allowed by the energy head of the upstream
cell, √(2g·max(E_up − η_down, 0)) (E = η + V²/2g; for an inflow cell on a steep slope, where the
uniform flow is supercritical, V also counts the supply speed, the face discharge per cell width
and depth). This is developer.md §68.40 and its two revisions (in Japanese). This case checks that
the rule avoids each of the opposite failures.

## Setup

| Configuration | Content |
|---|---|
| `param_osc5.txt` | A channel-only domain 5 columns wide and 80 rows long between walls (the domain edges). Δx = 10 m, bed −3.0 → −3.8 m (slope 1/1000), n = 0.03, segment inflow of 700 m³/s at the north edge (`inflow_dist = 2`), stage 0.9 m at the south edge (uniform-flow depth 4.72 m), initial depth 4.7 m, 120 minutes. The corner cells at both ends of the inflow section close (§69.9), so the inflow gathers into the middle 3 columns |
| `param_osc3.txt` | The same domain 3 columns wide. The inflow is 420 m³/s, the same discharge per unit width (it gathers into the middle column; uniform flow 3.0 m/s, Froude number 0.44) |
| `param_jet3.txt` | The 3-column domain with 700 m³/s (same domain, stage and initial depth as osc3) |
| `param_side.txt` | A spill on a fixed bed. Δx = 2 m, 16 columns × 20 rows. The main channel of the segment inflow at the west edge (column 1, rows 4 to 8, 5 m³/s) flows out freely at the east edge. From the cell next to the south end of the inflow section, a side ditch 0.5 m below the main channel (slope 0.05 to the south) runs along the boundary column i = 1 to a free outflow at the south edge. The banks are the main-channel bed + 1 m. 600 seconds |
| `param_steep.txt` | A supercritical segment inflow. Δx = 2 m, a channel of 60 columns × 8 rows between walls with slope 1/20 (n = 0.03, 4-neighbour stencil with `p_diagratio = 0`); 16 m³/s into all 8 rows at the west edge (1 m²/s per unit width, uniform-flow depth 0.300 m, Froude number 1.95), free outflow at the east edge, initial depth equal to the uniform-flow depth. 600 seconds. The section covers all rows of the west edge, so the corner cells (1,1) and (1,8) also take inflow through the north and south faces (corner cells are duplicated per edge) |

For side and steep the inflow section crosses a band boundary at MPI np = 2 and 4.

## Checks (Check_inflowadv.py)

1. **No oscillation of the inflow row** (osc5, osc3): the standard deviation of the residual of the
   discharge at j = 30 (every minute) from its 11-minute moving average is below 0.2 % of the mean
   discharge over 60 to 120 minutes, and the maximum below 0.5 %. The mean discharge matches the
   inflow within 1e-3. If the edges from the inflow cells into the section keep their advection
   term, a transverse mode coupled with the advection of the inflow row excites itself, giving a
   limit cycle of 6.3 % (maximum 11.9 %) at 5 columns and 15.5 % (maximum 29.1 %) at 3 columns
   (checked on 2026-10-29).
2. **No energy created by a spill** (side): at the final output, the energy head η + V²/2g of the
   first cell of the ditch (1,9) does not exceed that of the cell in the middle of the inflow
   section (1,6) by more than 0.05 m. On an edge without the advection term the velocity tends to
   the balance of surface gradient and friction, so if the edges along the face or the edges
   leaving the section have a zero advection term, the flow falling into the ditch exceeds the
   velocity that energy conservation allows.
3. **No energy created right below the inflow** (osc5, osc3, jet3; mild slope): at the final output
   (120 minutes), the largest energy head z + h + V²/2g of the cells in rows 2 to 10 does not exceed
   the largest one of the inflow row (row 1) by more than 0.1 m. Without the cap on the edges into
   the section, a supercritical jet forms right below the inflow (1.0 to 1.3 m deep at 13 m/s with
   3 columns). If the reference speed of the cap is switched by the current Froude number of the
   inflow cell, a jet remains in jet3.
4. **No throttling of a supercritical inflow** (steep): at the final output, all 10 columns on the
   inflow side are supercritical (Froude number > 1), the mean depth of the inflow column (column 1)
   is within ±4.5 % of the Manning uniform-flow depth, and the mean depth downstream (columns 31 to
   50) matches the uniform-flow depth within ±2 %. If the cap uses only the speed of the upstream
   cell, the inflow cells throttled by the cap become deeper.

| Rule | 1 (5 / 3 columns) | 2 (difference of energy head) | 3 (osc5 / osc3 / jet3) | 4 (inflow-column depth / uniform-flow depth) |
|---|---|---|---|---|
| Zero advection only on the edges into the section + velocity cap (current rule) | 0.000 / 0.000 % | +0.004 m | +0.048 / −0.269 / −0.404 m | 1.030 |
| No cap (first revision of 2026-10-29) | 0.000 / 0.000 % | +0.002 m | +0.227 / +5.198 m / stopped at 39 s | 1.030 |
| Zero advection on all edges touching the inflow cells (2026-10-24 to 29) | 0.000 / 0.000 % | +1.218 m | +0.092 / +5.198 m / stopped at 39 s | 1.014 |
| As above, but keeping the edges that leave the section (option compared on 2026-10-29) | 0.000 / 0.000 % | +0.258 m | +0.092 / +5.198 m / stopped at 39 s | 1.014 |
| No zero advection (before 2026-10-24) | 6.315 / 15.502 % | +0.030 m | +1.398 / +6.664 m / stopped at 4 minutes | 0.967 |
| Cap referenced to the speed of the upstream cell only (option compared) | 0.000 / 0.000 % | +0.004 m | same as the current rule | 1.061 |
| Cap also counting the supply speed when the inflow cell is supercritical (option compared) | 0.000 / 0.000 % | +0.004 m | +0.048 / −0.269 / +2.397 m | 1.030 |

With the rule of 2026-10-24 to 29, in param_feed of examples/meander (the capacity feed fixes the
bed of the inflow cells while the outer cells beside them are scoured), the flow falling into the
outer cell at the end of the section became too fast, scour and a jet fed each other, and the
Courant number exceeded 1 at 1:10:47 of hydraulic time. With the rule without the cap,
fixsuspfeed and other configurations of the same example stopped because the velocity on the edge
into a scour hole just inside the inflow cells became too high (developer.md §68.40).

## Usage

```
make
./Run.sh            # serial (about 30 seconds for the 5 runs)
./Run_MPI.sh 2      # MPI
```
