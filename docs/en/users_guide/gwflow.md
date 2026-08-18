# Groundwater (&list_gwflow and model-specific settings)

> English mirror of docs/users_guide/gwflow.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Handles infiltration, storage, lateral flow, and exfiltration by
shallow groundwater. Enable it with `fn_gwflow`, choose the models in
the common settings `&list_gwflow`, and write the chosen models'
specific setting groups in the same file (groups for unused models may
remain in the file and are ignored - A/B comparisons only require
switching the selectors).

Groundwater in ENCflow is a **shallow two-layer** scheme for runoff
analysis (soil layer + weathered bedrock layer; natural confined
aquifers and borehole-scale hydraulics are out of scope). On top of
these you can stack a **conduit continuum layer** (f_gwconduit) that
represents subgrid conduit networks - sewer networks, fractured
bedrock, and the like - as an equivalent continuum, and **well pumping
/ groundwater abstraction sinks** (f_gwpump).

## Overall configuration (&list_gwflow)

Choose the vertical part (surface <-> subsurface exchange) and the
lateral part (horizontal subsurface movement) independently, and stack
a second layer, a conduit continuum layer, and pumping sinks if needed.

| Parameter | Default | Meaning |
|---|---|---|
| f_gwvertical | 0 | Vertical model. 0: none (temporarily disabled), 1: bucket, 2: Green-Ampt |
| f_gwlateral | 0 | Lateral model. 0: none, 1: nonlinear Boussinesq |
| f_gwlayer2 | 0 | 1: enable the weathered bedrock layer (second layer) |
| f_gwconduit | 0 | 1: enable the conduit continuum layer (sewer networks, fractured bedrock, etc.) |
| f_gwpump | 0 | 1: enable well pumping / groundwater abstraction (sink) |
| f_gwfrost | 0 | 1: enable infiltration suppression by frozen ground (requires air temperature, fn_meteo) |
| dt_gwflow | 0 | Update interval of the groundwater computation (s). 0: every step. If specified, must be at least dt (consistency is maintained through the effective time step) |

**Soil depth sd and specific yield sy0 belong to the geographic
information side** (f_sdtype/sd0/fn_sd, sy0 in &list_geoinfo; see
[the geographic information chapter](geoinfo.md)). They are read only
when a model that needs soil depth (Green-Ampt or lateral) is selected.

**Typical configurations**

| Purpose | Configuration |
|---|---|
| Infiltration losses in an event flood | f_gwvertical=2 (Green-Ampt) only |
| Catchment hydrology (up to interflow) | f_gwvertical=2 + f_gwlateral=1 |
| Down to baseflow / low-flow recession | The above + f_gwlayer2=1 |
| Urban pluvial flooding (sewer drainage and surcharge) | f_gwconduit=1 (alone where imperviousness dominates; add f_gwvertical=2 to include infiltration) |
| Simplest loss model | f_gwvertical=1 (bucket) |

## Bucket model (f_gwvertical=1, &list_gwflow_bucket)

The simplest model: moves surface water into per-cell subsurface
storage at a constant infiltration capacity.

| Parameter | Meaning |
|---|---|
| gw_infil_mmh | Infiltration capacity (mm/h) |
| gw_capacity | Subsurface storage capacity (columnar water depth, m) |

The infiltration in each step is the minimum of "infiltration capacity
x time", the surface water depth, and the remaining capacity.
**Cannot be combined with the lateral model** (it stops because the
capacity would be doubly defined; if you need a constant infiltration
capacity with soil depth as the capacity, use Green-Ampt with
gw_psif=0).

## Green-Ampt (f_gwvertical=2, &list_gwflow_greenampt)

Moves surface water into the soil layer at the infiltration capacity
of the Green-Ampt formula (piston approximation)
f_v = K_sv (1 + psi_f n_e / F). The storage capacity is soil depth x
specific yield. Saturated cells stop infiltrating, and the excess is
handled by the shallow-water side as surface water.

| Parameter | Meaning |
|---|---|
| gw_ksv_mmh | Vertical saturated hydraulic conductivity K_sv (mm/h) |
| gw_psif | Capillary pressure head at the wetting front psi_f (m). 0 degenerates to a constant infiltration capacity K_sv |
| fn_gw_ksv | Distribution map of K_sv (mm/h; if omitted, the uniform value gw_ksv_mmh is used) |
| fn_gw_psif | Distribution map of psi_f (m; if omitted, the uniform value gw_psif is used) |

