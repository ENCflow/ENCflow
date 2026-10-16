# Fresh and salt water layers (&list_salt)

> English mirror of docs/users_guide/salt.md. The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Introduces a **salt-water layer** into the surface water and the shallow
groundwater (soil layer), approximately handling fresh/salt interactions
such as salt wedges, seawater intrusion, and freshwater lenses. Enable
it with `fn_salt`.

The model is a **quasi-static sharp-interface approximation** of the
same type as the sharp-interface (two-zone) methods established in
groundwater modeling (the idea of the SWI2 package of
MODFLOW[^bakker13]): the depth and subsurface storage
(h and Hg) remain the fresh+salt **totals**, and the "salt layer
thickness" (always the lowest part of the column) is tracked as part of
those totals. The density difference $`\varepsilon`$ appears only in the
driving head $`\Phi_s`$ of the salt layer; the momentum equation of the
shallow-water flow is unchanged ($`\eta`$: water level, $`\zeta`$:
interface elevation).

```math
\varepsilon = \frac{\rho_s - \rho_f}{\rho_f},
\qquad
\Phi_s = \eta + \varepsilon\,\zeta
```
 Even with a horizontal water
surface, a tilted interface produces a hydrostatic pressure difference
at depth that moves the salt water (removing a partition in a pool ends
with a stably stratified state, which the model reproduces).

![Section of the fresh/salt two layers and the connection to the sea](../../figs/salt_layers_en.png)

Coastal section. The salt layer hss sits at the bottom of the surface water h and the salt zone hgs at the bottom of the subsurface storage hg of the soil layer; the interface elevation ζ sets the driving head of the salt water, Φs = η + ε·ζ. Sea cells are an all-salt boundary at tide level: underground the salt water is exchanged in both directions while fresh water only discharges, and at the surface the run-up seawater is tracked as salt water.

## What it can do

- **Seawater intrusion**: with sea cells (with tide) as a prescribed
  salt-water head, intrusion into and retreat from the aquifer. The
  equilibrium interface follows the Ghyben–Herzberg relation[^bear79]
  $`z_s = h_f/\varepsilon`$ (the interface depth below sea level is
  $`1/\varepsilon`$ times the freshwater head above it, about 40 for
  seawater).
- **Freshwater lenses** (with recharge) and the quasi-steady position
  of **salt wedges**.
- **Storm-surge / tsunami run-up and where the seawater goes**: the
  run-up seawater flows over land as salt water (riding on the
  shallow-water advection).
- Mixing and entrainment (brackish water generation), the inertia of
  internal waves, and continuous concentration fields are **not
  handled** (the interface stays sharp).

## Just try it (minimal input)

Every parameter has a default, so **an empty &list_salt in fn_salt** is
enough to run (seawater 1025 and freshwater 1000 kg/m³ = 2.5 % density
difference). What it needs alongside: the sea mask fn_sw and the tide
fn_tide that make the sea the prescribed salt-water head
([the tide chapter](tide.md)), and f_gwlateral=1 when the subsurface
salt zone (f_salt_gw=1) is used ([the groundwater chapter](gwflow.md);
the lateral K and specific yield are shared).

```
&list_salt
/
```

## Overall configuration (&list_salt)

| Parameter | Default | Meaning |
|---|---|---|
| f_salt_surf | 1 | 1: surface salt layer (advection + bottom gravity current) |
| f_salt_gw | 1 | 1: subsurface (soil layer) salt zone. **Requires f_gwlateral=1** |
| salt_rhof / salt_rhos | 1000 / 1025 | Fresh / salt densities (kg/m3); they set eps |
| salt_alpha | 1.0 | Barotropic advection share of the salt layer, alpha (the bottom layer carries less of the flow; 1 = concentration-proportional) |
| salt_ni | 0.025 | Interfacial Manning roughness of the bottom gravity current |
| salt_hss0 / fn_salt_hss0 | 0 / - | Initial surface salt-layer thickness (specified as part of the existing h; uniform value or a map) |
| salt_hgs0 / fn_salt_hgs0 | 0 / - | Initial subsurface salt storage (**added salt water** - also added to Hg; uniform value or a map) |
| salt_eps | 1e-3 | Regularization amount for the dry test (m) |
| salt_eps_h | 1e-2 | Linearization width of the gravity-current sqrt law (head difference, m) |
| salt_diagratio | 2/(2+sqrt(2)) | Diagonal partitioning (normally no need to change) |
| salt_nsubmax | 200 | Upper bound of the adaptive subcycling of the surface gravity current |

