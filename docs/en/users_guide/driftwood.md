# Driftwood (fn_driftwood)

[Back to the user's guide index](../users_guide.md)

Estimates the generation, transport and deposition of **driftwood**
carried by floods, inundation and debris flows, as a **raster field**
of wood volume per unit area (m³/m²) in each cell. It is not an
individual-log tracking model (discrete element type); the purpose is a
map-scale potential assessment of "which standing trees become
driftwood, and where and how much of it arrives and deposits".

Wood is represented by three ledgers: **standing stock `wst`, moving wood
`hd`, and deposited wood `wd`**. Only `hd` is advected conservatively with
water (or the water–sediment mixture in debris flow); `wst` and `wd` are
immobile. Deposited volume `wd` is not added to bed elevation `z`.

- **① Hydraulic recruitment (`wst → hd`)**: recruit at rate `dw_wrec`
  when `H > dw_hrec` and `V > dw_vrec`.
- **② Erosion entrainment (`wst → hd`)**: recruit all remaining stock
  when `zref − z > dw_droot`. `zref` is the reference elevation at
  initialization (the saved value on restart); `z` is the current elevation.
  This tests **net lowering from the reference**, not the accumulated sum
  of erosion increments. It has no depth or speed test and does not
  distinguish which process lowered `z`.
- **③ Stopping / deposition (`hd → wd`)**: transfer all `hd` in dry cells
  (`h ≤ dd`). Otherwise, deposit at rate `dw_wstop` when `H < hf` or
  `V < dw_vstop`, where `hf` is the representative log draft.
- **④ Refloating (`wd → hd`)**: only if `dw_wfloat > 0`, transfer at rate
  `dw_wfloat` when `H > dw_rfloat × hf` and `V > dw_vfloat`.
  The default rate of zero disables refloating.

Here `H = h + max(hs, 0)` and `V` is the cell speed. Distinguish the depth
`H` used for thresholds from the water-only dry-cell test `h ≤ dd`.
Without sediment, `H = h`. For each rate w (m³/m²/s) the transfer in one
step is capped by the remaining amount S of the source ledger,

```math
\Delta = \min\left(w\,\Delta t,\; S\right).
```

Recruitment also converts
the area basis from `wst` to `hd`, as described below.

The draft `hf` of the representative log is the buoyancy balance of a
horizontal cylinder of diameter D = `dw_dlog` and specific gravity
sg = `dw_sglog` (submerged area fraction = specific gravity)[^braudrick00].
With θ the central angle of the submerged segment,

```math
\frac{\theta - \sin\theta}{2\pi} = sg,\qquad
h_f = \frac{D}{2}\left(1 - \cos\frac{\theta}{2}\right),
```

so sg = 0.5 gives θ = π and h_f = D/2 (half submerged). In general
h_f ≠ sg·D (sg = 0.3 gives h_f ≈ 0.34 D).

Numbers identify paths in the figure. After advection and landform updates,
the local execution order is **② → ① → ③ → ④ → dam capture → period-maximum
update**. A cell passing the dry-cell test is still tested subsequently
for refloating in ④ if enabled, using the conditions on `H` and `V`.

![Three driftwood ledgers, transfer conditions, draft and volume accounting](../../figs/driftwood_ledgers_en.png)

(a) Immobile standing and deposited ledgers and the moving ledger carried
by the flow. The dashed bank is the reference bed; the solid line is the
current bed. Their elevation difference controls ②. (b) Conditions for
the four paths. (c) Draft `hf` is derived from `dw_dlog` and `dw_sglog` by
equating the submerged cross-sectional area fraction of a horizontal
cylinder to its specific gravity `sg`. The drawing shows half submergence
for `sg = 0.5`; in general, `hf` is not `sg × diameter`.
(d) Outputs and volume accounting with area conversion. The section, trees
and logs are illustrative, not computed results or individual trajectories.
Generate with `python docs/figs/make_guide_figs.py driftwood`.

## Enabling and configuration

Specify `fn_driftwood` in `&list_sysparam`.

**The minimum input to "just try moving driftwood" is an empty
`&list_driftwood`** (every item takes its default). A uniform standing
stock of 0.001 m³/m² is placed on land cells (the observed envelope of
generated driftwood in conifer torrents), and the log properties,
recruitment (both hydraulic washout and erosion entrainment) and
stopping run with their defaults. Adopted defaults are printed at
start-up as `driftwood: dw_hrec = 0.5000 m (default)`, so they cannot
go unnoticed; review them for your case (type-specific starting values
are in "Recommended values by pattern" at the end of this chapter; the
rationale is in developer.md §50.6, Japanese).

```
&list_driftwood
/
```

In practice give the stock map and the recruitment and stopping
parameters:

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
| dw_stock0 | (0.001 on land cells) | uniform standing stock (m³/m²). Exclusive with fn_dwstock. **With neither given, 0.001 m³/m² is placed uniformly on land (non-sea) cells** |
| fn_dwstock | — | standing stock map (m³/m², same matrix format as the terrain) |
| dw_dlog | 0.3 | representative log diameter (m). The default is the middle of the 0.2-0.4 m range of the manual's estimate "mean driftwood diameter ≈ mean DBH of the standing trees upstream"[^nilim904] |
| dw_sglog | 0.5 | wood specific gravity ρwood/ρwater (0 < sg < 1). The draft (buoyant depth) is derived automatically as the exact solution of the cylinder buoyancy balance above[^braudrick00] (sg=0.5 gives exactly half submergence = 0.5×dw_dlog). The default is a middle value for green wood (literature value) |
| dw_wrec | 1e-5 | hydraulic recruitment rate (m/s = m³/m²/s). Specifying it enables hydraulic recruitment. Thresholds and rate are calibration values without a practical standard (empirical; sensitivity analysis recommended) |
| dw_hrec | 0.5 | depth threshold of recruitment (m; tested with H = h + max(hs, 0)) |
| dw_vrec | 1.0 | velocity threshold of recruitment (m/s) |
| dw_droot | 0.5 | rooting depth (m). Specifying it enables erosion entrainment (all remaining stock when reference-to-current lowering zref − z > dw_droot). The default is a representative rooting depth relative to shallow-failure and channel-scour depths (empirical) |
| dw_wstop | 0.01 | grounding deposition rate (m/s) |
| dw_vstop | 0 | velocity threshold of slow-flow deposition (m/s; 0 = depth (draft) criterion only) |
| dw_wfloat | 0 | refloat rate (m/s; 0 = deposited wood never moves again (conservative)) |
| dw_rfloat | 1.5 | refloat buoyancy margin (refloat when H > rfloat×draft and V > dw_vfloat; must be > 1). On the stable side of the flume onset of motion at ≈ 1.2×draft[^braudrick00] |
| dw_vfloat | — | velocity threshold of refloat (m/s; required with dw_wfloat > 0; must be >= dw_vstop) |

For the two recruitment paths (dw_wrec / dw_droot), **both take their
defaults when neither is given (erosion entrainment never fires unless
the terrain moves, so it is harmless), and giving only one disables the
other** (explicit intent is respected). Giving dw_wrec without
dw_hrec / dw_vrec takes the default thresholds.

## Recommended values by pattern

The defaults are a middle ground that "runs". When the type of event is
known, start from the following (calibration quantities; practical values
from the manual[^nilim904], source readings in developer.md §50.4 and §50.5):

| Type | Recruitment | Stock and properties | Thresholds and rates | Stopping | Notes |
|---|---|---|---|---|---|
| Torrent debris flow with driftwood (sabo planning) | erosion entrainment (dw_droot 0.3-1.0 m) + hydraulic | conifer 1e-3, broadleaf 1e-4 m³/m² (observed envelopes); dw_dlog = mean DBH (0.2-0.4 m), sg 0.5 | dw_hrec 0.3-0.5 m, dw_vrec 1-2 m/s, dw_wrec 1e-5 | dw_wstop 0.01, dw_vstop 0.02-0.05 (stop at the slope break) | enable with f_debris; check with an outflow ratio of 0.8-0.9 |
| River flood through riparian forest / floodplain | hydraulic only | fn_dwstock on riparian strips (1e-3 to 1e-2); dlog 0.3, sg 0.5 | dw_hrec 1.0 m, dw_vrec 1.0-1.5 m/s, dw_wrec 1e-5 to 1e-4 | dw_wstop 0.01, dw_vstop 0.02 | add f_fluvial for root undercutting via erosion entrainment |
| Storm-surge log yard (Isewan-typhoon type) | hydraulic as "mooring loss" | 0.5 m³/m² on yard cells; dlog 0.6 (logs), sg 0.5 | dw_hrec = normal depth + 1 m, dw_vrec 0, dw_wrec 2e-4 (full release within the surge) | dw_wstop 0.005, dw_vstop 0.02 | example timberyard |
| Tsunami through coastal forest / log yard | as above | coastal forest 1e-3 to 1e-2, log yard 0.5-1.0 m³/m² | dw_hrec = normal depth + 1-2 m, dw_vrec 0, dw_wrec 5e-4 (within the surge) | dw_wstop 0.005, dw_vstop 0.05 | example tsunami_town (chain with house destruction) |
| Upper-bound reach (hazard map) | per case | as above | as above | dw_vstop 0, dw_wfloat 0 | use Wd9999; the remaining amount is sensitive to dw_vstop and dw_wfloat (timberyard README) |
| Trapping by works (two-case comparison) | per case | as above | as above | as above | difference of Wd9999 with and without dams, sand basins or culverts |

**Practical guidance** (from NILIM Technical Note No. 904[^nilim904], the
Japanese national sabo planning manual for debris flow and driftwood):

- **dw_dlog**: the manual estimates the mean driftwood diameter as
  roughly equal to the **mean diameter at breast height (DBH)** of the
  standing trees upstream — survey DBH values can be used directly.
- **Standing stock**: from the single-tree volume
  $`V_1 = \tfrac{\pi}{4} D_{bh}^2 H_t f_s`$ (D_bh breast-height diameter,
  H_t tree height, f_s form factor 0.3-0.7) and the tree density N
  (trees/m²), $`wst = N V_1`$, converted to m³/m² in preprocessing. Observed envelopes of generated driftwood volume in
  torrents are about 1,000 m³/km² (= 0.001 m³/m²) for conifer forests
  and about 100 m³/km² (= 0.0001 m³/m²) for broadleaf forests (a
  guide for uniform stock values and for sanity-checking magnitudes).
- **Validation metric**: the manual cites field evidence that, without
  countermeasure works, 80-90% of the generated driftwood reached the
  valley outlet (outflow ratio 0.8-0.9) — usable to check
  torrent-scale results.
- **Erosion entrainment (dw_droot)** follows the same idea as the
  manual's generation estimate (standing trees within the
  failure/debris-flow erosion area become driftwood).

