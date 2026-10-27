# test/wfdoppler — verification of the change of the coastal wave field by currents (f_wf_current of fn_wavefield; stage W3)

> English mirror of test/wfdoppler/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Verification of stage W3, in which the coastal wave field ([User's Guide
chapter](../../../docs/en/users_guide/wavefield.md), developer.md §88) is changed by the
shallow-water flow (the dispersion relation with the Doppler shift, refraction and
advection by the current, and blocking). The results are compared with the conservation
of wave action flux, using a dispersion relation solved independently here, and the
results of `param.txt` are also compared with the reference Log.txt, wavefield.csv,
Wh9998.txt and u9998.txt (ULP=0).

## Configuration

A channel 600 m long and 40 m wide (`make_z.py`; 120 × 8 cells, Δx = Δy = 5 m). The bed rises
uniformly from −3 m at the west end to −1.5 m at the east end, so the velocity of a flow with
discharge q = 1.2 m²/s is faster in the shallow east. The flow enters from sources in the end
column and leaves through the opposite side (long-wave radiation). The waves are incident on
the west side, and the north and south sides are lateral Neumann for both waves and flow
(`wf_bc_side` = 2, `f_bc_n` = `f_bc_s` = 3). The river-mouth jet is 300 m × 200 m (120 × 80
cells, Δx = 2.5 m; a channel of the same type as test/wave_river).

| Configuration | File | Content |
|---|---|---|
| Base (blocking) | `param.txt` | Random waves H_m0 = 0.05 m, T = 1.5 s (unidirectional) on an opposing current (westward from sources in the east; 0.38 → 0.69 m/s). The dispersion relation loses its root at x ≈ 470 m (blocking). One hour. Also the straight run for the restart check (save_all) |
| Opposing current | `param_opp.txt` | Regular waves H = 0.05 m, T = 4 s on the same opposing current (not blocked, not breaking) |
| Following current | `param_fol.txt` | The flow reversed (eastward from sources in the west; 0.37 → 0.66 m/s), regular waves H = 0.05 m, T = 4 s |
| Following, finer directions | `param_fol72.txt` | The following current with 72 directional bins (the default is 40) |
| Unsteady | `param_opp_u.txt` | Regular waves on the opposing current (param_opp) in the unsteady mode (`wf_mode = 1`) from calm for 40 minutes. The flow also starts from rest |
| No current effect | `param_nocur.txt` | The same flow as the base with `f_wf_current = 0` (the path of stage W1) |
| Zero flow | `param_zero.txt` / `param_zero_off.txt` | No sources; `f_wf_current` = 1 and 0 |
| Restart | `param_rt1.txt` → `param_rt2.txt` | The base case saved at 1500 s (between the wave-field updates at 1200 s and 1800 s), restored and continued to 3600 s |
| River-mouth jet | `param_river.txt` / `param_river_nocur.txt` | Random waves H_m0 = 0.2 m, T = 2.5 s, spreading 20° from offshore on a jet leaving the channel at 1 m/s; `f_wf_current` = 1 and 0. 20 minutes |
| Invalid setting | `param_bad.txt` | `f_wf_current = 2` (must stop) |

## Checks (Check_wfdoppler.py)

