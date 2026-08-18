> English mirror of docs/users_guide.md (based on commit 6c5acfc). The Japanese file is the master copy.

# ENCflow User's Guide

This is the reference for configuring and running ENCflow. If you are
new to ENCflow, we recommend running it once through the
[tutorial](tutorial.md) before coming back here. This page (Part I)
explains the overall structure of ENCflow and the conventions of its
input; individual topics are split into per-chapter pages.

## Table of contents

**Part I: The big picture** (this page)
- [The skeleton of ENCflow](#the-skeleton-of-encflow)
- [Enabling features: the fn_\* principle](#enabling-features-the-fn_-principle)
- [How to read a parameter file](#how-to-read-a-parameter-file)
- [Running a computation](#running-a-computation)
- [User routines](#user-routines)
- [Finding features by task](#finding-features-by-task)

**Part II: Cross-cutting facilities**
- [Time management](users_guide/time.md) -- time axis, time step, output interval, calendar
- [Coordinate systems](users_guide/coordinates.md) -- EPSG, ESRI hdr, geographic (lat-lon) grids
- [Input and output formats](users_guide/io.md) -- text / bil / GeoTIFF, output file organization
- [Suspend and restart](users_guide/restart.md) -- state files, time continuation, use as initial conditions
- [Parallel execution](users_guide/parallel.md) -- OpenMP, MPI, reproducibility of results

**Part III: Feature reference**
- [Shallow water computation](users_guide/swflow.md) (&list_enc, numerical parameters) -- scheme selection, adaptive Runge-Kutta, numerical constants
- [Geographic information](users_guide/geoinfo.md) (&list_geoinfo) -- grid, terrain, roughness, masks, seawalls
- [Initial conditions](users_guide/initial.md) (&list_initial) -- depth, water level, depression filling
- [Boundary conditions](users_guide/boundary.md) (&list_bound_edge/source/stage/inflow) -- edge boundaries, sources, prescribed stages, reach inflow
- [Tide and sea surface](users_guide/tide.md) (&list_tide) -- storm surge, rising-tide inundation, drainage
- [Internal hydraulic structures](users_guide/structure.md) (&list_struct_pump/culvert/diversion/dam) -- pumps, culverts, diversions, dams
- [Channels](users_guide/channel.md) (&list_channel) -- levees, channel width, cross-section shape, breach
- [Rainfall and weather](users_guide/forcing.md) (&list_precip / intercept / meteo / evap / snow) -- precipitation, interception, air temperature, evapotranspiration, snow accumulation and snowmelt
- [Groundwater](users_guide/gwflow.md) (&list_gwflow plus model-specific settings) -- infiltration, lateral flow, weathered bedrock layer, conduit continuum layer (sewer networks, fractured bedrock)
- [Fresh and salt water layers](users_guide/salt.md) (&list_salt) -- salt wedges, seawater intrusion, freshwater lenses (sharp-interface approximation)
- [Sediment and landform change](users_guide/geomorph.md) (&list_geomorph) -- bedload, suspended sediment, hillslope erosion, debris flow, long-term landscape evolution
- [Glaciers](users_guide/glacier.md) (&list_glacier) -- accumulation, melt, ice flow, glacial erosion, avalanche redistribution
- [Water quality](users_guide/wq.md) (&list_wq) -- load input, transport, decay, washoff
- [Measurement](users_guide/record.md) (&list_record) -- probes, flux transects
- [Use cases](users_guide/usecases.md) -- lookup from phenomenon names to feature combinations (unsupported phenomena are listed too)

**Appendix**
- [Full parameter index](users_guide/params_index.md) -- reverse lookup from all 421 parameter names to their chapters

---

## The skeleton of ENCflow

ENCflow is structured as features (process modules) stacked on top of
a single time-evolution loop. At the core is the computation of
surface water by the shallow water equations (dynamic wave) on the
ENC grid; processes such as rainfall, groundwater, sediment, and water
quality are each computed as independent modules on the same grid and
within the same time loop.

All features are enabled in a common style. Writing a configuration
file name `fn_XXX` in the system parameters `&list_sysparam` wakes
that feature up; if you do not write it, **the feature consumes no
memory and no computation time at all**.

| Feature | Enabled by | namelist group |
|---|---|---|
| Geographic information (grid, terrain, roughness) | `fn_geoinfo` (required) | &list_geoinfo |
| Initial conditions | `fn_initial` | &list_initial |
| Shallow water computation tuning (ENC) | `fn_enc` | &list_enc |
| Boundary conditions | `fn_boundary` | &list_bound_edge / source / stage / inflow |
| Tide and sea surface | `fn_tide` | &list_tide |
| Internal hydraulic structures | `fn_structure` | &list_struct_pump / culvert / diversion / dam |
| Ponds | `fn_reservoir` | (used together with geographic information) |
| Channels | `fn_channel` | &list_channel (+ breach) |
| Precipitation | `fn_precip` | &list_precip |
| Rainfall interception | `fn_intercept` | &list_intercept (+ model-specific) |
| Weather forcing fields (air temperature etc.) | `fn_meteo` | &list_meteo |
| Evapotranspiration | `fn_evap` | &list_evap |
| Snow accumulation and snowmelt | `fn_snow` | &list_snow |
| Glaciers | `fn_glacier` | &list_glacier |
| Groundwater | `fn_gwflow` | &list_gwflow (+ model-specific) |
| Fresh and salt water layers | `fn_salt` | &list_salt |
| Sediment and landform change | `fn_geomorph` | &list_geomorph |
| Water quality (load runoff) | `fn_wq` | &list_wq |
| Measurement (probes, transects) | `fn_record` | &list_record |

"Precipitation" and "weather forcing fields" are separate because
their roles differ. Precipitation is the mass input to the water
balance (the main input of the model), while the weather forcing
fields, such as air temperature, are background fields for the
computation. In a run that uses only rain you never need to think
about `fn_meteo`. How to combine the weather inputs into a single
file when you use both is shown in the
[rainfall and weather chapter](users_guide/forcing.md).

## Enabling features: the fn_\* principle

The value of `fn_XXX` has three possible meanings.

| Value | Meaning |
|---|---|
| `""` (empty; default) | The feature is not used. Its settings are never read and no resources are allocated |
| `"-"` | **Read from the same file**. For keeping all parameters in one file |
| `"filename"` | Read from the named separate file. For keeping data and settings apart |

It is fine to give the same file name to several `fn_*` entries.
Namelist reading looks groups up by name, so multiple groups can live
together in one file (e.g. a forcing file that collects the weather
inputs). Conversely, groups left unused in a file are simply ignored,
so you can also keep variant configurations around by renaming them,
e.g. `&list_precip_planA`
([examples/List_samples](../../examples/List_samples/en/) is written
in this style). An annotated list of all parameters of &list_sysparam
is in [list_sysparam.txt](../../examples/List_samples/en/list_sysparam.txt)
(which doubles as a minimal example that runs as-is).

## How to read a parameter file

A parameter file is a text file in Fortran **namelist format**.

```
&list_sysparam            ! start of a group
  dt = 0.01               ! "name = value" entries; ! starts a comment
  tt = 8.0
  fn_geoinfo = "-"        ! strings are quoted
/                         ! end of the group
```

- Entries may appear in any order; parameters you do not write take
  their default values.
- Arrays can be written line by line with subscripts, as in
  `prval(:,1) = 0, 15`.
- **A parameter name that does not exist (a misspelling) stops the run
  with an error**. When a parameter has been renamed in a version
  update, the same mechanism detects it and the error message points
  you to the new name.
- Error messages and runtime output are in English (we prioritize the
  ability of users worldwide to search and ask about them; Japanese
  explanations are the documentation's job).

## Running a computation

```bash
./encflow param.txt
```

You run ENCflow by giving it a single parameter file. To set up the
executable, just place a link to `bin/encflow` (or a copy of it) in
the directory where you want to compute -- it works anywhere
([installation guide Sec. 2.4](install.md#24-run-your-computations-anywhere)).
The screen shows the configuration loading progress, followed by
monitoring columns such as time, conserved quantity S, Runge-Kutta
application rate, and Courant number (how to read the columns:
[tutorial Step 1](../../tutorials/wave/en/README.md#running);
selecting columns: f_disp_\* -- see the
[input and output chapter](users_guide/io.md)).

Results are written to the output directory (default `result/`) as
distribution files (`H0001.txt` etc.), the computation log `Log.txt`,
and a copy of the parameters used. The file naming scheme and formats
are collected in the [input and output chapter](users_guide/io.md).

When a computation stops midway, ENCflow identifies the cause and
**stops with an explicit error** (it never silently continues with
invalid values). The message includes the offending parameter name
and file name, so check those first.

## User routines

For cases where you want to specify terrain or initial conditions by
formulas or code (idealized experiments, benchmarks), there is a
mechanism of user routines invoked by name.

```
&list_initial
  f_user_routine = "wave_hump"   ! identifier of a registered routine
/
```

The registered identifiers are listed at the top of
`src/user_geoinfo.f90` (terrain) and `src/user_initial.f90` (initial
conditions). To write your own, duplicate the `template` at the end
of each file, register an identifier, and rebuild. User routines are
not used in ordinary computations with real data.

## Finding features by task

For a more detailed list (phenomenon -> feature combination -> key
settings, including unsupported phenomena), see
**[Use cases](users_guide/usecases.md)**.

| What you want to do | Features to use (chapters) |
|---|---|
| Flood inundation | [Geographic information](users_guide/geoinfo.md) + [boundary conditions](users_guide/boundary.md) (+ channels, structures) |
| Dam / farm-pond breach floods | [Channels](users_guide/channel.md) (levees + breach) + [Use cases](users_guide/usecases.md) |
| Open levees, detention basins, secondary levees | [Channels](users_guide/channel.md) (levees, openings) + [Structures](users_guide/structure.md) |
| Polder / lowland drainage by pumping | [Structures](users_guide/structure.md) (pumps) + [Tide and sea surface](users_guide/tide.md) |
| Storm surge / tsunami run-up | [Tide and sea surface](users_guide/tide.md) + [boundary conditions](users_guide/boundary.md) |
| Rainfall runoff (catchment hydrology) | [Rainfall and weather](users_guide/forcing.md) (+ groundwater) |
| Urban pluvial flooding (sewer drainage and surcharge) | [Groundwater](users_guide/gwflow.md) (conduit continuum layer) + [Rainfall and weather](users_guide/forcing.md) |
| Seawater intrusion, salt wedges, freshwater lenses | [Fresh and salt water layers](users_guide/salt.md) + [Tide and sea level](users_guide/tide.md) |
| Sediment transport / debris flow | [Sediment and landform change](users_guide/geomorph.md) |
| Rainfall-induced slope failure and debris flow | [Sediment and landform change](users_guide/geomorph.md) + [Groundwater](users_guide/gwflow.md) (infiltration -> pore pressure) |
| Reservoir sedimentation and flushing | [Sediment and landform change](users_guide/geomorph.md) + [Structures](users_guide/structure.md) |
| Pollutant loads / mass transport | [Water quality](users_guide/wq.md) |
| Runs including snowmelt | [Rainfall and weather](users_guide/forcing.md) (snow accumulation / snowmelt + temperature lapse rate) |
| Glacier meltwater / cirque formation | [Glaciers](users_guide/glacier.md) (+ rainfall and weather; suspend and restart for long runs) |
| Glacial lake outburst floods (GLOF) | [Glaciers](users_guide/glacier.md) + [Channels](users_guide/channel.md) (breach) |
| Comparison with gauging stations / discharge transects | [Measurement](users_guide/record.md) |
| Splitting long runs / scenario branching | [Suspend and restart](users_guide/restart.md) |
| GIS data (GeoTIFF etc.) input and output | [Coordinate systems](users_guide/coordinates.md) + [input and output](users_guide/io.md) |
| Large-scale runs / cluster execution | [Parallel execution](users_guide/parallel.md) |
