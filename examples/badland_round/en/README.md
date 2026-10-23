# examples/badland_round — an experiment on the origin of badlands whose ridges do not sharpen and whose lower hills are the rounder

> English mirror of examples/badland_round/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This example reproduces the landform type seen in photographs (clusters of
banded hills like those of the Chinle Formation in the United States; the
ridges are rounded, and the lower the hill the more dome-like) by
superimposing ENCflow's **dry-slope erosion f_splash (advective, incising)**
and **hillslope creep f_creep (diffusive, rounding)** (the counterpart to the
"deep valleys with sharp ridges" of examples/badland). The inputs are only the
`param_d*.txt` in this directory and the generated terrain `z.txt`.

## Origin (hypothesis and the picture in the literature)

- Slopes of swelling clay (smectitic mudstone: the Chinle Formation, the
  Morrison Formation, the Chadron Formation of Badlands NP, etc.) develop a
  "popcorn" weathering crust through repeated wetting and drying, most of the
  rainwater is absorbed into it, and **almost no surface flow occurs**.
- Instead, sediment moves down the slope **diffusively** (with a flux
  proportional to the slope) through the swelling and shrinking of the crust
  and small mudflows. Diffusive processes create convex-up rounded crests
  (Gilbert's convex slope, Culling's linear diffusion).
- **Advective** processes by rills and raindrops (incising with a power of
  the slope and accelerating in hollows) create sharp ridges and
  straight-to-concave flanks (the sharp badlands of the Mancos Shale type).
- The ratio of the two defines a length scale L = D / (P k_t S^(h−1)). If a
  hill is smaller than L, the whole hill is dominated by diffusion and
  becomes a dome; if larger, only the crest is rounded and the flanks are
  incised while staying straight. **Lower (smaller) hills are rounder
  because this length scale is constant while the size of the hills
  differs** (the same form as the Péclet-number argument of Perron et al.).

## Setup

| Item | Value |
|---|---|
| Domain and grid | 176 × 80 m, Δx = 1 m |
| Initial terrain | Four conical hills on a plain (z = 0 = erosion base level): H₀ = 24 / 15 / 9 / 5 m, flanks tanθ = 0.8 (≈ 39°), white noise ±0.4 m on the hills (fixed seed) |
| Rainfall and infiltration | Continuous uniform 10 mm/h, Green-Ampt 36 mm/h → all infiltrates (zero surface flow) |
| Dry-slope erosion | f_splash: spl_kr = 2e-4, spl_kt = 0.05, spl_h = 1.5, spl_cb = 32 m, spl_lc = 2 m, spl_dzmax = 0.2, spl_zbase = 0 (same as examples/badland) |
| Creep | f_creep: D = 0 / 3e-7 / 1e-6 / 3e-6 m²/s (L ≈ 0 / 2.4 / 8 / 24 m) |
| Horizontal strata (control for the bands) | param_d0_strata / param_d1e-6_strata.txt: alternating hard and soft beds 1.5 m thick (factors 1 / 0.3, 16 layers) via `spl_strata`. param_d0_strata3 / d3e-7_strata3 / d1e-6_strata3.txt: 3 m thick (8 layers) |
| Time | dt = 2 s, landform update every 2 s × morfac 500. 24 h = T_geo 4.3e7 s (430 m of rain at 10 mm/h). Z output every 2 h |

```
make                                       # link to ../../bin/encflow
python3 make_terrain.py                    # z.txt
for d in d0 d3e-7 d1e-6 d3e-6; do ./encflow param_$d.txt > Screen_$d.log; done   # 2–4 min each (about 4 min if the four run in parallel)
python3 plot_results.py | tee analysis.txt # figs/*.png + tables (checks and per-hill indices)
for d in d0_strata d1e-6_strata; do ./encflow param_$d.txt > Screen_$d.log; done  # control with bands
python3 plot_results.py strata | tee analysis_strata.txt   # figs/*_strata.png
for d in d0_strata3 d3e-7_strata3 d1e-6_strata3; do ./encflow param_$d.txt > Screen_$d.log; done  # layer thickness 3 m
python3 plot_results.py strata3 | tee analysis_strata3.txt # figs/*_strata3.png
```

## Checks

| Case | Max S_surf (m) | Final S_grnd (m) | Cumulative rainfall (m) | Σ(z₀−z)Δx² (m³) | splash export (solid) (m³) | Ratio |
|---|---|---|---|---|---|---|
| D = 0 | 0 | 0.2400 | 0.2400 | 28169 | 16901 | 1.6667 |
| D = 3e-7 | 0 | 0.2400 | 0.2400 | 25503 | 15302 | 1.6667 |
| D = 1e-6 | 0 | 0.2400 | 0.2400 | 19725 | 11835 | 1.6667 |
| D = 3e-6 | 0 | 0.2400 | 0.2400 | 11531 | 6919 | 1.6667 |

Surface flow is zero throughout (S_surf = 0), and the groundwater storage
matches the cumulative rainfall 10 mm/h × 24 h = 0.24 m. The volume loss of
the terrain agrees to all digits with the splash export ledger ÷ (1 − porosity
0.4), which at the same time confirms that creep is conservative (does not
change the volume).

