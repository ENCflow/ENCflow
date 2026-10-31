# test/rockinc — verification of bedrock incision by flowing water (f_rockinc)

> English mirror of test/rockinc/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The verification case for bedrock incision by flowing water in the
landform-change module (`f_rockinc = 1` in `&list_geomorph`;
[the landform-change chapter of the user's guide](../../../docs/en/users_guide/geomorph.md#bedrock-incision-by-flowing-water-f_rockinc))
(developer.md §89, T2 to T7 and T9 of docs/mountain_stream_plan.md §4.9, and C1 = T11 of §11.3).
Plucking by the flow and abrasion by the transported gravel lower the bedrock
surface z − sd; the plucked rock is added 1:1 to the mobile layer sd, and the
abraded fines leave the system. The mobile layer suppresses the incision
by the exposure exp(−sd/H*) (cover), and the outflow of bedload is multiplied
by the availability 1 − exp(−sd/H*). There is no reference; the case is judged
by analytic solutions, conservation and byte identity.

The channel is 1 cell wide (dry ground +2 m on both banks), 60 m long and runs
north to south (the flow crosses the MPI band interfaces in the j direction),
with slope 0.01, n = 0.04 and normal depth 0.3 m (V = 1.12 m/s). Inflow
Q = 0.336 m³/s enters through a section at the north end, and the south edge
is a free outflow. In a 1-cell channel all diagonal openings are blocked by the
banks, and with the dynamic reassignment (`f_opening_dynamic = 2`, the
default) both water and bedload flow along the axis with the full width.

| Configuration | File | Content | Criterion |
|---|---|---|---|
| T2 self-cover | `param_cover.txt` | Plucking only on bare rock (a zero soil-thickness file `sdzero.txt`) with immobile gravel (d50 = 5 cm, τ* = 0.036) (k_p = 6e-5 m/s, τ_c = 10 Pa, m = 1.5, H* = 5 cm). The first geomorphic update comes after the flow has become steady (dt_geomorph = 300 s; 6 updates in 1800 s) | e^{H/H*} = 1 + E_p0 t/H* in every cell (E_p0 from h and V at the final time; relative 1e-5) |
| T2/T7 update interval and acceleration | `param_cover_dtg.txt` / `param_cover_mf.txt` | dt_geomorph = 600 s (3 updates) / morfac = 2 (flow time 900 s) | Agrees with cover to relative 1e-9 (exact integration of the exposure) |
| T3 quasi-steady cover | `param_pluck.txt` | Plucking only from bare rock without sediment feed, with mobile gravel (d50 = 1 cm, τ* ≈ 0.18) (k_p = 3e-6 m/s, H* = 1 cm), morfac = 10 | With the edge capacity q_c and E_p0 from the hydraulics at the final time, solve q_j = (q_{j−1} + a_j)/(1 + a_j/q_c) (a = (1 − λ)Δy E_p0) from the north end (q_0 = 0) and compare with F_s(H*_j) = q_j/q_c (relative 5e-3). H*_j = H_j + B_p is the thickness just after plucking that the bedload sees |
| T4 conservation in a closed box | `param_box.txt` | The box of test/fluvial (101 × 101, radial flow from wave_hump) with sd0 = 5 mm, plucking and abrasion (β = 0.05 1/m), and the erodibility multiplier `rockmap_box.txt` (0 in rows 45 to 55, which contain the band interface j = 51; 0.5 in the western half) | Σ(z − z0) A = −abraded volume, Σ(sd − sd0) A = plucked volume, Σ Ri A = plucked + abraded volume (relative 1e-7 against the ledger), Ri = 0 in the rows with multiplier 0 |
| T3 hump of abrasion | `param_hump_r02.txt` … `param_hump_r12.txt` | Abrasion only without plucking (β = 0.005 1/m, H* = 1 cm). A constant sediment feed q_in = r q_c at the inflow cell at the north end (r = 0.2, 0.5, 0.8, 1.2) | In the interior cells (j = 21 to 50), the incision rate from the increment of Ri over the last 1000 s (geomorphic time) is β q_in (1 − q_in/q_c) and the cover fraction is q_in/q_c (relative 5e-3). For r = 1.2 the bed is fully covered and the incision rate is below 0.05 of the top of the hump |
| T7 acceleration (with bedload) | `param_pluck_mf5.txt` / `param_pluck_mf20.txt` | pluck with morfac = 5 (flow time 600 s) / 20 (150 s); the same geomorphic time 3000 s | The cumulative incision z − z0 agrees with pluck to relative 2e-3 / 4e-3 (O(dts)) |
| Restore of a bare-rock save | `param_cover_rt1.txt` → `param_cover_rt2.txt` (control `param_cover_rt2_off.txt`) | cover saved before the first geomorphic update (t = 200 s; the soil thickness is zero everywhere) and continued to 1800 s. The control restores the same save without f_rockinc | The save with zero soil thickness everywhere is accepted (the message is checked), and state.dat and geomorph_rockinc.dat are byte-identical to the straight run. The control stops as before |
| T8 steady longitudinal profile under uplift | `param_uplift.txt` | Uniform uplift U = 1e-5 m/s; only the outlet cell is neither uplifted nor eroded (`upmap.txt`, `rockmap_up.txt` = 0 = fixed base level). Plucking only from bare rock (k_p = 6e-6 m/s, H* = 5 cm), morfac = 50 (geomorphic time 7.5e4 s) | For j = 15 to 58: steadiness max\|dz/dt\| < 0.02 U, local balance B_p/(U dts) = 1 ± 0.02, the slope within 5 % of the quasi-analytic solution with uniform-flow hydraulics (E_p0(S)(1 − q_j/q_c(S)) = U, q_j = (1 − λ) U Δy j), and its downstream steepening within 2 % |
| T11 steady longitudinal profile under head supply (C1) | `param_t11_r02.txt`, `r05`, `r08`, `r05a` | T8 plus a constant supply q_in = r q_c0 at the inflow cell in the north (`inflow_qb`; r = 0.2, 0.5, 0.8; q_c0 = 1.81e-3 m²/s is an estimate of the uniform-flow capacity at slope 0.01). r05a also has abrasion (β = 0.005 1/m). Geomorphic time 1.5e5 s | For j = 15 to 58: steadiness max\|dz/dt\| < 0.02 U, the slope within 5 % of the quasi-analytic solution with uniform-flow hydraulics ((E_p0(S) + β q_j)(1 − q_j/q_c(S)) = U, q_j = q_{j−1} + (1 − λ)Δy E_p0(S)(1 − q_j/q_c(S)), q_0 = q_in), and the sediment budget Σ(z − z0)A = uplift − abrasion + (supply − open-boundary outflow)/(1 − λ) to relative 1e-8 (the outflow is the ledger of developer.md §89.12) |
| T5 restart round trip | `param_pluck_rt1.txt` → `param_pluck_rt2.txt` | pluck saved at 150 s from bare rock and continued to 300 s | state.dat and geomorph_rockinc.dat are byte-identical to the straight run |
| T9 steep uniform flow | `param_steep_s001.txt` … `param_steep_s020.txt`, `param_steep_s020_od0.txt`, `param_steep_s001_od3.txt` … `param_steep_s020_od3.txt` | Uniform flow at slopes 0.01 to 0.2 in a 5-cell channel (no landform change). od0 is without the dynamic reassignment, od3 uses f_opening_dynamic = 3 (blockage measured above the local plane; developer.md §68.41, in Japanese) | Ratio of the cell τ_b = ρ g n² V²/h^{1/3} to the uniform-flow balance. The default 2 and od0 are recorded; od3 must be 1 ± 0.5 % in both the middle of the channel and the column at the wall |
| T10 orientation of sheet flow (record) | `param_sheet_d00.txt`, `param_sheet_d45.txt` and `_od3` | Sheet flow from uniform rain of 100 mm/h on a plane of slope 0.05 (`z_sheet_d00.txt`, `z_sheet_d45.txt`): 0° (60 × 12, flow along the grid axis) and 45° (60 × 60, along the diagonal), f_opening_dynamic = 2 and 3 | Tabulates τ_b at flow lengths L = 10 to 50 m against uniform sheet flow (q = r L) and the local balance ρ g h S (no pass/fail) |

| File | Content |
|---|---|
| `make_init.py` | Generates the terrain, initial depth, bare-rock file, steep channels, sheet-flow planes and erodibility multiplier (constants are kept in step with `param*.txt` and `Check_rockinc.py`) |
| `Check_rockinc.py cover / pluck / hump / uplift / box LOG / t11 / steep / sheet` | The criteria above. The hydraulics are read from bil (single precision), H = sd, z and Ri from the saves (double precision) |
| `Run.sh` / `Run_MPI.sh N` | Runs and checks all configurations. MPI compares bytes with the serial saves (`save_*_serial`) and with the outputs of steep_s020_od3 and sheet_d45_od3 with f_opening_dynamic = 3 (`result_*_serial`) |

## Running

```bash
make
python3 make_init.py z > zinit.txt   # regenerate the inputs (bundled; only when changed)
./Run.sh            # serial (about 50 s)
./Run_MPI.sh 4      # MPI (after Run.sh; byte comparison with save_*_serial)
```

## Verification record (2026-10-27; rerun on 2026-10-28 after the change of the depth floor of the inflow face; gfortran 13.3 / Open MPI 4.1, the default -Ofast build)

- T2: in 60 cells (H = 0.0961 m, uniform) the maximum relative error from the
  analytic solution is 1.9e-8 (rounding of the single-precision hydraulic
  output). cover_dtg and cover_mf agree with cover to 2.0e-14 (the difference is
  the slow adjustment that the hydraulics continue in double precision; B/H*
  per update is 0.7 to 1.1, so an explicit scheme would differ by orders of
  magnitude).
- T3: cover fraction at the outlet 0.147, maximum relative difference from the
  recursion 4.0e-4. Comparing with the stored thickness instead of the thickness
  just after plucking is off by the plucking of one update (B_p/H* ≈ 1e-3).
- T7: the cumulative incision of pluck_mf5 and mf20 agrees with pluck to
  relative 5.6e-4 and 1.10e-3 (the difference is proportional to dts = first
  order).
- Hump of T3: at r = 0.2, 0.5 and 0.8 the incision rate agrees with the theory
  to 4.5e-6, 9.7e-7 and 1.3e-4, and the cover fraction to 5.4e-6, 2.3e-5 and
  4.6e-5. For r = 1.2 the bed is fully covered at 0.013 of the top of the hump
  (the cover keeps thickening). The cover at r = 0.8 is 1.41 cm in the inflow
  cell and uniform at 1.57 cm from the second cell.
- T8: slope 0.00768 to 0.00861 (quasi-analytic 0.00785 to 0.00879), maximum
  relative difference 2.2 % (halving the time step changes the slope by only
  1e-4; it appears to be the approximation of the gradually varied flow of the
  profile by uniform flow), difference of the steepening 0.16 %, steadiness
  4.4e-3 U, local balance 2.4e-3. The profile is smooth from the inflow cell
  (second differences 0.2 mm or less).
- T11: the slope (j = 15 to 58) is 0.00902 to 0.00990 for r = 0.2 (quasi-analytic
  0.00915 to 0.01003), 0.01088 to 0.01169 for r = 0.5 (0.01097 to 0.01179),
  0.01261 to 0.01338 for r = 0.8 (0.01267 to 0.01345) and 0.00998 to 0.01055 for
  r = 0.5 with abrasion (0.01005 to 0.01063). The maximum relative differences
  are 1.5 %, 0.82 %, 0.53 % and 0.77 %. More supply steepens the slope through
  the cover (T8 with r = 0 has 0.00768 to 0.00861), and adding abrasion makes the
  supply act as tools, so the slope is gentler for the same supply. Steadiness
  3.2e-5 U or less; the sediment budget closes within relative 4e-10 (the digits
  printed in the ledgers).
- Before the change of the depth floor of the inflow face (2026-10-28;
  developer.md §89.25, in Japanese), the inflow cell flowed slowly (face
  velocity 0.74 times at slope 0.01, Fr 0.65): the cover of T2 varied between
  0.069 and 0.097 m, for r > 0.7 in the hump of T3 a mound formed at the inlet
  (the capacity of the edge leaving the inflow cell was 0.72 of the interior),
  and just below the inflow cell of T8 a 2-cell step pattern formed that decayed
  by about −0.7 per cell (second differences +237, −176, +98 mm, …).
- T4: Σ(z − z0) A = −0.236164 m³ (abraded volume), Σ(sd − sd0) A = 0.693794 m³
  (plucked volume) and Σ Ri A = their sum agree with the ledger within 2e-9;
  Ri = 0 in the rows with multiplier 0.
- T5: the run saved at 150 s from bare rock and continued is byte-identical to
  the straight run. The continuation from the save with zero soil thickness
  everywhere (cover_rt1) is also byte-identical to the straight run, and the
  control without f_rockinc stops.
- MPI: np = 2 with -fcheck=all (the same debug flags as nightly) was run first:
  no bounds violation (on 2026-10-27 all configurations were also byte-identical
  to the debug serial run). np = 1, 2, 4 with -Ofast are also byte-identical to
  serial (also in the rerun of 2026-10-28, and with -O2).
- T9 (record): τ_b / ρ g h tanθ in the middle of the channel is 1.014, 1.070,
  1.141 and 1.291 at slopes 0.01, 0.05, 0.1 and 0.2, and 1.006, 1.029, 1.060
  and 1.124 in the column at the wall; V / V_Manning(h) in the middle is 1.007
  to 1.136. Without the dynamic reassignment (od0, slope 0.2) the middle gives
  1.025 (but the ratio in the column at the wall drops to 0.66 = loss of
  conveyance). The deviation depends only on the slope (grid spacing × slope /
  depth), not on the roughness or the Froude number, because the blocking
  fraction counts the upslope ground of a uniform slope as a partial wall
  (developer.md §89.4).
- T9 with f_opening_dynamic = 3 (added on 2026-10-29; developer.md §68.41): the
  middle of the channel gives 1.0000 to 1.0001, the column at the wall 0.9999,
  and V / V_Manning(h) in the middle 1.0000 (slopes 0.01 to 0.2; the depth is
  the uniform-flow depth 0.300 m), all passing.
- T10 (record): τ_b / τ of uniform sheet flow (q = r L) and τ_b / ρ g h S at
  L = 10 to 50 m are 1.25 to 1.27 and 1.34 to 1.38 at 0° with 2, 0.99 to 1.00
  and 0.96 to 0.99 with 3; at 45° they are 1.13 to 1.18 and 1.29 to 1.34 with 2,
  0.91 to 0.95 and 0.95 to 0.99 with 3. With 3 both orientations are close to
  the local balance. That τ_b / τ of uniform flow is below 1 at 45° comes from
  an orientation property: the unit discharge from H and V is 0.91 to 0.93
  times r L (the same with 2; not investigated).

## Findings

- In a 5-cell channel, the conveyance of the columns at the walls differs from
  the interior, so the incision rate differs between columns; a cross-channel
  difference of the bed grows, and a positive feedback concentrating the flow
  in the interior prevented a quasi-steady state. With a 1-cell channel the
  problem becomes a 1-D chain with u = 0 and closes with the recursion
  (developer.md §89.4).
- When the bedload pass width is set to `fluv_diagratio = 0`, the table of the
  dynamic reassignment of water is applied to the axial edges and the capacity
  of a 1-cell channel becomes 2.41 times larger (consistent with the default
  fluv_diagratio).
