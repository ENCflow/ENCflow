# levee_breach — breaching a resolved levee with prescribed bed motion (fn_bedmotion)

> English mirror of examples/levee_breach/README.md. The Japanese file is the master copy.

[日本語](../README.md)

In a high-resolution DEM the levee is present **as elevation itself**
(called a **resolved levee** here, by analogy with a resolved channel).
This levee has none of the virtual walls of the
[channel chapter](../../../docs/en/users_guide/channel.md), so its breach
cannot be given with `&list_channel_breach`. Instead,
[prescribed bed motion](../../../docs/en/users_guide/bedmotion.md) §5
lowers the ground elevation of the breach cells at a chosen time, width
and depth. This example is an idealized terrain of a straight channel + a
resolved levee 20 m wide and 3 m high + a floodplain; at the flood peak,
5 rows × 2 columns of levee cells are lowered to the floodplain ground
over 20 minutes (the central row reaches the floor in 10 minutes, then the
opening widens to both sides). The preprocessing script
[make_breach.py](../make_breach.py) converts the breach schedule into the
input of fn_bedmotion (windowed cumulative-displacement files and a
snapshot table). A comparison case gives the same schedule to a virtual
wall through `&list_channel_breach`. No code change (settings only).

## Geometry and setup

![Setup](../figs/setup.png)

Left: terrain and the breach opening. Right: east–west profile along the
central row of the opening (j = 50) at the start of the run and after the
breach.

1,200 m × 800 m, dx = dy = 10 m (120 × 80 cells). Descends from north to
south at 1/1000. From the west:

| x (m) | Cell index i | Terrain | Role |
|---|---|---|---|
| 0–150 | 1–15 | Floodplain + 4 m | Hill-bounded (west bank; does not flood) |
| 150–200 | 16–20 | Floodplain − 3 m | Channel (50 m wide, roughness 0.03) |
| 200–220 | 21–22 | Floodplain + 3 m | **Resolved levee** (20 m wide) |
| 220–1,200 | 23–120 | Descends eastward at 1/2000 | Floodplain (roughness 0.05) |

- Inflow: a discharge hydrograph on the 5 channel cells of the north edge
  (100 m³/s → 700 m³/s at 60 min, held until 120 min, 100 m³/s at
  150 min). The downstream end (the 5 channel outlet cells on the south
  edge) prescribes the uniform-flow water level in step with the
  hydrograph (a 2-D computation has no sidewall friction, R = h: 4.7 m at
  Q 700, 1.3 m below the crest). The south and east edges of the
  floodplain are free outflow.
- Breach: columns 21–22 × rows 48–52 (50 m wide). The floor in each row is
  the ground elevation at the toe (column 23) (`--floor-col 23`). Starts
  at 70 min from the central row, each row reaching the floor in 10 min;
  the rows on both sides start at 75 and 80 min (full width and full depth
  at 90 min). `make bm/bmlist.txt` runs the following:

```
python3 make_breach.py --z z.txt --cols 21 22 --rows 48 52 --floor-col 23 \
    --t0 70 --t1 90 --tdeep 10 --out bm
```

| Case | Parameter file | Levee | Breach | Terrain |
|---|---|---|---|---|
| Resolved levee | param.txt | Elevation in z (columns 21–22 at + 3 m) | Prescribed bed motion (bm/bmlist.txt) | z.txt |
| Virtual wall | param_vwall.txt | bank0 = 3 m in &list_channel (datum: floodplain cell elevation) | &list_channel_breach (5 sites, same times; f_br_diag = 1 couples the diagonal edges too) | z_vwall.txt (columns 21–22 replaced by the floodplain ground) |

dt = 0.5 s, 3 hours. The computation takes about 30 seconds per case
(gfortran, 4 threads).

## Using make_breach.py (for your own case)

```
python3 make_breach.py --z <ground elevation> --cols I1 I2 --rows J1 J2 \
    (--floor Z | --floor-col C | --floor-row R) --t0 T0 --t1 T1 [--tdeep TD] [--center K] [--out DIR]
```

- `--cols`, `--rows`: the cell rectangle of the breach opening (1-based;
  both columns when the levee is 2 cells wide). The long side becomes the
  direction along the levee, and the cells start with a delay outward from
  the `--center` cell (default: the middle).
- Floor: `--floor` is a constant, `--floor-col C` the ground elevation of
  column C in each row (a north–south levee; the column of the landside
  toe), `--floor-row R` the ground elevation of row R in each column (an
  east–west levee).
- `--t0`, `--t1` (minutes): the start and the time at which the full width
  reaches full depth. `--tdeep` (minutes): the time for one cell to reach
  the floor (default t1 − t0 = all cells simultaneously).
- Output: `DIR/bmlist.txt` (times in seconds; each line carries the window
  `i1 j1 ni nj`) and `DIR/breach_NN.txt` (cumulative displacement of the
  window only, one per break point in time). The main input needs only
  `fn_bedmotion = '-'` and `&list_bedmotion fn_bmlist = 'DIR/bmlist.txt'`.
- The displacement files are text matrices. In runs using GeoTIFF / bil
  ground elevations (f_input_mode), convert them to the same format first
  (the conversion is preprocessing).

## How to run

```
cd examples/levee_breach
make                                   # link, z.txt etc., bm/ (make_breach.py)
./encflow param.txt                    # resolved levee + prescribed bed motion
./encflow param_vwall.txt              # virtual wall + &list_channel_breach
python3 plot_results.py                # figs/*.png and tables
```

## Results

![Time series](../figs/timeseries.png)

