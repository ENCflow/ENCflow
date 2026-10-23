# examples/tower_karst — Formation experiment of bare-rock towers left standing on a plain (tower karst)

> English mirror of examples/tower_karst/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This example looks at the process by which limestone towers (fenglin) are left
standing above a plain in a humid tropical karst, as the superposition of
**dissolution f_dissol** (diffuse dissolution proportional to the infiltration
+ lateral dissolution of rock walls in contact with ponded water) and
**rockfall and talus f_rockfall** (bedrock mode `rf_bedrock = 1`). The inputs
are only `param.txt` in this directory and the generated inputs `z.txt`,
`sd.txt` and `ksv.txt` (developer.md §86, §48.7; docs/karst_plan.md §2.5,
§2.6). For the formation of doline fields see
[examples/karst](../../karst/en/README.md).

## Causation (cause and effect inside the model)

- The towers are bare rock with a small infiltration capacity (1 mm/h), so
  almost all the rain runs off as surface flow down to the foot. The plain is
  covered by soil (1 m) with a large infiltration capacity (40 mm/h), so it
  infiltrates its own rain and the water arriving from the towers.
  Dissolution is proportional to the infiltration (aggressive water that has
  passed through soil CO₂), and on bare rock 0.3 times the runoff generated
  there also dissolves the rock face, so **the plain and the tower feet are
  lowered quickly and the towers at about one third of that rate**.
- The cells at the foot receive the water collected from the towers and
  infiltrate especially much, so they are lowered into a moat. Rock walls in
  contact with the ponded water at the foot are cut into notches by lateral
  dissolution (distributed by the wetted-area ratio).
- When the rock wall exposed by the lowering of the foot (the drop to the
  lowest point within a window of 1 cell) exceeds the critical height
  H_c = 10 m, the excess collapses and accumulates at the foot as talus (ht;
  also added to the soil sd). The towers are bedrock without soil, so
  `rf_bedrock = 1` is used to collapse them. As the talus buries the foot the
  exposed face becomes lower and collapse stops.
- Since no sinks are used, the water uptake is capped by the infiltration
  capacity and the positive feedback within a storm does not run away.
  However, the hole where the water collecting at the tower foot infiltrates
  can be deepened by tens of centimetres in a single storm, so morfac is kept
  at 5×10³ (at 10⁴ the flow diverged at a step of 9 m in the hole).

## Setup

| Item | Value |
|---|---|
| Domain and grid | 1000 × 1000 m, Δx = 10 m (100 × 100 cells), walls on all four sides |
| Initial terrain | Plain (z ≈ 0; undulation with correlation length ≈ 30 m and standard deviation 0.3 m) with 4 bell-shaped hills (height 40 m, radius 90 m) and 2 small hills (20 m, 60 m). z > 5 m is bare rock |
| Soil and infiltration | Plain: soil 1 m (sy 0.2), Green-Ampt 40 mm/h; bare rock: soil 1e-3 m, 1 mm/h (`sd.txt`, `ksv.txt`). Soil water drains to the conduit layer (the receiver of the fracture network) at 20 mm/h. No sinks |
| Rainfall | Representative storm 40 mm/h × 1 h, repeated with a 1-day period |
| Dissolution | c_eq = 300 mg/L (below the soil in the humid tropics), ρ_r = 2500 → k_d = 1.2×10⁻⁴; infiltration + runoff on bare rock × 0.3 (dissol_src = 3); residue fraction 0.1; lateral dissolution dissol_lat = −1 (automatic distribution) |
| Rockfall | rf_hc = 10 m (half of the 20 m tower wall), window rf_rc = 10 m, talus repose angle 35°, relax = 0.5, bedrock mode rf_bedrock = 1, cap of 1 m per edge and update |
| Time | dt = 2 s, landform update every 10 min × morfac 5×10³ (1 day = 5×10³ storms = 100 years at 50 per year). 60 days = 6 kyr of morphological time. Output every 10 days. About 1–2 hours (4 threads) |

```
make                                       # link to ../../bin/encflow
python3 make_terrain.py                    # z.txt, sd.txt, ksv.txt
./encflow param.txt > Screen.log           # about 1-2 hours
python3 plot_results.py | tee analysis.txt # figs/*.png + tables
```

## Checks

Tables from `plot_results.py` (morphological time 6000 years = 300000 storms
converted at 50 per year):

| Item | Value |
|---|---|
| Water balance | Final S_total = 2.400 m = cumulative rainfall 40 mm × 60 days (mass conservation; the ponded water disappears by infiltration every day) |
| Dissolved rock (ledger) | 1 465 945 m³ |
| Rock moved by collapse (ledger; bulk) | 2 493 m³ (44 thousand edge updates). Final talus Σht Δx² = 2 172 m³ (maximum 3.7 m) |
| Volume loss of the ground surface | Σ(z₀ − z)Δx² = 1 319 350 m³ = dissolution × (1 − 0.1) = 1 319 350 m³ (agreement to all digits; collapse is conservative and does not contribute) |
| Denudation of the plain (cells never ponded) | Median 1.30 m = 216 mm/kyr |
| Denudation of the foot (261 ponded plain cells) | Median 2.8 m, maximum 12.1 m |
| Soil (debris + residue) | Plain 1.14 m (initially 1 m), bare-rock area 0.04 m (initially 0.001 m), maximum 6.2 m (talus at the foot) |

