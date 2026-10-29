# ENCflow

> English mirror of README.ja.md. The Japanese file is the master copy.

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

[日本語 README](README.ja.md) /
[Installation](docs/en/install.md) /
[Tutorial](docs/en/tutorial.md) /
[User's Guide](docs/en/users_guide.md) /
[Comparison with other models](docs/en/comparison.md)

---

## What is ENCflow?

ENCflow is a simulation program that computes many processes related to
overland water flow simultaneously on the same raster grid, built
around the two-dimensional shallow water equations. It uses an original
eight-neighborhood connected collocated grid
([Tada, 2026](https://doi.org/10.3178/hrl.25-00052)), in which flow
along all eight directions, including the diagonals, suppresses the
grid-direction-dependent spurious depressions and flow blockages of
conventional four-neighbor rasters. The name ENC comes from this grid.

Ordinarily, river flooding, catchment hydrology, sediment transport,
water quality, and snow and ice are computed with separate software
packages, passing results from one to the next. ENCflow handles all of
them in a single program with a single input system. Processes you do
not need are simply left unactivated. Each additional configuration
file you drop in makes the model one step smarter.

ENCflow is also designed to lower the barrier to running a first
computation outside your own field. When a river engineer wants to try
groundwater, a geomorphologist wants to try floods, or a hydrologist
wants to try sediment or water quality, there is no need to learn an
entirely new modeling system. You keep the same grid and the same input
system, and add the processes you need one at a time.

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

You can also try it without installing anything: a
[Colab notebook](https://colab.research.google.com/github/ENCflow/ENCflow/blob/main/docs/en/colab_quickstart.ipynb)
runs entirely in the browser. Windows users new to Unix: see
[Using ENCflow on Windows](docs/en/windows.md).

The first example is nothing more than a mound of water collapsing and
spreading over a still surface. The input is [a single text file](tutorials/wave/en/param_step1.txt) a few
dozen lines long. From there, the ENCflow way is to grow the model one
line at a time: add rainfall, switch to real terrain, thread a river
channel, add groundwater ([Tutorial](docs/en/tutorial.md)).

## What it can do

Each item below corresponds to an independent research topic or
practical application, yet all share the same input system, the same
grid, and the same way of running. They are not mutually exclusive
modes: any combination can be activated at once, and interactions
between processes, from rainfall through snowmelt, runoff and erosion
to inundation, are solved within the same time evolution. You do not
need to understand all of it. Read only the lines you care about.

- **River flooding and inundation**: dynamic-wave shallow water
  equations. Subgrid channels, levee breach, and a family of structures
  up to pumps, sluice gates, culverts, diversions, and dam operation.
- **Storm surge and tsunami run-up**: coastal inundation driven by
  tide or sea-level time series on sea cells. The dynamic wave with
  wetting-and-drying tracks the run-up front. Storm surge, river flood
  and heavy rainfall form a compound flood in a single model. Timber
  influx from coastal log yards into urban areas is handled with the
  driftwood feature, and the destruction of wooden houses and the
  generation, flow and deposition of the resulting debris by the
  building-damage feature, both estimated in the same time evolution as
  the run-up, giving damage-ratio maps and
  debris arrival and deposit maps.
- **Coastal waves**: shoaling, refraction, breaking and the shadows of
  breakwaters and islands are computed for offshore waves on the same
  grid by a phase-averaged energy balance over directional bins, giving
  maps of wave height and direction. Wave setup and longshore currents
  (radiation stress, roller and GLM Stokes drift) can also be added to
  the shallow-water flow, and conversely river-mouth jets, tidal and
  longshore currents can change the waves (Doppler shift, refraction by
  currents and blocking) in a two-way coupling. Longshore sediment
  transport and beach erosion and recovery, with sand stirred by the wave
  field and carried by the wave-driven flow and wave asymmetry, are
  computed in the same time evolution as the morphology.
- **Tsunami generation from an earthquake, and dispersive waves**: the
  fault displacement is given as a time history of the ground, and the
  tsunami is followed from generation through propagation to run-up in
  one computation. Because land and sea cells move alike, the waves
  raised at the shore by coseismic coastal uplift and subsidence, and
  the flooding of subsided lowland, are in the same run. An optional
  one-layer non-hydrostatic correction covers the cases where
  dispersion is essential, such as soliton fission of a tsunami
  intruding up a river, solitary waves, and the near field of landslide
  tsunamis.
- **Rainfall–runoff and catchment hydrology**: uniform or distributed
  rainfall, canopy interception, evapotranspiration, Green–Ampt
  infiltration, and two-layer groundwater in a soil layer and a
  weathered-bedrock layer providing baseflow and recession. Well
  pumping and groundwater abstraction sinks for drawdown analysis.
  Also Tani's VZ model, which derives the runoff response of mountain
  hillslopes from vertical unsaturated infiltration (the one-dimensional
  Richards equation on shared reference columns, read out at the soil
  depth of the zones and drained directly to outlets).
- **Seawater intrusion and salt wedges**: with a fresh/salt two-layer
  sharp-interface approximation, seawater intrusion into and retreat
  from aquifers, freshwater lenses, pumping-induced intrusion and well
  salinization, and where the seawater that ran up in a storm surge or
  tsunami ends up, on the same grid as the surface and ground water.
- **Urban pluvial flooding**: the sewer network is represented as an
  equivalent continuum with per-cell capacity and 8-direction
  conveyances, fully coupled with the surface inundation in a single
  time evolution, from inlet uptake through pipe-full pressurized flow
  to manhole eruption, sea outfalls, and pump stations. The same
  machinery applies to fractured bedrock, karst, farmland tile drains,
  and qanats.
- **Sediment and slope hazards**: riverbed evolution by bedload and
  suspended load, hillslope erosion, slope failure, and debris flow.
  Terrain and soil depth evolve during the computation and feed back
  into the flow. The development of meandering channels (bed-load
  direction correction in bends, bank erosion, angle-of-repose
  avalanching, vegetation fixation of inner-bank bars, neck cutoff, a
  ledger of fines in the bed) emerges as landform change on the same
  grid. Driftwood generation, transport and deposition can be
  assessed as maps, and a mixed debris-flow-and-driftwood surge only
  needs both features enabled. Hazard outputs such as safety-factor
  maps, maximum flow depth, fluid force and driftwood arrival, and the
  operational Soil Water Index are included.
- **Volcanic hazards**: sector collapse, pyroclastic flows, and lahars,
  with their deposition and natural dam formation, as equivalent-fluid
  analyses. The chain from eruption supply through runout, deposition,
  natural damming, dam-break flooding, and rainfall-triggered secondary
  lahars can be followed in a single run. Sending the collapsed mass
  into a lake or the sea as a "moving bed layer" extends the same run
  to landslide tsunamis, including submarine slides, from generation
  through propagation to run-up.
- **Lava flows**: effusion from a set of vent cells, Bingham viscous
  spreading and stopping, and solidification into lava-field
  topography. Because solidified lava becomes the bed, subsequent
  rainfall, floods, and sediment transport flow over the new topography
  in the same run.
- **Water quality and mass transport**: load runoff from point sources,
  areal sources, land-use-specific unit loads, and wet deposition;
  advective transport, decay and settling, buildup and washoff.
  Two-phase partitioning of sorbing substances such as heavy metals,
  transport through groundwater, and completely mixed reservoirs and
  ponds close the mass budget across surface, subsurface and impounded
  water in one run. Also suited to the sanitation risk of sewage
  eruption and to radionuclide runoff analysis.
- **Snow accumulation and melt**: degree-day method. With the
  temperature lapse rate, the snow line emerges automatically.
  Infiltration suppression by frozen ground captures snowmelt floods
  running over frozen soil. Runout and deposition of dense-flow snow
  avalanches can also be analyzed with the same equivalent fluid as the
  volcanic flows.
- **Glaciers**: firnification of perennial snow and ice-surface melt,
  ice flow by the shallow ice approximation, basal sliding with glacial
  erosion, and avalanche redistribution of snow. Glacier meltwater
  feeds the runoff and flood computation, and long-term experiments can
  form glacial landforms such as cirques.
- **Long-term landscape evolution**: bedrock weathering, uplift, and
  repeated representative hydrology for millennium-scale landscape
  evolution experiments, a landscape evolution model driven by real
  hydraulics.

Any process that is not used consumes no memory and no CPU time at
all. In its minimal configuration, ENCflow is simply a fast,
well-behaved 2-D flood model.

To look up the feature combination and key settings from the
phenomenon you want to compute, see the
[use-case gallery](docs/en/users_guide/usecases.md). And
[with an AI agent](docs/en/ai_guide.md) you can start from a model
case described in the words of the phenomenon, without looking
anything up yourself.

## What it deliberately does not do

ENCflow intentionally stays within the depth-averaged, constant-density,
two-dimensional world. The following are out of scope by design and
belong to specialized models
([comparison](docs/en/comparison.md)).

- **Wind waves** — short-period waves such as wind waves, swell and
  breaking. Storm surge and tsunami are long waves and can be solved,
  and the non-hydrostatic correction covers the dispersion of long
  waves, but wave computation is the realm of dedicated wave models.
- **Pyroclastic surges, eruption plumes, and atmospheric ash
  transport** — compressible, three-dimensional atmospheric phenomena
  outside the shallow-water approximation. The volcanic density flows
  above are covered, and if ash-fall deposit distributions are given to
  the terrain and soil layer in preprocessing, their rainfall-triggered
  secondary lahars can be analyzed.
- **Water temperature** — no energy balance is solved, so water
  temperature itself is not predicted. Temperature corrections for
  snowmelt, evapotranspiration, and water quality are handled via air
  temperature.
- **The dynamics of density currents and stratification** — the
  momentum equations keep a constant density. Fresh/salt two-layer
  phenomena are handled with a sharp-interface approximation, but
  mixing and entrainment, internal waves, and reservoir thermal
  stratification cannot be reproduced. Vertical structure itself is not
  resolved either: secondary flow in bends is not carried as a vertical
  velocity profile, only its effect on the bed-load direction enters,
  through an equilibrium parameterisation.
- **Individual sewer pipes and operational control** — tracking
  individual pipes, and network analyses involving control structures
  driven by operating rules, are the realm of dedicated 1-D pipe-network
  models. Standalone structures are covered by the internal hydraulic
  structures, and the areal drainage capacity, pressurized flow, and
  eruption of dense street-level networks by the conduit continuum
  layer; being a continuum approximation, it cannot identify which
  manhole erupts.
  Systems dominated by a single trunk main also belong to network
  models.
- **Deep groundwater** — ENCflow's groundwater is a shallow two-layer
  system for runoff analysis. The "confined" state of the conduit layer
  is an artificial confinement representing pipe-full pressurized flow;
  the hydraulics of natural regional confined aquifers belong to 3-D
  groundwater models. Pumping is given as a cell-scale sink, and
  borehole-scale hydraulics are not represented.

## Why choose ENCflow

- **Absolute portability with zero dependencies** — the only
  dependencies are the language standard and the open standards OpenMP
  and MPI. Even GeoTIFF reading and writing and decompression are
  implemented in-house. You will never be defeated by "it won't build."
- **A single source from laptop to supercomputer** — on a single
  machine, OpenMP threading uses all cores with no configuration. On
  workstations and supercomputers, one line in the make configuration
  switches to hybrid OpenMP×MPI, threads within a node and MPI across
  nodes, scaling to large runs with the same input files.
- **Reproducible results** — with the same executable, input, and
  computing environment, bit-identical answers regardless of the number
  of threads or MPI ranks is the rule of ENCflow's parallelization,
  checked by the regression tests. Restarts match uninterrupted runs
  exactly. This directly serves research reproducibility and
  professional accountability. Bitwise agreement holds under
  conditions: build settings (optimization flags, real precision) and
  the enabled features impose limits (e.g. multi-threaded OpenMP runs
  of the non-hydrostatic solver, or BMI runs through the shared
  library). See [Parallel execution](docs/en/users_guide/parallel.md)
  and the known issues in each release note.
- **Progressive refinement by design** — start from minimal "it just
  runs" parameters and refine step by step as data becomes available.
  Every feature is built with this philosophy.
- **A gateway to the field next door** — estimate with a simple model
  whether a process matters, and move on to a specialist model of that
  field only once you know it does. ENCflow is also a common ground
  for that first step. What it lowers is the barrier to trying;
  interpreting the results still takes the knowledge of the field.
- **Simple text input and output** — matrix text, namelists, and CSV,
  plus GeoTIFF for practical work. Pre- and post-process with GIS,
  Python, Excel, whatever you prefer.
- **High affinity with script automation** — because the parameter
  files are plain text, you can generate cases mechanically with sed or
  Python, run them in batch, and diff or aggregate the text outputs,
  all from shell scripts alone. This suits sensitivity analysis,
  calibration, and bulk scenario runs. The same property extends
  directly to advanced automation by AI: since the input and output are
  pure text, AI agents can drive case generation, execution,
  verification, and analysis directly. Much of the development and
  verification of ENCflow itself is carried out in collaboration with
  AI agents, and this project is the demonstration.
- **Full source code available** — inspect it, verify it. The
  computational code is written entirely from scratch and contains no
  third-party code; zero dependencies also means a clean, unambiguous
  copyright provenance. Licensed under Apache-2.0, commercial use
  included.
- **Accountable through sources, verification, and consistency** —
  the sources of each model, governing equation, and parameter are
  cited wherever possible, and simplifications of our own that rest on
  no literature are labelled as such. Behaviour with an analytical
  solution or a conservation law is checked by self-judging
  verification scripts, separately from the regression against
  reference results. Agreement between code and documentation, between
  originals and translations, and between tests and their references
  is checked mechanically by CI. Keeping the state in which a third
  party can trace "why this result" is a basic policy alongside full
  source disclosure ([docs/developer.md](docs/developer.md) §0; English
  translation of §0 in [docs/en/developer.md](docs/en/developer.md)).
- **Sustainability as a project** — everything from the reasoning
  behind each design decision ([docs/developer.md](docs/developer.md),
  in Japanese) to the overall map
  ([docs/architecture.md](docs/architecture.md), in Japanese) is
  documented, and
  the correctness of changes is verified mechanically by the
  regression tests and CI. Because the development knowledge lives in
  the repository itself, combined with the fully open source code,
  development can be continued by third parties even if the current
  developers do not.

## Requirements

| | Required | Notes |
|---|---|---|
| Fortran compiler | Yes | Tested with gfortran / Intel ifx / NVIDIA / AMD / NEC. OpenMP enabled by default |
| MPI | Optional | Only for hybrid runs across nodes. OpenMPI, MPICH, etc. |
| Other libraries | None | — |

Linux, macOS, and WSL are the assumed platforms. See the
[installation guide](docs/en/install.md). Windows users new to Unix:
start from [Using ENCflow on Windows](docs/en/windows.md). A Colab
notebook that runs in the browser alone is also available.

## Learning to use it

1. [Installation](docs/en/install.md) — a single `make install`
2. [Tutorial](docs/en/tutorial.md) — from the minimal example to real-terrain catchments
3. [User's Guide](docs/en/users_guide.md) — reference for every setting
4. [examples/](examples/README.en.md) — sample configuration files
5. [test/](test/README.en.md) — verified examples, doubling as regression tests
6. [Using ENCflow with AI agents](docs/en/ai_guide.md) — delegating
   case building, execution, and analysis to an AI in the words of the
   phenomenon

When you want algorithm or implementation details that the
documentation does not cover, the quickest route is to have an AI
agent examine the source code for you. The entire computation lives
in the Fortran under `src/`, and the reasons behind every design
decision are documented in
[docs/developer.md](docs/developer.md) (in Japanese), so a question like "which
equation computes X, and where?" can be answered with the actual
code as evidence.

Developers and the curious should head to
[docs/architecture.md](docs/architecture.md) for the one-page map of
the architecture, [docs/developer.md](docs/developer.md) for the
authoritative source on design philosophy and conventions (the project
policy §0 is in English in [docs/en/developer.md](docs/en/developer.md); both in
Japanese), and [docs/en/comparison.md](docs/en/comparison.md) for the
comparison with other models.

## Interoperability (BMI)

ENCflow implements the CSDMS [Basic Model Interface (BMI) 2.0](https://bmi.csdms.io/)
and passes the official conformance test bmi-tester. The whole model
becomes a single BMI component that can be controlled from outside
through the standard initialize / update / get_value / set_value calls.

- **Drive it from Python** — no extra tooling beyond numpy. You can pause
  the run at any interval and pull out fields such as water depth, water
  level, and flow speed, so you can render results live while the model
  runs, or sweep through many scenarios from a script.
- **Combine it with other models** — BMI is a common socket adopted by
  models across hydrology, geomorphology, oceanography, snow and ice,
  and beyond, for plugging models into one another. It is a door to
  going beyond ENCflow's own limits: physics that ENCflow deliberately
  leaves out, such as deep three-dimensional groundwater or wind waves,
  can be solved in one connected system by exchanging state with the
  specialist model of that field. And the direction reverses: external
  systems can call on ENCflow's flood hydraulics as an engine. A
  continental-scale hydrology model can dispatch ENCflow to resolve
  high-resolution inundation just in the basins at risk, or a
  forecasting system that assimilates observations while it runs can
  use ENCflow as its flood component.
- **A whole model, or a small part** — ENCflow is a self-contained model
  with many processes, yet a feature that is not enabled costs no memory
  and no CPU, and needs no parameter file of its own. Minimal
  configurations such as shallow water only, or groundwater only, run
  light, so ENCflow also serves as a small component that another model
  calls to supply a process it lacks. This is in the spirit of what CSDMS
  pursues with BMI: composing models from interchangeable parts.
- **The core is untouched** — BMI lives in the optional `bmi/` adapter;
  the regular builds remain dependency-free as before.

See [bmi/README.en.md](bmi/README.en.md) for usage, exposed variables,
and how to reproduce the conformance check, and
[docs/bmi_plan.md](docs/bmi_plan.md), in Japanese, for the design
history and roadmap.

## Who it is for

- **Students and educators** — runs with nothing but a compiler, takes
  a single text file as input, and produces results that plot
  immediately. Suited to hydraulics and hydrology coursework.
- **Researchers** — process interactions such as slope failure leading
  to debris flow, channel blockage and inundation, or weathering
  leading to soil and erosion, in a single model. Bit reproducibility of
  runs under matched conditions makes numerical experiments strictly
  comparable.
- **Practitioners** — inundation analysis, structure operation,
  sediment hazards, and water quality in one input system, with no
  tool-switching between projects, and a direct path to large runs on
  supercomputers.

## License

[Apache License 2.0](LICENSE). Commercial use, modification, and
redistribution are permitted, retaining the copyright notice and
[NOTICE](NOTICE); see LICENSE for details.
In research, please cite both **the ENCflow software version you
used** (every release is archived on
[Zenodo](https://doi.org/10.5281/zenodo.22042847) with a DOI, so you
can cite the exact version) and **the article on the underlying ENC
grid and numerical scheme** ([Tada, 2026](https://doi.org/10.3178/hrl.25-00052),
Hydrological Research Letters). See [CITATION.cff](CITATION.cff) for
the formats. That article covers the base scheme; a model description
paper of ENCflow as a whole (the individual process models and their
coupling) has not been published yet. For what each feature has been
verified against and the limits of its applicability, see the
[list of verification cases](test/README.en.md) and the
[users guide](docs/en/users_guide.md).
For the use of the ENCflow name and official logos, see the
[ENCflow Name and Trademark Policy](TRADEMARKS.md).

## Development

- Hydraulic Engineering Laboratory, Department of Civil and
  Environmental Engineering, National Defense Academy of Japan
- Hydro-Environmental System Laboratory, Department of Civil
  Engineering, Tohoku University

Questions and consultations are welcome at
[Discussions](https://github.com/ENCflow/ENCflow/discussions);
clear bug reports and feature requests go to
[Issues](https://github.com/ENCflow/ENCflow/issues).
See [CONTRIBUTING](CONTRIBUTING.en.md) for how to write them and the
current policy on code pull requests; when in doubt, Discussions is fine.
For citation in research, see [CITATION.cff](CITATION.cff).
