# Boundary conditions (&list_bound_edge / source / stage / inflow)

> English mirror of docs/users_guide/boundary.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the user's guide index](../users_guide.md)

Defines the exchange of water between the computational domain and the
outside world. Enabled via `fn_boundary`; **four families** are
configured in independent namelist groups. A family is inactive if its
group is not written (absence is normal).

| Family | Group | Role |
|---|---|---|
| Edge boundaries | &list_bound_edge | boundary condition type on the four outer edges of the domain |
| Internal sources | &list_bound_source | injection/extraction Q(t) at arbitrary cells |
| Prescribed water level | &list_bound_stage | force the water level of a cell set to eta(t) |
| Segment inflow | &list_bound_inflow | river inflow Q(t) through a segment of the outer edge |

For every family, cell sets and time series can be written directly in
the namelist or given as files (`fn_*`; paths relative to dir_data).
Time series are interpolated linearly, and the end values are held
outside the range. Cell coordinates (i, j) are **1-based** (add +1 when
picking numbers from the 0-based numbering of GIS such as QGIS;
[coordinates chapter](coordinates.md)).

## Edge boundaries (&list_bound_edge)

Assigns a boundary condition type to each of the four outer edges
(west = i=1, east = i=nx, north = j=1, south = j=ny; row order is north
to south).

```
&list_bound_edge
  f_bc_w = 2                ! west edge
  f_bc_e = 2                ! east edge
  f_bc_n = 2                ! north edge
  f_bc_s = 2                ! south edge
/
```

| Type | Meaning | Suited for |
|---|---|---|
| 0 (default) | impermeable (wall) | tanks, closed catchments |
| 1 | free outflow. Advancing flow passes through as is, and standing water drains by free overfall. No inflow | outflow of flood flows advancing over dry ground |
| 2 | long-wave radiation. No outflow at still water; only the water level deviation of waves reaching the boundary is transmitted (inflow of receding waves is also allowed) | propagation of tsunamis, storm surges, and waves |

- The reference water level of type 2 is derived automatically from the
  initial condition if unspecified (with a constant initial water
  level, the radiation flux at t=0 is exactly zero). To fix it, give a
  uniform value in `bc_eta_w/e/n/s` (same elevation datum as z).
- Edge boundaries take effect only on **edges where valid cells touch
  the grid frame**. They have no effect on catchment terrain surrounded
  by a rim of nodata (outside the mask) -- use prescribed water level
  cells for drainage in that case.
- For a working example see
  [tutorial Step 3](../../../tutorials/wave/en/README.md#step-3-setting-boundary-conditions).

## Internal sources (&list_bound_source)

Injection (Q > 0) or extraction (Q < 0) at an arbitrary cell set. The
third subscript is the source number (consecutive from 1).

```
&list_bound_source
  src_cell(:,1,1) = 10, 10       ! cell (i, j) of source 1
  src_cell(:,2,1) = 10, 11
  src_val(:,1,1) =   0,   0.0    ! (time (min), discharge (m3/s))
  src_val(:,2,1) =  60, 100.0
/
```

- The discharge is the **total over the whole cell set**, distributed
  equally among the cells.
- Extraction stops when the cell's depth reaches 0 (the shortfall is
  not pumped).
- The injection carries no directionality (momentum). For river inflow,
  use the segment inflow.

## Prescribed water level cells (&list_bound_stage)

Forces the water level of a cell set to a fixed value `stage_eta(n)` or
a time series `stage_val`. The depth is set to h = max(eta - z, 0)
every step, and the exchange with the surroundings is computed by the
momentum equation from the gradient created by the prescribed level (so
it also appears in velocity/discharge output and transect measurement).

```
&list_bound_stage
  stage_cell(:,1,1) = 100, 200
  stage_eta(1) = -999.0          ! water level below the bed -> perfect drain
/
```

- For the **outlet of a catchment-clipped computation** (drainage out
  of the catchment), set eta below the bed -- the cells become
  permanently empty perfect drains.
- For **tidal reaches and backwater**, use a water level time series
  `stage_val(:,k,n) = t, eta`.
- A large level difference between prescribed cells and their
  surroundings produces a local dam-break flow. If the initial Cn_max
  is large, review dt.

## Segment inflow (&list_bound_inflow)

A boundary through which a river or similar enters across the outer
edge of the domain. Prescribes the **total discharge** Q(t) of the
segment on the outward normal face of a cell segment touching the outer
edge. Unlike an injection, it is a directional inflow carrying
momentum.

```
&list_bound_inflow
  inflow_cell(:,1,1) = 1, 100    ! segment j=100..102 on the west edge
  inflow_cell(:,2,1) = 1, 101
  inflow_cell(:,3,1) = 1, 102
  inflow_val(:,1,1) =   0,   0.0 ! (time (min), total discharge (m3/s))
  inflow_val(:,2,1) =  60, 500.0
  inflow_dist(1) = 2             ! distribution mode within the segment
/
```

**Distribution modes (inflow_dist)** -- in every mode the total inflow
is exactly Q(t).

| Value | Distribution | Characteristics |
|---|---|---|
| 0 (default) | equal (proportional to opening width) | unit-width discharge is uniform over the segment |
| 1 | proportional to depth | inflow velocity is uniform over wet cells. No inflow into dry cells |
| 2 | proportional to conveyance (h^5/3) | same as a uniform-slope Manning cross section. Distribution resembling a river cross section |

Modes 1 and 2 blend continuously toward the equal mode according to the
Froude-number margin of the velocity, so they do not break down on dry
cross sections or during recession. At low flow the inflow enters only
the low-flow channel, not the dry floodplain.

- Discharges are non-negative only (for outflow use prescribed water
  level or extraction).
- When combined with sediment computation (suspended sediment), the
  incoming sediment can be given as a concentration time series
  `inflow_cs` or a sediment discharge time series `inflow_qs`
  (mutually exclusive) ([sediment and geomorphic change
  chapter](geomorph.md)). If unspecified, the inflow is clear water.

## Examples and format samples

- Annotated example of all parameters: [examples/List_samples/list_boundary.txt](../../../examples/List_samples/en/list_boundary.txt)
- Edge boundary (radiation): [tutorials/wave](../../../tutorials/wave/en/README.md) Step 3
- Structures such as drainage pumps and sluice gates are on the fn_structure side ([structures chapter](structure.md)).
