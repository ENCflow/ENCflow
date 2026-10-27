# test/wfcurrent — verification of the action of the coastal wave field on the flow (wf_flow of fn_wavefield; stage W2)

> English mirror of test/wfcurrent/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Verification of stage W2, in which the coastal wave field ([User's Guide
chapter](../../../docs/en/users_guide/wavefield.md), developer.md §88) acts on the
shallow-water flow (radiation-stress forcing, the roller, the GLM Stokes drift, wave-current
bed friction and the lateral Neumann flow boundary). The two-way coupling with the
action of the current on the waves (stage W3, `f_wf_current`) is checked too (`param_cur.txt`).
The results are compared with theoretical solutions, closed-form balances and conservation
laws, and the results of `param.txt` are also compared with the reference Log.txt,
wavefield.csv, E9998.txt and v9998.txt (ULP=0).

## Configuration

A beach of uniform slope 1/80 (`make_z.py`; the same profile as test/wfshoal, 120 × 8 cells,
Δx = Δy = 10 m). The west (i = 1) is offshore with the incident waves, and the shoreline is at
x = 1100 m. The north and south sides are lateral Neumann for both waves and flow
(`wf_bc_side` = 2, `f_bc_n` = `f_bc_s` = 3), and the offshore flow side is long-wave radiation.

| Configuration | File | Content |
|---|---|---|
| Base | `param.txt` | Random waves H_m0 = 1 m, T = 8 s, direction of travel 20°, spreading 20°. `wf_flow = 2` with the roller (default). One hour. Also the straight run for the restart check (save_all) |
| No roller | `param_long.txt` | As the base without the roller |
| Setup | `param_setup.txt` | Regular waves H = 1 m, T = 8 s, normal incidence. `wf_flow = 1` (forcing only). The lower bound of the friction velocity is vv = 0.2 m/s to damp the start-up seiche |
| Uniform depth | `param_flat.txt` | A flat bed 5 m deep with a wall in the east. Random waves H_m0 = 1.5 m at a direction of travel of 30°; the alongshore forcing comes only from the dissipation of bottom friction f_w = 0.05. `wf_flow = 2` without the roller. Roughness n = 0.05 (a spin-up time scale of about 10 minutes) |
| Grid rotated by 90° | `param_rot.txt` | The base case on a grid rotated clockwise by 90° (8 × 120; north is offshore and the east and west sides are lateral Neumann) |
| Two-way coupling | `param_cur.txt` | The base case with the action of the current on the waves (`f_wf_current = 1`; stage W3). The longshore current changes the waves (Doppler shift, refraction and transport by the current), and the waves drive the longshore current |
| Restart | `param_rt1.txt` → `param_rt2.txt` | The base case saved at 90 s (during the ramp-up, between wave-field updates), restored and continued to 3600 s |
| Invalid setting | `param_bad.txt` | `wf_flow = 3` (must stop) |

## Checks (Check_wfcurrent.py)

- **Setup** (setup): at the steady state at rest, the per-face discrete balance
  g_e (η_{i+1} − η_i)/Δx = (F_i + F_{i+1})/(2ρ h_f) (h_f is the mean depth of the two cells,
  g_e the steep-slope gravity correction) holds within a residual of 2% + 5e-6 m/s². Offshore
  of breaking, the set-down agrees with η = −H²k/(8 sinh 2kh) (Longuet-Higgins & Stewart
  1962; relative to the offshore boundary cell) within 2% of the set-down at the breaker
  line, and in the surf zone the slope dη/dx = K dz/dx is within −8% to +4% of
  K = 1/(1 + 8/(3γ²)) = 0.186 of Bowen et al. (1968) (slightly smaller than the shallow-water
  limit because of the finite depth and the Miche-type breaking wave height). Uniform
  alongshore.
- **Longshore current on a uniform depth** (flat): no refraction and uniform alongshore.
  The model v agrees within 2% of the maximum velocity with v = v_S + v_E, where v_E solves
  the per-cell alongshore momentum balance F_y/(ρh) = g n² |V_E| v_E / h^{4/3}
  (v_E = v − v_S, |V_E| = √(u_E² + v_E² + (1.16 u_rms)²)) in closed form; the integral
  alongshore momentum balance Σ F_y = Σ τ_y holds within 2%, and the current flows north in
  every cell. Cross-shore, the per-face balance g Δη/Δx = F_x/(ρh) + friction of the undertow
  u^E = −u^S holds within 1% (the undertow friction is about 23% of the setup gradient). The
  GLM Lagrangian velocity u^L ≈ 0.
