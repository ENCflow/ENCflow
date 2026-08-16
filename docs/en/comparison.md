> English mirror of docs/comparison.md (based on commit 6c5acfc). The Japanese file is the master copy.

# Comparison with Other Simulation Software (comparison.md)

Survey as of 2026-08-10 (later additions to the findings are dated
individually). It assumes the current state of ENCflow's feature
implementation (complete up to shallow water + channels + structures
+ runoff + evapotranspiration + two-layer groundwater + sediment +
water quality + buildup-washoff + snow + long-term landscape
evolution).
Licenses and distribution forms can change, so re-check each official
site before citing.

## 1. Comparison of distribution forms

| Model | Developer | Cost | Code | Notes |
|---|---|---|---|---|
| **ENCflow** | (this project) | Free (policy) | Fully open (policy) | Basic policy is developer.md Sec. 0 |
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
= binary distribution via iRIC)

## 2. Comparison of process coverage (against ENCflow's current state)

| Process | ENCflow | Representatives with equal or better coverage | Notes |
|---|---|---|---|
| 2D shallow water (dynamic wave) | Yes: eight-neighbor connected collocated grid (ENC grid), adaptive RK | TELEMAC, Delft3D, HEC-RAS, TUFLOW, Iber, BASEMENT | The ENC grid is original (Tada, 2026, HRL 20(2), doi:10.3178/hrl.25-00052) |
| Storm surge / tsunami run-up (coastal inundation) | Yes: sea cells + tide/water-level time series (m_tide) + wetting-drying | TELEMAC, Delft3D, ANUGA, GeoClaw | Offshore generation and propagation are received as water levels from outside (observed waveforms, large-domain models). Handling the compound disaster of storm surge x river x heavy rain in a single model is an advantage of the integrated design |
| Subgrid channels (sigma cross-section, width) | Yes | LISFLOOD-FP (subgrid channels), HEC-RAS (1D-2D) | One water level per cell + sigma(h) is a distinctive approach |
| Structures (breach, pumps, culverts, sluice gates, diversions, dam operation) | Yes | HEC-RAS, TUFLOW, MIKE, SOBEK family | An area where the free/open camp is thin |
| Rainfall runoff, interception, evapotranspiration | Yes (canopy, Hamon/Thornthwaite, lapse rate) | RRI, GSSHA, MIKE SHE, SHETRAN | The hydraulics-specialized camp does not have these |
| Groundwater | Yes: two layers (soil-layer Boussinesq + weathered bedrock layer) | MIKE SHE (3D), SHETRAN (3D), GSSHA | Two layers in a plan-view 2D model is a minority position |
| Sediment and landform change (bedload, suspension, collapse, debris flow) | Yes, with MORFAC | GAIA, Delft3D-MOR, BASEMENT, CAESAR-Lisflood, Morpho2DH | For debris/mud flow (landslide-triggered runout and deposition), the representative free practical tool is Morpho2DH (iRIC); ENCflow differs in housing debris flow together with catchment hydrology and flooding |
| Water quality (load runoff, decay, settling, buildup-washoff) | Yes | MIKE ECO Lab, Delft3D-WAQ, Iber-WQ, GSSHA | Free and open coexistence of hydrology + water quality + hydraulics is rare |
| Snow accumulation and snowmelt | Yes: degree-day method (Sec. 31; 2026-08-10) | MIKE SHE, GSSHA, SHETRAN (also degree-day family) | For HEC-RAS this is on the HMS side |
| Glaciers | No (SIA designed in as a future slot) | Absent from all general-purpose flood models | The domain of dedicated models (PISM, Elmer/Ice, OGGM) |
| Long-term landform evolution | Yes: weathering, uplift, cyclic forcing (Sec. 32; 2026-08-10) | CAESAR-Lisflood, Landlab, Badlands, FastScape | Driven by real hydraulics, on par with CAESAR-Lisflood. See Sec. 4 |
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
- (Added 2026-08-14, updated 2026-08-16) In addition to features, a
  first full round of user-facing groundwork is now in place: a
  17-chapter user's guide plus a full parameter index (370 entries),
  annotated namelist samples for every feature
  (examples/List_samples), and 2 hands-on tutorials (minimal example
  wave, real terrain chichibu; from the pitfalls of real data --
  depression removal and discharge oscillations from flat reaches --
  up to 3D visualization with ParaView, all turned into teaching
  material). Pre/post-processing utilities are also bundled (utils/:
  depression removal rmdepress_river, catchment delineation
  calc_catchmentarea, land-use-to-mask lu2mask, VTK conversion
  out2vtk, and more). In the comparison of adoption cost
  (self-teachability), it also ranks high among the open players.
  User-facing documentation now has a full Japanese-English mirror
  (docs/en/ and the tutorials' en/); the remaining English gap is
  only in the developer documentation (developer.md etc. are
  Japanese-only). Note also that most of the comparative advantages
  presuppose finalizing "free and fully open" (restoration of the
  license notice; Sec. 34.3).

## 4. Remaining items: who implements them, and directions

- **Snow accumulation and snowmelt**: implemented with the degree-day
  method (Sec. 31; 2026-08-10). Double-threshold rain/snow
  partitioning + snowline by elevation lapse rate + direct injection
  of snowmelt into h. The energy balance method comes after adding
  radiation and wind speed slots to m_meteo (handoff 1m).
- **Glaciers**: hydrologically, a glacier is "a perennial snowpack
  with accumulation and ablation", an extension of the degree-day
  method (the same idea as OGGM). If ice-body flow is to be included,
  the SIA (shallow ice approximation) has a structure similar to the
  shallow water equations, so it fits the framework well.
- **Long-term landform evolution**: the supply side (bedrock
  weathering = soil production function, uplift) and cyclic forcing
  t_cycle are implemented (Sec. 32; 2026-08-10). Together with the
  existing transport side (erosion, deposition, and collapse with
  MORFAC), it can constitute the same "landscape evolution driven by
  real hydraulics" as CAESAR-Lisflood, with more refined hydraulics.
  The execution style is repetition of representative hydrology x
  MORFAC x restart chaining (Sec. 32.3). Remaining: distributed
  uplift, bulking, demonstration runs (handoff 1n).
  Landlab/Badlands/FastScape are process-law LEMs (simplified
  hydraulics) and occupy a separate niche.
