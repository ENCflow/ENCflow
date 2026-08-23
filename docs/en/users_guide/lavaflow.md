# Lava flows (&list_lavaflow)

> English mirror of docs/users_guide/lavaflow.md. The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Computes lava effusion from a set of vent cells, its downslope
spreading, stopping, and solidification into lava fields and new
topography. The dynamics are a depth-averaged Bingham viscous gravity
current (lubrication approximation); the viscosity η and yield stress
τ_y are given directly. Stopped lava is converted into the bed
elevation z at a fixed rate (solidification), and **rainfall, flooding,
and sediment transport over the new topography continue in the same
run** (eruption → lava field → secondary hydrologic response as one
chain). The full design is in [docs/lava_plan.md](../../lava_plan.md);
the implementation record is developer.md Sec. 51.

## What is computed

- The state is the per-cell lava thickness `s%hl` (m), written as the
  distributed field `Hl0001...` at every output time.
- Only cell edges where the basal shear stress ρg·hl·S (S = slope of
  the lava surface z+hl) exceeds the yield stress τ_y flow (τ_y = 0
  gives a Newtonian viscous flow). The stopping thickness on a slope
  tanθ is h∞ = τ_y/(ρg tanθ).
- Lava in "stopped" cells — where the edge velocity falls below the
  threshold `lv_vsol` — is converted to z at the rate `lv_wsol` (m/s;
  irreversible). The solidified surface does not add to the soil layer
  sd: it behaves as non-erodible bedrock.
- The model is isothermal (cooling and temperature-dependent viscosity
  are a future extension; lava_plan.md Sec. 8). One rheology set per
  run; there is no per-vent viscosity (viscosity differences are really
  temperature/composition differences, to be handled by the temperature
  extension).

## Enabling (minimal namelist)

Set `fn_lavaflow = "-"` (read from the same file) or a separate file
name in the main parameters, and write `&list_lavaflow`:

```
&list_lavaflow
  lv_rho  = 2600.0          ! density (kg/m3)
  lv_visc = 1.0e4           ! viscosity (Pa s)
  lv_tauy = 2000.0          ! yield stress (Pa)
  lv_cell(1:2,1,1) = 55, 40 ! cells (i, j) of vent 1
  lv_cell(1:2,2,1) = 55, 41
  lv_q0(1) = 10.0           ! constant effusion rate (m3/s)
/
```

## Parameters

| Parameter | Default | Meaning |
|---|---|---|
| f_lavaflow | 1 | 0 disables temporarily while keeping the file |
| dt_lavaflow_c | "" (every step) | update interval (duration string like "10 s") |
| lv_rho | 2600 | lava density ρ (kg/m³) |
| lv_visc | (required) | viscosity η (Pa s); basaltic 10²–10⁴, andesitic and up ≥10⁵ |
| lv_tauy | 0 | yield stress τ_y (Pa); 0 = Newtonian |
| lv_wsol | 0 | solidification rate of stopped cells (m/s); 0 = none |
| lv_vsol | (required if lv_wsol>0) | stop-detection velocity threshold (m/s); typically 10⁻⁴–10⁻³ |
| lv_cfl | 0.4 | safety factor of the explicit subcycling (0–1) |
| lv_nsubmax | 10000 | cap on subcycles per update (runaway guard) |
| lv_cell(1:2,k,n) | — | cell k (i, j) of vent n; vent numbers n are consecutive from 1 |
| lv_q0(n) | — | constant effusion rate of vent n (m³/s) |
| lv_val(1:2,k,n) | — | effusion time series (time (min), m³/s); overrides lv_q0 |
| fn_lv_cell(n) | "" | cell-set file (rows of "i j"; overrides inline cells) |
| fn_lv_val(n) | "" | effusion time-series file (min, m³/s; highest priority) |

- The effusion rate is the **total over the cell set**, distributed
  equally to its cells (same convention as the internal source
  &list_bound_source). It carries no momentum.
- Represent fissure eruptions by listing cells; multiple vents with
  different timing use the third index n (up to 20 vents).
- Time series are linearly interpolated. Writing the same time twice
  makes a step change (`(5,0.5),(5,0.0)` = shut off exactly at 5 min).

## Effect on outputs

- The distributed output gains `Hl` (lava thickness, m; always written
  while enabled, no flag).
- Solidified lava appears as an increase of the bed elevation `Z`
  (set `f_out_z = 1` to write it at every output time).
- It is not counted in the conserved-volume column S_total on the
  screen/Log (it is not a water column). A volume ledger (erupted,
  solidified, molten) is reported at the end of the run.
- Restart uses the private file save/lavaflow.dat (automatic).

## Examples

- Verification case: [test/lava](../../../test/lava/) — the Huppert
  similarity solution (axisymmetric spreading in the Newtonian limit)
  and the Bingham stopping thickness h∞ against analytic solutions.

## Constraints and interactions

- **Interaction with water is through the topography only**: surface
  water does not see flowing lava and flows over the bed z (the same
  simplification as glaciers). Because solidification raises z, rain
  and floods after solidification automatically follow the new
  topography. There is no thermal lava–water interaction (steam
  explosions, quench fragmentation), and flowing lava does not dam
  water.
- Roughness and infiltration on the solidified surface keep their
  existing distributions (consider giving maps such as fn_gw_ksv in
  preprocessing if needed).
- No lava enters sea cells (submarine flow is out of scope).
- Not supported with STG (f_gridsystem=1), nor together with geomorph
  morfac > 1 (lava is an event-time process).
- **Time-step note**: the explicit diffusion (~ρg hl³/3η) is stabilized
  by subcycling. Very fluid basalt (η ≤ 10² Pa s) makes the subcycle
  count — and cost — large (if the run stops on lv_nsubmax, shorten
  dt_lavaflow_c or reconsider η; lava_plan.md Sec. 6).
