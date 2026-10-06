> English mirror of docs/comparison.md (based on commit 76b671c). The Japanese file is the master copy.

# Comparison with Other Simulation Software (comparison.md)

Survey as of 2026-08-10, updated since (source-check dates are
noted inline). It assumes the current state of ENCflow's feature
implementation (complete up to shallow water + channels + structures
+ runoff + evapotranspiration + two-layer groundwater + sediment +
water quality + buildup-washoff + snow + long-term landscape
evolution + driftwood + building destruction and debris + the
non-hydrostatic correction + prescribed bed motion for fault tsunamis;
updated 2026-10-06).
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

## 2. Comparison of process coverage (against ENCflow's current state)

| Process | ENCflow | Representatives with equal or better coverage | Notes |
|---|---|---|---|
| 2D shallow water (dynamic wave) | Yes: eight-neighbor connected collocated grid (ENC grid), adaptive RK | TELEMAC, Delft3D, HEC-RAS, TUFLOW, Iber, BASEMENT | The ENC grid is original (Tada, 2026, doi:10.3178/hrl.25-00052) |
| Storm surge / tsunami run-up (coastal inundation) | Yes: sea cells + tide/water-level time series + wetting-drying | TELEMAC, Delft3D, ANUGA, GeoClaw | Offshore generation and propagation are received as water levels from outside (to solve the generation, see the fault tsunami row). Compound storm surge, river and rainfall flooding in a single model |
| Landslide tsunamis (subaerial collapse plunging into water, submarine slides) | Partial: moving bed layer (inertialess Voellmy, moving-bottom approach) | GeoClaw + landslide source, VolcFlow, NHWAVE, r.avaflow | Release, run-out, wave generation, propagation and run-up in a single time evolution with a one-equation bed layer. Inertia is out of scope (an estimate). Near-field dispersion via the non-hydrostatic correction |
| Fault tsunami generation (time history of seabed displacement) | Yes: prescribed bed motion (displacement history applied incrementally to z; preprocessing utils/fault2disp) | GeoClaw, COMCOT, JAGURS, TUNAMI | Because the time-dependent deformation is applied incrementally, earthquake-triggered submarine slides can share the run. The Kajiura effect of short deformation via the non-hydrostatic correction |
| Non-hydrostatic, dispersive waves (soliton fission, undular bores, solitary waves) | Partial: one-layer non-hydrostatic correction (projection; active set, breaking switch) | SWASH, NEOWAVE, FUNWAVE, GeoClaw-Bouss | Does not compete with dedicated models on accuracy; corrects only the reaches where dispersion is essential (zero cost when disabled). Linear and solitary waves within 1% of one-layer theory |
| Subgrid channels (sigma cross-section, width) | Yes | LISFLOOD-FP, HEC-RAS (1D-2D) | One water level per cell + sigma(h) is a distinctive approach |
| Structures (breach, pumps, culverts, sluice gates, diversions, dam operation) | Yes | HEC-RAS, TUFLOW, MIKE, SOBEK | An area where the free/open camp is thin |
| Rainfall runoff, interception, evapotranspiration | Yes: canopy, Hamon/Thornthwaite, lapse rate | RRI, GSSHA, MIKE SHE, SHETRAN | The hydraulics-specialized camp does not have these |
| Groundwater | Yes: two layers (soil + weathered bedrock) + well pumping sinks | MIKE SHE, SHETRAN, GSSHA, ParFlow | Two layers in a plan-view 2-D model is a minority position. Pumping combined with the fresh/salt layers also covers pumping-induced seawater intrusion |
| Seawater intrusion / fresh-salt two-layer | Partial: sharp interface (SWI2-type) + surface salt layer | MODFLOW+SWI2/SEAWAT, SUTRA, FEFLOW | Variable-density transport that resolves mixing and dispersion is a dedicated domain. Following run-up seawater to its destination in a single time evolution with surface inundation and tide is the original point |
| Urban drainage / conduit networks | Partial: conduit continuum layer (equivalent confined continuum, 8-direction conveyance, surcharge) | SWMM + 2-D couplings (TUFLOW, InfoWorks ICM, xpswmm) | The world standard couples a 2-D surface model with a 1-D pipe network. ENCflow homogenizes the network into a continuum; control structures and trunk-dominated systems are ceded to network models |
| Sediment and landform change (bedload, suspension, collapse, debris flow) | Yes, with MORFAC | GAIA, Delft3D-MOR, BASEMENT, CAESAR-Lisflood, Morpho2DH | Differs in placing debris flows alongside catchment hydrology and floods |
| Volcanic flows and snow avalanches (debris avalanches, pyroclastic flows, lahars, dense-flow avalanches) | Yes: equivalent fluid (Voellmy, constant retarding stress, curvature term) | Titan2D, VolcFlow, RAMMS, r.avaflow, LAHARZ | Resistance laws at the level of dedicated models. Original in following eruption, run-out, deposition, natural damming, dam-break flood and secondary lahar as one chain in a single run. Dilute systems (surges, plumes) are out of scope |
| Post-ashfall rain-triggered mudflows (ashfall → rainfall → erosion of the ash layer → deposition) | Yes: give the ash thickness as soil depth, no source specification | OpenLISEM (Hazard edition). FLO-2D, Kanako-2D, Morpho2DH, LaharFlow, RAMMS, r.avaflow, HEC-RAS 6 and LAHARZ cover part of the chain | Dedicated models do either the rainfall runoff or the mass-flow run-out, with the other as input. Sharing one grid and time loop lets the mudflow arise by itself. The counterpart for a comparison study is OpenLISEM |
| Lava flows (effusion, stopping, solidification) | Yes: depth-averaged Bingham (isothermal) + solidification into topography | MOLASSES, Q-LavHA (CA, probabilistic), MAGFLOW, LavaSIM (thermally coupled), VolcFlow | A physics level between the CA/probabilistic and thermally coupled camps. Original in that solidified lava becomes the bed and rainfall, floods and sediment then flow over the new topography in the same run |
| Driftwood (generation, transport, deposition) | Partial: raster-field estimate (Eulerian transport of timber volume) | iRIC driftwood modules, IberWood (individual rigid-body tracking) | The mainstream tracks individual logs down to the geometry of blockage. ENCflow assesses arrival and deposition potential as maps in a single time evolution with floods and debris flows |
| Building destruction and debris (wooden houses, debris transport and deposition) | Partial: raster-field estimate (fragility-type destruction + Eulerian debris transport + void-ratio feedback) | Fragility-function post-processing, DEM and particle-method debris tracking | The practical standard is depth-based fragility post-processing. Original in handling the fate of debris and the added destructive force of driftwood and debris in the same time evolution |
| Water quality (load runoff, decay, settling, buildup-washoff, Kd partitioning, in-groundwater transport, completely mixed reservoirs) | Yes | MIKE ECO Lab, Delft3D-WAQ, Iber-WQ, GSSHA | Free and open codes rarely combine hydrology, water quality and hydraulics. Closes the mass budget across surface, subsurface and reservoirs in one code |
| Snow accumulation and snowmelt | Yes: degree-day + frozen-ground infiltration suppression | MIKE SHE, GSSHA, SHETRAN | HEC-RAS leaves it to HMS |
| Glaciers | Yes: degree-day mass balance + SIA flow + sliding + glacial erosion + avalanche redistribution | None among general flood models. Detailed ice dynamics: PISM, Elmer/Ice, OGGM | No other model runs glaciers side by side with flood hydraulics, catchment hydrology and landform change |
| Long-term landform evolution | Yes: weathering, uplift, periodic forcing | CAESAR-Lisflood, Landlab, Badlands, FastScape | On a par with CAESAR-Lisflood among hydraulics-driven models; the others are process-law LEMs |
| Parallelization | OpenMP + MPI. Bit-reproducible regardless of rank count | TELEMAC, Delft3D (MPI; bit reproducibility not guaranteed) | Deterministic reductions are the differentiator |
| Restart exactness | Yes: module-private save contract | Commercial codes generally support it | Few open codes enforce it thoroughly |

