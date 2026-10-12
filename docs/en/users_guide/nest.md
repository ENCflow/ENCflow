# Nesting (multi-level grids)

> English mirror of docs/users_guide/nest.md. The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Places finer child grids inside a coarse parent grid and solves them in the
same run (deep-sea tsunami propagation and coastal run-up, a wide-area
flood and the details of a town, and so on). Children can be nested to any
depth, and one parent can hold several children. The design background is
in docs/nesting_plan.md (Japanese).

**Current coverage**: parent → child is the water level only in the boundary
band (nest_bc = 1), level + velocity + edge discharge (2, default), Flather
radiation on open edges (3, no band), or 2 + an inner sponge (4). Child →
parent is one-way (nest_fb = 0) / area average (1) / wet-cell average (2,
default) / 2 + conservation correction (3). The time ratio r_t is any
integer, and the levels can be nested to any depth. The water-column amounts
of suspended sediment, water quality, driftwood, debris and salt water and
the groundwater storages (hg, hg2, hgc) are exchanged automatically when the
process is enabled on both parent and child. On a non-hydrostatic child
(f_nonhydrostatic = 1) the band cells become known (Dirichlet) cells of the
parent's non-hydrostatic potential φ (nest_nh, default).

![Grid layout and exchange](../../figs/nest_layout_en.png)

(a) Align the north-west corner of child cell (1,1) with that of parent
cell `(i0, j0)` specified in the grid list. i increases eastward and j
southward. The example has a 14×11 parent, an 18×18 child,
`(i0, j0) = (5, 3)` and spatial ratio `r = 3`. The child covers 6×6
parent cells, i = 5…10 and j = 3…8, leaving at least one parent cell
between its footprint and every parent edge.

Yellow marks the child's outer **boundary band**. The example uses
`nest_bc=2`, width `nb=3` child cells (one parent-cell width), and no
sponge. For `nest_bc=1, 2, 4`, the parent supplies the band values while
the child advances its interior. With `nest_nb=0`, the automatic width
is nb=2 for advection scheme 1 and nb=3 for schemes 2 and 3. Flather
(`nest_bc=3`) has no band and ignores `nest_nb`.

(b) The upper view shows interpolation from surrounding parent-cell
centres to the centre of child band cell (1,4). The spatial interpolation
shown is for cell-centred quantities with all four parent cells wet.
At each child sub-step start, values are interpolated in time between
two parent states. `nest_bc=2` also transfers edge discharge as well as
level and velocity; edge quantities use different spatial interpolation
locations from cell-centred quantities.

The lower view returns values from child cells i = 10…12, j = 10…12
to parent cell (8,6), which covers exactly the same area. It illustrates
the area average for `nest_fb=1` with effective area fraction equal to 1;
the destination parent cell is drawn separately on the right. In this
layout the replaced parent cells are i = 6…9, j = 4…7. Parent cells
containing the boundary band are excluded; `nest_bc=4` also excludes
those containing the sponge. A parent cell is replaced only when its
**entire r×r child block** lies inside the child interior beyond both
band and sponge. `nest_fb=0` disables child-to-parent replacement. See
"Child-to-parent replacement" below for the averaging options.

Generate both languages as PNG and SVG with
`python docs/figs/make_nest_figs.py layout`.

## How to use

1. Name the list file in the parameter file of the root (the coarsest grid).

```
&list_sysparam
  ...
  fn_nest = "nest.txt"      ! list of nested grids (empty = no nesting)
/
```

2. The list file (one grid per line; `#` lines are comments):

```
# id  parent  param_file           r  r_t  i0  j0
1     0       param_root.txt
2     1       bay/param_bay.txt    1  1    133 133
3     2       town/param_town.txt  1  1    40  25
```

| Column | Meaning |
|---|---|
| id | grid number; equal to the line number (1 = root) |
| parent | the parent's grid number (smaller than its own; 0 for the root) |
| param_file | the parameter file of that grid (terrain, properties, initial conditions and output directory are per grid) |
| r | spatial ratio = parent dx / child dx (positive integer; 1 if omitted) |
| r_t | time ratio = parent dt / child dt (positive integer; 1 if omitted; r_t = r is the usual choice) |
| i0, j0 | the parent cell at which the corner of child cell (1,1) is aligned (required for children). j increases in file row order (north to south) |

![Nested time stepping and boundary-value interpolation](../../figs/nest_time_en.png)

(a) One parent step Δt contains three child steps with `r_t=3`; each child
step contains two grandchild steps with `r_t=2`, giving six in total.
Each `r_t` is relative to the immediate parent and is independent of the
spatial ratio `r`. The horizontal axis shows physical simulation time,
not a schedule in which all grids advance concurrently. The parent takes
its step first and retains the parent-window values needed for the child
boundary at `tⁿ` and `tⁿ⁺¹`, before and after that step. The child then
takes `r_t` sub-steps.

