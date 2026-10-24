# test/berode — bank erosion (f_berode)

> English mirror of test/berode/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A check of bank erosion, which retreats a neighbouring cell higher than the
water surface (a bank face) under the shear stress of the toe cell
(developer.md §84.4; stage 2 of the extension toward meander development,
docs/meander_plan.md). The retreat rate is of the excess-shear-stress type,
E_b = K_b (τ*/τ*c,b − 1)^m, and the volume of the submerged bank height h_w
(the depth at the toe) × the width passed is moved conservatively from the
bank cell to the toe cell (the bedload carries it on afterwards). Terrain and
flow are the same as in [test/bankface](../../bankface/en/README.md)
(a straight channel 10 cells wide, dry banks of +2 m on both sides, dam-break
flow in a closed domain).

## Configuration

| Item | Value |
|---|---|
| Terrain and flow | Identical to test/bankface (`make_init.py` is shared) |
| Bank erosion | `f_berode = 1`, τ*c,b = 0.05, m = 1. `param_kb1.txt` K_b = 1e-5 m/s, `param_kb2.txt` K_b = 2e-5 m/s |
| Coupling with fixation | `param_fix0.txt`: kb1 + fixation (T_fix = 0.001 h, c_τ = 100) with `fix_ctau_bank = 0`; `param_fix1.txt`: the same settings with the default (c_τ,b = c_τ). developer.md §84.13 |
| Coupling with slump blocks | `param_slump.txt`: kb1 + the bank mode of rockfall and talus (`f_rockfall = 1`, `rf_bank = 1`, H_c = 1.5 m < bank 2 m, talus repose angle 35°) + shielding `berode_hcover = 0.1 m`; `param_slump0.txt`: the same settings without shielding. developer.md §84.17 |
| Bedload | Ashida–Michiue formula, d50 = 1 mm, soil layer 10 m (same as bankface) |
| Time | dt = 0.05 s, 60 s |

| File | Contents |
|---|---|
| `Check_berode.py` | (1) volume conservation \|Σ(z − z₀)\| < 1e-9; (2) all of the 2 bank rows adjacent to the channel (120 cells) have Δz < 0, and the non-adjacent banks are exactly 0; (3) the ratio of the bank loss volumes loss(2K_b)/loss(K_b) = 2 ± 2% (linearity of the erosion law); (4) the identity of the co-moving update; (5) the bank coefficient of fixation: z of fix0 agrees exactly with kb1, and the bank loss of fix1 is less than 5 % of kb1; (6) slump blocks: volume conservation and co-moving update of slump / slump0, talus ht ≥ 0 accumulating only in the channel rows (the toe); (7) shielding: the bank-erosion ledger of slump is less than 0.1 times that of slump0; (8) removal: the final total talus is smaller than the rockfall ledger (the part carried away by the bedload)|

## Running

```bash
make
./Run.sh          # input generation → K_b, 2K_b → Check (a few seconds)
./Run_MPI.sh 4    # MPI; the rule is that state.dat is byte-identical to the serial run
```

## Findings (2026-10-17)

| Check | K_b = 1e-5 | K_b = 2e-5 |
|---|---|---|
| Σ(z − z₀) | 4.6e-13 | −6.4e-13 |
| Bank loss volume | 0.206 m·cell | 0.412 m·cell (ratio 1.998) |
| Minimum Δz of the adjacent banks | −3.4 mm | −6.9 mm |

- While the toe shear stress is the same, the retreat is proportional to K_b
  (ratio 1.998; at twice K_b more sediment deposits at the toe, giving a slight
  nonlinearity).
- K_b has no default (a calibration value; no literature standard is set) and
  must be specified explicitly.
- MPI np = 2, 4 are byte-identical to the serial run; -fcheck=all np=2 runs
  normally.

## Findings (2026-10-23; slump blocks)

| Check | slump (h_cover = 0.1 m) | slump0 (no shielding) |
|---|---|---|
| Rockfall ledger (bulk) | 30.6 m³ | 30.4 m³ |
| Bank-erosion ledger | 0.002 m³ | 0.299 m³ (kb1 alone gives a bank loss of 0.367 m³·cell) |
| Final talus Σht | 18.8 m³ | — |

- Since the 2 m bank exceeds H_c = 1.5 m it collapses immediately, and talus of 0.25 m
  covers the toe (the rows at both edges of the channel). With shielding, at toes where
  the talus is ≥ h_cover the shear stress does not reach the bank face, and bank erosion
  is 0.007 times. The talus decreases by 12 m³ in 60 s through the outflow of bedload
  (removal).
- MPI np = 2, 4: state.dat and geomorph_rockfall.dat are byte-identical to the serial run.

## Related documents

- developer.md §84.4, docs/meander_plan.md §3.3
- [docs/users_guide/geomorph.md](../../../docs/en/users_guide/geomorph.md) — `f_berode`, `berode_kb`, `berode_tausc`, `berode_m`
