# ENCflow

[![CI](https://github.com/ENCflow/ENCflow/actions/workflows/ci.yml/badge.svg)](https://github.com/ENCflow/ENCflow/actions/workflows/ci.yml)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.22042847-blue)](https://doi.org/10.5281/zenodo.22042847)

**Solving surface-water phenomena seamlessly on a single grid** —
from river flooding, storm surge, and tsunami run-up to rainfall–runoff,
groundwater, sediment, water quality, snow, glaciers, and landscape
evolution, all in one Fortran program.

ENCflow aims to:

1. **represent the process chains of the Earth's surface as one
   model,**
2. **be a laboratory where whatever catches your interest can be put
   to a numerical experiment right away, and**
3. **make it easier for researchers and students to take a first step
   into the field next door.**

Replacing each field's specialist models is not the goal.

[日本語 README](README.md) /
[Installation](docs/en/install.md) /
[Tutorial](docs/en/tutorial.md) /
[User's Guide](docs/en/users_guide.md) /
[Comparison with other models](docs/en/comparison.md)

*The Japanese documentation is the authoritative version; the English
pages are derived mirrors. The user-facing documentation — README,
installation, tutorials, user's guide, use-case gallery, comparison,
and the AI guide — is fully mirrored in English (docs/en/); developer
documentation (developer.md etc.) is currently Japanese only.*

---

## What is ENCflow?

ENCflow is a simulation program that computes many processes related to
overland water flow **simultaneously on the same raster grid**, built
around the two-dimensional shallow water equations (dynamic wave). It
uses an original **eight-neighborhood connected collocated grid (ENC
grid)** ([Tada, 2026](https://doi.org/10.3178/hrl.25-00052)), in which
flow along all eight directions — including the diagonals — suppresses
the grid-direction-dependent spurious depressions and flow blockages of
conventional four-neighbor rasters. This grid is where the name comes
from.

Ordinarily, river flooding, catchment hydrology, sediment transport,
water quality, and snow/ice are computed with separate software packages,
passing results from one to the next. ENCflow handles all of them in a
single program with a single input system. Processes you do not need
are simply left unactivated — and each additional configuration file
you drop in makes the model one step smarter.

ENCflow is also designed to **lower the barrier to running a first
computation outside your own field**. When a river engineer wants to
try groundwater, a geomorphologist wants to try floods, or a
hydrologist wants to try sediment or water quality, there is no need
to learn an entirely new modeling system — you keep the same grid and
the same input system, and add the processes you need one at a time.

**All you need is a Fortran compiler.** Zero external libraries. The
same source code runs unchanged on a student's laptop, a lab
workstation, or a supercomputer. On a laptop, OpenMP automatically uses
every core; on large machines, hybrid OpenMP×MPI parallelism scales
across nodes.

## Your first simulation in five minutes

```bash
git clone https://github.com/ENCflow/ENCflow.git
cd ENCflow/src && make install
cd ../test/wave && ./Run.sh
```

**You can also try it without installing anything** — a
[Colab notebook](https://colab.research.google.com/github/ENCflow/ENCflow/blob/main/docs/en/colab_quickstart.ipynb)
runs entirely in the browser (Windows users new to Unix: see
[Using ENCflow on Windows](docs/en/windows.md)).

The first example is nothing more than a mound of water collapsing and
spreading over a still surface. The input is a single text file a few
dozen lines long. From there, the ENCflow way is to grow the model one
line at a time: add rainfall, switch to real terrain, thread a river
channel, add groundwater… ([Tutorial](docs/en/tutorial.md)).

## What it can do

Each item below corresponds to an independent research topic or
practical application, yet all share the same input system, the same
grid, and the same way of running. They are not mutually exclusive
modes — **any combination can be activated at once**, and interactions
between processes (rainfall → snowmelt → runoff → erosion →
inundation…) are solved within the same time evolution. You do not
need to understand all of it — **feel free to read only the lines you
care about.**

- **River flooding and inundation**: dynamic-wave shallow water
  equations on the ENC grid. Subgrid channels (cross-section shape and
  width), levee breach, and a family of structures up to pumps, sluice
  gates, culverts, diversions, and dam operation.
- **Storm surge and tsunami run-up**: coastal inundation driven by
  tide/sea-level time series on sea cells. The dynamic wave with
  wetting-and-drying tracks the run-up front. Storm surge + river flood
  + heavy rainfall — **compound flooding in a single model**. Combined
  with the driftwood feature it also handles Isewan-typhoon-style
  timber influx from coastal log yards into urban areas.
- **Rainfall–runoff and catchment hydrology**: rainfall (uniform or
  distributed), canopy interception, evapotranspiration
  (Hamon/Thornthwaite with temperature lapse rate), Green–Ampt
  infiltration, and two-layer groundwater (soil-layer Boussinesq plus a
  weathered-bedrock layer) providing baseflow and recession. Well
  pumping / groundwater abstraction sinks (cells + time series) for
  drawdown analysis.
- **Seawater intrusion and salt wedges**: with a fresh/salt two-layer
  (sharp interface) approximation, seawater intrusion into and retreat
  from aquifers (Ghyben-Herzberg), freshwater lenses, pumping-induced
  intrusion and well salinization, and where the seawater that ran up
  in a storm surge or tsunami ends up - on the same grid as the
  surface and ground water.
- **Urban pluvial flooding (sewer drainage and surcharge)**: the sewer
  network is represented as an equivalent continuum (an artificial
  confined layer) with per-cell capacity and 8-direction conveyances,
  fully coupled with the surface inundation in a single time evolution
  - from inlet uptake through pipe-full pressurized flow (surcharge) to
  manhole eruption, sea outfalls, and pump stations (pumps drawing
  directly from the conduit layer). The same machinery applies to
  fractured bedrock, karst, farmland tile drains, and qanats
  (groundwater-collecting galleries).
- **Sediment and slope hazards**: riverbed evolution by bedload and
  suspended load, hillslope erosion, slope failure (stability
  analysis), and debris flow. Terrain and soil depth evolve during the
  computation and feed back into the flow. **Driftwood** — its
  generation (washout of standing trees, uprooting entrainment by
  erosion), transport and deposition — can be assessed as maps (a
  mixed debris-flow-and-driftwood surge only needs both features
  enabled). Hazard outputs (safety factor Fs maps, maximum flow depth,
  fluid force and driftwood arrival) and the operational **Soil Water
  Index** (JMA 3-tank model; dedicated runs) are included.
- **Volcanic hazards (density flows)**: sector collapse (debris
  avalanches), pyroclastic flows, and lahars, with their deposition
  and natural dam formation, as equivalent-fluid analyses (Voellmy and
  constant-retarding-stress laws — the same formulation level as
  dedicated models). The chain from eruption supply through runout,
  deposition, natural damming, dam-break flooding, and
  rainfall-triggered secondary lahars can be followed **in a single
  run**.
- **Lava flows**: effusion from a set of vent cells (an effusion-rate
  time series), Bingham viscous spreading and stopping (viscosity and
  yield stress given directly), and solidification into lava-field
  topography. Because solidified lava becomes the bed, **subsequent
  rainfall, floods, and sediment transport flow over the new
  topography** in the same run.
- **Water quality and mass transport**: load runoff from point sources,
  areal sources, land-use-specific unit loads, and wet deposition;
  advective transport, decay and settling, buildup–washoff (nonlinear
  L–Q). **Kd two-phase partitioning** of sorbing substances such as
  heavy metals (tied to suspended sediment), **transport through
  groundwater** (infiltration → lateral flow → seepage, with sorption
  retardation) and **completely mixed reservoirs and ponds** close the
  mass budget across surface, subsurface and impounded water in one
  run. Coupled with the urban sewer layer, it assesses the
  **sanitation risk of sewage eruption (E. coli spreading with the
  floodwater)**; also suited to radionuclide runoff analysis.
- **Snow accumulation and melt**: degree-day method. With the
  temperature lapse rate, the snow line emerges automatically.
  Infiltration suppression by frozen ground (a temperature-driven
  freezing index) captures snowmelt floods running over frozen soil.
  Runout and deposition of **dense-flow snow avalanches** can also be
  analyzed with the same equivalent fluid (Voellmy law) as the
  volcanic flows.
- **Glaciers**: firnification of perennial snow (accumulation) and
  ice-surface melt, ice flow by the shallow ice approximation (SIA),
  basal sliding with glacial erosion, and avalanche redistribution of
  snow. Glacier meltwater feeds the runoff and flood computation, and
  long-term experiments can form glacial landforms such as cirques.
- **Long-term landscape evolution**: bedrock weathering (soil
  production), uplift, and repeated representative hydrology for
  millennium-scale landscape evolution experiments (a landscape
  evolution model driven by real hydraulics).

Any process that is not used **consumes no memory and no CPU time at
all**. In its minimal configuration, ENCflow is simply a fast,
well-behaved 2-D flood model.

To look up the feature combination and key settings from the
phenomenon you want to compute (farm-pond breach, open levees and
detention basins, polder drainage, rainfall-induced slope failure,
glacial lake outburst floods, and more), see the
**[use-case gallery](docs/en/users_guide/usecases.md)**. And
[with an AI agent](docs/en/ai_guide.md) you can **start from a model
case described in the words of the phenomenon**, without looking
anything up yourself.

The relationship between ENCflow and each field resembles the one
between Excel and accounting. Just as having Excel does not make you
an accountant, having ENCflow does not make you an expert in any of
these fields. But just as an accountant with Excel can get remarkably
far even without software optimized for the purpose, ENCflow is a
powerful tool in the hands of each field's experts. Just as Excel
serves those beginning to learn accounting, ENCflow serves
researchers and students entering a neighboring field as the entry
point where they first compute and understand its phenomena (with
[support from an AI agent](docs/en/ai_guide.md) available as well). And just
as Excel is not dedicated to accounting, ENCflow aims to be a common
platform for numerical experiments shared across disciplines.

## What it deliberately does not do

ENCflow intentionally stays within the two-dimensional
(depth-averaged, constant-density, hydrostatic) world. The following
are out of scope by design and belong to specialized models
([comparison](docs/en/comparison.md)):

- **Wind waves** — short-period waves (wind waves, swell, breaking).
  Storm surge and tsunami are long waves and can be solved; wave
  computation is the realm of dedicated wave models.
- **Pyroclastic surges, eruption plumes, and atmospheric ash
  transport** — compressible, three-dimensional atmospheric phenomena
  outside the shallow-water approximation (the volcanic *density
  flows* above are covered; give ash-fall deposit distributions to the
  terrain and soil layer in preprocessing and their
  rainfall-triggered secondary lahars can be analyzed).
- **Water temperature** — no energy balance is solved, so water
  temperature itself is not predicted (temperature-based corrections
  for snowmelt, evapotranspiration, and water quality are handled via
  air temperature).
- **The dynamics of density currents and stratification** — the
  momentum equations keep a constant density. Fresh/salt two-layer
  phenomena (salt wedges, seawater intrusion, freshwater lenses) are
  handled with a sharp-interface approximation, but mixing and
  entrainment (brackish water generation), internal waves, and
  reservoir thermal stratification cannot be reproduced; nor can
  vertical structure such as secondary flow in bends.
- **Individual sewer pipes and operational control** — tracking
  individual pipes, and network analyses involving **control structures
  driven by operating rules** (pumps, weirs, outfalls, CSOs), are the
  realm of network models (dedicated 1-D pipe-network models;
  standalone structures are
  covered by the internal hydraulic structures; the areal drainage
  capacity, pressurized flow, and eruption of dense street-level
  networks are covered by the conduit continuum layer. Being a
  continuum approximation, it reproduces the spatial pattern of
  surcharge but cannot identify *which* manhole erupts. Systems
  dominated by a single trunk main also belong to network models).
- **Deep groundwater** — ENCflow's groundwater is a shallow two-layer
  system (plus the conduit continuum layer) for runoff analysis. The
  "confined" state of the conduit layer is an artificial confinement
  representing pipe-full pressurized flow; the hydraulics of natural
  regional confined aquifers belong to 3-D groundwater models. Pumping
  is given as a cell-scale sink; borehole-scale hydraulics (well
  radius, skin, partial penetration, lift) are not represented.

## Why choose ENCflow

- **Absolute portability with zero dependencies** — the only
  dependencies are the language standard and OpenMP/MPI (open
  standards). Even GeoTIFF reading/writing and decompression are
  implemented in-house. You will never be defeated by "it won't build."
- **A single source from laptop to supercomputer** — on a single
  machine, OpenMP threading uses all cores with no configuration. On
  workstations and supercomputers, one line in the make configuration
  switches to hybrid OpenMP×MPI — threads within a node, MPI across
  nodes — scaling to large runs with the same input files.
- **Reproducible results** — bit-identical answers regardless of the
  number of threads or MPI ranks. Restarts match uninterrupted runs
  exactly. This directly serves research reproducibility and
  professional accountability.
- **Progressive refinement by design** — start from minimal "it just
  runs" parameters and refine step by step as data becomes available.
  Every feature is built with this philosophy.
- **A gateway to the field next door** — estimate with a simple model
  whether a process matters, and move on to a specialist model of that
  field only once you know it does. ENCflow is also a common ground
  for that first step (what it lowers is the barrier to *trying*:
  interpreting the results still takes the knowledge of the field).
- **Simple text input and output** — matrix text, namelists, and CSV
  (plus GeoTIFF for practical work). Pre- and post-process with GIS,
  Python, Excel — whatever you prefer.
- **High affinity with script automation** — because the parameter
  files are plain text (namelists), you can generate cases
  mechanically with sed or Python, run them in batch, and diff or
  aggregate the text outputs, all from shell scripts alone. This suits
  sensitivity analysis, calibration, and bulk scenario runs. The same
  property extends directly to **advanced automation by AI**: since
  the input and output are pure text, AI agents can drive case
  generation, execution, verification, and analysis directly. In
  practice, ENCflow's own regression tests (test/*/Run.sh: generating
  derived cases and automatically comparing against references) run on
  exactly this machinery, and much of the development and verification
  of this very project is carried out in collaboration with AI agents
  — both are working **demonstrations** of the claim.
- **Full source code available** — inspect it, verify it. The
  computational code is written entirely from scratch and **contains
  no third-party code** (zero dependencies also means a clean,
  unambiguous copyright provenance). Licensed under Apache-2.0,
  **commercial use included**.
- **Sustainability as a project** — everything from the reasoning
  behind each design decision ([docs/developer.md](docs/developer.md),
  in Japanese) to the overall map
  ([docs/architecture.md](docs/architecture.md)) is documented, and
  the correctness of changes is verified mechanically by the
  regression tests (bit reproducibility) and CI. Because the
  development knowledge lives in the repository itself, combined with
  the fully open source code (Apache-2.0), **development can be
  continued by third parties** even if the current developers do not
  — and AI agents make that easier still (this project itself is the
  demonstration).

## Requirements

| | Required | Notes |
|---|---|---|
| Fortran compiler | Yes | Tested with gfortran / Intel ifx / NVIDIA / AMD / NEC. OpenMP enabled by default |
| MPI | Optional | Only for hybrid (OpenMP×MPI) runs across nodes (OpenMPI, MPICH, etc.) |
| Other libraries | **None** | — |

Linux, macOS, and WSL are the assumed platforms. See the
[installation guide](docs/en/install.md). Windows users new to Unix:
start from [Using ENCflow on Windows](docs/en/windows.md) (a Colab
notebook that runs in the browser alone is also available).

## Learning to use it

1. [Installation](docs/en/install.md) — a single `make install`
2. [Tutorial](docs/en/tutorial.md) — from the minimal example to real-terrain catchments
3. [User's Guide](docs/en/users_guide.md) — reference for every setting
4. [examples/](examples/) — sample configuration files
5. [test/](test/) — verified examples (doubling as regression tests)
6. [Using ENCflow with AI agents](docs/en/ai_guide.md) — delegating
   case building, execution, and analysis to an AI in the words of the
   phenomenon

When you want algorithm or implementation details that the
documentation does not cover, the quickest route is to have an AI
agent examine the source code for you. The entire computation lives
in the Fortran under `src/`, and the reasons behind every design
decision are documented in
[docs/developer.md](docs/developer.md), so a question like "which
equation computes X, and where?" can be answered with the actual
code as evidence.

Developers and the curious should head to
[docs/architecture.md](docs/architecture.md) (in Japanese) (the
one-page map of the architecture — read this first),
[docs/developer.md](docs/developer.md) (in Japanese) (the authoritative source for
design philosophy and conventions) and
[docs/comparison.md](docs/en/comparison.md) (comparison with other
models). Developer documentation is currently in Japanese.

## Interoperability (BMI)

ENCflow implements the CSDMS [Basic Model Interface (BMI) 2.0](https://bmi.csdms.io/)
and passes the official conformance test (bmi-tester). The whole model
becomes a single BMI component that can be controlled from outside
through the standard initialize / update / get_value / set_value calls.

- **Drive it from Python** — no extra tooling beyond numpy. You can pause
  the run at any interval and pull out fields such as water depth, so the
  evolving inundation map can be rendered live with matplotlib while the
  model runs (sample: [bmi/python/live_view.py](bmi/python/live_view.py)).
- **Couple with other models** — connects to the BMI ecosystem such as
  Landlab and pymt. Rainfall (external forcing) and terrain / water depth
  (state exchange) can be set as well as read, and array layout and grid
  metadata are self-describing in the BMI standard convention, so the
  partner never needs to flip row order.
- **The core is untouched** — BMI lives in the optional `bmi/` adapter;
  the regular builds (encflow / encflow_mpi) remain dependency-free as
  before.

See [bmi/README.md](bmi/README.md) for usage, exposed variables, and how
to reproduce the conformance check, and
[docs/bmi_plan.md](docs/bmi_plan.md) for the design history and roadmap.

## Who it is for

- **Students and educators** — runs with nothing but a compiler, takes
  a single text file as input, and produces results that plot
  immediately. Suited to hydraulics and hydrology coursework.
- **Researchers** — process interactions (e.g., slope failure → debris
  flow → channel blockage → inundation, or weathering → soil →
  erosion) in a single model. Bit reproducibility makes numerical
  experiments strictly comparable.
- **Practitioners** — inundation analysis, structure operation,
  sediment hazards, and water quality in one input system, with no
  tool-switching between projects — and a direct path to large runs on
  supercomputers.

## License

[Apache License 2.0](LICENSE). Commercial use, modification, and
redistribution are permitted (retaining the copyright notice and
[NOTICE](NOTICE); see LICENSE for details).
For citation in research, see [CITATION.cff](CITATION.cff).
Every release is archived on
[Zenodo](https://doi.org/10.5281/zenodo.22042847) with a DOI, so you
can cite the exact version you used.

## Development

- Hydraulic Engineering Laboratory, Department of Civil and
  Environmental Engineering, National Defense Academy of Japan
- Hydro-Environmental System Laboratory, Department of Civil
  Engineering, Tohoku University

Questions and consultations are welcome at
[Discussions](https://github.com/ENCflow/ENCflow/discussions);
clear bug reports and feature requests go to
[Issues](https://github.com/ENCflow/ENCflow/issues)
(see [CONTRIBUTING](CONTRIBUTING.en.md) for how to write them and the
current policy on code pull requests — when in doubt, Discussions is fine).
For citation in research, see [CITATION.cff](CITATION.cff).