Thresholds and rates of hydraulic recruitment (dw_wrec/hrec/vrec) are
calibration parameters (the manual has no depth/velocity washout
criterion, so no standard values exist — sensitivity analysis is
recommended). As guidance for refloat, flume experiments show that
logs parallel to the flow or with rootwads move at about 1.2 times
their buoyant depth, while logs oblique to the flow move below the
buoyant depth by pivoting[^braudrick00] (the default
dw_rfloat=1.5 is on the stable side).

## Outputs and volume accounting

| Switch | File | Content |
|---|---|---|
| f_out_hd | Hd0001… | Moving wood `hd` (m³/m² of effective area, at dt_file intervals) |
| f_out_wd | Wd0001… | Deposited wood `wd` (m³/m² of effective area) |
| f_out_wd | Wd9999 | Per-cell period maximum `maxₜ(hd + wd)` (m³/m² of effective area) |

`Wd9999` takes the maximum of instantaneous `hd + wd` after local
processes and dam capture. It is neither cumulative passage volume nor
the sum of separate maxima of `hd` and `wd` at different times.

`wst` is wood volume per **geometric cell area**; `hd` and `wd` use the
same **effective area** as water. With `A = dx × dy` and
`f = gv × wfrac` (`wfrac = 1` without specified channel widths),
the volume in the domain is

