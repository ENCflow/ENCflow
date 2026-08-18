# Fresh and salt water layers (&list_salt)

> English mirror of docs/users_guide/salt.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Introduces a **salt-water layer** into the surface water and the shallow
groundwater (soil layer), approximately handling fresh/salt interactions
such as salt wedges, seawater intrusion, and freshwater lenses. Enable
it with `fn_salt`.

The model is a **quasi-static sharp-interface approximation** of the
same type as MODFLOW's SWI2 package: the depth and subsurface storage
(h and Hg) remain the fresh+salt **totals**, and the "salt layer
thickness" (always the lowest part of the column) is tracked as part of
those totals. The density difference eps = (rho_s - rho_f)/rho_f
appears only in the driving head of the salt layer,
Phi_s = water level + eps x interface elevation; the momentum equation
of the shallow-water flow is unchanged. Even with a horizontal water
surface, a tilted interface produces a hydrostatic pressure difference
at depth that moves the salt water (removing a partition in a pool ends
with a stably stratified state, which the model reproduces).

## What it can do

- **Seawater intrusion**: with sea cells (with tide) as a prescribed
  salt-water head, intrusion into and retreat from the aquifer. The
  equilibrium interface follows the Ghyben-Herzberg relation.
- **Freshwater lenses** (with recharge) and the quasi-steady position
  of **salt wedges**.
- **Storm-surge / tsunami run-up and where the seawater goes**: the
  run-up seawater flows over land as salt water (riding on the
  shallow-water advection).
- Mixing and entrainment (brackish water generation), the inertia of
  internal waves, and continuous concentration fields are **not
  handled** (the interface stays sharp).

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
- See test/salt for schematic experiments (the pool-partition
  experiment and seawater intrusion, with analytic checks).
