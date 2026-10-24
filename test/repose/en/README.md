# test/repose — Angle-of-repose avalanching (f_repose)

> English mirror of test/repose/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This case verifies that a dry 45° sand cone (summit 3 m, closed domain, no
water) collapses to the 30° angle of repose (developer.md §84.4; stage 2 of
the meander-development extension docs/meander_plan.md; both in Japanese).
The height difference corresponding to the part of the slope between
neighbouring cells that exceeds tanφ_r is moved from the higher side to the
lower side at the fraction `repose_relax`/2/8 per update (a conservative
relaxation that does not overshoot even with 8 directions at once; one sweep
per update).

## Configuration

| Item | Value |
|---|---|
| Domain and grid | 41 m × 41 m, 41 × 41 cells (Δx = 1 m), walls on all four sides |
| Terrain | A cone at the centre (side slope 1.0 = 45°, summit 3 m). `make_init.py` |
| Settings | `f_repose = 1`, φ_r = 30°, relax = 0.5, change cap 0.05 m, soil layer 10 m. No bed load |
| Time | dt = 0.1 s, 60 s (600 updates). `save/state.dat` at the end |

| File | Contents |
|---|---|
| `Check_repose.py <save>` | (1) volume conservation \|Σ(z − z₀)\| < 1e-9, (2) final maximum slope (axial and diagonal) ≤ tan30° + 1e-4, (3) the summit drops by at least 0.5 m, (4) identity of the co-moving update |

## Running

```bash
make
./Run.sh          # generate inputs → run (1 second) → Check
./Run_MPI.sh 4    # MPI. The rule is that state.dat is byte-identical to the serial run
```

## Findings (2026-10-17)

| Check | Value |
|---|---|
| Σ(z − z₀) | 1.8e-14 m·cell |
| Maximum slope | 0.577350 (converged to tan30° within 1e-7) |
| Summit | 3.00 → 2.08 m (moved volume 7.9 m³) |
| Co-moving update | 2.1e-14 m |

The profile along the central row is 0, 0.35, 0.93, 1.51, 2.08, 1.51, 0.93,
0.35, 0 m: a 30° cone, including the diagonal directions. MPI np = 2, 4 are
byte-identical to the serial run.

## Related documents

- developer.md §84.4, docs/meander_plan.md §3.3 (in Japanese)
- [docs/users_guide/geomorph.md](../../../docs/en/users_guide/geomorph.md) — `f_repose`, `repose_phi`, `repose_relax`
