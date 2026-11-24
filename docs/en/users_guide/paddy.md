# Paddy-field dams (restricting the outlets of rice paddies; fn_paddy)

> English mirror of docs/users_guide/paddy.md. The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

A **paddy-field dam** (*tambo dam*) is a measure in which a plate that restricts the outflow (a hole or a
notch) is fitted to the outlet (drainage box) of a rice paddy, so that the water of a heavy rain is stored
for a while inside the levees and the peaks of the drains and rivers downstream are lowered[^maff2026]. This
feature puts the storage of paddy fields and the discharge laws of their outlets on the grid, so that you
can estimate how the runoff and the inundation change with the adoption ratio (the share of paddy fields
made into paddy-field dams), the type of device and the ponding before the rain.

The current version represents the paddy fields in a cell as **subgrid tanks** (see
[How it works](#how-it-works) below). The same formulas can be used from basin models of 100–200 m to
drainage districts of 20–50 m. Resolving each plot on a grid of 5–10 m, with the levees as virtual walls and
the outlets as notches in them, is planned (design in docs/paddy_plan.md §7).

- **Paddy tanks**: tanks that receive the rain falling on the paddy area fraction a of a cell. The paddy
  fields are split by the adoption ratio into "paddy fields with normal outlets" (class 1) and "paddy-field
  dams" (class 2), and each class has one ponding depth (water depth above the field surface).
- **Outlets**: one outlet for each representative plot area A_plot. Its discharge is given by the device law
  from the ponding depth and the water depth downstream (on the surface of the cell). The discharge goes to
  the surface water of the cell and flows with the shallow water flow.
- **Levees**: ponding above the levee height overflows at once to the surface.

The history and the decisions of the design are in developer.md §119, and the study and the list of
references are in docs/paddy_plan.md.

## Enabling and settings

Give `fn_paddy` in `&list_sysparam` (`"-"` for the same parameter file). The settings are one group.

```
&list_paddy
  fn_pd_frac = 'paddy_frac.txt'   ! map of the paddy area fraction (share of the cell area, 0-1)
  pd_adopt = 0.5                  ! adoption ratio (share of the paddy area made into paddy-field dams; default 0)
  !pd_aplot = 3000.0              ! representative plot area (m2; default 3000)
  !pd_hlev = 0.30                 ! levee height (m; default 0.30)
  !pd_dev_type(2) = 1             ! device type of the paddy-field dams (default 1 = separated type)
  !pd_open_d(2) = 0.05            ! diameter of the hole of the outflow control plate (m; default 0.05)
/
```

`f_paddy = 0` disables it temporarily while keeping the settings. Give the area fraction either as a map
`fn_pd_frac` or as a uniform value `pd_frac`, and the adoption ratio either as a map `fn_pd_adopt` or as a
uniform value `pd_adopt`.

## Getting started (minimal input)

Only the **paddy area fraction** (`fn_pd_frac` or `pd_frac`) is required. Make the share of the area of each
grid cell from land-use data (for example the "paddy field" class of the National Land Numerical Information
land-use subdivision mesh) in preprocessing (the model does not read land use; this is the same idea as the preprocessing that makes masks from
land use, see the sea mask and channel mask section of [Geographic information](geoinfo.md) and developer.md §40). If the rest is omitted, a plot of 30 a, levees of 0.30 m, a decrease
in depth of 5 mm/d and no adoption (all normal outlets = a water-level board of 0.03 m × 0.30 m wide) are used,
and the adopted values are shown on the screen with `(default)`. Compare the effect of paddy-field dams by
giving `pd_adopt`.

**Typical setups**

| Setup | Configuration | What to look at |
|---|---|---|
| River peaks of a basin (100–200 m) | map of the paddy area fraction + compare runs with adoption ratio 0 and 1 (and in between) | peak and timing of the discharge on the flux lines of the channels, storage and full share in `paddy.csv` |
| Water level of the main drain of a district (20–50 m) | main drain as a channel mask with a subgrid width, paddy fields by the area fraction | discharge on the flux lines and water level at the probes of the main drain, ponding depth `Hpd` |
| Comparing devices | change `pd_dev_type(2)` and the size of the hole | rate of the outflow (outlet flow and overflow) `qsurf` and storage in `paddy.csv` |
| Comparing the state before the rain | `pd_h0` (0 = empty for mid-season drainage, 0.03 = normal ponding, 0.30 = full from an earlier rain) | same as above |

## How it works

### Paddy tanks

The paddy area fraction a of cell (i, j) is split into two classes by the adoption ratio r.

```math
a_1 = a\,(1 - r)\ (\text{normal outlets}),\qquad a_2 = a\,r\ (\text{paddy-field dam outlets})
```

The paddy fields of class c have one ponding depth $`H_c`$ (water depth above the field surface) in the cell,
and there is one outlet for each representative plot area $`A_{\mathrm{plot}}`$. The number of outlets in the
cell is $`N_c = a_c\,\Delta x\,\Delta y/A_{\mathrm{plot}}`$, the outflow of the cell is $`N_c\,Q_c`$, and the outflow
rate per unit paddy area is

```math
q_c = \frac{Q_c(H_c, h_D)}{A_{\mathrm{plot}}}
```

Because $`q_c`$ does not depend on the grid size, the same paddy fields respond in the same way on a grid of
100 m and on a grid of 20 m (the same form as an earlier study that represented paddy fields in a coarse
distributed runoff model as tanks on the area fraction of each cell[^nihei2024]). Every step (right after the
shallow water flow) the tanks advance in this order.

1. **Rain**: the rain $`a\,R\,\Delta t`$ that fell on the paddy fields is taken from the surface water and
   $`R\,\Delta t`$ is added to each tank (R is the rain at the ground, after
   [rainfall interception](forcing.md) when it is used).
2. **Outlet flow**: $`\Delta H = q_c\,\Delta t`$ is moved to the surface. $`h_D`$ is the surface water depth of the
   cell (the water level downstream of the outlet measured from the field surface).
3. **Overflow**: the part of $`H_c`$ above the levee height is moved to the surface at once (the same treatment
   as the simple paddy runoff calculation program of MAFF[^maff2026]).
4. **Decrease in depth**: water leaves the system at the rate `pd_perc_mmd` (it does not enter the groundwater).

The water moved to the surface flows as surface water of the cell with the shallow water flow and gathers in
the channels and drains.

### Device laws of the outlets

The discharge Q (m³/s) of one outlet is obtained from the ponding depth H and the water depth downstream
$`h_D`$ (same datum). There are three elements.

**Weir (crest of the water-level board or of the outflow control plate; crest height z, width B,
coefficient C)**. $`h_1 = H - z`$ and $`h_2 = \max(h_D - z, 0)`$.

```math
Q = \frac{2}{3}C\sqrt{2g}\,B\,h_1^{3/2}\quad(h_2/h_1 < 2/3),
\qquad
Q = \sqrt{3}\,C\,B\,h_2\sqrt{2g\,(h_1 - h_2)}\quad(h_2/h_1 \ge 2/3)
```

The two are continuous at the switching point. With C = 0.525 they agree with the Honma formula (0.35 and
0.91; [Explanation of hydraulic laws](hydraulics.md) §1) used for levee overflow in ENCflow. Generalising the
form of the Honma formula with the discharge coefficient C is our own construction.

**Triangular notch (V-notch; vertex height z, angle θ)**: $`Q = \tfrac{8}{15}C\tan(\theta/2)\sqrt{2g}\,h_1^{5/2}`$[^maff2026].
For submergence the ratio of the submerged to the free weir flow
$`S(\rho) = \tfrac{3\sqrt{3}}{2}\rho\sqrt{1 - \rho}`$ ($`\rho = h_2/h_1 \ge 2/3`$) is applied (our own analogy).

**Hole (circle of diameter d, or rectangle of width b and height e; bottom height $`z_o`$)**. The free outflow is
the integral over the chord width of the hole.

```math
Q_f = C\int_{z_o}^{\min(H,\ z_o + \text{height})} b(y)\sqrt{2g\,(H - y)}\,dy
```

This form also holds at low heads where only part of the hole is under water[^yoshikawa2010][^miyazu2012]; when H
is well above the height of the hole it approaches $`C\,a\sqrt{2g\,(H - \text{centre of the hole})}`$[^maff2026].
When the water depth downstream is above the bottom of the hole, the smaller of $`Q_f`$ and the submerged formula
$`Q_s = C\,A_w\sqrt{2g\,(H - h_D)}`$ ($`A_w`$ is the area of the hole below H)[^miyazu2012] is taken (the
same idea as joining the three flows of a culvert by the smaller one; [Explanation of hydraulic
laws](hydraulics.md) §2; our own construction).

The device type `pd_dev_type` assembles the elements[^maff2026].

| Type | Device | Discharge |
|---|---|---|
| 0 | water-level board only (normal outlet; a removed board is crest 0) | weir (crest `pd_board_h`, width `pd_board_w` of the water-level board) |
| 1 | separated type (an outflow control plate with a hole inside the drainage box, apart from the water-level board) | min(weir of the water-level board, hole + overflow of the crest `pd_plate_h` of the outflow control plate) |
| 2 | integrated type (a hole or notch in the lower part of the water-level board) | hole + overflow of the crest of the water-level board |

With type 1, the weir of the water-level board decides the discharge while the rain is small (no
restriction), and the hole restricts it once the discharge exceeds what the hole can pass. With type 2 the
hole restricts from the start of the rain. Integrated types with a triangular notch (V-notch weir) or a
rectangular notch (gate-shaped weir) are given by the hole shapes `pd_open_type` = 3 and 2 of type 2.

### Relation to the surface water (one way)

The water depth downstream of the outlet is the surface water depth of the cell. When the surface water rises,
the outlet becomes submerged and the outflow decreases; when the surface water level reaches the ponding
depth, the outflow stops. **Flow in the opposite direction (inundation entering the paddy fields through the
outlets or over the levees) is not represented.** The surface water covers the whole cell while a tank sits on
the paddy area only, so making the exchange two-way would count the storage twice when the two levels become
equal (for paddy fields with area fraction 0.8 and levees of 0.3 m under inundation, the inundation depth would
be underestimated by about 0.24 m). For targets where inundation entering the paddy fields matters in low-lying
land, read [Scope and restrictions](#scope-and-restrictions) below.

### Time step

The tanks are explicit and use the same step $`\Delta t`$ as the shallow water flow. The outlet discharge changes
over the time it takes the ponding depth to change by a few cm (minutes to hours), which is much longer than the
step of the shallow water flow (seconds), so it does not limit the step. The water moved in one step is capped
by the storage above the level at which the outlet starts to drain and by the amount that fills half the
difference of the levels to the downstream (to prevent overshoot of the explicit scheme).

## Output and checks

| Output | Contents |
|---|---|
| `Hpn0001…`, `Hpd0001…` | ponding depth (m, above the field surface) of the paddy fields with normal outlets and of the paddy-field dams. Written automatically only in runs that have paddy fields of that class. 0 in cells without paddy fields |
| `paddy.csv` (every `dt_record`) | time(s), area1 and area2 (paddy area of each class, m²), rain (accumulated rain on the paddy fields, m³), outflow (accumulated outlet flow), spill (accumulated levee overflow), perc (accumulated decrease in depth), store1 and store2 (storage of each class, m³), residual (change of storage − (rain − outflow − spill − perc)), qsurf (rate moved to the surface in the last step, m³/s), h1 and h2 (mean ponding depth of each class, mm), full1 and full2 (share of the paddy area filled to the levee height) |
| S (S_surf) in the Log | surface water plus the storage of the paddy tanks (domain mean, m) |

The accumulated values in `paddy.csv` start at the beginning of the run (at the restart when restarted). The
ponding depths of the paddy tanks are saved with the state (`f_state_save`) in the private file `paddy.dat` and
carried over on restart ([interruption and restart](restart.md)).

**Reading the effect of paddy-field dams**: compare two runs that differ only in the adoption ratio, by the peaks
and timing of the discharge on the flux lines of the channels and drains and by the depth and extent of the
inundation. Periods with `full2` (share of the paddy-field dams that are full) close to 1 are periods in which
the storage of the paddy-field dams is used up and their effect is gone. The difference between `h2` and the
levee height is the remaining free storage.

## Scope and restrictions

**What cannot be represented (out of scope by design)**

- Breaching, leakage or collapse of levees, and clogging or removal of the control plates (given only as scenarios
  by changing the device type and the adoption ratio).
- Flow of inundation into the paddy fields (see [Relation to the surface water](#relation-to-the-surface-water-one-way) above).
- Growth of the rice and judgement of submergence damage (up to giving the ponding depth and its duration),
  irrigation intake and distribution, and changes of water management in time such as mid-season drainage (the
  devices do not change during a run).
- Variation between plots: all paddy fields of the same class in the same cell have the same ponding depth.
  Variation of field surface or levee heights is not represented.
- Evapotranspiration from the tanks (even with `fn_evap`, nothing is taken from the paddy tanks; the amount is small
  over the time of a flood).
- The water of the decrease in depth leaves the system and does not enter the groundwater (`fn_gwflow`).

**Limits of accuracy (when reading the results)**

- The water from an outlet comes out on the surface of its own cell and flows with the shallow water flow. Coarse
  grids do not resolve the drains, so the time from the paddy fields to the channels depends on the surface
  roughness. With the large roughness meant for hillslopes, the outflow from the paddy fields is delayed too much.
- The reduction of river peaks in a basin becomes smaller in proportion to the paddy area fraction and the adoption
  ratio. Little effect has been reported for large rivers with a paddy area fraction below 20 %[^saha2023]. When the
  paddy-field dams become full in a long rain the effect disappears; tests of commercial devices reported almost no
  effect for rain above 450 mm in 3 days[^minakawa2022].
- Field studies reported that the main cause of overflow is backflow and poor drainage due to the rising water level
  of the drains. In a computation of Kameda-gō, Niigata (41 % paddy), over 90 % of the overflowing paddy fields were caused
  by high water levels in the drains, and at 200 mm/d of rain 89 % of the overflow was backflow from the drains[^sato2021].
  This version restricts the outflow by the downstream water level but does not represent backflow, so it underestimates
  overflow in low-lying land with strong backwater.
- In a basin, the effect has been reported to be largest for a rain of 268 mm/d (about once in 120 years) and to become
  smaller for stronger rain as more paddy fields overflow their levees[^miyazu2020].
- **Cells where river or inland flood water reaches the paddy fields** (overtopping or breaching of rivers, overflow of
  drains): the surface water does not enter the tanks and the tank water does not merge with the flood. In cells flooded
  above the levee crest, the flood level is underestimated by up to "area fraction × ponding depth of the tank" (0.16 m
  for an area fraction of 0.8 and a ponding depth of 0.2 m), and `Hpn` and `Hpd` keep the ponding depth stored from rain
  alone (smaller than the actual ponding of the flooded fields). Below the levee crest, the surface water spreads over the
  whole cell, so the inundation depth comes out smaller than the actual depth outside the paddy fields (roads, drains,
  settlements) (the same limit as a coarse-grid run without paddy fields). Assessing low-lying land where floods reach the
  paddy fields needs the method that resolves the plots (planned).
- The discharge coefficients of devices vary from 0.40 to 0.88 with the product and the installation
  [^yoshikawa2009][^minakawa2022]. The default 0.6 is the value of the calculation program of the guide and is a starting
  point for calibration.

**Restrictions on combinations**: only the ENC grid system (`f_gridsystem = 0`). It cannot be combined with nesting
(multiple grids), water quality (`fn_wq`) or the two-layer fresh and salt water (`fn_salt`) (stops at start-up).
Paddy cells (area fraction > 0) cannot be on sea, channel (`fn_rw`), water level boundary, inflow boundary, source or
structure cells, nor on zone cells of [VZ](vz.md) or of the [storage function method](sfm.md). The area fraction cannot
exceed the void ratio of buildings `fn_gv` (paddy fields and buildings are different parts of the same cell).

**Combination with landform change** (`fn_geomorph`): the rain on paddy fields falls into the tanks (the ponded water on
the fields), so erosion by raindrops (the raindrop term of `f_wash`, `f_splash`) is computed without the paddy part (the
erosion rate is multiplied by "1 − area fraction"; ponded water nearly stops erosion by raindrop splash[^bako2016]). The
paddy part is excluded even when a tank is empty (ponding depth 0) (an original simplification). Limits: the tanks carry
no sediment and the water from the outlets is clear (turbid water such as the drainage after puddling is not
represented). Erosion by flow (the sheet erosion term of `f_wash`, entrainment of suspended sediment, bed load) is
computed over the whole cell, so the soil of the paddy part is also eroded by the surface flow. The rain amount for
dissolution (`f_dissol`) is not changed (the settings driven by the rain amount count the rain on the paddy part, and the
settings driven by the infiltration do not count the percolation of paddy fields).

## Parameters and the basis of their defaults

The labels in the Basis column are explained in [How to read the basis of a default](../users_guide.md#how-to-read-the-basis-of-a-default).

**&list_paddy** (the index of the device arrays is the class: 1 = normal outlets, 2 = paddy-field dams)

| Parameter | Default | Meaning | Basis |
|---|---:|---|---|
| f_paddy | 1 | 0 disables it temporarily | **Option** |
| fn_pd_frac | — | map of the paddy area fraction (share of the cell area, 0–1) | **Given** one of this and `pd_frac` is required |
| pd_frac | — | uniform value of the paddy area fraction | **Given** |
| fn_pd_adopt | — | map of the adoption ratio (share of the paddy area made into paddy-field dams, 0–1) | **Given** |
| pd_adopt | 0 | uniform value of the adoption ratio | **Given** 0 = no adoption |
| pd_aplot | 3000 m² | representative plot area (paddy area per outlet) | **Literature** standard plot of 30 a[^maff2026][^maffplan] |
| pd_hlev | 0.30 m | levee height (above the field surface) | **Literature** levees of about 30 cm in the guide[^maff2026][^maffplan] |
| pd_h0 | level at which the outlet starts to drain | ponding depth before the run (above the field surface; same value for both classes) | **Given** the default is normal ponding (height of the water-level board) |
| pd_perc_mmd | 5 mm/d | decrease in depth (leaves the system) | **Literature** default of the calculation program of the guide[^maff2026] |
| pd_dev_type(c) | 0 / 1 | device type (0: water-level board only, 1: separated type, 2: integrated type) | **Option** class 1 = normal outlet, 2 = separated type[^maff2026] |
| pd_board_h(c) | 0.03 m | crest height of the water-level board (above the field surface) | **Literature** default of the calculation program[^maff2026][^minakawa2022] |
| pd_board_w(c) | 0.30 m | width of the water-level board (weir width) | **Literature** example of the guide[^maff2026] |
| pd_open_type(c) | 1 | shape of the hole (1: circle, 2: rectangle, 3: triangle) | **Option** |
| pd_open_d(c) | 0.05 m | diameter of a circular hole | **Literature** example of the guide and φ50 in Niigata[^maff2026][^yoshikawa2009] |
| pd_open_b(c), pd_open_e(c) | — | width and height of a rectangular hole | **Given** required for a rectangle |
| pd_open_ang(c) | 60° | angle of a triangular notch | **Literature** example of the integrated type in the guide[^maff2026] |
| pd_open_z(c) | 0 m | height of the bottom of the hole (vertex for a triangle) above the field surface | **Given** |
| pd_plate_h(c) | none | crest height of the outflow control plate (overflow of type 1; none = no overflow) | **Given** |
| pd_plate_w(c) | width of the water-level board | width of the overflow of the outflow control plate | **Given** |
| pd_cw(c) | 0.6 | discharge coefficient C of weirs | **Literature** default of the calculation program[^maff2026] |
| pd_co(c) | 0.6 | discharge coefficient C of holes | **Literature** default of the calculation program[^maff2026]; 0.62–0.88 in experiments and fields[^yoshikawa2009][^yoshikawa2010][^miyazu2012] |

**Hints for revising the defaults**

- **Devices**: give the type and dimensions of the devices used in the district. The guide gives the separated type with
  φ50 and the integrated type with a 60° notch as examples, and lists examples from other districts such as holes of φ30–60 mm
  (matched to the plot area) and a gate-shaped notch of 12 cm × 5 cm[^maff2026].
- **Plot area**: in districts with large plots (such as 1 ha), increase `pd_aplot`. With the same hole, a larger plot
  gives a smaller outflow rate per unit paddy area.
- **Ponding before the rain**: the results change much with the water management at the time of the flood (empty for
  mid-season drainage, normal ponding, full from an earlier rain). It is safer to run several states and show the range.

## Verification and examples

| Case | Contents | Key points |
|---|---|---|
| [test/paddy](../../../test/paddy/en/README.md) | drainage, equilibrium, overflow, maps, save → restore of a plot | weir and V-notch against exact solutions (error of the explicit scheme ≤ 1.3×10⁻⁴), circular and rectangular holes and the separated type against independently solved reference solutions (within 3×10⁻⁸ relative), water conservation in a closed domain (7×10⁻¹⁵ m), bit-identical for np = 1, 2, 4 |

## References

[^maff2026]: Ministry of Agriculture, Forestry and Fisheries (MAFF), Rural Development Bureau (2026): Guide to "paddy-field dams" (revised edition) and its reference material (description of the simple paddy runoff calculation program). https://www.maff.go.jp/j/nousin/mizu/kurasi_agwater/attach/pdf/ryuuiki_tisui-207.pdf (first edition April 2022). In Japanese.
[^maffplan]: MAFF: Planning and design standards for land improvement projects, Planning "farmland consolidation (paddy fields)". In Japanese.
[^yoshikawa2009]: Yoshikawa, Nagao and Misawa (2009): Transactions of the Japanese Society of Irrigation, Drainage and Rural Engineering, 77(3), 263–271. doi:10.11408/jsidre.77.263 (in Japanese)
[^yoshikawa2010]: Yoshikawa, Koide and Misawa (2010): same journal, 78(4), 273–279. doi:10.11408/jsidre.78.273 (in Japanese)
[^miyazu2012]: Miyazu et al. (2012): same journal, 80(6), 479–488. doi:10.11408/jsidre.80.479 (in Japanese)
[^miyazu2020]: Miyazu et al. (2020): Journal of JSCE, Ser. B1 (Hydraulic Engineering), 76(2), I_805–I_810. doi:10.2208/jscejhe.76.2_I_805 (in Japanese; conditions under which the effect of paddy-field dams becomes smaller, in a basin in Tochigi)
[^sato2021]: Sato et al. (2021): Journal of JSCE, Ser. B1 (Hydraulic Engineering), 77(2), I_439–I_444. doi:10.2208/jscejhe.77.2_I_439 (in Japanese; causes of the overflow of paddy fields in Kameda-gō)
[^minakawa2022]: Minakawa and Miyazu (2022): Transactions of the Japanese Society of Irrigation, Drainage and Rural Engineering, 90(1), I_157–I_165. doi:10.11408/jsidre.90.I_157 (in Japanese)
[^nihei2024]: Nihei et al. (2024): *Water*, 16(2), 255. doi:10.3390/w16020255
[^saha2023]: Saha et al. (2023): *Sustainability*, 15(8), 6604. doi:10.3390/su15086604
[^bako2016]: Nouhou Bako et al. (2016): *Earth Surface Processes and Landforms*, 41, 1199–1210. doi:10.1002/esp.3894 (water depth and the transport of soil by raindrop splash)
