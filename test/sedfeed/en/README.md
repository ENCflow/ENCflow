# test/sedfeed — Sediment feed at a segment inflow

> English mirror of test/sedfeed/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Verification of the three sediment-feed methods for bed load and suspended
sediment (developer.md §84.9, docs/meander_plan.md §3.6a; both in Japanese).

## Setup

A straight channel 5 cells wide (Δx = 1 m, length 300 m, slope 0.002,
n = 0.03, dry ground at +2 m on both banks, soil thickness 2 m so that the
whole bed is mobile, and `f_opening_dynamic = 2` so that the uniform flow
matches Manning). Segment inflow Q = 2.35 m³/s at the west end (uniform-flow
depth 0.5 m); free outflow at the east edge (a wall in the qb configuration).
d50 = 3 mm, morfac = 10 (cseq: suspended sediment 0.2 mm, morfac = 1).

| Configuration | Settings | Role |
|---|---|---|
| nofeed | fluv_bcfeed = 0 | No feed. A degradation wave from the upstream end |
| feed1 | fluv_bcfeed = 1, fluv_bcfeed_fac = 1 | Capacity feed. Supply through the inflow face = net outflow of the inflow cell → the bed at the inlet is fixed |
| feed05 | factor 0.5 | The lowering at the inlet is reduced (not proportionally: once a hole forms at the inlet, the net outflow decreases and so does the supply) |
| qb | inflow_qb = 0.0005 m³/s (the east edge is a wall) | Source of the bed-load transport rate. Ledger (1 − λ) Σ(z − z0) A = ∫Qb dt × morfac |
| cseq | f_suspend = 1, inflow_cs_eq = 1 | Equilibrium-concentration feed of suspended sediment. Inflow concentration = C_eq of the inflow cell |
| nofeed_creep | nofeed + f_creep = 1 (creep_d = 1e-30 m²/s) | Control for the combination with creep. The change made by creep in one update is smaller than the ULP of z, so the bed should be bit-identical to nofeed (developer.md §19.10) |

## Checks (Check_sedfeed.py)

1. No feed: Δz of the inlet cells < −0.2 m.
2. Capacity feed (factor 1): |Δz| of the inlet cells < 1e-9 (checked on z in
   save; exactly 0 since supply = net outflow), mean |Δz| over the upstream
   reach x = 20–120 m < 0.03 m (0.075 without feed).
3. Factor 0.5: the lowering of the inlet cells is smaller than without feed.
4. The inflow_qb ledger closes to relative 1e-9 (z of save_qb/state.dat).
5. Equilibrium-concentration feed: hs/h in the inflow column agrees within
   ±1 % with the C_eq evaluated by the same formula from τ* of the inflow
   cells.
6. Combination with creep (nofeed_creep): the bed is bit-identical to nofeed
   (creep must not count the open-boundary outflow of bed load a second time;
   before the fix of 2026-10-27 the cells at the east end were scoured by
   110 m). With creep_d of about 1e-12, the contribution of creep itself
   (about 1e-7 m) is amplified to 0.16 m by the nonlinear development of the
   bed degradation, so the control uses a value below the ULP.

Run_MPI.sh performs the same checks under MPI and checks bit identity with
save_*_serial (serial and MPI are built with the strict flags and compared;
§28.3).

## Usage

```
make
./Run.sh            # serial (6 runs, about 5 minutes)
./Run_MPI.sh 2      # MPI
```