(b) Number the child sub-steps `k=0…r_t−1`. The start time is
`tⁿ + k Δt/r_t`, with interpolation weight `α=k/r_t`. A quantity Q
stored in the parent window is interpolated as
`Q(α)=(1−α)Qⁿ+αQⁿ⁺¹`, followed by spatial interpolation, wet/dry rules
and other operations appropriate to the boundary method. This **start-time**
interpolation supplies water level, velocity and related data. Flather
(`nest_bc=3`) also uses the start time, supplying external level and
velocity on open edges instead of overwriting a band. The illustrated
weights are `0/3, 1/3, 2/3`.

For a non-hydrostatic child with `nest_nh=1` and `nest_bc=1, 2, 4`, the
known band values of φ are interpolated to the sub-step **end time**.
The figure denotes this weight by `β=α+1/r_t`, giving `1/3, 2/3, 3/3`.
Both ordinary boundary data and φ are prepared before advancing the child
step, but they refer to different times. Even with `r_t=1`, ordinary
boundary data use the parent at `tⁿ`, while φ uses `tⁿ⁺¹`. A parent
without non-hydrostatic calculation supplies zero φ.

A grandchild repeats the same procedure recursively inside each child
step, interpolating between two states of its immediate parent. Green
arrows mark replacement at synchronization for `nest_fb=1–3`. The example
executes: parent step → [child step → two grandchild steps → replace into
child]×3 → replace into parent. The end-time window used for interpolation
is captured immediately after that grid's step, before replacement from
its descendants. If one parent has several children, each child completes
all its sub-steps and replacement into the parent before the next child
is advanced.

`nest_fb=0` skips child-to-parent replacement. Methods 1–3 average the
eligible interior back into the parent; method 3 also applies interface
flux conservation correction. Parent cells containing a boundary band or
sponge are excluded. See "Child-to-parent replacement" below for averaging
and wet/dry handling. The figure is an algorithm schematic, not a computed
time series.

Generate both languages as PNG and SVG with
`python docs/figs/make_nest_figs.py time`.

3. Write `&list_nest` in the child's parameter file (defaults apply if omitted):

```
&list_nest
  nest_bc = 2        ! parent -> child: 1 = water level only (TUNAMI type), 2 = level + velocity + edge discharge (default; best interface consistency),
                     !        3 = Flather radiation on open edges (f_bc_* = 2; no band; one-way, lets the child's disturbances out),
                     !        4 = 2 + a sponge relaxing the nest_ns cells inside the band towards the parent's values
  nest_fb = 2        ! child -> parent: 0 = none (one-way), 1 = area average of h/m/n (volume exact), 2 = wet-cell average (default; for coastlines),
                     !        3 = 2 + conservation correction (adjusts the parent outside the interface to the child's fluxes; conserves volume)
  nest_ns = 4        ! sponge width (cells; the relaxation zone inside the band for nest_bc = 4)
  nest_nb = 0        ! boundary band width (cells). 0 = automatic (2 for advection scheme 1, 3 for schemes 2 and 3)
  nest_nh = 1        ! non-hydrostatic child: 1 = the band holds the parent's phi as Dirichlet cells (default), 0 = band + margin hydrostatic
/
```

![Nested-grid boundary methods and the non-hydrostatic option](../../figs/nest_bc_en.png)

The figure shows a west-edge row excerpt of the child; the interior continues
to the right. Panels (a)–(c) compare boundary methods selected by `nest_bc`.
Panel (d) shows the additional `nest_nh` setting for a non-hydrostatic child
with a band. The illustrated widths are nb=3 and nest_ns=4 child cells.

- (a) `nest_bc=1` prescribes water level in the band; the child computes
  velocity and discharge. `nest_bc=2` (default) transfers parent level,
  velocity and edge discharge. The solid black line is the child's outer
  wall (`f_bc_w=0` at the west edge).
- (b) `nest_bc=3` uses Flather radiation with no band. The orange dashed line
  is an open edge (`f_bc_w=2` at the west edge). The arrows show incoming
  parent waves and outgoing child disturbances. Normal velocity in the
  equation is **positive outward from the child**, to the left at this edge.
- (c) `nest_bc=4` adds a sponge inside the same band as method 2. The numbers
  in green cells are relaxation weights w, decreasing inward. Parent cells
  containing the band or sponge are excluded from child-to-parent replacement.
