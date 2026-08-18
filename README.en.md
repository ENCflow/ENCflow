# ENCflow

**Solving surface-water phenomena seamlessly on a single grid** —
from river flooding, storm surge, and tsunami run-up to rainfall–runoff,
groundwater, sediment, water quality, snow, glaciers, and landscape
evolution, all in one Fortran program.

[日本語 README](README.md) /
[Installation](docs/en/install.md) /
[Tutorial](docs/en/tutorial.md) /
[User's Guide](docs/en/users_guide.md) /
[Comparison with other models](docs/en/comparison.md)

*The Japanese documentation is the authoritative version; this English
README is a derived translation (based on commit 2a9d10d). Guides and
tutorials are currently available in Japanese only.*

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
inundation…) are solved within the same time evolution. Feel free to
read only the lines you care about.

- **River flooding and inundation**: dynamic-wave shallow water
  equations on the ENC grid. Subgrid channels (cross-section shape and
  width), levee breach, and a family of structures up to pumps, sluice
  gates, culverts, diversions, and dam operation.
- **Storm surge and tsunami run-up**: coastal inundation driven by
  tide/sea-level time series on sea cells. The dynamic wave with
  wetting-and-drying tracks the run-up front. Storm surge + river flood
  + heavy rainfall — **compound flooding in a single model**.
- **Rainfall–runoff and catchment hydrology**: rainfall (uniform or
  distributed), canopy interception, evapotranspiration
  (Hamon/Thornthwaite with temperature lapse rate), Green–Ampt
  infiltration, and two-layer groundwater (soil-layer Boussinesq plus a
  weathered-bedrock layer) providing baseflow and recession.
- **Seawater intrusion and salt wedges**: with a fresh/salt two-layer
  (sharp interface) approximation, seawater intrusion into and retreat
  from aquifers (Ghyben-Herzberg), freshwater lenses, and where the
  seawater that ran up in a storm surge or tsunami ends up - on the
  same grid as the surface and ground water.
- **Urban pluvial flooding (sewer drainage and surcharge)**: the sewer
  network is represented as an equivalent continuum (an artificial
  confined layer) with per-cell capacity and 8-direction conveyances,
  fully coupled with the surface inundation in a single time evolution
  - from inlet uptake through pipe-full pressurized flow (surcharge) to
  manhole eruption. The same machinery applies to fractured bedrock,
  karst, and farmland tile drains.
- **Sediment and slope hazards**: riverbed evolution by bedload and
  suspended load, hillslope erosion, slope failure (stability
  analysis), and debris flow. Terrain and soil depth evolve during the
  computation and feed back into the flow.
- **Volcanic hazards (density flows)**: sector collapse (debris
  avalanches), pyroclastic flows, and lahars, with their deposition
  and natural dam formation, as equivalent-fluid analyses (Voellmy and
  constant-retarding-stress laws — the same modeling level as Titan2D /
  VolcFlow). The chain from eruption supply through runout,
  deposition, natural damming, dam-break flooding, and
  rainfall-triggered secondary lahars can be followed **in a single
  run**.
- **Water quality and mass transport**: load runoff from point sources,
  areal sources, land-use-specific unit loads, and wet deposition;
  advective transport, decay and settling, buildup–washoff (nonlinear
  L–Q), and entrainment into infiltration. Also suited to radionuclide
  runoff analysis.
- **Snow accumulation and melt**: degree-day method. With the
  temperature lapse rate, the snow line emerges automatically.
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

## What it deliberately does not do

ENCflow intentionally stays within the two-dimensional
(depth-averaged, constant-density, hydrostatic) world. The following
are out of scope by design and belong to specialized models
([comparison](docs/en/comparison.md)):

- **Wind waves** — short-period waves (wind waves, swell, breaking).
  Storm surge and tsunami are long waves and can be solved; wave
  computation is the realm of wave models such as SWAN.
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
  realm of SWMM and similar network models (standalone structures are
  covered by the internal hydraulic structures; the areal drainage
  capacity, pressurized flow, and eruption of dense street-level
  networks are covered by the conduit continuum layer. Being a
  continuum approximation, it reproduces the spatial pattern of
  surcharge but cannot identify *which* manhole erupts. Systems
  dominated by a single trunk main also belong to network models).
- **Deep groundwater** — ENCflow's groundwater is a shallow two-layer
  system (plus the conduit continuum layer) for runoff analysis. The
  "confined" state of the conduit layer is an artificial confinement
  representing pipe-full pressurized flow; natural regional confined
  aquifers and well-scale groundwater resource analysis belong to 3-D
  groundwater models.

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
- **Simple text input and output** — matrix text, namelists, and CSV
  (plus GeoTIFF for practical work). Pre- and post-process with GIS,
  Python, Excel — whatever you prefer.
- **Full source code available** — inspect it, verify it.

## Requirements

| | Required | Notes |
|---|---|---|
| Fortran compiler | Yes | Tested with gfortran / Intel ifx / NVIDIA / AMD / NEC. OpenMP enabled by default |
| MPI | Optional | Only for hybrid (OpenMP×MPI) runs across nodes (OpenMPI, MPICH, etc.) |
| Other libraries | **None** | — |

Linux, macOS, and WSL are the assumed platforms. See the
[installation guide](docs/en/install.md).

## Learning to use it

1. [Installation](docs/en/install.md) — a single `make install`
2. [Tutorial](docs/en/tutorial.md) — from the minimal example to real-terrain catchments
3. [User's Guide](docs/en/users_guide.md) — reference for every setting
4. [examples/](examples/) — sample configuration files
5. [test/](test/) — verified examples (doubling as regression tests)

Developers and the curious should head to
[docs/architecture.md](docs/architecture.md) (in Japanese) (the
one-page map of the architecture — read this first),
[docs/developer.md](docs/developer.md) (in Japanese) (the authoritative source for
design philosophy and conventions) and
[docs/comparison.md](docs/en/comparison.md) (comparison with other
models). Developer documentation is currently in Japanese.

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

The license is currently under consideration. Until it is formally
determined, all rights are reserved as a matter of copyright law.
Please contact us if you wish to use ENCflow.

## Development

- Hydraulic Engineering Laboratory, Department of Civil and
  Environmental Engineering, National Defense Academy of Japan
- Hydro-Environmental System Laboratory, Department of Civil
  Engineering, Tohoku University

Bug reports and feature requests are welcome at
[Issues](https://github.com/ENCflow/ENCflow/issues).
For citation in research, see [CITATION.cff](CITATION.cff).
