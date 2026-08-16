> English mirror of docs/tutorial.md (based on commit 6c5acfc). The Japanese file is the master copy.

# ENCflow Tutorials

This is a guide for learning how to use ENCflow step by step, with
runnable examples. Each tutorial is self-contained in a directory
under [tutorials/](../../tutorials/), and you work through it by
typing the commands yourself while reading the README inside. For
prerequisites, see the [installation guide](install.md) (all the
computation needs is a single Fortran compiler; visualization of the
results uses gnuplot, and the 3D visualization in chichibu uses
ParaView -- see section 2.5 of the same guide for installing them).

## Tutorial list

| # | Case | What you learn |
|---|---|---|
| 1 | [wave -- waves spreading over still water](../../tutorials/wave/en/README.md) | First run and reading the output / structure of the parameter file / time step and accuracy, the adaptive Runge-Kutta method / boundary conditions / the nature of walls on the ENC grid |
| 2 | [chichibu -- rain falling on a real-terrain catchment](../../tutorials/chichibu/en/README.md) | Real terrain data (DEM, masks) and depression removal / GeoTIFF input and output / channel mask and roughness / recording (probes, transects) / tuning numerical settings / rainfall interception, subsurface infiltration and the water balance / boundary conditions at the catchment outlet / understanding discharge oscillations originating in real terrain data / 3D visualization (animation) with ParaView |

Further tutorials (channel refinement, long runs and restart, etc.)
will be added over time. Beyond these, the configuration sample
collection in [examples/](../../examples/) and the verified examples
in [test/](../../test/) are useful references.

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
  and execution (the big-picture and cross-cutting chapters are
  published; the feature reference chapters are being added)
- [Comparison with other models](comparison.md) -- where ENCflow
  stands
- [developer.md](../developer.md) (in Japanese) -- design philosophy
  and development conventions (for those joining development)