From the water level and velocity written by the model, the checks independently solve the
dispersion relation (ω − kU)² = g k tanh(kh) for the bin direction θ = 0 on the branch that is
continuous as U → 0 (Newton's method, double precision), and compare with the steady solution
that conserves the wave action flux (c_g + U)E/σ.

- **Opposing current** (opp): the action flux is constant within 1e-5 (relative) over cells 1 to
  115 (the cells near the source column are excluded). The incident cell holds the offshore
  energy. Uniform alongshore.
- **Following current** (fol, fol72): the action flux is constant within 2e-4 (relative) over
  cells 3 to 117. On the following current the source column coincides with the incident column,
  and the velocity doubles within one cell (the u of a source cell is half, as a mean of its
  faces). The refraction by this strong gradient of the current (divergent) spreads about 3% of
  the unidirectional waves into the neighbouring bins (±Δθ) (in the first-order upwind scheme in
  direction space θ = 0 is an extremum, so the limited second-order correction does not act; it
  is the representation of waves spread uniformly over the width of a bin). The spread part is
  transported more slowly in x, and downstream the refraction by depth turns it back to θ = 0,
  so the total energy deviates from the one-dimensional theory in proportion to Δθ². fol72
  checks that this deviation decreases with the square of the bin width (the ratio is at least
  80% of (72/40)² = 3.24).
- **Unsteady** (unst): after 40 minutes the wave height agrees with the quasi-steady solution
  (param_opp) within 1e-6 (relative), and the cumulative ledger in action × ω closes within 1e-9 of
  the inflow in every row while the current spins up (the state is wave action, an adiabatic
  invariant in a time-varying current, so it does not increase or decrease outside the ledger when σ
  changes).
- **Blocking** (blk): the wave height drops at the cell where blocking (no root on the branch of
  the dispersion relation, or c_g + U ≤ 0) begins, and beyond it the wave height is at most 6% of
  H_m0. Over the stretch where breaking is negligible (cells 1 to 63), the action flux is conserved
  within 3e-3 (including the part that turns near the blocking point and returns to the incident
  cell; the increase of the energy in the incident cell ≤ 5e-3). Breaking of the waves steepened by
  the opposing current removes most of the energy (breaking > blocking), the action reaching the
  blocking point is recorded in the ledger as "blocked" (blocked_W), and the ledger (action × ω)
  closes.
- **With and without the current effect** (nocur, zero): without the current effect the waves
  reach beyond the blocking point. With zero flow the solution with `f_wf_current = 1` agrees with
  the path of stage W1 to the output precision.
- **River-mouth jet** (river): without the current effect the waves propagate up the channel
  (H ≥ 0.2 H_m0); with it they do not (H ≤ 0.02 H_m0; as blocking by the dispersion relation,
  without a cut-off like wave_vmax of fn_wave). The waves steepen and focus on the jet (higher
  than without the current effect), and blocking is recorded in the ledger.
- **Restart** (Run.sh): state.dat, swflow_enc.dat, wavefield.dat and the final fields of the split
  run are byte-identical to the straight run (including the accumulated blocking).
- **Invalid setting** (Run.sh): `f_wf_current = 2` stops with the reason.

## Running

```bash
make
./Run.sh          # serial + reference comparison + checks (about 9 minutes with one thread; about half is the slowly converging blocked base case and the restart)
./Run_MPI.sh 4    # MPI (np ≤ 4). ULP=0 against the reference; the river-mouth jet byte-identical to np = 1; restart also under MPI
```

## Verification record (2026-10-27; gfortran 13.3 / Open MPI 4.1.6, Ubuntu 24.04)

On the opposing current U = −0.375 → −0.674 m/s and σ/ω = 1.086 → 1.222; the largest relative
deviation from the conservation of the wave action flux is 2.8e-7 (cells 1 to 115), and the
energy in cell 115 is 1.351 times the shoaling value without the current effect. On the following
current U = 0.365 → 0.655 m/s and σ/ω = 0.932 → 0.859; the largest relative deviation is 1.05e-4
(cell 117), 3.2e-5 with 72 directional bins (ratio 3.28; (72/40)² = 3.24), and the energy is 0.846
times the value without the current effect. Blocking starts at cell 94 (x = 467.5 m), the wave height
also drops at cell 94, and beyond it the wave height is at most 0.0026 m. Upstream of breaking
(cells 1 to 63) the action flux is conserved within 2.3e-3, and the energy in the incident cell
increases by 2.3e-3. The ledger has an inflow of 30.11 W, an outflow of 1.94 W, breaking of
27.24 W and blocking of 0.93 W, with a residual of 6e-10 of the inflow. The unsteady run agrees with
the quasi-steady solution within 7.3e-8 after 40 minutes, and the cumulative ledger closes within
3.8e-15 of the inflow in all 40 rows. Without the current effect the wave height beyond the
blocking point (x = 553 m) is 0.0496 m (0.0021 m with it). With zero flow the wave height agrees
with the path of W1 to the output precision. For the river-mouth jet the wave height in the
channel (x = 20 to 80 m) is 0.0617 m without the current effect and 0.0000 m with it, the wave
height on the jet is 0.370 m (0.200 m without), and the blocking in the ledger is 119 W. The
restart continuation is byte-identical to the straight run. With `-Og -fcheck=all` the serial
run and np = 2 agree (no out-of-bounds access); with release builds np = 1, 2 and 4 are ULP=0
against the serial reference, the river-mouth jet is byte-identical to np = 1, and the restart
continuation also agrees under MPI.
