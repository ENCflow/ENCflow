# test/sfzone — zones, tanks and outlets of the storage function method (fn_sfm)

> English mirror of test/sfzone/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of the solution of the tanks, the input of the zones, the transfer to outlets, the
handling of rain, baseflow, synchronisation, restart, lag time and the combination with VZ of the
storage function runoff of zones ([the chapter of the User's
Guide](../../../docs/en/users_guide/sfm.md), developer.md §106). `Check_sfzone.py` compares
with analytic solutions, reference solutions and conservation laws, and the results of
`param.txt` are also compared with the Log.txt of the reference (ULP=0; the CSV files are
left out of the comparison for the same reason as in [test/vzcol](../../vzcol/en/README.md)).

## Set-up

7 × 8 cells (Δx = Δy = 10 m; the same grid and rain as [test/vzzone](../../vzzone/en/README.md)).
Columns 1–5 are zone cells: rows 1–3 are zone 1, rows 4–5 zone 2 and rows 6–8 zone 3.
Column 6 is outside the domain, and in column 7 only rows 1, 3 and 5 are inside the domain,
as isolated receiving cells O_a, O_b, O_c (surrounded by cells outside the domain, so surface
water does not move).

| Zone | Tank (S [mm] = K·q[mm/h]^P) | Initial runoff rate | Outlet |
|---|---|---|---|
| 1 | K = 10, P = 0.6 | 0.1 mm/h | 0.6 to O_a, 0.4 to O_b |
| 2 | K = 2 (h), P = 1 (linear reservoir) | 1 mm/h | 1.0 to O_a (the same receiving cell as zone 1) |
| 3 | K = 20, P = 0.4 | 0 (dry) | outflow from the system |

O_c is a control that receives only rain. K and P are example values for the check. The rain
is 1 mm/h from 0 to 60 min, 50 mm/h from 61 to 180 min, then 0, uniform over all cells.
dt = 5 s, dt_sfm = 0 (every step), 12 h.

| Configuration | File | Content |
|---|---|---|
| base | `param.txt` | as above |
| rain distribution | `param_avg.txt` | rain given as a distribution (`prmap.txt`, mm/day × time-series multiplier) with f_sfm_rain = 1 (area average within a zone) |
| stop of the strict mode | `param_strictfail.txt` | the same rain with f_sfm_rain = 0 → should stop because the rainfall differs within a zone |
| save and restart | `param_save.txt` / `param_restart.txt` | save at 6 h (a synchronisation time) and restart up to 12 h |
| baseflow | `param_bflow.txt` (the series of zone 3 in `data_sfzone/base3.txt`) | zone 1 has a baseflow from the namelist and zone 3 from a file (the same series as test/vzzone). Run.sh also checks save → restart with sed |
| defaults | `param_dflt.txt` | sfm_p and sfm_q0_mmh of zone 1 and the numerical controls are not written. Run.sh also checks with sed that a configuration without K stops |
| synchronisation interval | `param_sync.txt` | dt_sfm = 60 s. Run.sh also checks with sed save → restart in the middle of an interval (21625 s) |
| steady state | `param_steady.txt` | constant rain of 10 mm/h for 48 h |
| lag time | `param_lag.txt` | lag times of 0.5, 1 and 0.2501 h for zones 1, 2 and 3 (zone 3 is rounded to a multiple of dt = 5 s, 0.25 h = 180 steps). Run.sh also checks with sed save → restart at 6 h, a run with dt_sfm = 60 s, and save → restart in the middle of its interval (21625 s) |
| combination with VZ | `param_mosaic.txt` (`zone_mosaic.txt`, `vzzone_mosaic.txt`) | rows 6–8 are a VZ zone (trial default column, soil depth 1 m, outflow from the system) and the storage function has zones 1 and 2. Run.sh also checks with sed the stops for overlapping zones (`vzzone_overlap.txt`), a storage function outlet on a VZ cell, and P > 1 |

## Checks (Check_sfzone.py)

In SI, a tank is q = c·S^m (m = 1/P, c = (1000/K)^m / 3.6×10⁶, S [m], q [m/s]). The rain of
each step is made in Python following the rule of rainfall updates (every dt_prupdate = 60 s).

