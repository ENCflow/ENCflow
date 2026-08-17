# Geographic information (&list_geoinfo)

> English mirror of docs/users_guide/geoinfo.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the user's guide index](../users_guide.md)

Settings for the grid, topography, roughness, and the various masks that
form the foundation of a computation. This is the only **mandatory
feature**; it is read via `fn_geoinfo` (default `"-"` = inside the
parameter file).

The minimal configuration is just the grid definition (tutorial wave
takes this form).

```
&list_geoinfo
  lx = 100.0, ly = 100.0    ! size of the computational domain (m)
  nx = 300, ny = 300        ! number of grid cells
/
```

For real-terrain computations, topography files, roughness, and masks
are added on top of this.

## Grid definition

| Parameter | Default | Meaning |
|---|---|---|
| nx, ny | -- | number of grid cells (mandatory) |
| dx, dy | -- | grid spacing (m) |
| lx, ly | -- | domain size (m) |
| epsg | 0 | EPSG code of the grid's coordinate system ([coordinates chapter](coordinates.md)) |

For each direction, specify **nx and either dx or lx** (if both dx and
lx are given, their consistency is checked and a contradiction stops the
run). With bil input accompanied by a `.hdr` sidecar, nx, ny, dx, dy are
filled in automatically and can be omitted.

## Topography (ground elevation)

