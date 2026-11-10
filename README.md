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
[Examples](examples/README.en.md) /
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

Every item uses the same input, the same grid, and the same way of
running, and any combination can be enabled at once. Chains of
phenomena, from rainfall through snowmelt, runoff and erosion to
inundation, interact within a single run. Read only the lines you care
about.

- **River flooding and inundation**: water spilling from rivers and
  spreading over the land, levee breaches, and the effect of operating
  pumps, sluice gates and dams on the flooding.
- **Storm surge and tsunami run-up**: surge and tsunami running up onto
  land, and compound disasters where they coincide with river floods
  and heavy rain. The fate of timber swept away and of debris from
  destroyed houses can also be estimated.
- **Coastal waves**: wave heights along the coast, including the
  shadows of breakwaters and islands, wave setup and longshore
  currents, the contest between waves and currents at river mouths,
  and beach erosion and recovery.
- **Earthquake tsunamis**: a tsunami from fault motion, from generation
  through propagation to run-up, together with coseismic uplift and
  subsidence and the flooding of lowland. Also waves where dispersion
  matters, such as a tsunami splitting up as it travels up a river, or
  landslide tsunamis.
- **Rainfall–runoff and catchment hydrology**: where the rain goes
  (interception by the canopy, evapotranspiration, infiltration,
  baseflow from groundwater). Also the runoff response of mountain
  hillslopes and the drawdown of groundwater by well pumping.
- **Seawater intrusion and salt wedges**: seawater intruding into and
  retreating from coastal aquifers, freshwater lenses, wells turning
  saline under pumping, and where the seawater that ran up in a storm
  surge or tsunami ends up.
- **Urban pluvial flooding**: flooding when the sewers overflow, from
  inlet uptake through manhole eruption to outfalls and pump stations.
  Also the water in fractured bedrock, karst, tile drains and qanats.
- **Sediment and slope hazards**: riverbed erosion and deposition,
  hillslope erosion and failure, debris flows, the growth and cutoff of
  meanders, and driftwood. The changed terrain changes the flow in
  turn. Hazard maps and the Soil Water Index are included.
- **Volcanic hazards**: sector collapse, pyroclastic flows and lahars
  with their deposits, natural dams forming and breaking, and
  rain-triggered secondary lahars, up to landslide tsunamis where the
  collapsed mass plunges into a lake or the sea.
- **Lava flows**: lava flowing from vents, stopping and solidifying,
  and the rain, floods and sediment that then flow over the new lava
  field.
- **Water quality and mass transport**: runoff and transport of
  pollutant loads, decay and settling, buildup and washoff, sorbing
  substances such as heavy metals, movement through groundwater, and
  mixing in reservoirs. Also for the sanitation risk of sewage eruption
  and the runoff of radionuclides.
- **Snow accumulation and melt**: snowpack and melt that change with
  elevation, snowmelt floods running over frozen ground, and the runout
  and deposits of snow avalanches.
- **Glaciers**: glacier accumulation, flow and melt with meltwater
  runoff, glacial erosion, and the formation of landforms such as
  cirques.
- **Long-term landscape evolution**: landscapes developing over
  millennia through weathering, uplift and repeated runoff events.

Processes you do not use consume no memory or CPU time and need no
settings file. In its minimal configuration, ENCflow is simply a fast,
well-behaved 2-D flood model.

To look up the feature combination and key settings from a phenomenon,
see the [use-case gallery](docs/en/users_guide/usecases.md); set-ups
that chain several processes are in
[examples: Examples of chained processes](examples/README.en.md#examples-of-chained-processes).
[With an AI agent](docs/en/ai_guide.md) you can start by describing the
phenomenon in your own words and having a model case built.

## What it deliberately does not do

ENCflow intentionally stays within the depth-averaged, constant-density,
two-dimensional world. The following are out of scope by design and
belong to specialized models
([comparison](docs/en/comparison.md)).

- **Wave hindcasting and phase-resolving short waves** — neither the
  growth of waves by wind nor computation that follows the water
  surface wave by wave. The coastal waves above are a phase-averaged
  estimate with one representative period, taking the offshore waves as
  given.
- **Pyroclastic surges, eruption plumes, and atmospheric ash
  transport** — compressible, three-dimensional atmospheric phenomena
  outside the shallow-water approximation. If ash-fall deposits are
  given to the terrain and soil layer in preprocessing, the
  rainfall-triggered secondary lahars can be analyzed.
- **Water temperature** — no energy balance is solved, so water
  temperature is not predicted.
- **The dynamics of density currents and stratification** — the
  momentum equations keep a constant density, and vertical structure is
  not resolved. Apart from a sharp-interface approximation of fresh and
  salt water layers, mixing and entrainment, internal waves, and
  reservoir thermal stratification cannot be reproduced.
- **Individual sewer pipes and operational control** — tracking
  individual pipes, and network analyses involving control structures
  driven by operating rules, belong to 1-D pipe-network models. Urban
  sewers are treated as an areal continuum, so which manhole erupts
  cannot be identified, and systems dominated by a single trunk main
  are not a good fit.
- **Deep groundwater** — the groundwater is a shallow two-layer system
  for runoff analysis. Regional confined aquifers and borehole-scale
  hydraulics are not represented.

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
  professional accountability.
- **Progressive refinement by design** — start from minimal "it just
  runs" parameters and refine step by step as data becomes available.
  Every feature is built with this philosophy.
- **A gateway to the field next door** — estimate with a simple model
  whether a process matters, and move on to a specialist model of that
  field only once you know it does. ENCflow is also a common ground
  for that first step.
- **Simple text input and output** — matrix text, namelists, and CSV,
  plus GeoTIFF for practical work. Pre- and post-process with GIS,
  Python, Excel, whatever you prefer.
- **High affinity with script automation** — because the parameter
  files are plain text, you can generate cases mechanically with sed or
  Python, run them in batch, and diff or aggregate the text outputs,
  all from shell scripts alone. This suits sensitivity analysis,
  calibration, and bulk scenario runs.
- **Automation with AI agents** — the same property extends directly
  to advanced automation by AI, letting AI agents drive case
  generation, execution, verification, and analysis directly. Much of
  the development and verification of ENCflow itself is carried out in
  collaboration with AI agents, and this project is the demonstration.
- **Full source code available** — inspect it, verify it. The
  computational code is written entirely from scratch and contains no
  third-party code; zero dependencies also means a clean, unambiguous
  copyright provenance. Licensed under Apache-2.0, commercial use
  included.
- **Accountable through sources and verification** —
  the sources of each model, governing equation, and parameter are
  cited wherever possible, and simplifications of our own that rest on
  no literature are labelled as such. Behaviour with an analytical
  solution or a conservation law is checked by self-judging
  verification scripts, separately from the regression against
  reference results. Keeping the state in which a third party can trace
  "why this result" is a basic policy alongside full source disclosure
  ([docs/developer.md](docs/developer.md) §0; English
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
  leaves out, such as deep three-dimensional groundwater or the growth
  of waves by wind,
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
