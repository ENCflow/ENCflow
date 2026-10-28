# test/wfsed — verification of the stirring and transport of sediment by the coastal wave field (f_wfsed of fn_geomorph; stages W4 and W5)

> English mirror of test/wfsed/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Verification of stage W4, in which the coastal wave field ([User's Guide
chapter](../../../docs/en/users_guide/wavefield.md), developer.md §90) acts on bed load and
suspended load (stirring by the wave–current bed shear stress, and transport with the Eulerian
mean velocity u^E), and of stage W5 (the onshore transport velocity u_a of wave skewness and
asymmetry). The results are compared with the shear stress, equilibrium concentration and
transport of Soulsby (1997) and the u_a of Ruessink et al. (2012) assembled independently from
the model output, with the conservation of sediment and with the CERC longshore transport, and the results of `param.txt`
are also compared with the reference Log.txt, wavefield.csv, Z9998.txt and Hs9998.txt (ULP=0).

## Configuration

| Configuration | File | Content |
|---|---|---|
| Base (beach) | `param.txt` | The base case of test/wfcurrent (a 1:80 beach of 120 × 8 cells, Δx = 10 m, random waves H_m0 = 1 m, T = 8 s, direction 20°, `wf_flow = 2` with the roller) plus bed load (MPM) and suspended load (fine sand 0.2 mm) with `f_wfsed = 1` (the coefficients of u_a at the default 0.1). The north and south sides are lateral Neumann. One hour. Also the straight run for the restart check (save_all) |
| Stirring | `param_stir.txt` | Random waves H_m0 = 0.5 m, T = 8 s only, on a flat bed 5 m deep (no flow; `wf_flow = 0`). Suspended load only, without u_a (`wfsed_facsk = wfsed_facas = 0`). 30 minutes |
| Bed load | `param_bed.txt` | A flat channel 2 m deep (600 m × 40 m) with a current of 0.45 m/s from sources and random waves H_m0 = 0.5 m, T = 6 s, direction 30° (`wf_flow = 0`). Bed load only, without u_a. 30 minutes |
| Closed basin | `param_closed.txt` | The base case with walls on all four sides for the flow (the longshore current turns at the north wall and circulates). 30 minutes |
| High and low waves | `param_storm.txt` / `param_calm.txt` | Normally incident H_m0 = 2 m, T = 8 s (erosion) and H_m0 = 0.6 m, T = 12 s (recovery) on the base beach. 30 minutes |
| Breaking turbulence | `param_turb.txt` | The base case with the stirring by the turbulence of wave breaking (`f_wfsed_turb = 1`; the form of turb = wave_averaged of XBeach) |
| Restart | `param_rt1.txt` → `param_rt2.txt` | The base case saved at 1530 s (between the wave-field updates and the bed updates), restored and continued to 3600 s |
| Invalid settings | `param_bad1.txt` to `param_bad5.txt` | No `fn_wavefield`, together with the longshore transport of fn_wave, `f_wfsed = 2`, `f_wavefield = 0`, `f_wfsed_turb = 1` with `f_wfsed = 0` (each must stop) |

## Checks (Check_wfsed.py)

- **Stirring** (stir): there is no flow, so the suspended sediment is not transported and the
  concentration of each cell approaches the equilibrium concentration. From the orbital velocity
  Wu of the model, τ*_w = ½ f_w u_w²/(s g d) (u_w = √2 u_rms, f_w = 1.39 (A/z0)^−0.52,
  A = u_w/ω, z0 = d50/12; Soulsby 1997) and the equilibrium concentration
  C_eq = esa (τ*_w/τ*c − 1) are assembled, and the concentration hs/h of the model agrees within
  1e-5 (relative) with the E-D relaxation per bed update c_n = (C_eq/β)(1 − (1 − β w_f Δt/h)^n).
  The total solid Σ hs + (1 − λ) Σ (z − z0) is conserved (within 1e-10 of the total, in the
  double precision of the save).
- **Bed load** (bed): the cell estimates of the bed load Qbx and Qby agree within 1e-5
  (relative) with q_b = q*(τ*_max) √(τ*_c/τ*_max) √(sgd³) assembled from the velocity, depth,
  orbital velocity and mean wave direction of the model (τ*_max from eqs. 69 and 70 of Soulsby
  1997, q* by MPM; with u_a = 0 in this configuration the shear stress τ*_s of the transport
  speed equals τ*_c), point in the current direction, and the waves increase the transport of the
  current alone at least 1.5 times.
- **Longshore transport on the beach** (beach): the longshore transport is northward (the same as
  the current) in every row, its cross-shore distribution peaks in the surf zone (the cells where
  breaking dissipation exceeds 5% of its maximum), offshore of the surf zone it is at most 5% of
  the peak, the row totals differ by at most 1e-4 and the bed change by at most 1e-5 m between
  rows (lateral Neumann sides), the total is 0.2 to 5 times CERC (Komar & Inman 1970; K = 0.77,
  with H_rms, depth and direction at the cell of the maximum wave height taken as the breaker
  point; agreement in order of magnitude, since it is a quantity fitted by a coefficient), the
  cross-shore transport in the surf zone is offshore (undertow), and deposition lies offshore of
  erosion (bar formation by the undertow).
