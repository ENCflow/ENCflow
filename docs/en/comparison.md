> English mirror of docs/comparison.md (based on commit 76b671c). The Japanese file is the master copy.

# Comparison with Other Simulation Software (comparison.md)

Survey as of 2026-08-10, updated since (source-check dates are
noted inline). It assumes the current state of ENCflow's feature
implementation (complete up to shallow water + channels + structures
+ runoff + evapotranspiration + two-layer groundwater + sediment +
water quality + buildup-washoff + snow + long-term landscape
evolution).
Licenses and distribution forms can change, so re-check each official
site before citing.

## 1. Comparison of distribution forms

| Model | Developer | Cost | Code | Notes |
|---|---|---|---|---|
| **ENCflow** | (this project) | Free (policy) | Fully open (policy) | Basic policy is developer.md Sec. 0. Ships agent-oriented groundwork (Sec. 3) |
| RRI | ICHARM/PWRI | Free | Open (own terms) | Copyright-notice obligation; commercial use by permission. iRIC-version solver also published |
| iRIC (Nays2DFlood etc.) | iRIC organization | Free | Main solvers open | Platform of GUI + solver suite |
| Morpho2DH | Takebayashi (DPRI, Kyoto Univ.) / iRIC | Free | Closed (distributed via iRIC) | Morpho2D (2D bed deformation) + debris/mud flow. Considers structures such as sabo dams |
| HEC-RAS 2D | USACE (US Army) | Free | Closed | One of the de facto standards in practice. Catchment hydrology is delegated to HEC-HMS |
| LISFLOOD-FP 8 | University of Bristol | Free | Open (GPL) | Subgrid channels, GPU |
| CAESAR-Lisflood | UK universities | Free | Open (GPL) | LISFLOOD-FP hydraulics + landscape evolution (hours to millennia) |
| TELEMAC-2D (+GAIA) | EDF-led | Free | Open (GPLv3) | Unstructured FE/FV. Sediment via GAIA. No catchment hydrology |
| Delft3D FM | Deltares | Kernel free | Kernel open (GPLv3) | GUI distributed free but under license management |
| MIKE 21 / MIKE SHE | DHI | Commercial | Closed | Integrated hydrology (SHE) is the most comprehensive, snow included |
| TUFLOW | BMT | Commercial | Closed | Free demo limited to 100,000 cells / 10 minutes |
| Iber | UPC/GEAMA et al. | Free | Closed (EULA, no redistribution) | Water quality, habitat, GPU version |
| BASEMENT | ETH Zurich | Free (commercial use allowed) | Closed (binary distribution) | Strong on riverbed evolution |
| GSSHA | USACE ERDC | Free | Open | Distributed hydrology + 2D overland flow + groundwater + snow |
| SHETRAN | Newcastle University | Free | Open (GitHub) | Physically based 3D groundwater + snow |
| ParFlow | CSM, LLNL, Univ. of Bonn et al. | Free | Open (LGPL) | Integrated hydrology: 3D variably saturated groundwater (Richards) + overland flow + land surface (CLM). MPI, GPU. Many dependencies (Hypre, HDF5, NetCDF, ...) |
| r.avaflow | Mergili & Pudasaini | Free | Open (GRASS GIS module) | Multi-phase mass flows (debris flows, avalanches, lahars, GLOFs). Supports chains of mass flows (v4, 2025) |
| CSDMS (Landlab, pymt) | US NSF / Univ. of Colorado | Free | Open | Not a single model but a community platform: a repository of 200+ models and the BMI coupling framework (see Sec. 3) |
| ANUGA | ANU/GA | Free | Open | SWE in Python. Inundation and tsunami |
| GeoClaw | Clawpack team | Free | Open (BSD) | Tsunami generation to propagation to run-up (AMR). Tsunami-specialized |

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
(checked 2026-08-26)

## 2. Comparison of process coverage (against ENCflow's current state)