```math
Q = \sum_{i,j} A\left[wst_{i,j} + f_{i,j}(hd_{i,j}+wd_{i,j})\right].
```

Recruitment subtracts `Δw` from `wst` and adds `Δw / f` to `hd`.
The rate `dw_wrec` uses geometric area; `dw_wstop` and `dw_wfloat`
use effective area (m³/m²/s). A simple sum of `wst + hd + wd` represents
the volume budget only when the area factor equals one.

`result/driftwood.csv` is written at `dt_recrd` intervals. Columns
`rec_hyd_m3`, `rec_ero_m3`, `deposit_m3`, `refloat_m3` and `to_dam_m3` are
cumulative process volumes; `vol_stock_m3`, `vol_float_m3` and
`vol_deposit_m3` are current stocks.
All are converted to m³. In a closed domain without dam capture,
the sum of current stocks `Q` preserves the initial volume, apart from
numerical error. Account for outflow and dam capture separately.
Recruitment, deposition and refloating are internal transfers; adding
their cumulative values to current stocks would double count volume.

## Combinations and restrictions

- ENC grid only. Cannot be combined with morphological acceleration
  (morfac ≠ 1) — driftwood is an event-scale quantity.
- Free to combine with [sediment and landform change](geomorph.md)
  (enable together with f_debris for mixed debris-flow-and-driftwood
  surges). Hydraulic recruitment also works without geomorph. Erosion
  entrainment does not trigger unless z falls below the reference level
  by more than the rooting threshold.
