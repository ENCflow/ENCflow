# Water Quality and Load Runoff (&list_wq)

> English mirror of docs/users_guide/wq.md (based on commit c7e801e). The Japanese file is the master copy.

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

The minimal input to "just try it" is **fn_wq with one initial
concentration or one load** (without decay, settling or partitioning the
substance is a conservative tracer = extent and dilution).

```
&list_wq
  wq_c0 = 100.0                  ! a 100 mg/L tracer on the initial water everywhere
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

**Representative values by substance (a starting point)** - because
water-quality properties differ by orders of magnitude between
substances, ENCflow sets no defaults (with no decay, settling or
partitioning the substance runs as a conservative tracer) and lists
representative values instead. All of them span 1-2 orders of
magnitude, so bracketing with a low and a high case is the practical
approach (sources in developer.md §66).

| Substance type | Decay | Settling / partitioning | Subsurface | Notes |
|---|---|---|---|---|
| Conservative tracer (salinity, dye, turbidity index) | none | none | f_wq_infil=1, wq_rg=1 | Extent and dilution; the first thing to run |
| Coliforms / pathogen indicators (sewer surcharge, CSO) | wq_k20 1-5 /day (T90 0.5-2 days; fast in sunny summer, slow in cloudy / winter conditions) | none (wq_kd 1e3-1e4 to see attachment to turbidity) | f_wq_infil=0 (stays on the surface) | Concentrations in "Sanitary risk of sewer surcharge" below |
| Organic pollution (BOD), ammonia | wq_k20 0.1-0.5 /day (Streeter-Phelps deoxygenation coefficient) | none | f_wq_infil=1 | Dissolved oxygen is not solved |
| Nutrients (nitrate), dissolved salts | none to 0.01 /day | none | f_wq_infil=1, wq_rg=1 | Returns through groundwater seepage |
| Turbidity / SS (particulate) | none | wq_vs 0.5-10 m/day (clay 2 um 0.3, silt 10 um 8; Stokes) | f_wq_infil=0 | f_wq_settle=1 for the resuspension cycle |
| Heavy metals (Zn, Cu, Pb; mainly particulate) | none | wq_kd 1e3-1e5 L/kg (Zn 1e3, Cu 3e3, Pb 1e4-1e5; requires f_suspend) | f_wq_infil=1, wq_rg 1e2-1e4 | Two-phase partitioning (below) |
| Radiocesium (Cs-137) | wq_thalf 11019 day (30.17 yr) | wq_kd 1e3-1e4 L/kg (strong sorption to clay; requires f_suspend) | f_wq_infil=1, wq_rg 1e3-1e4 (R = 1 + rho_b Kd / theta) | Long-term catchment behavior |
| Pesticides, dissolved organics | wq_thalf 10-60 day | wq_kd 1-100 L/kg (Koc x organic-carbon fraction) | f_wq_infil=1, wq_rg 2-100 | Degradation rate depends on temperature and radiation |

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
- Transport inside the weathered-bedrock layer (f_gwlayer2) is not
  supported yet.

Worked example: [test/gwseep](../../../test/gwseep/) (a closed sloping
domain cycling infiltration → lateral groundwater flow → seepage →
re-infiltration, with built-in checks of the ledger closure and the
immobilization at wq_rg=1e12).

## Reservoirs and retention ponds

No extra setting is needed — this works automatically when
dams/lakes ([structures](structure.md)) or retention ponds (rscap;
[geographic information](geoinfo.md)) are present.

- **Dams and lakes (storage type)** are treated as **completely mixed
  reservoirs**. The mass entering with the captured water accumulates
  in the lake's pool, and the released water carries the storage
  concentration M/V (spills carry the same concentration). This
  represents the attenuation and delay of loads passing through
  reservoir chains such as tank cascades. Decay (wq_thalf / wq_k20)
  acts inside the pool as well. **In-reservoir settling is not
  implemented**, so for settling substances the release concentration
  is on the safe (high) side.
- The mass entering a **fixed-level lake** (no release cells) leaves
  the system together with the water (counted in the to_dam_g
  ledger).
- The mass of the water absorbed by **retention ponds (rscap)**
  accumulates in a per-cell pond pool (the overflow after the pond is
  full is never absorbed, so the pool only accumulates; evaporation
  removes pure water and the mass remains = enrichment).

Worked example: [test/damwq](../../../test/damwq/) (a slope with a
retention-pond patch and a constant-release dam, with built-in checks
of the ledger closure and the end-to-end preservation of a uniform
concentration).

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

## Sanitary risk of sewer surcharge (with the conduit continuum layer)

Evaluates the **spatial distribution of the sanitary risk (fecal
indicators such as coliforms)** when sewage erupting from manholes and
outfalls during pluvial flooding spreads through the town together with
the flood water. It serves to prioritize post-flood disinfection, public
information and evacuation guidance, and to compare countermeasures such
as storage pipes and outfall improvements.

The mechanism is a **"fixed supply-side concentration" approximation**:
the budget of bacteria inside the pipes is not solved; the water that
comes out of the sewer onto the surface (surcharge and landside outfall
discharge) is regarded as sewage of a constant concentration, and the
load of that volume times concentration is injected onto the surface.
Once on the surface it follows the ordinary water-quality computation
(advected with the flood water and dying off by first-order decay).
Dilution and transport inside the pipes are not solved, but since the
sewage concentration itself varies over 1-2 orders of magnitude, this
approximation is adequate for the practical questions "where, when, and
at what order of magnitude is the contamination".

### Setup steps

**Step 1 - build the sewer network as a conduit continuum layer** (the
conduit continuum layer of [the groundwater chapter](gwflow.md); the
urban preset: inlet density given, no interlayer exchange). We recommend
running without water quality first and checking that the location and
magnitude of the surcharge are reasonable (the hydraulics dominate the
result).

**Step 2 - enable water quality and give the sewage concentration**:

```
&list_sysparam
  fn_wq = '-'               ! enable water quality (settings in the same file)
