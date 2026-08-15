# Measurement (&list_record)

> English mirror of docs/users_guide/record.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Sets up **probes** (point time series) and **flux transects** (time
series of discharge crossing a line) for comparison with gauging
stations and for obtaining discharge hydrographs. Enable it with
`fn_record`; the output interval is controlled by `dt_recrd` in
`&list_sysparam` (and the time window st_recrd/et_recrd;
[the time chapter](time.md)).

```
&list_record
  ! probes (by cell number)
  pbxy(:,1) = 150, 150           ! probe 1: (ix, iy)
  pbxy(:,2) = 200, 120           ! probe 2
  ! flux transect (by cell number): from right bank to left bank
  flxy(:,1) = 100, 50, 100, 60   ! transect 1: (right-bank ix, iy, left-bank ix, iy)
/
```

**Cell numbers are 1-based** (the westernmost column and the
northernmost row are 1). Rasters in GIS such as QGIS count from 0, so
add +1 to both row and column numbers picked in a GIS
([the coordinate systems chapter](coordinates.md)).

## Probes (point time series)

| Parameter | Default | Meaning |
|---|---|---|
| pbxytype | 0 | How coordinates are specified. 0: cell numbers (ix, iy) (**1-based**), 1: real coordinates (x positive east, y positive north; absolute coordinates if georeferencing exists, otherwise local coordinates with the origin at the southwest corner - [the coordinate systems chapter](coordinates.md)) |
| pbxy | - | Probe positions `(x, y, number)`. Multiple probes allowed |

Output is written one file per point, e.g.
`result/probes/probe0001.csv`. The columns are time (hour/min), ground
elevation z, depth h, velocities u, v, |V|, discharge q, subsurface
storage hg, suspended sediment hs, and soil depth sd (plus
concentration C and surface load cq when water quality is enabled).
Columns of unused features stay 0.

## Flux transects (time series of crossing discharge)

| Parameter | Default | Meaning |
|---|---|---|
| flxytype | 0 | 0: cell-number specification (a DDA staircase surface connecting the two end-cell centers), 1: real-coordinate specification (coordinates interpreted as for probes; integrated over the in-cell segment portions of every cell the segment grazes) |
| flxyfile | 0 | 0: specify directly with flxy, 1: read from the transect file fn_flxy |
| flxy | - | Start and end points of a transect `(right-bank x, right-bank y, left-bank x, left-bank y, number)` |
| fn_flxy | - | Transect file (one transect per line, comma- or space-separated: "right-bank x, right-bank y, left-bank x, left-bank y") |

- The sign of the discharge is **positive for flow passing to the
  right when going from the start point to the end point** (common to
  cell-number and real-coordinate specification). In a river, taking
  the right bank as the start and the left bank as the end makes the
  downstream direction positive.
- A diagonal transect specified by cell numbers is converted to a DDA
  staircase surface (a stepped surface following cell interfaces), so
  transects can be drawn at any angle. **The two ends must not be the
  same cell** (with a single cell the orientation of the measured
  surface is undetermined, so it is an error; use real-coordinate
  specification to measure within one cell).
- **With real-coordinate specification (flxytype=1), even a short
  transect that does not span multiple cells can be measured** - the
  orientation and length of the transect are determined from the real
  coordinates, and the discharge corresponding to the in-cell segment
  portion (component normal to the segment x segment length) is
  integrated. If the transect is extended across multiple cells the
  definition continues seamlessly, and in a uniform flow it is exact
  for any position, inclination, and length.
- Output is one file per transect, e.g. `result/fluxes/flux0001.csv`.
- Discharge transferred through structures such as culverts does not
  register on transects ([the structures chapter](structure.md)).

## Summary output

With measurement enabled, aggregate statistics (maxima etc.) of all
probes and all transects are written together to `result/summary.csv`.

## Worked examples of the format

Annotated list of all parameters:
[examples/List_samples/list_record.txt](../../../examples/List_samples/en/list_record.txt).

## Post-hoc measurement from distributed output (utils/rerecord)

For the case "I want to add measurement points after the run has
finished", the utility `utils/rerecord` reconstructs time series from
the already-written distribution files (output of the flow direction
`f_out_qd` is required; [the input/output chapter](io.md)). This
avoids redoing a long computation.
