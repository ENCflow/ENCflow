# Glaciers (&list_glacier)

> English mirror of docs/users_guide/glacier.md. The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Handles accumulation, ablation, and ice flow of land glaciers, and the
glacial erosion of landforms (cirques, U-shaped valleys) that flowing
ice produces. Enabled with `fn_glacier`. **Air temperature (fn_meteo)
and snow accumulation/snowmelt (fn_snow) are required** (snowfall is
the accumulation source). Like landform change, the processes are
**stackable**: enable only what you need.

| Process | Flag | Description |
|---|---|---|
| Mass balance | (always on) | Firnification of perennial snow (accumulation) and degree-day melt of the ice surface (ablation) |
| Ice flow | f_glflow | Ice deformation flow by the shallow ice approximation (SIA) |
| Basal sliding | f_glslide | Weertman-type basal sliding (requires f_glflow) |
| Glacial erosion | f_glero | Bed erosion proportional to sliding speed (requires f_glslide) |
| Avalanche redistribution | f_glava | Gravitational transport of snow off steep slopes |

The state is the per-cell ice thickness (m), written as the
distributed field `Hi0001...` at every output time. The conserved
storage column S_total on screen and in the Log includes the water
equivalent of the ice, and restarts
([Suspend and restart](restart.md)) continue from the private file
glacier.dat in the state directory (fn_glacier must have been enabled
when saving).

The design background (the SIA formulation, the time-acceleration
concept, and the documented simplifications) is in the developer
document [docs/glacier_plan.md](../../glacier_plan.md) (Japanese).

## Execution control and the notion of time

Glaciers evolve far more slowly (years to millennia) than the
hydraulics (seconds to days), so ENCflow uses **intermittent updates
and time acceleration** to cover geomorphic time.

| Parameter | Default | Meaning |
|---|---|---|
| f_glacier | 1 | 0 temporarily disables while keeping the file |
| dt_glacier_c | "1 day" | Update interval for firnification, flow, and erosion (a duration string such as "6 hour") |
| gl_morfac | 1.0 | Glacier-time acceleration factor. One update = gl_morfac repetitions of the same event for the ice and the landform |

- **Meltwater is not accelerated**: water produced by ice melt enters
  the surface water at the real-time rate every step (driving the
  flood computation), while only the ice loss is multiplied by
  gl_morfac (the same concept as morfac in landform change).
- **When combined with sediment/landform change (fn_geomorph),
  gl_morfac must equal morfac in &list_geomorph** (a single
  "geomorphic time" is an ENCflow contract; a mismatch stops the run
  at initialization).
- Millennial-scale experiments are composed of a repeated
  representative year (t_cycle_c in &list_sysparam) × gl_morfac ×
  restart chaining (the same recipe as long-term landform change; see
  the [sediment and landform change chapter](geomorph.md)).

## Mass balance (accumulation and ablation)

| Parameter | Default | Meaning |
|---|---|---|
| gl_dens | 900.0 | Ice density (kg/m³), used for the SWE ⇄ ice-thickness conversion |
| gl_tfirn_yr | 10.0 | Time constant of snow-to-ice conversion (firnification) in years; a few to ~10 years for temperate glaciers |
| gl_ddfi | — | Degree-day factor of the ice surface (mm/°C/day). **Required.** Larger than the snow value (snow_ddf); literature values are around 6–12 |
| gl_tmelt | 0.0 | Air-temperature threshold for ice melt (°C) |

- Snowfall accumulates as SWE through the snow feature, and **only
  snow that survives the year** is slowly converted to ice with time
  constant gl_tfirn_yr (seasonal snow simply melts and runs off).
- Ice melts **only where it is not covered by snow** (snow melts
  first).
- Air temperature is evaluated at the **ice-surface elevation**
  (ground + ice thickness), so combined with the temperature lapse
  rate (f_temp_lapse in &list_meteo) a thicker glacier has a colder
  surface — a realistic feedback. The snow line and equilibrium line
  are not prescribed; they **emerge** from temperature and
  precipitation.

## Ice flow (f_glflow)

With the shallow ice approximation (SIA), ice deforms under its own
weight and flows toward lower ice-surface elevations.