| Parameter | Default | Meaning |
|---|---|---|
| f_ztype | 0 | 0: fixed value z0, 1: file fn_z |
| z0 | 0 | fixed ground elevation (m) |
| fn_z | "" | ground elevation distribution file |
| mag_z | 1 | multiplier applied to the ground elevation (for sensitivity experiments and unit conversion) |
| f_user_routine | "" | identifier of a user routine that modifies the topography (for idealized experiments; [Part I](../users_guide.md#user-routines)) |

## Roughness (Manning coefficient)

| Parameter | Default | Meaning |
|---|---|---|
| f_rntype | 0 | 0: fixed value rn0, 1: file fn_rn |
| rn0 | 0.015 | fixed roughness value |
| fn_rn | "" | roughness distribution file |

Roughness is given directly (a fixed value or a distribution file). To
change the roughness on channel cells only, you do not need to build an
fn_rn distribution -- `rn0_rw` (below) can override it. To derive a
roughness distribution from land-use codes, map the values in
preprocessing (GIS etc.) to create the file and supply it with
`f_rntype = 1` (the in-model conversion f_rntype=2 has been removed --
developer.md Sec. 41).

## Domain mask (restricting the computed area)

| Parameter | Default | Meaning |
|---|---|---|
| f_masktype | 0 | 0: compute the whole domain, 1: file fn_mask, 2: auto-generate from the sea mask |
| fn_mask | "" | domain mask file (1: computed, 0: excluded) |

Cells outside the mask are **completely excluded from the computation
and consume neither memory nor CPU time** (check `number of valid
cells` on the screen). For wide-area runs clipped along the catchment
boundary this directly affects memory and speed, so setting a mask is
recommended for real terrain. f_masktype=2 is a shortcut that
auto-generates the mask from the sea mask (below): it keeps all land
cells plus only the one-cell-wide strip of sea adjacent to land,
excluding the wide offshore sea from the computation.

## Sea mask and channel mask

| Parameter | Default | Meaning |
|---|---|---|
| fn_sw | "" | sea mask (1: sea). Marks the sea area for tide, storm surge, and tsunami computations ([tide chapter](tide.md)) |
| fn_rw | "" | channel mask (1: channel cell) |
| depth_rw / fn_depth_rw | 0 / "" | incision depth of channel cells (uniform value / distribution; dug down from the topography) |
| rn0_rw | -1 | fixed roughness of channel cells. A positive value **overrides the roughness of channel cells** regardless of how roughness is given (rn0 / file), independently of whether incision is specified |

The channel mask is a shortcut for representing channels that are not
resolved at the resolution of the topography data, by incising the
terrain and replacing the roughness. More refined subgrid channels
(cross-section shape, channel width, levees) can be introduced step by
step via fn_channel ([channel chapter](channel.md)).

Masks are created in preprocessing. If land-use data is available, the
bundled `utils/lu2mask` can generate a 0/1 raster in which "cells of the
specified land-use codes are 1" (intended for the sea mask and the
seaside mask; see the source header for usage). After generation,
inspect the result visually in GIS etc. and edit it where needed (e.g.
treat a lake without an outflowing river as sea so that it acts as a
drainage target). For the channel mask, generation from land-use codes
that include lakes and floodplains does not give sufficient quality, so
rasterizing river centerlines in GIS is recommended (background:
developer.md Sec. 40).

## Drag of building clusters (urban inundation)

| Parameter | Default | Meaning |
|---|---|---|
| fn_gv | "" | distribution of the building void fraction (fraction not covered by buildings) |
| fn_bb | "" | distribution of the mean building size (m) |
| min_gv / min_bb | 0.001 | lower limit of each (to avoid division by zero) |

Represents the storage reduction and the drag caused by building
clusters in urban areas (numerical constants such as the drag
coefficient are on the &list_sysparam side -- [shallow water flow
chapter](swflow.md)).

## Ponds

| Parameter | Default | Meaning |
|---|---|---|
| fn_rscap | "" | distribution of the pond storage limit depth (m) (cells with a value are ponds) |

Gives cells a storage separate from the surface water, used e.g. as an
intake source for pumps ([structures chapter](structure.md)). The pond
water depth can be output as `Hrs0001` with `f_out_hrs = 1`.

## Soil layer (for groundwater computation)

| Parameter | Default | Meaning |
|---|---|---|
| f_sdtype | 0 | 0: fixed value sd0, 1: file fn_sd |
| sd0 / fn_sd | 0 / "" | soil depth (m) (uniform value / distribution) |
| sy0 | 0.2 | specific yield (effective porosity) |

Read -- and memory allocated -- only when a groundwater model that
requires the soil depth (Green-Ampt, lateral flow) is selected
([groundwater chapter](gwflow.md)).

## Seawall

| Parameter | Default | Meaning |
|---|---|---|
| fn_seaside | "" | seaside mask (1: treated as the sea side; the sea of fn_sw is always seaside) |
| fn_seawall / seawall0 | "" / -9999 | crest height distribution (at landside cell positions) / uniform value (mutually exclusive; the uniform value is assigned automatically to every land cell adjacent to the sea side = a wall along the entire coastline) |
| f_seawall_datum | 2 | crest height datum (1: height above the cell's own ground, 2: absolute elevation) |
| f_seawall_mode | 0 | hydraulic mode (0: overtopping only, 1: flap gate (gates), 2: forced drainage) |

Represents seawalls as line-shaped virtual walls without widening cells
(the coastal application of the same mechanism as river levees,
fn_bank). In tide cases fn_seaside can be omitted (it is derived
automatically from the sea area), but **for cases where waves enter
through the boundary, such as tsunamis, fn_seaside is mandatory**.

Notes when giving the crest with a distribution file `fn_seawall`:

- The crest is given at **land-side (protected-side) cell** positions.
  This is the opposite of river levees, fn_bank (held by the channel =
  water-side cells): in cases like tsunamis where the sea is solved as
  ordinary cells, the "water side" cannot be determined by a static
  mask (the design record is developer.md §17.1).
- Wall edges are erected on all edges (**including diagonals**) between
  a crest-holding land cell and a seaside cell. **Also give a crest to
  land cells that touch seaside cells only at a corner (diagonally)** —
  edges of cells without a value get no wall and water leaks inland
  through the diagonal links. The uniform value `seawall0` is assigned
  automatically to every land cell adjacent (including diagonally) to
  the seaside, so this is not a concern.

## Examples and constraints

- Annotated list of all parameters: [examples/List_samples/list_geoinfo.txt](../../../examples/List_samples/en/list_geoinfo.txt)
- Minimal configuration: [tutorials/wave](../../../tutorials/wave/en/README.md) (grid only + a user routine)
- Real terrain: [examples/chichibu](../../../examples/chichibu/), [examples/abukuma](../../../examples/abukuma/)
- For the format and coordinate system of distribution files, see the [input/output](io.md) and [coordinates](coordinates.md) chapters.
- Subgrid channel elements such as channel width and levees are configured on the fn_channel side ([channel chapter](channel.md)).