## Recommended values by pattern

The defaults are middle-of-the-road values that make the two layers
"run". When the target is known, start from the following (calibration
quantities).

| Type | f_salt_surf / f_salt_gw | salt_rhos (kg/m³) | Initial salt water | Used together with | Notes |
|---|---|---|---|---|---|
| Coastal aquifer salt wedge (Ghyben-Herzberg) | 0 / 1 | 1025 | fn_salt_hgs0 with the existing salt-water surface along the coast, or start fresh and wait for intrusion | f_gwlateral=1, K_sh 3600-36000 mm/h (sandy aquifer 1e-3 to 1e-2 m/s), sy0 0.2-0.3, sd0 = aquifer thickness 5-20 m | With recharge (rainfall + Green-Ampt) a freshwater lens appears |
| Estuary / tidal-river salt wedge | 1 / 0 | 1025 (brackish inner bay 1005-1015) | 0 | fn_tide + segment inflow (river discharge) | Calibrate the wedge position with salt_ni 0.02-0.03 and salt_alpha 0.5-1 |
| Where storm-surge / tsunami seawater goes | 1 / 0 | 1025 | 0 | Tide (surge) or boundary incidence (tsunami) + seawalls | Mixing is not solved = extent of the salt-water run-up and where it drains |
| Salinization of reclaimed lowland (intrusion and drainage) | 1 / 1 | 1025 | fn_salt_hgs0 with the existing salt-water surface | Drainage pumps ([structures](structure.md)) | Fresh/salt split of infiltration is not implemented (see constraints) |
| Stratified brackish lake / reservoir (halocline position) | 1 / 0 | 1010-1020 | salt_hss0 = lower-layer thickness | - | Sharp interface: no mixed layer or entrainment |

## Connection to the sea

Sea cells (the sea mask of [Tide and sea level](tide.md)) automatically
become an "all salt, water level = tide level" boundary:

- **Subsurface**: salt water is exchanged in both directions between
  the aquifer and the sea according to the head difference; fresh water
  only discharges to the sea (there is no fresh water in the sea).
  Tidal variations are reflected directly in the boundary head.
- **Surface**: seawater that runs up over land at high tide or in a
  storm surge is tracked as salt water (and salt water that returns to
  the sea disappears).

## Output and monitoring

- The surface salt-layer thickness `Hss` (shared with `f_out_h`) and
  the subsurface salt storage `Hgs` (shared with `f_out_hg`) are
  additionally output while enabled.
- Salt water is still water, so the S columns (water budget) show the
  totals as before.
- Restart is handled automatically through the private file
  saltwater.dat (fn_salt must have been enabled at save time).

## Constraints and notes

- f_salt_gw=1 requires the lateral flow of the soil layer
  (f_gwlateral=1 in [Groundwater](gwflow.md)); K_sh and the specific
  yield are shared.
- The fresh/salt partitioning of evapotranspiration and infiltration is
  not yet implemented (implicitly treated as fresh; the "salt damage"
  path where infiltrating seawater contaminates the aquifer is a future
  extension).
- At rapidly advancing intrusion fronts, a small partition error
  between the total and the salt (proportional to dt) can arise from
  time splitting; reducing dt reduces it (see developer.md sec. 47.2).

## Tests and examples

- [test/salt](../../../test/salt/): the pool-partition experiment (approach to a stable stratification) and seawater intrusion with analytic checks.
- Worked example of the format: [examples/List_samples/en/list_salt.txt](../../../examples/List_samples/en/list_salt.txt).

## References

[^bear79]: Bear, J. (1979): *Hydraulics of Groundwater*. McGraw-Hill, New York. (sharp-interface approximation and the Ghyben–Herzberg relation)
[^bakker13]: Bakker, M., Schaars, F., Hughes, J. D., Langevin, C. D. and Dausman, A. M. (2013): Documentation of the Seawater Intrusion (SWI2) Package for MODFLOW. *U.S. Geological Survey Techniques and Methods*, 6-A46. (a practical implementation of the two-zone sharp-interface method)
