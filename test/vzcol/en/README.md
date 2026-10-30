# test/vzcol — one VZ shared reference column (fn_vz)

> English mirror of test/vzcol/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of the computational kernel of the vertical unsaturated flow (VZ)
runoff ([the chapter of the User's Guide](../../../docs/en/users_guide/vz.md),
developer.md §87) and of the read-out and ledger of a zone. With one column and
one zone, `Check_vzcol.py` confirms properties known analytically, and the
results of `param.txt` are also compared with the Log.txt of the reference
(ULP=0). vz_zone.csv and vz_column.csv are written with 16 digits, so their last
digit changes on a different CPU (differences in the vectorisation of
-march=native), and they are not part of the reference comparison (their content
is confirmed by the checks, and the independence from the number of MPI ranks by
a byte comparison with np = 1. Against a reference made on the same host they
can be compared bit by bit with `FILES="Log.txt vz_zone.csv vz_column.csv" ./Run.sh`).

## Set-up

All cells of a 3 × 8 grid (Δx = Δy = 10 m) form zone 1, which refers to one
column (3 m deep, 2.5 cm layers = 120 layers) and drains out of the system
(`vz_out_kind = 2`; no surface flow occurs). The soil depth is distributed
between 0.3 and 2.9 m, mixing values on interfaces (0.5, 1.0, etc.) and values
between interfaces (0.7375, 1.2340, etc.). The Kosugi parameters are example
values for the test (Ks = 100 mm/h, θs = 0.5, θr = 0.1, ψm = −0.5 m, σ = 1.5),
not recommended values for a particular soil.

| Configuration | File | Content |
|---|---|---|
| base | `param.txt` | initial steady gravity drainage q0 = 1 mm/h. Rain 1 mm/h (= q0) from 0 to 60 min, 50 mm/h from 61 to 180 min, then 0. dt = 5 s, dt_vz = 60 s, 12 h |
| fixed-pressure bottom | `param_fixed.txt` | 1 m deep with 1 cm layers, bottom ψ = 0 (f_vz_bottom = 2), 10 mm/h at the top for 10 days. Initially uniform ψ = −0.5 m |
| time convergence | `param_tight.txt` | the time error tolerances of the base (vz_tol_theta, vz_tol_psi, vz_tol_q) divided by 4 |
| area average | `param_avg.txt` | the base with f_vz_rain = 1 (area average within a column). The rain is uniform |
| zero soil depth | `param_sd0.txt` | the soil depth of the base replaced by `sd_zero.txt` (3 cells are 0 m) |
| hydrostatic initial condition | `param_hydro.txt` | 0.5 m deep with 2.5 cm layers, bottom ψ = 0 (f_vz_bottom = 2), initially hydrostatic with the water table at the bottom (vz_wt0 = 0.5 m), no rain for 1 day |
| trial defaults | `param_dflt.txt` | the base without `&list_vz_column` (defaults: the Kosugi set of Tatsunokuchi-yama TY, initially q0 = 0.1 mm/h, 10 m deep with 2.5 cm layers) |
| explicit defaults | `param_tyx.txt` | control with the same values as the trial defaults given explicitly |
| partial set | `param_partial.txt` | only Ks of the Kosugi parameters is given (must stop) |

## Checks (Check_vzcol.py)

- **Steady phase** (t ≤ 3600 s, rain = q0): with a free-drainage bottom a uniform
  ψ0 (K(ψ0) = q0) is an exact steady solution, so the cumulative flux at all
  depths = q0·t and the storage is unchanged.
- **Depth-wise conservation**: at each output depth d, S(d, t) − S(d, t1) =
  [F0(t) − F0(t1)] − [D(d, t) − D(d, t1)] within the budget of the nonlinear
  residual vz_mb_rate·t (holds structurally because drainage and storage are read
  with the same interpolation coefficients).
- **Kosugi model**: θ(ψ) and K(ψ) of the vertical profiles (vzprof) agree with the
  Kosugi model computed with Python's math.erfc (equations (7), (14) and (20) of
  Kosugi 1996). In addition, the output pairs of θ and K satisfy another expression
  that does not use ψ, K_r(S_e) = S_e^{1/2} {Q[Q^{-1}(S_e) + σ]}² (equation (21) of
  the same paper).