- **Longshore current on the beach** (long, roller): the integral alongshore momentum
  balance Σ F_y = Σ τ_y holds within 2%, the per-cell closed form within 5% of the maximum
  velocity (the share by which the oblique ENC faces and advection smooth the sharp change
  of forcing at the onset of breaking), the maximum of the longshore current lies in the
  surf zone, the flow offshore of the surf zone (breaking dissipation below 0.1% of its
  maximum) is within 1% of the maximum, the rows including those at the lateral Neumann
  sides differ by less than 1% of the maximum, and u^L ≈ 0. With the roller, the peak of
  the forcing moves shoreward by at least one cell and the centroid of the longshore current
  by at least 3 m, the roller energy budget (breaking in the ledger + removal by the limit =
  Σ 2βgE_r/c + outflow at the shoreline) closes within 1%, and the roller energy exists only
  in the surf zone.
- **Grid rotated by 90°** (rot): the base result mapped from cell (i, j) to (9 − j, i), with
  the eastward u becoming the southward v and the y components (south positive) becoming the
  x components with the sign reversed, agrees with the water level, velocities, forcing,
  Stokes drift and roller of the rotated grid (water level 1e-4 m, velocities 1e-3 of the
  maximum). A check of the lateral Neumann boundary on the W and E sides and of the sign
  convention of the y direction (agreement at the rounding level, since the order of
  operations differs).
- **Two-way coupling** (cur): the same checks of the longshore current on the beach as the base
  case (per-cell closed form within 5% of the maximum velocity, integral momentum balance within
  2%, alongshore uniformity, u^L ≈ 0) and the roller energy budget within 1% (the roller is also
  carried by the current and its phase speed is the intrinsic σ̄/k̄; the breaking in the ledger is
  in action × ω, so it is converted to energy with σ/ω weighted by the distribution of breaking).
  The action of the current changes the wave height by 1e-4 to 5% (the action is effective), and
  the wave ledger (action × ω) closes.
- **Restart** (Run.sh): state.dat, swflow_enc.dat, wavefield.dat and the final fields of the
  split run are byte-identical to the straight run (the ramp-up of the forcing, the forcing
  held between quasi-steady updates and the continuation of the roller state).
- **Invalid setting** (Run.sh): `wf_flow = 3` stops with the reason.

## Running

```bash
make
./Run.sh          # serial + reference comparison + checks (about 2 minutes with one thread)
./Run_MPI.sh 4    # MPI (np ≤ 4). ULP=0 against the reference; the rotated grid and the two-way coupling byte-identical to np = 1; restart also under MPI
```

## Verification record (2026-10-27; gfortran 13.3 / Open MPI 4.1.6, Ubuntu 24.04)

For the setup, the residual of the per-face discrete balance is 0.00 of the tolerance
(111 faces), the set-down offshore of the breaker line (i = 94) is −48.65 mm in the model
and −48.57 mm by Longuet-Higgins & Stewart (maximum difference offshore of the surf zone
0.078 mm), and K of the surf-zone slope is 0.1766 to 0.1834 (12 cells; Bowen et al. 0.1858).
The longshore current on the uniform depth has a maximum of 0.0555 m/s, differs from the
per-cell closed form by 0.87% of the maximum, has an integral ratio Σ τ_y/Σ F_y = 0.986, a
residual of the cross-shore per-face balance of 3.4e-4 (the undertow friction is 23 to 24%
of the setup gradient) and a maximum u^L of 6.8e-6 m/s. The longshore current on the beach
has, without the roller, a maximum of 0.224 m/s, a difference from the closed form of 3.2%,
an integral ratio of 1.000 and a row difference of 7.1e-5 m/s (0.03% of the maximum); with
the roller, a maximum of 0.229 m/s, a difference of 3.0%, a ratio of 0.998 and a row
difference of 5.4e-5 m/s (0.02%); the peak of the forcing moves shoreward by one cell and
the centroid of the current by 7.1 m, and the residual of the roller energy budget is
0.00%. On the rotated grid the water level differs by 1.0e-5 m and the velocities by
6.0e-5 m/s (2.6e-4 of the maximum). The two-way coupling (stage W3) has a maximum of
0.229 m/s, a difference from the closed form of 2.99%, a ratio of 0.998 and a row difference
of 3.5e-5 m/s; the residual of the roller energy budget is 0.01%, the current changes the
wave height by at most 0.17% and the peak of the longshore current by −0.07%, and the
residual of the wave ledger (action × ω) is 1.1e-7 of the inflow. The restart continuation
is byte-identical to the straight run. With `-Og -fcheck=all` the serial run and np = 2 agree
(no out-of-bounds access); with release builds np = 1, 2 and 4 are ULP=0 against the serial
reference, and the rotated grid and the two-way coupling are byte-identical to np = 1.