- Floating wood entering a **dam capture zone** is trapped by the dam
  (releases carry no wood). **Culverts and pumps** transfer water only,
  so wood accumulates upstream of such works (= upper-bound estimate of
  trapping; usable for with/without two-case comparisons in the same
  manner as [representing sabo facilities](geomorph.md)).
- Save/restore preserves `hd`, `wd`, `wst` and `zref` in
  `driftwood.dat`. **The `Wd9999` maximum and cumulative process volumes
  in the CSV are not restored**. Combine the separate run segments when
  evaluating statistics and budgets over the complete period.

## Verification case

[test/driftwood](../../../test/driftwood/) checks volume conservation, transport and
deposition for both erosion entrainment and hydraulic recruitment, and compares
saved states from split and uninterrupted runs.

## Worked example: timber influx from a coastal log yard by storm surge

An idealized experiment of the Isewan-typhoon type — timber floating in
a coastal log storage yard is released by the storm-surge water-level
rise and carried into an urban area by the overtopping flow — is
included in [examples/timberyard](../../../examples/timberyard/)
(`python3 make_terrain.py && ./encflow param.txt`; about one minute).
Its [README](../../../examples/timberyard/README.md) (Japanese) explains
the key points of the setup (no sea mask for the log yard and harbor,
timber stock only in the yard cells via `fn_dwstock`, hydraulic
recruitment used as "mooring loss by the surge" with `dw_hrec` above
the normal yard depth, seawall and opening as terrain, buildings as
`fn_gv`), the results with figures and tables, how to use Wd9999 (the
per-cell period maximum of hd+wd) versus the final frame Wd9998, sensitivity
cases on the deposition parameters (`dw_vstop`, `dw_wfloat`), and the
postprocessing recipe for timber impact forces.

## What is not modeled

Trajectories, orientation and rotation of individual logs, geometric
jamming at bridge piers and slit dams (log length vs. opening width),
and impact forces are out of scope (an explicit limit of the raster
representation policy). To examine the **effect** of blockage, give it
as a scenario (narrowed openings or culverts) and compare two cases.
**Impact forces** are evaluated in postprocessing: the Japanese design
standard (NILIM No. 905[^nilim905] §4.3) applies the boulder impact formula with
the flow velocity and the maximum log diameter, so feeding ENCflow's
maximum velocity V9999 (or velocity frames) and the representative log
properties into that formula (or the FEMA P-646 log impact formula)
gives a standard-consistent impact-force map (worked through in the
example README above). Use F9999 (= u²h) for the fluid force of the
water itself.
Implementation details: developer.md §50 (Japanese).

## References

[^braudrick00]: Braudrick, C. A. and Grant, G. E. (2000): When do logs move in rivers? *Water Resour. Res.*, 36(2), 571–583. (flume experiments on draft and onset of motion)
[^nilim904]: NILIM (2016): Guidelines for sabo master planning (debris flow and driftwood), commentary. *NILIM Technical Note*, No. 904 (in Japanese; title translated). (practical values and generation mechanisms)
[^nilim905]: NILIM (2016): Technical standard for the design of debris-flow and driftwood countermeasures, commentary. *NILIM Technical Note*, No. 905 (in Japanese; title translated). (log impact force, §4.3)
