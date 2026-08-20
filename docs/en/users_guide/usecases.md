# Use cases (lookup by phenomenon)

> English mirror of docs/users_guide/usecases.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

A lookup table from "the phenomenon you want to compute" to the
combination of features and the key settings. See each chapter for
details and the [full parameter index](params_index.md) for exact
parameter meanings. **Phenomena not yet supported (planned)** are
listed explicitly at the end.

The notes column contains only what a user should know for that use
case - the nature of the approximation, how to supply the data, and
accuracy caveats (blank = nothing special).

## Floods and inundation

| Phenomenon | Features | Key settings | Notes |
|---|---|---|---|
| River (fluvial) flood inundation | [Geographic information](geoinfo.md) + [Boundary conditions](boundary.md) (+ [Channels](channel.md), [Structures](structure.md)) | Terrain + inflow time series (bc_qin / inflow) | Preprocess real terrain with depression removal (utils/rmdepress_river). See the tutorial for discharge oscillations on flat channel reaches |
| Rain-on-grid inundation (pluvial) | [Rainfall and weather](forcing.md) | Put fn_precip (uniform/distributed) directly on the terrain | Represent losses physically with infiltration (Green-Ampt in [Groundwater](gwflow.md)) rather than runoff coefficients |
| Dam / farm-pond breach flood | Levees + breach in [Channels](channel.md) (+ initial condition) | Represent the reservoir as channel cells (rw) and the dam body as a levee (bank); give the breach as a crest time series (&list_channel_breach) | The breach widening process is an input (time series); erosion-driven self-widening is not predicted |
| Open levees (kasumi-tei), overflow levees, secondary levees, ring levees | Levees in [Channels](channel.md) | fn_bank / bank0 + openings f_bank_opening | Overflow widths, crest heights, and opening locations are given as data |
| Detention basins / retarding ponds | Terrain + [Channels](channel.md) + [Structures](structure.md) | Overflow levee (bank) + intake / drainage gates (culvert/gate) | |
| Urban flooding by wave overtopping | Source in [Boundary conditions](boundary.md) | Feed the overtopping discharge time series into cells behind the seawall with &list_bound_source | Waves and the overtopping rate themselves are not computed (supply externally estimated values) |

## Coasts and estuaries

| Phenomenon | Features | Key settings | Notes |
|---|---|---|---|
| Storm-surge / tsunami run-up | [Tide and sea level](tide.md) | Sea mask + tide/water-level time series | Offshore generation and propagation are received as water levels from outside |
| River tsunami (tsunami intrusion up a river) | [Tide and sea level](tide.md) + [Channels](channel.md) | Tsunami waveform on the sea cells at the river mouth | One water level per cell inside the channel (no cross-sectional variation) |
| Compound flooding (surge x river flood x heavy rain) | Superposition of tide + boundaries + rainfall | Just enable the features together | The ordering and coupling between processes is automatic (single time evolution) |
| Seawater intrusion into / retreat from aquifers | [Fresh and salt water layers](salt.md) + [Groundwater](gwflow.md) | fn_salt (f_salt_gw=1) + f_gwlateral=1 + sea mask | Sharp-interface approximation: no brackish water (mixing) is produced. Equilibrium follows Ghyben-Herzberg |
| Pumping-induced seawater intrusion / well salinization | [Fresh and salt water layers](salt.md) + pumping sink in [Groundwater](gwflow.md) | The above + f_gwpump=1 (coastal wells) | Pumping takes fresh water first (shallow well screen approximation); whatever the fresh thickness cannot supply appears as salt contamination of the well, and the induced wedge movement / upconing emerge automatically from the lateral flow and the salt-layer dynamics |
| Freshwater lenses (islands, sand bars) | [Fresh and salt water layers](salt.md) + rainfall/infiltration | Recharge (rain + Green-Ampt) + sea mask | Lens thickness is set by the recharge-to-K_sh ratio (spin-up recommended) |
| Estuarine salt wedge | [Fresh and salt water layers](salt.md) (f_salt_surf=1) | River inflow (fresh) + tide (salt) | Targets the quasi-steady wedge position and its response (no internal-wave inertia). The advection share salt_alpha is the practical calibration point |
| Tidal response of coastal aquifers | [Fresh and salt water layers](salt.md) + [Tide and sea level](tide.md) | The tide series directly becomes the subsurface sea-side boundary head | The sea-subsurface connection exists only through the fresh/salt module |
| Where run-up seawater ends up (areal salt distribution) | [Fresh and salt water layers](salt.md) + [Tide and sea level](tide.md) | Run-up seawater is tracked automatically as salt water (Hss output) | Currently up to the surface extent; the path where it infiltrates and contaminates soil/aquifer (complete salt-damage analysis) is planned (below) |
| Polder / lowland drainage by pumping stations | Levees in [Channels](channel.md) + [Structures](structure.md) + [Tide and sea level](tide.md) | Enclose with levees and pump to the outer water (sea / channel) | |

