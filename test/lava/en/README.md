# test/lava — lava flow (fn_lavaflow): Huppert similarity solution, Bingham stopping thickness, plastic dome, solidification at a wall, burial of the soil layer, temperature (cooling, heat advection, a flow that stops as it cools, crosswind numerical diffusion of the heat) and conveyance of valleys (8 neighbours)

> English mirror of test/lava/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Checks of the lava flow module (`fn_lavaflow`; Bingham viscous gravity
current + solidification. [The lava flow chapter of the users
guide](../../../docs/en/users_guide/lavaflow.md), developer.md §51). It is
closed by analytical-solution checks without a reference comparison (the
same practice as [test/volcano](../../volcano/en/README.md)). The flow is
computed on the default 8-neighbour 9-point stencil (`lv_diagratio = 1/3`;
from 2026-11-05; developer.md §96). Four neighbours are given explicitly in
configuration 4' (control), configuration 10 (a check of a property of four
neighbours) and `ch45w3q` of configuration 11 (control).

1. **Huppert** (`param.txt`): flat bed, constant-rate effusion from the
   single central cell (yield stress 0 = Newtonian limit). The
   area-equivalent radius, the growth law and the ledger are compared with
   the axisymmetric similarity solution of Huppert (1982) for constant
   supply, r_N = 0.715 (g Q³/3ν)^{1/8} √t.
2. **Bingham** (`param_ty.txt`): supply for 300 s from a row of vents at the
   upstream end of a uniform slope (tanθ = 0.2), then stop. The stopping
   thickness h∞ = τ_y/(ρ g tanθ), the solidification and the ledger are
   compared.
3. **Equivalence of the defaults** (`param_min.txt` / `param_minx.txt`): the
   same settings as configuration 2 with `lv_visc` and `lv_vsol` omitted /
   explicit; the save and the Log are byte-identical (§66).
