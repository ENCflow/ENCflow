# Channels explained (supplement to the channel chapter)

> English mirror of docs/users_guide/channel_models.md. The Japanese file is the master copy.

[Back to the channel chapter](channel.md) | [Back to the user's guide index](../users_guide.md)

This page gives the formulation, the design rationale and the basis of the
defaults for the mechanisms of the [channel chapter](channel.md): levees
(virtual walls), the subgrid channel width, the cross-section shape σ and
breaches. The weir formula is in
[Hydraulic laws of structures and boundaries](hydraulics.md) §1. The
implementation is in `src/m_swflow_enc_channel.f90` and
`src/m_swflow_enc.f90` (section shape, passage widths); the design history
is in developer.md §17, §18 and §26 (in Japanese).

## 1. Levees (virtual walls)

A virtual wall that does not widen the cells is erected on every edge
(diagonals included) between channel cells and landside cells. The crest
is set from the channel-side cell's value with the following datum.

| f_bank_datum | crest $`z_c`$ |
|---|---|
| 0 | bed (after incision) + height |
| 1 (default) | landside cell elevation + height; aggregated over the adjacent landside cells as the mean (f_bank_aggr = 0), minimum (1) or maximum (2) |
| 2 | absolute elevation |

The effective crest of each edge never falls below the landside ground
$`z_l`$ or the channel bed $`z_b`$:

```math
z_{c}^{\mathrm{eff}} = \max\!\left(z_c,\ z_l,\ z_b\right)
```

Where the crest is lower, the ground itself enters the ordinary
shallow-water computation as a step and no levee acts (`bank0 = 0` is the
same as no levee; this matters on natural banks in V-shaped valleys and
when the crest is given as an absolute elevation).

Whatever exceeds the crest spills to the landside as Honma weir
overtopping ([hydraulic laws](hydraulics.md) §1). When the levee is deeply
submerged (landside ponding far above the crest, a closed depression) the
submerged-weir discharge is capped so that one step closes at most half of
the level difference between the two sides. This prevents the inertialess
weir formula from reversing the flow direction every other step in deep
water; it has no effect on ordinary overtopping near the crest.

**Opening correction (f_bank_opening = 1).** The passage width of openings
blocked by levee walls is reallocated to the open channel–channel edges of
the same cross-section. In an axis-aligned one-cell channel the blocked
diagonal openings go to the normal edge; in a diagonal (8-connected)
one-cell channel the blocked axis openings go to the diagonal edge. Either
way the passage width becomes the natural width of the cell (axis: the
cell width; diagonal: cell area / diagonal path length = 0.707 cell width),
correcting the under-conveyance of one-cell channels regardless of
orientation; 0 is for comparison with the old behaviour (checked against
Manning uniform flow in the straight and diagonal channels of
[test/bendloss](../../../test/bendloss/)).

**Hydraulic mode (f_bank_mode).** 0 is overtopping only (impermeable up to
the crest in both directions), 1 a sluice gate (check valve; a shortcut
passing landside → channel only) and 2 forced drainage (for compatibility
and experiments). Real pumping stations and sluices use the pumps and
culverts of the [structures chapter](structure.md).

## 2. Subgrid channel width

On a cell with width $`W`$ the plan-area fraction

```math
f_w = \min\!\left(\frac{W}{\Delta},\ 1\right)
```

is used for storage (water volume of the cell = $`f_w\,\Delta^2 h`$) and as
the conveyance cap, and the depth, level and discharge represent only the
channel portion of the cell. The landside portion of the cell is treated
as nonexistent, and the exchange between channel and landside takes place
directly with the adjacent landside cells. This differs from models that
carry two water levels (slope and channel) per cell, such as RRI: it cannot
represent storage or inundation of the landside portion within the cell,
and in exchange there is no model switching as the river width crosses the
cell size, so a single formulation solves from the thin uppermost streams
to the large downstream river (developer.md §18). The inundation area is
resolved at cell granularity; where flooding inside the channel cell
itself must be resolved, make the cell size finer than the river width and
move to a resolved channel.

- **Natural banks and dynamic opening correction.** Without a levee the
  exchange between the channel and the hillslopes stays the ordinary
  shallow-water computation, and the conveyance of blocked diagonal
  openings is corrected dynamically by f_opening_dynamic (on by default;
  [ENC grid explained](encgrid.md)). The normalisation of the in-channel
  velocity (conveyance ratio) uses the same blocked fraction every step,
  so a cell adjacent to a dry, high hillslope gets the same velocity as
  with a wall. Do not combine natural banks with f_opening_dynamic = 0,
  which makes the velocity of channels narrower than the cell too small.
  The former automatic zero-height levee was dropped: on natural banks
  whose hillslope is above the crest its weir overflow became a drop flow
  and diverged.
- **Edge boundaries.** Where the channel reaches the domain edge, the
  free-outflow and long-wave-radiation faces are scaled to the channel
  width (the boundary cannot drain the small storage of a narrow channel).
  Inflow segments deliver the prescribed discharge as before.
- **Insensitivity to the width value.** The width is only ever used as
  $`\min(W/\Delta, 1)`$, so any value beyond the cell size gives strictly
  identical results. Strictly, only the cells at the upstream and
  downstream ends of a channel need twice the cell size to saturate the
  plan-area fraction, so paint reaches to be treated as resolved with at
  least 2 × the cell size (e.g. 9999). The same holds together with the
  section shape σ (σ acts on the fluxes and the stage through the
  rectangular-equivalent depth, and the width is used only for the
  plan-area fraction of storage and the conveyance cap; changed
  2026-10-04, before which the effective width was "width × σ(h)" and the
  actual width mattered at low flow).
- **Advection.** `f_channel_advection = 0` drops the advection term on
  edges involving channel cells (a stabilisation option under strong width
  heterogeneity; default 1).
- **Accuracy limits.** The channel is a raster (channel mask + width) and
  channel cells are connected by the implicit rule "adjacent cells are
  connected". Unlike one-dimensional channel-network models, which hold
  the connectivity between reaches explicitly, the correspondence at
  confluences and bifurcations and the separation of nearby parallel
  channels cannot be specified exactly, so unintended connections or
  breaks can occur. Where the topology of the river network dominates the
  result this limits the accuracy; refine the cell size at suspect
  locations. Applying the width to a small river that meanders within one
  cell underestimates the channel length and makes discharge and velocity
  too large.

## 3. Cross-section shape (sigma law)

A one-parameter cross-section shape with the conveyance ratio
$`\sigma(h) = (h/D)^m`$. The rectangular-equivalent depth $`v_h`$ (section
area ÷ width) is

```math
v_h = \int_0^h \sigma\,dh' =
\begin{cases}
\dfrac{D}{m+1}\left(\dfrac{h}{D}\right)^{m+1} & (h < D)\\[8pt]
h - \dfrac{m}{m+1}\,D & (h \ge D)
\end{cases}
```

The flux is velocity × section area (width × $`v_h`$) and the stage comes
from the inverse map from $`v_h`$ to $`h`$. $`m = 0`$ is the rectangle, 0.5
roughly parabolic and 1 roughly triangular; at $`h \ge D`$ the dynamics
degenerate to the rectangle.

**Transition depth D.** Not specified directly. On cells with an active
levee it is "crest − bed" (with f_bank_datum = 1, bank0 + landside
elevation − bed; bank0 + depth_rw when channel cell and landside have the
same ground level), and on cells without a levee the incision depth
depth_rw is D itself. When the bed moves (bedload of
[sediment and landform change](geomorph.md), for example) the crest (the
levee crest, or the initial bed + depth_rw) is fixed and D follows the
difference to the bed every step: bed lowering deepens the section (larger
bankfull capacity), deposition makes it shallower, and once filled to the
crest it returns to the rectangle. When D changes the stored volume is
preserved and only the depth is re-read.

**Inaccurate widths.** With σ active the width enters only the plan-area
fraction of storage and the conveyance cap. Even when the width is
overstated (the cell size or a uniform convenience value), the low-flow
state admits an equivalent interpretation as a multi-thread section (many
thin braided threads flowing across the overly wide bed), and at high flow
($`h \ge D`$) the dynamics degenerate to the rectangle, so the difference
from the real width nearly vanishes. Refining the width data gradually is
enough: start with the reaches where the low-flow stage and velocity
matter.

The shape exponent m is a single domain-uniform value. Mountain streams
upstream and the large river downstream naturally have different section
shapes, so an extension to per-cell specification via a distribution file
is a candidate for the future, to be considered when the need arises.

## 4. Breach

The crest of the single boundary edge of a site (a pair of adjacent channel
and landside cells) is lowered with the remaining fraction $`r(t)`$ (linear
interpolation of br_series):

```math
z_c^{\mathrm{eff}}(t) = z_l + r(t)\,\bigl(z_c - z_l\bigr)
```

with $`z_l`$ the landside ground elevation. A failure spanning several
cells is specified as several sites; the breach width is per edge.

## 5. Parameters and the basis of their defaults

| Parameter | Default | Meaning | Basis |
|---|---:|---|---|
| f_bank_datum | 1 | datum of the levee height | empirical; the landside-elevation datum is natural when building a levee-height map in GIS and rarely produces crests below the ground |
| f_bank_aggr | 0 | aggregation of the crest for datum = 1 | empirical; the mean of the adjacent landside cells suppresses DEM noise. 1 is faithful to the onset of overtopping, 2 conservative |
| f_bank_mode | 0 | hydraulic mode | overtopping only by default; the check valve (1) is a shortcut, real works are [structures](structure.md) |
| f_bank_opening | 1 | opening correction | verification case: one-cell straight and diagonal channels follow Manning uniform flow in [test/bendloss](../../../test/bendloss/) (§1) |
| p_sect_m | 0 | shape exponent of the section | rectangle by default (compatibility); the recommended 0.3–1 is empirical (table in the chapter) |
| f_channel_advection | 1 | advection term on edges involving channel cells | normal by default; 0 is for stabilisation under strong width heterogeneity |
| rn0_rw | — | channel roughness | customary Manning n values[^chow59] (concrete 0.015–0.02, sand bed 0.025–0.035, gravel bed 0.035–0.05, vegetated floodplain 0.05–0.1; the Japanese river technical standards give similar ranges) |

## 6. Verification cases

- [test/bendloss](../../../test/bendloss/): straight, bent and diagonal channels, subgrid width and opening correction, assessed against Manning uniform flow or a straight-channel comparison.
- [test/chichibu](../../../test/chichibu/): real-terrain examples comparing channel masks, roughness, width and levee settings through flood-wave behaviour.

## References

[^chow59]: Chow, V. T. (1959): *Open-Channel Hydraulics*. McGraw-Hill, New York. (tables of Manning's n)
