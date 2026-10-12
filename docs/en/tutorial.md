> English mirror of docs/tutorial.md. The Japanese file is the master copy.

# ENCflow Tutorials

This is a guide for learning how to use ENCflow step by step, with
runnable examples. Each tutorial is self-contained in a directory
under [tutorials/](../../tutorials/), and you work through it by
typing the commands yourself while reading the README inside. For
prerequisites, see the [installation guide](install.md) (all the
computation needs is a single Fortran compiler; visualization of the
results uses gnuplot, and the 3D visualization in chichibu uses
ParaView -- see section 2 of the same guide for installing them).

## Tutorial list

| # | Case | What you learn |
|---|---|---|
| 1 | [wave -- waves spreading over still water](../../tutorials/wave/en/README.md) | First run and reading the output / structure of the parameter file / time step and accuracy, the adaptive Runge-Kutta method / boundary conditions / the nature of walls on the ENC grid |
| 2 | [chichibu -- rain falling on a real-terrain catchment](../../tutorials/chichibu/en/README.md) | Real terrain data (DEM, masks) and depression removal / GeoTIFF input and output / channel mask and roughness / recording (probes, transects) / tuning numerical settings / rainfall interception, subsurface infiltration and the water balance / boundary conditions at the catchment outlet / understanding discharge oscillations originating in real terrain data / 3D visualization (animation) with ParaView |

Further tutorials (channel refinement, long runs and restart, etc.)
will be added over time. Beyond these, the configuration sample
collection in [examples/](../../examples/) and the verified examples
in [test/](../../test/) are useful references.

## Learning path (by level)

A path from simple examples onward; each level assumes the one before
it. The chapter pages of the user's guide are written in the order
"overview → just try it (minimal input) → recommended values by pattern
→ details → tests and examples", so **the first two sections are enough
to get a run going**. The explanation pages ("... explained") collect
the equations and the basis of the defaults for advanced readers and
can be left for later.

| Level | Read or run | What you learn |
|---|---|---|
| Beginner 1 | [tutorials/wave](../../tutorials/wave/en/README.md) Steps 1–3 | first run, structure of the parameter file, time step, boundary conditions |
| Beginner 2 | [User's guide Part I](users_guide.md) (skeleton, the fn_\* principle, reading a parameter file) | how features are enabled, what goes into one file |
| Beginner 3 | [test/wave](../../test/wave/), [test/dambreak](../../test/dambreak/), [examples/benchmark](../../examples/benchmark/) | reading comparisons with analytical solutions (bores, rainfall runoff); using `./Run.sh` and `Check_*.py` |
| Intermediate 1 | [tutorials/chichibu](../../tutorials/chichibu/en/README.md) | real terrain data, channel mask, recording, interception and infiltration, water balance |
| Intermediate 2 | the "just try it" sections of [Geographic information](users_guide/geoinfo.md), [Initial conditions](users_guide/initial.md), [Boundary conditions](users_guide/boundary.md) and [Rainfall and meteorology](users_guide/forcing.md) | the minimal input for assembling your own case |
| Intermediate 3 | [test/tide](../../test/tide/), [test/pump](../../test/pump/), [test/culvert](../../test/culvert/), [examples/sewer_hybrid](../../examples/sewer_hybrid/), [examples/qanat](../../examples/qanat/) | minimal examples of tide, structures, groundwater and conduits (one feature each) |
| Advanced 1 | [ENC grid and time integration](users_guide/encgrid.md) → [Advection](users_guide/advection.md) → [Diffusion](users_guide/diffusion.md) → [Non-hydrostatic correction](users_guide/nonhydrostatic.md) | equations, schemes and the basis of the defaults of the shallow-water computation |
| Advanced 2 | [examples/nest_reflect](../../examples/nest_reflect/), [examples/landslide_tsunami](../../examples/landslide_tsunami/), [examples/tsunami_fault](../../examples/tsunami_fault/), [examples/tsunami_coast](../../examples/tsunami_coast/) | combining nesting, the non-hydrostatic correction, the moving bed layer and prescribed bed motion |
| Advanced 3 | [examples/tsunami_town](../../examples/tsunami_town/), [examples/timberyard](../../examples/timberyard/), [examples/ashfall_lahar](../../examples/ashfall_lahar/), [examples/badland](../../examples/badland/) | chains of several processes (house destruction, driftwood, debris flow, landscape evolution) and how to set up two-case comparisons |
| Development | [developer.md](../developer.md) §0 (policy, in Japanese) → [architecture.md](../architecture.md) | the design philosophy and the contract for adding a new process |

## Roles of the directories

The three easily confused directories are used as follows.

- **tutorials/** -- for learning. Hands-on tutorials you work through
  while reading an explanatory document (README).
- **examples/** -- a collection of sample configuration files.
  Model namelist configurations for each feature
  (`examples/List_samples/`) and examples with real data.
- **test/** -- regression tests for development. They come with
  automatic comparison against reference values and carry no
  explanations aimed at learners.

## What to read next

- [User's guide](users_guide.md) -- the reference for configuration
  and execution (Part I big picture, Part II cross-cutting features,
  Part III feature reference with explanation pages)
- [Comparison with other models](comparison.md) -- where ENCflow
  stands
- [developer.md](../developer.md) (in Japanese) -- design philosophy
  and development conventions (for those joining development)
