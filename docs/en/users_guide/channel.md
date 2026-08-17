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

Notes when giving the height with a distribution file `fn_bank`:

- The height is given at **channel-cell** positions (wall edges are
  erected on all edges — **including diagonals** — between channel
  cells and landside cells, and the crest uses the channel-side cell's
  value). Beware that this is the opposite of the coastal seawall
  `fn_seawall`, which is held by the land-side cells
  ([geographic information chapter](geoinfo.md)).
- **Also give a height to channel cells that touch landside cells only
  at a corner (diagonally)**. Edges of a channel cell without a value
  (−900 or below) get no wall, and since the ENC grid exchanges water
  through diagonal links too, water leaks to the landside there. The
  uniform value `bank0` is assigned to every channel cell, so this is
  not a concern.
- Conversely, **giving extra values is harmless**. Values on channel
  cells not adjacent to the landside are never used (no wall is
  erected), and values on non-channel cells are ignored. Painting a
  **generous buffer along the channel** is therefore the safe side,
  and it automatically prevents the corner-contact leaks above.

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

**Key premise of the model (important)**: once the width is active,
the physical quantities and state variables of that cell (depth, water
level, discharge, storage) represent **only the channel portion of the
cell**. The landside (non-channel) portion of that cell is treated as
nonexistent, and the water exchange between the channel and the
landside (overtopping inundation and return flow) takes place
**directly with the adjacent landside cells**. This design differs
from models like RRI that carry two water levels (slope and channel)
per cell: it **cannot represent storage or inundation of the landside
portion within the cell**, and in exchange there is no model switching
as the river width crosses the cell size, so **a single formulation
solves seamlessly from the thin uppermost streams to the large
downstream river** (the record of this decision is developer.md §18).
The inundation area is resolved at cell granularity; where you need to
resolve flooding inside the channel cell itself, make the cell size
finer than the river width and move to a resolved channel.

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
- In that regime **the width value itself does not affect the
  results**. The width is only ever used as a coefficient of the form
  "min(width / cell dimension, 1)", so any value beyond the cell size
  -- the real river width or a convenience value like 9999 -- gives
  strictly identical results and is harmless. Feel free to paint
  reaches you want treated as resolved with a single large value
  (strictly speaking, only the cells at the upstream/downstream ends
  of a channel need twice the cell size to saturate the plan-area
  fraction, so to be certain use at least 2x the cell size, e.g.
  9999).
- **Exception: when combined with the cross-section shape sigma
  (p_sect_m > 0)**, the effective width at low flow depends on the
  actual value as "width x sigma(h)", so "any large value is the same"
  does not strictly hold (though even an overstated width remains
  interpretable and does not break the model badly -- see the note in
  the cross-section section below).
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

The channel width (fn_width) is not required for using sigma. **On
cells without a width, sigma is applied to a section of the full cell
width (= the cell size)**. Enabling sigma alone, without preparing any
width data, is the simplest configuration.

**Inaccurate channel widths do not break the model badly**. With sigma
active, the low-flow regime depends on the width value through the
effective width = width x sigma(h); but even when the width is
overstated (e.g., set to the cell size or a uniform convenience
value), the low-flow state admits an equivalent interpretation as a
multi-thread section -- many thin braided threads flowing across the
overly wide bed -- and at high flow (h >= D) the dynamics degenerate
to the rectangle, so the difference from the real width nearly
vanishes. In line with this program's policy that simple data should
just work, refining the width data gradually is enough -- start
refining to real widths in the reaches where the low-flow stage and
velocity matter.

The shape exponent m is currently a single domain-uniform value. It
is only natural that mountain streams upstream and the large river
downstream have different section shapes, so an extension to per-cell
specification via a distribution file is a candidate for the future,
to be considered when the need arises.

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