- **Input**: vin of a zone = area × accumulated ground rainfall.
- **Exact solution of the linear reservoir** (zone 2): for piecewise-constant rain, step by
  step S ← S_eq + (S − S_eq)·exp(−Δt/τ) (τ = 3600·K s, S_eq = τ·r).
- **Reference solution of nonlinear tanks** (zones 1 and 3): dS/dt = r − c·S^m with the same
  rain solved by RK4 with each step split into 10.
- **Analytic recession**: from the storage S1 at the first recording time t1 after the rain
  stops, S^(1−m) = S1^(1−m) + (m − 1)·c·(t − t1) (exponential for P = 1).
- **Consistency of the output**: column q = (S/K)^(1/P); balance residual of the zones at the
  rounding level.
- **Depth of the receiving cells** (probes): with R the accumulated ground rainfall and V1, V2
  the transfers of zones 1 and 2, O_a = R + (0.6 V1 + V2)/A, O_b = R + 0.4 V1/A, O_c = R. Total
  surface water = rain on the receiving cells + V1 + V2.
- **Overall balance**: change of S_total in the Log = rain − outflow from the system (zone 3) /
  total area (the storage of the tanks is in S_grnd).
- **Rain distribution and area averaging**: input of each zone = zone area × mean rainfall
  within the zone; S_total balance. With the same rain, the strict mode stops.
- **Restart**: sfm_zone.csv and the Log after saving at 6 h and restarting are bit-identical to
  the second half of the continuous run (also with baseflow).
- **Baseflow**: cumulative vbase = exact integral of the piecewise-linear series (Python
  fractions) × zone area; the tank columns are identical as strings to the run without
  baseflow; outlet volume = runoff + baseflow; S_total balance.
- **Defaults**: the adopted values are displayed with `(default)`, and all outputs are
  bit-identical to `param.txt`, which gives the same values explicitly.
- **Synchronisation interval**: the storage at the synchronisation times with dt_sfm = 60 s
  agrees with the reference solution within sfm_tol, and the input agrees with every-step
  synchronisation. The storage after save → restart in the middle of an interval agrees with
  the continuous run (within the tolerance), and the balance residual is at the rounding level.
- **Steady state**: after 48 h, q → 10 mm/h and S = K·r^P.
- **Lag time**: for the input with the rain lagged by the number of lag steps (the initial
  runoff rate q0 before the start), the exact solution of the linear reservoir for zone 2
  and the RK4 reference solution for zones 1 and 3. Column vlag = rain of the last T_L
  (including the steady part of q0 just after the start) × zone area; input vin equals the
  run without lag; balance residual (including the water in transit) at the rounding level;
  S_total balance of the Log. Save → restart is bit-identical to the continuous run. The
  storage with dt_sfm = 60 s agrees with the reference solution within sfm_tol.
- **Combination with VZ**: sfm_zone.csv of storage function zones 1 and 2 and the probes of the
  receiving cells agree with `param.txt`; S_total balance of the Log (including the VZ storage
  and outflow from the system).

## Running

```bash
make
./Run.sh          # serial + reference comparison + all checks
./Run_MPI.sh 4    # MPI (np ≤ 4). Log ULP=0 against the serial reference, CSV identical to np = 1, area averaging, stops, restart and the combination also under MPI
```

## Verification record (2026-11-11. gfortran 13.3 / Open MPI 4.1, Ubuntu 24.04)

Relative 3.2e-7 from the exact solution of the linear reservoir, 4e-8 (storage) and 1.1e-7
(runoff rate) from the RK4 reference solution of the nonlinear tanks, and within 3.6e-7 of the
analytic recession. The lag-time run is within 2.8e-7 of the exact solution and 1.1e-7 of the
reference solution for the lagged rain, and the water in transit agrees to 4e-16 (relative).
The balance residual of the zones is 4e-14 of the input, the total surface
water 5e-14 (relative), and the S_total balance 6.7e-15 m. With dt_sfm = 60 s the storage is
within 1.5e-5 of the reference solution, and the steady q is within 4.4e-9 of 10 mm/h. MPI
np = 1, 2, 4 match the serial reference with ULP=0, and sfm_zone.csv and the state file saved in
the middle of an interval are byte-identical to np = 1. With `-Og -fcheck=all`, all outputs of
serial and np = 2, 4 agree. The reference was placed provisionally on the basis of the analytic
checks (to be confirmed by human visual inspection).
