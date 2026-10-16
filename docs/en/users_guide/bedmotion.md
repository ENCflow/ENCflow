# Prescribed bed motion (&list_bedmotion)

> English mirror of docs/users_guide/bedmotion.md. The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Forces the bed elevation z with a prescribed **time history** of ground
displacement. There are three uses. (A) Generate a tsunami from the
seafloor and coastal deformation computed from fault parameters and
follow generation, propagation, run-up and inundation in a single run.
(B) Give coseismic coastal uplift and subsidence (flooding of subsided
lowland, waves spreading from uplifted areas) or a displacement field
obtained from geodetic data or another model. (C) Lower a levee that is
present as elevation in a high-resolution DEM (a **resolved levee**) at a
chosen time, width and depth to represent a **breach**. During the local
displacement update, h is kept and z is moved, so e = z + h moves by the
same amount. The subsequent flow calculation changes depth and velocity
(the same contract as the morphological modules). The design is in
[docs/bedmotion_plan.md](../../bedmotion_plan.md), the implementation
record in developer.md §70, and the preprocessing from fault parameters in
the [fault2disp geometry diagram and setup guide](../../../utils/fault2disp/README.en.md#2-fault-parameter-conventions).
The time interpolation of the displacement, the fault displacement field,
the relation to the non-hydrostatic correction and the behaviour contract
are in [Prescribed bed motion explained](bedmotion_models.md).

## 1. Just try it (minimal input)

An example that only lifts part of the terrain by 0.5 m in 10 seconds.
All it needs is **one snapshot table and two displacement files**; the
displacement files are matrices in the same layout as the bed elevation
z (row 1 is the northern edge).

```
# bm/bmlist.txt (time in s, file names relative to dir_data)
  0.0   bm/d0.txt      ! zero displacement (all cells 0)
 10.0   bm/d1.txt      ! cumulative displacement after 10 s (0.5 on the lifted cells, 0 elsewhere)
```

Write the displacement files by hand or, for example, like this (a
100 × 60 grid, lifting the central 10 × 10 cells by 0.5 m):

```python
import numpy as np
nx, ny = 100, 60
d = np.zeros((ny, nx)); np.savetxt('bm/d0.txt', d, fmt='%.3f')
d[25:35, 45:55] = 0.5;   np.savetxt('bm/d1.txt', d, fmt='%.3f')
```

The model parameters are just `fn_bedmotion` and `&list_bedmotion`
(terrain, initial level and boundaries as usual).

```
&list_sysparam
  fn_bedmotion = '-'        ! read &list_bedmotion from the same file
  f_out_z = 1               ! also output the deformed bed Z0001...
  ...
/
&list_bedmotion
  fn_bmlist = 'bm/bmlist.txt'
/
```

Run `./encflow param.txt`. At the start the number of snapshots and
their time range are printed; at the end the maximum and minimum applied
displacement (+0.5 m and 0 in this example). Check in Z0001... that the
bed rises linearly over 10 seconds and that, where there is water, the
surface rises by the same amount (the depth does not change). After the
last time in the table the last displacement is held. A negative
displacement is subsidence.

## 2. Input conventions (snapshot table and displacement files)

The **table** has one line per snapshot, "time file" (blank lines and
lines starting with `#` or `!` are ignored). Times are relative to the
start t0 and **strictly increasing**; file names are relative to dir_data.
The internal snapshot time is `t0 + table time × bm_tscale`.

```
# time(s)  file
  0.0      bm/disp_0000.txt
 10.0      bm/disp_0010.txt
 60.0      bm/disp_0060.txt
```

Each **displacement file** holds the **cumulative** displacement d [m] at
that time, relative to the terrain at the start of the run (not the
increment since the previous time), in the same format and row order as
the bed elevation z (text matrix / bil / GeoTIFF according to
f_input_mode; row 1 is the northern edge). Positive is uplift, negative
subsidence.

- Before the first time the first value holds; after the last time the
  last value holds. A zero-displacement line at t = 0 is the usual start
  (fault2disp writes one).
- Between snapshots the displacement is interpolated linearly
  (f_bminterp=1, default) or held stepwise (f_bminterp=0, the previous
  snapshot is kept).
- Times are in seconds. A table written in minutes or hours is converted
  with bm_tscale (60, 3600).
- The model keeps two snapshots (previous and next) plus the applied
  displacement, reading the next file as time advances. The number of stored
  raster arrays is independent of table length, but the lists of times,
  file names, and windows grow with the number of snapshots.
- Eligible cells have `x > 0` and `sw = 0`. Land cells, dry cells and
  initially submerged seabed all move with the same displacement field.
  Cells in the sea mask (sw > 0) have their level prescribed and do not
  move.

### Windowed displacement files (when the deformation covers only part of the grid)

When the full grid is large and the deformation covers only part of it,
append four integers `i1 j1 ni nj` to the line. The file is then read as
an ni × nj matrix covering only the **window** of columns i1..i1+ni−1 and
rows j1..j1+nj−1 of the full grid, with zero displacement outside. The
window indices are 1-based from the northwest. Align the window with cell
edges, with `nj` file rows and `ni` columns. The z/e update loops scan the
**bounding rectangle enclosing all snapshot windows**. Gaps between separate
windows are included; this is not a scan of only their exact union. Each
snapshot is zero outside its own window before temporal interpolation.

Windowing reduces input files and read buffers, but the retained displacement
arrays and temporal interpolation still span each MPI band. Total work and
memory do not scale solely with window area. `f_window=1` in fault2disp
writes this format, using `d_min` as the threshold for the discarded region.
For the breach of §5 a window of the few breach cells is enough.

```
# time(s)  file               i1  j1  ni  nj
  0.0      bm/disp_0000.txt   90  40  80  70
 30.0      bm/disp_0010.txt   90  40  80  70
```

![Time history, input patterns and windows of the prescribed bed motion](../../figs/bedmotion_patterns_en.png)

Figure: (a) An example of cumulative displacement at one cell and the
interpolation modes. See §7 for exact step-switch behavior at snapshot times.
(b) A creates displacement from fault parameters (§3), B preprocesses existing
rasters, and C uses a one-row table for the final field (§4); all feed a table to
`fn_bmlist`. C can use the output from A or B. (c) The local update adds
`Δd = d(tₙ₊₁) − d_prev` to the bed. Depth is the same immediately before and
after that update; bed and surface move by the same Δd. The window illustrates
`nx=16, ny=10, i1=5, j1=2, ni=7, nj=5`: 35 cells in columns 5–11 and rows
2–6. This schematic is separate from the input example in the text.

## 3. Application A: tsunami from a fault (utils/fault2disp)

Earthquake tsunamis use this pattern. From the fault position, strike,
dip, rake, length, width, slip, rupture start time and rise time the
utility computes the displacement field with the elastic half-space
solution (Okada's formulas) and writes the table. Several segments (with
rupture-time lags) and the horizontal-displacement contribution (when a bed
elevation is given) are supported ([the explanation](bedmotion_models.md) §2).
The steps to generate the tsunami of a single reverse fault in an
idealised sea (no georeference) are as follows.

**(1) Fault parameters to a displacement time history** (utils/fault2disp)

```
&list_fault2disp
  nx = 200                  ! grid (same as ENCflow's list_geoinfo)
  ny = 150
  dx = 1000.0
  dy = 1000.0
  dir_out = 'bm'            ! writes bm/disp_0000.txt ... and bm/bmlist.txt
  nout = 10
  nseg = 1
  x_top(1) = 120000.0       ! top-edge centre (120 km east, 75 km north of the lower-left corner)
  y_top(1) = 75000.0
  d_top(1) = 5000.0         ! top-edge depth 5 km
  strike(1) = 0.0           ! strike N; the fault dips to the right of the strike (east)
  dip(1) = 15.0
  rake(1) = 90.0            ! reverse fault
  flength(1) = 60000.0
  fwidth(1) = 30000.0
  slip(1) = 5.0
  t_r(1) = 0.0              ! rupture start (s)
  t_rise(1) = 30.0          ! rise time 30 s
/
```

```
cd utils/fault2disp && make          # once (build src first if libencflow.a is missing)
cd <the case's dir_data> && <path>/fault2disp fault2disp.txt
```

**(2) The model parameters** (excerpt; only the settings specific to a
tsunami run are shown)

```
&list_sysparam
  fn_bedmotion = '-'        ! read &list_bedmotion from the same file
  f_out_z = 1               ! also output the deformed bed
  ...
/
&list_initial
  f_htype = 2               ! fixed initial water level (still water e0 = 0; z < 0 is sea)
  e0 = 0.0
/
&list_bound_edge
  f_bc_w = 0                ! landward edge: wall
  f_bc_e = 2                ! seaward edges: long-wave radiation (no reflection)
  f_bc_n = 2
  f_bc_s = 2
/
&list_bedmotion
  fn_bmlist = 'bm/bmlist.txt'   ! the table written by (1) (relative to dir_data)
/
```

**(3) Run** as usual, `./encflow param.txt` (the MPI build likewise).
The complete example is
[examples/tsunami_fault](../../../examples/tsunami_fault/README.md)
(this setup itself). The water body and boundaries are discussed in §6.

Coordinates can be given in three ways, all absorbed on the fault2disp
side, so the model settings do not change (details in fault2disp README §3).

| How the coordinates are held | fault2disp setting |
|---|---|
| Idealised experiment (no georeference) | x_top, y_top as distances (m) from the lower-left corner of the grid (the example above) |
| Georeferenced analysis in a projected system | give the bil+hdr / GeoTIFF bed elevation as fn_z: the grid and origin are taken from the file and x_top, y_top are absolute coordinates of that system. The Japanese plane rectangular order (X northing, Y easting) is f_jpr=1 |
| Longitude/latitude | f_lonlat=1 with lon_top, lat_top and the grid's projection (proj_lon0 etc.; UTM or plane rectangular). The strike is corrected for grid convergence |

## 4. Application B: coastal uplift and subsidence, and displacement fields of your own

Land cells move with the same displacement field, so when the fault
deformation reaches the coast and the land (flooding of subsided lowland,
waves spreading from uplifted areas, their superposition in bays) it is
part of the same run with the settings of §3 unchanged. The example is
[examples/tsunami_coast](../../../examples/tsunami_coast/README.md) (a deep
fault under the coast subsides the shore by 0.6 m, and the disturbance
reaches the coast 10 minutes before the offshore fault's tsunami).

When you already hold **a displacement field of your own** (geodetic
data, slip inversions, other models), write the table yourself following
§2 without going through a fault model. Resample the rasters to the same
grid and format as z in preprocessing (ENCflow does not interpolate) and
make each one cumulative. The minimal example of §1 has this form. Slow
deformation such as land subsidence is easier to handle with the table
written in minutes or hours and converted with bm_tscale.

An **instantaneous displacement** (a field available at a single time)
uses a one-row table. This skips the rupture process and applies the
final displacement; the final raster can come from A or B. The table value
`0.0` corresponds to `t0`.

```
# instantaneous: final displacement at t = 0
0.0  bm/disp_0010.txt
```

In a fresh run, the final displacement is applied **at the head of the first
time step**, before solving the flow. Initial output `0000` precedes that
application and therefore contains the undeformed terrain and surface.
It does not guarantee the same result as changing only the initial water
depth over fixed terrain: bedmotion changes the terrain while keeping the
depth during application. The time-history input differs in near-field
arrival time and wave height (the sizes found in the examples are in
[the explanation](bedmotion_models.md) §2).

## 5. Application C: breaching a resolved levee

Levees can be represented in two ways: as [virtual walls](channel.md)
standing on the boundary between channel cells and landside cells (a
levee that does not thicken the cells; the breach is the crest time
series of `&list_channel_breach`), or as **elevation itself in a
high-resolution DEM** (cells of 5–10 m; called a **resolved levee** here,
by analogy with a resolved channel). A resolved levee has no virtual
wall, so `&list_channel_breach` cannot be used. Instead, the breach model
is the prescribed bed motion **lowering the bed of the breach cells at a
chosen time, width and depth**. Crest cells move even while dry (z drops
with h = 0), so the river water flows over the lowered crest onto the
floodplain.

**Procedure** (the preprocessing script
[examples/levee_breach/make_breach.py](../../../examples/levee_breach/make_breach.py)
writes the table and the windowed displacement files):

1. **Choose the breach opening**: the rectangle of levee cells (columns
   i1..i2 × rows j1..j2; both columns when the levee is two cells wide).
   The final breach width is the number of cells along the long side.
   Cell indices are 1-based ([coordinates chapter](coordinates.md)).
2. **Choose the floor elevation**: a constant (`--floor`), or for each
   row the ground of the landside toe column (`--floor-col`, a levee
   running N–S), or for each column the ground of the toe row
   (`--floor-row`, a levee running E–W). Lowering to the floodplain
   ground is usual; give a lower value for scour down to the river bed.
3. **Choose the schedule**: start t0, the time t1 at which the full width
   is at full depth (minutes), and tdeep, the time for one cell to reach
   the floor. With tdeep < t1 − t0 the central cells deepen first and the
   outer cells start later (widening). Set the start at the time the
   river level approaches the crest (from the probe output of an earlier
   run or observed stages).
4. **Generate and configure**:

```
python3 make_breach.py --z z.txt --cols 21 22 --rows 48 52 --floor-col 23 \
    --t0 70 --t1 90 --tdeep 10 --out bm
```

```
&list_sysparam
  fn_bedmotion = '-'
  f_out_z = 1               ! to check the breached terrain
  ...
/
&list_bedmotion
  fn_bmlist = 'bm/bmlist.txt'   ! table times in seconds (bm_tscale default 1)
/
```

The script writes the cumulative displacement of each cell
$`d(t) = -(z_0 - z_{floor})\,p(t)`$ (the progress p is a piecewise-linear
ramp from 0 to 1) at every break point, so linear interpolation
(f_bminterp = 1) reproduces the schedule exactly. Each table line carries
the window `i1 j1 ni nj` of the breach rectangle, and the files hold only
that rectangle. The settings of the channels chapter (fn_rw, bank0) are
not needed.

5. **Check**: the minimum applied displacement printed at the end equals
   "crest − floor", Z0001... shows the lowered opening, a
   [flux transect](record.md) drawn on the landside of the opening
   records the breach discharge, and a transect downstream in the river
   shows the discharge dropping.

The complete example is
[examples/levee_breach](../../../examples/levee_breach/README.md) (a
straight channel with a 20 m wide, 3 m high resolved levee, with a
comparison case giving the same schedule to a virtual wall through
`&list_channel_breach`).

Notes:

- Prescribed bed motion is a **prescribed change of shape**. It does not
  represent the natural widening by erosion of the embankment or the
  deposition of its material on the floodplain (the soil depth sd is not
  changed). The progression of the breach width and depth is an input
  (from observed breach geometries or empirical relations).
- Sediment and landform change (geomorph) may move the breach cells in
  the same run: the displacement is applied incrementally, so they do not
  conflict. Bed scour and breaching can be handled together.
- The effective width of a resolved-levee breach is close to the number
  of cells × dx and matches the broad-crested weir estimate 1.7·B·H^1.5.
  A virtual-wall breach with f_br_diag = 1 (diagonal edges lowered too)
  gives nearly the same discharge at 2–3 cells of width (1.5 times for one
  cell, 0.85 for five; measured in examples/levee_breach).
- An opening narrower than a cell cannot be represented (the resolution
  of a resolved levee is the cell). On a coarse grid use the breach of the
  virtual (subgrid) wall.

## 6. Water body and boundaries (tsunami runs)

- A tsunami run does **not** use the sea mask: the water body is given
  by the fixed initial level f_htype=2 (still water e0; cells with
  z < e0 are sea), the "solved sea" configuration (the same as
  [examples/landslide_tsunami](../../../examples/landslide_tsunami/)). Cells in the sea mask (sw > 0) have their
  level prescribed and therefore do not move when a displacement is given.
- Open-ocean edges use long-wave radiation (f_bc_* = 2) to reduce reflection;
  it does not guarantee zero reflection for every wave. Landward edges use
  walls (0).
- Inundation after subsidence and drying after uplift are determined by
  subsequent flow and the normal wetting/drying treatment.

## 7. Time handling, hydrostatic and non-hydrostatic

At the head of each step the displacement at the end-of-step time is
interpolated from the snapshots and the **difference** from the previously
applied displacement is added to z (the water column h is unchanged;
equations in [the explanation](bedmotion_models.md) §1). In a hydrostatic
run the bed uplift maps directly onto the surface, which is sufficient for
subduction-zone earthquakes whose source width is much larger than the
depth. For short deformation whose width is comparable to the depth (splay
faults, narrow deep-sea slip, submarine slides), use the
[non-hydrostatic correction](swflow.md) with f_nonhydrostatic=1 and
f_nh_bottom=1 and write the snapshots densely (increase nout of fault2disp);
the reason and the size of the effect are in
[the explanation](bedmotion_models.md) §3. Slow displacements such as a
breach (§5) or land subsidence are fine in hydrostatic mode.

## 8. Parameters

Set `fn_bedmotion = "-"` (read from the same file) or a file name in the
main parameters and write `&list_bedmotion`. When not specified there is
no memory or CPU cost.

| Parameter | Default | Meaning |
|---|---|---|
| f_bedmotion | 1 | 0 disables temporarily while keeping the file |
| fn_bmlist | (required) | snapshot table file (relative to dir_data) |
| f_bminterp | 1 | interpolation between snapshots: 1 linear, 0 step (hold the previous snapshot) |
| bm_tscale | 1.0 | unit of the times in the table (seconds; 60 for minutes, 3600 for hours) |

The displacement files follow the same f_input_mode (&list_geoinfo) as
the bed elevation.

## 9. Behaviour contract and interplay with other features

- The increment is added to z of eligible cells (x > 0, sw = 0); h is kept
  and e = z + h is recovered. Momentum and the soil depth sd are untouched.
- Because the displacement is applied incrementally, it does not conflict
  with sediment/landform change (including f_bedslide) or lava flow moving
  z in the same run.
- A restart continues from the same table, treating the displacement at the
  restart time as already applied (for the caveat about saving and
  restarting exactly at a switch time of the step interpolation, see
  [the explanation](bedmotion_models.md) §4).
- ENC only. The library API set_value('z') is refused while fn_bedmotion is
  active (z has a single producer).
- Output: the bed elevation Z (f_out_z) shows the deformed terrain. At the
  end the maximum and minimum of the applied displacement are printed.

## 10. Tests and examples

- [test/nhbottom](../../../test/nhbottom/) configuration 3: a Hammack-type
  uplift given as a per-step snapshot table, checked against the same
  motion through the library API, against a restart and together with a
  submarine slide (details in [the explanation](bedmotion_models.md) §5).

- [examples/tsunami_fault](../../../examples/tsunami_fault/README.md): an
  idealised reverse fault (strike N-S, dip 15°, 60 km × 30 km, slip 5 m,
  30 s rise). Comparison of hydrostatic / instantaneous / non-hydrostatic
  + acceleration term, and setup examples of the fault2disp coordinate
  patterns (bil and GeoTIFF georeference, plane rectangular system,
  longitude/latitude).
- [examples/tsunami_coast](../../../examples/tsunami_coast/README.md):
  three segments, a deep fault under the coast (0.6 m coastal subsidence),
  a shallow offshore fault (the main tsunami, 30 s later) and a splay
  fault at the bay mouth (0.8 m uplift of the cape). The disturbance from
  the coastal deformation reaches the shore 10 minutes before the offshore
  tsunami, and the subsided plain at the bay head floods earlier.
- [examples/levee_breach](../../../examples/levee_breach/README.md): a
  straight channel with a 20 m wide, 3 m high resolved levee. At the flood
  peak, 5 rows × 2 columns of levee cells are lowered to the floodplain
  ground over 20 minutes (the centre deepens first, then widens). With a
  comparison case giving the same schedule to a virtual wall through
  &list_channel_breach.