K_sv and psi_f can be given as areal distributions by maps, following
the land use (permeable pavement, infiltration facilities,
bare/paved-surface distinctions, and so on). The map K_sv may be 0;
cells with 0 are impervious (fully paved). The uniform specification
(gw_ksv_mmh) still requires a positive value.

## Lateral flow (f_gwlateral=1, &list_gwflow_lateral)

Lateral Darcy flow in the saturated zone (2D, 8-neighbor; the same
diagonal partitioning as the ENC core). Groundwater moves along the
gradients of the terrain and the soil-layer base, and the excess of
cells exceeding the saturation capacity exfiltrates to the surface
(return flow = generation of saturation-excess overland flow).

| Parameter | Default | Meaning |
|---|---|---|
| gw_ksh_mmh | - | Lateral saturated hydraulic conductivity (mm/h) |
| gw_eps | 1e-3 | Regularization thickness for the dry test and suppression of excessive outflow (m) |
| gw_diagratio | 2/(2+sqrt(2)) | Diagonal partitioning (normally no need to change; 0 is equivalent to 4 neighbors) |

The stability condition of the explicit scheme is checked at
initialization; if dt exceeds the limit, the limit value is printed
and the run stops (lower dt or thin the updates with dt_gwflow).

## Weathered bedrock layer (f_gwlayer2=1, &list_gwflow_layer2)

Inserts a second layer directly below the soil layer to hold a
slow-recession component (baseflow) with a long residence time. Water
percolates down from layer 1, moves laterally within layer 2, the
saturation excess returns to layer 1, and the excess of layer 1
exfiltrates to the surface.

| Parameter | Default | Meaning |
|---|---|---|
| gw2_depth | - | Layer thickness (m) |
| gw2_sy | - | Specific yield (effective porosity) |
| gw2_infil_mmh | - | Infiltration capacity from layer 1 to layer 2 (mm/h) |
| gw2_ksh_mmh | - | Lateral saturated hydraulic conductivity of layer 2 (mm/h). 0 disables lateral flow (a capacity buffer) |
| gw2_sat0 | 0 | Initial saturation [0,1]. In event runs, a calibration parameter that sets the baseflow discharge |

- **Cannot be combined with the bucket vertical model.**
- For long runs, instead of specifying the initial saturation, we
  recommend **spin-up -> save -> reuse as the initial condition**
  (f_state_restore=2 in [Suspend and restart](restart.md)).
- Evapotranspiration does not touch layer 2.

## Conduit continuum layer (f_gwconduit=1, &list_gwflow_conduit)

Represents **subgrid conduit networks** - sewer networks, fractured
bedrock, karst, farmland tile drains - as an "artificial confined
aquifer" with a per-cell storage capacity and 8-direction conveyances
(equivalent continuum approximation). When a cell exceeds its capacity
(pipe-full), it switches to a pressurized state in which the head rises
steeply (a pseudo slot), representing pressurized flow (surcharge).
Applications are expressed by parameter combinations:

| Application | Typical settings |
|---|---|
| Urban sewer network | Inlet density given (fn_gwc_inlet); no interlayer exchange (use gwc_leak_layer=1 for infiltration/inflow) |
| Bedrock / karst | No inlet density (specify it for sinkholes); gwc_leak_layer=2 (exchange with the weathered bedrock layer) |