- **Aggregation of the zone**: the storage and drainage of the zone (aggregation
  by the weights W and M) agree with the values summed cell by cell by
  interpolating at the distributed soil depths. The balance residual of the zone
  is within the budget.
- **Rainfall and ledger**: the top input F0 of the column agrees with the rainfall
  built independently from the rainfall table (1-minute updates, linear
  interpolation), and the change of S_total in the Log agrees with F0 − outflow /
  total area.
- **Steady solution with a fixed-pressure bottom**: agrees with the profile of the
  steady solution dψ/dζ = 1 − q/K(ψ), ψ(L) = 0 integrated by RK4 (within the
  discretisation error of 1 cm layers), and the bottom flux = the top flux.
- **Time convergence**: the cumulative fluxes differ from the rerun with
  tolerances divided by 4 by at most 0.2%.
- **Area-average mode**: agrees with the strict mode when the rain is uniform.
- **Zero soil depth**: cells with soil depth 0 are read at the surface (drainage
  = rain, storage = 0), so the aggregation of the zone agrees with the sum of the
  cell-by-cell read-outs and the balance residual is within the budget.
- **Hydrostatic initial condition**: in a column with a fixed bottom pressure
  ψ = 0, the hydrostatic state with the water table at the bottom is a solution at
  rest with zero flux, so without rain ψ(ζ) = ζ − 0.5 m is kept and the cumulative
  fluxes at all faces stay 0.
- **Trial defaults**: the run with the column settings omitted agrees byte by byte
  in all outputs (Log.txt, CSV, vertical profiles) with the run giving the same
  values explicitly, and the six adopted items (five Kosugi parameters and q0) are
  displayed with `(default)`. Giving only some of the Kosugi parameters stops with
  the reason (checked by Run.sh).

## Running

```bash
make
./Run.sh          # serial + reference comparison + all checks
./Run_MPI.sh 4    # MPI (np ≤ 4). Log at ULP=0 against the serial reference, CSV identical to np = 1, area average also under MPI
```

## Verification record (2026-10-26. gfortran 13.3 / Open MPI 4.1, Ubuntu 24.04)

Steady phase: relative error of the cumulative fluxes 1e-15, storage change 0;
depth-wise conservation at 2.4e-4 of the budget; Kosugi model 4e-16 (θ) and
2e-15 (K), and 3e-15 against equation (21); the zone aggregation agrees with the
cell-by-cell sums to 1e-16; the
S_total balance of the Log 9e-12 m. The steady solution with a fixed-pressure
bottom differs from quadrature by 1.1e-4 m (arithmetic mean; 1.7e-5 m with the
harmonic mean), bottom flux = top flux to 2e-14. The difference from tolerances
divided by 4 is 2.6e-4. The area-average mode agrees exactly with the strict
mode. Under `-Og -fcheck=all` all output files agree between serial and np = 2
and 4; in release, np = 1, 2, 4 match the serial reference at ULP=0 (on the host
that made it, including the CSV files). In a build for Zen3 (`-march=znver3`)
Log.txt agrees bit by bit with the reference and the CSV files differ only in the
last digit (relative 1e-15).

Confirmation of the reference (2026-10-29, at the user's instruction): the
provisional reference was confirmed. It was updated with
`ULP=0 RTOL=0 FILES="Log.txt vz_zone.csv vz_column.csv" ./Run.sh -u` (serial
release). Log.txt and param.txt are bit-identical to the previous reference; only
the CSV files changed in the last digit (relative 1e-15 or less; in the residual
column, rounding noise of the order of 1e-12 m³). The working host has a different
CPU from the one that made the reference, and the difference comes from the default
`-march=native` (building the commit that made the reference on the same host gives
the same CSV files; not a code change). MPI np = 2 and 4 agree with the new
reference including the CSV files.
