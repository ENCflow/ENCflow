# test/dissol — analytical verification of limestone dissolution (f_dissol) and restart round trip

> English mirror of test/dissol/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The verification case for limestone dissolution in the landform-change module
(`f_dissol = 1` in `&list_geomorph`;
[the landform-change chapter of the user's guide](../../../docs/en/users_guide/geomorph.md#limestone-dissolution-f_dissol))
(developer.md §86, docs/karst_plan.md §3). Dissolution is a local, linear
update that lowers z by exactly "the amount of water entering the rock × k_d
(= c_eq/ρ_r) × morfac", so the ground elevation at the end is checked in 3
configurations in which the water amount is determined analytically.

| Configuration | File | Source of the water | Analytical value |
|---|---|---|---|
| A diffuse dissolution | `param.txt` | Bucket infiltration 36 mm/h (= 1e-5 m/s) for 100 s → I = 1e-3 m. dt_geomorph = 5 s (accumulation over 100 steps), morfac = 1e4, residue fraction 0.25 | w = 4e-5 × 1e-3 × 1e4 = 4e-4 m → Δz = −3e-4 m, Δsd = +1e-4 m |
| B concentrated dissolution (doline term) | `param_sink.txt` | Schematic experiment A of [test/conduit](../../conduit/en/README.md) (ponded water drops into a conduit layer of uniform inlet density and reaches equilibrium) with the sink term superposed, soluble only in the central 5×5 (`data_dissol/sol.txt`). dt_geomorph = tt (once at the final step), f_sink = 0.5 | Δz(center) = −4e-5 × 0.5 × hgc(150 s) × 1e4 = −0.2 × Hgc0003, Δz(outside) = 0 |
| C rainfall source | `param_rain.txt` | No groundwater; uniform rainfall 30 mm/h for 3600 s (dissol_src = 2). morfac = 1000 | Δz = −4e-5 × 0.03 × 1000 = −1.2e-3 m |
| D lateral dissolution | `param_lat.txt` | Ponded water at level −0.5 m (f_htype = 2) in a −1 m pit occupying only the central 3×3 of a flat 0 m domain (`data_dissol/zpit.txt`). Bucket infiltration gives the 9 pit cells a dissolution capacity W = 4e-4 m, dissol_lat = 0.4 | Floor (1−p)W, walls of the surrounding 16 cells pW·L_k/ΣL (axial 1, diagonal 2/(2+√2); karst_plan §2.5). Total 9W |
| F surface-flow source | `param_surf.txt` | Uniform rainfall 30 mm/h for 1 hour on bare rock (sd0 = 1e-3 m), bucket infiltration 10 mm/h, dissol_src = 3 (fsurf = 0.3, sdsurf = 0.1). morfac = 1000 | Δz = −k_d (I + fsurf·fb·(P − I)) morfac = −4e-5 × 0.01594 × 1000 = −6.376e-4 m (all cells). The rt1 → rt2 round trip is also checked |
| G safety valve | `param_clip.txt` | The same infiltration as A (dissolution 2e-5 m per update) with dissol_dzmax = 1e-5 | Δz = −20 × 1e-5 = −2e-4 m (all cells; the excess capacity is discarded) |
| E automatic distribution | `param_lata.txt` | The same pit as D, with a tiny uniform rainfall of 0.36 mm/h as the rainfall source giving W = 4e-4 m to every cell, dissol_lat = −1 (wetted-area ratio) | p = hΣL/(hΣL + Δx²) for each pit cell (h = 0.5 m, Δx = 2 m). Dry cells put W on the floor. Total 441W (relative 1e-4) |
| Restart round trip | `param_rt1.txt` → `param_rt2.txt` | A is saved at 52 s (part way through the 5 s update interval) and continued to 100 s | state.dat, geomorph_dissol.dat and Z9998.bil are byte-identical to the straight-through run (`save_all`, `result`) |

k_d = c_eq/ρ_r = (100 mg/L)/(2500 kg/m³) = 4e-5 m/m is written in both
`param*.txt` and `Check_analytic.py`. Change both at the same time. Because
the bil output (float32) is read, `f_output_mode = 3` is required.

| File | Contents |
|---|---|
| `param.txt` / `param_sink.txt` / `param_rain.txt` / `param_lat.txt` / `param_lata.txt` / `param_surf.txt` / `param_clip.txt` | Configurations A / B / C / D / E / F / G |
| `param_rt1.txt` / `param_rt2.txt` | Restart split of A (first half 0→52 s, second half 52→100 s) |
| `param_surf_rt1.txt` / `param_surf_rt2.txt` | Restart split of F (saved at 1830 s = part way through the update interval; a check of the private save of the rainfall accumulation frn) |
| `data_dissol/sol.txt` | Soluble-fraction map of B (central 5×5 = 1, 0 elsewhere) |
| `data_dissol/zpit.txt` | Terrain of D (central 3×3 = −1 m, 0 elsewhere) |
| `Check_analytic.py` | Reads the bil of Z9998 (and Sd9998, Hgc0003) and compares with the analytical values (relative error 1e-6; 1e-3 for the total of D because of float32 rounding) |
| `Run.sh` / `Run_MPI.sh N` | Runs all configurations + analytical checks + round-trip checks (+ reference comparison of the Log.txt of A) |

## Running

```bash
make
./Run.sh            # serial: runs A–G and the round trip with the analytical and round-trip checks. The Log.txt of A is compared with the reference (ULP = 1)
./Run_MPI.sh 4      # MPI: runs A–G with the analytical checks. Log.txt is ULP = 0 against the serial reference.
                    # If the serial result* are copied to result*_serial beforehand, the bil files are also compared byte by byte
```

## Verification record (2026-10-21; gfortran 13.3 / Open MPI, -O2)

- Analytical checks: in A, B and C every cell of the bil agrees with the
  analytical value (maximum relative error 1e-8 or less = float32 rounding).
  In D (2026-10-22) every floor and wall cell agrees with the distribution
  formula, and the total dissolution capacity 9W is conserved (within float32
  rounding); at np = 4 the pit straddles bands. E (automatic distribution)
  agrees likewise (relative error of p within 1e-4 = the change of h due to
  the rainfall). F (surface-flow source) agrees in every cell with the
  analytical value, and the round trip saved part way through the update
  interval is byte-identical (private save of the rainfall accumulation).
- Restart round trip: a save part way through the update interval (52 s) →
  continuation is byte-identical to the straight-through run in state.dat,
  geomorph_dissol.dat and Z9998.bil (verification of the private file of the
  accumulation field).
- MPI: np = 1, 2, 4 give ULP = 0 against the serial run in Log.txt, and all
  bil files are byte-identical. No bounds violation at np = 2 with
  -Og -fcheck=all.
- When disabled (no f_dissol): wave, conduit, chichibu, creep and splash are
  bit-identical to the existing references.
