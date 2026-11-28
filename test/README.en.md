# test/ — verification cases and regression tests

[日本語](README.md)

Verification cases, one or more per feature. They double as regression
tests: each has an automatic comparison against a reference, a script
that checks analytical solutions or conservation (Check_*.py), or both.
Teaching material is in [tutorials/](../tutorials/); worked examples by
phenomenon are in [examples/](../examples/README.en.md).

## How to run

```bash
cd test/<name>
make              # link the executables from bin/ (and build inputs where needed)
./Run.sh          # serial (OpenMP); compared against the reference when one exists
./Run_MPI.sh 4    # MPI with 4 ranks; the rule is that it matches the serial run
python3 Check_*.py   # analytical or conservation check (where provided)
```

Run.sh and Run_MPI.sh call the common engine
[Scripts/Run_case.sh](Scripts/Run_case.sh), which compares Log.txt and
the record CSV files with the reference (Compare_ref.sh). The reference
is updated (`-u`) only after a person has checked that the results are
right; a mismatch is diagnosed and reported (the absolute rule in
CLAUDE.md).

## Cases

"Check" column: ref = automatic comparison with the reference; analytic =
analytical-solution or conservation check by Check_*.py. "Contents" summarises what each case
checks; the configurations, numbers and pass criteria are in the README of each case.

