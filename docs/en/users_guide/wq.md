# Water Quality and Load Runoff (&list_wq)

> English mirror of docs/users_guide/wq.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Handles load input, advective transport, decay, settling,
infiltration entrainment, Kd two-phase partitioning, and transport
through groundwater of a single substance. Usable for runoff analyses
of pollutant loads, radionuclide migration, basin-scale heavy-metal
transport, tracer experiments, and so on. Enable it with `fn_wq`.

```
&list_wq
  wq_c0 = 0.0                    ! initial concentration (mg/L)
  wq_thalf = 8.0                 ! half-life of 8 days (example: I-131)
  ! point source: 2 g/s from cell (50,60)
  wq_pt_cell(:,1,1) = 50, 60
  wq_pt_load(1) = 2.0
/
```

## Substance properties

| Parameter | Default | Meaning |
|---|---|---|
| f_wq | 1 | 0 temporarily disables while keeping the file |
| wq_c0 | 0 | Initial concentration (mg/L, uniform) |
| wq_thalf / wq_k20 | - | Decay: half-life (day) or first-order decay coefficient (1/day). Mutually exclusive |
| wq_vs | - | Settling velocity (m/day). Loss from surface water to the riverbed (single-phase approximation; mutually exclusive with wq_kd) |
| wq_kd | - | Equilibrium partition coefficient (L/kg). Two-phase dissolved/particulate partitioning (below; requires f_suspend) |
| f_wq_settle | 0 | Destination of settling. 0: lost to the riverbed, 1: to the surface buildup pool (resuspension cycle) |
| f_wq_infil | 1 | Behavior at infiltration. 0: remains on the surface (for particulate substances), 1: entrained at the current concentration into the subsurface pool (for dissolved substances) |
| wq_rg | 1 | Retardation factor R (>= 1) for subsurface transport. Reduces the effective concentration of groundwater advection and seepage return to 1/R (see "Transport through groundwater" below) |

## How loads are given (superposable)

The input paths are **superposed**, not mutually exclusive (they can
be combined, e.g. background load + specific sources). The cell set of
each group can also be given by file (`fn_*_cell`), and cell
coordinates (i, j) are **1-based** (beware of 0-based GIS numbering;
see [the coordinate systems chapter](coordinates.md)). Times in the
load and concentration time series are **elapsed days** from t=0.

**Point sources (outfalls etc.)** - cell group + load (g/s, total over
the group)

```
  wq_pt_cell(:,1,1) = 50, 60          ! cells of group 1
  wq_pt_load(1) = 2.0                 ! constant load (g/s)
  !wq_pt_series(:,1,1) = 0.0, 2.0     ! or a time series (elapsed days, g/s)
```

**Diffuse sources (farmland etc.)** - cell group + unit load
(kg/ha/day)

```
  wq_ar_cell(:,1,1) = ...
  wq_ar_load(1) = 0.5                 ! constant unit load (kg/ha/day)
```

**Distributed diffuse source (unit loads by land use)** - a cell-wise
distribution over the whole domain

| Parameter | Meaning |
|---|---|
| fn_wq_map | Distribution file of unit loads (kg/ha/day) |
| wq_map_factor | Multiplier on the distribution (for calibration) |
| f_wq_map | Interpretation of the distribution. 0: injected directly into surface water, 1: buildup rate into the surface buildup pool |

**Rainfall concentration (wet deposition)** - domain-wide input as
"rainfall reaching the surface x concentration": `wq_rain_conc`
(constant, mg/L) or `wq_rain_series` (elapsed days, mg/L).

**Boundary inflow concentration** - per segment-inflow number of
[Boundary conditions](boundary.md), `wq_in_conc(n)` (constant) or
`wq_in_series(:,:,n)` (time series).

## Two-phase partitioning of sorbing substances (Kd; e.g. heavy metals)

Substances that sorb strongly onto suspended sediment, such as heavy
metals, are treated as an equilibrium two-phase (dissolved +
particulate) substance when `wq_kd` (equilibrium partition
coefficient, L/kg) is given. [Suspended sediment](geomorph.md)
(`f_suspend`) is required (the partitioning needs a sediment
concentration; without it the run stops with an error).

Every step and cell, the dissolved fraction fd = 1/(1 + Kd·Css)
(Css: suspended-sediment mass concentration, kg/m³) is evaluated, and

- **infiltration** entrains only the dissolved fraction fd into the
  ground (the particulate fraction is filtered out and remains on the
  surface),