- (d) `nest_nh=1` (default) prescribes the parent's φ as known band values.
  The example interior is wet and active in the projection. The orange
  band–interior edges are corrected too. Ordinary boundary values are
  interpolated to the sub-step **start**, while φ uses the sub-step **end**.
  `nest_nh` is separate from `nest_bc` and does not apply to band-free method 3.

Generate both languages as PNG and SVG with
`python docs/figs/make_nest_figs.py bc`. For comparisons against a uniform
fine grid, see the illustrated README in examples/nest_reflect.

## Conditions on a child grid (checked at initialization; the run stops if violated)

- child dx × r = parent dx, child dt × r_t = parent dt, and the same t0 and
  duration as the parent. Each grid's dt follows its own CFL condition and
  r_t = r is the usual choice (with r_t = 1 the parent's dt is also set by
  the child's CFL).
- The child's nx and ny are multiples of r. The whole child lies inside the
  parent, at least one parent cell away from the parent's outer edge (the
  cell outside the footprint is used for interpolation).
- The child's outer edges are walls (`&list_bound_edge` f_bc_* = 0, the
  default) with no inflow segments. The band (the outer nb cells) is given by
  the parent, so no boundary condition is set on the child. **nest_bc = 3 is
  the opposite**: the edges that receive the parent's values are set to
  `f_bc_* = 2` (long-wave radiation; see below).
- The child is large enough compared with the band (nx, ny > 2·nb + 2).
- The scheme is ENC (f_gridsystem = 0).

## Output and restart

- Every grid writes to its own `dir_result` as usual (distributions, probes,
  transects, Log.txt). Give each grid a different directory.
- State save / restore (f_state_save / f_state_restore) also works per grid.
  Give each grid its own `dir_save`. Restarting the root restarts all grids.
- The screen output alternates between grids (each root step is followed by
  its children).

## Non-hydrostatic child grids (nest_nh)

When a child with a band is non-hydrostatic (f_nonhydrostatic = 1), the band
cells are removed from the unknowns of the child's projection (the elliptic equation
for φ) and become known (Dirichlet) cells of φ. By default (nest_nh = 1) the
parent's φ (interpolated to the end of the sub-step) is placed there, so the
non-hydrostatic pressure of a dispersive wave coming from the parent is
continuous at the interface, and in a 1:1 self-nest the child's interior
matches the parent (to the CG tolerance; maximum difference 2e-13 m in the
nh case of test/nest_identity). nest_nh = 0 makes the band and the
nh_bc_margin cells inside it hydrostatic (the same margin as the other forced
boundaries), which shifts the phase of dispersive waves at the interface
(maximum difference 1.4e-2 m in the same case). If the parent is not
non-hydrostatic, φ = 0 is placed even with the default.

- Children with nest_bc = 1, 2 and 4 (with a band) are supported. It does
  not apply to Flather (nest_bc = 3), where the vicinity of the open faces
  keeps the hydrostatic margin nh_bc_margin.
- The active set (f_nh_adaptive = 1) can be used as is. Interior candidates
  adjacent in the eight-cell neighbourhood to band cells whose |φ_e| meets
  the seed floor are also seeded. No extra setting is needed for nesting.
- The auxiliary solve of the moving-bottom smoothing (f_nh_bottom) is done
  with φ = 0 in the band (an approximation).

## Flather radiation (nest_bc = 3)

Instead of a band, the long-wave characteristic condition
u_n = u_n,e + √(g/h)(η − η_e) is imposed on the boundary faces of the child's
open edges (Flather 1976). η_e and u_n,e are the parent's water level and
outward normal velocity on the edge (interpolated to the centre of the
boundary cell, and in time to the start of the sub-step). It generalizes the
existing long-wave radiation boundary (`f_bc_* = 2`, where η_e = reference
level and u_e = 0): waves coming from the parent pass in, and disturbances
generated inside the child (reflections from the finer coast, the return
flow of run-up) radiate out. Both u_n and u_n,e are positive outward from the
child, and h is the child boundary-cell depth. The implementation uses
max(h, dv) in the denominator, then projects the resulting edge-normal
velocity onto the individual ENC boundary faces to compute discharge.

- Meant for **one-way** nests (nest_fb = 0), when you do not want the
  child's reflections trapped inside the child. With a Dirichlet band
  (nest_bc = 2) the child's disturbances are overwritten by the parent's
  values in the band, which can cause reflection. Two-way replacement
  (nest_fb ≥ 1) can reduce this effect. Use the default 2 normally and
  consider 3 for one-way nests.
- In the child's `&list_bound_edge`, set the edges that receive the parent's
  values to `f_bc_* = 2` (it can be written inside the parameter file with
  `fn_boundary = '-'`). Edges with 0 (wall) stay walls (place the landward
  boundary above the maximum run-up). 1 (free outflow) and inflow segments
  are not allowed. At least one edge must be 2.