## Results

![maps](../figs/maps.png)

![sections](../figs/sections.png)

![radial](../figs/radial.png)

![rounding](../figs/rounding.png)

Per-hill indices at T_geo = 1.44e7 s (8 h) (from the azimuthally averaged
radial profiles):

| Case | Hill H₀ (m) | Crest height (m) | Maximum flank slope | Crest curvature −∂²z/∂r² (1/m) |
|---|---|---|---|---|
| D = 0 | 24 / 15 / 9 / 5 | 21.1 / 12.1 / 5.9 / 2.2 | 3.80 / 1.51 / 1.11 / 0.56 | 1.27 / 0.27 / 0.31 / 0.11 |
| D = 3e-7 | same | 19.4 / 10.4 / 4.3 / 1.3 | 1.67 / 1.25 / 0.61 / 0.20 | 0.19 / 0.21 / 0.19 / 0.07 |
| D = 1e-6 | same | 17.2 / 8.2 / 2.8 / 1.1 | 1.02 / 0.64 / 0.27 / 0.08 | 0.12 / 0.12 / 0.07 / 0.001 |
| D = 3e-6 | same | 13.4 / 5.1 / 2.1 / 1.0 | 0.57 / 0.27 / 0.09 / 0.05 | 0.065 / 0.042 / 0.001 / 0.006 |

- **No creep (advective only)**: the hills shrink while keeping sharp
  ridges, and the flanks in fact steepen (initial 0.8 → 1.1–3.8). After
  T_geo ≈ 1.4e7 s the hollow feedback lets gullies carve the hills radially
  and dismember them, leaving a spire at the center (sharp badlands of the
  Mancos type). The alignment of the gullies with the grid axes and
  diagonals is an artifact of grid anisotropy.
- **D = 1e-6 m²/s (L ≈ 8 m)**: the crests become convex-up rounded caps and
  the flanks become gentler (0.08–1.0). **The smaller the hill, the smaller
  the crest curvature (the rounder)**: the H₀ = 5 m hill becomes a flat dome
  as a whole, the 9 m hill a rounded mound, and the 24 m hill keeps a rounded
  crest with traces of gullies on its flanks — the type in the photographs,
  "rounded ridges, rounder further down (on the lower hills)". Gentle aprons
  of creep deposits form at the feet, and the hills join at their feet.
- **D = 3e-6 m²/s (L ≈ 24 m)**: all hills are domes (haystack type) from the
  start, and no gullies form.
- The lowering rate of the crest is initially faster the stronger the creep
  (it shaves the cap of the crest and carries it to the flanks), but since no
  dismemberment by gullies occurs it is slower in the later stage, and the
  hills survive longer.

## Adding bands (hard/soft contrast of horizontal strata)

The bands in the photographs (horizontal strata) are differences not only in
color but also in hardness. With `spl_strata` (a table of the bottom elevation
and the erodibility factor of each layer;
[geomorph.md](../../../docs/en/users_guide/geomorph.md)) we gave alternating
hard and soft beds 1.5 m thick (factors: soft 1, hard 0.3; 16 layers from
z = 0 to 24 m) and compared with and without strata for no creep (D = 0) and
for D = 1e-6 m²/s. The factor multiplies only the dry erosion E and not the
creep.

![maps_strata](../figs/maps_strata.png)

![sections_strata](../figs/sections_strata.png)

![radial_strata](../figs/radial_strata.png)

(The grey bands in the section plots are the hard layers. Drawn with
`python3 plot_results.py strata`.)

| Quantity | D = 0, no strata | D = 0, alternating beds | D = 1e-6, no strata | D = 1e-6, alternating beds |
|---|---|---|---|---|
| Export of dry erosion out of the system (solid m³, 24 h) | 16901 | 16650 | 11835 | 8145 |
| Crest height of the 24 m hill (m) (T_geo 1.44e7 / 4.3e7 s) | 21.1 / 1.5 | 22.0 / 5.9 | 17.2 / 7.9 | 17.8 / 12.4 |
| Maximum flank slope (T_geo 1.44e7 s, 24 m hill) | 3.80 | 1.77 | 1.02 | 0.82 |

- **No creep + alternating beds**: the flanks become **stepped**. The soft
  layers erode quickly down to the top of the hard layer below, a flat step
  (bench) forms there, and the face of the hard layer remains as a steep step
  (riser) (second row of the section plots; step height = layer thickness
  1.5 m). In plan view the contour lines gather at the tops of the hard
  layers into bands. Because the hard layers protect the edges of the hills,
  dismemberment by gullies is delayed (the crest of the 24 m hill is still
  22 m at 1.44e7 s), and in the end a plateau-like residual hill (mesa)
  capped by a hard layer remains.
