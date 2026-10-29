# test/inflowadv — Advection on the edges touching a segment inflow

> English mirror of test/inflowadv/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The momentum-conserving advection (schemes 2 and 3) sets the advection term to zero on the edges
that run from an outer cell with the normal face of a segment inflow (an inflow cell) into the
section (the normal edges from the inflow face inwards and the diagonal edges within the width of
the section). The edges along the inflow face (both ends inflow cells) and the edges that leave
the section at its two ends keep their advection term (developer.md §68.40, in Japanese). This
case checks that the rule avoids two opposite failures.

## Setup

| Configuration | Content |
|---|---|
| `param_osc5.txt` | A channel-only domain 5 columns wide and 80 rows long between walls (the domain edges). Δx = 10 m, bed −3.0 → −3.8 m (slope 1/1000), n = 0.03, segment inflow of 700 m³/s at the north edge (`inflow_dist = 2`), stage 0.9 m at the south edge (uniform-flow depth 4.72 m), initial depth 4.7 m, 120 minutes. The corner cells at both ends of the inflow section close (§69.9), so the inflow gathers into the middle 3 columns |
| `param_osc3.txt` | The same domain 3 columns wide. The inflow is 420 m³/s, the same discharge per unit width (it gathers into the middle column) |
| `param_side.txt` | A spill on a fixed bed. Δx = 2 m, 16 columns × 20 rows. The main channel of the segment inflow at the west edge (column 1, rows 4 to 8, 5 m³/s) flows out freely at the east edge. From the cell next to the south end of the inflow section, a side ditch 0.5 m below the main channel (slope 0.05 to the south) runs along the boundary column i = 1 to a free outflow at the south edge. The banks are the main-channel bed + 1 m. 600 seconds |

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

| Edges with a zero advection term | 1 (5 / 3 columns) | 2 (difference of energy head) |
|---|---|---|
| Only the edges from the inflow cells into the section (current rule) | 0.000 / 0.000 % | +0.002 m |
| All edges touching the inflow cells (rule of 2026-10-24 to 29) | 0.000 / 0.000 % | +1.218 m |
| As above, but keeping the edges that leave the section (option compared on 2026-10-29) | 0.000 / 0.000 % | +0.258 m |
| None (before 2026-10-24) | 6.315 / 15.502 % | +0.030 m |

With the rule of 2026-10-24 to 29, in param_feed of examples/meander (the capacity feed fixes the
bed of the inflow cells while the outer cells beside them are scoured), the flow falling into the
outer cell at the end of the section became too fast, scour and a jet fed each other, and the
Courant number exceeded 1 at 1:10:47 of hydraulic time (developer.md §68.40).

## Usage

```
make
./Run.sh            # serial (about 20 seconds for the 3 runs)
./Run_MPI.sh 2      # MPI
```
