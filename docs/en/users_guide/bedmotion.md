# Prescribed bed motion (&list_bedmotion)

> English mirror of docs/users_guide/bedmotion.md. The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Forces the bed elevation z with a prescribed **time history** of ground
displacement. The main use is tsunami generation from fault-derived
seafloor deformation (generation, propagation, run-up and inundation in a
single run). The water column h is kept and z is moved, so the surface
e = z + h rises with the bed (the same contract as the morphological
modules). The design is in [docs/bedmotion_plan.md](../bedmotion_plan.md),
the implementation record in developer.md §70.

## Enabling

Set `fn_bedmotion = "-"` (read from the same file) or a file name in the
main parameters and write `&list_bedmotion`. When not specified there is
no memory or CPU cost.

```
&list_bedmotion
  fn_bmlist = 'bm/bmlist.txt'   ! snapshot table (relative to dir_data)
/
```

| Parameter | Default | Meaning |
|---|---|---|
| f_bedmotion | 1 | 0 disables temporarily while keeping the file |
| fn_bmlist | (required) | snapshot table file (relative to dir_data) |
| f_bminterp | 1 | interpolation between snapshots: 1 linear, 0 step (hold the previous snapshot) |
| bm_tscale | 1.0 | unit of the times in the table (seconds; 60 for minutes, 3600 for hours) |

## Snapshot table and displacement files

One line per snapshot: "time file" (blank lines and lines starting with
`#` or `!` are ignored). Times are relative to t0 and increasing; file
names are relative to dir_data.

```
# time(s)  file
  0.0      bm/disp_0000.txt
 10.0      bm/disp_0010.txt
 60.0      bm/disp_0060.txt
```

Each file holds the **cumulative** displacement d [m], relative to the
terrain at the start of the run (not an increment), in the same format and
row order as the bed elevation z (text matrix / bil / GeoTIFF according to
f_input_mode). Before the first time the first value holds, after the last
time the last value holds. A table with a single line (final displacement
at t = 0) is an instantaneous deformation at the start, equivalent to the
initial-surface-displacement approach.

For large domains, four integers `i1 j1 ni nj` at the end of a line make
the file a **window**: an ni × nj matrix covering columns i1..i1+ni−1 and
rows j1..j1+nj−1 of the full grid, with zero displacement outside
(`f_window = 1` of utils/fault2disp writes this form). The model restricts
the application to the union of the windows, so both the file size and the
per-step work scale with the window, not the grid.

```
# time(s)  file               i1  j1  ni  nj
  0.0      bm/disp_0000.txt   90  40  80  70
 30.0      bm/disp_0010.txt   90  40  80  70
```

## Behaviour

- At the head of each step the displacement at the end of that step is
  interpolated and the **difference** from the last applied displacement is
  added to z of land cells (x > 0, outside the sea mask). h is unchanged and
  e = z + h is recovered. Momentum is untouched. The soil thickness sd is
  unchanged (the bedrock surface z − sd moves).
- Because increments are applied, morphological change (including
  f_bedslide) and lava flow may move z in the same run without conflict
  (an earthquake-triggered submarine landslide can be in the same run).
- Sea-mask cells (sw > 0) do not move. Run tsunamis without a sea mask,
  representing the water by the initial surface (f_htype=2), as in
  examples/landslide_tsunami.
- With linear interpolation the bed velocity is constant between
  snapshots. With the non-hydrostatic acceleration term (f_nh_bottom) the
  velocity jump at each snapshot boundary enters as an acceleration pulse;
  emit denser snapshots from the preprocessing when a smooth history is
  needed (test/nhbottom uses one per step).
- Restart: no private state is saved. On restore the displacement at the
  restore time is evaluated from the table and taken as already applied,
  so the increments are those of an uninterrupted run.
- The library API set_value('z') is refused while fn_bedmotion is active
  (one producer of z).
- Output: the bed elevation Z (f_out_z) shows the deformed terrain; the
  maximum and minimum applied displacement are printed at the end.

## Relation to the non-hydrostatic correction

In hydrostatic runs the bed uplift maps directly onto the surface, which is
adequate for long-wavelength subduction earthquakes. For deformation whose
width is comparable to the depth (splay faults, narrow deep-sea slip,
submarine landslides) the short-wave attenuation due to the inertia of the
water column (Kajiura filter) is supplied by f_nh_bottom=1 of the
[non-hydrostatic correction](swflow.md) (one-layer approximation
1/(1 + βk²)²; developer.md §69.10).

## Verification

test/nhbottom configuration 3: a Hammack-type uplift of 0.2 m in 1 s over
|x − x_c| < 20 m in 10 m of water, given as a one-snapshot-per-step table,
matches the driver that imposes the same motion through the library API
(identical except the last digit of the full-precision volume column of the
Log). A restart (save at 0.5 s, then restore) matches the uninterrupted run
(hydrostatic; with the non-hydrostatic f_nh_bottom it differs by one step of
the acceleration term),
and in coexistence with a submarine landslide (f_bedslide) the ledger
Σ(z − z0) = Σ d holds within the output precision (the bed layer's internal
transfer sums to zero).

## Preprocessing (fault parameters → displacement): utils/fault2disp

A utility that converts fault parameters (centre of the top edge, top
depth, strike, dip, rake, length, width, slip, rupture start time, rise
time) into displacement snapshots and the snapshot table with Okada's
(1985) formulas ([utils/fault2disp/README.md](../../utils/fault2disp/README.md)).
It superposes several segments, each with its own start time and rise
function (linear / half-sine), optionally adds the contribution of the
horizontal displacement u_h·∇z (Tanioka & Satake 1996) when a bed
elevation file is given, and can write windowed output for large domains
(f_window). Fault positions are given either in the projected coordinates
of the grid or in longitude/latitude (f_lonlat=1; Transverse Mercator =
UTM and the Japanese plane rectangular systems; the strike is corrected
for the meridian convergence to grid north).

```
cd utils/fault2disp && make && make check   # check against Okada (1985) Table 2
./fault2disp fault2disp.txt                  # bm/disp_NNNN.txt and bm/bmlist.txt
```

See examples/tsunami_fault (an idealised reverse fault: strike N-S, dip
15°, 60 km × 30 km, slip 5 m, 30 s rise; hydrostatic / instantaneous /
non-hydrostatic with the acceleration term).
