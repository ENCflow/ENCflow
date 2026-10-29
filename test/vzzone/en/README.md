# test/vzzone — VZ zones, shared columns and outlets (fn_vz)

> English mirror of test/vzzone/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of the zones, column sharing, transfer to outlets, handling of rain,
restart and baseflow of the vertical unsaturated flow (VZ) runoff ([the chapter of the User's
Guide](../../../docs/en/users_guide/vz.md), developer.md §87). `Check_vzzone.py`
confirms quantities known analytically, and the results of `param.txt` are also
compared with the Log.txt of the reference (ULP=0; the CSV files are left out of
the comparison for the same reason as in [test/vzcol](../../vzcol/en/README.md)).

## Set-up

7 × 8 cells (Δx = Δy = 10 m). Columns 1–5 are VZ cells: rows 1–3 are zone 1,
rows 4–5 zone 2 and rows 6–8 zone 3. Column 6 is outside the domain, and in
column 7 only rows 1, 3 and 5 are inside the domain, as isolated receiving cells
O_a, O_b, O_c (surrounded by cells outside the domain, so surface water does not
move).

| Zone | Column referred to | Outlet |
|---|---|---|
| 1 | column 1 (Ks = 100 mm/h, σ = 1.5) | 0.6 to O_a, 0.4 to O_b |
| 2 | column 2 (Ks = 50 mm/h, σ = 1.0) | 1.0 to O_a (the same receiving cell as zone 1) |
| 3 | column 1 (shared with zone 1) | outflow from the system |

O_c is a control that receives only rain. The Kosugi parameters are example
values for the test. The rain is the same as in test/vzcol (1 mm/h from 0 to 60
min, 50 mm/h from 61 to 180 min, then 0), uniform over all cells. dt = 5 s,
dt_vz = 60 s, 12 h.

| Configuration | File | Content |
|---|---|---|
| base | `param.txt` | as above |
| duplicated column | `param_dup.txt` | zone 3 refers to a duplicate of column 1 (column 3) |
| rain distribution | `param_avg.txt` | rain given as a distribution (`prmap.txt`, mm/day × time-series multiplier) with f_vz_rain = 1 (area average within a column) |
| stop of the strict mode | `param_strictfail.txt` | the same rain with f_vz_rain = 0 → should stop because the rainfall differs within a column |
| save and restart | `param_save.txt` / `param_restart.txt` | save at 6 h (a synchronisation time) and restart up to 12 h |
| baseflow | `param_bflow.txt` (the series of zone 3 in `data_vzzone/base3.txt`) | zone 1 has a baseflow from the namelist (0 up to 30.5 min, a step from 2 to 4 mm/h at 90 min, 1 mm/h at 300.25 min, held afterwards), zone 3 a baseflow from a file (0.5 up to 10 min, 1.5 mm/h at 360 min, held afterwards). Run.sh rewrites tt, dir_result, f_state_save and f_state_restore with sed to also check save → restart and the stop for a series whose time decreases |

## Checks (Check_vzzone.py)

- **Depth of the receiving cells** (probes): with R the cumulative ground rainfall
  and V1, V2 the transfers of zones 1 and 2 to the surface, O_a = R + (0.6 V1 +
  V2)/A, O_b = R + 0.4 V1/A, O_c = R.
- **Total amount of surface water** (S_surf of the Log × number of cells × A) =
  rain on the three receiving cells + V1 + V2 (the amounts passed from two zones
  to the same receiving cell are added once).
- **Overall balance**: the change of S_total in the Log = rain − outflow (zone 3)
  / total area.
- The **balance residual of each zone** is within the budget of the nonlinear
  residual.
- **Shared versus duplicated column**: whether zone 3 shares column 1 or refers to
  its duplicate (column 3), the zone responses and the Log are bit-identical (a
  shared column only reduces the cost and does not change the result).
- **Rain distribution and area average**: the input of each zone = zone area × mean
  rainfall within the column (for column 1 the mean over the cells of zones 1 and
  3), and the S_total balance. With the same rain, the strict mode stops.
- **Restart**: the results after saving at 6 h and restarting (vz_zone.csv,
  vz_column.csv, Log) are bit-identical to the second half of the continuous run.
- **Baseflow** (compared with the results of `param.txt`): cumulative baseflow
  vbase = exact integral (computed with Python fractions) of the piecewise-linear
  series (end values held outside the range) × zone area; the VZ side (vin, vstore,
  vdrain, vcorr, residual and vz_column.csv) agrees as text with the run without
  baseflow; outlet volume (vsurface, vexternal) = drainage + baseflow. The depths of
  the receiving cells, the total amount of surface water and the S_total balance
  are checked with the same checks as the base run (the baseflow of zone 1 is an
  input to the system, that of zone 3 goes from outside to outside). Save → restart
  is bit-identical to the continuous run, and a series whose time decreases stops.

## Running

```bash
make
./Run.sh          # serial + reference comparison + all checks
./Run_MPI.sh 4    # MPI (np ≤ 4). Log at ULP=0 against the serial reference, CSV identical to np = 1; area average, stop and restart also under MPI
```

## Verification record (2026-10-26. gfortran 13.3 / Open MPI 4.1, Ubuntu 24.04)

The depths of the receiving cells follow the ratios within the 5 digits shown
by the probes, the total amount of surface water agrees to 3e-14 (relative), the
S_total balance to 2e-11 m, the zone residuals are at 3e-4 of the budget. Shared
and duplicated columns give exactly identical zone responses and Log. The input
in the area-average mode agrees to 3e-14, and the strict mode stops with
"rainfall differs within column" (on all ranks under MPI). Save → restart agrees
exactly with the continuous run (serial and MPI). Under `-Og -fcheck=all` all
output files (including probes) agree between serial and np = 2 and 4; in
release, np = 1, 2, 4 match the serial reference at ULP=0.

Confirmation of the reference (2026-10-29, at the user's instruction): the
provisional reference was confirmed. It was updated with
`ULP=0 RTOL=0 FILES="Log.txt vz_zone.csv vz_column.csv" ./Run.sh -u` (serial
release). Log.txt and param.txt are bit-identical to the previous reference; only
the CSV files changed in the last digit (relative 1e-15 or less; in the residual
column, rounding noise of the order of 1e-13 m³). The reason is the same as in
test/vzcol (the default `-march=native` on a working host with a different CPU; not
a code change). MPI np = 2 and 4 agree with the new reference including the CSV
files.

Baseflow (2026-10-27): the cumulative baseflow agrees with the analytical integral
to 2e-14 (relative), outlet volume = drainage + baseflow to 2e-14 (relative), the
VZ side and vz_column.csv agree with the run without baseflow, and the S_total
balance to 2e-11 m. Save → restart agrees exactly with the continuous run, and a
series whose time decreases stops with "baseflow times of zone 1 must not
decrease" (on all ranks under MPI). Under `-Og -fcheck=all` no runtime check
fires; in release np = 1, 2, 4 pass, and all output files (including probes) of
np = 1 and 4 agree. The existing configurations without baseflow agree byte for
byte with the reference in Log.txt, vz_zone.csv and vz_column.csv.