| Parameter | Default | Meaning |
|---|---|---|
| f_gwc_fluxlaw | 2 | Lateral flux law. 1: linear, 2: sqrt (turbulent conduit flow, q proportional to the square root of the gradient) |
| gwc_cnd_m2s / fn_gwc_cnd | 0 / - | Conveyance density (m2/s; pipe-full discharge per unit width at unit hydraulic gradient). Uniform value or a map. 0 disables lateral flow |
| gwc_cap / fn_gwc_cap | - | Storage capacity (columnar m; total pipe volume / cell area). Cells with 0 have no conduits |
| gwc_depth / fn_gwc_bot | - | Head datum (invert) elevation. Uniform burial depth (z - gwc_depth) or an elevation map |
| gwc_sy | - | Storage coefficient while unconfined (in-pipe filling; (0,1]) |
| gwc_slot_sy | - | Pseudo-slot storage coefficient while confined (<= gwc_sy; smaller = stiffer pressure response) |
| gwc_sat0 | 0 | Initial filling ratio [0,1] |
| gwc_inlet / fn_gwc_inlet | 0 / - | Density of stormwater inlets / manholes / sinkholes (1/m2). Specifying it enables surface exchange |
| gwc_cw | 2.66 | Weir coefficient for inflow (per inlet, q = cw h^1.5 m3/s) |
| gwc_co | 0.15 | Orifice coefficient Cd A (m2). Used for pipe-full inflow and pressurized eruption |
| gwc_leak_layer | 0 | Interlayer exchange partner. 0: none, 1: soil layer, 2: weathered bedrock layer |
| gwc_leak_mmh | - | Interlayer exchange capacity (mm/h). From the higher head to the lower |
| gwc_eps | 1e-3 | Regularization amount for the dry test (m) |
| gwc_eps_h | 1e-2 | Linearization width of the sqrt law (head difference, m) |
| gwc_diagratio | 2/(2+sqrt(2)) | Diagonal partitioning (normally no need to change) |

- Surface exchange switches automatically with the head difference: if
  the surface water level is higher, water flows in (weir type while
  unconfined, orifice type when pipe-full); if the conduit head exceeds
  the surface level while pressurized, water **erupts** (manhole
  surcharge to the surface).
- The stability condition of the explicit scheme is checked at
  initialization. The limit is governed by the pseudo slot gwc_slot_sy,
  so with fine grids and a small slot_sy, reduce dt_gwflow or relax
  slot_sy / gwc_eps_h.
- gwc_leak_layer=1 requires the soil-layer system (Green-Ampt or
  lateral) to be enabled; =2 requires f_gwlayer2=1.
- See test/conduit for schematic experiments (with an analytic
  equilibrium check).

**What it can and cannot do (range of the continuum approximation)**

- Can do: the **areal drainage capacity** of dense street-level
  networks, pressure propagation after pipe-full and the **spatial
  pattern of surcharge**, and the **two-way exchange** between the
  sewer system and surface inundation (dual drainage) - on the same
  grid and in the same time evolution as the surface water.
- Cannot do (limits in principle; see gwconduit_plan.md sec. 2):
  - **Tracking individual pipes and manholes.** It shows roughly where
    surcharge occurs, but cannot identify *which* manhole erupts.
  - **Control structures driven by operating rules** (pumps, weirs,
    outfalls, CSOs). They sit outside conservation laws plus
    gradient-driven flow, so a continuum cannot represent them
    (standalone structures are covered by
    [internal hydraulic structures](structure.md); networks dominated
    by them belong to dedicated 1-D pipe-network models).
  - **Systems dominated by a single trunk main** (catchments where one
    pipe larger than the cell size controls the behavior). The
    homogenization premise breaks down.
- Other constraints:
  - **Multiple conduit layers cannot be combined in one run** (e.g.
    sewers plus bedrock; single instance).
  - The invert elevation is fixed at the start of the run and does not
    follow terrain evolution (fn_geomorph). Evapotranspiration and
    water quality (solute transport) do not touch the conduit layer.
    No exchange with sea cells.

## Well pumping / groundwater abstraction (f_gwpump=1, &list_gwflow_pump)

A sink that withdraws the specified pumping rate from subsurface
storage at a set of cells and removes it from the system (the
subsurface counterpart of the internal source &list_bound_source; for
water-supply / agricultural abstraction, pumping-induced drawdown, and
pumping-induced seawater intrusion). Up to 50 wells, numbered
consecutively from 1.

| Parameter | Default | Meaning |
|---|---|---|
| gwp_cell(1:2,k,n) | - | Abstraction cells (i, j) of well n (multiple cells = well field / gallery) |
| fn_gwp_cell(n) | - | Cell list file (each line "i j"; takes precedence over inline) |
| gwp_q0(n) | - | Constant pumping rate (m3/s; positive = abstraction) |
| gwp_val(1:2,k,n) | - | Pumping rate time series (min, m3/s) (takes precedence over gwp_q0) |
| fn_gwp_val(n) | - | Time series file (each line "min m3/s"; highest precedence) |
| gwp_layer(n) | 1 | Abstraction layer. 1: soil layer, 2: weathered bedrock layer (requires f_gwlayer2=1) |