## Results

![maps](../figs/maps.png)

![sections](../figs/sections.png)

![towers](../figs/towers.png)

| Morphological time (yr) | Plain (m) | Summit height of towers 1–4 (m) | Relative height of towers 1–4 (m) | Relative height of small hills 5 and 6 (m) | Max. slope angle of the bedrock surface at the foot |
|---|---|---|---|---|---|
| 0 | 0.0 | 39.3–40.3 | 39.3–40.4 | 19.4–19.6 | 29–35° |
| 3000 | −0.67 | 39.1–40.1 | 39.8–40.8 | 19.9–20.1 | 35–38° |
| 6000 | −1.32 | 39.0–40.0 | 40.3–41.3 | 20.4–20.6 | 38–48° |

- **Differential dissolution increases the relative height.** The plain is
  lowered uniformly at 216 mm/kyr, while the tower summits are lowered only
  50 mm/kyr (0.3 m in 6 kyr) by the surface source on bare rock
  (runoff × 0.3), so the relative height increases by the difference, 1.0 m.
  The equivalent radius is almost unchanged; the change in shape is
  concentrated at the foot.
- **Moats and holes at the foot.** The rain on the towers collects in the
  lowest cells at the foot and infiltrates there, so the ring at the foot is
  lowered twice as much as the plain (3 m), and the few cells that collect
  the most water are lowered on the order of 10 m (the black dots around the
  towers in the denudation-depth map; the streaks along the valley lines of
  the plain's undulation are the paths along which water flowed and
  infiltrated). These correspond to the "swallow holes and foot caves at the
  base of the towers" of real karst.
- **Steepening of the foot and collapse.** As the foot is lowered the lower
  slope steepens (maximum slope angle of the bedrock surface 35° → 37–49°).
  Collapse occurs only where the exposed face exceeds H_c = 10 m (the walls
  of cells whose foot holes have reached the order of 10 m); the rock moved
  is 0.2 % of the dissolution (2.5 thousand m³), and the talus accumulates up
  to 3.7 m inside the holes. The tower walls have not retreated yet (in 6 kyr
  the incision at the foot is a few metres and most of the wall is below
  H_c). Reducing H_c or extending the morphological time enters the stage in
  which the walls collapse and retreat.
- **The small hills** (height 20 m) do not disappear in 6 kyr either. The
  disappearance of towers and the transition from fengcong to fenglin need
  tens of kyr of morphological time, until the lowering of the plain reaches
  the tower height (at morfac 5×10³ one day = 100 years, so 600 days = 60 kyr
  in a restart chain).

## Notes on interpretation

- The coefficients are not calibrated values. c_eq = 300 mg/L is toward the
  upper end for recharge water below the soil in the humid tropics, and a
  plain denudation of about 240 mm/kyr is at the upper end of the literature
  range for tropical karst (tens to hundreds of mm/kyr). The morphological
  time is a conversion with "one 1-day cycle = one representative storm,
  50 per year".
- Collapse is an instantaneous relaxation set by the critical height `rf_hc`
  (not a rate law) and spreads at the talus repose angle `rf_phi`. The debris
  stays at the foot as talus ht and soil sd and, apart from the talus repose
  angle, does not move unless creep or bedload is enabled (this example does
  not move it). The towers are bedrock without soil, so `rf_bedrock = 1` is
  required (with the default 0, cells with sd ≤ 0 do not collapse).
- Dissolution of the tower rock faces is the surface source
  (`dissol_src = 3`), which spends 0.3 times the dissolution capacity of the
  runoff generated on the tower on that rock face. Water arriving from
  upstream is regarded as saturated and not counted, so concentration of
  dissolution along flow paths (karren) is not represented.
- The notches at the foot act only while the foot is ponded immediately after
  a storm, because lateral dissolution works on "walls in contact with ponded
  water". In this 6 kyr run no wall retreat is visible; the holes and debris
  at the foot are the main changes. To see tower retreat, extend the
  morphological time by a factor of 10 or more.
- The upper limit of morfac is looser than with sinks but not unlimited. The
  holes at the foot can be deepened by tens of centimetres in a single storm
  (infiltration 40 mm/h × duration of ponding), so at 10⁴ the flow diverged
  once the step of the hole reached 9 m (stable at 5×10³).
- All four sides are walls, and the water on the plain disappears only by
  infiltration. To represent a plain that drains quickly (lateral groundwater
  flow or rivers), add lateral flow or an outlet.

## Related

- [examples/karst](../../karst/en/README.md) — doline fields, the upper limit
  of morfac, comparison of lateral dissolution and collapse
- [docs/users_guide/geomorph.md](../../../docs/en/users_guide/geomorph.md)
  "Limestone dissolution" and "Rockfall and talus",
  [sediment.md](../../../docs/en/users_guide/sediment.md) — equations and the
  basis of the defaults
- [test/dissol](../../../test/dissol/en/README.md),
  [test/rockfall](../../../test/rockfall/en/README.md) — analytical
  verification; [docs/karst_plan.md](../../../docs/karst_plan.md) (in
  Japanese) — design and limitations