- **Creep + alternating beds**: the steps are smoothed by creep into **bands
  of gentle undulation**, and the overall rounded shape (convex crest, gentle
  flanks) is kept (fourth row of the section plots; the slope eases slightly
  at the hard layers). The total erosion drops to 70 % of that without
  strata, and the hills stay higher (final crest height of the 24 m hill
  12.4 m, versus 7.9 m without strata). The "rounded hills with bands but no
  steps" in the photographs correspond to this combination: the hardness
  contrast creates the bands and the diffusive process erases the steps.
- Whether the hardness contrast shows up as steps is decided by the ratio of
  the step height (layer thickness) to the creep length scale L (the steps
  disappear if L ≫ layer thickness). Thicker layers or a smaller D bring out
  the steps (confirmed in the next section).

### Do steps appear with 3 m layers?

Doubling the layer thickness to 3 m (8 layers), we compared no creep,
D = 3e-7 (L ≈ 2.4 m < layer thickness) and D = 1e-6 (L ≈ 8 m > layer
thickness) (`python3 plot_results.py strata3`).

![sections_strata3](../figs/sections_strata3.png)

![radial_strata3](../figs/radial_strata3.png)

Step indices: on the azimuthally averaged profiles of the 24 m and 15 m hills,
the maximum/minimum ratio and the relative variation of the local slope over
the flank interval whose height above the foot is 15–85 % of the crest (large
if steps exist; T_geo = 1.44e7 s):

| Case | Layer thickness (m) | L (m) | S max/min (24 m hill) | Relative variation (24 m / 15 m) |
|---|---|---|---|---|
| No creep, alternating beds | 3 | 0 | 4.6 | 0.42 / 0.39 |
| D = 3e-7, alternating beds | 3 | 2.4 | 2.5 | 0.28 / 0.22 |
| D = 1e-6, no strata | – | 8 | 1.6 | 0.14 / 0.15 |
| D = 1e-6, alternating beds | 1.5 | 8 | 1.5 | 0.09 / 0.09 |
| D = 1e-6, alternating beds | 3 | 8 | 1.4 | 0.11 / 0.14 |

- **At D = 1e-6 (L ≈ 8 m) no steps appear even with 3 m layers.** The slope
  variation of the flanks is the same as without strata (relative variation
  0.11–0.14), and the profiles stay smoothly convex. The effect of the hard
  layers appears only in the total erosion (80 % of that without strata) and
  in how the hills survive.
- **At D = 3e-7 (L ≈ 2.4 m < layer thickness 3 m) steps appear.** Gentle
  steps (inflections of the slope) line up at the tops of the hard layers
  (z = 6, 12, 18 m), and the relative variation of 0.28 lies between no creep
  (0.42) and no strata (0.14). It is the 3 m steps of the no-creep case (flat
  benches where the soft layer eroded down to the top of the hard layer, and
  steep risers) rounded by creep.
- That is, whether steps are visible is decided by the ratio of the layer
  thickness to L (steps for layer thickness ≳ L, bands only for layer
  thickness ≪ L), and hills with bands but no steps, as in the photographs,
  indicate that the layers are thinner than the creep length scale (or that
  the hardness contrast is small).

## Notes on interpretation

- The coefficients are not calibrated values. The f_splash coefficients are
  those of examples/badland, and the creep D was chosen so that the length
  scale L spans the sizes of the hills (radius 6–30 m). The landform time is
  advanced with continuous rain at 10 mm/h, so converted to an arid region
  with 250 mm of annual precipitation the real time is about 350 times longer
  (T_geo 4.3e7 s ≈ 480 years), and D = 1e-6 m²/s is ≈ 0.1 m²/yr in real time
  (the upper side of the literature range 0.001–0.05 for soil creep; a
  reasonable order of magnitude for the active surface movement of swelling
  clay).
- f_creep is a linear diffusion that moves only z, not a mechanical model of
  swelling and shrinking (a known compromise in developer.md). The strata
  factor does not apply to creep, so the effect of hard layers throttling the
  sediment supply to creep is represented only through the factor on the
  dry-erosion side.
- The strata are horizontal (a function of elevation only). Tilted or folded
  layers cannot be represented.
- The alignment of the gullies with the grid axes and diagonals in the
  no-creep case is the anisotropy of the discretized cone and persists even
  with ±0.4 m of noise. It can be used to compare shapes (sharp ridges,
  steepening, dismemberment), but the number and orientation of the gullies
  are not physics.
- The speed of the deep stage of f_splash depends on the grid spacing (see
  the notes in examples/badland). This experiment is about comparing shapes;
  use the times for relative comparison.

## Related

- [examples/badland](../../badland/en/README.md) (deep valleys with sharp ridges on a plateau and steep cliff),
  [examples/badland_storm](../../badland_storm/en/README.md) (a cliff with surface flow only during heavy rain)
- [docs/users_guide/geomorph.md](../../../docs/en/users_guide/geomorph.md) — `f_splash`, `f_creep`;
  [sediment.md](../../../docs/en/users_guide/sediment.md) — equations and the basis of the defaults
- Use cases: [docs/users_guide/usecases.md](../../../docs/en/users_guide/usecases.md) "Valley formation on badlands and pyroclastic cones"
