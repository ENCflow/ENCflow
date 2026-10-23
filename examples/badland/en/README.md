# examples/badland — valleys carved into a plateau and steep cliff (badland-type landform evolution)

> English mirror of examples/badland/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This example follows, in a single run, the formation and growth of valleys
when rainfall is applied continuously to a terrain in which a plateau of
highly permeable pyroclastic material drops into the sea at a sea cliff
(typical of the margins of the pyroclastic cones in southern Niijima). All
the rainfall infiltrates and **surface runoff stays zero**; dry-slope erosion
`f_splash` (raindrops + the hollow feedback of subgrid rills;
[description](../../../docs/en/users_guide/sediment.md#6-dry-slope-erosion-f_splash))
self-organizes valleys out of the white noise at the cliff margin and grows
them into deep valleys with sharp ridges. The valley spacing is set by the
correlation length of the curvature `spl_lc` (the collection scale of the
subgrid rills), and the sea level is given as the erosion base level
`spl_zbase` (developer.md §48.3).

| Case | Files | Contents |
|---|---|---|
| Main case | param.txt | 120 × 240 m, plateau 30 m high and 60 m wide, 56° cliff, spl_lc = 2 m. Long-term evolution to T_geo = 9×10⁶ s |
| Correlation-length series | param_lc1 / lc2 / lc4.txt | 100 × 240 m, plateau 15 m. spl_lc = 1 / 2 / 4 m (valley spacing ∝ ℓ) |
| Grid-κ control | param_grid.txt | As above with spl_lc = 0 (the evaluation of the old version; the spacing sticks to the grid) |
| Grid convergence | param_lc2_dx05 / dx2.txt | spl_lc = 2 m at Δx = 0.5 / 2 m (same terrain and noise as param_lc2) |

## Running

```
make                                   # link to ../../bin/encflow
python3 make_terrain.py main           # z_main.txt, sw_main.txt
python3 make_terrain.py sweep          # z_sweep.txt, sw_sweep.txt (for the series and the control)
python3 make_terrain.py sweep --dx 0.5 # z_sweep05.txt (for grid convergence)
python3 make_terrain.py sweep --dx 2   # z_sweep2.txt
./encflow param.txt                    # main case (about 1 min; Z in result/ every 30 min = T_geo 9×10⁵ s)
for p in param_lc1 param_lc2 param_lc4 param_grid param_lc2_dx2 param_lc2_dx05; do ./encflow $p.txt; done   # 10 s to 3 min each
python3 plot_results.py                # 4 figures in figs/ + tables
```

## Key settings

- **Terrain** (make_terrain.py): a plateau (z = h_p) + cliff (tanθ = 1.5)
  drops into the sea (sea mask `fn_sw`) at z ≤ 0. **White noise** (uniform
  ±0.5 m, fixed seed, on a 1 m reference grid) is applied at the position of
  the cliff margin so that no particular wavelength is introduced. The same
  margin shape is seen when the grid spacing is changed (for the
  grid-convergence comparison).
- **Rainfall and infiltration**: a uniform 10 mm/h is applied continuously,
  and the Green-Ampt infiltration capacity of 36 mm/h exceeds it, so no
  surface runoff occurs (S_surf on the screen is always 0). Erosion is
  carried by f_splash alone, and the detached sediment is exported out of the
  system to the sea (the total is printed at the end).
- **Erosion law**: `spl_kt = 0.05`, `spl_h = 1.5`, hollow amplification
  `spl_cb = 32`, raindrop term `spl_kr = 0.0002`. The curvature is taken from
  z smoothed over the correlation length `spl_lc` (m). Diffusion terms such
  as creep are not mechanical models and are not used (they are not needed
  to select the spacing. The initial white noise does not decay and remains
  neutrally, but it merely fails to grow, and the valleys of the selected
  wavelength grow exponentially and cover it).
- **Base level**: `spl_zbase = 0` (sea level). Valley floors do not drop
  below the sea level. The soil thickness `sd0` is made sufficiently larger
  than the cliff height (as the soil thickness approaches 0, the groundwater
  capacity falls below the storage and water spills onto the surface,
  breaking the no-runoff premise. This is why the base level is given by
  spl_zbase rather than by sd).
- **Time**: dt = 2 s, landform update every 2 s × morfac 500 → the landform
  time T_geo is 500 times the real time. The 5 hours of the main case are
  T_geo = 9×10⁶ s (104 days of 10 mm/h rain). `spl_dzmax = 0.2` is the cap
  per update (a safety valve) and acts on some cells in the stage where the
  valley heads retreat fastest ("Notes on interpretation" below).

## Result 1: main case (from white noise to deep valleys and sharp ridges)

![maps](../figs/main_maps.png)

Top: evolution of the terrain (T_geo = 0, 1.8×10⁶, 3.6×10⁶, 9×10⁶ s). From a
cliff margin holding nothing but white noise, valleys spaced a little over
10 m first self-organize on the cliff face (1.8×10⁶ s), the valley heads bite
into the plateau as amphitheaters (3.6×10⁶ s), and finally the plateau is
dismembered into **long parallel ridges** like the teeth of a comb, with the
valley floors reaching the sea level (base level) (9×10⁶ s). Bottom left:
evolution of a cross-section through the cliff-face zone (the valley floors
reach the base level and the ridges remain thin and high). Bottom right:
longitudinal profiles through a valley floor and a ridge crest.

![series](../figs/main_series.png)

Time series. The relief (the standard deviation in the y direction in the
cliff-face zone) increases as the valleys deepen and decreases as the plateau
is dismembered. The wavelength of the spectral centroid of the landform change
Δz and the valley spacing are set at ≈ 5–6 ℓ in the linear stage (theory
λ* = 4.4 ℓ), and the valley spacing then stabilizes at around 12 m. The
maximum incision reaches the base level (30 m), and the valley heads retreat
from the plateau margin at a constant speed.

![features](../figs/main_features.png)

Badland-like features. Left: the slope distribution changes from the initial
two values (plateau 0, cliff 1.5) to a continuous distribution of sharp
ridges and valley walls. Center: the sign of the curvature (blue = convex =
ridge, red = concave = valley). Center right: D8 drainage area of the final
terrain — the valleys form a parallel dendritic network perpendicular to the
plateau margin. Right: the y-direction curvature of the ridge crests (local
maxima of the columns in the cliff-face zone). The more negative, the sharper
the ridge. The ridges are sharp crests 2–4 cells wide, and their tops are
lowered by erosion with the gradient of both faces (the effect of
`spl_sgrad = 1` (default), which evaluates the slope by steepest descent.
With a central difference the slope cancels at the crest, so one-cell-wide
ridges never erode and become immortal; developer.md §48.4).

| Quantity | Initial | Final (T_geo = 9×10⁶ s) |
|---|---|---|
| y-direction relief of the cliff-face zone (m) | 0.44 | 5.50 (maximum 7.5 at T_geo 4.5×10⁶ s) |
| Valley spacing (m) (prominence of Δz ≥ 1 m) | – | 1.8×10⁶ s: 13.6 ± 8.1 (15 valleys / 240 m); final: 12.2 ± 6.8 (18 valleys) |
| Wavelength of the spectral centroid of Δz (m) | – | 1.8×10⁶ s: 11.5; 3.6×10⁶ s: 14.6; final: 12.4 |
| Maximum incision / mean lowering of the cliff-face zone (m) | – | 29.0 / 18.0 |
| Position x of the valley heads (m) (plateau margin at 60 m) | 60.5 | 12.5 (retreat 48 m; nearly constant speed ≈ 7 m / 10⁶ s after T_geo 3.6×10⁶ s) |
| Ridges (local maxima of the columns in the cliff-face zone): median width / fraction one cell wide / median height | – | 3 cells / 0 % / 12 m (1 cell / 56 % / 23 m with the central-difference slope evaluation) |
| y-direction curvature of the ridges (1/m): median / minimum | – | −4.2 / −16.5 |
| Fraction of land cells with slope > 1.0 | 0.24 | 0.34 |
| Eroded volume Σ(z₀ − z)Δx² (m³) | – | about 2.7×10⁵ |
| Cumulative number of cells clipped by spl_dzmax | – | 3.8×10⁴ (2.9×10⁶ with the central difference) |

The table is output by `plot_results.py` (the values above are for
spl_dzmax = 0.2).

## Result 2: what sets the valley spacing

![spacing](../figs/spacing.png)

Top: terrain with the grid κ (spl_lc = 0) and with spl_lc = 1 / 2 / 4 m (at
the time the relief of the cliff-face zone first exceeds 2 m. The larger ℓ,
the slower the growth, so the growth stage is aligned instead of the time).
Bottom left: the spacing-selection rule (the centroid wavelength and valley
spacing of Δz at T_geo = 1.8×10⁶ s and at the time the relief reaches 2 m vs
ℓ. The grey line is the linear theory λ* = 4.4 ℓ). Bottom center: grid
convergence for spl_lc = 2 m (Δx = 0.5 / 1 / 2 m). Bottom right: terrain at
Δx = 0.5 m and 2 m (T_geo = 3.6×10⁶ s).

| Case | spl_lc (m) | Δx (m) | T_geo = 1.8×10⁶ s: centroid wavelength of Δz / valley spacing (m) / mean lowering (m) | At relief 2 m (T_geo): centroid wavelength / valley spacing (m) / number of valleys / mean lowering (m) | Final: relief (m) / maximum incision / mean lowering (m) / valley-head x (m) |
|---|---|---|---|---|---|
| param_grid | 0 | 1 | 3.3 / 3.5 / 7.5 | (9×10⁵ s) 3.4 / 3.5 / 66 / 4.9 | 1.02 / 15.0 / 12.5 / 0.5 (cuts through the plateau) |
| param_lc1 | 1 | 1 | 6.8 / 6.7 / 4.6 | (9×10⁵ s) 5.5 / 6.0 / 39 / 3.0 | 4.10 / 14.8 / 8.1 / 0.5 (cuts through the plateau) |
| param_lc2 | 2 | 1 | 10.1 / 14.5 / 3.0 | (2.7×10⁶ s) 10.9 / 13.2 / 17 / 4.6 | 3.74 / 14.5 / 6.5 / 30.5 |
| param_lc4 (to T_geo 2.2×10⁷ s) | 4 | 1 | 4.2 / – / 1.7 (not yet grown) | (2.2×10⁷ s) 22.5 / 24.5 / 4 / 10.3 | 0.53 / 14.7 / 10.3 / 30.5 |
| param_lc2_dx05 | 2 | 0.5 | 9.6 / 11.8 / 3.8 | (2.7×10⁶ s) 10.4 / 11.8 / 19 / 5.4 | 4.55 / 14.5 / 7.9 / 22.8 |
| param_lc2_dx2 | 2 | 2 | 10.8 / 15.4 / 2.0 | (5.4×10⁶ s) 12.8 / 15.1 / 14 / 4.9 | 1.96 / 13.9 / 4.9 / 37.0 |

The plateau margin is at x = 40 m; "final" is T_geo = 5.4×10⁶ s except for
param_lc4.

- **With the grid κ the spacing sticks to the grid** (3.4 m ≈ 3 Δx; a
  checkerboard relief stands up and an erosion front of 2Δx scale cuts
  through the plateau). The old version (2026-08) suppressed this with a weak
  creep and stated that "the wavelength selection is the ratio of spl_cb to
  creep_d", but on linearization both the hollow amplification and the
  diffusion scale with k², so the diffusion term only decides whether growth
  occurs (the sign) and does not select the spacing. Creep is not a
  mechanical model either, so this example does not use it (developer.md
  §48.3).
- **Giving spl_lc makes the spacing proportional to ℓ.** The centroid
  wavelength when the relief reaches 2 m is 5.5 / 10.9 / 22.5 m for
  ℓ = 1 / 2 / 4 m (≈ 5–6 ℓ; theory λ* = 4.4 ℓ; for ℓ = 4 m valley merging
  has progressed by the time it is reached). The larger ℓ, the slower the
  growth (σ_max ∝ 1/ℓ²); ℓ = 4 m takes about 8 times as long as 2 m.
- **Grid convergence**: solving ℓ = 2 m at Δx = 0.5 / 1 / 2 m, the centroid
  wavelength in the linear stage (T_geo = 1.8×10⁶ s) converges as
  9.6 / 10.1 / 10.8 m (the spacing-selection rule does not depend on the
  grid). The mean lowering is 3.8 / 3.0 / 2.0 m and finally 7.9 / 6.5 /
  4.9 m: the growth speed once the valleys are deep is faster the finer Δx,
  and it **does not fully converge**. The cause is the verticalization of
  the valley walls: this model has no upper bound on the slope and the valley
  walls steepen to one-cell-wide steps (S ≈ Δz/Δx), so the 99 % point of the
  slope is 11 / 6.5 / 3.3 at Δx = 0.5 / 1 / 2 m, inversely proportional to
  the grid spacing, and the erosion rate S^1.5 becomes larger the finer the
  grid (with the central-difference slope evaluation it was 17 / 8 / 4;
  steepest descent roughly halved the grid dependence). Use **ℓ/Δx ≥ 2** as
  a guide for comparing the linear-stage spacing and the initial incision,
  and use the speed of the deep-valley stage only for relative comparisons
  on a fixed grid ("Notes on interpretation").
- Changing the seed leaves the statistics of spacing and growth unchanged and
  only changes the positions of the valleys (Perron & Fagherazzi 2012:
  "the statistics are self-organized, the arrangement is set by the initial
  condition").

## Derived case: cliff collapse and export to the sea (param_rockfall.txt)

A derived case that superimposes collapse and talus `f_rockfall` (developer.md
§48.7; the windowed version with critical height H_c = 15 m, r_c = 8 m, talus
repose angle 35°, talus erodibility factor 0.1) on the main case. Cliffs
facing sea cells collapse into the sea and leave the system (the z of the sea
cells is unchanged; the limit of a sea cliff whose talus is removed by waves;
"rockfall exported to sea cells" at the end of the run).

```
./encflow param_rockfall.txt           # about 2 min
```

| Quantity (T_geo = 9×10⁶ s) | Main case | With rockfall |
|---|---|---|
| Export of dry erosion out of the system (solid m³) | 160,371 | 40,495 |
| Volume moved by rockfall (bulk m³, cumulative) / of which into the sea | – | 25,465 / 192 |
| Total talus (m³, final) | – | 754 |
| y-direction relief of the cliff-face zone (m) / mean lowering (m) | 1.68 / 13.2 | 2.09 / 6.9 |
| Position x of the valley heads (m) (plateau margin at 60 m) | 12.5 | 42.5 |

Rockfall collapses the 56° cliff face (drop > 15 m within the window) down to
the repose angle and the talus covers the face, so the driving force of dry
erosion (S^1.5 and hollow amplification) falls, the retreat of the valley heads
goes from 47.5 m to 17.5 m, and the export drops to a quarter. The collapse
into the sea is small, 192 m³, because in this terrain the foot of the cliff
meets the sea cells at the sea level (z = 0) and the step facing the sea is
small (placing a vertical sea cliff directly against sea cells would make the
export into the sea dominant). The rockfall parameters are not calibrated
values, and this example does not decide whether the cliffs of consolidated
pyroclastic material on Niijima are of the collapse type or the dry-erosion
type.

## Notes on interpretation

- Dry-slope erosion is a parameterization of a subgrid process, and the
  coefficients (spl_kt, spl_cb, spl_lc) are empirical values that assume
  calibration. To apply it to Niijima, the procedure is to back out
  ℓ ≈ spacing/5 from the measured valley spacing and to fit spl_kt and spl_cb
  to the incision rate (the cliff retreat rate).
- **The speed of the deep-valley stage depends on the grid spacing.** When
  the valley walls become vertical the slope S grows in inverse proportion to
  the grid spacing (grid convergence above), and κ̃ at the valley heads keeps
  increasing as depth/ℓ², so the product of Φ_B = 1 + c_b κ̃ and S^h becomes
  large at deep valley heads. The clipping by `spl_dzmax` is reduced to 1/70
  by the steepest-descent slope evaluation (3.8×10⁴ cells cumulative), and
  raising dzmax from 0.2 to 0.5 m does not change the time series (lowering
  it to 0.1 m leaves the valley-head position at 9×10⁶ s bound by the
  clipping, 12.5 → 29.5 m). The valley spacing, the shape (amphitheater →
  parallel ridges) and the initial deepening are robust; **use the retreat
  speed of the deep stage only for relative comparisons on a fixed grid**.
  Superimposing angle-of-repose avalanching `f_repose` (φ = 56.3°), which
  suppresses the verticalization of the walls, bounds the slope and reduces
  the grid dependence, but the collapsed sediment fills the valleys
  (conservative form), so the relief stays at 1–2 m and no deep valleys with
  sharp ridges form (consolidated pyroclastic material holds walls steeper
  than the repose angle, so it is not used in this example). A slope
  saturation (an upper bound on S) or a saturating form of Φ_B that matches
  the wall retreat of consolidated material is the next task
  (docs/splash_plan.md §8).
- Valley floors that have reached the sea level (base level) do not erode.
  Once the plateau is completely dismembered the terrain approaches a flat
  plain at the base level (the plateau disappears at T_geo = 1.8×10⁷ s).
- There is no surface runoff in this case, so the settings of the advection
  scheme of the shallow-water equations do not affect the results
  (bit-identical to the old version on the revised tree).

## Related

- [test/splash](../../../test/splash/en/README.md) (analytical verification; in Japanese), [test/splashslide](../../../test/splashslide/en/README.md) (cohesion contrast; in Japanese),
  [test/splashlc](../../../test/splashlc/en/README.md) (test of the wavelength selection; in Japanese)
- docs/splash_plan.md (formulation and record of trials; in Japanese), developer.md §48, §48.3 (in Japanese)
- [docs/users_guide/geomorph.md](../../../docs/en/users_guide/geomorph.md) — `f_splash`, `spl_*`
