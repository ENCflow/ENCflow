# Water Quality and Load Runoff (&list_wq)

> English mirror of docs/users_guide/wq.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Handles load input, advective transport, decay, settling, and
infiltration entrainment of a single substance. Usable for runoff
analyses of pollutant loads, radionuclide migration, tracer
experiments, and so on. Enable it with `fn_wq`.

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
| wq_vs | - | Settling velocity (m/day). Loss from surface water to the riverbed |
| f_wq_settle | 0 | Destination of settling. 0: lost to the riverbed, 1: to the surface buildup pool (resuspension cycle) |
| f_wq_infil | 1 | Behavior at infiltration. 0: remains on the surface (for particulate substances), 1: entrained at the current concentration into the subsurface pool (for dissolved substances) |

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
  inputs, boundary inflows, infiltration, outflow out of the system,
  decay, and so on; useful to verify the budget).
- Columns for concentration C and surface load cq are added to the
  probe CSV ([the measurement chapter](record.md)).
- Restart (save/restore) is handled automatically.

## Worked examples and related chapters

- Examples: [examples/List_samples/list_wq.txt](../../../examples/List_samples/en/list_wq.txt)
- Combined with groundwater, infiltration entrainment and the
  subsurface pool can be tracked
  ([the groundwater chapter](gwflow.md)).