## Urban

| Phenomenon | Features | Key settings | Notes |
|---|---|---|---|
| Pluvial flooding including sewer drainage and surcharge (dual drainage) | Conduit continuum layer in [Groundwater](gwflow.md) | f_gwconduit=1 + capacity, conveyance, inlet density | Reproduces the areal drainage capacity and the spatial pattern of surcharge (does not identify *which* manhole erupts). Networks dominated by operated structures (pumps, CSOs) or by a single trunk main are out of scope |
| Storage effect of underground detention / storm trunks | Conduit continuum layer | Give large cap and conveyance along the relevant cell strings | Tracking a single trunk main is a weak point (continuum approximation) |
| Rainwater storage/infiltration facilities, green infrastructure, permeable pavement | [Structures](structure.md) and ponds (rscap) + infiltration maps ([Groundwater](gwflow.md)) | Represent storage with structures/ponds, and infiltration with map input of the Green-Ampt parameters (fn_gw_ksv / fn_gw_psif) | Give the K_sv map by land use, from 0 (fully paved = impervious) up to large values (infiltration facilities). The internal structure of a facility is not represented (expressed as per-cell infiltration capacity and storage) |

## Catchment hydrology and groundwater

| Phenomenon | Features | Key settings | Notes |
|---|---|---|---|
| Rainfall runoff (flood runoff analysis) | [Rainfall and weather](forcing.md) + [Groundwater](gwflow.md) | Green-Ampt + lateral flow (f_gwlateral=1) | |
| Baseflow / low-flow recession | Weathered bedrock layer in [Groundwater](gwflow.md) | f_gwlayer2=1 + spin-up via [Suspend and restart](restart.md) | In event runs the initial saturation gw2_sat0 is the practical calibration point |
| Catchment water balance / recharge estimates | [Rainfall and weather](forcing.md) (evapotranspiration) + [Groundwater](gwflow.md) | Track S_surf/S_grnd/S_total over a long run | The S columns are domain-mean storage depths (m); their differences give the net balance |
| Farmland tile drainage | Conduit continuum layer | The tile-drain preset with gwc_leak_layer=1 (exchange with the soil layer) | |
| Well pumping / groundwater drawdown | Pumping sink in [Groundwater](gwflow.md) | f_gwpump=1 + well cells + rate (gwp_cell / gwp_q0 / gwp_val) | Withdrawal is capped by the cell's storage (check dry wells in the demand-vs-pumped summary printed at the end). Borehole-scale hydraulics (well radius, skin, etc.) are not represented |

## Sediment, slopes, and volcanoes

