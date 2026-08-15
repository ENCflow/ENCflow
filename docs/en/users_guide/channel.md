# Channels (&list_channel / channel_breach)

> English mirror of docs/users_guide/channel.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the user's guide index](../users_guide.md)

Handles the hydraulic structure of channels that cannot be resolved at
the cell size -- levees, subgrid channel width, cross-section shape,
and breach. Enabled via `fn_channel`.

**Prerequisites and division of roles**: designating channel cells (the
channel mask `fn_rw`), and the cell topography and properties (bed
incision `depth_rw`, channel roughness `rn0_rw`) are settings of the
[geographic information chapter](geoinfo.md). This chapter covers the
**conveyance structure** between cells (levees = virtual walls, channel
width, hydraulic modes). Specifying levees requires fn_rw.

## Levees (virtual walls)

Erects a virtual wall, without widening cells, on the boundary between
channel cells and landside cells. Whatever exceeds the crest spills to
the landside as weir overtopping by the Honma formula.

```
&list_channel
  bank0 = 1.0                   ! uniform levee height (mutually exclusive with fn_bank)
  f_bank_datum = 1              ! datum of the height (table below)
/
```

| Parameter | Default | Meaning |
|---|---|---|
| fn_bank / bank0 | "" / -- | levee height (distribution / uniform value; one or the other. In the distribution, -900 or below means no levee) |
| f_bank_datum | 1 | datum of the height. 0: bed (after incision), 1: landside cell elevation (recommended), 2: absolute elevation |
| f_bank_aggr | 0 | aggregation of the crest for datum=1. 0: mean of the adjacent landside cells (noise suppression), 1: minimum (faithful to overtopping onset), 2: maximum (conservative) |
| f_bank_mode | 0 | hydraulic mode. 0: overtopping only (impermeable up to the crest in both directions), 1: sluice gate (check valve; passes landside -> channel only), 2: forced drainage (for compatibility and experiments; for real-world pumping stations use the pumps of the [structures chapter](structure.md)) |
| f_bank_opening | 1 | opening correction that reallocates the passage width of diagonal openings to the channel's normal edges (corrects the under-conveyance of one-cell-wide channels; 0 is for comparison with the old behavior) |

## Subgrid channel width

Represents the conveyance and storage of rivers narrower than the cell
size as a subgrid channel of rectangular cross section. Enabled by
specifying `fn_width`.

```
  fn_width = "channel_width.txt"  ! channel width distribution (m; effective on channel cells only.
                                  !   0 or below means no width information = treated as resolved)
```

- If no levee is specified, a levee of "height 0, landside cell
  elevation datum" is enabled automatically (the formulation of the
  channel width presupposes combination with the wall).
- Cells whose width is at or above the cell size are automatically
  treated the same as a conventional resolved channel (incision +
  wall) -- a single width dataset connects the thin upstream streams to
  the large downstream river.
- `f_channel_advection = 0` drops the advection term on edges involving
  channel cells (a stabilization option under strong width
  heterogeneity; the default is 1 = normal).
- **Applicability**: use it at resolutions where the real channel runs
  more smoothly than the raster. Applying it to a small river that
  meanders within one cell underestimates the channel length and makes
  discharge and velocity too large.

## Cross-section shape (sigma law)

A generalization of the cross-section shape that improves the
reproduction of water level drawdown and recession in the low-water
channel.

```
  p_sect_m = 0.5                ! shape exponent of the section (default 0 = rectangular)
```

A one-parameter cross-section shape with the conveyance ratio
sigma(h) = (h/D)^m; m = 0 corresponds to the conventional rectangle,
0.5 to a roughly parabolic, and 1 to a roughly triangular section. The
transition depth D is "crest - bed" on levee-active cells, otherwise
the incision depth (with neither, p_sect_m > 0 is an error); at h >= D
it degenerates to the conventional rectangular dynamics.

## Breach (&list_channel_breach)

Lowers the effective crest of a levee along a time series to represent
a failure (levees must be enabled).

```
&list_channel_breach
  br_cell(:,1) = 120, 45, 120, 44   ! site 1: channel cell ic,jc and landside cell il,jl
  br_series(:,1,1) = 0.0,  1.0      ! (time min, remaining crest fraction 0-1)
  br_series(:,2,1) = 60.0, 1.0      !   no breach until 60 min
  br_series(:,3,1) = 70.0, 0.2      !   fails to 20% between 60 and 70 min
  br_series(:,4,1) = 90.0, 0.0      !   full failure down to the landside ground at 90 min
/
```

- A site is "a pair of adjacent channel and landside cells", and the
  crest of that single boundary edge varies as effective crest =
  landside ground elevation + fraction x (crest - landside ground
  elevation). Even on a one-cell-wide channel, the left and right banks
  are distinguished by which landside cell is specified. Cell
  coordinates are **1-based** (beware the 0-based numbering of GIS;
  [coordinates chapter](coordinates.md)).
- A failure spanning several cells is specified as multiple sites (the
  breach width is per edge).

## Examples and related topics

- Format samples: [examples/List_samples/list_channel.txt](../../../examples/List_samples/en/list_channel.txt)
- Seawalls (fn_seawall) are the coastal application of the same
  virtual-wall mechanism, configured in the [geographic information
  chapter](geoinfo.md).
- To treat sluice pipes and sluice gates rigorously as conduits
  (section, invert elevation, gate), use the culverts of the
  [structures chapter](structure.md) (the check valve of f_bank_mode=1
  is the shortcut).
