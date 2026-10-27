# test/rockinc — verification of bedrock incision by flowing water (f_rockinc)

> English mirror of test/rockinc/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The verification case for bedrock incision by flowing water in the
landform-change module (`f_rockinc = 1` in `&list_geomorph`;
[the landform-change chapter of the user's guide](../../../docs/en/users_guide/geomorph.md#bedrock-incision-by-flowing-water-f_rockinc))
(developer.md §88, T2 to T7 and T9 of docs/mountain_stream_plan.md §4.9).
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
| T5 restart round trip | `param_pluck_rt1.txt` → `param_pluck_rt2.txt` | pluck saved at 150 s from bare rock and continued to 300 s | state.dat and geomorph_rockinc.dat are byte-identical to the straight run |
| T9 steep uniform flow (record) | `param_steep_s001.txt` … `param_steep_s020.txt`, `param_steep_s020_od0.txt` | Uniform flow at slopes 0.01 to 0.2 in a 5-cell channel (no landform change). od0 is without the dynamic reassignment | Tabulates the ratio of the cell τ_b = ρ g n² V²/h^{1/3} to the uniform-flow balance (no pass/fail) |

| File | Content |
|---|---|
| `make_init.py` | Generates the terrain, initial depth, bare-rock file, steep channels and erodibility multiplier (constants are kept in step with `param*.txt` and `Check_rockinc.py`) |
| `Check_rockinc.py cover / pluck / box LOG / steep` | The criteria above. The hydraulics are read from bil (single precision), H = sd, z and Ri from the saves (double precision) |
| `Run.sh` / `Run_MPI.sh N` | Runs and checks all configurations. MPI compares bytes with the serial saves (`save_*_serial`) |

## Running

```bash
make
python3 make_init.py z > zinit.txt   # regenerate the inputs (bundled; only when changed)
./Run.sh            # serial (about 30 s)
./Run_MPI.sh 4      # MPI (after Run.sh; byte comparison with save_*_serial)
```

## Verification record (2026-10-27; gfortran 13.3 / Open MPI 4.1, the default -Ofast build)

- T2: in 60 cells (H = 0.069 to 0.097 m) the maximum relative error from the
  analytic solution is 9.2e-8 (rounding of the single-precision hydraulic
  output). cover_dtg and cover_mf agree with cover to 3.9e-12 (the difference is
  the slow adjustment that the hydraulics continue in double precision; B/H*
  per update is 0.7 to 1.1, so an explicit scheme would differ by orders of
  magnitude).
- T3: cover fraction at the outlet 0.147, maximum relative difference from the
  recursion 3.7e-4. Comparing with the stored thickness instead of the thickness
  just after plucking is off by the plucking of one update (B_p/H* ≈ 1e-3).
- T7: the cumulative incision of pluck_mf5 and mf20 agrees with pluck to
  relative 6.8e-4 and 1.35e-3 (the difference is proportional to dts = first
  order).
- Hump of T3: at r = 0.2, 0.5 and 0.8 the incision rate agrees with the theory
  to 6.0e-5, 4.5e-6 and 6.5e-4, and the cover fraction to 7.9e-5, 1.9e-4 and
  2.3e-4. For r = 1.2 the bed is fully covered at 0.013 of the top of the hump
  (the cover keeps thickening). The capacity of the edge leaving the inflow
  cell (low velocity) is 0.72 of the interior on the uniform slope, so for
  r > 0.7 a mound forms at the inlet and grows until the capacity rises (0.88
  of the interior at r = 0.8).
- T4: Σ(z − z0) A = −0.236164 m³ (abraded volume), Σ(sd − sd0) A = 0.693794 m³
  (plucked volume) and Σ Ri A = their sum agree with the ledger within 2e-9;
  Ri = 0 in the rows with multiplier 0.
- T5: the run saved at 150 s from bare rock and continued is byte-identical to
  the straight run.
- MPI: np = 2 with -fcheck=all (the same debug flags as nightly) was run first:
  no bounds violation, and all configurations are byte-identical to the debug
  serial run. np = 1, 2, 4 with -Ofast are also byte-identical to serial.
- T9 (record): τ_b / ρ g h tanθ in the middle of the channel is 1.014, 1.070,
  1.141 and 1.291 at slopes 0.01, 0.05, 0.1 and 0.2, and 1.006, 1.029, 1.060
  and 1.124 in the column at the wall; V / V_Manning(h) in the middle is 1.007
  to 1.136. Without the dynamic reassignment (od0, slope 0.2) the middle gives
  1.025 (but the ratio in the column at the wall drops to 0.66 = loss of
  conveyance). The deviation depends only on the slope (grid spacing × slope /
  depth), not on the roughness or the Froude number, because the blocking
  fraction counts the upslope ground of a uniform slope as a partial wall
  (developer.md §88.4).

## Findings

- In a 5-cell channel, the conveyance of the columns at the walls differs from
  the interior, so the incision rate differs between columns; a cross-channel
  difference of the bed grows, and a positive feedback concentrating the flow
  in the interior prevented a quasi-steady state. With a 1-cell channel the
  problem becomes a 1-D chain with u = 0 and closes with the recursion
  (developer.md §88.4).
- When the bedload pass width is set to `fluv_diagratio = 0`, the table of the
  dynamic reassignment of water is applied to the axial edges and the capacity
  of a 1-cell channel becomes 2.41 times larger (consistent with the default
  fluv_diagratio).
