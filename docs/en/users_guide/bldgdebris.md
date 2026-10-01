# Building destruction and debris (fn_bldgdebris)

[Back to the user's guide index](../users_guide.md)

Estimates the **destruction of wooden houses** by tsunami, storm-surge
and flood inundation flows, and the transport and deposition of the
resulting **debris**, as a **raster field** of debris volume per unit
area (m³/m²) in each cell. It is not a structural-response model of
individual houses nor a trajectory model of individual debris pieces;
the purpose is a map-scale potential assessment of "which houses are
destroyed and how much, how far the debris reaches, and where it
remains". It is a separate module of the same type as
[Driftwood](driftwood.md); enabling both represents **house
destruction by flows carrying driftwood**.

Debris moves through three ledgers:

```
building stock wbs --destroy--> floating debris hbd --ground/slow--> deposit wbd
 (immobile input)              (advected with the flow)              (can refloat)
                 `--sinking part (bd_fsink)-----------------------------'
```

- **Destruction**: the building stock of cells where the criterion
  exceeds a threshold turns into debris at a specified rate. The
  criterion is either the **inundation depth** (`f_bdcrit=1`,
  corresponding to depth-based fragility functions used in practice)
  or the **load** (`f_bdcrit=2`, the momentum flux of the flow
  including driftwood and debris, (h + (1+s)·hs + sg_log·hd +
  sg_deb·hbd)·V², on the same basis as F9999). With the load
  criterion **floating driftwood hd and floating debris hbd add to the
  destructive force**, so the chain driftwood → destruction → debris →
  further destruction is represented within one time evolution.
- **Stopping**: debris deposits in cells where the depth falls below
  the draft (the buoyant depth from the cylinder buoyancy balance of
  the debris specific gravity and size, derived as for driftwood) or
  the flow becomes slow. In dry cells the whole amount deposits.
- **Transport**: floating debris is advected at the same velocity as
  the water (or the mixture when the debris-flow model is active).
- **Feedback to the void ratio** (`f_bdgv=1`, default): the building
  void ratio gv rises with the destroyed fraction, so the same water
  spreads over a larger area and the water level drops — destruction
  feeds back to the flow (volume is conserved exactly). `f_bdgv=0`
  gives one-way coupling (destroyed fraction and debris maps only, the
  flow is unchanged), so the effect of the feedback can be compared
  on the same case.

## Enabling and configuration

Specify `fn_bldgdebris` in `&list_sysparam`. The minimum configuration
is the building stock, the representative debris properties, and the
destruction and stopping parameters:

```
&list_bldgdebris
  fn_bdstock = 'bdstock.txt' ! building stock (m3/m2, destructible volume incl. wooden fraction)
  bd_dlog = 0.2             ! representative debris size (m)
  bd_sg = 0.5               ! apparent specific gravity of debris (0-1; draft derived automatically)
  f_bdcrit = 1              ! criterion (1: inundation depth, 2: load)
  bd_hcrit = 2.0            ! depth threshold (m)
  bd_wdes = 1.0e-4          ! destruction rate (m/s)
  bd_wstop = 0.01           ! grounding deposition rate (m/s)
/
```

## Parameters

| Parameter | Default | Meaning |
|---|---|---|
| f_bd | 1 | 0 disables temporarily while keeping the file |
| bd_stock0 | — | uniform building stock (m³/m²). Exclusive with fn_bdstock; one of them is **required** |
| fn_bdstock | — | building stock (destructible volume) map (m³/m², same matrix format as the terrain). Fold the wooden fraction into it (a cell with 30% wooden houses gets 30% of a fully wooden cell) |
| fn_bdfrac | — | map of the destructible share fw (0-1) of the building footprint. Default 1. Where RC or tsunami-resistant structures remain, it bounds the void-ratio feedback at gv0 + (1−gv0)·fw |
| bd_dlog | — | representative debris size (m). **Required** |
| bd_sg | — | apparent specific gravity of debris (0-1). **Required**. The draft is the exact cylinder buoyancy solution as for driftwood |
| f_bdcrit | 1 | criterion: 1 = inundation depth h+hs, 2 = load (h+(1+s)hs+sg_log·hd+sg_deb·hbd)·V² |
| bd_hcrit | — | depth threshold (m; required for f_bdcrit=1) |
| bd_hcrit2 | none | second depth threshold (m; optional. A linear destructible fraction, 0 at threshold 1 and 1 at threshold 2, multiplies the rate = approximation of the fragility-curve width) |
| bd_fcrit | — | load threshold (m³/s²; required for f_bdcrit=2) |
| bd_fcrit2 | none | second load threshold (m³/s²; optional, ditto) |
| bd_wdes | — | destruction rate (m/s = m³/m²/s). **Required**. Time to destroy = stock ÷ rate |
| bd_fsink | 0 | sinking fraction (0-1): this share of the destroyed amount deposits on the spot (abstraction of sinking debris such as tiles and foundations; 0 = all floats = upper bound of reach) |
| bd_wstop | — | grounding deposition rate (m/s). **Required** |
| bd_vstop | 0 | velocity threshold of slow-flow deposition (m/s; 0 = depth (draft) criterion only) |
| bd_wfloat | 0 | refloat rate (m/s; 0 = deposited debris never moves again (conservative)) |
| bd_rfloat | 1.5 | refloat buoyancy margin (refloat when depth > rfloat×draft; must be > 1) |
| bd_vfloat | — | velocity threshold of refloat (m/s; required with bd_wfloat > 0; must be >= bd_vstop) |
| f_bdgv | 1 | 1 = raise the void ratio with the destroyed fraction (feedback), 0 = one-way coupling |

**Guidance on thresholds** (all calibration parameters; the literature
check is recorded in developer.md §63.7, Japanese):

- **Depth threshold (f_bdcrit=1)**: Shuto (1993) relates tsunami
  intensity to house damage: wooden houses are destroyed above about
  2 m of inundation depth and partially damaged around 1 m. The
  fragility functions of the 2011 Tohoku tsunami (Suppasri et al.
  2013, by structural type and storeys) also show the washout
  probability of wooden houses rising steeply around 2 m and most
  houses washed away above 4 m. Since fragility functions are
  probability curves while this module uses a threshold plus rate (or
  a two-threshold linear ramp), read "the median of the curve as the
  midpoint of bd_hcrit to bd_hcrit2, and the width of the curve as the
  ramp width" (the example uses 1.0-3.0 m). RC buildings are far less
  likely to be washed away at the same depth, which is why the stock
  (wooden fraction) and fn_bdfrac represent them.
- **Load threshold (f_bdcrit=2)**: the unit is that of F9999, m³/s²
  (freshwater-normalised; ×ρw gives N/m). Convert it from the
  force-based fragility functions of Koshimura et al. (2009),
  F = ½ρ C_D u²h, or compare the water-only F9999 map with observed
  damage. FEMA P-646 multiplies the hydrodynamic force of a
  debris-laden flow by a factor k_s (1.25 recommended); this module
  computes the same effect from the floating-matter columns (the
  driftwood and debris terms). These terms are "the average
  destructive force of a flow carrying floating matter", not a
  replacement of the impact or damming load of individual logs and
  debris (NILIM No. 905 §4.3, the individual loads of FEMA P-646).
- **Building stock**: floor area × structural volume per floor area ×
  wooden fraction, aggregated per cell (aggregation from building
  inventories is preprocessing). Conversion to building counts or
  monetary values is postprocessing.

## Output

| Switch | File | Contents |
|---|---|---|
| f_out_hbd | Bf0001… | floating debris volume (m³/m²) distribution (dt_file interval) |
| f_out_wbd | Bd0001… | deposited debris (m³/m²) distribution |
| f_out_wbd | Bd9999 | **maximum arrival over the run** max(floating+deposited) — the debris hazard map |
| f_out_bds | Bs0001… | destroyed fraction 1 − remaining stock/initial stock (0-1). The final frame is the damage-ratio map |
| f_out_fdmax | Fd9999 | maximum fluid force including driftwood and debris (h+(1+s)hs+sg_log·hd+sg_deb·hbd)·V² (the existing F9999 keeps its water-and-sediment definition) |

`result/bldgdebris.csv` records the volume ledger (cumulative
destruction (floating and sinking), deposition, refloat and dam
trapping, and current storages) at dt_recrd intervals. In a closed
domain the sum stock+floating+deposit matches the initial total stock
to machine precision. Convert to volume as column × gv × cell area
(volume is conserved even in cells whose void ratio changes).

## Combinations and restrictions

- ENC grid only. Cannot be combined with morphological acceleration
  (morfac ≠ 1).
- Free to combine with [Driftwood](driftwood.md); with the load
  criterion (f_bdcrit=2) floating driftwood counts towards the
  destructive force. The driftwood module does not know about debris
  (one-way). Also compatible with
  [sediment and landform change](geomorph.md) and groundwater.
- With the **void-ratio feedback** (f_bdgv=1) the water depth of a
  destroyed cell shrinks under volume conservation (h × gv unchanged);
  subsurface storages are untouched. The mean building size bb is not
  changed (a fully destroyed cell switches automatically to the
  "no buildings" treatment at void ratio 1).
- Floating debris entering a **dam capture zone** is trapped by the
  dam. **Culverts and pumps** transfer water only, so debris
  accumulates upstream of such works.
- On save/restore all debris ledgers and the modified void ratio are
  stored in `bldgdebris.dat`, so a split run continues exactly.

## Worked example: tsunami run-up into a town with house destruction and debris

An idealized experiment of a tsunami running up into a coastal town,
destroying wooden houses and carrying debris inland, is included in
[examples/tsunami_town](../../examples/tsunami_town/) (comparisons
without/with driftwood, depth/load criterion, and feedback on/off;
explained in its README, in Japanese).

## What is not modeled

Structural response of individual houses, trajectories, orientation,
rotation and interaction of individual debris pieces, individual
impact forces of debris and logs, geometric blockage by debris, fire,
and the conversion of deposited debris into terrain or re-closure of
the void space are out of scope (an explicit limit of the raster
representation policy). RC and steel structures are represented as
"non-destructible occupation" through fn_bdfrac; per-structure-type
thresholds (multi-class) are a future topic. Implementation details:
developer.md §63 (Japanese).