| Process | ENCflow | Representatives with equal or better coverage | Notes |
|---|---|---|---|
| 2D shallow water (dynamic wave) | Yes: eight-neighbor connected collocated grid (ENC grid), adaptive RK | TELEMAC, Delft3D, HEC-RAS, TUFLOW, Iber, BASEMENT | The ENC grid is original (Tada, 2026, HRL 20(2), doi:10.3178/hrl.25-00052) |
| Storm surge / tsunami run-up (coastal inundation) | Yes: sea cells + tide/water-level time series (m_tide) + wetting-drying | TELEMAC, Delft3D, ANUGA, GeoClaw | Offshore generation and propagation are received as water levels from outside (observed waveforms, large-domain models). Handling the compound disaster of storm surge x river x heavy rain in a single model is an advantage of the integrated design |
| Subgrid channels (sigma cross-section, width) | Yes | LISFLOOD-FP (subgrid channels), HEC-RAS (1D-2D) | One water level per cell + sigma(h) is a distinctive approach |
| Structures (breach, pumps, culverts, sluice gates, diversions, dam operation) | Yes | HEC-RAS, TUFLOW, MIKE, SOBEK family | An area where the free/open camp is thin |
| Rainfall runoff, interception, evapotranspiration | Yes (canopy, Hamon/Thornthwaite, lapse rate) | RRI, GSSHA, MIKE SHE, SHETRAN | The hydraulics-specialized camp does not have these |
| Groundwater | Yes: two layers (soil-layer Boussinesq + weathered bedrock layer) + well pumping sinks (2026-08-18) | MIKE SHE (3D), SHETRAN (3D), GSSHA, ParFlow (3D variably saturated Richards + CLM) | Two layers in a plan-view 2D model is a minority position. Pumping is a cell-scale sink (a plan-view analog of MODFLOW WEL); combined with the fresh/salt layers it also covers pumping-induced seawater intrusion. ParFlow is the physics-fidelity pole (Sec. 3) |
| Seawater intrusion / fresh-salt two-layer | Partial: sharp-interface 2-zone (SWI2-type; Phi_s = eta + eps*zeta, prescribed sea head, surface salt layer; developer.md sec. 47; prototype 2026-08-18) | MODFLOW+SWI2/SEAWAT, SUTRA, FEFLOW (variable density) | Variable-density transport (SEAWAT/SUTRA) resolves dispersion and mixing and is a dedicated domain. ENCflow's originality is the quasi-static sharp interface in a single time evolution with surface inundation and tide (tracking run-up seawater end to end) |
| Urban drainage / conduit networks | Partial: conduit continuum layer (equivalent confined continuum, 8-direction anisotropic conveyance, pressurized surcharge, inlet exchange; developer.md sec. 46, prototype 2026-08-18) | SWMM + 2D couplings (TUFLOW, InfoWorks ICM, xpswmm and other dual-drainage codes) | The world standard couples a 2D surface model with a 1D pipe-network model. ENCflow takes the original route of homogenizing the network into a continuum solved in a single time evolution (quantifying its limits of applicability is a research theme; gwconduit_plan.md sec. 3). Control structures and trunk-dominated systems are out of scope in principle and are ceded to network-model coupling |
| Sediment and landform change (bedload, suspension, collapse, debris flow) | Yes, with MORFAC | GAIA, Delft3D-MOR, BASEMENT, CAESAR-Lisflood, Morpho2DH | For debris/mud flow (landslide-triggered runout and deposition), the representative free practical tool is Morpho2DH (iRIC); ENCflow differs in housing debris flow together with catchment hydrology and flooding |
| Volcanic flows and snow avalanches (debris avalanches, dense pyroclastic flows, lahars, dense-flow snow avalanches) | Yes: equivalent fluid (Voellmy, constant retarding stress, f_release; Sec. 28.8) | Titan2D, VolcFlow, RAMMS (avalanches), r.avaflow (multi-phase, chains), LaharZ (empirical) | The same SWE + granular-resistance level as the dedicated tools. ENCflow is unique in following the chain eruption supply → runout → deposition → natural damming → dam-break flood → rainfall-triggered secondary lahars in a single model and a single run (the dedicated tools are mostly single-process; r.avaflow, with the Pudasaini multi-phase model, comes closest in handling chains between mass flows — collapse → lake impact → GLOF etc. — but does not house catchment hydrology, flood hydraulics, or water quality). Dense-flow snow avalanches use the same setup (release as a scenario; velocity-proportional path entrainment via f_dbed=4; see users_guide/geomorph.md). Dilute phenomena (surges, plumes, ash transport, powder avalanches) are declared out of scope (debris_plan.md Sec. 5) |
| Lava flows (vent effusion, stopping, solidification) | Yes: depth-averaged Bingham viscous gravity current (isothermal; η and τ_y given directly + velocity-threshold solidification into topography; Sec. 51, lava_plan.md; 2026-08-23) | MOLASSES, Q-LavHA (probabilistic/CA), MAGFLOW, LavaSIM (thermally coupled), VolcFlow (lava version) | The practical standards split into CA/probabilistic tools (isothermal, empirical) and thermally coupled ones. ENCflow's isothermal Bingham diffusion sits between those physics levels; its distinctive point is that solidified lava becomes the bed z, so rain, floods, and sediment flow over the new topography in the same run (eruption → lava field → secondary hydrologic response). Cooling and temperature-dependent viscosity are future extensions (lava_plan.md Sec. 8); thermal lava-water interaction is declared out of scope |
| Water quality (load runoff, decay, settling, buildup-washoff, Kd two-phase partitioning, in-groundwater transport, completely mixed reservoirs) | Yes | MIKE ECO Lab, Delft3D-WAQ, Iber-WQ, GSSHA | Free and open coexistence of hydrology + water quality + hydraulics is rare; the mass budget across surface, groundwater and reservoirs closes in a single code |
| Snow accumulation and snowmelt | Yes: degree-day method (Sec. 31) + infiltration suppression by frozen ground (freezing index; 2026-08-18) | MIKE SHE, GSSHA, SHETRAN (also degree-day family) | For HEC-RAS this is on the HMS side |
| Glaciers | Yes: degree-day mass balance + SIA flow + sliding + glacial erosion + avalanche redistribution (Sec. 45; 2026-08-16) | Absent from all general-purpose flood models | Detailed ice dynamics remain the domain of dedicated models (PISM, Elmer/Ice, OGGM). Running glaciers alongside flood hydraulics, catchment hydrology, and landform change in a single model has no counterpart |
| Long-term landform evolution | Yes: weathering, uplift, cyclic forcing (Sec. 32; 2026-08-10) | CAESAR-Lisflood, Landlab, Badlands, FastScape | Driven by real hydraulics, on par with CAESAR-Lisflood. Landlab/Badlands/FastScape are process-law LEMs (simplified hydraulics) occupying a different niche |
| Parallelization | OpenMP + MPI. **Bit reproducibility regardless of rank count** | TELEMAC/Delft3D use MPI (bit reproducibility not guaranteed) | Deterministic reductions (Sec. 11) are the differentiator |
| Restart exactness | Yes (module-private save contract; Sec. 7) | Commercial products generally support this | Thorough examples are rare in the open camp |

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
  20-chapter user's guide plus a full parameter index (453 entries),
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