- **Closed basin** (closed): the total solid with bed load, advection of suspended load (face
  fluxes with the Stokes transport and u_a subtracted) and E-D together is conserved (within
  1e-10 of the total).
- **Onshore transport velocity** (asym; result of the base case): the u_a of the model (output
  Wua) agrees within 2e-4 (relative) with u_a = (f_Sk S_k − f_As A_s) u_rms (van Thiel de Vries
  2009; S_k = B cos ψ and A_s = B sin ψ from the parameterization of Ruessink et al. 2012 with the
  Ursell number Ur = (3/8)√2 H_rms k/(kh)³, coefficients as in the public XBeach source)
  assembled from the wave height, depth, period and orbital velocity, and is onshore in the
  cells with waves.
- **Erosion by high waves and recovery by low waves** (shore): with high waves the cross-shore
  transport is offshore everywhere in the surf and shoaling zones (the undertow beats u_a); with
  low waves it is onshore in every cell with transport offshore of the surf zone (u_a beats the
  undertow). A qualitative check (V13 of wavefield_plan.md).
- **Stirring by the turbulence of wave breaking** (turb; compared with the base case): the output
  near-bed turbulence Wkb agrees within 1e-4 of its maximum with k_b = k_s/(exp(h/L_mix) − 1)
  (k_s = (D_r/ρ)^{2/3}, D_r = 2βgE_r/c, L_mix = √(2E_r T/(ρc))) assembled from the output roller
  energy E_r, the depth and the period, and the output Wu stays u_rms without turbulence (the linear
  theory H_rms σ/(2√2 sinh kh)). The maximum of k_b lies shoreward of the maximum of breaking
  dissipation, the longshore transport exceeds that of the base case (ratio 1 to 1.5), and the row
  totals differ by less than 1e-4.
- **Restart** (Run.sh): state.dat, swflow_enc.dat, wavefield.dat (including the export to
  sediment) and the final fields (Z, Hs, Qby, Qsy) of the split run are byte-identical to the
  straight run.
- **Invalid settings** (Run.sh): the five configurations stop with the reason.

## Running

```bash
make
./Run.sh          # serial + reference comparison + checks (about 2 minutes with one thread)
./Run_MPI.sh 4    # MPI (np ≤ 4). ULP=0 against the reference; stirring, bed load, the closed basin and the breaking turbulence byte-identical to np = 1; restart also under MPI
```

## Verification record (2026-10-27; gfortran 13.3 / Open MPI 4.1.6, Ubuntu 24.04)

For stirring (u_rms 0.157 m/s, τ*_w 0.0666) the largest relative difference between the model
concentration and the relaxation towards the equilibrium concentration is 4.9e-7, and the total
solid is conserved within 3.2e-12 of the total suspended load. For bed load the largest relative
difference from the assembled transport is 1.5e-7, the direction differs by 5.5e-15 rad, and the
waves increase the transport 2.24 times. The longshore transport on the beach totals 4.47e-2 m³/s
(northward; bed load 1.6e-3, suspended load 4.31e-2), 1.62 times CERC (2.76e-2 m³/s); its
cross-shore distribution peaks at i = 95 inside the surf zone (i = 86 to 109), offshore of the surf
zone it is at most 0.7% of the peak, the row totals differ by 1.6e-5 and the bed change by 2.2e-7 m
between rows, the cross-shore transport summed over the surf zone is −1.28e-3 m²/s (offshore), and
the largest deposition (i = 92) lies offshore of the largest erosion (i = 109). In the closed basin
the total solid is conserved within 4.6e-14 of the total. u_a agrees with the assembled formula
within 8.8e-7 (relative) over 872 cells, with a maximum of 0.061 m/s (i = 96). With high waves the
transport is offshore in cells 20 to 110, and with low waves it is onshore in cells 46 to 89 offshore
of the surf zone. The restart continuation is byte-identical to the straight run. With
`-Og -fcheck=all` the serial run and np = 2 agree (no out-of-bounds access); with release builds
np = 1, 2 and 4 are ULP=0 against the serial reference (stirring, bed load and the closed basin
byte-identical to np = 1; restart also under MPI).

The stirring by the turbulence of wave breaking (added 2026-10-28; developer.md §90.14) has a
largest difference between the output Wkb and the assembled k_b of 9.2e-6 of the maximum and
between the output Wu and the linear-theory u_rms of 1.1e-6 of the maximum (Wu contains no
turbulence); the maximum k_b of 0.019 m²/s² is at the shoreline cell (i = 109, depth 0.30 m,
stirring speed ×1.10), shoreward of the peak breaking dissipation (i = 98); the longshore transport
is 1.019 times the base case and the row totals differ by 1.6e-5. With release builds np = 1, 2 and
4 are ULP=0 against the serial reference and the turbulence case is byte-identical to np = 1; with
`-Og -fcheck=all` the serial run and np = 2 agree; the restart continuation saved at 1530 s is
byte-identical to the straight run.