- **settling** removes the particulate fraction (1 − fd) at the
  **same settling velocity as the suspended sediment** (`wq_vs` is no
  longer needed; specifying both is an error). The destination is
  `f_wq_settle`, and **1 (the surface buildup pool) is recommended** —
  combined with shear washoff (`wq_wash_kf`) it closes the cycle of
  resuspension during floods and bed accumulation during low flow.
- Advection carries the total mass with the water (dissolved and
  suspended particles move at the same velocity; the phases differ
  only vertically).

Kd varies by orders of magnitude with the substance, the sediment and
the water chemistry (pH etc.). Literature orders of magnitude are
roughly Pb: 10⁴–10⁶, Cu/Zn/Cd: 10³–10⁵, As: 10¹–10³ L/kg, but
**back-calculating from observed particulate/dissolved ratios in the
target basin is more reliable**. Sorption retardation in groundwater
is given separately by `wq_rg` (below).

Worked example: [test/kdpart](../../../test/kdpart/) (a suspended-
sediment dam break plus a point source, with built-in checks of the
ledger closure and the monotonic response to increasing Kd).

## Transport through groundwater (infiltration → lateral flow → seepage)

With `f_wq_infil=1` (the default), the mass entrained into the
subsurface pool by infiltration **moves with the groundwater** when
[lateral groundwater flow](gwflow.md) (`f_gwlateral=1`) is enabled, and
**returns to the surface water at its groundwater concentration where
saturation excess seeps out**. No extra setting is needed — enabling
both water quality and lateral flow activates it. This closes the
"infiltration → groundwater flow → seepage into rivers" pathway, so
the dry-weather river quality dominated by baseflow can be handled in
one run.

The **retardation factor `wq_rg`** (R >= 1, default 1 = no
retardation) lumps the delay caused by equilibrium sorption in the
soil. The substance moves at 1/R of the groundwater velocity (and the
seepage water carries the dissolved 1/R side of the concentration).
For linear equilibrium sorption, R = 1 + ρb·Kd/θ (ρb: dry bulk
density, θ: effective porosity, Kd: partition coefficient). Strongly
sorbing substances such as heavy metals have R of the order of
10–10⁴, which effectively immobilizes the groundwater pathway — give
that judgement through R.

- Only the dissolved treatment (`f_wq_infil=1`) is transported. Decay
  (wq_thalf / wq_k20) acts on the subsurface pool as well.
- The subsurface budget can be verified in `result/wq.csv` with
  `to_gw_g` (infiltrated into the ground), `seep_g` (cumulative mass
  returned by seepage) and `mass_gw_g` (current subsurface storage):
  to_gw − seep = mass_gw.
- Transport inside the weathered-bedrock layer (f_gwlayer2) and
  entrainment of the mass absorbed by small retention ponds (rscap)
  are not supported yet (the absorbed mass remains on the surface).

Worked example: [test/gwseep](../../../test/gwseep/) (a closed sloping
domain cycling infiltration → lateral groundwater flow → seepage →
re-infiltration, with built-in checks of the ledger closure and the
immobilization at wq_rg=1e12).

## Surface buildup + washoff (nonlinear L-Q)

A buildup-washoff mechanism where the load accumulated on the surface
in dry weather is washed off by rainfall. It can represent a nonlinear
L-Q relation between discharge and load, and first flush.

| Parameter | Meaning |
|---|---|
| wq_bd_rate | Uniform buildup rate (kg/ha/day) (mutually exclusive with the distributed form f_wq_map=1) |
| wq_bd_max | Buildup limit (kg/ha). Omit for linear, unlimited buildup |
| wq_bd0 / fn_wq_bd0 | Initial pool (kg/ha) (uniform value / distribution; mutually exclusive) |
| wq_wash_kr | Raindrop washoff coefficient (1/m; corresponds to 1000 x the exponential washoff coefficient c1 [1/mm] customary in urban drainage models) |
| wq_wash_kf / wq_wash_tauc | Shear washoff coefficient (1/s) and critical shear stress (N/m^2) (required with kf) |

## Output and monitoring

- The concentration distribution `C0001` (mg/L) is output
  automatically (also the pool distribution `B0001` when the buildup
  pool is enabled).
- A mass-budget ledger is output to `result/wq.csv` (cumulative
  inputs, boundary inflows, infiltration, seepage return (seep_g),
  outflow out of the system, decay, and so on; useful to verify the
  budget).
- Columns for concentration C and surface load cq are added to the
  probe CSV ([the measurement chapter](record.md)).
- Restart (save/restore) is handled automatically.

## Worked examples and related chapters

- Examples: [examples/List_samples/list_wq.txt](../../../examples/List_samples/en/list_wq.txt)
- Combined with groundwater, infiltration entrainment and the
  subsurface pool can be tracked
  ([the groundwater chapter](gwflow.md)).