- There is no band (nest_nb is ignored). No sponge. Combined with
  child → parent replacement (two-way), parent cells that contain boundary
  cells are not replaced. The additional fields (suspended sediment, water
  quality, groundwater, ...) are not exchanged (inflow through the faces is
  clear water).
- Put the open edges in **permanently wet water**. A face is closed during
  the sub-steps in which the parent's interpolation point is dry, and the
  flux is 0 if the child's boundary cell is dry (no re-wetting from the
  boundary).
- If the parent is at rest (constant η, u = 0) the result is bit-identical
  to the existing radiation boundary (the flather case of
  test/nest_identity). The comparison with a band on a one-way r3t3 interface
  crossing is in examples/nest_reflect (README).

## Sponge (nest_bc = 4)

Inside the same boundary band as `nest_bc=2`, add a relaxation region
`nest_ns` child cells wide. At each sub-step start, blend a cell quantity q
towards its interpolated parent value q_parent as
`q ← (1 − w) q + w q_parent`. For the shortest inward cell distance
d=1…nest_ns from the band, `w = [1 − d/(nest_ns + 1)]²`. With nest_ns=4
as illustrated, the weights from the band inward are 0.64, 0.36, 0.16 and 0.04.

This applies to depth, velocity, cell discharge and enabled additional
fields exchanged between parent and child. Edge quantities are not relaxed
with these weights. The band is replaced by parent values; the sponge is
relaxed towards them before advancing the child. Only complete r×r child
blocks beyond both band and sponge contribute to child-to-parent replacement.

## Child-to-parent replacement (nest_fb)

- Parent cells whose entire r×r child block lies inside the child interior,
  excluding the band and sponge, are replaced by child averages at the end
  of each parent step. Flather has no band, but the one-parent-cell rim
  corresponding to the child's outer edges is excluded from replacement.
  nest_fb = 2 averages the level and depth over the wet child cells
  only, and dries the parent cell if the parent's ground is above the mean
  level (for regions straddling the coastline; the water volume is not
  strictly conserved). nest_fb = 1 is a plain average of depth and discharge
  that conserves volume exactly (for fully wet regions).
- Parent cells whose effective area fraction is not 1 (subgrid channel width
  or porosity) receive the child's true water amount converted back to a
  rectangular depth with the parent's area fraction (consistency of channel
  levels).
- nest_fb = 3 returns the difference between the parent's and the child's
  interface fluxes around the replaced region to the parent's depth, so the
  whole system conserves volume (equivalent to GeoClaw's reflux).
- A summary is printed at the end (water volume added to the child by the
  band replacement, the number of replacements and the cumulative change of
  the parent's water volume, the amount of the conservation correction). On
  land, rain falling in the band is overwritten by the parent's values, so
  the child's water balance is checked by adding this band replacement
  volume.

## Using it from BMI

A nest system is one BMI model as it is (bmi/README.md). Passing the root's
parameter file to `initialize` initializes all grids; `update` is one root
step (the children advance inside it) and the time is the root's. Grids are
distinguished by grid id: 0 = root, k = line k+1 of the list. Variables of
non-root grids carry `~grid<k>` in the object part of the name
(`surface_water~grid1__depth` = the depth of grid 1). In Python
`var_on_grid(VAR_DEPTH, 1)` builds the name, and `model.grids`,
`model.shape_of(k)` and `model.origin_of(k)` return the grid information. If
there is no georeferencing, a child's origin is derived from the parent's
origin and the alignment position, so all grids are expressed in the root's
coordinate system. set (depth, terrain, precipitation) works per grid under
the same conditions. The acceptance test is test/bmi_nest.

## Notes

- In one-way mode (nest_fb = 0) the child's reflections and run-up do not
  return to the parent. The parent's coarse coastal reflection enters the
  child through the band, and the child's disturbances reflect at the band
  (resolved by two-way mode, or by nest_bc = 3 which radiates them out).
- Run-up on land near the child's band (about nb × r cells) is coarsely
  approximated; keep it away from the points of interest. Place the landward
  boundary above the maximum run-up so that water never reaches it.
- In a 1:1 self-nest (child = a subregion of the parent) the child's interior
  is bit-identical to the same region of the parent, and in two-way mode the
  whole root is bit-identical to a stand-alone run (test/nest_identity; its
  README lists the identity cases; useful for verifying the band and
  replacement design).
- Verification of waves crossing the interface of two-way nests at ratios 3
  and 5 (comparison with a uniform fine grid; figures of the levels, errors,
  one-way band vs Flather and the non-hydrostatic band) is in
  examples/nest_reflect.
