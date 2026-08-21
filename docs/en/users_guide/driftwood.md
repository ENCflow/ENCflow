# Driftwood (fn_driftwood)

[Back to the user's guide index](../users_guide.md)

Estimates the generation, transport and deposition of **driftwood**
carried by floods, inundation and debris flows, as a **raster field**
of wood volume per unit area (m³/m²) in each cell. It is not an
individual-log tracking model (discrete element type); the purpose is a
map-scale potential assessment of "which standing trees become
driftwood, and where and how much of it arrives and deposits".

Wood moves through three ledgers:

```
standing stock wst --recruit--> floating wood hd --ground/dry--> deposit wd
 (immobile input)   (a)(b)   (advected with the flow)      (can refloat)
```

- **(a) Hydraulic recruitment**: standing trees in cells where the
  inundation depth and velocity exceed thresholds are washed out at a
  specified rate (driftwood generation in ordinary floods).
- **(b) Erosion entrainment**: when the cumulative erosion depth of a
  cell exceeds the rooting depth, its standing trees are washed out
  entirely, roots and all. Erosion from any process of
  [sediment and landform change](geomorph.md) — bedload, debris flow or
  slope failure — couples automatically (no extra setting).
- **Stopping**: wood deposits in cells where the water depth falls
  below the draft (the buoyant depth from the buoyancy balance of a
  cylinder, determined by the wood specific gravity and diameter;
  Braudrick & Grant, 2000) or the flow becomes slow. In dry cells the
  whole amount deposits.
- **Transport**: floating wood is advected at the same velocity as the
  water (or the water-sediment mixture when the debris-flow model is
  active). **A mixed debris-flow-and-driftwood surge is represented
  simply by enabling f_debris and this feature together.**

## Enabling and configuration

Specify `fn_driftwood` in `&list_sysparam`. The minimum configuration
is the standing stock, the representative log properties, and the
recruitment and stopping parameters:

```
&list_driftwood
  dw_stock0 = 0.01          ! standing stock (m3/m2, uniform)
  dw_dlog = 0.3             ! representative log diameter (m)
  dw_sglog = 0.5            ! wood specific gravity (0-1; the draft is derived
                            !   automatically from the buoyancy balance)
  dw_wrec = 1.0e-5          ! hydraulic recruitment rate (m/s)
  dw_hrec = 0.5             ! depth threshold of recruitment (m)
  dw_vrec = 1.0             ! velocity threshold of recruitment (m/s)
  dw_droot = 0.5            ! rooting depth (m; erosion-entrainment threshold)
  dw_wstop = 0.01           ! grounding deposition rate (m/s)
/
```

## Parameters

| Parameter | Default | Meaning |
|---|---|---|
| f_dw | 1 | 0 disables temporarily while keeping the file |
| dw_stock0 | — | uniform standing stock (m³/m²). Exclusive with fn_dwstock; one of them is **required** |
| fn_dwstock | — | standing stock map (m³/m², same matrix format as the terrain) |
| dw_dlog | — | representative log diameter (m). **Required** |
| dw_sglog | — | wood specific gravity ρwood/ρwater (0-1). **Required**. The draft (buoyant depth) is derived automatically as the exact solution of the cylinder buoyancy balance (Braudrick & Grant, 2000; sg=0.5 gives exactly half submergence = 0.5×dw_dlog) |
| dw_wrec | none | hydraulic recruitment rate (m/s = m³/m²/s). Specifying it enables hydraulic recruitment |
| dw_hrec | — | depth threshold of recruitment (m; with debris flow the mixed flow depth h+sediment is used. Required with dw_wrec) |
| dw_vrec | — | velocity threshold of recruitment (m/s; ditto) |
| dw_droot | none | rooting depth (m). Specifying it enables erosion entrainment (full washout when cumulative erosion > dw_droot) |
| dw_wstop | — | grounding deposition rate (m/s). **Required** |
| dw_vstop | 0 | velocity threshold of slow-flow deposition (m/s; 0 = depth (draft) criterion only) |
| dw_wfloat | 0 | refloat rate (m/s; 0 = deposited wood never moves again (conservative)) |
| dw_rfloat | 1.5 | refloat buoyancy margin (refloat when depth > rfloat×draft; must be > 1) |
| dw_vfloat | — | velocity threshold of refloat (m/s; required with dw_wfloat > 0; must be >= dw_vstop) |

At least one recruitment path (dw_wrec / dw_droot) must be specified.
Convert forest inventory data into stock volume (m³/m²) in
preprocessing. Thresholds and rates are calibration parameters (no
established standard values — sensitivity analysis is recommended).
As guidance for refloat, flume experiments show that logs parallel to
the flow or with rootwads move at about 1.2 times their buoyant depth,
while logs oblique to the flow move below the buoyant depth by
pivoting (Braudrick & Grant, 2000 — the default dw_rfloat=1.5 is on
the stable side).

## Output

| Switch | File | Contents |
|---|---|---|
| f_out_hd | Hd0001… | floating wood volume (m³/m²) distribution (dt_file interval) |
| f_out_wd | Wd0001… | deposited wood (m³/m²) distribution |
| f_out_wd | Wd9999 | **maximum arrival over the run** max(floating+deposited) — the driftwood hazard map |

`result/driftwood.csv` records the volume ledger (cumulative
recruitment, deposition, refloat and dam trapping, and current
storages) at dt_recrd intervals. In a closed domain the sum
stock+floating+deposit matches the initial total stock to machine
precision (outflow and dam trapping are subtracted where present).

## Combinations and restrictions

- ENC grid only. Cannot be combined with morphological acceleration
  (morfac ≠ 1) — driftwood is an event-scale quantity.
- Free to combine with [sediment and landform change](geomorph.md)
  (enable together with f_debris for mixed debris-flow-and-driftwood
  surges). Works without geomorph too, using hydraulic recruitment only
  (erosion entrainment never fires when the terrain does not move).
- Floating wood entering a **dam capture zone** is trapped by the dam
  (releases carry no wood). **Culverts and pumps** transfer water only,
  so wood accumulates upstream of such works (= upper-bound estimate of
  trapping; usable for with/without two-case comparisons in the same
  manner as [representing sabo facilities](geomorph.md)).
- On save/restore all wood ledgers are stored in `driftwood.dat`, so a
  split run continues exactly.

## What is not modeled

Trajectories, orientation and rotation of individual logs, geometric
jamming at bridge piers and slit dams (log length vs. opening width),
and impact forces are out of scope (an explicit limit of the raster
representation policy). To examine the **effect** of blockage, give it
as a scenario (narrowed openings or culverts) and compare two cases.
Implementation details: developer.md §50 (Japanese). Reference for the
draft and movement thresholds: Braudrick, C. A. and Grant, G. E.
(2000), When do logs move in rivers?, Water Resources Research 36(2),
571-583.
