# test/fluxline — angle sweep of flux transects (comparison with the analytical values of uniform flow)

> English mirror of test/fluxline/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check that the flux transects of the measurement module (`fn_record`) read
the right discharge at various angles (developer.md §24.3). A steady uniform
flow runs along a straight east-west channel, and the same flow is measured
with transects given by cell indices (`flxytype = 0`) and by real
coordinates (`flxytype = 1`). There is no reference; `Check_fluxline.py`
decides pass or fail.

## Configuration

| Item | Value |
|---|---|
| Channel | 500 × 21 cells (Δx = 1 m), slope 0.002, n = 0.03. The north and south edges are domain walls (written by `make_init.py`) |
| Flow | Q = 9.860442 m³/s over the full width of the west edge (the unit discharge of the Manning normal depth 0.5 m × 21 m), free outflow on the east edge. Initial depth 0.5 m |
| Time | dt = 0.2 s, 2400 s (transect CSVs every 300 s) |
| Configuration 1 | `param_stair.txt`: 25 transects by cell indices (`record_stair.txt`) |
| Configuration 2 | `param_xy.txt`: 23 transects by real coordinates (`record_xy.txt`) |

The angle φ of a transect is its tilt from the direction normal to the flow
(north-south). Angles from 0 to 85° are laid out, in three kinds:

- transects across the full width, from wall to wall
- transects across interior rows only (rows 6–16 by cell indices, y = 5.3–15.8 m by real coordinates)
- transects parallel to the flow

## Checks (Check_fluxline.py)

The unit discharge q is the mean h·|V| of the cells the transect passes
through (the flow is eastward).

| Transect | Real coordinates (`xy`) | Cell indices (`stair`) |
|---|---|---|
| Wall to wall | Q at every angle (difference at most 5e-4 m³/s) | Below 45° (advancing by rows): Q. From 45° up (advancing by columns): Q − q_end (q_end is h·\|V\| of the north end tread cell; ratio 1 ± 0.01) |
| Interior | F·n̂·L = q × the south-north length (ratio 1 ± 2e-4) | Below 45°: q (n − δ) (n is the number of treads; δ is 0.55–0.62 and independent of angle and length). From 45° up: q × the row difference between the end centres (ratio 1 ± 0.005) |
| Parallel | 0 | 0 |

For the wall-to-wall transects the check also confirms that the last two
rows (2100 s and 2400 s) are unchanged (steady state).

The real-coordinate method is exact for a uniform discharge vector at any
position, tilt and length (§36.2). The cell-index method (ENC) sums the edge
discharges crossing the staircase face, and a wall-to-wall transect that
advances by rows matches Q by conservation. Two conventions govern the ends:

- A transect that advances by columns is extended by half a cell at both
  ends along its long direction (columns) only (§24 (2b)). Even drawn from
  wall to wall, the half cells of the end rows (one row along the wall in
  total) stay outside the face.
- When an end lies in flowing water, the diagonal edges through the end
  corners (two at each end) are not counted. In uniform flow each diagonal
  edge carries d/2 of a row's discharge (d = 2/(2+√2)), so the transect
  reads δ ≈ d = 0.586 rows less.

Neither matters when the ends of the transect are placed in cells without
water (these conventions are kept, with a note in the measurement chapter of
the users guide; developer.md §24.3).

| File | Contents |
|---|---|
| `make_init.py` | Writes the topography, initial depth and transects (record_stair.txt, record_xy.txt); Run.sh and Run_MPI.sh call it first |
| `Run.sh` | Runs both configurations serially and checks them (30–40 s each); copies the results to result_*_serial/ |
| `Run_MPI.sh N` | Runs the same checks on N ranks and compares the transect CSVs and the final depth and velocity distributions byte by byte with the serial results (21 rows, so N ≤ 10) |
| `Check_fluxline.py` | The checks above; `stair` / `xy` |

## Running

```bash
make
./Run.sh
./Run_MPI.sh 4
```

## Findings

| Transect | Real coordinates | Cell indices |
|---|---|---|
| Wall to wall 0–40° | Q (ratio 0.999996) | Q (9.8604) |
| Wall to wall 45–85° | Q (ratio 0.999996–1.000006) | Q − q_end (9.3911; ratio 1.0000–1.0003) |
| Interior 0–40° | F·n̂·L (ratio 0.99999–1.00001) | q (n − δ), δ = 0.5851–0.5854 |
| Interior 45–85° | F·n̂·L (ratio 0.99999–1.00004) | q \|Δj\| (ratio 1.00002–1.00008) |
| Parallel | 0.0000 | 0.0000 |

- The wall-to-wall values are the same at 2100 s and 2400 s (steady state).
- The interior δ is 0.1 % below d = 0.5858 and does not depend on the length
  (n = 7, 11, 15) or the angle.
- With MPI, np = 1, 2 and 4 all give transect CSVs and final distributions
  identical byte for byte to the serial run (every transect crosses rank
  boundaries).

## Related documents

- [docs/en/users_guide/record.md](../../../docs/en/users_guide/record.md) — specifying transects and where to put their ends
- developer.md §24 (staircase face), §24.2 (edge-discharge method), §24.3 (this check and the end conventions), §36.2 (real coordinates)
