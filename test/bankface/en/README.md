# test/bankface — Bed-load blocking on bank faces and the supply limiter (conservation of the bed-load Exner equation)

> English mirror of test/bankface/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This case verifies the two behaviour changes made on 2026-10-17 to the
bed-load Exner equation (`f_fluvial`) (developer.md §84.1 and §84.2; stage 0
of the meander-development extension docs/meander_plan.md; both in Japanese).

1. **Bed-load blocking on bank faces** (§84.2): bed load rolls on the bed
   surface, so (R1) a dry cell supplies nothing, and (R2) nothing is carried
   onto ground higher than the water surface of the supplying cell. Before the
   change, the edge hydraulic quantities were averages of both cells, so the
   ground of dry bank cells 2 m above the water surface fluctuated by a few mm
   to a few cm (sediment "climbed" onto land).
2. **Conservative supply limiter** (§84.1): in a cell where the simultaneous
   outflow through several edges exceeds the soil thickness sd, the sediment
   fluxes of all edges for which that cell is upwind are scaled down by the
   same ratio. Before the change there was only a per-edge clamp, and the
   excess was clipped at the bedrock so that sediment volume vanished
   (0.57 m³ in the thin soil layer of this case).

## Configuration

| Item | Value |
|---|---|
| Domain and grid | 60 m × 20 m, 60 × 20 cells (Δx = 1 m), walls on all four sides (closed domain) |
| Terrain | Rows 6–15 are the channel (bed slope 0.002, higher to the west); on both sides are dry banks at bed +2 m. `make_init.py z` |
| Initial depth | Channel only: dam-break type with 1.0 m in the upstream half (i ≤ 30) and 0.2 m in the downstream half. Banks are 0. `make_init.py h` |
| Soil layer | `param.txt` sd₀ = 10 m (the limiter never acts) / `param_thin.txt` sd₀ = 0.5 mm (the limiter acts) |
| Sediment transport | Ashida–Michiue formula, d50 = 1 mm, τ*c = 0.05, porosity 0.4, change cap 0.05 m |
| Time | dt = 0.05 s, 60 s (update every step). `save*/state.dat` at the end |

| File | Contents |
|---|---|
| `Check_bankface.py <save> <sd0>` | (1) volume conservation \|Σ(z − z₀)\| < 1e-9, (2) max\|z − z₀\| of the dry bank cells is exactly 0, (3) co-moving update max\|(sd − sd₀) − (z − z₀)\| < 1e-10, (4) activity in the channel > 1e-4 m, (5) min sd ≥ 0 |

## Running

```bash
make
./Run.sh          # generate inputs → param.txt / param_thin.txt → Check (a few seconds)
./Run_MPI.sh 4    # MPI. The rule is that state.dat is byte-identical to the serial run
```

## Findings (2026-10-24; gfortran 13.3, -Ofast)

| Check | sd₀ = 10 m | sd₀ = 0.5 mm |
|---|---|---|
| (1) Σ(z − z₀) | −5.3e-13 | −3.3e-13 (the supply limiter acted in 332,120 cell updates) |
| (2) max\|z − z₀\| of the dry banks | 0 | 0 |
| (3) co-moving update | 1.8e-15 | 5.2e-14 |
| (4) max\|z − z₀\| in the channel | 11.5 mm | 6.1 mm |
| (5) min sd | 9.99 m | 0 (bedrock exposed; the floor is not broken through) |

With the code before the change, (2) is 0.39 mm / 0.50 mm and (1) for the
thin soil layer is 0.95 m·cell (0.57 m³ lost), so both FAIL.

## Related documents

- developer.md §84 (record of the staged plan for meandering, bank erosion
  and bed-load direction correction; in Japanese), docs/meander_plan.md
  (master design document; in Japanese)
- [docs/users_guide/sediment.md](../../../docs/en/users_guide/sediment.md) §3 (order of the clamps)