The formulations, verification figures and implementation dates behind
each row are in the corresponding sections of developer.md and the
user's guide chapters, not in this table.

## 3. Positioning observations

- In the free, open-code class, the only ones that carry "dynamic-wave
  2D hydraulics + catchment hydrology + structures + sediment + water
  quality + multi-layer groundwater" in a single code are effectively
  GSSHA and SHETRAN, and both lean toward hydrology (their hydraulics
  are diffusive-wave with simplified channels). Conversely, the open
  players strong in hydraulics (TELEMAC, Delft3D FM, LISFLOOD-FP) are
  thin on catchment hydrology and structure operation. ENCflow enters,
  free and open, the middle band of "stacking all catchment processes
  at flood-hydraulics accuracy" -- territory traditionally occupied
  by the commercial MIKE/TUFLOW.
- **Rainfall runoff and mass flows side by side**: a chain such as the
  post-ashfall rain-triggered mudflow (examples/ashfall_lahar), where the
  runoff computation drives the erosion and the erosion changes the nature
  of the flow (concentration, resistance), only starts without a specified
  source when the runoff model and the mass-flow model share one grid and
  one time loop. Across open and commercial codes, OpenLISEM (Hazard
  edition) is practically the only other one solving it in one run; the
  rest take one side as input (the lahar row of §2).
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
  researcher can try groundwater, and a flood researcher can try
  sediment, snowmelt, or water quality, starting from one added
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
  its laptop-first accessibility and its breadth of processes.
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