Left: inflow hydrograph, discharge through the breach opening (transect at
column 23), and channel discharge downstream (j = 70). Center: river level
in front of the opening and ground elevation of the breach cells (for the
resolved levee the z column of probe 3 shows the lowering of the levee
directly). Right: inundation depth on the floodplain (toe, middle, far).
The band marks the progress of the breach (70–90 min).

![Inundation](../figs/inundation.png)

| Case | Peak discharge through the opening (m³/s) / time (min) | Flood volume (10⁴ m³) | Inundated area (ha; h > 0.01 m) | Maximum inundation depth (m) | Start of inundation at the toe (min) |
|---|---:|---:|---:|---:|---:|
| Resolved levee + prescribed bed motion | 152 / 120 | 40.2 | 71.8 | 1.10 | 76 |
| Virtual wall + &list_channel_breach (f_br_diag = 1) | 150 / 120 | 41.4 | 71.0 | 0.98 | 76 |

- With the resolved levee, once the levee cells have been lowered to the
  floor the opening consists of ordinary cells and the shallow-water
  equations solve the flow as they are (all links to the 8 neighbours
  open). The channel discharge downstream drops from 700 to 550 m³/s, and
  150 m³/s leaves through the opening onto the floodplain. The minimum
  applied displacement printed at the end, −3.00 m, equals
  "crest − floor".
- With the virtual wall, the edges made sites convey flow by the Honma
  formula. With `f_br_diag = 1` the diagonal edges touching a site are
  lowered to the same crest, so the passing width per breached cell
  becomes one cell width (normal 0.414 + diagonal 2 × 0.293), and at 5
  cells of width the discharge is 0.98 times that of the resolved levee.
  With `f_br_diag = 0`, which lowers only the normal edges of the sites as
  before, the diagonal links between adjacent sites remain walls, so the
  discharge stays at 0.44 times (measurements below). The division of
  roles is: the virtual-wall breach for failures narrower than a cell or
  on coarse grids, prescribed bed motion for runs in which the levee is
  resolved by cells.

**Relation between breach width and discharge** (the breach width varied
on the same terrain, total failure simultaneously at 70–80 min, steady
discharge at 100 min compared):

| Width (cells / sites) | Resolved levee Q (m³/s) | Broad-crested weir 1.7·B·H^1.5 (m³/s) | Virtual wall f_br_diag = 0 Q / ratio to resolved | f_br_diag = 1 Q / ratio to resolved |
|---:|---:|---:|---:|---:|
| 1 | 36.5 | 37 | 15.1 / 0.41 | 60.8 / 1.66 |
| 2 | 73.7 | 70 | 29.5 / 0.40 | 86.1 / 1.17 |
| 3 | 105.1 | 102 | 43.1 / 0.41 | 108.5 / 1.03 |
| 5 | 152.3 | 162 | 67.5 / 0.44 | 149.2 / 0.98 |

The resolved levee matches the broad-crested weir estimate (B = number of
cells × dx, H = river level − floor ≈ 1.5–1.7 m), and for wider openings
it falls below the weir formula as the water level rises on the
floodplain side (152 vs 162 at 5 cells). The virtual wall with
f_br_diag = 0 has an effective width of 0.38 dx per site (the
passing-width share 0.414 of a normal edge), proportional to the number
of sites; f_br_diag = 1 is nearly equal to the resolved levee at 3–5
cells of width (1.03 and 0.98 times) and overestimates at 1 cell by the
two end diagonals (0.59 cell widths; 1.66 times). The f_br_diag = 1
result agrees with a run in which the diagonal pairs are added explicitly
as sites (maximum difference 0.35 m³/s, because the reference ground
elevation of the diagonal sites themselves differs by 1 cm; measured with
f_advection_scheme = 1). The table uses the default advection scheme 3;
with scheme 1 (the setting of this example until 2026-10-23) the virtual
wall with f_br_diag = 1 was closest to the resolved levee at 2–3 cells and
0.85 times at 5 cells (in the virtual-wall channel the river level in
front of the opening moves by about 0.1 m with the scheme). The options
considered and rejected are in
[Channels explained](../../../docs/en/users_guide/channel_models.md) §4.

## Notes

- Prescribed bed motion is a prescribed change of shape; it does not
  represent the natural widening by erosion of the embankment or the
  deposition of the embankment material (the soil depth sd is not
  changed). The progression of the breach width and depth is given as
  input (observed breach geometries or empirical relations).
- With a free-outflow downstream end the water surface drops toward the
  outlet (backwater length ≈ h/S = 4.7 km), the river level at the
  opening is 2 m away from the crest and the overflow is weak. A short
  idealized channel needs a prescribed water level at the downstream end.
- Advection is the default (`f_advection_scheme = 3`, momentum-conserving
  form + MUSCL). The code before 2026-10-18 self-excited a discharge
  oscillation of 5-minute period and ±6 % in this deep straight channel
  (insufficient damping of the diagonal sublattice mode;
  docs/developer.md §68.36–68.39, docs/handoff.md 00a), so both cases of
  this example used `f_advection_scheme = 1` at that time. With the
  current code the standard deviation of the channel discharge after the
  breach is complete (92–120 min) is 0.6 m³/s (0.9 with scheme 1), and the
  transverse distribution in the channel is uniform over the 5 columns.
- The datum of the virtual-wall crest is stated explicitly as
  `f_bank_datum = 1` (floodplain cell elevation). The default of the code
  before 2026-10-13 was 0 (bed datum); if omitted, the crest in this
  example coincided with the floodplain ground and overflowed along its
  whole length (docs/handoff.md 00a). The current default is 1, and the
  explicit setting remains as a caution to the reader.
