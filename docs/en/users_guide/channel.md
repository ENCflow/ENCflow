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

## Just try it (minimal input)

A channel runs as a "resolved channel" with only the channel mask fn_rw
and the incision depth_rw of the [geographic information](geoinfo.md)
(fn_channel is not needed). The minimal input that adds levees is one
line with a uniform height:

```
&list_channel
  bank0 = 2.0                   ! levee height above the landside cell elevation (m)
/
```

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
  The effective crest of each edge never falls below the landside
  ground or the channel bed (where the crest is lower, the ground itself
  is the wall, so the ground difference is never added to the overflow
  head; this matters on natural banks in V-shaped valleys and when the
  crest is given as an absolute elevation).
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
| f_bank_opening | 1 | opening correction that reallocates the passage width of openings blocked by levee walls to the open channel-channel edges of the same cross-section. In an axis-aligned one-cell channel the blocked diagonal openings go to the normal edge; in a diagonal (8-connected) one-cell channel the blocked axis openings go to the diagonal edge. Either way the passage width becomes the natural width of the cell (axis: the cell width, diagonal: cell area / diagonal path length = 0.707 cell width), so the under-conveyance of one-cell channels is corrected regardless of orientation (0 is for comparison with the old behavior) |

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

- If no levee is specified, the channel has **no wall (natural banks)**:
  the exchange between the channel and the hillslopes stays the ordinary
  shallow-water computation, and the conveyance of blocked diagonal
  openings is corrected dynamically by f_opening_dynamic (on by default;
  see [Shallow water flow computation](swflow.md)). For embanked rivers
  specify bank0 / fn_bank explicitly (the former automatic zero-height
  levee has been dropped: on natural banks whose hillslope is above the
  crest its weir overflow became a drop flow and diverged).
- Where the channel reaches the domain edge, the free-outflow and
  long-wave-radiation boundary faces are scaled to the channel width
  (the boundary cannot drain the small storage of a narrow channel).
  Inflow segments deliver the prescribed discharge as before.
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
- **Accuracy limit (connectivity ambiguity)**: the channel is
  represented as a raster (channel mask + width), and channel cells are
  connected by the implicit rule "adjacent cells are connected". Unlike
  one-dimensional channel-network models, which hold the connectivity
  between reaches explicitly, the correspondence at confluences and
  bifurcations, and the separation of nearby parallel channels, cannot
  be specified exactly, so unintended connections or breaks can occur.
  Where the topology of the river network (what flows into what)
  dominates the result, this ambiguity limits the accuracy. Refine the
  cell size around suspect locations so that connections and
  separations are resolved.

## Cross-section shape (sigma law)

A generalization of the cross-section shape that improves the
reproduction of water level drawdown and recession in the low-water
channel.

```
  p_sect_m = 0.5                ! shape exponent of the section (default 0 = rectangular)
```

A one-parameter cross-section shape with the conveyance ratio
sigma(h) = (h/D)^m; m = 0 corresponds to the conventional rectangle,
0.5 to a roughly parabolic, and 1 to a roughly triangular section. Here
D is the transition depth, which is not specified directly: on cells
with an active levee it is "crest - bed" (with f_bank_datum=1, bank0 +
landside elevation - bed; bank0 + depth_rw when the channel cell and
the landside have the same ground level), and on cells without a levee
the incision depth depth_rw is D itself (with neither, p_sect_m > 0 is
an error); at h >= D
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

## Recommended values by pattern

| Type | Configuration | depth_rw (m) | bank0 (m) | rn0_rw | Width / section | Notes |
|---|---|---|---|---|---|---|
| Mountain stream (width < cell) | fn_rw + fn_width + p_sect_m | 0.5-1 | not needed (no wall = natural banks) | 0.04-0.06 | width 2-10 m, m 0.5 | Not for streams meandering within one cell |
| Small / medium river (width 10-50 m, cell 10-25 m) | fn_rw + depth_rw + bank0 | 1-3 | 1-3 (f_bank_datum=1) | 0.03-0.04 | fn_width not needed when width >= cell | Overtopping by the Honma formula |
| Large river (width > 100 m) | resolved channel + levees | 3-6 | 3-8 | 0.025-0.035 | p_sect_m 0.3-0.5 for low-water recession | Floodplain roughness via fn_rn |
| Urban incised channel, concrete flume | fn_rw + depth_rw | 2-4 | none | 0.015-0.025 | - | Sluice gates and pumping stations are [structures](structure.md) |
| Breach scenario | the above + &list_channel_breach | as above | as above | as above | - | br_series ramps to a remaining ratio of 0 over 10-30 min |

Roughness guides are the customary Manning n values (Japanese river
technical standards; Chow 1959): concrete 0.015-0.02, sand-bed low-water
channel 0.025-0.035, gravel bed 0.035-0.05, vegetated floodplain 0.05-0.1.

**When one run spans several channel types, from mountain streams to the
river mouth**, you do not have to pick a single value from the table.
rn0_rw, depth_rw and bank0 are shortcuts that give every channel cell the
same value, so for large-scale runs with mixed types leave rn0_rw
unspecified (negative) and put the per-cell n of the channel cells into
the roughness distribution fn_rn (f_rntype=1) of the
[geographic information](geoinfo.md) (likewise fn_depth_rw and fn_bank
distributions for the incision and the levee height). Painting the
table values reach by reach in GIS preprocessing is the way the policy
"conversions belong to preprocessing" intends.

**Guide for the cross-section shape sigma (p_sect_m)** - sets the
conveyance ratio sigma = (h/D)^m at depths below the transition depth D.
The larger m, the higher the low-water level and the slower the
recession. D is not a value you specify directly: on cells with an
active levee it is "crest - bed" (about bank0 + depth_rw), and on cells
without a levee depth_rw is D itself. The column "Settings that set D"
gives the combination of depth_rw ([geographic information](geoinfo.md))
and bank0 (this chapter) that realizes that D.

| Channel type | p_sect_m | Settings that set D | Notes |
|---|---|---|---|
| Concrete flume, rectangular section | 0 (default) | - | The conventional rectangle (D is not used) |
| Large compound-section river (low-water channel + floodplain) | 0.3-0.5 | With levees: bank0 + depth_rw of 3-8 m (e.g. bank0 3 + depth_rw 3) | Larger when the low-water channel is narrow relative to the full width |
| Single-section natural channel (gentle sand/gravel bed) | 0.5 | No levee: depth_rw 1-3 m is D itself | Parabolic. Works in the simplest configuration without width data |
| V-shaped mountain stream, steep gorge | 0.7-1 | No levee: depth_rw 0.5-1 m is D itself | Triangular. Combine with fn_width to narrow the thalweg |
| Calibrating low-water levels to observations | sweep 0.3-1 | unchanged | If the base-flow level is too high, raise m (smaller sigma raises the level for the same discharge) |

## Examples and related topics

- Format samples: [examples/List_samples/list_channel.txt](../../../examples/List_samples/en/list_channel.txt)
- Seawalls (fn_seawall) are the coastal application of the same
  virtual-wall mechanism, configured in the [geographic information
  chapter](geoinfo.md).
- To treat sluice pipes and sluice gates rigorously as conduits
  (section, invert elevation, gate), use the culverts of the
  [structures chapter](structure.md) (the check valve of f_bank_mode=1
  is the shortcut).