/
&list_wq
  wq_gwc_conc = 1.0e4       ! concentration of surcharge / outfall water (see the unit reading below)
  f_wq_gwc_in = 1           ! load of flood water swallowed by inlets is removed to the conduit side (default)
  wq_k20 = 2.303            ! first-order decay = ln(10)/T90 (example: T90 = 1 day)
/
```

That is all: the concentration accompanies the surcharge and landside
outfall water (the run stops with an error if the conduit continuum
layer is not enabled).

### Reading the units (the coliform case)

The units of the water-quality module are nominally "g" and "mg/L", but
since it is a linear transport of a single substance **they can be
reinterpreted as any quantity**. For coliforms, the convenient
convention is "g = 10^6 CFU":

| Actual quantity | Reading | Value of wq_gwc_conc |
|---|---|---|
| Sewage 10^6 CFU/100mL | = 10^10 CFU/m3 = 10^4 units/m3 | 1.0e4 |
| Sewage 10^5 CFU/100mL | | 1.0e3 |
| Sewage 10^7 CFU/100mL | | 1.0e5 |

To convert the output concentration field C (nominal mg/L = units/m3)
back to CFU/100mL, use **C x 100** (1 unit/m3 = 10^6 CFU/m3 =
100 CFU/100mL). For example C = 50 means 5x10^3 CFU/100mL - compared
with bathing-water standards (e.g. fecal coliforms at or below
100 CFU/100mL) this reads as "water to avoid contact with".

### Representative values (a starting point)

| Quantity | Guide | Notes |
|---|---|---|
| Coliforms in dry-weather sewage | 10^5-10^7 CFU/100mL | Raw sewage. Sanitary sewers of separate systems are at the upper end |
| Wet weather (combined sewer overflow) | 10^4-10^6 CFU/100mL | About an order lower by stormwater dilution. Use this for combined-system assessments |
| T90 (90 % die-off time) | Sunny summer daytime: hours to 1 day / cloudy, rainy or winter: 1 to several days | Varies strongly with radiation, water temperature and turbidity. For flood assessments a longer, conservative value (1-2 days) is recommended |
| Conversion to the decay coefficient | k (1/day) = ln(10) / T90 (day) | T90 = 1 day → wq_k20 = 2.303 |

Both the concentration and T90 are uncertain by 1-2 orders of magnitude,
so the practical approach is **not to commit to one value but to bracket
with a low and a high case** (the result is nearly linear in the
concentration).

### Reading the output

- **Concentration fields C0001...** (nominal mg/L): the spatial
  distribution of contamination. Convert to CFU/100mL as above and map
  to risk classes. To capture "the area that was ever covered by
  contaminated water" after the flood recedes, use the period maximum
  (as with H9999; refine dt_file if needed).
- **result/wq.csv**: the mass ledger. `in_gwc_g` = input from the sewer
  (surcharge and outfalls), `to_gwc_g` = removed to the conduit side by
  inlets, `decay_g` = die-off. **Use it to verify that the budget closes
  (residual ≈ 0).**
- The concentration column C of the probe CSVs monitors the time series
  at specific points (shelters, wells, ...).

### What this approximation cannot do

- **Transport and dilution inside the pipes**: "sewage swallowed at an
  upstream inlet comes out at a downstream outfall" is not represented
  (the swallowed load is only removed in the ledger). Wet-weather
  dilution inside the pipes is not solved either, so for combined
  systems give the concentration of the overflow water directly in
  wq_gwc_conc.
- **Environmental dependence of the decay coefficient**: the time
  variation of T90 with radiation and water temperature is approximated
  by a constant coefficient (bracketing with low and high cases is
  recommended).
- The concentration is fully mixed (no vertical profile) and a single
  substance (to include viruses etc., run each substance separately).

Example: [test/sewer_wq](../../../test/sewer_wq/) (a town with trunk and
branch sewers under 100 mm/h x 30 min of rain - the chain of surcharge →
flooding → spreading → decay, and the budget check of wq.csv. How the
network was built: [examples/sewer_hybrid](../../../examples/sewer_hybrid/)).

## Output and monitoring

- The concentration distribution `C0001` (mg/L) is output
  automatically (also the pool distribution `B0001` when the buildup
  pool is enabled).
- A mass-budget ledger is output to `result/wq.csv` (cumulative
  inputs, boundary inflows, infiltration, seepage return (seep_g),
  dam capture/release (to_dam_g / rel_dam_g), pond absorption
  (to_rs_g), outflow out of the system, decay, and so on, plus the
  current stored mass on the surface, underground, in the buildup
  pool, in dams and in ponds; useful to verify the budget).
- Columns for concentration C and surface load cq are added to the
  probe CSV ([the measurement chapter](record.md)).
- Restart (save/restore) is handled automatically.

## Worked examples and related chapters

- Examples: [examples/List_samples/list_wq.txt](../../../examples/List_samples/en/list_wq.txt)
- Combined with groundwater, infiltration entrainment and the
  subsurface pool can be tracked
  ([the groundwater chapter](gwflow.md)).
