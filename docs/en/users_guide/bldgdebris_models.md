# Building destruction and debris models explained (supplement to the building destruction and debris chapter)

> English mirror of docs/users_guide/bldgdebris_models.md. The Japanese file is the master copy.

[Back to the building destruction and debris chapter](bldgdebris.md) | [Back to the user's guide index](../users_guide.md)

This page gives the destruction criterion and rate, the feedback to the
void ratio, the area bases and the volume budget, the correspondence of the
thresholds with the literature and the basis of the defaults for the
[building destruction and debris chapter](bldgdebris.md). The draft and the
basic transfer rules are shared with
[Driftwood models explained](driftwood_models.md). The implementation is in
`src/m_bldgdebris.f90`; the design history and literature checks are in
developer.md §63 (in Japanese).

## 1. Destruction criterion and rate

The criterion $`X`$ is the mixed flow depth $`H = h + \max(h_s, 0)`$ for
`f_bdcrit = 1` and, for `f_bdcrit = 2`, the freshwater-normalised fluid force
per unit width

```math
X = \bigl[h + (1 + s)\max(h_s, 0) + s_{g,\mathrm{log}}\,h_d + s_{g,\mathrm{bd}}\,h_{bd}\bigr]\,V^2
\quad [\mathrm{m^3/s^2}]
```

($`s`$: submerged specific gravity of the sediment, $`s_{g,\mathrm{log}}`$:
specific gravity of the wood; the wood term enters only when the driftwood
module is enabled). The load is the definition of the output Fd9999, while
F9999 keeps its water-and-sediment-only definition.

With the first threshold $`c_1`$ and the second $`c_2`$ the multiplier is

```math
a(X) = \min\left(1,\ \max\left(0,\ \frac{X - c_1}{c_2 - c_1}\right)\right)
```

zero at or below $`c_1`$, rising linearly between them and one at or above
$`c_2`$. Explicitly specifying only the first threshold disables the ramp:
the multiplier is one when $`X > c_1`$. The ramp is a piecewise-linear
approximation of the fragility functions in the literature (cumulative
washout probability against inundation depth[^suppasri13][^koshimura09]):
read the median of the curve as $`(c_1 + c_2)/2`$ and its width as
$`c_2 - c_1`$. The destroyed amount in one step is

```math
w = \min\left(w_{bs},\ \mathtt{bd\_wdes}\;a(X)\,\Delta t\right)
```

The "destructible fraction" is a rate multiplier, not a cap on cumulative
damage (sustained a = 0.5 keeps destroying the remaining stock at half the
rate). Of the destroyed amount $`w`$, the share bd_fsink deposits on the spot
into $`w_{bd}`$ and the rest enters $`h_{bd}`$; the sinking share can also
refloat under the refloat rule of $`w_{bd}`$ if enabled (there is no separate
permanently immobile ledger). The stopping and refloating conditions and
the cap on the rate transfers have the same form as in
[Driftwood models](driftwood_models.md) §1.

## 2. Feedback to the void ratio

The damage is $`d = 1 - w_{bs}/w_{bs0}`$ (zero where the initial stock
$`w_{bs0}`$ is zero). With `f_bdgv = 1` the void ratio is updated to

```math
g_v = g_{v0} + (1 - g_{v0})\,f_w\,d
```

where $`f_w`$ is the destructible share of the building footprint from
`fn_bdfrac` (default 1), which bounds the feedback. It differs from the ramp
multiplier $`a`$ and does not multiply the initial stock or the destruction
rate (fold the destructible volume and the wooden fraction into
`fn_bdstock` or `bd_stock0`). The update multiplies the effective-area
columns $`h`$, $`h_s`$, $`h_{bd}`$, $`w_{bd}`$ and others by
$`g_{v,\mathrm{old}}/g_{v,\mathrm{new}}`$ to conserve volume, so the depth
and water level drop before the next flow calculation. The local order is
load evaluation → ① destruction / feedback → ② stop → ③ refloat → dam
capture → maximum update; $`H`$ is evaluated at the start of the local
calculation and the dry-cell test uses the water depth $`h`$ at that point.

## 3. Area bases and volume budget

$`w_{bs}`$ is volume per geometric cell area, while $`h_{bd}`$ and $`w_{bd}`$
use the effective area. With $`A = \Delta x\,\Delta y`$ and
$`f = g_v\,w_{frac}`$ ($`w_{frac} = 1`$ without specified channel widths),
the volume in the domain is

```math
Q = \sum_{i,j} A\left[w_{bs,ij} + f_{ij}\,(h_{bd,ij} + w_{bd,ij})\right]
```

The destroyed amount $`w`$ is divided by $`f`$ when added to $`h_{bd}`$ or
$`w_{bd}`$. In a closed domain without dam capture the sum of the current
storages $`Q`$ conserves the initial volume (apart from numerical error).

## 4. Thresholds and the literature

- **Depth threshold (f_bdcrit = 1)**: Shuto[^shuto93] relates tsunami
  intensity to house damage: wooden houses are destroyed above about 2 m of
  inundation depth and partially damaged around 1 m. The fragility
  functions of the 2011 Tohoku tsunami (by structural type and
  storeys)[^suppasri13] also show the washout probability of wooden houses
  rising steeply around 2 m and most houses washed away above 4 m. Since
  fragility functions are probability curves while this module uses a
  threshold plus rate (or a two-threshold linear ramp), read "the median
  of the curve as the midpoint of bd_hcrit to bd_hcrit2, and the width of
  the curve as the ramp width" (the example uses 1.0–3.0 m). RC buildings
  are far less likely to be washed away at the same depth, which is why
  the stock (wooden fraction) and fn_bdfrac represent them.
- **Load threshold (f_bdcrit = 2)**: the unit is that of F9999, m³/s²
  (freshwater-normalised; × ρ_w gives N/m). Convert it from the
  force-based fragility functions[^koshimura09]
  $`F = \tfrac{1}{2}\rho C_D u^2 h`$ via $`X = hV^2 = F/(\tfrac{1}{2}\rho C_D)`$,
  or compare the water-only F9999 map with observed damage. FEMA
  P-646[^fema12] multiplies the hydrodynamic force of a debris-laden flow
  by a factor $`k_s`$ (1.25 recommended); this module computes the same
  effect from the floating-matter columns (the driftwood and debris terms).
  These terms are "the average destructive force of a flow carrying
  floating matter", not a replacement of the impact or damming load of
  individual logs and debris (NILIM No. 905[^nilim905] §4.3, the individual
  loads of FEMA P-646).

## 5. Parameters and the basis of their defaults

The labels in the Basis column are explained in [How to read the basis of a default](../users_guide.md#how-to-read-the-basis-of-a-default).

| Parameter | Default | Meaning | Basis |
|---|---:|---|---|
| building stock | 0.3 m³/m² (cells with buildings, gv < 1) | default when neither input is given | **empirical** footprint 0.4 × 1.5 storeys × structural volume of wooden houses (about 0.5 m³/m² of floor area). The run stops when gv is 1 everywhere so that an input is given |
| bd_dlog / bd_sg | 0.3 m / 0.5 | representative size and apparent specific gravity | **empirical** size class and specific gravity of wooden structural members; draft 0.15 m |
| bd_hcrit / bd_hcrit2 | 1.0 / 3.0 m | ramp of the depth threshold | **literature value** wooden houses destroyed above 2 m[^shuto93] as the median, with the width of the wooden washout curves[^suppasri13]. Both default when neither is given (ramp on); the first threshold alone means no ramp (explicit intent respected) |
| bd_fcrit / bd_fcrit2 | 2.0 / 6.0 m³/s² | ramp of the load threshold | **calibration** corresponds to $`hV^2`$ at 2 m depth and 1–1.7 m/s (convertible from the force-based curves[^koshimura09]); meant to be re-placed from the water-only F9999 map |
| bd_wdes | 5e-4 m/s | destruction rate | **empirical** the default stock of 0.3 m³/m² is destroyed in 10 min, the duration of one tsunami surge |
| bd_wstop | 0.01 m/s | grounding deposition rate | **empirical** same as driftwood |
| bd_vstop | 0.05 m/s | velocity threshold of slow-flow deposition | **empirical** debris in stagnant ponded water stays where it is (the value of the example). It differs from the driftwood default of 0 because urban debris left by stagnation is closer to reality |
| bd_fsink / bd_wfloat | 0 / 0 | sinking fraction and refloat | **empirical** all floating and no refloat = upper bound of reach (conservative) |
| f_bdgv | 1 | feedback to the void ratio | **method** returns the added storage and reduced drag of destroyed houses to the flow (§3) |

**Where to look when revising the defaults**

- The building stock can be replaced region by region from floor-area
  statistics (urban planning surveys, property registers) × the structural
  volume per floor area of wooden houses.
- Read the thresholds off the fragility literature (depth vs. collapse
  rate[^shuto93][^suppasri13], fluid force vs. damage rate[^koshimura09])
  for the house types of your area. For the force threshold, a practical
  way is to run water only once and place "the value where collapse
  starts" on the F9999 map.

Verification (developer.md §63.9): in [test/bldgdebris](../../../test/bldgdebris/)
an empty &list_bldgdebris with gv.txt and a configuration with every
default written explicitly give byte-identical saved states.

## 6. Verification cases

- [test/bldgdebris](../../../test/bldgdebris/): debris-volume conservation, one-way coupling with driftwood, water-volume conservation under void-ratio feedback, split-run continuation.
- [test/gvchange](../../../test/gvchange/): unit checks of the void-ratio update procedure.
- [examples/tsunami_town](../../../examples/tsunami_town/): tsunami run-up into a town (without/with driftwood, depth/load criterion, feedback on/off).

## References

[^shuto93]: Shuto, N. (1993): Tsunami intensity and disasters. In: Tinti, S. (ed.), *Tsunamis in the World*, Kluwer, 197–216. (tsunami intensity vs. house damage)
[^suppasri13]: Suppasri, A., Mas, E., Charvet, I., Gunasekera, R., Imai, K., Fukutani, Y., Abe, Y. and Imamura, F. (2013): Building damage characteristics based on surveyed data and fragility curves of the 2011 Great East Japan tsunami. *Nat. Hazards*, 66(2), 319–341.
[^koshimura09]: Koshimura, S., Oie, T., Yanagisawa, H. and Imamura, F. (2009): Developing fragility functions for tsunami damage estimation using numerical model and post-tsunami data from Banda Aceh, Indonesia. *Coastal Eng. J.*, 51(3), 243–273.
[^fema12]: FEMA (2012): Guidelines for Design of Structures for Vertical Evacuation from Tsunamis, Second Edition. *FEMA P-646*. (debris factor k_s and individual impact loads)
[^nilim905]: NILIM (2016): Technical standard for the design of debris-flow and driftwood countermeasures, commentary. *NILIM Technical Note*, No. 905 (in Japanese; title translated). (log impact force, §4.3)
