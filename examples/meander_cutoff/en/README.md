# meander_cutoff — cutoff of a meander loop with a narrow neck and plugging of the old channel (stage 4)

> English mirror of examples/meander_cutoff/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This example follows, using only landform evolution on a fixed grid and the
wet/dry treatment, the process by which the narrow strip of land between
adjacent loops (the neck) of a highly sinuous channel (a sine-generated curve)
is overtopped by a flood and cut off, and the old channel (the loop) turns into
slack water (docs/meander_plan.md stage 4 and §3.5; developer.md §84.5). No
reconnection of the channel centreline and no special treatment to "make an
oxbow lake" are used. No code changes (settings only).

## Geometry and settings

- 346 m × 206 m, dx = dy = 2 m. The centreline is a sine-generated curve with
  direction angle θ(s) = ω sin(2πs/Λ) (ω = 105°, Λ = 320 m, 2 wavelengths); the
  inlet and outlet are straight (inflow cells on the west edge → free outflow on
  the east edge). Width 20 m, bed slope 0.001 (along the channel length),
  initial depth 0.8 m.
- The floodplain height is "the maximum bed elevation within a radius of 24 m
  + 1.6 m" (above the water surface of every adjacent reach; if it were set by
  channel length or valley slope, the floodplain of the highly sinuous downstream
  part would lie below the upstream water surface and overflow before the flood).
  Only the land close to both of two channel reaches = the neck is +0.95 m
  (orange outline in the figures). The soil thickness is 0 within 30 m of both
  ends and ramps over 150 m from the upstream end.
- Inflow Q = 15 m³/s (30 min) → 40 m³/s (flood at 40–100 min) → 15 m³/s (until
  180 min). morfac = 10 (3 h hydraulic = 30 h morphological time).
- Landform evolution: Ashida–Michiue formula (d50 = 1 mm), bed-slope term,
  equilibrium secondary-flow term (deviation-angle cap `sec_rmax = 0.3`; in the
  sharp bends with R/W = 3, r = N* h κ grows with the depth, and the cap keeps
  the pools from deepening without limit), angle-of-repose avalanching at 40°
  (the banks at 1.6 m / 2 m = 38.7° are stable). Neither the bank-erosion law
  nor suspended sediment is used (combining 0.2 mm suspended sediment without
  sediment feed lowers the bed rapidly by suspension). Advection uses the default
  scheme 3, dynamic reassignment of blocked openings on all edges
  (`f_opening_dynamic = 2`; §84.7), dt = 0.1 s.

## Running

```
cd examples/meander_cutoff
make                      # generates the inputs (10 s) and links the executable
./encflow param.txt       # about 10 min (gfortran, 2–4 threads)
python3 plot_results.py   # figs/*.png and tables
```

## Results (recomputed on 2026-10-19; gfortran 13.3, -Ofast; advection with the default scheme 3 (after the §68.36 fix, including the two-sided condition of a one-sided face of §68.39), f_opening_dynamic = 2)

![Sequence](../figs/sequence.png)

Left: velocity; right: bed change (blue = scour, red = deposition; black line =
initial banks). Before the flood (30 min) pools form at the outer bank and bars
at the inner bank of each loop (the same mechanism as examples/meander). During
the flood (40–100 min) the floodplain is widely inundated, and the flow crossing
the neck carves a new channel joining the roots of the loop. After the flood
(from 120 min) the flow concentrates in the new channel, the loop becomes slack
water with velocity below 0.3 m/s, and deposition proceeds at its ends and
inside the loop.

![Final state](../figs/final.png)

| t (min) | Morphological time (h) | Q (m³/s) | Flowing cells in the loop (\|V\| > 0.3 m/s) | Flowing cells in the neck zone | Wet outside the initial channel | Deepest scour (m) |
|---|---|---|---|---|---|---|
| 30 | 5 | 15 | 2262 | 76 | 95 | −1.88 |
| 60 | 10 | 40 | 1659 | 323 | 4369 | −2.48 |
| 90 | 15 | 40 | 1686 | 234 | 3400 | −4.13 |
| 120 | 20 | 15 | 965 | 148 | 2582 | −3.63 |
| 150 | 25 | 15 | 868 | 163 | 2478 | −3.61 |
| 180 | 30 | 15 | 774 | 153 | 2437 | −3.66 |

## Findings