| Phenomenon | Features | Key settings | Notes |
|---|---|---|---|
| Rainfall-induced slope failure -> debris flow -> inundation | [Sediment and landform change](geomorph.md) + [Groundwater](gwflow.md) | f_slide + infiltration (Green-Ampt) + lateral flow | The stability judgment is driven by the groundwater level (pore pressure) - enable infiltration to make it truly "rainfall-induced" |
| Sector collapse -> channel blockage (landslide dam) -> outburst flood | [Sediment and landform change](geomorph.md) | f_release / f_slide + debris flow + deposition | The deposited terrain dams the flow automatically (two-way coupling of terrain and flow) |
| Landslide / sector-collapse-generated tsunamis (surges in reservoirs, landslide-dammed lakes, bays) | [Sediment and landform change](geomorph.md) + a water body (initial level f_htype=2 or [Tide and sea level](tide.md)) | Give the failing mass with fn_dbinit / f_slide (no extra settings - entry, wave generation, propagation, and run-up are automatic) | The wave is generated by the volume and momentum of the entering mixture and by the bed rise from deposition (depth is preserved, so the water surface lifts). Being a non-dispersive long-wave model, near-field waveforms and peak heights in deep water bodies where dispersion matters are limited (reservoirs and narrow bays, where the long-wave approximation holds, are the right scale). After entry the sediment moves with the water column - it does not separate into an underwater density current |
| Reservoir sedimentation and sediment flushing | [Sediment and landform change](geomorph.md) + [Structures](structure.md) | Suspended load (f_suspend) + dam operation | Flushing-gate operation is given as a time series |
| Riverbed evolution / river-mouth bar flushing | [Sediment and landform change](geomorph.md) + [Tide and sea level](tide.md) | Bedload and suspended load + floods / tide | |
| Lahars and snowmelt-type mudflows | [Sediment and landform change](geomorph.md) + snow ([Rainfall and weather](forcing.md)) | Debris-flow resistance laws + meltwater | Dilute systems (pyroclastic surges, ash transport) are out of scope |
| Valley formation on badlands and pyroclastic cones (highly permeable slopes with no surface runoff) | [Sediment and landform change](geomorph.md) | f_splash (dry-slope erosion) + infiltration (Green-Ampt); combine with weak f_creep to select the valley spacing | Even where all rainfall infiltrates and no overland flow occurs, valleys grow from cliff margins through the hollow-amplification feedback of rainsplash + subgrid rills. Cohesion (combine with f_slide) decides whether valleys form at all |

## Snow and ice

| Phenomenon | Features | Key settings | Notes |
|---|---|---|---|
| Snowmelt floods, rain-on-snow | Snow in [Rainfall and weather](forcing.md) | fn_snow + air temperature (lapse rate) | Degree-day method (energy balance not implemented) |
| Infiltration suppression by frozen ground (meltwater running over frozen soil) | Frozen ground (f_gwfrost) in [Groundwater](gwflow.md) + temperature (+ snow) | f_gwfrost=1 + fro_fifull (+ fro_swe0 for snow insulation, fro_fi0 to start "already frozen") | The simplest model - a degree-day freezing index reduces the infiltration capacity (soil temperature and frost depth are not solved). fro_fifull is the practical calibration point |
| Glacial lake outburst floods (GLOF) | [Glaciers](glacier.md) + terrain + breach in [Channels](channel.md) | Represent the glacial lake as impounded terrain; give the breach as a crest time series | The breach trigger and widening are inputs |
| Glacier retreat / cirque formation (long term) | [Glaciers](glacier.md) + long runs | Repeated representative years x morfac x restart chains | |

## Water quality

| Phenomenon | Features | Key settings | Notes |
|---|---|---|---|
| Pollutant load runoff / first flush | [Water quality](wq.md) | Buildup-washoff + advection | |
| Coliform, nutrient, pesticide runoff (first-order approximation) | [Water quality](wq.md) | Match decay coefficients and settling velocities to the substance | Reactions are first-order decay and settling only (no ecosystem / reaction networks). Concentrations are fully mixed (no vertical profile) |

## Long-term landforms

| Phenomenon | Features | Key settings | Notes |
|---|---|---|---|
| Landform evolution / erosion rates (hydraulics-driven LEM) | Long-term features of [Sediment and landform change](geomorph.md) | Weathering, uplift + cyclic forcing + morfac | |

## Not yet supported (planned)

The following are recognized user needs, planned as extensions that fit
the existing framework (order and timing undecided).

| Phenomenon | Current state | Planned form |
|---|---|---|
| Wind-driven flow / wind setup (bays, lakes, wide floodplains) | No wind stress term | Wind stress in the momentum equations + wind input (extension of the weather forcing) |
| Complete salt-damage analysis (contamination of soil/aquifer by infiltrated seawater) | Possible up to the areal extent of run-up seawater (above) | Fresh/salt partitioning of infiltration and evapotranspiration |
| Paddy field dams (runoff suppression by outlet restriction) | Can be approximated by storage + orifices, but no standard recipe | Under consideration |
| Online coupling with 1-D pipe-network models, explicit tracking of large trunk mains | Out of scope (beyond the continuum approximation) | Under consideration as external coupling / a trunk hybrid |
