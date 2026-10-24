# test/nhbore — Undular bore splitting from a long-wave step (soliton fission by the non-hydrostatic correction)

> English mirror of test/nhbore/README.md. The Japanese file is the master copy.

[日本語](../README.md)

docs/nonhydrostatic_plan.md §11 Phase 5 (in Japanese); the elementary process
of the "soliton fission and undular bores of tsunamis running up rivers" of
its §1. In a flat-bed, frictionless, wall-bounded channel (450 m × 8 m,
Δx = Δy = 0.25 m = H/4, 32 rows), a step with H = 1 m raised by a/H = 0.1 for
x < 100 m (tanh transition 4 m; user routine `wave_bore`) is given the
velocity of a right-going simple wave u = 2(√(g(H+η)) − √(gH)) and
propagated for 100 s. The front steepens nonlinearly and, by dispersion,
splits into a wave train from its head.

- `./Run.sh` / `./Run_MPI.sh N`: regression test of param.txt
  (f_nonhydrostatic=1, CG) (Log.txt; the Runge column excluded).
- After running `./encflow param20.txt` (a/H = 0.2) and
  `./encflow param_h.txt` (hydrostatic), `./Bore.py` tabulates, from the
  water surface along the central row, the position of the front, the
  position and height η₁/a of the leading wave, the number of crests in the
  wave train, and the speed of the leading wave. `./Fig.py` draws the figure
  to `figs/bore.png`.

## Figure

![Undular bore splitting from a step and growth of the leading wave](../figs/bore.png)

## Findings (2026-10-12)

| Configuration | η₁/a (t = 50 / 90 s) | Number of crests (90 s) | Leading-wave speed / √(gH) (second half) |
|---|---:|---:|---:|
| Non-hydrostatic a/H = 0.1 | 1.72 / 1.97 | 6 | 1.076 |
| Non-hydrostatic a/H = 0.2 | 2.18 / 2.46 | 10 | 1.137 |
| Hydrostatic a/H = 0.1 | 1.41 / 1.55 (numerical oscillation behind the bore) | 11 | 1.106 |

- In the non-hydrostatic run the front of the step splits from its head into
  a wave train (undular bore), and the height of the leading wave approaches
  monotonically the asymptotic value 2a of the KdV undular bore (Gurevich &
  Pitaevskii 1974) (1.97a at 90 s for a/H = 0.1, still growing). The speed of
  the leading wave is −2% relative to √(gH)(1 + a/H) = 1.10 for a solitary
  wave of height 2a (including the −0.8% effect of the channel in which the
  diagonal edges are missing at the walls; test/nhsolitary).
- For a/H = 0.2 the leading wave grows beyond 2a (2.46a at 90 s). Unlike the
  weakly nonlinear KdV, the undular bore of the fully nonlinear one-layer
  model (Serre/Green–Naghdi type) has a leading-wave ratio that exceeds 2 for
  stronger steps (El, Grimshaw & Smyth 2006), and this is consistent with
  that. 100 s is excluded because the front has reached the east wall.
- The hydrostatic run advances as a bore, but numerical oscillations
  (1.4–1.6a) arise behind the bore (the same origin as the overshoot behind
  the bore seen for dt ≤ 0.025 in the verification against the Stoker
  solution; §69.6). They are distinct from the wave train split by
  dispersion, and the crest spacing depends on the grid.
- The growth of the leading wave is slow, t ∝ 1/(dispersion time scale), and
  does not reach the asymptotic value even in the 450 m channel. For a
  quantitative comparison, use the time evolution of the leading-wave height
  itself (figure, right).