- The demand is **divided equally** over the cell set, and the
  withdrawal at each cell is capped by that cell's storage (a dry well
  = supply-limited; no redistribution to other cells). A per-well
  summary of demand vs. actual withdrawal is printed at the end of the
  run so you can check for dry wells.
- Combined with the [fresh and salt water layers](salt.md)
  (f_salt_gw=1), pumping takes **fresh water first** (shallow well
  screen approximation). Whatever the fresh thickness cannot supply is
  taken from the salt layer (= salt contamination of the well);
  pumping-induced seawater intrusion and upconing emerge automatically
  from the lateral flow and the salt-layer dynamics.
- Injection (negative rates) is not supported (return flow /
  irrigation to the surface is given with &list_bound_source in
  [Boundary conditions](boundary.md)).
- A well is a cell-scale sink (borehole-scale hydraulics - well
  radius, skin, partial penetration - are not represented).

## Infiltration suppression by frozen ground (f_gwfrost=1, &list_gwflow_frost)

To represent meltwater and rain running over frozen ground (snowmelt
floods, enhanced early-spring runoff), a **freezing index** FI
(degC.day) is accumulated per cell from the air temperature (fn_meteo
in [Rainfall and meteorology](forcing.md); lapse rate included), and a
reduction factor is applied to the vertical infiltration capacity
(Green-Ampt and bucket).

- Freezing index: freezing degree-days accumulate while the air
  temperature is below the threshold fro_tf, and thawing degree-days
  (times fro_ct) reduce it above the threshold (FI >= 0).
- Reduction factor (linear): fac = max(fro_fmin, 1 - FI/fro_fifull).
  The factor reaches its minimum (impervious if fro_fmin=0) at
  FI = fro_fifull.
- Snow insulation (optional): with fro_swe0 > 0 and snow enabled
  (fn_snow in [Rainfall and meteorology](forcing.md)), both freezing
  and thawing are attenuated by exp(-swe/fro_swe0) (under snow the
  ground cools - and thaws - more slowly).

| Parameter | Default | Meaning |
|---|---|---|
| fro_fifull | - | Freezing index at which the reduction factor reaches its minimum (degC.day). The practical calibration point |
| fro_fmin | 0 | Lower bound of the reduction factor [0,1). 0 = fully frozen ground is impervious |
| fro_tf | 0 | Freeze/thaw threshold air temperature (degC) |
| fro_ct | 1 | Thawing efficiency (multiplier on thawing degree-days). Smaller values delay the spring thaw |
| fro_swe0 | 0 | e-folding snow water equivalent of the snow insulation (m). 0 = no insulation |
| fro_fimax | 0 | Cap on the freezing index (degC.day). 0 = no cap. To keep the thaw from being unrealistically delayed after a long severe winter, about 1-2 x fro_fifull is recommended |
| fro_fi0 | 0 | Initial freezing index (degC.day). Set it to start an event run of the melt season "already frozen" |

- This is the simplest degree-day model (same philosophy as the
  degree-day snow model); soil temperature, frost depth, and unfrozen
  water are not solved. Fitting fro_fifull to observed runoff is the
  practical approach.
- The distribution of the reduction factor is output as `Ff0001`
  (1 = unfrozen, fro_fmin = fully frozen).
- The freezing index is a persistent state; across
  [Suspend and restart](restart.md) it is carried automatically by the
  private file gwflow_frost.dat (f_gwfrost must have been enabled at
  save time).

## Output and monitoring

- The distribution of subsurface storage depth can be output as
  `Hg0001` with `f_out_hg = 1` (also `Hg2` when layer 2 is enabled and
  `Hgc` when the conduit continuum layer is enabled).
- With groundwater enabled, the S column on the screen and in the log
  splits into three columns, **S_surf / S_grnd / S_total**, so the
  surface, subsurface, and total water budgets can be tracked
  separately.
- Restarting models with internal state is handled automatically
  through private state files (the models enabled at save time must
  also be enabled at restart time).

## Worked examples of the format

Annotated examples of all groups:
[examples/List_samples/list_gwflow.txt](../../../examples/List_samples/en/list_gwflow.txt).
For the overall picture of runoff computations combined with rainfall,
see [the rainfall and meteorology chapter](forcing.md).
