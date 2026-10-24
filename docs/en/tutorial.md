> English mirror of docs/tutorial.md. The Japanese file is the master copy.

# ENCflow Tutorials

This is a guide for learning how to use ENCflow step by step, with
runnable examples. Each tutorial is self-contained in a directory
under [tutorials/](../../tutorials/en/README.md), and you work through it by
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
collection in [examples/](../../examples/README.en.md) and the verified examples
in [test/](../../test/README.en.md) are useful references.

## Learning path

Not everyone needs to understand every field. Only the following three
are required; they teach the principles (enabling features with
fn_\*, writing the parameter file, running and reading the output).

1. [tutorials/wave](../../tutorials/wave/en/README.md) Steps 1–3 — first run, the parameter file, time step, boundary conditions
2. [tutorials/chichibu](../../tutorials/chichibu/en/README.md) — real terrain data, rainfall, recording, water balance
3. [User's guide Part I](users_guide.md) — skeleton, the fn_\* principle, reading a parameter file

If the Courant number (the `Cn_max` column) and the choice of the time step
`dt` in Step 1 of wave puzzle you, read
[Courant number and how to choose the time step](users_guide/courant.md)
(a primer for newcomers to the numerical computation of flow).

To assemble your own case, the "just try it (minimal input)" sections
of [Geographic information](users_guide/geoinfo.md),
[Initial conditions](users_guide/initial.md),
[Boundary conditions](users_guide/boundary.md) and
[Rainfall and meteorology](users_guide/forcing.md) are where to start.

Beyond that, read **only the chapters of the fields you are interested
in**. The chapter pages give priority to "getting a run going casually":
read them in the order "overview → just try it → recommended values by
pattern → the sections you need". If you want more, go on to the
**explanation pages** that hang under each chapter (theory, equations,
the basis of the defaults, detailed settings).

| Field (chapter page) | Explanation pages |
|---|---|
| [Time management](users_guide/time.md) | [Courant number and how to choose the time step](users_guide/courant.md) (primer), [Time-step design policy](users_guide/timestep_policy.md) |
| [Shallow water computation](users_guide/swflow.md) | [ENC grid and time integration](users_guide/encgrid.md), [Advection](users_guide/advection.md), [Diffusion](users_guide/diffusion.md), [Non-hydrostatic correction](users_guide/nonhydrostatic.md) |
| [Structures](users_guide/structure.md), [Boundary conditions](users_guide/boundary.md), [Channels](users_guide/channel.md) | [Hydraulic laws of structures and boundaries](users_guide/hydraulics.md) |
| [Groundwater](users_guide/gwflow.md) | [Groundwater models](users_guide/gwflow_models.md) |
| [Sediment and landform change](users_guide/geomorph.md) | [Sediment transport, hillslope and long-term processes](users_guide/sediment.md), [Debris flow, slope failure and moving bed layer](users_guide/massflow.md) |
| [Water quality](users_guide/wq.md) | [Water-quality models](users_guide/wq_models.md) |
| [Rainfall and meteorology](users_guide/forcing.md) | [Rainfall and meteorology models](users_guide/forcing_models.md) |
| [Channels](users_guide/channel.md) | [Channels explained](users_guide/channel_models.md) |
| [Nesting](users_guide/nest.md) | [Nesting explained](users_guide/nest_models.md) |
| [Prescribed bed motion](users_guide/bedmotion.md) | [Prescribed bed motion explained](users_guide/bedmotion_models.md) |
| [Driftwood](users_guide/driftwood.md), [Building destruction and debris](users_guide/bldgdebris.md) | [Driftwood models](users_guide/driftwood_models.md), [Building destruction and debris models](users_guide/bldgdebris_models.md) |

Your reason for using ENCflow may be that you want to **chain several
processes in one run** (rainfall → runoff → sediment → channel; tsunami
→ house destruction → debris; eruption → lava field → secondary
flooding, and so on). Use the [use-case gallery](users_guide/usecases.md) to find the
feature combination for a phenomenon and combine the relevant chapters.
Specialised features such as nesting and the non-hydrostatic correction
can wait until you need them.

[test/](../../test/README.en.md) and [examples/](../../examples/README.en.md) are not teaching
material for beginners, so look at them after the chapters, as needed. The
tests show how each feature is verified (against analytical solutions
and conservation laws); the examples show namelist samples and set-ups
that combine several processes.

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
