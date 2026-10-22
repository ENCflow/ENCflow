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
| [wave/](wave/) | A mound of water spreading over still water, the minimal example. Subject of tutorial 1 | Shallow water | ref |
| [chichibu/](chichibu/) | Rain on the real Chichibu catchment. Subject of tutorial 2. Many derived cases for resolution, schemes and levees | Shallow water, channels, rainfall, records | ref |
| [chichibu_icmap/](chichibu_icmap/) | Chichibu with a gradient map of the fixed interception ratio. Regression for the band distribution of map files when the domain-mask window does not start at the grid origin (§82) | Shallow water, rainfall, interception | ref |
| [dambreak/](dambreak/) | Wet-bed dam break. Verification of the advection schemes against the Stoker solution | Shallow water | ref, analytic |
| [hillslope/](hillslope/) | Comparison of advection schemes for hillslope flow: analytical solution and grid convergence | Shallow water, rainfall | analytic (scripts) |
| [bendloss/](bendloss/) | Isolating the artificial loss at a 90° bend of a one-cell-wide channel | Channels, advection schemes | analytic |
| [diffusion/](diffusion/) | Gaussian-jet benchmark of the momentum diffusion term (analytical solution, grid convergence) | Shallow water f_diffusion_term | analytic |
| **Non-hydrostatic correction** | | | |
| [nhwave/](nhwave/) | Standing waves in a closed tank: measuring the numerical dispersion of the hydrostatic ENC scheme | Shallow water | ref |
| [nhwave_nh/](nhwave_nh/) | The same tank with the one-layer non-hydrostatic correction | Non-hydrostatic | ref |
| [nhsolitary/](nhsolitary/) | Propagation of a solitary wave (nonlinear verification) | Non-hydrostatic | ref |
| [nhcurrent/](nhcurrent/) | Dispersion relation of linear waves on a uniform current | Non-hydrostatic, reach inflow, radiation boundary | ref |
| [nhshelf/](nhshelf/) | Soliton fission of a solitary wave climbing a shelf; verification of the bottom-slope terms | Non-hydrostatic f_nh_slope | ref |
| [nhbore/](nhbore/) | Undular bore splitting from a long-wave step | Non-hydrostatic | ref |
| [nhbreak/](nhbreak/) | Run-up of a breaking solitary wave on a beach: breaking switch, eddy viscosity, wet-dry degeneration | Non-hydrostatic f_nh_breaking | ref |
| [nhbottom/](nhbottom/) | Moving-bottom acceleration term: exact solution for a prescribed uplift, coupling with a submarine slide, prescribed bed motion | Non-hydrostatic f_nh_bottom, fn_bedmotion | ref |
| **Coast and tide** | | | |
| [tide/](tide/) | Smoke test of the tidal boundary | Tide | ref |
| [coastal_drain/](coastal_drain/) | Drainage of a polder below sea level (outfalls and pump stations) | Conduit continuum layer, tide | ref |
| [culvert/](culvert/) | Passage through the three culvert regimes (drainage test; monotonic recovered discharge) | Structures | ref, analytic |
| [salt/](salt/) | Fresh/salt two-layer experiments (final state of a lock exchange, sea boundary) | Fresh/salt two-layer | ref |
| **Groundwater and urban drainage** | | | |
| [gwdefault/](gwdefault/) | Minimal input of each groundwater model and the display of defaults | Groundwater | screen output |
| [pump/](pump/) | Linear drawdown by a well pumping sink (analytical check) | Groundwater | ref |
| [frost/](frost/) | Linear reduction of infiltration by frozen ground (analytical check) | Groundwater, snow | ref |
| [conduit/](conduit/) | Conduit continuum layer experiment (uniform, analytical equilibrium) | Conduit continuum layer | ref |
| [sewer_wq/](sewer_wq/) | Sanitation risk of sewage eruption (water quality × conduit layer) | Conduit continuum layer, water quality | ref |
| **Rainfall, interception, Soil Water Index** | | | |
| [icevap/](icevap/) | Minimal input of each interception and evapotranspiration model and the display of defaults | Interception, evapotranspiration | screen output |
| [swi/](swi/) | Analytical reference of the Soil Water Index (JMA three-tank model) | Soil Water Index | analytic |
| **Sediment and landform change** | | | |
| [creep/](creep/) | Gaussian-hill benchmark of hillslope creep (linear diffusion) | Sediment f_creep | analytic |
| [dissol/](dissol/) | Limestone dissolution. The final ground elevation matches the analytic value for the three water sources (infiltration, sink inflow = doline term, rainfall); restart round trip with a save inside an update interval | Landform f_dissol, conduit continuum layer | ref, analytic |
| [fluvial/](fluvial/) | Bedload Exner equation: smoke test and conservation (closed-domain dam break) | Sediment f_fluvial | analytic |
| [bankface/](bankface/) | Dam-break flow in a channel with dry banks. Bed-load blocking on bank faces (dry banks stay unchanged) and the supply limiter on a thin soil layer (volume conservation) | bed load | analytic |
| [bendsed/](bendsed/) | Bed-load direction correction in a 90° bend. Outer-bank scour and inner-bank deposition, left/right mirror symmetry, contrast with no correction | bed load fluv_slope, f_secflow | analytic |
| [berode/](berode/) | Bank erosion in a channel with dry banks. Only the banks touching the channel retreat, the lost volume is linear in K_b, sediment is conserved | bed load f_berode | analytic |
| [repose/](repose/) | A dry 45° sand cone collapses to the 30° angle of repose. Final slope and volume conservation | f_repose | analytic |
| [rockfall/](rockfall/) | A rock pillar collapses into debris down to the stable rock angle. Agreement with an independent implementation of the recursion and rock-volume conservation | f_rockfall | ref, analytic |
| [fixation/](fixation/) | Fixation of a bar exposed at low flow. Analytic growth law, a fixed bar is not eroded by the flood, reset by cumulative erosion, the roughness increase slows the flow over the bar while the section discharge is conserved, supplied fines settle on the fixed bar, restart round trip | bed load and suspended load f_fixation, fix_cn | analytic, self-check |
| [bedfines/](bedfines/) | Ledger of fines in the bed. 100 % fines is bit-identical to the feature off, bed load + suspended load keep 0 <= sf <= sd and conserve total solids and fines to machine precision, a purely coarse bed releases no suspended load, fines fed into a coarse channel leave a stock exactly equal to the deposit, the capacity feed keeps the inlet bed level and stock fixed, restart round trip | bed load and suspended load f_bedfines, fines_la, fines_frac0 | analytic, self-check |
| [sedfeed/](sedfeed/) | Sediment feed at an inflow segment of a straight channel. Degradation wave without feed, the capacity feed (factor 1) fixes the inlet bed exactly, the inflow_qb ledger closes to machine precision, the equilibrium concentration feed matches C_eq of the inflow cells | bed load fluv_bcfeed, fluv_bcfeed_fac, inflow_qb, inflow_cs_eq | analytic, self-check |
| [uniflow/](uniflow/) | Uniform flow in straight channels 1 and 5 cells wide between dry ground. Matches Manning with f_opening_dynamic = 2; without the reassignment the bank-adjacent rows carry too little flow (known property recorded) | ENC conveyance, f_opening_dynamic | analytic |
| [suspend/](suspend/) | Suspended load (advection, erosion, settling): smoke test and conservation | Sediment f_suspend | analytic |
| [wash/](wash/) | Hillslope erosion (splash and sheet): smoke test and conservation | Sediment f_wash | conservation (Log) |
| [splash/](splash/) | Analytical verification of dry hillslope erosion | Sediment f_splash | ref |
| [splashslide/](splashslide/) | Cemented versus failing scarp (dry erosion combined with slope failure) | f_splash, f_slide | analytic |
| [splashlc/](splashlc/) | Valley wavelength selection by the curvature correlation length spl_lc (growth of a two-wavelength perturbation) | f_splash (spl_lc, spl_zbase) | analytic |
| [sedinflow/](sedinflow/) | Ledger check of the sediment-concentration time series of a reach inflow | Boundaries, sediment | analytic |
| **Debris flow, failure, volcanic flows, avalanches** | | | |
| [debris/](debris/) | Debris flow (erosion-triggered): smoke test and conservation. Takahashi and Egashira types | Debris flow f_debris | analytic |
| [slide/](slide/) | Instantaneous fluidisation (landslide type): smoke test, conservation, stability analysis | Slope failure f_release, f_slide | analytic |
| [volcano/](volcano/) | Voellmy steady uniform-flow benchmark of volcanic flows (debris avalanche, pyroclastic flow) | Equivalent fluid | analytic |
| [curvature/](curvature/) | With and without the curvature (centrifugal) term | Equivalent fluid f_dbcurv | analytic |
| [avalanche/](avalanche/) | Dense-flow snow avalanche (equivalent fluid with velocity-proportional entrainment): smoke test and conservation | Equivalent fluid, snow | analytic |
| [bedslide/](bedslide/) | Moving bed layer: debris avalanche plunging into a lake and its tsunami, a submarine slide, hand-over from a debris flow | Moving bed layer f_bedslide | analytic |
| **Driftwood and building destruction** | | | |
| [driftwood/](driftwood/) | Mixed debris-flow and driftwood surge, washout by a flood, remobilisation | Driftwood fn_driftwood | analytic |
| [bldgdebris/](bldgdebris/) | Building destruction by flood flow and debris: smoke test and conservation; combination with driftwood, void-ratio feedback | Building destruction fn_bldgdebris | analytic |
| [gvchange/](gvchange/) | Unit test of the void-ratio change procedure (volume conservation; no time loop) | m_state_set_gv | unit test |
| **Water quality** | | | |
| [damwq/](damwq/) | Steady-state check of completely mixed dam release and pond entrainment | Water quality, dams | ref, analytic |
| [tracer/](tracer/) | Numerical diffusion of the first-order upwind scalar transport: spreading of a clean-water front (longitudinal) and lateral variance of a steady plume, against the modified-equation values | Water quality (scalar advection) | ref, analytic |
| [gwseep/](gwseep/) | Steady-state check of lateral groundwater transport and seepage return | Water quality, groundwater | ref, analytic |
| [kdpart/](kdpart/) | Steady-state check of Kd equilibrium two-phase partitioning | Water quality, suspended sediment | ref, analytic |
| **Glaciers and lava** | | | |
| [glacier/](glacier/) | Halfar dome of SIA ice flow, cirque formation | Glaciers | analytic |
| [lava/](lava/) | Huppert similarity solution of a Bingham lava flow, minimal input | Lava flow | analytic |
| **Nesting and BMI** | | | |
| [nest_twin/](nest_twin/) | Alternating two cases in one process reproduces the standalone runs (basis of multiple instances) | Multiple m_main instances | identity (script) |
| [nest_identity/](nest_identity/) | 1:1 self-nesting identity (child interior == parent; two-way: root == standalone). Restart, conservative correction, groundwater | Nesting fn_nest | identity (driver) |
| [bmi_nest/](bmi_nest/) | Multi-grid BMI exposure (grid ids, qualified names). Identity, re-initialize and same-value set from Python; bmi-tester | BMI, nesting | identity (Python), bmi-tester |
| **Input and output** | | | |
| [gtif/](gtif/) | Test assets for the GeoTIFF reader (compression and coordinate-system variants) | GeoTIFF | unit test |
| Scripts/ | Common run engine and comparison scripts | — | — |

For the MPI rule (np = 1, 2, 4 must match the serial run) and the
allocation-bounds check (gfortran -fcheck=all), see
[CLAUDE.md](../CLAUDE.md) and [docs/developer.md](../docs/developer.md)
Sec. 3 and 11.