4. **Isotropy** (`param_dome.txt`): the shape at rest of lava erupted for
   900 s from the single central cell of a flat bed is compared with the
   analytic plastic dome h(r)² = (2τ_y/ρg)(R − r) (Blake 1990), checking
   that it is the same along the grid axes and the diagonals
   (developer.md §51.4). `param_dome4.txt` (configuration 4') is a control
   that computes the same input with the flow on 4 neighbours
   (`lv_diagratio = 0`, the default before 2026-11-05; developer.md §96) and
   must pass the same check.
5. **Solidification at a wall** (`param_wall.txt`): lava is ponded against a
   10 m step (wall) at the end of a flat floor, and the check is that the
   whole amount solidifies, up to the cells touching the wall
   (developer.md §51.5).
6. **Burial of the soil layer** (`param_bury.txt`): a soil layer and
   groundwater (Green-Ampt) are added to the topography of configuration 5,
   and the check is that the soil layer under solidified lava is buried and
   the total water is conserved when the water in it moves to the surface
   (developer.md §51.6).
7. **Cooling of a layer at rest** (`param_cool.txt`; temperature mode
   f_lvtemp = 1): a uniform 1 m layer of lava (which does not flow) on a flat
   floor; the temperature as it cools by radiation and convection is compared
   with the backward-Euler recursion of the cooling equation and with its exact
   solution, and the time of solidification at the solidification temperature
   and the heat ledger are checked. `param_coolm.txt` (configuration 7m) is the
   same computation reading the air temperature from fn_meteo, and its save is
   byte-identical (developer.md §51.7).
8. **Heat advection** (`param_adv.txt`; temperature mode, no cooling): lava is
   erupted from two vents with different eruption temperatures, and the
   conservation of heat and the range of the temperature (between the two
   eruption temperatures) are checked. `param_adv0.txt` (configuration 8') is
   the isothermal run of the same input with f_lvtemp = 0, and the lava deposit
   is byte-identical (with zero temperature sensitivity and no cooling, the
   flow of the temperature mode is the same as the isothermal one).
9. **A flow that stops as it cools** (`param_run.txt`, `param_run4.txt`;
   temperature mode): the same volume is erupted on a uniform slope at effusion
   rates Q and 4Q, and the check is that the length of the flow that has stopped
   by cooling increases with the effusion rate (the same direction as Walker
   1973). `param_runi.txt` and `param_runi4.txt` are the isothermal control
   without temperature, whose length does not depend on the effusion rate.
   Configuration 9r checks that configuration 9 saved part way and restarted is
   byte-identical to the uninterrupted run (Run.sh writes its inputs).
   Configuration 9n (`param_runnz.txt`, `param_run4nz.txt`) computes the two
   runs of the temperature mode on a slope with a fixed perturbation of ±1 mm in
   the bed (`make_init.py runnz`) and checks that the same trend (the 4Q flow is
   longer) holds for the perturbed flow (a flow uniform across splits into
   channels under a perturbation; the correction in developer.md §94).
10. **Crosswind numerical diffusion of the heat** (`param_x0.txt`,
    `param_x0m.txt`, `param_x45.txt`, `param_x45m.txt`; temperature mode, no
    cooling): lava at 1150 °C from one side of the vents and at 1050 °C from the
    other side of a sheet flow down a uniform slope; the width to which the
    temperature boundary spreads across the flow is compared for a flow along a
    grid axis (0°) and at 45°, with first-order upwind (`f_lvtemp_scheme = 1`
    given explicitly) and MUSCL (`f_lvtemp_scheme = 3`, the default) for the
    heat advection. The checks are that it does
    not spread at 0°, that at 45° first-order upwind matches the crosswind
    diffusivity of the modified equation (√2/4)·u·Δx, and that MUSCL gives less
    than 1/4 of it (developer.md §94). These are properties of 4 neighbours,
    so `lv_diagratio = 0` is given explicitly. Configuration 10d
    (`param_x0d.txt`, `param_x0dm.txt`, `param_x45d.txt`, `param_x45dm.txt`)
    computes the same input on the 8-neighbour 9-point stencil of the flow
    (`lv_diagratio = 1/3`) and checks that the first-order crosswind
    diffusivity matches (1 − d)F(φ) + d√2 F(φ − 45°) (F the 4-neighbour
    coefficient; 0.167 at 0° and 0.236 at 45°) and that MUSCL gives less than
    1/4 of it (developer.md §96).
11. **Dependence of the conveyance of valleys on their orientation**
    (`param_ch0w1.txt`, `param_ch45w1.txt`, `param_ch0w3.txt`,
    `param_ch45w3.txt`, `param_ch45w3q.txt`; the 8-neighbour 9-point stencil
    `lv_diagratio = 1/3`): valleys one and three cells wide at 0° and 45° are
    cut into a slope of 0.1 (walls 20 m higher on both sides), Newtonian lava
    flows down them at a constant rate, and the conveyance ratio
    k = Q/(W(ρg/3η)h³S) (W the valley width) is found from the thickness of the
    uniform flow in the middle of the valley. The model has no wall drag, so
    k = 1 is correct. The checks are k = 1 at 0° and for one line at 45°, and
    1 ± 0.1 for three lines at 45°; the 4-neighbour control (`ch45w3q`,
    `lv_diagratio = 0`) must give k < 0.8 (the check can detect the
    difference) (developer.md §96).

## Configuration

| Item | Configuration 1 Huppert | Configuration 2 Bingham | Configuration 4 isotropy | Configuration 5 solidification at a wall | Configuration 6 burial of the soil layer |
|---|---|---|---|---|---|
| Domain and grid | 61 m × 61 m, Δx = 1 m, flat | 100 m × 8 m, Δx = 1 m, tanθ = 0.2 (`zinit.txt`) | 61 m × 61 m, Δx = 1 m, flat | 40 m × 8 m, Δx = 1 m, flat floor and a 10 m step for i ≥ 31 (`zwall.txt`) | Topography of configuration 5 with a soil layer sd0 = 1 m (specific yield 0.2), Green-Ampt groundwater (infiltration capacity 360 mm/h) and 5 cm of initial surface water |
| Effusion | Constant 0.5 m³/s at the center (31, 31) | A total of 0.5 m³/s over the 8 cells at the upstream end i = 5 for 300 s (stepwise stop by a duplicated time) | 2 m³/s at the center (31, 31) for 900 s (1798 m³ in total) | A total of 0.2 m³/s over the 8 cells of column i = 28, 3 m from the wall, for 300 s | A total of 0.2 m³/s from the vents of configuration 5 at 15–20 min (after the surface water has infiltrated) |
| Fluid | ρ = 2600, η = 2e4 Pa·s, τ_y = 0, no solidification | ρ = 2600, η = 2e3 Pa·s, τ_y = 2000 Pa, solidification rate 0.005 m/s, stop detection 5e-4 m/s | ρ = 2600, η = 1e6 Pa·s, τ_y = 1e4 Pa, no solidification | Same as configuration 2 | Same as configuration 2 |
| Time | dt = 0.5 s, 600 s | dt = 0.5 s, 4800 s | dt = 1 s, 6000 s | dt = 0.5 s, 4800 s | dt = 0.5 s, 6000 s |
| Analytical value | r_N(600 s) = 12.13 m | h∞ = 2000/(2600 × 9.8 × 0.2) = 0.3925 m | R = 17.11 m, center thickness H = √(aR) = 3.665 m (a = 2τ_y/ρg = 0.7849 m) | (conservation and complete solidification) | (conservation; 16 m³ of water in total) |

Temperature mode (configurations 7–9; the values are for the checks, not defaults):

| Item | Configuration 7 cooling of a layer at rest | Configuration 8 heat advection | Configuration 9 a flow that stops as it cools |
|---|---|---|---|
| Domain and grid | 4 m × 8 m, Δx = 1 m, flat | 41 m × 21 m, Δx = 1 m, flat | 320 m × 40 m, Δx = 5 m, tanθ = 0.1 (`zrun.txt`) |
| Effusion | A total of 3.2 m³/s into all 32 cells (`cool_cells.txt`) at the first update only (t = 10 s) = a 1 m layer | 0.5 m³/s each at (11, 11) and (31, 11) for 600 s, eruption temperatures 1150 and 1050 °C | 1150 °C lava over the 8 cells at the upstream end i = 3, a total of 2 m³/s for 40 min (configuration 9) / 8 m³/s for 10 min (9b); the same volume of about 4800 m³ |
| Fluid | does not flow (uniform layer) | η = 2e4 Pa·s, τ_y = 0, temperature sensitivity 0 | η_r = 1e3 Pa·s, τ_r = 100 Pa (at 1150 °C), temperature sensitivities 0.04 1/K; the isothermal control has η = 1e3, τ_y = 2500 Pa and solidification by a speed threshold |
| Cooling | ε = 0.95, h_c = 70 W/m²/K, c_p = 1150 J/kg/K, air 20 °C, solidification 800 °C | none (ε = 0, h_c = 0), solidification 700 °C | ε = 0.95, h_c = 70, c_p = 1150, air 20 °C, solidification 1000 °C |
| Time | dt = 1 s, update 10 s, 7200 s | dt = 0.5 s, 900 s | dt = 1 s, 7200 s |
| Compared with | the backward-Euler recursion, the exact solution (RK4), the time of solidification (4990 s) | Σ V_k T_k (heat), the range of the temperature, the isothermal run | the ratio of the flow lengths (temperature mode and isothermal control) |

Configuration 10, crosswind numerical diffusion of the heat (temperature mode, no cooling; the values are for the check):

| Item | 0° (`param_x0.txt`, `param_x0m.txt`) | 45° (`param_x45.txt`, `param_x45m.txt`) |
|---|---|---|
| Domain and grid | 300 m × 100 m (60 × 20), Δx = 5 m, slope 0.1 along x (`wrk_zx0.txt`) | 300 m × 300 m (60 × 60), Δx = 5 m, slope 0.1 along (1,1) (`wrk_zx45.txt`) |
| Effusion | 5 m³/s each at 1150 °C from j = 1–10 and at 1050 °C from j = 11–20 of column i = 3, for 3000 s | 9.9 m³/s each at 1150 °C from the 14 cells with i < j and at 1050 °C from the 14 cells with i > j on the anti-diagonal i + j = 33, for 3000 s |
| Flow | a uniform sheet flow of q = 0.1 m²/s per width (η = 2e4 Pa·s, τ_y = 0, temperature sensitivity 0: 1.33 m thick, 0.075 m/s); no cooling | same |
| Heat advection | first-order upwind (`x0`) and MUSCL (`x0m`) | first-order upwind (`x45`) and MUSCL (`x45m`) |
| Compared with | the temperatures on both sides of the boundary (they stay at the eruption temperatures) | the crosswind diffusivity from the spreading of the boundary width σ (0.354·u·Δx for first-order upwind by the modified equation) |
| Configuration 10d (8-neighbour 9-point stencil, d = 1/3) | the same input with first-order upwind (`x0d`) and MUSCL (`x0dm`); the crosswind diffusivity from σ along the rows across the check columns i = 10, 20, 30 (first-order theory 0.167·u·Δx) | the same input with first-order upwind (`x45d`) and MUSCL (`x45dm`); from σ on the anti-diagonals (theory 0.236·u·Δx) |

Configuration 11, conveyance of valleys (8-neighbour 9-point stencil; values for the check):

| Item | 0° (`param_ch0w1.txt`, `param_ch0w3.txt`) | 45° (`param_ch45w1.txt`, `param_ch45w3.txt`, `param_ch45w3q.txt`) |
|---|---|---|
| Domain and grid | 500 m × 55 m (100 × 11), Δx = 5 m, slope 0.1 in x. Both sides of the valley in row j = 6 (one cell) or 5–7 (three cells) are 20 m higher (`wrk_zch0w*.txt`) | 360 m × 360 m (72 × 72), Δx = 5 m, slope 0.1 in the (1,1) direction. Both sides of the band \|i − j\| = 0 (one line) or ≤ 1 (three lines) are 20 m higher (`wrk_zch45w*.txt`) |
| Eruption | from the valley cells of column i = 3, the discharge of a uniform flow 1 m thick, Q = W × 0.8493 m²/s (one cell 4.25 m³/s, three cells 12.74 m³/s), for 500 s | likewise from the band cells with i + j = 8 and 9 (W = number of lines × Δx/√2; one line 3.00 m³/s, three lines 9.01 m³/s) |
| Flow | Newtonian (η = 1e3 Pa·s, τ_y = 0). `lv_diagratio = 1/3` | the same (`ch45w3q` is the control with `lv_diagratio = 0`) |
| Compared with | k from the mean thickness h of the valley cells of columns i = 40–60 | k from the mean thickness h of the band cells with i + j = 64–80 |

| File | Contents |
|---|---|
| `make_init.py` / `make_init.py wall` / `cool` / `run` / `runnz` / `x0`, `x45` / `x0c1`, `x0c2`, `x45c1`, `x45c2` / `ch0w1`, `ch0w3`, `ch45w1`, `ch45w3` / `ch0w1c` etc. | `zinit.txt` (uniform slope) / `zwall.txt` (flat floor and a 10 m step) / `cool_cells.txt` (the vent of all cells of configuration 7) / `zrun.txt` (the slope tanθ = 0.1 of configuration 9) / `wrk_zrunnz.txt` (the slope of configuration 9n with a perturbation of ±1 mm; a linear congruential generator, the same with any Python version) / `wrk_zx0.txt`, `wrk_zx45.txt` (the slopes of configuration 10) / `wrk_x0c*.txt`, `wrk_x45c*.txt` (the vents of configuration 10) / `wrk_zch*.txt` (the valleys of configuration 11) / `wrk_ch*c.txt` (the vents of configuration 11; wrk_* files are not tracked by git and are written by Run.sh and Run_MPI.sh) |
| `Check_lava.py <save> huppert\|bingham\|dome\|wall\|bury\|cool\|adv\|run\|runnz\|heat\|xdiff\|xdiff8\|chan` | Configuration 1: (1) ledger Σhl·A = V_in, (2) area-equivalent radius of thickness 1 cm or more within 10% of r_N, (3) r(tt)/r(tt/2) within 5% of √2. Configuration 2: (1) ledger Σhl + Σdz = V_in (solidification is an internal transfer to z), (2) hl + dz in the check window (i = 15–35) within 20% of h∞ and CV < threshold, (3) solidified fraction > 0.7. Configuration 4: (1) ledger Σhl·A = V_in, (2) the ratio of the area-equivalent radii of the sectors along the grid axes (±22.5°) and along the diagonals (±22.5°) within 5% of 1, (3) center thickness within 5% of H and area-equivalent radius within 5% of R, RMS error of the profile for r < R < 5% of H. Configuration 5: (1) ledger Σhl + Σdz = V_in, (2) solidified fraction > 0.999, (3) in every row of the column touching the wall (i = 30), hl = 0 and dz above half the maximum thickness. Configuration 6: (1) lava ledger, (2) sd = 0 and hg = 0 in every cell with solidified lava, sd = 1 m in the other cells, (3) Σ(h + hrs + hg) within 1e-9 (relative) of the initial surface water. Configuration 7 (`cool`; the third argument is the screen log): (1) the output Tl is uniform over all cells and within 2e-4 °C of the backward-Euler recursion, (2) the temperature drop within 1% (relative) of the exact solution, (3) still molten before the update at which the recursion reaches T ≤ the solidification temperature and all cells solidified after it, (4) the residual of the heat ledger within 1e-12 (relative) and its breakdown matching the recursion. Configuration 8 (`adv`): (1) lava ledger, (2) Σhl·Tl·A within 1e-9 (relative) of Σ V_k T_k and the residual on the screen, (3) 1050 ≤ Tl ≤ 1150 in every cell with lava, and a mixed zone exists. Configuration 9 (`run`; reads the saves of the four runs): (1) ledger and complete solidification, (2) residual of the heat ledger, (3) ratio of the flow lengths of the temperature mode L(4Q)/L(Q) > 1.5, (4) ratio of the isothermal control 1 ± 0.1. Configuration 9r (`heat`): residual of the heat ledger of the restarted run. Configuration 10 (`xdiff`; reads the saves of the four runs): (1) ledgers and conservation of heat of the four runs, (2) every cell of columns i = 10, 20 and 30 at 0° within 1e-9 °C of the eruption temperature of its side (both first-order upwind and MUSCL), (3) at 45° with first-order upwind, the growth of the square of the boundary width σ = √π ∫θ(1 − θ) dn, from the temperature θ on the anti-diagonals i + j = 37, 43, 53 and 63, gives D⊥ = u Δσ²/(2Δs) within 15% (relative) of (√2/4)·u·Δx, (4) D⊥ of MUSCL at 45° below 0.25 times first order, and 1050 ≤ Tl ≤ 1150 in every cell with lava. Configuration 4' (`dome`): the same as configuration 4. Configuration 9n (`runnz`; reads the saves of the two runs): (1) ledger and complete solidification, (2) residual of the heat ledger, (3) L(4Q)/L(Q) > 1.5. Configuration 10d (`xdiff8`): (1) ledgers and conservation of heat of the four runs, (2) D⊥ of first-order upwind at 0° and 45° within 15% (relative) of (1 − d)F(φ) + d√2 F(φ − 45°), (3) D⊥ of MUSCL below 0.25 times first order and the range of the temperature. Configuration 11 (`chan`; reads the saves of the five runs): (1) ledgers of the five runs, (2) \|k − 1\| < 0.01 for one and three cells at 0°, (3) \|k − 1\| < 0.02 for one line at 45°, (4) \|k − 1\| < 0.1 for three lines at 45° and k < 0.8 for the 4-neighbour control |
| `Fig.py` | The figure `en/figs/lava.png` below (`python3 Fig.py en`; `figs/lava.png` is the Japanese version) |

## Running

```bash
make
./Run.sh          # configuration 1 → Check → configuration 2 → Check → equivalence check of configuration 3 → configurations 4, 4', 5–9, 9r, 9n, 10, 10d and 11 → Check (about 1.5 minutes on one thread)
./Run_MPI.sh 4    # MPI. state.dat and lavaflow.dat (and lavaflow_temp.dat) are byte-identical to the serial run (-O2 strict math)
python3 Fig.py en # en/figs/lava.png
```

## Figures

![Lava flow](figs/lava.png)

Top left: the lava thickness of configuration 1 after 600 s. It spreads
axisymmetrically from the center. Top center: the growth of the area-equivalent
radius. The computation (●) follows the √t law of the similarity solution,
and the growth law r(tt)/r(tt/2) agrees with √2 to 0.1%. The absolute value
of the radius is 12.6 m (+3.7%) by the counting method of Check_lava
(thickness 1 cm or more, as in the figure). Counting down to a thin fringe of
1e-6 m gives 13.5 m (+10.9%); the difference is the treatment of the numerical
precursor film at the front, which the similarity solution does not have
(including the lag of the front due to the edge-averaged thickness; on 4
neighbours 12.5 m (+2.8%) and 13.2 m (+8.5%); the check counts at 1 cm;
developer.md §96).
Top right: the final thickness of configuration 2 (row average). Downstream of
the vents at x = 6–40 m, hl + dz forms a flat plateau of 0.42 m, agreeing
with the analytical stopping thickness 0.3925 m to 7.1%, and the whole
amount has solidified (dz = hl + dz).
Bottom left: profiles of the shape at rest of configuration 4. The profiles
along the grid axis (●) and along the diagonal (■) overlap and follow the
analytic plastic dome (black) (center thickness +1.3%, area-equivalent
radius −1.3%). With the scheme before the fix, which judged the yield on the
gradient across the edge only, the front along the diagonal stopped at 0.74
times the distance along the grid axis, and the shape at rest was a diamond
elongated along the grid axes (developer.md §51.4). Bottom center: the same
shape at rest seen from above; it is a circle of the analytic radius (dashed).
Bottom right: the final topography of configuration 5 (row average). The lava
ponded against the wall has solidified up to the column touching the wall
(dz 0.97 m at the wall). With the stop criterion before the fix, which counted
inflow edges, the column touching the wall stayed molten (hl 0.98 m, 13% of
the erupted volume) (developer.md §51.5).

## Findings

| Check | Computed | Result |
|---|---|---|
| Configuration 1 (1) ledger Σhl·A − V_in | −5.7e-14 m³ (V_in = 300 m³) | PASS |
| Configuration 1 (2) area-equivalent radius (thickness 1 cm or more) | 12.58 m (r_N 12.13 m, +3.7%, tolerance 10%) | PASS |
| Configuration 1 (3) growth law r(tt)/r(tt/2) | 1.413 (0.1% from √2) | PASS |
| Configuration 2 (1) ledger (Σhl + Σdz)·A − V_in | 1.2e-11 m³ (V_in = 149.75 m³) | PASS |
| Configuration 2 (2) stopping thickness <hl + dz> | 0.4202 m (h∞ 0.3925, +7.1%, tolerance 20%), CV 0.001 | PASS |
| Configuration 2 (3) solidified fraction | 1.000, max dz 0.43 m | PASS |
| Configuration 3 equivalence of the defaults | save and Log byte-identical, 2 "(default)" lines | PASS |
| Configuration 4 (1) ledger Σhl·A − V_in | 4.5e-13 m³ (V_in = 1798 m³) | PASS |
| Configuration 4 (2) ratio of the sector area-equivalent radii (diagonal / grid axis) | 17.04 m / 16.74 m = 1.018 (tolerance 1 ± 0.05) | PASS |
| Configuration 4 (3) analytic plastic dome | center thickness 3.714 m (H 3.665 m, +1.3%), area-equivalent radius 16.90 m (R 17.11 m, −1.3%), profile RMS 0.076 m (2.1% of H) | PASS |
| Configuration 4' (1)–(3) 4-neighbour control | ledger −2.3e-13 m³, ratio of the area-equivalent radii 16.96/16.74 m = 1.014, center thickness 3.710 m (+1.2%), area-equivalent radius 16.86 m (−1.5%), profile RMS 0.076 m (2.1% of H) | PASS |
| Configuration 5 (1) ledger (Σhl + Σdz)·A − V_in | −1.9e-13 m³ (V_in = 59.9 m³) | PASS |
| Configuration 5 (2) solidified fraction | 1.0000 (no lava left) | PASS |
| Configuration 5 (3) column touching the wall | hl = 0 in every row, min dz 0.966 m (max dz 1.084 m) | PASS |
| Configuration 6 (1) lava ledger | −2.0e-13 m³ (V_in = 60 m³) | PASS |
| Configuration 6 (2) burial of the soil layer | sd = 0 and hg = 0 in the 80 cells under the lava, sd = 1 m elsewhere (soil buried 80 m³, groundwater moved to the surface 5.65 m³) | PASS |
| Configuration 6 (3) water conservation Σ(h + hrs + hg) − initial | −4.1e-13 m³ (initial 16 m³) | PASS |
| Configuration 7 (1) difference between the output Tl and the backward-Euler recursion | max 4.2e-5 °C (uniform over all cells) | PASS |
| Configuration 7 (2) difference of the temperature drop from the exact solution | 9.4e-4 relative (tolerance 1%) | PASS |
| Configuration 7 (3) solidification by temperature | all cells solidify at the 499th update (t = 4990 s, 799.60 °C), dz = 1 m | PASS |
| Configuration 7 (4) residual of the heat ledger | −2.9e-16 (relative to the erupted heat); erupted 1.0525e11 J = radiated 1.8562e10 + convected 1.0180e10 + solidified 7.6505e10 J | PASS |
| Configuration 7m air temperature from fn_meteo | save byte-identical to configuration 7 | PASS |
| Configuration 8 (1) ledger Σhl·A − V_in | −1.1e-13 m³ (V_in = 599.5 m³) | PASS |
| Configuration 8 (2) conservation of heat | Σhl·Tl·A = Σ V_k T_k to −1.8e-16 relative; residual on the screen −1.2e-15 | PASS |
| Configuration 8 (3) range of the temperature | 1050.000000–1150.000000 °C, mixed zone of 53 cells | PASS |
| Configuration 8' agreement with the isothermal run | lavaflow.dat and state.dat byte-identical | PASS |
| Configuration 9 (1)(2) ledger and heat ledger | machine precision and complete solidification in all four runs, residual of the heat ledger ≤ 4.7e-16 | PASS |
| Configuration 9 (3) flow length in the temperature mode | 75 m (2 m³/s) → 155 m (8 m³/s), ratio 2.07 (tolerance > 1.5) | PASS |
| Configuration 9 (4) flow length of the isothermal control | 120 m → 120 m, ratio 1.00 (tolerance 1 ± 0.1) | PASS |
| Configuration 9n (1)–(3) perturbed slope | machine precision and complete solidification in both runs, residual of the heat ledger ≤ 1.2e-16, length 75 m (2 m³/s) → 155 m (8 m³/s), ratio 2.07 (tolerance > 1.5). Largest row-averaged thickness of the Q flow 2.50 m (2.46–2.57 m across the rows in that column) | PASS |
| Configuration 9r restart round trip | the three save files byte-identical to the uninterrupted run, residual of the heat ledger −6.32e-16 | PASS |
| Configuration 10 (1) ledgers and conservation of heat | in all four runs Σhl·A − V_in ≤ 5.1e-11 m³ (V_in 30,000 and 59,400 m³), heat ≤ 1.4e-15 (relative), residual on the screen ≤ 3.7e-13 | PASS |
| Configuration 10 (2) boundary at 0° | with both first-order upwind and MUSCL both sides of the boundary stay at the eruption temperatures (difference ≤ 4.5e-13 °C); the MUSCL save is byte-identical to first-order upwind | PASS |
| Configuration 10 (3) first-order upwind at 45° | σ = 6.85, 11.04, 15.73, 19.37 m (s = 14, 35, 71, 106 m), D⊥ = 0.357·u·Δx (theory 0.354, +1.0%; tolerance 15%) | PASS |
| Configuration 10 (4) MUSCL at 45° | σ = 3.83, 5.02, 6.06, 6.75 m, D⊥ = 0.034·u·Δx (0.09 times first order; tolerance < 0.25), Tl = 1050–1150 °C | PASS |
| Configuration 10d (1) ledger and conservation of heat | Σhl·A − V_in ≤ 5.1e-11 m³ in all four runs, heat relative ≤ 1.0e-15, residual on the screen ≤ 3.8e-13 | PASS |
| Configuration 10d (2) first-order upwind on 8 neighbours | D⊥ = 0.1667·u·Δx at 0° (theory 0.1667, +0.0%), 0.2376 at 45° (theory 0.2357, +0.8%; tolerance 15%) | PASS |
| Configuration 10d (3) MUSCL on 8 neighbours | 0.0252 at 0° (0.15 times first order), 0.0282 at 45° (0.12 times) (tolerance < 0.25), Tl = 1050–1150 °C | PASS |
| Configuration 11 (1) ledger | Σhl·A − V_in ≤ 2.7e-12 m³ in all five runs | PASS |
| Configuration 11 (2) 0° | k = 1.0000 (one cell), 1.0000 (three cells) (tolerance 1 ± 0.01) | PASS |
| Configuration 11 (3) one line at 45° | k = 1.0000 (tolerance 1 ± 0.02; no flow on 4 neighbours) | PASS |
| Configuration 11 (4) three lines at 45° | k = 1.0650 (tolerance 1 ± 0.1), 4-neighbour control k = 0.6667 (tolerance < 0.8) | PASS |

- The +7% of the stopping thickness includes the upward bias
  h∞ + √(v_sol h/(coef (2h + h₀) S)) from the cutoff by the stop detection
  `lv_vsol` (§51.3). The approach to stopping is slow, and the check is
  built with "a viscosity for which the drainage reaches the vicinity of h∞
  within the check time" (with η = 1e4 the bias is 29% at 900 s = a
  guideline for parameter selection).
- The ledger closes to machine precision by the exact addition of the
  injection and the edge-antisymmetric diffusion. The restart round trip
  (300 s save → restore → 600 s) is also byte-identical (and so is
  3000 s save → restore → 6000 s for configuration 4).
- Configuration 4 is a detector of distortion by the grid orientation. Run
  with the scheme before the fix (yield and stopping judged on the gradient
  across the edge only), it FAILs with a sector radius ratio of 0.860, a
  center thickness of +9.5%, an area-equivalent radius of −5.1% and a
  profile RMS of 12.5%. The viscosity does not affect the shape at rest, so
  a value that stops within the check time (η = 1e6 Pa·s) is used (the
  center thickness differs by 1.6% between 3000 s and 6000 s).
- Configurations 1 and 2 have byte-identical saves before and after the fix
  (2026-11-03): configuration 1 has τ_y = 0, and configuration 2 is uniform
  across the width, so the gradient along the edges is 0.
- Configuration 5 is a detector of the stop criterion. Run with the
  criterion before the fix, which counted inflow edges, it FAILs with a
  solidified fraction of 0.869 and hl 0.978 m at the wall. Apart from the
  wall, the deposit has the same shape before and after the fix. The saves
  of configurations 1–4 are also byte-identical before and after the fix of
  the stop criterion (§51.5).
- Configuration 6 is a detector of the burial of the soil layer. Before the
  fix, solidification only raised z, and sd = 1 m and groundwater storage
  (up to 0.059 m) remained in the 80 cells under the lava, so it FAILs. The
  lava deposit (z, hl) is byte-identical with and without the burial (only
  the soil and the water change). Configurations 1–5 use no soil layer, so
  their saves are byte-identical before and after the burial fix (§51.6).
  Configuration 6 is not in the figure.
- Configurations 7–9 check the temperature mode (developer.md §51.7). The
  backward Euler of configuration 7 is first-order accurate; with 10 s steps
  (the cooling time constant is about 80 minutes) the error of the temperature
  drop is 0.09%. Configuration 9 shows that in the isothermal mode the flow
  length is set by the volume and the yield stress and does not depend on the
  effusion rate (a uniform deposit at the stopping thickness 0.98 m), whereas
  in the temperature mode the flow at the lower effusion rate cools from its
  front and stops early, and the lava piles up behind it (largest row-averaged thickness 2.5 m; 3.5 m
  on 4 neighbours).
  Configurations 7–9 are not in the figure either.
- On 4 neighbours (the default before 2026-11-05) the flow of configuration 9
  is perfectly uniform across (all rows the same), and this solution is
  unstable. With a perturbation of ±1 mm in the bed, as in configuration 9n, a
  positive feedback (a hotter channel flows faster and cools more slowly) splits
  the flow into channels (deposit thickness varying by ±15–25% across the rows),
  and the length of the Q flow grows from 50 m to 85 m. On the default 8
  neighbours the asymmetry of the rows at the walls acts as a perturbation, so
  configuration 9 splits into channels as well, and configurations 9 and 9n give
  the same lengths of 75 m and 155 m. The length of the perturbed solution is
  75–85 m with first-order upwind or MUSCL, 4 or 8 neighbours, and cells of 5 to
  1.25 m (the correction in developer.md §94). The check of configuration 9
  (length ratio > 1.5) holds for every one of these solutions.
- The saves, field outputs and Log.txt of configurations 1–6 are
  byte-identical before and after the addition of the temperature mode (the
  isothermal run allocates no temperature arrays and goes through the same
  code).
- Configuration 10 is a detector of the numerical diffusion of the heat
  advection (developer.md §94). With 4-neighbour first-order upwind there is no
  crosswind diffusion for a flow along a grid axis, but at 45° the heat entering
  through both the x and the y edges averages the temperatures of the donors,
  and the boundary spreads with D⊥ = (Δx/2)(|u_x| sin²θ + |u_y| cos²θ) =
  0.354·u·Δx of the modified equation. MUSCL (`f_lvtemp_scheme = 3`) removes the
  leading term; what remains is where the limiter falls back to first order at
  both ends of the boundary. At 0° the temperature is constant along the flow
  and stepwise across it, so the reconstruction does not act, and the result is
  byte-identical to first-order upwind. The saves (except the line with the
  creation time in save_info.txt), field outputs and Log.txt of configurations
  1–9 were byte-identical before and after the addition of MUSCL (the default
  was then 1). Making 3 the default (2026-11-05; the flow was then on 4 neighbours by
  default) changes configuration 8, where
  lava flows in the temperature mode (only the temperature field; with no
  cooling and zero temperature sensitivity the deposit does not change), and
  configurations 9 and 9r (the shape of the deposit and the flow length; for
  the flow at effusion rate Q 55 → 50 m, ratio 2.64 → 2.90). The isothermal
  configurations 1–6 and the isothermal controls of configuration 9, the
  configuration 7 that does not flow, and x0 and x45 of configuration 10, which
  give first-order upwind explicitly, do not change. Configuration 10 is not in
  the figure. Configuration 10d computes the same flows on the 8-neighbour
  9-point stencil; the diagonal edges carry heat too, so first-order upwind
  diffuses across the flow even at 0° (d√2 F(−45°) = 0.167·u·Δx). The formula
  is this guide's own derivation, of the same form as for first-order upwind of
  the surface water on the ENC grid, and the measurements at 0° and 45° agree
  with it within 1%. MUSCL gives 0.12–0.15 times first order at both 0° and
  45°, nearly the same in every direction.
- Configuration 11 checks the 8-neighbour 9-point stencil of the flow
  (`lv_diagratio`; default 1/3; developer.md §96). On 4
  neighbours a diagonal valley one cell wide, whose cells touch only at
  corners, does not flow (in a trial the lava piled up 19.7 m at the vent
  and the subcycles exceeded 1.2 million, so it is not in the check). A band
  of three lines flows only through the zigzag of the axis edges, k = 2/3
  (`ch45w3q`). With 8 neighbours the blocked diagonal shares are reassigned,
  according to the lava thickness, to the axis edges, and in a diagonal valley
  whose axis neighbours are blocked, to the diagonal edges, so a valley at 0°
  keeps the conveyance of 4 neighbours (k = 1) and one line at 45° also gives
  k = 1. The +6.5% for three lines at 45° is an excess from the axis edges at
  the edges of the band receiving the shares of blocked diagonals that cross
  the valley; for uniform thickness it is 1 + d/6 (+5.6% for d = 1/3; the
  derivation is in developer.md §96). For a band of five lines (trial) it
  drops to +4.0%.
- The saves (except the line with the creation time in save_info.txt), field
  outputs and Log.txt of configurations 1–10 were byte-identical before and
  after the addition of the 8 neighbours (the default was then 0; the code of
  the 4-neighbour path is unchanged). Making 1/3 the default (2026-11-05)
  changes the values of configurations 1, 2, 4–6, 8, 9, 9r and 9n, whose flow
  follows the default (the findings above are the values for 1/3). The main
  differences from 4 neighbours are the area-equivalent radius of configuration
  1, 12.48 → 12.58 m (+2.8 → +3.7%), the sector ratio of configuration 4,
  1.014 → 1.018, the flow lengths of configuration 9, 50 and 145 m → 75 and
  155 m (ratio 2.90 → 2.07), those of configuration 9n, 85 and 150 m → 75 and
  155 m (ratio 1.76 → 2.07), and the mixed zone of configuration 8, 21 → 53
  cells (the diagonal edges carry heat too). Configurations 4', 10 and
  `ch45w3q` of 11, which give 4 neighbours explicitly, and configuration 7,
  which does not flow, do not change (the save of configuration 4' is
  byte-identical to the former configuration 4).

## Related documents

- [docs/users_guide/lavaflow.md](../../../docs/en/users_guide/lavaflow.md) — `&list_lavaflow` (viscosity, yield stress, solidification, vents, temperature mode)
- developer.md §51 (implementation and verification record), §66 (defaults) (in Japanese)
