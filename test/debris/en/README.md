# test/debris — connectivity and conservation laws of debris flow (erosion-deposition E-D): four constitutive laws

> English mirror of test/debris/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This is a check of the connectivity and conservation laws of the single-layer
mixture debris-flow model (`f_debris = 1`: the surface water h and the sediment
column hs are represented as a single layer, and the erosion-deposition E-D
with the bed and the resistance law are switchable; docs/debris_plan.md,
developer.md §28). A rainfall of 200 mm/h is applied to the slope_break terrain
(a slope of tanθ = 0.4 → the slope break at x = 30 m → flat), and the process
in which sediment eroded on the slope is carried below the slope break is run
with four combinations of constitutive laws. It is not a quantitative
benchmark; **conservation of the total solids, the identity of the co-moving
update, and activity (erosion occurs and sediment arrives)** are checked by
`Check_debris.py` (§28.3, §28.5–7).

## Configuration

Common: 60 m × 20 m (Δx = 1 m), movable layer sd₀ = 5 m, porosity λ = 0.4
(C* = 0.6), rainfall 200 mm/h, dt = 0.02 s, walls on all four sides (closed
domain = the ledger closes).

| Configuration | File | E-D formula `f_dbed` | Resistance law `f_dbres` | Time | Check mode |
|---|---|---|---|---|---|
| 1 | `param.txt` | 1: relaxation to the Takahashi-type equilibrium concentration C∞(θ) (δe = 0.0007, δd = 0.05) | 1: Coulomb + Manning combined (φ = 35°) | 30 s | default |
| 2 | `param_eg.txt` | 2: Egashira and Ashida (1992) | 2: Egashira constitutive law (d50 = 0.05 m, restitution coefficient 0.85) | 30 s | eg |
| 3 | `param_tk.txt` | 3: Takahashi and Nakagawa (1991) eqs. (12)(27) | 3: stony type, eqs. (22)–(25) | 60 s | eg |
| 4 | `param_tkwet.txt` | 3 + pore-water entrainment `f_dbwet = 1` (bed saturation s_b) | 3 | 60 s | wet |

Checks: (1) conservation of the total solids |Σhs + (1 − λ)Σ(z − z₀)| < 1e-9
(a consequence of the antisymmetric exchange of E-D), (2) identity of the
co-moving update max|(sd − sd₀) − (z − z₀)| < 1e-10 (z and the soil depth sd
move by the same amount), (3) activity: slope erosion min dz < −1e-3 m and
arrival of sediment on the flat (configuration 1: deposition below the slope
break, max dz; eg mode: max hs), (4) wet mode only, the water ledger
|Σh − total rainfall + λ s_b Σdz| < 1e-9 (the surface water increases by the
entrained pore water).

| File | Contents |
|---|---|
| `Check_debris.py <save> [eg\|wet]` | The checks above (reads `save*/state.dat`) |
| `Fig.py` | The figures `figs/*.png` below |

## Running

```bash
make
./Run.sh          # run the 4 configurations in turn, each followed by Check. PASS when all pass (a few seconds)
./Run_MPI.sh 4    # MPI. state.dat is byte-identical to the serial run (with the -O2 strict-math build)
python3 Fig.py    # figs/profile.png, figs/map.png
```

## Figures

![Longitudinal profiles of the 4 configurations](../figs/profile.png)

Top: terrain. Middle: terrain change dz (average over all rows, cm). In every
configuration the whole slope is thinly eroded (0.2–0.4 cm in configurations
1–3, 1.6 cm in configuration 4), erosion intensifies just before the slope
break, and in configuration 1 deposition (+0.2 cm) appears directly below the
slope break. Bottom: sediment in motion hs (cm). It is carried at a constant
concentration on the slope and drops sharply on the flat beyond the slope break
(in a dilute sheet flow θ_e ≈ 0, so deposition on the flat is slow, and in a
short check the arrival of hs is taken as the evidence of activity). The
pore-water entrainment of configuration 4 adds the pore water of the eroded bed
to the flow, so the surface water increases (Σh 4.0 → 7.5 m·cell), and a
positive feedback in which the velocity and erosion increase further is seen
(erosion −0.44 → −2.2 cm).

![Distributions of configuration 1](../figs/map.png)

The terrain change (left) and the flow depth (right) of configuration 1.
Transversely uniform erosion, a deposition zone of 1–2 cells directly below the
slope break, and a thin water film on the flat are seen.

## Findings

| Configuration | Total solids Σhs + (1 − λ)Σdz | Co-moving update | Activity (min dz / arrival) | Water ledger |
|---|---|---|---|---|
| 1 | −1.8e-13 | 7e-14 | −0.32 cm / deposition below the slope break +0.18 cm | — |
| 2 Egashira | 7e-13 | 9e-14 | −0.25 cm / max hs 0.15 cm | — |
| 3 Takahashi–Nakagawa | 2.2e-13 | 7e-14 | −0.44 cm / max hs 0.09 cm | — |
| 4 + pore-water entrainment | 2.2e-13 | 9e-14 | −2.2 cm / max hs 1.1 cm | 1.1e-13 |

- The total solids and the co-moving update hold at machine precision in all
  4 configurations. The E-D exchange amounts are obtained from the field at
  time n in two passes and then applied (the lesson of the real OpenMP race
  bug of §28.2), and the state.dat of np = 1, 2, 4 is byte-identical to the
  serial run (with the -O2 strict-math build; with -Ofast there are ULP
  differences between builds; §28.5).
- This case is a check of **connectivity and conservation laws**. The
  quantitative validity of the constitutive laws is recorded in debris_plan.md
  as remaining work on literature comparison (coefficients for the immature
  debris-flow regime, the deposition formula for the bedload-like regime,
  etc.).
- Instantaneous mobilization (f_release) and the slope-stability judgement
  (f_slide) are checked in [test/slide](../../slide/en/README.md), and the
  equivalent-fluid mode (no exchange) in [test/volcano](../../volcano/en/README.md).

## Related documents

- [docs/users_guide/geomorph.md](../../../docs/en/users_guide/geomorph.md) — debris-flow settings (`f_dbed`, `f_dbres`, `f_dbwet`, stopping `f_dbstop`)
- [docs/debris_plan.md](../../../docs/debris_plan.md) (in Japanese) — the full design and the remaining literature comparison
- developer.md §28.1–28.7 (configuration, real bugs, verification records, the Egashira and Takahashi–Nakagawa laws, pore-water entrainment)
