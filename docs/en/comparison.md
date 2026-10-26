> English mirror of docs/comparison.md. The Japanese file is the master copy.

# Comparison with Other Simulation Software (comparison.md)

Survey as of 2026-08-10, updated since (source-check dates are
noted inline). It assumes the current state of ENCflow's feature
implementation (complete up to shallow water + channels + structures
+ runoff + evapotranspiration + two-layer groundwater + sediment +
water quality + buildup-washoff + snow + long-term landscape
evolution + driftwood + building destruction and debris + the
non-hydrostatic correction + prescribed bed motion for fault tsunamis +
multi-level nesting + meandering-channel development + rockfall and talus +
wave-driven longshore transport (stage 1) + limestone dissolution (karst);
including the 2026-10-22
alignment of the sea-mask semantics (not solved, level prescribed, outflow
to the sea leaves the ledgers) across all modules; updated 2026-10-23).
Licenses and distribution forms can change, so re-check each official
site before citing.

## 1. Comparison of distribution forms

| Model | Developer | Cost | Code | Notes |
|---|---|---|---|---|
| **ENCflow** | (this project) | Free | Fully open | Basic policy is developer.md Sec. 0. Ships agent-oriented groundwork (Sec. 3). Implements CSDMS BMI 2.0 (passes bmi-tester; optional adapter, core stays dependency-free; 2026-08-29) |
| RRI | ICHARM/PWRI | Free | Open (own terms) | Copyright-notice obligation; commercial use by permission. iRIC-version solver also published |
| iRIC (Nays2DFlood etc.) | iRIC organization | Free | Main solvers open | Platform of GUI + solver suite |
| Morpho2DH | Takebayashi (DPRI, Kyoto Univ.) / iRIC | Free | Closed (distributed via iRIC) | Morpho2D (2D bed deformation) + debris/mud flow. Considers structures such as sabo dams |
| HEC-RAS 2D | USACE (US Army) | Free | Closed | One of the de facto standards in practice. Catchment hydrology is delegated to HEC-HMS |
| LISFLOOD-FP 8 | University of Bristol | Free | Open (GPL) | Subgrid channels, GPU |
| CAESAR-Lisflood | UK universities | Free | Open (GPL) | LISFLOOD-FP hydraulics + landscape evolution (hours to millennia) |
| SFINCS | Deltares | Free | Open (GPLv3; GitHub Deltares/SFINCS; Fortran) | Reduced-complexity shallow-water model for compound flooding (storm surge, waves, rainfall, rivers). Local inertia equations (advection term optional) + subgrid topography + quadtree grid, GPU (OpenACC). HydroMT-SFINCS builds the inputs automatically; links with Delft Dashboard and FloodAdapt. Leijnse et al. (2021), van Ormondt et al. (2025) |
| TELEMAC-2D (+GAIA) | EDF-led | Free | Open (GPLv3) | Unstructured FE/FV. Sediment via GAIA. No catchment hydrology |
| Delft3D FM | Deltares | Kernel free | Kernel open (GPLv3) | GUI distributed free but under license management. Includes sediment (MOR) and water quality (WAQ) |
| MIKE 21 / MIKE SHE | DHI | Commercial | Closed | Integrated hydrology (SHE) is the most comprehensive, snow included. Water quality is ECO Lab |
| TUFLOW | BMT | Commercial | Closed | Free demo limited to 100,000 cells / 10 minutes |
| Iber | UPC/GEAMA et al. | Free | Closed (EULA, no redistribution) | Water quality, habitat, driftwood (IberWood), GPU version |
| BASEMENT | ETH Zurich | Free (commercial use allowed) | Closed (binary distribution) | Strong on riverbed evolution |
| GSSHA | USACE ERDC | Free | Open | Distributed hydrology + 2D overland flow + groundwater + snow |
| SHETRAN | Newcastle University | Free | Open (GitHub) | Physically based 3D groundwater + snow |
| ParFlow | CSM, LLNL, Univ. of Bonn et al. | Free | Open (LGPL) | Integrated hydrology: 3D variably saturated groundwater (Richards) + overland flow + land surface (CLM). MPI, GPU. Many dependencies (Hypre, HDF5, NetCDF, ...) |
| r.avaflow | Mergili & Pudasaini | Free | Open (GRASS GIS module) | Multi-phase mass flows (debris flows, avalanches, lahars, GLOFs). Supports chains of mass flows (v4, 2025) |
| OpenLISEM (Hazard edition) | Jetten, Bout et al. (ITC, Univ. of Twente) | Free | Open (GitHub) | Distributed rainfall-infiltration-runoff and soil erosion integrated with Pudasaini two-phase debris flow, slope failure and entrainment (Bout et al. 2018). One of the very few codes that solve rainfall → debris-flow initiation → runout → deposition in one run |
| FLO-2D | FLO-2D Software | Commercial | Closed | Rain-on-grid runoff + mudflow (O'Brien quadratic rheology). Industry standard. The mudflow concentration is an input time series (concentration growth by erosion is not solved) |
| LaharFlow | Woodhouse et al. (Univ. of Bristol) | Free (web) | Closed | Lahar-specific shallow-layer model solving bulking/dilution by bed erosion and deposition. Takes a source flux (no rainfall runoff) |
| Kanako-2D / Kanako-LS | Nakatani, Satofuka, Mizuyama (sabo) | Free | Closed | Takahashi-type debris flow with erosion and deposition (1D-2D). Sabo practice. Input is a debris-flow hydrograph at the upstream end |
| RAMMS (AVALANCHE / DEBRISFLOW) | WSL/SLF → RAMMS AG | Commercial | Closed | Voellmy equivalent fluid + curvature term + shear-stress entrainment. Industry standard for avalanches and debris flows. Initiated by block release or hydrograph |
| Titan2D | Univ. at Buffalo | Free | Open | Savage–Hutter granular flow (terrain-following coordinates, earth-pressure coefficients, AMR), Pitman–Le two-phase. Track record in volcanic-flow comparison and uncertainty quantification. Initiated by a pile or a flux source |
| CSDMS (Landlab, pymt) | US NSF / Univ. of Colorado | Free | Open | Not a single model but a community platform: a repository of 200+ models and the BMI coupling framework (see Sec. 3) |
| ANUGA | ANU/GA | Free | Open | SWE in Python. Inundation and tsunami |
| GeoClaw | Clawpack team | Free | Open (BSD) | Tsunami generation to propagation to run-up (AMR). Time-dependent seafloor deformation (dtopo), Boussinesq variant |
| COMCOT | Cornell University (Liu) et al. | Free | Distributed by the developers | Tsunami generation to run-up (nested grids). Okada deformation, time-dependent deformation |
| JAGURS | JAMSTEC, Baba et al. | Free | Open (GitHub) | Tsunami (dispersion, elastic response of the Earth). Parallel. Time-dependent seafloor deformation |
| TUNAMI | Tohoku University | Free | Distributed by the developers | One of the standard tsunami propagation/run-up codes. Initial-surface approach |
| SWASH | TU Delft | Free | Open (GPL) | Multi-layer non-hydrostatic waves, tsunamis and coasts |
| FUNWAVE-TVD | University of Delaware | Free | Open (GitHub) | Boussinesq-type waves (soliton fission, breaking) |
| NHWAVE | University of Delaware | Free | Open (GitHub) | Sigma-coordinate 3-D non-hydrostatic. Track record in landslide tsunami generation |
| NEOWAVE | University of Hawaii | — | Closed | One-layer non-hydrostatic tsunami model (the same one-layer approximation as ENCflow) |
| VolcFlow | Université Clermont Auvergne (Kelfoun) | Free | Distributed by the developers | Volcanic mass flows (debris avalanches, pyroclastic flows, lava). Two-layer version for landslide tsunamis |
| SOBEK | Deltares | Commercial | Closed | 1D-2D hydraulics with structures (being merged into the Delft3D FM Suite) |
| SWMM | US EPA | Free | Open (public domain) | Urban drainage pipe networks (1-D). Coupling with 2-D surface models is done by vendor products |
| InfoWorks ICM / xpswmm | Autodesk (formerly Innovyze) | Commercial | Closed | The practical standard for dual drainage (pipe network + 2-D surface) |
| MODFLOW (+SWI2 / SEAWAT) | USGS | Free | Open | The standard for 3-D groundwater. SWI2 for sharp interfaces, SEAWAT for variable density |
| SUTRA | USGS | Free | Open | Variable-density, variably saturated groundwater flow and transport |
| FEFLOW | DHI | Commercial | Closed | 3-D groundwater, heat and mass transport (variable density) |
| MOLASSES / Q-LavHA | USF / VUB | Free | Open | Cellular-automaton and probabilistic lava-flow models |
| MAGFLOW / LavaSIM | INGV / Japan (Hidaka et al.) | — | Closed (to be confirmed) | Thermally coupled lava-flow models |
| LAHARZ | USGS | Free | Open | Empirical lahar inundation extent (GIS) |
| Badlands / FastScape | University of Sydney / GFZ | Free | Open | Process-law landscape evolution models (Landlab is in the CSDMS row) |
| PISM / Elmer/Ice / OGGM | UAF and PIK / CSC / University of Innsbruck et al. | Free | Open | Dedicated ice-sheet and glacier dynamics models |

Sources (confirmed 2026-08-10):
[RRI](https://www.pwri.go.jp/icharm/research/rri/index.html) /
[RRI terms of use](http://www.icharm.pwri.go.jp/research/rri/rri_contract_e.html) /
[BASEMENT](https://basement.ethz.ch/about.html)
([v3 paper](https://arxiv.org/pdf/2102.12862)) /
[Iber](https://iberaula.es/space/54/downloads) /
[GSSHA](https://en.wikipedia.org/wiki/GSSHA) /
[Delft3D FM](https://oss.deltares.nl/web/delft3dfm) /
[TUFLOW Licensing](https://wiki.tuflow.com/index.php?title=TUFLOW_Licensing) /
[CAESAR-Lisflood](https://sourceforge.net/projects/caesar-lisflood/) /
[Morpho2DH](https://i-ric.org/en/solvers/morpho2dh/) (checked
2026-08-16; no public source of the solver itself could be confirmed
= binary distribution via iRIC) /
[ParFlow](https://github.com/parflow/parflow) (checked 2026-08-26) /
[r.avaflow v1 paper](https://gmd.copernicus.org/articles/10/553/2017/),
[v4 paper](https://gmd.copernicus.org/articles/18/9879/2025/)
(checked 2026-08-26) /
[CSDMS paper](https://gmd.copernicus.org/articles/15/1413/2022/)
(checked 2026-08-26).
The rows after GeoClaw (COMCOT to PISM) were added on 2026-10-06 so
that every model named in Sec. 2 appears here; their distribution
forms are from general knowledge and should be confirmed on each
official site before citing.

Nesting sources (confirmed 2026-10-10):
[Dispersive, nested and parallel JAGURS (PAGEOPH 2015)](https://link.springer.com/doi/10.1007/s00024-015-1049-2) /
[Non-hydrostatic nesting in NEOWAVE (Yamazaki et al., IJNMF 2011; the file name says 2010)](https://uaf.edu/cfos/files/publications/kowalik/Yamazaki_et_al_2010-IJNMF-1.pdf) /
[Implicit AMR of GeoClaw-Bouss (Berger & LeVeque, SISC 2024)](https://faculty.washington.edu/rjl/pubs/mjb-rjl-implicit-2023/index.html) /
[Multi-grid nesting of FUNWAVE-TVD (GMD 2022)](https://gmd.copernicus.org/articles/15/5441/2022/) /
[Nested Boussinesq (Zhou et al., NHESS 2011)](https://nhess.copernicus.org/articles/11/2677/2011/) /
[TUFLOW Multiple 2D Domains (Classic M2D and HPC Quadtree)](https://docs.tuflow.com/classic-hpc/manual/2026.0/TwoD2DLinking-2.html) /
[HEC-RAS 2D (no nesting; refinement regions)](https://therassolution.kleinschmidtgroup.com/the-ras-solution-forum/topic/reduce-grid-size-at-area-of-interest) /
[Refinement by domain decomposition in Delft3D 4 (DDM29)](https://www.ddm.org/DD29/proceedings/ID104_pages.pdf) /
[Multiple Grids of MIKE 21 Classic](https://en.wikipedia.org/wiki/MIKE_21) /
[Two-way nesting of ROMS-AGRIF (Debreu et al., Ocean Modelling 2012)](https://memsic.ccsd.cnrs.fr/UNIV-GRENOBLE1/hal-00690731).
The coupling methods of COMCOT, TUNAMI-N2 and MOST are in docs/nesting_plan.md
§2.1 (in Japanese; includes the source checks).

SFINCS sources: [SFINCS documentation](https://sfincs.readthedocs.io/en/latest/) and
[GitHub Deltares/SFINCS](https://github.com/Deltares/SFINCS) (added 2026-10-20.
Neither site could be reached from the working environment, so the content is
from knowledge of Leijnse et al. 2021 (Coastal Engineering) and van Ormondt et
al. 2025 (GMD); confirm before citing).

## 2. Comparison of process coverage (against ENCflow's current state)

| Process | ENCflow | Representatives with equal or better coverage | Notes |
|---|---|---|---|
| 2D shallow water (dynamic wave) | Yes: eight-neighbor connected collocated grid (ENC grid), adaptive RK, momentum-conservative advection (Stelling & Duinmeijer type extended to eight directions, MUSCL, lateral-face coupling of the diagonal sub-lattice mode) | TELEMAC, Delft3D, HEC-RAS, TUFLOW, Iber, BASEMENT | The ENC grid is original (Tada, 2026, doi:10.3178/hrl.25-00052). The design and verification of the momentum-conservative advection on the ENC grid are unpublished (docs/advection_design.md, in Japanese; within 1 % of Stoker's bore solution, decay of the sub-lattice mode in test/sublattice) |
| Storm surge / tsunami run-up (coastal inundation) | Yes: sea cells (not solved, level prescribed; cannot hold boundaries, structures or nest bands, excluded from statistics) + tide/water-level time series + wetting-drying. To solve the offshore side, use bathymetry + f_htype=2 ("solved sea") | TELEMAC, Delft3D, ANUGA, GeoClaw, SFINCS (specialised in compound flooding of storm surge + waves + rainfall + rivers; waves as the stationary wave solution of SnapWave) | Offshore generation and propagation are received as water levels from outside (to solve the generation, see the fault tsunami row). Compound storm surge, river and rainfall flooding in a single model |
| Landslide tsunamis (subaerial collapse plunging into water, submarine slides) | Partial: moving bed layer (inertialess Voellmy, moving-bottom approach) | GeoClaw + landslide source, VolcFlow, NHWAVE, r.avaflow | Release, run-out, wave generation, propagation and run-up in a single time evolution with a one-equation bed layer. Inertia is out of scope (an estimate). Near-field dispersion via the non-hydrostatic correction |
| Fault tsunami generation (time history of seabed displacement) | Yes: prescribed bed motion (displacement history applied incrementally to z; preprocessing utils/fault2disp) | GeoClaw, COMCOT, JAGURS, TUNAMI | Because the time-dependent deformation is applied incrementally, earthquake-triggered submarine slides can share the run. The Kajiura effect of short deformation via the non-hydrostatic correction |
| Non-hydrostatic, dispersive waves (soliton fission, undular bores, solitary waves) | Partial: one-layer non-hydrostatic correction (projection; active set, breaking switch) | SWASH, NEOWAVE, FUNWAVE, GeoClaw-Bouss | Does not compete with dedicated models on accuracy; corrects only the reaches where dispersion is essential (zero cost when disabled). Linear and solitary waves within 1% of one-layer theory |
| Subgrid channels (sigma cross-section, width) | Yes | LISFLOOD-FP, HEC-RAS (1D-2D), SFINCS (subgrid topography that tabulates depth–volume and conveyance from the elevation distribution within a cell; not limited to channels) | One water level per cell + sigma(h) is a distinctive approach |
| Structures (breach, pumps, culverts, sluice gates, diversions, dam operation) | Yes | HEC-RAS, TUFLOW, MIKE, SOBEK (SFINCS goes as far as thin walls, weirs, drainage pumps and culverts) | An area where the free/open camp is thin |
| Rainfall runoff, interception, evapotranspiration | Yes: canopy, Hamon/Thornthwaite, lapse rate | RRI, GSSHA, MIKE SHE, SHETRAN | The hydraulics-specialized camp does not have these (SFINCS goes as far as rain-on-grid + infiltration (constant, CN, Green-Ampt, Horton); no interception, evapotranspiration or groundwater) |
| Groundwater | Yes: two layers (soil + weathered bedrock) + well pumping sinks + streambed exchange limit (the capped form of MODFLOW RIV) | MIKE SHE, SHETRAN, GSSHA, ParFlow | Two layers in a plan-view 2-D model is a minority position. Pumping combined with the fresh/salt layers also covers pumping-induced seawater intrusion. River-aquifer exchange is represented on the channel-mask cells themselves, without a separate river package |
| Vertical unsaturated flow (Richards) | Partial: one-dimensional Richards (Kosugi model) on shared reference columns, read out at the soil depth of the zones and drained directly to outlets (the VZ runoff model of Tani 2023) | HYDRUS-1D (dedicated vertical 1-D), MIKE SHE, SHETRAN, ParFlow | No vertical grid per cell; a few reference columns represent the zones (state = columns × layers). A rough estimate that does not solve the lateral delay. In the first version it cannot be combined with the groundwater (two layers) at the same place |
| Seawater intrusion / fresh-salt two-layer | Partial: sharp interface (SWI2-type) + surface salt layer | MODFLOW+SWI2/SEAWAT, SUTRA, FEFLOW | Variable-density transport that resolves mixing and dispersion is a dedicated domain. Following run-up seawater to its destination in a single time evolution with surface inundation and tide is the original point |
| Urban drainage / conduit networks | Partial: conduit continuum layer (equivalent confined continuum, 8-direction conveyance, surcharge) | SWMM + 2-D couplings (TUFLOW, InfoWorks ICM, xpswmm) | The world standard couples a 2-D surface model with a 1-D pipe network. ENCflow homogenizes the network into a continuum; control structures and trunk-dominated systems are ceded to network models |
| Sediment and landform change (bedload, suspension, collapse, debris flow) | Yes, with MORFAC. Also cliff rockfall and talus (f_rockfall; windowed free-face height, export into the sea for sea cliffs) | GAIA, Delft3D-MOR, BASEMENT, CAESAR-Lisflood, Morpho2DH | Differs in placing debris flows alongside catchment hydrology and floods |
| Formation of a river-mouth delta (bifurcation at the mouth bar, lobe growth, channel switching; fan versus bird-foot by the sand/mud ratio; stabilisation of distributaries by discharge variation and fixation) | Yes, settings only (sea as ordinary cells + initial water level, capacity feed + suspended mud + bed-fines ledger + slope correction + angle of repose + fixation) | DeltaRCM (reduced complexity, random walks), Delft3D (physics-based 2D/3D; Edmonds & Slingerland), CAESAR-Lisflood (local inertia + lateral erosion) | The effect of the sand/mud ratio (more mud, fewer and longer distributaries) has the same sign as in all three. Symmetry breaking by the instability of the bifurcation rather than by random numbers. Solving backwater and the jet with momentum-conserving flow, coupled on the same grid with discharge variation, tide and catchment hydrology, is the distinctive part. Waves, tidal currents and plume buoyancy are not implemented. docs/delta_plan.md (Japanese) |
| Development of meandering channels (bed-load direction correction in bends, bank erosion, angle-of-repose avalanching, vegetation fixation of inner-bank bars, neck cutoff, a ledger of fines in the bed) | Yes, as landform change on the raster (no vector bank line; equilibrium secondary flow, non-equilibrium planned) | Nays2DH (iRIC), Delft3D-MOR, BASEMENT, CAESAR-Lisflood, research models with self-evolving banks (Asahi et al. 2013) | Dedicated models track the bank line or solve in curvilinear coordinates. ENCflow treats the bank face as the step between neighbouring cells, so cutoffs and the merging of bars into the floodplain emerge from wetting-drying and landform change; it sits in the same time evolution as catchment hydrology and floods (examples/meander, meander_cutoff) |
| Volcanic flows and snow avalanches (debris avalanches, pyroclastic flows, lahars, dense-flow avalanches) | Yes: equivalent fluid (Voellmy, constant retarding stress, curvature term) | Titan2D, VolcFlow, RAMMS, r.avaflow, LAHARZ | Resistance laws at the level of dedicated models. Original in following eruption, run-out, deposition, natural damming, dam-break flood and secondary lahar as one chain in a single run. Dilute systems (surges, plumes) are out of scope |
| Post-ashfall rain-triggered mudflows (ashfall → rainfall → erosion of the ash layer → deposition) | Yes: give the ash thickness as soil depth, no source specification | OpenLISEM (Hazard edition). FLO-2D, Kanako-2D, Morpho2DH, LaharFlow, RAMMS, r.avaflow, HEC-RAS 6 and LAHARZ cover part of the chain | Dedicated models do either the rainfall runoff or the mass-flow run-out, with the other as input. Sharing one grid and time loop lets the mudflow arise by itself. The counterpart for a comparison study is OpenLISEM |
| Lava flows (effusion, stopping, solidification) | Yes: depth-averaged Bingham (isothermal) + solidification into topography | MOLASSES, Q-LavHA (CA, probabilistic), MAGFLOW, LavaSIM (thermally coupled), VolcFlow | A physics level between the CA/probabilistic and thermally coupled camps. Original in that solidified lava becomes the bed and rainfall, floods and sediment then flow over the new topography in the same run |
| Driftwood (generation, transport, deposition) | Partial: raster-field estimate (Eulerian transport of timber volume) | iRIC driftwood modules, IberWood (individual rigid-body tracking) | The mainstream tracks individual logs down to the geometry of blockage. ENCflow assesses arrival and deposition potential as maps in a single time evolution with floods and debris flows |
| Building destruction and debris (wooden houses, debris transport and deposition) | Partial: raster-field estimate (fragility-type destruction + Eulerian debris transport + void-ratio feedback) | Fragility-function post-processing, DEM and particle-method debris tracking | The practical standard is depth-based fragility post-processing. Original in handling the fate of debris and the added destructive force of driftwood and debris in the same time evolution |
| Water quality (load runoff, decay, settling, buildup-washoff, Kd partitioning, in-groundwater transport, completely mixed reservoirs) | Yes | MIKE ECO Lab, Delft3D-WAQ, Iber-WQ, GSSHA | Free and open codes rarely combine hydrology, water quality and hydraulics. Closes the mass budget across surface, subsurface and reservoirs in one code |
| Snow accumulation and snowmelt | Yes: degree-day + frozen-ground infiltration suppression | MIKE SHE, GSSHA, SHETRAN | HEC-RAS leaves it to HMS |
| Glaciers | Yes: degree-day mass balance + SIA flow + sliding + glacial erosion + avalanche redistribution | None among general flood models. Detailed ice dynamics: PISM, Elmer/Ice, OGGM | No other model runs glaciers side by side with flood hydraulics, catchment hydrology and landform change |
| Wave-driven longshore transport (shoreline smoothing, spits, arcuate deltas) | Partial: no wave propagation, a CERC-type estimate in the shoreline band (f_wave_longshore; offshore H0, T and direction as inputs, smoothed shoreline orientation, local-slope term, river-mouth velocity rule; stirring and sheltering refinements are planned) | Delft3D-MOR+WAVE (SWAN), XBeach, CEM (the one-line coastline model of Ashton & Murray) | Models that propagate waves are a domain of their own. Running the CERC rule of one-line models on top of 2-D landform change is the distinctive point (the wave case of examples/delta; developer.md §84.15, Japanese) |
| Long-term landform evolution | Yes: weathering, uplift, periodic forcing, limestone dissolution (recharge-proportional chemical denudation plus a sink-inflow term for dolines) | CAESAR-Lisflood, Landlab, Badlands, FastScape | On a par with CAESAR-Lisflood among hydraulics-driven models; the others are process-law LEMs. Dissolution runs in the same run as the conduit continuum layer (karst hydrology) as a first-order estimate; cave-network geometry (speleogenesis models) is out of scope |
| Nesting (multi-level grids) | Yes: static nesting (any depth; the ratios r and r_t are arbitrary integers). Band Dirichlet / Flather radiation / sponge; replacement by area averaging, wet test and conservation correction. The non-hydrostatic φ and additional fields (sediment, water quality, subsurface storage, etc.) are exchanged too | Tsunami: COMCOT, TUNAMI, MOST, JAGURS, NEOWAVE, GeoClaw (AMR), FUNWAVE-TVD. Structured-grid MIKE 21 Classic, TUFLOW Classic, Delft3D 4. Ocean and atmosphere (ROMS-AGRIF, WRF) | The open flood codes refine locally with unstructured or quadtree grids and have no nesting. Coupling dispersive waves across the interface is the minority of JAGURS, NEOWAVE, GeoClaw-Bouss and FUNWAVE (Sec. 3) |
| Parallelization | OpenMP + MPI. Bit-reproducible regardless of rank count | TELEMAC, Delft3D (MPI; bit reproducibility not guaranteed), SFINCS (OpenMP + GPU/OpenACC) | Deterministic reductions are the differentiator |
| Restart exactness | Yes: module-private save contract | Commercial codes generally support it | Few open codes enforce it thoroughly |

The formulations, verification figures and implementation dates behind
each row are in the corresponding sections of developer.md and the
user's guide chapters, not in this table.

## 3. Positioning observations

- In the free, open-code class, the only ones that carry "dynamic-wave
  2D hydraulics + catchment hydrology + structures + sediment + water
  quality + multi-layer groundwater" in a single code are effectively
  GSSHA and SHETRAN, and no example, open or commercial, adds driftwood
  and building destruction and debris (fragility-type destruction
  criterion + raster transport of debris + void-ratio feedback; Sec. 2)
  to that in the same time evolution (damage assessment by
  depth-to-damage-ratio post-processing is the practical standard). Both
  lean toward hydrology (their hydraulics are diffusive-wave with
  simplified channels). Conversely, the open
  players strong in hydraulics (TELEMAC, Delft3D FM, LISFLOOD-FP) are
  thin on catchment hydrology and structure operation. ENCflow enters,
  free and open, the middle band of "stacking all catchment processes
  at flood-hydraulics accuracy" -- territory traditionally occupied
  by the commercial MIKE/TUFLOW.
- **Contrast with SFINCS (the closest open player)**: Deltares' SFINCS is
  the closest to ENCflow in distribution form -- free, open code, Fortran,
  raster grid, simple input and output -- and shares the "compound
  flooding" orientation of handling storm surge, waves, rainfall, river
  inflow and structures within the same time evolution. The differences
  lie in the equations and in the scope. SFINCS specialises by default in
  **fast computation of coastal lowlands** with the local inertia equations
  (no advection term) + subgrid topography + quadtree (GPU-capable; track
  record in global-scale compound-flood assessment); its catchment
  hydrology stops at rain-on-grid and infiltration, and it has no
  groundwater, sediment, water quality or volcanic family. ENCflow takes
  the dynamic wave (momentum-conservative advection) as its default,
  reaches the steep channels of mountain catchments, and puts everything
  from catchment hydrology to sediment and landform change in one run.
  That the local inertia equations without the advection term depend
  strongly on resolution on steep real terrain is shown in the supplement
  to tutorials/chichibu (result 3), so the two divide into "wide-area,
  fast, coastal lowlands (SFINCS)" and "multi-process from mountains to
  coast (ENCflow)". The quadtree, subgrid topography and GPU of SFINCS are
  elements ENCflow does not have; how far to adopt them under the
  raster-purity policy (developer.md Sec. 0) is a medium-term question
  (nesting is substituted by static nesting, as in Sec. 2).
- **River-mouth deltas (versus DeltaRCM)**: DeltaRCM is a reduced-complexity
  model that routes water by random walks and places sand and mud by rules; it
  suits the exploration of regimes and long-term statistics. ENCflow produces
  the same regimes (bifurcation at the mouth bar, fan versus bird-foot by the
  sand/mud ratio, channel switching) from the shallow-water equations and
  transport formulae (docs/delta_plan.md), with the symmetry breaking carried by
  the instability of the bifurcation instead of random numbers. The share of
  mechanistic content is clearly larger for the flow, at the same level as
  other physics-based 2D models (Delft3D, CAESAR-Lisflood) for the sediment
  (empirical transport formulae), and phenomenological for the fixation. The
  advantage lies where the flow dynamics matter (backwater, jets, coupling with
  discharge variation and other processes) and where coefficients must be
  transferable; for regime exploration and many-realisation statistics the
  reduced-complexity model is the better tool. The cost is orders of magnitude
  higher (dx 2.5 m, 4000 h of morphological time: 7 hours on 4 threads).
- **Rainfall runoff and mass flows side by side**: a chain such as the
  post-ashfall rain-triggered mudflow (examples/ashfall_lahar), where the
  runoff computation drives the erosion and the erosion changes the nature
  of the flow (concentration, resistance), only starts without a specified
  source when the runoff model and the mass-flow model share one grid and
  one time loop. Across open and commercial codes, OpenLISEM (Hazard
  edition) is practically the only other one solving it in one run; the
  rest take one side as input (the lahar row of §2).
- **Position of nesting (multi-level grids)**: nested grids are standard
  equipment in tsunami models (COMCOT, TUNAMI, MOST, JAGURS, NEOWAVE, the
  AMR of GeoClaw), but coupling dispersive waves (non-hydrostatic,
  Boussinesq) across the interface is limited to JAGURS (Baba et al.
  2015), NEOWAVE (Yamazaki et al. 2011; Dirichlet on the non-hydrostatic
  pressure), GeoClaw-Bouss (Berger & LeVeque 2024; SGN under AMR, the
  elliptic equation solved implicitly level by level) and FUNWAVE-TVD
  (Choi et al. 2022; two-way). The band φ of ENCflow (NEOWAVE type) belongs
  to this minority and has a verification in which a 1:1 self-nest
  reproduces the parent in the child's interior to 2e-13 m
  (test/nest_identity). Outside tsunamis, the open flood and river codes
  refine locally with unstructured, quadtree or non-uniform grids (TELEMAC,
  Delft3D FM, HEC-RAS, TUFLOW HPC Quadtree, LISFLOOD-FP 8.1) and therefore
  have no nesting, while the structured-grid generation -- MIKE 21 Classic
  (Multiple Grids), TUFLOW Classic (M2D), Delft3D 4 (domain
  decomposition) -- supported nested and multi-domain grids (all their
  successors moved to unstructured grids). In ocean and atmospheric models
  (ROMS-AGRIF/CROCO, WRF) nesting is standard, and ENCflow's Flather
  radiation and reflux are of that lineage. What is original in ENCflow is
  that **it refines locally with static nesting while keeping raster
  purity, and exchanges not only the shallow-water h and u but also
  suspended sediment, water quality, driftwood, debris, salt water and
  subsurface storage through the same bands and replacement**; no example,
  open or commercial, nests catchment hydrology and groundwater (the
  integrated hydrology models MIKE SHE, GSSHA and ParFlow are
  single-grid).
- **Bit reproducibility for any rank count, restart exactness, and the
  ULP=0 verification discipline** are explicitly guaranteed by almost
  no product, commercial ones included, and make a strong research
  reproducibility claim.
- The absolute portability of **zero external libraries (only the
  standard MPI/OpenMP specifications), single-language Fortran, and
  in-house GeoTIFF/inflate** has no parallel elsewhere (TELEMAC needs
  METIS etc., Delft3D has many dependencies, ANUGA presumes a Python
  stack). The reach of a single source from educational use (a laptop)
  to vector machines and supercomputers contrasts with TUFLOW's demo
  limits and the commercial GUI-first products.
- **Ease of adoption (self-teachability)**: as user-facing
  groundwork, it ships a
  26-chapter user's guide plus a full parameter index (583 entries),
  annotated namelist samples for every feature
  (examples/List_samples), and 2 hands-on tutorials (minimal example
  wave, real terrain chichibu; from the pitfalls of real data --
  depression removal and discharge oscillations from flat reaches --
  up to 3D visualization with ParaView, all turned into teaching
  material). Pre/post-processing utilities are also bundled (utils/:
  depression removal rmdepress_river, catchment delineation
  calc_catchmentarea, land-use-to-mask lu2mask, VTK conversion
  out2vtk, and more). In the comparison of adoption cost it also
  ranks high among the open players.
  User-facing documentation now has a full Japanese-English mirror
  (docs/en/ and the tutorials' en/); the remaining English gap is
  only in the developer documentation (developer.md etc. are
  Japanese-only).
- **AI-agent orientation**: on top of the fully
  text-based input and output (no GUI dependency), ENCflow ships a
  documentation system that lets "phenomenon -> features -> parameters"
  be looked up mechanically (use-case gallery, full parameter index,
  annotated samples) and repository-bundled groundwork for agents (the
  CLAUDE.md conventions, the /make-case standard procedure, and the
  user-facing docs/ai_guide.md in Japanese and English). Bit
  reproducibility and the regression baselines are also the foundation
  that lets an agent verify its own work in a loop. Much of the
  development and verification of ENCflow itself is carried out in
  collaboration with AI agents, so the claim comes with a working
  demonstration. GUI-first and closed-source products are structurally
  hard for agents to operate, and among the open players no example of
  repository-level agent groundwork is found at this time (a gap that
  may narrow as other models catch up).
- **A third positioning axis — a gateway across
  disciplines (screening)**: the value of ENCflow cannot be measured
  only on the axis "is it more precise than each field's specialist
  model?". Because neighboring-field processes can be added one at a
  time while keeping the same grid, the same input system, and the
  same way of running, the barrier to running a *first* computation
  outside one's own field is one step lower than with the conventional
  practice of combining separate software systems (e.g. a river
  researcher can try groundwater, a flood researcher can try sediment,
  snowmelt, or water quality, and a tsunami researcher can try driftwood
  or building destruction and debris, starting from one added
  configuration file). The value is as a screening tool — estimate
  with a simple model whether a process matters, and move to a
  specialist model once you know it does — so the positioning is **a
  gateway to, not a replacement for, specialist models**. This is an
  advantage on a different axis from the feature table (Sec. 2), and
  it aligns with education (processes can be learned as accumulating
  on the same state) and with AI-agent operation (the uniform
  structure lets a machine guide the entry into an unfamiliar
  process). The statement of purpose is codified at the head of
  developer.md Sec. 0. Note this does not mean "correct results
  without expertise" — what is lowered is the barrier to trying, not
  the expertise barrier, and user-facing wording keeps to this line.
- **Contrast with two other routes to
  integration**: (a) **physics-first integrated hydrology (ParFlow)**
  — the representative open model that tightly couples 3D variably
  saturated Richards flow with land-surface processes (CLM). Superior
  in physical fidelity, but premised on HPC and a dependency stack
  (Hypre, HDF5, ...), and without structures, sediment, water
  quality, or the volcanic family. ENCflow's approximate route with
  an abstracted vertical (developer.md Sec. 0, policy 5) coexists by
  its laptop-first accessibility and its breadth of processes (as an
  exception, only for Tani's VZ runoff model, which deals with the
  response of vertical unsaturated infiltration itself, the Richards
  equation is solved on a few shared reference columns, with no
  vertical grid per cell; developer.md Sec. 87).
  (b) **coupling frameworks (CSDMS: BMI, pymt, Landlab)** — the
  community route of connecting existing specialist models through a
  standard interface. Its strength is using each field's specialist
  model as-is, while aligning grids, time steps, and I/O — and wiring
  the models together — remains the user's work. ENCflow is in-house
  integration in a single code and a single time evolution: processes
  can be added without coupling work, at the price of keeping each
  process at the screening level — the two routes are complementary.
  (Added 2026-08-29) That complementarity is now an actual connection:
  ENCflow itself behaves as a BMI 2.0 component (passes bmi-tester;
  see bmi/), so the in-house integrated process chain can be offered
  as a single component to CSDMS-side coupling (Landlab, pymt,
  GLOFRIM-style chains). "In-house integration vs. coupling framework"
  is no longer either-or: the former can serve as a building block of
  the latter (history in docs/bmi_plan.md).
