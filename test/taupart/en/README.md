# test/taupart — resistance partitioning on steep gravel beds (f_taupart)

English mirror of test/taupart/README.md

Verification of the resistance partitioning that multiplies the τ* passed to the
transport formula by the relative-depth factor
φ(h) = {1 + (a1/a2)² (h/D84)^(−5/3)}^(−e/2) (`f_taupart = 1` in `&list_geomorph`;
Rickenmann & Recking 2011, Nitsche et al. 2011; developer.md §89.30,
docs/mountain_stream_plan.md §14). In uniform flow in a steep channel one cell
wide, the steady bed-load rate is obtained from the ledger of bed load that left
through the open eastern boundary and compared with the capacity evaluated with
the same transport formula from the depth and velocity of the outlet cell.

## Setup

| Item | Value |
|---|---|
| Channel | 500 × 8 cells (Δx = 1 m); row 4 is the channel, the other rows are dry ground 2 m above the bed. Slope 0.05, n = 0.03, higher in the west (written by `make_init.py`) |
| Flow | Segment inflow Q = 0.469545 m³/s at the western cell (1, 4) (Manning uniform depth 0.190 m, Fr 1.8; the same unit discharge as the supercritical configuration of test/uniflow); free outflow at the eastern edge |
| Sediment | `f_fluvial = 1`, Ashida–Michiue formula (MPM in d19_mpm), d50 = 0.01 m, τ*c = 0.05, mobile layer 2 m, no feed (a degradation wave from the upstream end reaches 200 m in 1500 s) |
| Time | dt = 0.1 s. Every configuration runs for 1500 s and 3000 s (Run.sh generates the 3000 s param by replacing tt and dir_result); the difference of the ledgers / 1500 s is the steady bed-load rate |

| Configuration | Partitioning | D84 (m) | h/D84 | φ | Role |
|---|---|---|---|---|---|
| param.txt (off) | none | — | — | 1 | compared with the reference (regression; bit-identical to the previous formula) |
| d044 | on | 0.044 | 4.3 | 0.71 | intermediate-scale roughness |
| d19 | on | 0.19 | 1.0 | 0.22 | large-scale roughness |
| d76 | on | 0.76 | 0.25 | 0.04 | φ τ* < τ*c (no bed load) |
| d0 | on | 0 (= 2.2 d50 = 0.022) | 8.6 | 0.88 | default D84 |
| d19_mpm | on | 0.19 | 1.0 | 0.22 | MPM formula |
| excl | on + fluv_taufac = 0.5 | — | — | — | the combination stops |

## Checks (Check_taupart.py)

1. Uniform flow: in the measuring section x = 250–400 m at 1500 s, the depth is within ±2 % of the
   Manning uniform depth, V·h within ±1 % of q, and the coefficient of variation of the depth < 1 %.
   The degradation wave from the upstream end has not reached the section (|Δz| < 5 mm).
2. The steady bed-load rate agrees within ±0.5 % with the capacity evaluated from the h and V of the
   outlet cell at 3000 s with the transport formula including the factor (the capacity of an
   open-boundary face uses the hydraulics of the cell itself; the outlet cell lowers by about 3 cm in
   3000 s because of the free-outflow boundary, which does not affect the check because the h and V
   of that moment are used). The configuration below the threshold has a ledger of 0.
3. Without the partitioning (param.txt) the Log.txt is bit-identical to the reference (regression in
   `Run.sh`).
4. Combining `f_taupart = 1` with `fluv_taufac ≠ 1` stops the run (Run.sh checks the return code and
   the message).
5. MPI (`Run_MPI.sh N`): the regression of param.txt, and the Log.txt of d19 is byte-identical to the
   serial run (`Log_d19_serial.txt` left by `Run.sh`).

Record of 2026-11-02 (gfortran 13.3, release build): steady rate / capacity = off 1.0000, d044 0.9994,
d19 1.0004, d0 0.9988, d19_mpm 1.0004; d76 has no bed load. np = 2 and 4 are byte-identical to the
serial run.

## Run

```bash
make
./Run.sh          # run → regression → Check (about 2 minutes)
./Run_MPI.sh 4    # MPI (2 or 4 ranks)
```
