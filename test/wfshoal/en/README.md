# test/wfshoal — verification of the coastal wave field on a beach profile (fn_wavefield)

> English mirror of test/wfshoal/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Verification of the coastal wave field ([User's Guide chapter](../../../docs/en/users_guide/wavefield.md),
developer.md §88) on a one-dimensional beach profile. Shoaling, saturated breaking,
refraction, breaking of random waves, bottom friction, unsteady propagation, the ledger
and restarts are checked against theoretical solutions and against discrete steady
solutions built independently in `Check_wfshoal.py`. The results of `param.txt` are also
compared with the reference Log.txt, wavefield.csv and Wh0001.txt (ULP=0).

## Configuration

A beach of uniform slope 1/80 (`make_z.py`; 120 × 8 cells, Δx = Δy = 10 m). The west
(i = 1) is offshore with 13.7 m depth; the shoreline is at x = 1100 m in the east, with dry
land east of it. The north and south sides are lateral Neumann, so the solution must be
exactly uniform alongshore (the 8 rows bit-identical). The water level is 0 and there is no
flow (the wave field of stage W1 does not act on the flow).

| Configuration | File | Content |
|---|---|---|
| Base | `param.txt` | Time series of random waves (H_m0 1.0 → 1.5 m, T 8 → 9 s, direction of travel 340° → 20° crossing 0°, spreading 20 → 15°). Quasi-steady, updated every 600 s. Baldock breaking, f_w = 0.02, diagnostics written |
| Shoaling | `param_shoal.txt` | Regular waves H = 1 m, T = 8 s, normal incidence. wf_tol = 1e-8 |
| Refraction | `param_refr.txt`, `param_refr80.txt` | Regular waves H = 0.2 m, T = 8 s, angle of incidence 30°. 40 and 80 directional bins |
| Breaking | `param_brk.txt` | Random waves H_m0 = 1.5 m, T = 8 s, normal incidence (unidirectional). Baldock et al. (1998) |
| Breaking and friction | `param_brkjb.txt` | As above with Janssen & Battjes (2007) and f_w = 0.02 |
| Unsteady | `param_unst.txt` | The breaking configuration in the unsteady mode from calm for 900 s (saved to save_all) |
| Restart | `param_rt1.txt` → `param_rt2.txt` | Unsteady run saved at 100 s (the front is in the middle of the domain), restored and continued to 900 s |
| No wave field | `param_nowf.txt` | The base configuration without fn_wavefield |
| Invalid setting | `param_bad.txt` | wf_ntheta = 30 (not a multiple of 8; must stop) |

## Checks (Check_wfshoal.py)

- **Shoaling and saturated breaking** (shoal): regular waves have no dissipation other
  than saturation, so the discrete steady solution conserves c_g E (the two-link
  decomposition uses only the axis link for normal incidence) and is capped at H = γh in
  cells where H > γh. The wave height agrees with the recursion
  E_i = min(E_{i−1} c_{g,i−1}/c_{g,i}, ρg(γh_i)²/8) and with linear theory
  H = H_0 (c_g1/c_g)^{1/2} (γh in the saturated zone). The dispersion relation is solved
  independently by Newton's method in double precision. Cells with depth at or below
  wf_hmin and land have no waves.
- **Refraction** (refr): for depths of 1 m or more, the mean direction follows Snell's law
  sin α/c = sin α_0/c_0 and the wave height follows H_0 K_s K_r
  (K_r = (cos α_0/cos α)^{1/2}) (within 2° and 1% with 40 bins). With 80 bins the error
  falls below 0.65 times (first-order convergence).
- **Breaking** (brk, brkjb): the discrete steady solution for normal incidence, uniform
  alongshore, is fixed by the per-cell balance c_{g,i} E_i + Δx D(E_i) = c_{g,i−1} E_{i−1}
  and the recursion with the limit H_rms ≤ γmax h. D (Baldock and Janssen & Battjes
  breaking, friction with the coefficients of Guza & Thornton) is written independently in
  this script from the forms in the literature. The wave height, the breaking dissipation
  Wb and the orbital velocity Wu agree with this solution. In addition, the difference from
  the energy balance d(E c_g)/dx = −D integrated by RK4 with a fine step (Δx/100) is within
  2% of the offshore wave height (the size of the first-order upwind discretisation error).
- **Unsteady** (unst): at t = 60 s the position where E is half the steady value agrees
  within 2 cells with the distance travelled at the group velocity, ∫dx/c_g = 60 s. After
  900 s it reaches the same discrete steady solution as the quasi-steady mode, and the
  cumulative ledger (change of storage − net input) closes.
- **Restart** (rt and Run.sh): wavefield.dat, state.dat and Wh9998 of the split run are
  byte-identical to the straight run, and the ledger CSV rows agree with the rows of the
  straight run at the same times.
- **Base** (base): the offshore waves at each update time equal the linear interpolation
  of the series (the direction the short way across 0°), every update converges, the field
  is uniform alongshore, and Wu = H_rms σ/(2√2 sinh kh).
- **Ledger**: the quasi-steady imbalance (rate of change of storage in the last iteration)
  is small compared with the inflow (1e-8 to 1e-9 or less for the configurations with
  wf_tol = 1e-8).
- **No action on the flow** (Run.sh): Log.txt without the wave field is byte-identical to
  the base Log.txt.
- **Invalid setting** (Run.sh): a wf_ntheta that is not a multiple of 8 stops with the reason.

## Running

```bash
make
./Run.sh          # serial + reference comparison + all checks (about 12 s)
./Run_MPI.sh 4    # MPI (np ≤ 4). ULP=0 against the reference; breaking and unsteady byte-identical to np = 1; restart also under MPI
```

## Verification record (2026-10-27; gfortran 13.3 / Open MPI 4.1.6, Ubuntu 24.04)

Shoaling agrees with the discrete solution and linear theory to 5.7e-8 (the resolution of
the single-precision output), with 13 saturated cells and a ledger residual of 1.6e-16 of
the inflow. Refraction with 40 bins deviates by at most 1.52° in direction (near 1 m
depth) and 0.50% in height; with 80 bins 0.63° and 0.29% (ratios 0.42 and 0.57). Breaking
agrees with the discrete solution to 5.1e-8 (Baldock) and 4.5e-8 (Janssen & Battjes +
friction), Wb to 4.5e-8 and 7.5e-8, Wu to 5.7e-8 and 5.8e-8; the difference from the
energy balance with a fine step is 0.93% and 0.97% of the offshore wave height, and 3 and
2 cells hit the limit. The unsteady front is at 434.2 m (group-velocity travel distance
435.0 m), the steady state differs from the quasi-steady one by 0, and the cumulative
ledger residual is 2.1e-14. The restart continuation is byte-identical to the straight
run. The interpolation of the offshore waves in the base case is exact to the printed
digits. With `-Og -fcheck=all` the serial run and np = 2 and 4 agree in the reference
comparison (no out-of-bounds access); with release builds np = 1, 2 and 4 are ULP=0 against
the serial reference.