- **The cutoff emerges as a consequence of the wet/dry treatment and landform
  evolution** (the policy of plan §3.5). Even without the overflow of a flood,
  bank retreat alone (angle-of-repose avalanching, or slump blocks of cohesive
  banks) cuts the neck at 100 to 120 h (see "Slump blocks and a cutoff without
  a flood" below). Before the flood almost no flow crosses
  the neck (76 flowing cells in the neck zone); the flow overtopping it during
  the flood (323 cells) carves a channel through the neck, and the new channel
  remains after the flood (153 cells). The flowing cells in the loop decrease
  from 2262 to 774, and most of the old channel has become slack water.
- **The opening of the new channel and the plugging of the old channel are
  separate stages** (plan §3.5). After 30 h of morphological time, deposition
  has only begun at the ends of the loop, and complete separation (an oxbow
  lake) is not reached. Transporting the fines that fill the old channel
  requires suspended sediment (f_suspend) and sediment-feed conditions (§84.5).
- A flood of Q = 25 m³/s does not overtop the neck (+0.95 m) and no cutoff
  occurs. The flood magnitude and the neck height (= the degree of bar fixation
  and floodplain formation) set the condition for a cutoff.
- The outer-bank pools of the sharp bends (R/W = 3) deepen to more than 3 m
  (initial depth 0.8 m). The depth changes with `sec_rmax` and the repose angle.
  During the flood the flow in these pools is fast, hence dt = 0.1 s (dt = 0.2
  stops with a CFL violation).
- The per-update change limit `fluv_dzmax` (0.05 m) is triggered often (rapid
  incision of the new channel during the flood). Lowering morfac reduces the
  triggering, but the storyline of the results is the same.

## Slump blocks and a cutoff without a flood (2026-10-23)

With the bank mode of cliff collapse and talus `f_rockfall` from main
(`rf_bank = 1`; developer.md §84.17), four configurations with and without the
flood were compared (`./encflow param_<name>.txt`; figures with
`python3 plot_results.py result_<name> 7`).

| Parameter file | Inflow | Banks | Morphological time |
|---|---|---|---|
| param_slump.txt | with the flood (as above) | angle of repose 40° + slump blocks (H_c = 1.8 m, talus 35°) | 30 h |
| param_noflood.txt | Q = 15 m³/s constant (the neck is not overtopped) | angle of repose 40° (control) | 180 h |
| param_slump_noflood.txt | same | angle of repose 40° + slump blocks | 180 h |
| param_slump_cohesive.txt | same | **cohesive**: angle of repose 60° (banks at 1.6 m / 2 m = 38.7° do not fail) + retreat by slump blocks only | 180 h |

With the flood, the cutoff is hardly changed by the slump blocks (after 30 h,
846 flowing cells in the loop against 774, 139 in the new channel against 153;
collapse 490 m³): slump blocks take no part in a cutoff carved by overflow. In
the three runs without a flood, the flowing cells in the loop and in the neck
zone evolved as follows (every 20 h of morphological time).

| Morphological time (h) | 20 | 40 | 60 | 80 | 100 | 120 | 140 | 160 | 180 |
|---|---|---|---|---|---|---|---|---|---|
| control (repose 40°) loop / neck | 2220 / 231 | 2151 / 237 | 2068 / 235 | 1940 / 230 | **833** / 154 | 811 / 171 | 793 / 163 | 1208 / 140 | 1124 / 161 |
| repose 40° + slump blocks | 2232 / 240 | 2133 / 250 | 2092 / 228 | 1914 / 243 | **821** / 154 | 794 / 196 | 777 / 204 | 1090 / 159 | 1005 / 154 |
| cohesive + slump blocks | 2231 / 229 | 2140 / 238 | 2079 / 251 | 1889 / 241 | 1817 / 249 | **787** / 172 | 795 / 177 | 784 / 175 | 1095 / 147 |

![Sequence without a flood, cohesive banks with slump blocks](../figs/sequence_slump_cohesive.png)

![Final state without a flood, cohesive banks with slump blocks](../figs/final_slump_cohesive.png)

- **Even without overflow, bank retreat alone cuts the neck** (the proper form
  of a neck cutoff). In the control (non-cohesive = avalanching) and with slump
  blocks added, the flowing cells in the loop drop from 1,900 to 800 between 80
  and 100 h; with cohesive banks (slump blocks only) between 100 and 120 h, and
  the flow moves into the new channel through the neck. Of the 409 cells of the
  neck zone, about 230 are lowered by more than 0.2 m at 60 h (in all three
  runs) and about 220 stay wet after the cutoff.
- **On cohesive banks the slump blocks are the only path of retreat**
  (avalanching 0 m³, collapse 11,300 m³). The cutoff comes 20 h later than on
  non-cohesive banks, and its timing is set by the critical height H_c (= the
  pool scour at which failure starts). In the non-cohesive control, avalanching
  (11,600 m³) plays the same role, and adding slump blocks does not change the
  timing (only the split, 6,900 m³ of collapse + 4,900 m³ of avalanching).
- The downstream (second) loop is the one cut; the upstream loop remains at
  180 h (figure, 120 to 150 h: the right loop is slack water = black). The
  flowing cells in the loop return to about 1,100 after 160 h because the
  widened new channel reconnects with the ends of the loop and part of the flow
  re-enters it (180 h). As with the flood, the plugging of the old channel
  (deposition at its ends) only begins.
- The wet cells outside the initial channel grow to about 3,400 at 180 h. Banks
  with a repose angle of 40° or a critical height of 1.8 m retreat widely under
  180 h of constant discharge (widening), so the timing of the neck cutoff
  depends strongly on the bank strength (φ_r, H_c).

## Related documents

- docs/meander_plan.md §3.5, developer.md §84.5 and §84.17 (in Japanese)
- [examples/meander](../../meander/en/README.md) — deformation of a meandering channel by the same mechanism (widening and cross-section shape)
- [docs/users_guide/geomorph.md](../../../docs/en/users_guide/geomorph.md)
