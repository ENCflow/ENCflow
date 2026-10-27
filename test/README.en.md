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
analytical-solution or conservation check by Check_*.py.

| Directory | Contents | Main features | Check |
|---|---|---|---|
| **Shallow water and channels** | | | |
| [wave/](wave/en/README.md) | A mound of water spreading over still water, the minimal example. Subject of tutorial 1 | Shallow water | ref |
| [chichibu/](chichibu/en/README.md) | Rain on the real Chichibu catchment. Subject of tutorial 2. Many derived cases for resolution, schemes and levees | Shallow water, channels, rainfall, records | ref |
| [chichibu_icmap/](chichibu_icmap/en/README.md) | Chichibu with a gradient map of the fixed interception ratio. Regression for the band distribution of map files when the domain-mask window does not start at the grid origin (§82) | Shallow water, rainfall, interception | ref |
| [dambreak/](dambreak/en/README.md) | Wet-bed dam break. Verification of the advection schemes against the Stoker solution | Shallow water | ref, analytic |
| [hillslope/](hillslope/en/README.md) | Comparison of advection schemes for hillslope flow: analytical solution and grid convergence | Shallow water, rainfall | analytic (scripts) |
| [bendloss/](bendloss/en/README.md) | Isolating the artificial loss at a 90° bend of a one-cell-wide channel | Channels, advection schemes | analytic |
| [diffusion/](diffusion/en/README.md) | Gaussian-jet benchmark of the momentum diffusion term (analytical solution, grid convergence) | Shallow water f_diffusion_term | analytic |
| **Non-hydrostatic correction** | | | |
| [nhwave/](nhwave/en/README.md) | Standing waves in a closed tank: measuring the numerical dispersion of the hydrostatic ENC scheme | Shallow water | ref |
| [nhwave_nh/](nhwave_nh/en/README.md) | The same tank with the one-layer non-hydrostatic correction | Non-hydrostatic | ref |
| [nhsolitary/](nhsolitary/en/README.md) | Propagation of a solitary wave (nonlinear verification) | Non-hydrostatic | ref |
| [nhcurrent/](nhcurrent/en/README.md) | Dispersion relation of linear waves on a uniform current | Non-hydrostatic, segment inflow, radiation boundary | ref |
| [nhshelf/](nhshelf/en/README.md) | Soliton fission of a solitary wave climbing a shelf; verification of the bottom-slope terms | Non-hydrostatic f_nh_slope | ref |
| [nhbore/](nhbore/en/README.md) | Undular bore splitting from a long-wave step | Non-hydrostatic | ref |
| [nhbreak/](nhbreak/en/README.md) | Run-up of a breaking solitary wave on a beach: breaking switch, eddy viscosity, wet-dry degeneration | Non-hydrostatic f_nh_breaking | ref |
| [nhbottom/](nhbottom/en/README.md) | Moving-bottom acceleration term: exact solution for a prescribed uplift, coupling with a submarine slide, prescribed bed motion | Non-hydrostatic f_nh_bottom, fn_bedmotion | ref |
| **Coast and tide** | | | |
| [tide/](tide/en/README.md) | Smoke test of the tidal boundary | Tide | ref |
| [coastal_drain/](coastal_drain/en/README.md) | Drainage of a polder below sea level (outfalls and pump stations) | Conduit continuum layer, tide | ref |
| [culvert/](culvert/en/README.md) | Passage through the three culvert regimes (drainage test; monotonic recovered discharge) | Structures | ref, analytic |
| [salt/](salt/en/README.md) | Fresh/salt two-layer experiments (final state of a lock exchange, sea boundary) | Fresh/salt two-layer | ref |
| **Groundwater and urban drainage** | | | |
| [gwdefault/](gwdefault/en/README.md) | Minimal input of each groundwater model and the display of defaults | Groundwater | screen output |
| [pump/](pump/en/README.md) | Linear drawdown by a well pumping sink (analytical check) | Groundwater | ref |
| [frost/](frost/en/README.md) | Linear reduction of infiltration by frozen ground (analytical check) | Groundwater, snow | ref |
| [conduit/](conduit/en/README.md) | Conduit continuum layer experiment (uniform, analytical equilibrium) | Conduit continuum layer | ref |
| [sewer_wq/](sewer_wq/en/README.md) | Sanitation risk of sewage eruption (water quality × conduit layer) | Conduit continuum layer, water quality | ref |
| **Rainfall, interception, Soil Water Index** | | | |
| [icevap/](icevap/en/README.md) | Minimal input of each interception and evapotranspiration model and the display of defaults | Interception, evapotranspiration | screen output |
| [swi/](swi/en/README.md) | Analytical reference of the Soil Water Index (JMA three-tank model) | Soil Water Index | analytic |
| [vzcol/](vzcol/en/README.md) | One VZ shared reference column: steady gravity drainage, depth-wise conservation, Kosugi model, agreement of zone weights with the cell-by-cell read-out, steady solution with a fixed-pressure bottom versus quadrature, time convergence, area-average mode, zero soil depth, hydrostatic initial condition | VZ runoff fn_vz | ref, analytic |
| [vzzone/](vzzone/en/README.md) | VZ zones, shared columns and outlets: receiving by the distribution ratios, a single addition to a shared receiving cell, S_total balance, bit-identical results for shared and duplicated columns, rain distribution with area averaging, stop of the strict mode, save → restart agreement | VZ runoff fn_vz | ref, analytic |
| **Sediment and landform change** | | | |
| [creep/](creep/en/README.md) | Gaussian-hill benchmark of hillslope creep (linear diffusion). Depth-dependent creep (creep_hstar): the limit of thick soil, supply limitation of thin soil, bare rock unchanged, and conservation | Sediment f_creep, creep_hstar | analytic |
| [hillsoil/](hillsoil/en/README.md) | Soil on hillslopes. Uniform and distributed (fn_wthr) soil production by weathering agree with the analytical solution to rounding, cells with multiplier 0 stay unchanged, input errors stop the run, restart round trip | Landform f_wthr, fn_wthr | analytic, self-check |
| [dissol/](dissol/en/README.md) | Limestone dissolution. The final ground elevation matches the analytic value for the three water sources (infiltration, sink inflow = doline term, rainfall); restart round trip with a save inside an update interval | Landform f_dissol, conduit continuum layer | ref, analytic |
| [fluvial/](fluvial/en/README.md) | Bedload Exner equation: smoke test and conservation (closed-domain dam break) | Sediment f_fluvial | analytic |
| [bankface/](bankface/en/README.md) | Dam-break flow in a channel with dry banks. Bed-load blocking on bank faces (dry banks stay unchanged) and the supply limiter on a thin soil layer (volume conservation) | bed load | analytic |
| [bendsed/](bendsed/en/README.md) | Bed-load direction correction in a 90° bend. Outer-bank scour and inner-bank deposition, left/right mirror symmetry, contrast with no correction | bed load fluv_slope, f_secflow | analytic |
| [berode/](berode/en/README.md) | Bank erosion in a channel with dry banks. Only the banks touching the channel retreat, the lost volume is linear in K_b, sediment is conserved | bed load f_berode | analytic |
| [repose/](repose/en/README.md) | A dry 45° sand cone collapses to the 30° angle of repose. Final slope and volume conservation | f_repose | analytic |
| [fixation/](fixation/en/README.md) | Fixation of a bar exposed at low flow. Analytic growth law, a fixed bar is not eroded by the flood, reset by cumulative erosion, the roughness increase slows the flow over the bar while the section discharge is conserved, supplied fines settle on the fixed bar, restart round trip | bed load and suspended load f_fixation, fix_cn | analytic, self-check |
| [bedfines/](bedfines/en/README.md) | Ledger of fines in the bed. 100 % fines is bit-identical to the feature off, bed load + suspended load keep 0 <= sf <= sd and conserve total solids and fines to machine precision, a purely coarse bed releases no suspended load, fines fed into a coarse channel leave a stock exactly equal to the deposit, the capacity feed keeps the inlet bed level and stock fixed, restart round trip | bed load and suspended load f_bedfines, fines_la, fines_frac0 | analytic, self-check |
| [sedfeed/](sedfeed/en/README.md) | Sediment feed at an inflow segment of a straight channel. Degradation wave without feed, the capacity feed (factor 1) fixes the inlet bed exactly, the inflow_qb ledger closes to machine precision, the equilibrium concentration feed matches C_eq of the inflow cells, creep does not count the open-boundary outflow a second time, the ledger of bed load at open boundaries closes with the bed change | bed load fluv_bcfeed, fluv_bcfeed_fac, inflow_qb, inflow_cs_eq | analytic, self-check |
| [rockinc/](rockinc/en/README.md) | Bedrock incision by flowing water. Analytical solution of self-cover, quasi-steady cover, hump of abrasion, conservation and ledgers in a closed box, the acceleration factor, restoring a bare-rock save and restart round trips, the steady long profile under uplift, τ_b of steep uniform flows (record) | Landform f_rockinc, fn_rock, fn_uplift | analytic, self-check |
| [wave_shore/](wave_shore/en/README.md) | Wave-driven longshore transport. A sinusoidal perturbation of a straight shoreline decays at the linear-theory rate (Ashton & Murray 2006) under low-angle waves and grows at the theoretical rate under high-angle waves (physical smoothing length wave_lsm; the cell-radius kernel is kept as a record of grid-scale bar growth); conservation, bit-identity when disabled | bed load fn_wave f_wave_longshore wave_lsm | analytic, self-check |
| [wave_river/](wave_river/en/README.md) | River-mouth rule wave_vmax. Reproduces the problem of a channel pool acting as a wave source so that longshore transport works on a riffle, and shows the rule keeps the channel unchanged while waves still act at sea | bed load fn_wave wave_vmax | self-check |
| [uniflow/](uniflow/en/README.md) | Uniform flow in straight channels 1 and 5 cells wide between dry ground. Matches Manning with f_opening_dynamic = 2; without the reassignment the bank-adjacent rows carry too little flow (known property recorded) | ENC conveyance, f_opening_dynamic | analytic |
| [suspend/](suspend/en/README.md) | Suspended load (advection, erosion, settling): smoke test and conservation | Sediment f_suspend | analytic |
| [wash/](wash/en/README.md) | Hillslope erosion (splash and sheet): smoke test and conservation | Sediment f_wash | conservation (Log) |
| [wetlw/](wetlw/en/README.md) | Lateral spreading of wet detachment wet_lw: conservation of total solids, reduced grid-scale roughness, MPI identity | Sediment wet_lw | self-check |
| [splash/](splash/en/README.md) | Analytical verification of dry hillslope erosion | Sediment f_splash | ref |
| [splashslide/](splashslide/en/README.md) | Cemented versus failing scarp (dry erosion combined with slope failure) | f_splash, f_slide | analytic |
| [splashlc/](splashlc/en/README.md) | Valley wavelength selection by the curvature correlation length spl_lc (growth of a two-wavelength perturbation) | f_splash (spl_lc, spl_zbase) | analytic |
| [splashstrata/](splashstrata/en/README.md) | Analytic check of the erodibility factors of horizontal strata spl_strata (3 layers: cap rock 0 / 0.5 / 1) | f_splash (spl_strata) | ref + analytic |
| [splashsat/](splashsat/en/README.md) | Analytic check of the saturation of the hollow amplification spl_ksat (parabolic trough, constant curvature) | f_splash (spl_ksat) | ref + analytic |
| [rockfall/](rockfall/en/README.md) | Rockfall and talus (collapse of a vertical plateau: conservation, final height differences <= H_c, talus budget; windowed, supported-face, undercut, sea-cell and bedrock rf_bedrock configurations) | f_rockfall | analytic |
| [sedinflow/](sedinflow/en/README.md) | Ledger check of the sediment-concentration time series of a segment inflow | Boundaries, sediment | analytic |
| **Debris flow, failure, volcanic flows, avalanches** | | | |
| [debris/](debris/en/README.md) | Debris flow (erosion-triggered): smoke test and conservation. Takahashi and Egashira types | Debris flow f_debris | analytic |
| [slide/](slide/en/README.md) | Instantaneous fluidisation (landslide type): smoke test, conservation, stability analysis | Slope failure f_release, f_slide | analytic |
| [volcano/](volcano/en/README.md) | Voellmy steady uniform-flow benchmark of volcanic flows (debris avalanche, pyroclastic flow) | Equivalent fluid | analytic |
| [curvature/](curvature/en/README.md) | With and without the curvature (centrifugal) term | Equivalent fluid f_dbcurv | analytic |
| [avalanche/](avalanche/en/README.md) | Dense-flow snow avalanche (equivalent fluid with velocity-proportional entrainment): smoke test and conservation | Equivalent fluid, snow | analytic |
| [bedslide/](bedslide/en/README.md) | Moving bed layer: debris avalanche plunging into a lake and its tsunami, a submarine slide, hand-over from a debris flow | Moving bed layer f_bedslide | analytic |
| **Driftwood and building destruction** | | | |
| [driftwood/](driftwood/en/README.md) | Mixed debris-flow and driftwood surge, washout by a flood, remobilisation | Driftwood fn_driftwood | analytic |
| [bldgdebris/](bldgdebris/en/README.md) | Building destruction by flood flow and debris: smoke test and conservation; combination with driftwood, void-ratio feedback | Building destruction fn_bldgdebris | analytic |
| [gvchange/](gvchange/en/README.md) | Unit test of the void-ratio change procedure (volume conservation; no time loop) | m_state_set_gv | unit test |
| **Water quality** | | | |
| [damwq/](damwq/en/README.md) | Steady-state check of completely mixed dam release and pond entrainment | Water quality, dams | ref, analytic |
| [tracer/](tracer/en/README.md) | Numerical diffusion of the first-order upwind scalar transport: spreading of a clean-water front (longitudinal) and lateral variance of a steady plume, against the modified-equation values | Water quality (scalar advection) | ref, analytic |
| [gwseep/](gwseep/en/README.md) | Steady-state check of lateral groundwater transport and seepage return | Water quality, groundwater | ref, analytic |
| [kdpart/](kdpart/en/README.md) | Steady-state check of Kd equilibrium two-phase partitioning | Water quality, suspended sediment | ref, analytic |
| **Glaciers and lava** | | | |
| [glacier/](glacier/en/README.md) | Halfar dome of SIA ice flow, cirque formation | Glaciers | analytic |
| [lava/](lava/en/README.md) | Huppert similarity solution of a Bingham lava flow, minimal input | Lava flow | analytic |
| **Nesting and BMI** | | | |
| [nest_twin/](nest_twin/) | Alternating two cases in one process reproduces the standalone runs (basis of multiple instances) | Multiple m_main instances | identity (script) |
| [nest_identity/](nest_identity/en/README.md) | 1:1 self-nesting identity (child interior == parent; two-way: root == standalone). Restart, conservative correction, groundwater | Nesting fn_nest | identity (driver) |
| [bmi_nest/](bmi_nest/en/README.md) | Multi-grid BMI exposure (grid ids, qualified names). Identity, re-initialize and same-value set from Python; bmi-tester | BMI, nesting | identity (Python), bmi-tester |
| **Input and output** | | | |
| [gtif/](gtif/en/README.md) | Test assets for the GeoTIFF reader (compression and coordinate-system variants) | GeoTIFF | unit test |
| Scripts/ | Common run engine and comparison scripts | — | — |

For the MPI rule (np = 1, 2, 4 must match the serial run) and the
allocation-bounds check (gfortran -fcheck=all), see
[CLAUDE.md](../CLAUDE.md) and [docs/developer.md](../docs/developer.md)
Sec. 3 and 11.