| Directory | Contents | Main features | Check |
|---|---|---|---|
| **Shallow water and channels** | | | |
| [wave/](wave/en/README.md) | A mound of water spreading over still water, the minimal example. Subject of tutorial 1 | Shallow water | ref |
| [chichibu/](chichibu/en/README.md) | Rain on the real Chichibu catchment. Subject of tutorial 2. Many derived cases for resolution, schemes and levees | Shallow water, channels, rainfall, records | ref |
| [chichibu_cond/](chichibu_cond/en/README.md) | The Chichibu regression case with the standard inputs (elevation with a conditioned channel bed, channel roughness 0.04); it differs from the regression case of chichibu only in these two inputs | Shallow water, channels, rainfall, records | ref |
| [chichibu_icmap/](chichibu_icmap/en/README.md) | Chichibu with a gradient map of the fixed interception ratio. Regression for the band distribution of map files when the domain-mask window does not start at the grid origin (§82) | Shallow water, rainfall, interception | ref |
| [dambreak/](dambreak/en/README.md) | Wet-bed dam break. Verification of the advection schemes against the Stoker solution | Shallow water | ref, analytic |
| [hillslope/](hillslope/en/README.md) | On a smooth slope, a stepped slope and a V-shaped catchment, the difference in overland flow between advection schemes is separated out with the kinematic-wave analytical solution and grid convergence | Shallow water f_advection_scheme, f_govequation, rainfall | analytic (scripts) |
| [vshaped/](vshaped/en/README.md) | Rainfall runoff of a V-shaped catchment on a 20 m grid, placed at 0° and 45° to the grid, compared with the kinematic-wave theory | Shallow water, rainfall, measurement; orientation independence of the eight neighbours | analytic |
| [vchannel/](vchannel/en/README.md) | The cross-channel distribution and discharge of flow in a uniformly sloping V-shaped channel match the exact solution for flow directions of 0°, 22.5° and 45° | Shallow water, sediment flow; orientation independence of the eight neighbours; dynamic reassignment of blocked openings | analytic |
| [bendloss/](bendloss/en/README.md) | Isolating the artificial loss at a 90° bend of a one-cell-wide channel | Channels, advection schemes | analytic |
| [bankcap/](bankcap/en/README.md) | Water in a channel whose level is below a thinly wet bank does not climb the bank under the edge-depth cap, and the discharge does not swing back and forth when the level crosses the bank height (§108, §110.24, §113, §114) | Shallow water f_dry_head_cap | analytic |
| [bankhalo/](bankhalo/en/README.md) | In a closed box with a levee-lined channel, the water levels on both banks equalise over the deeply submerged levees, and N ranks and one rank give byte-identical results even when a band boundary crosses the channel (§128) | channel, levee, parallel | analytic |
| [bankspill/](bankspill/en/README.md) | As the channel level rises slowly, the level at which water starts to spill into a hollow in the bank does not depend on the time step and does not exceed the upstream energy head (§110.22–§110.24, §114) | Shallow water f_dry_head_cap | analytic |
| [chutepool/](chutepool/en/README.md) | Where supercritical flow falls over a drop in a steep channel into a deep pool, the discharge in the pool matches the given discharge and does not oscillate (§110.26, §110.30, §114) | Shallow water f_dry_head_cap | analytic |
| [cascade/](cascade/en/README.md) | A slowly increasing discharge given to a steep channel with successive drops: the head of the flow does not exceed the water level of the cell that gives the discharge, and the mass balance closes (§110.29, §110.30) | Shallow water f_dry_head_cap, advection scheme f_advection_lateral | analytic |
| [brink/](brink/en/README.md) | At a free overfall at a pond outlet in a one-cell-wide channel, the water-surface profile and the position of the hydraulic jump match the 1-D theory, the head does not exceed the pond with the treatment of the edge just after a bend, and a confluence pool settles to a steady state (§110, §113, §114) | Shallow water f_advection_bend | analytic |
| [wetbank/](wetbank/en/README.md) | A bank wetted by rain does not change the depth of a one-cell-wide raster channel oblique to the grid by more than 5 % beyond the inflow of the rain | Channels, advection f_advection_donor, f_advection_lateral | analytic |
| [wallpond/](wallpond/en/README.md) | Even with a still pond behind the virtual walls of channel levees and seawalls, the water level in front of the wall agrees within 1 mm with runs in which the far side is dry and with runs that resolve the levee (§134, §134.9, §134.10) | channel, levee fn_bank, seawall seawall0, advection scheme | analytic |
| [sliver/](sliver/en/README.md) | The channel level is the same with and without sub-grid channel cells of nearly zero width, the slivers left by occupancy fractions (§137) | channel (subgrid channel width), dynamic reassignment of blocked openings | analytic |
| [tjunction/](tjunction/en/README.md) | At a one-cell-wide T-junction, the depth of the main channel just upstream of the confluence is compared with the 1-D momentum theory, and the backwater does not depend on whether the banks are wet or on the grid orientation (§110.19, §110.22, §110.25, §113) | Channels, advection schemes f_advection_lateral, f_advection_donor, f_advection_bend | analytic |
| [stairbank/](stairbank/en/README.md) | A one-cell-wide channel oblique to the grid with high cells beside it: raising and lowering the discharge gives the same depth, the maximum velocity does not exceed that of the channel with walls only, and water does not climb into the wall cells (§112, §113) | Channels, advection schemes f_advection_donor, f_advection_bend, f_advection_lateral, f_dry_head_cap | analytic |
| [stageside/](stageside/en/README.md) | In a channel whose eastern column is a prescribed-stage group or a source, the water flowing out along the lateral Neumann edges becomes steady and uniform along the banks whatever the advection rules (§113.9) | Shallow water, stage-prescribed cells, sources, lateral Neumann, advection schemes f_advection_bend, f_advection_lateral | self-check |
| [slopefric/](slopefric/en/README.md) | Uniform thin-sheet flow and the sediment shear on steep slopes: the slope-parallel and the horizontally projected formulas hold whatever the slope orientation and with 8 or 4 neighbours (§91, §93) | Shallow water f_gravity_correction, bedload f_fluvial | analytic |
| [steepwave/](steepwave/en/README.md) | With a variable gravity g′ in the water-surface gradient term, a lake with steep shores stays at rest, and the arrival time of long waves and the speed of waves on a slope match the theory (§100) | Shallow water f_gravity_correction | analytic |
| [dbslope/](dbslope/en/README.md) | The uniform-flow depth of a mixture flow on a 30° slope matches the formulas of slope-parallel and horizontal evaluation for all five resistance laws (§28.18, §101) | Debris flow f_debris, shallow water f_gravity_correction | analytic |
| [diffusion/](diffusion/en/README.md) | Gaussian-jet benchmark of the momentum diffusion term (analytical solution, grid convergence) | Shallow water f_diffusion_term | analytic |
| [sublattice/](sublattice/en/README.md) | Diagonal circulations rotating in opposite senses in a frictionless closed tank, measuring per scheme the decay of the diagonal sub-lattice (checkerboard) mode of the momentum-conservative advection (§68.36) | Shallow water, advection schemes | self-check |
| [stg/](stg/en/README.md) | Operation check of the legacy STG grid: the water of rain on a closed slope is conserved, and a region mask or two or more MPI ranks stop the run at initialisation | Shallow water (STG) f_gridsystem | analytic |
| [inflowadv/](inflowadv/en/README.md) | With the rule for edges next to the outer cells of a segment inflow, the inflow row does not oscillate, no energy is created at the ends of the inflow segment or just downstream, and supercritical inflow is not throttled | Shallow water, segment inflow f_inflow_edge, advection schemes | analytic |
| **Non-hydrostatic correction** | | | |
| [nhwave/](nhwave/en/README.md) | A standing wave in a closed square tank, measuring the numerical dispersion of the hydrostatic ENC grid | Shallow water | ref |
| [nhwave_nh/](nhwave_nh/en/README.md) | The same tank as nhwave with the one-layer non-hydrostatic correction: the period of the standing wave matches the dispersion relation of the correction | Non-hydrostatic f_nonhydrostatic | ref |
| [nhsolitary/](nhsolitary/en/README.md) | A solitary wave propagating along a flat channel keeps its shape with the one-layer non-hydrostatic correction, and its speed matches the theory | Non-hydrostatic f_nonhydrostatic | ref |
| [nhcurrent/](nhcurrent/en/README.md) | The dispersion relation of small-amplitude waves on a uniform current matches the theory of the one-layer non-hydrostatic correction | Non-hydrostatic f_nonhydrostatic, segment inflow, radiation boundary | ref |
| [nhshelf/](nhshelf/en/README.md) | Soliton fission of a solitary wave running up a slope onto a shallow shelf, checking the bottom-slope term of the non-hydrostatic correction | Non-hydrostatic f_nh_slope | ref |
| [nhbore/](nhbore/en/README.md) | An undular bore whose steepening front splits into a wave train: the speed of the leading wave matches the theory | Non-hydrostatic f_nonhydrostatic | ref |
| [nhbreak/](nhbreak/en/README.md) | A breaking solitary wave running up a beach in the setup of Synolakis (1987), checking the breaking switch, eddy viscosity and wet-dry degeneration of the non-hydrostatic correction | Non-hydrostatic f_nh_breaking | ref |
| [nhbottom/](nhbottom/en/README.md) | Moving-bottom acceleration term: exact solution for a prescribed uplift, coupling with a submarine slide, prescribed bed motion | Non-hydrostatic f_nh_bottom, fn_bedmotion | ref, analytic |
| **Coast and tide** | | | |
| [tide/](tide/en/README.md) | Raising the tide: both drainage from the land and inundation of the land work, and writing the defaults or a list of distribution files does not change the results | Tide fn_tide | ref |
| [coastal_drain/](coastal_drain/en/README.md) | Drainage of a polder below the tide level: the negative pipe invert, the sea outfall and the pumping station of the conduit continuum layer work | Conduit continuum layer f_gwconduit, tide | ref |
| [culvert/](culvert/en/README.md) | Passage through the three culvert regimes (drainage test; monotonic recovered discharge) | Structures | ref, analytic |
| [damops/](damops/en/README.md) | The releases of each dam operation rule and of additional outlet works agree with the formulas and time series on every record row, with volume conservation and restart continuity | Structures (dams) f_dam_mode | ref, analytic |
| [salt/](salt/en/README.md) | Nine idealised fresh/salt two-layer experiments compared with analytical values: the final state of a lock exchange in the surface salt layer, the equilibrium of seawater intrusion, the exchange of salt water between the surface and the subsurface, and no salt water leaking across walls | Fresh/salt two-layer fn_salt, f_salt_surf, f_salt_exch | ref, analytic |
| [wfshoal/](wfshoal/en/README.md) | A beach profile of the coastal wave field: shoaling, breaking, refraction and random-wave breaking match theory or independent discrete solutions, and the ledger closes | Coastal wave field fn_wavefield | ref, analytic |
| [wfshadow/](wfshadow/en/README.md) | Two-dimensional coastal wave field: the shadow of a breakwater and an enclosure of diagonal walls. Agreement with an independently implemented sweep solution, blocking by diagonal walls, exactly sharp shadows for waves aligned with a lattice direction | Coastal wave field fn_wavefield | ref, analytic |
| [wfcurrent/](wfcurrent/en/README.md) | The action of the wave field on the flow: set-up, longshore currents and the roller match the theoretical balances, and the results do not change with the boundaries, the grid orientation or a restart | wf_flow of the coastal wave field fn_wavefield, boundary f_bc = 3, f_opening_dynamic | ref, analytic |
| [wfdoppler/](wfdoppler/en/README.md) | Change of the wave field by currents: the wave action flux on opposing and following currents matches the Doppler-shifted dispersion relation, and the blocking position and the ledger are correct | f_wf_current of the coastal wave field fn_wavefield | ref, analytic |
| [wfsed/](wfsed/en/README.md) | Stirring and transport of sediment by the wave field: the equilibrium concentration and transport rates match independent formulas, and the direction and distribution of longshore transport, the direction of erosion and recovery, and sediment conservation hold | f_wfsed, wfsed_facsk, wfsed_facas of fn_geomorph; sediment at lateral Neumann sides | ref, analytic |
| [wfswash/](wfswash/en/README.md) | Swash-zone transport: the amount of one update agrees with the formula of Larson et al. (2004), the foreshore moves towards the equilibrium slope without overshooting, and sediment is conserved in a closed basin | f_wfswash, wfswash_tanbe of fn_geomorph | analytic, self-check |
| **Groundwater and urban drainage** | | | |
| [gwdefault/](gwdefault/en/README.md) | In four groundwater configurations, the minimal input that omits the defaults and the input that writes all of them give byte-identical results, and the defaults are displayed as expected | Groundwater defaults of &list_gwflow | identity, screen output |
| [pump/](pump/en/README.md) | Well pumping: the demand equals the actual withdrawal, and the subsurface storage decreases linearly as the analytical value | Groundwater f_gwpump | ref, analytic |
| [frost/](frost/en/README.md) | The frozen-ground model, which lowers the infiltration capacity with a freezing index: under a constant air temperature the change of the subsurface storage agrees with the analytical solution to all digits | Groundwater f_gwfrost, snow | ref, analytic |
| [conduit/](conduit/en/README.md) | Two idealised experiments of the conduit continuum layer: the analytical equilibrium of a uniform field and the symmetry of full coupling | Conduit continuum layer f_gwconduit | ref, analytic |
| [sewer_wq/](sewer_wq/en/README.md) | A regression test following E. coli in sewage surcharged from the sewer in heavy rain as it spreads on the surface and dies off, with water quality coupled to the conduit continuum layer | Conduit continuum layer f_gwconduit, water quality fn_wq | ref |
| [gwbed/](gwbed/en/README.md) | Streambed exchange limit: the k_bed replacement of the vertical infiltration capacity of channel cells and the cap on the lateral-flow edge discharge between channel and non-channel cells agree with the analytical values (3 configurations; §16.5) | Groundwater f_gwbed | ref, analytic |
| [gwlateral/](gwlateral/en/README.md) | Lateral groundwater flow (non-linear Boussinesq) compared with the linearised solution: the spreading of a mound and the decay rate of undulations along a strip match the discrete prediction (§16.6) | Groundwater f_gwlateral, f_gw_opening | analytic |
| [gwtani/](gwtani/en/README.md) | Constant rain on a steep slope with a thin soil layer: the time of saturation matches the vertical arrival time, and the steady water table matches the kinematic discrete solution (§16.7) | Groundwater f_gwlateral, f_gwlayer2, f_gw_opening | analytic |
| [gwwidth/](gwwidth/en/README.md) | In cells with a sub-grid channel width, the volume exchanged between the subsurface and the surface is conserved and matches the total rain and a control without channel width, and evapotranspiration equals PET × area × time (§26.1, §27.1) | Groundwater f_gwlateral, f_gwconduit; channel width fn_width; evapotranspiration fn_evap; water quality | ref, analytic |
| [gwsect/](gwsect/en/README.md) | In cells with a cross-section shape σ, the volume exchanged between the surface, the subsurface and the water sources is conserved and matches the total rain, and evapotranspiration equals PET × area × time (§26.2, §27.1) | Channel section shape p_sect_m, groundwater f_gwlateral and f_gwconduit, snowmelt, evapotranspiration fn_evap, water quality | ref, analytic |
| **Rainfall, interception, Soil Water Index** | | | |
| [icevap/](icevap/en/README.md) | In three configurations of rainfall interception and evapotranspiration, the minimal input and the input with the defaults written out give byte-identical results, and the defaults are displayed as expected | Defaults of interception fn_intercept and evapotranspiration fn_evap | identity, screen output |
| [evapdry/](evapdry/en/README.md) | Suppression of evapotranspiration by soil dryness: the decline of subsurface storage after rain agrees with the analytical solution within rounding, and the water balance closes (§27.2) | evap_hglim of evapotranspiration fn_evap, groundwater (bucket), water quality | ref, analytic |
| [prmap/](prmap/en/README.md) | The interpretation of the time units of rainfall distributions and a save and restart in the middle of a frame, checked by the depth in a flat closed domain equalling the accumulated rain | Rainfall prtype, dt_mapunit, dt_maplist | analytic |
| [swi/](swi/en/README.md) | The JMA three-tank Soil Water Index compared with a finely integrated reference solution: the final value, the maximum over the period, its time and the spatial uniformity agree | Soil Water Index fn_swi | analytic |
| [vzcol/](vzcol/en/README.md) | One VZ shared reference column: gravity drainage, depth-wise conservation, the Kosugi model, the steady solution with a fixed-pressure bottom and time convergence agree with analytical solutions or quadrature | VZ runoff fn_vz | ref, analytic |
| [vzzone/](vzzone/en/README.md) | VZ zones, shared columns and outlets: water is received by the distribution ratios, the balance closes, shared and duplicated columns are bit-identical, and save and restart agree | VZ runoff fn_vz | ref, analytic |
| [sfzone/](sfzone/en/README.md) | Zone tanks of the storage function method: they match the exact solution of linear storage, the reference solution of the non-linear tank and the analytical recession, and the balance, save and restart, lag time, evapotranspiration and interception are handled correctly | Storage function method fn_sfm | ref, analytic |
| [paddy/](paddy/en/README.md) | The outlet laws of paddy-field dams match exact and reference solutions, water is conserved with paddy tanks and with resolved plots, and save and restart agree | Paddy-field dams fn_paddy | ref, analytic |
| **Sediment and landform change** | | | |
| [creep/](creep/en/README.md) | Gaussian-hill benchmark of hillslope creep (linear diffusion). Depth-dependent creep (creep_hstar): the limit of thick soil, supply limitation of thin soil, bare rock unchanged, and conservation | Sediment f_creep, creep_hstar | analytic |
| [hillsoil/](hillsoil/en/README.md) | Soil production by weathering agrees with the analytical solution to rounding, uplift, weathering and depth-dependent creep lead to a steady hillslope, and a restart round trip agrees | Landform f_wthr, fn_wthr, creep_hstar, f_uplift | analytic, self-check |
| [dissol/](dissol/en/README.md) | Limestone dissolution: for each water source (infiltration, sinks, rainfall, surface flow, recharge to the rock) and for lateral dissolution, the final ground elevation matches the analytical value | Landform f_dissol, conduit continuum layer | ref, analytic |
| [fluvial/](fluvial/en/README.md) | A collapsing water mound in a closed domain: the bed moves with bed load and the Exner equation, and the sediment volume is conserved | Sediment f_fluvial | analytic |
| [bankface/](bankface/en/README.md) | Dam-break flow in a channel with dry banks. Bed-load blocking on bank faces (dry banks stay unchanged) and the supply limiter on a thin soil layer (volume conservation) | bed load | analytic |
| [bendsed/](bendsed/en/README.md) | Bed-load direction correction in a 90° bend. Outer-bank scour and inner-bank deposition, left/right mirror symmetry, contrast with no correction | bed load fluv_slope, f_secflow | analytic |
| [berode/](berode/en/README.md) | Bank erosion in a channel with dry banks. Only the banks touching the channel retreat, the lost volume is linear in K_b, sediment is conserved | bed load f_berode | analytic |
| [repose/](repose/en/README.md) | A dry 45° sand cone collapses to the 30° angle of repose. Final slope and volume conservation | f_repose | analytic |
| [fixation/](fixation/en/README.md) | Fixation of a bar exposed at low flow: it follows the analytical growth law, a fixed bar is not eroded by floods, and cumulative erosion resets it | bed load and suspended load f_fixation, fix_cn | analytic, self-check |
| [bedfines/](bedfines/en/README.md) | The ledger of bed fines: 100 % fines is bit-identical to the disabled run, total solids and fines are conserved to machine precision, and the stock of supplied fines equals the deposition | bed load and suspended load f_bedfines, fines_la, fines_frac0 | analytic, self-check |
| [sedfeed/](sedfeed/en/README.md) | Sediment feed at a segment inflow of a straight channel: capacity feed fixes the bed at the inlet, the feed ledger closes to machine precision, and the outflow at an open boundary is not counted twice | bed load fluv_bcfeed, fluv_bcfeed_fac, inflow_qb, inflow_cs_eq | analytic, self-check |
| [bedmix/](bedmix/en/README.md) | Mixed grain sizes: when all classes have the same size the results match a single grain size, and armouring and the class-wise balances of outflow, feed and collapse close | bed load f_bedmix, bmix_*, inflow_qbfrac, fn_inflow_qbmix, f_out_bmix, f_suspend (mixed sizes), f_taupart, f_rockfall, rf_frac, creep_hstar, f_wave_longshore (mixed sizes) | analytic, self-check |
| [dbmix/](dbmix/en/README.md) | Debris flow combined with mixed grain sizes: when all classes have the same size the results match a single grain size, the class-wise balances close, and the selector that erodes only mobile classes works | landform f_debris + f_bedmix, inflow_csfrac, fn_inflow_csfrac, f_slide, fn_dbinit, f_dbsel, db_seltan | analytic, self-check |
| [taupart/](taupart/en/README.md) | Resistance partitioning on steep gravel beds: the bed-load ledger of a uniform-flow channel agrees within ±0.5 % with the transport formula through the relative-depth factor and with the effective shear formula (§89.30, §121) | Bed load f_taupart (partition of τ*, effective shear) | ref, analytic |
| [rockinc/](rockinc/en/README.md) | Bedrock incision by flowing water: it matches the analytical self-cover solution and the quasi-steady cover, is conserved in a closed box, and reaches a steady long profile under uplift | Landform f_rockinc, fn_rock, fn_uplift | analytic, self-check |
| [dbrock/](dbrock/en/README.md) | Rock erosion by debris flows: it matches the analytical self-cover solution, is conserved in a closed box, and runs alternating flood and debris-flow computations continuously | Landform rock_kdb of f_rockinc, f_debris | analytic, self-check |
| [wave_shore/](wave_shore/en/README.md) | A sinusoidal perturbation of a straight shoreline decays under low-angle waves and grows under high-angle waves at the rates of the linear theory of Ashton & Murray (2006) | bed load fn_wave f_wave_longshore wave_lsm | analytic, self-check |
| [wave_river/](wave_river/en/README.md) | River-mouth rule wave_vmax. Reproduces the problem of a channel pool acting as a wave source so that longshore transport works on a riffle, and shows the rule keeps the channel unchanged while waves still act at sea | bed load fn_wave wave_vmax | self-check |
| [uniflow/](uniflow/en/README.md) | Uniform flow in straight channels 1 and 5 cells wide between dry ground matches Manning with the dynamic reassignment of openings, and carries too little flow without it | ENC conveyance, f_opening_dynamic | analytic |
| [suspend/](suspend/en/README.md) | Suspended sediment: smoke test and conservation, and the balance of entrainment and settling in a uniform-flow channel, where the equilibrium concentration and the adaptation decay rate match the discrete prediction | Sediment f_suspend | analytic |
| [wash/](wash/en/README.md) | Uniform rain over a closed-domain dam break: raindrop and sheet erosion work, and the total solids are conserved | Sediment f_wash, f_suspend | conservation (Log) |
| [wetlw/](wetlw/en/README.md) | Lateral spreading of wet detachment wet_lw: conservation of total solids, reduced grid-scale roughness, MPI identity | Sediment wet_lw | self-check |
| [splash/](splash/en/README.md) | Rain on a slope with no overland flow: the depth of dry hillslope erosion matches the analytical solution | Sediment f_splash | ref |
| [splashslide/](splashslide/en/README.md) | With the same cliff and rain, valleys are cut into a consolidated cliff, while an unconsolidated cliff collapses and becomes smooth | f_splash, f_slide | analytic |
| [splashlc/](splashlc/en/README.md) | Valley wavelength selection by the curvature correlation length spl_lc (growth of a two-wavelength perturbation) | f_splash (spl_lc, spl_zbase) | analytic |
| [splashstrata/](splashstrata/en/README.md) | Analytic check of the erodibility factors of horizontal strata spl_strata (3 layers: cap rock 0 / 0.5 / 1) | f_splash (spl_strata) | ref + analytic |
| [stencil9/](stencil9/en/README.md) | The nine-point creep and the curvature of dry hillslope erosion with eight neighbours are isotropic, and the reassignment of diagonal shares blocked by walls matches the exact discrete solution (§96) | f_creep (creep_diagratio), f_splash (spl_diagratio) | analytic, self-check |
| [splashsat/](splashsat/en/README.md) | Analytic check of the saturation of the hollow amplification spl_ksat (parabolic trough, constant curvature) | f_splash (spl_ksat) | ref + analytic |
| [rockfall/](rockfall/en/README.md) | Rockfall from a vertical plateau and the talus: the volume is conserved, the final height difference is at most H_c, and the talus balance closes | f_rockfall | analytic |
| [sedinflow/](sedinflow/en/README.md) | A time series of sediment concentration or sediment discharge on a segment inflow: the total sediment that enters equals water volume × concentration to machine precision | Boundaries, sediment inflow_cs, inflow_qs | analytic |
| **Debris flow, failure, volcanic flows, avalanches** | | | |
| [debris/](debris/en/README.md) | Erosion-triggered debris flow: smoke test and conservation, the equilibrium concentration of uniform flow on slopes matching the theory, and the water ledger with groundwater closing (§28.15, §28.17, §28.18) | Debris flow f_debris | analytic |
| [slide/](slide/en/README.md) | Instantaneous fluidisation of the landslide type: smoke test and conservation, the ledger of retained water, and the factor of safety of the slope-stability check matching the formula (§28.17, §28.19) | Slope failure f_release, f_slide | analytic |
| [volcano/](volcano/en/README.md) | Voellmy steady uniform-flow benchmark of volcanic flows (debris avalanche, pyroclastic flow) | Equivalent fluid | analytic |
| [curvature/](curvature/en/README.md) | On a concave circular arc of a slope, the difference in the steady flow of a mixture with and without the curvature term matches the numerical solution of a one-dimensional ODE | Equivalent fluid f_dbcurv | analytic |
| [dbonset/](dbonset/en/README.md) | Rest and onset by yielding, the effective gravity on steep slopes and the steepest gradient of the slope-stability check do not depend on the slope orientation or on 8 or 4 neighbours (§28.16, §91, §92) | Mixture flow f_dbres, f_gravity_correction, f_slide | analytic |
| [avalanche/](avalanche/en/README.md) | A flowing avalanche that entrains the snow of its track, grows, stops and deposits, with the snow conserved throughout | Equivalent fluid f_dbres, f_dbed, snow | analytic |
| [bedslide/](bedslide/en/README.md) | Moving bed layer: debris avalanche plunging into a lake and its tsunami, a submarine slide, hand-over from a debris flow | Moving bed layer f_bedslide | analytic |
| **Driftwood and building destruction** | | | |
| [driftwood/](driftwood/en/README.md) | Mixed debris-flow and driftwood flow, washout by floods, remobilisation, and capture and jamming at structures and culvert inlets, with conservation of wood volume and the analytical backwater | Driftwood fn_driftwood, fn_dwtrap, culv_jam | analytic |
| [bldgdebris/](bldgdebris/en/README.md) | Building destruction by flood flow and debris: smoke test and conservation; combination with driftwood, void-ratio feedback | Building destruction fn_bldgdebris | analytic |
| [gvchange/](gvchange/en/README.md) | Unit test of the void-ratio change procedure (volume conservation; no time loop) | m_state_set_gv | unit test |
| [bldgdrag/](bldgdrag/en/README.md) | In uniform flow through a channel with buildings, the depth and velocity match the theoretical balance of the momentum equation including the building drag (§107) | Building-group drag fn_gv, fn_bb, cd, kk | analytic |
| **Water quality** | | | |
| [damwq/](damwq/en/README.md) | The ledger of water-quality substances carried by the fully mixed release of a dam and by entrainment into a pond agrees with the analytical solution to all digits | Water quality fn_wq, dams, ponds | ref, analytic |
| [tracer/](tracer/en/README.md) | Numerical diffusion of the first-order upwind scalar transport: spreading of a clean-water front (longitudinal) and lateral variance of a steady plume, against the modified-equation values | Water quality (scalar advection) | ref, analytic |
| [gwseep/](gwseep/en/README.md) | Along the path in which a water-quality substance infiltrates, moves laterally underground and seeps back to the surface, mass is conserved, the ledger closes and the concentration does not change | Water quality fn_wq, groundwater | ref, analytic |
| [kdpart/](kdpart/en/README.md) | Equilibrium partitioning between the dissolved and particulate phases: the input mass splits exactly into surface, subsurface and settled parts, and a larger Kd increases settling | Water quality wq_kd, f_wq_settle, suspended sediment | ref, analytic |
| [wqbound/](wqbound/en/README.md) | The water-quality ledger closes for exchanges with sea cells, open edges and prescribed-stage cells, and the water of prescribed-stage cells is treated as outside water | Water quality, boundary conditions | ref, analytic |
| [wqstruct/](wqstruct/en/README.md) | In closed compartments linked by pumps, culverts, diversions and withdrawals, the concentration of water-quality substances carried with the water does not change, and the ledger closes (§30.10) | Water quality, structures, internal sources, well pumping | ref, analytic |
| **Glaciers and lava** | | | |
| [glacier/](glacier/en/README.md) | Halfar dome of SIA ice flow, cirque formation, isotropy of the avalanche redistribution, erosion coupling length | Glaciers | analytic |
| [lava/](lava/en/README.md) | Lava flows compared with analytical solutions: the Huppert similarity solution, the Bingham stopping thickness, a plastic dome, solidification, temperature and more | Lava flow fn_lavaflow | analytic |
| **Nesting and BMI** | | | |
| [nest_twin/](nest_twin/) | Alternating two cases in one process reproduces the standalone runs (basis of multiple instances) | Multiple m_main instances | identity (script) |
| [nest_identity/](nest_identity/en/README.md) | 1:1 self-nesting identity (child interior == parent; two-way: root == standalone). Restart, conservative correction, groundwater | Nesting fn_nest | identity (driver) |
| [bmi_nest/](bmi_nest/en/README.md) | Multi-grid BMI exposure (grid ids, qualified names). Identity, re-initialize and same-value set from Python; bmi-tester | BMI, nesting | identity (Python), bmi-tester |
| [bmi_vars/](bmi_vars/en/README.md) | Acceptance test of the feature-dependent BMI variable table and of setting hg and swe: presence of variables, analytical values, same-value set, and rejection of invalid sets (§76) | BMI, groundwater, snow | identity (Python), bmi-tester |
| [bmi_dam/](bmi_dam/en/README.md) | Exposing dam quantities through BMI and external operation: a release given from outside agrees on every row with a time-series dam, and the sample controller and volume conservation hold (§133) | BMI, structures (dams) f_dam_mode = 6 | identity (Python), analytic, bmi-tester |
| **Input and output** | | | |
| [gtif/](gtif/en/README.md) | Test assets for the GeoTIFF reader (compression and coordinate-system variants) | GeoTIFF | unit test |
| [river_flowline/](river_flowline/en/README.md) | The pre-processing that moves a channel mask onto the flow lines of the elevation rebuilds the realigned masks of the four Chichibu grids byte for byte | Preprocessing utils/river_flowline | unit test |
| [fluxline/](fluxline/en/README.md) | Angle sweep of flux transects: a transect across from wall to wall matches the total discharge, and interior segments and parallel transects match the theoretical values (§24.3) | Transects of fn_record | analytic |
| Scripts/ | Common run engine and comparison scripts | — | — |

For the MPI rule (np = 1, 2, 4 must match the serial run) and the
allocation-bounds check (gfortran -fcheck=all), see
[CLAUDE.md](../CLAUDE.md) and [docs/developer.md](../docs/developer.md)
Sec. 3 and 11.