| Parameter | Default | Meaning |
|---|---|---|
| gl_afl | 1.0e-16 | Glen flow-law coefficient A (Pa⁻³ yr⁻¹); ~1e-16 for temperate ice |
| gl_cfl | 0.4 | Numerical stability safety factor (normally leave unchanged) |
| gl_nsubmax | 10000 | Upper bound on internal iterations per update (guards against runaway parameters) |

You do not need to worry about the time step: the model checks the
stability condition from the current ice thickness and slope at every
update and subdivides internally as needed (ice volume is conserved
exactly).

## Basal sliding and glacial erosion (f_glslide / f_glero)

| Parameter | Default | Meaning |
|---|---|---|
| gl_as | — | Weertman sliding coefficient As (m yr⁻¹ Pa⁻³). **Required** when f_glslide=1 |
| gl_kg | — | Erosion coefficient Kg. **Required** when f_glero=1. Coefficient of the erosion law ė = Kg·usˡ with sliding speed us measured in m/yr (dimensionless for l=1; literature values around 1e-4) |
| gl_lexp | 1.0 | Power-law exponent l of the erosion law (1–2) |

- Erosion occurs **only under sliding ice** (f_glero requires
  f_glslide); thin ice erodes almost nothing.
- Erosion lowers the computed elevation z and, if a soil layer sd
  exists, reduces it in step (once the soil is exhausted the bedrock
  erodes). Terrain evolution can be output with `f_out_z = 1` as
  `Z0001...`.
- Eroded debris is treated as evacuated from the system by ice and
  meltwater (depositional moraines are not yet represented; the total
  is reported at the end of the run).

## Avalanche redistribution (f_glava)

| Parameter | Default | Meaning |
|---|---|---|
| gl_ava_tanc | 0.6 | Critical avalanche slope tan θc (0.6 ≈ 31°) |

Snow on cells whose steepest ice-surface slope exceeds the threshold
is moved to the steepest-descent neighbor. This is a simple
representation of cliffs shedding snow so that accumulation
concentrates into cirques. Recommended for cirque-formation
experiments.

## Initial conditions

| Parameter | Default | Meaning |
|---|---|---|
| fn_glacier_hi0 | "" | Distributed initial ice thickness file (m) |

- **The default is ice-free** (hi = 0): the glacier is grown from
  snowfall (spin-up). This is the standard approach for glacial
  landform experiments. Save the spun-up steady state and branch
  climate scenarios from it via restart.
- For meltwater/runoff analyses of real glaciers, clip an ice
  thickness product (e.g. the Farinotti et al. consensus estimate) in
  GIS and supply it as fn_glacier_hi0. On restart, the saved ice
  thickness takes precedence.

## Configuration example

```
&list_meteo
  tempval(:,1) = 0.0, -5.0      ! representative-year temperature (elapsed days, degC)
  tempval(:,2) = 182.5, 10.0
  tempval(:,3) = 365.0, -5.0
  f_temp_lapse = 1              ! lapse rate (elevation-dependent snow line)
  f_prec_lapse = 1              ! precipitation gradient (more accumulation higher up)
  prec_lapse = 5.0              ! +5%/100m
/
&list_snow
  snow_ddf = 4.0
/
&list_glacier
  dt_glacier_c = "1 day"
  gl_morfac = 100.0             ! 1 computed year = 100 glacier/landform years
  gl_ddfi = 8.0
  f_glflow = 1
  f_glslide = 1
  gl_as = 1.0e-13
  f_glero = 1
  gl_kg = 1.0e-4
  f_glava = 1
/
```

Long-period climate change (glacial cycles, warming trends) can be
superimposed on the representative year with `tempofs` (an air
temperature offset series) in &list_meteo
([rainfall and weather chapter](forcing.md)).

## Combination requirements

| Use | Required other features |
|---|---|
| Glacier mass balance and meltwater | Precipitation + weather forcing + snow |
| Ice flow (f_glflow) | Same as above |
| Glacial erosion (f_glero) | f_glslide (+ t_cycle and restart chaining for long experiments) |
| Combined with landform change | fn_geomorph (with matching morfac) |

Idealized verification experiments (an analytic SIA benchmark and a
cirque-formation test) are in [test/glacier/](../../../test/glacier/),
and an annotated configuration sample is in
[examples/List_samples/en/list_glacier.txt](../../../examples/List_samples/en/list_glacier.txt).
