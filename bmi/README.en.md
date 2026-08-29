# bmi/ — CSDMS Basic Model Interface (BMI 2.0) adapter

[日本語 README](README.md)

This is the **standard interface for operating ENCflow from Python or
from other models**. The whole of ENCflow becomes a single BMI
component: through the common calls initialize / update / get_value /
set_value you can pause the run at any point, pull out the model state,
and feed forcings in from outside. It passes the official CSDMS
conformance test (bmi-tester).

BMI is an optional feature. The regular builds (encflow / encflow_mpi)
do not depend on this directory and keep working with no external
libraries, as always. Using BMI adds only numpy on the Python side
(the BMI specification file is bundled here; no CMake or other tooling
is needed).

## Quick start (from Python)

```sh
cd bmi && make        # builds libencflow_bmi.so (and ../src on first run)
```

```python
import sys; sys.path.insert(0, "path/to/ENCflow/bmi/python")
from encflow import ENCflow, VAR_DEPTH

with ENCflow("param.txt") as model:          # any normal case works as-is
    while model.time < model.end_time:
        model.update_until(model.time + 600.0)   # advance 10 min at a time
        h = model.get2d(VAR_DEPTH)               # water depth, (ny, nx) numpy array
        print(model.time, h.max())
```

Parameter files, input data, and result output are exactly the same as
in a standalone run (BMI only adds a control handle — the dt_file
outputs and Log.txt are still written as usual).

A sample that renders the evolving depth map and a hydrograph live
while the model runs:

```sh
cd test/chichibu
python3 ../../bmi/python/live_view.py param.txt --probe 479 36
python3 ../../bmi/python/live_view.py param.txt --save frames   # PNG frames (headless)
```

The display interval is `--interval` in seconds; if omitted, dt_file is
read from the parameter file so the display is synchronized with the
file output.

## Exposed variables (get / set)

| CSDMS Standard Name | Quantity | Units | set (external supply) |
| --- | --- | --- | --- |
| `surface_water__depth` | water depth | m | Allowed (**replacement**, not addition; velocities are left unchanged) |
| `land_surface__elevation` | elevation | m | Allowed **only when no terrain-evolution feature (geomorph etc.) is enabled** in the case. Water depth is preserved and the water level follows. Sea cells are not touched |
| `atmosphere_water__precipitation_leq-volume_flux` | precipitation rate | m/s | Allowed **only when the case sets no precipitation in its parameters**. Persists as a forcing until the next set |
| `surface_water__elevation` | water level (= elevation + depth) | m | No (get only) |
| `surface_water_flow__speed` | flow speed (magnitude) | m/s | No (get only) |
| `surface_water_flow__unit_width_volume_flow_rate` | unit-width discharge (magnitude) | m²/s | No (get only) |
| `surface_water__x_component_of_velocity` | x (eastward) velocity component | m/s | No (get only) |
| `surface_water__y_component_of_velocity` | y (northward) velocity component | m/s | No (get only) |

All eight variables can be read with get (the velocity components are
cell-centered derived quantities composed from the internal edge-based
fields, in the conventional orientation x = east, y = north). The first
three can also be set; a set value is applied at the start of the next
update. The "only when" conditions come from one
principle — **each quantity has a single source** (file forcing and
external supply are never combined) — and a set that violates them
returns an error (BMI_FAILURE). In Python:
`model.set(name, array)` (flattened standard form below, or a 2-D
(ny, nx) array).

**Choosing the exchange interval**: get/set copy whole fields, so
exchange at the **time scale of the quantity being exchanged** (minutes
for rainfall), not at every model time step. Exchanging too finely is
merely wasteful; exchanging too coarsely becomes a coupling error.

## Array and grid conventions

- Arrays are flattened 1-D as the BMI specification requires, with
  **element 0 at the south-west corner and rows running south to
  north** (consistent with the grid origin at the lower-left corner and
  positive spacing). They map one-to-one onto Landlab RasterModelGrid
  node arrays with no transformation.
- Python's `get2d()` returns (ny, nx) with row 0 in the south (use
  `origin='lower'` in matplotlib for a map-oriented display).
- The grid is grid 0 = uniform_rectilinear, shape in [ny, nx] order.
  For cases with georeferencing (hdr), real coordinates appear in the
  origin.
- References (get_value_ptr) and the unstructured-grid queries are not
  supported (they return BMI_FAILURE / NotImplementedError, as the BMI
  specification permits).

## Using with MPI

```sh
cd bmi && make clean && make MODE=mpi      # → test driver test_encflow_bmi_mpi
mpirun -np 4 ./test_encflow_bmi_mpi param.txt
```

- update / update_until / get / set are **called by all ranks
  together**. The global array returned by get, and the array given to
  set, are **valid on rank 0 only** (arrays on other ranks are not
  referenced).
- If MPI has already been initialized by the caller (mpi4py etc.),
  ENCflow neither takes it over nor finalizes it.
- The shared library for Python is currently serial only; with MPI,
  BMI is used from Fortran (the driver above is an example).

## Verification tools

| Tool | Purpose |
| --- | --- |
| `test_encflow_bmi [param] [set]` | Test driver that runs a case to completion through BMI (results match a standalone run; with `set`, also checks that a same-value set is harmless) |
| `python/test_set_value.py` | Equivalence tests for set_value (e.g. file forcing and external supply give identical results; run in test/wave) |
| `python/check_bmi.sh` | Runs the official CSDMS conformance test, bmi-tester |

To reproduce the conformance check:

```sh
pip install bmi-tester bmipy 'pytest<8' 'gimli.units==0.3.*'
cd test/wave
../../bmi/python/check_bmi.sh param.txt
```

## Files

| File | Role |
| --- | --- |
| `vendor/bmi.f90` | The BMI 2.0 specification (bundled from CSDMS bmi-fortran; MIT — see `vendor/LICENSE` and NOTICE) |
| `bmi_encflow.f90` | The adapter itself (use this module to call BMI from Fortran) |
| `bmi_encflow_c.f90` | C-compatible symbol layer (the shared-library entry) |
| `python/encflow.py` | Python wrapper: the `ENCflow` class (use this for everyday work) |
| `python/encflow_bmi.py` | bmipy-conformant class `EncflowBmi` (for bmi-tester and pymt-style tools) |
| `python/live_view.py` | Live visualization sample |

## Limitations and notes

- One model per process (two ENCflow instances cannot coexist;
  re-initializing after finalize works in serial).
- Runs through the shared library (.so) may not match a standalone run
  down to the last bit, because the compilation conditions differ (the
  physical outputs agree to the printed precision). For verification
  that needs strict bit reproducibility, use the static
  `test_encflow_bmi` driver.

## For developers

The design history and roadmap are in
[docs/bmi_plan.md](../docs/bmi_plan.md) (in Japanese), and the
authoritative records of decisions and verification are in
[docs/developer.md](../docs/developer.md) Secs. 53–59 (in Japanese).
