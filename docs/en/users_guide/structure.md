# Internal hydraulic structures (&list_struct_pump / culvert / diversion / dam)

> English mirror of docs/users_guide/structure.md (based on commit 583d100). The Japanese file is the master copy.

[Back to the user's guide index](../users_guide.md)

Handles drainage pumps, culverts (sluice pipes and sluice gates),
diversions, and dams/lakes. Enabled via `fn_structure`, with one
namelist group per type (absence of a group = no structures of that
type).

The four types share a common skeleton: **two cell sets (intake side ->
outlet side or out of the domain) + a hydraulic rule Q (a function of a
reference value) + mass-conservative transfer**. Every step the
transfer is limited to "the volume of water actually present on the
intake side", so water that is not there is never taken. Every cell set
can also be given as a file (`fn_*_cell`; each line "i j"), and
piecewise-linear rules are interpolated linearly with end values held
outside the range. Cell coordinates (i, j) are **1-based** (add +1 when
picking numbers from the 0-based numbering of GIS such as QGIS;
[coordinates chapter](coordinates.md)).

**Common format rules**: structures are identified by a number n per
type, and parameters are given as `name(n)` (one value per structure)
or `name(:,k,n)` (the k-th element of a cell set or polyline). Numbers
must be **consecutive from 1** per type (a gap stops with an error), up
to 50 structures per type, 999 cells per structure, and 999 polyline
points. The table at the end of each section lists all parameters --
"mandatory" items stop with an error when omitted; all others are
optional, with the behavior when omitted given in the "default" column.

## Drainage pumps (&list_struct_pump)

Forced transfer (mechanical drainage) from an intake cell set to an
outlet cell set. Intake and outlet need not be adjacent and have no
distance limit; **omitting the outlet means drainage out of the
domain** (pumping into sewers or another catchment = removal from the
system).

```
&list_struct_pump
  ! pump 1: interior water to the main river. Starts at a forebay depth of 0.5 m, rated at 1.0 m
  pump_in_cell(:,1,1)  = 120, 45
  pump_out_cell(:,1,1) = 95, 12
  f_pump_ref(1) = 1                 ! reference = depth h of the representative intake cell
  pump_rule(:,1,1) = 0.5, 0.0      ! (depth m, discharge m3/s)
  pump_rule(:,2,1) = 1.0, 5.0
  ! pump 2: constant 2 m3/s out of the domain at all times
  pump_in_cell(:,1,2) = 200, 80
  pump_q0(2) = 2.0
/
```

- Operation is either `pump_q0(n)` (constant at all times) or
  `pump_rule` (a piecewise-linear reference-discharge curve), one or
  the other. Threshold ON/OFF is expressed by a steep ramp between two
  close points, and multi-stage operation by a staircase-shaped
  polyline (being a function of the current value, there is no history
  = no effect on restart).
- The reference is `f_pump_ref(n)` = 0: water level eta of the
  representative intake cell (the first one), 1: depth h of the same
  cell.
- **Pond intake**: if the intake cell is a pond (rscap > 0 in geoinfo),
  water is drawn from the pond storage instead of the surface water
  (forebay drainage). In this case only the depth (= pond depth) can be
  used as the reference.

| Parameter | Default | Meaning |
|---|---|---|
| pump_in_cell(:,k,n) | -- (mandatory) | Set of intake cells (i, j) (either this or fn_pump_in_cell) |
| pump_out_cell(:,k,n) | none | Set of outlet cells (i, j). Omitted = drainage out of the domain (removal from the system) |
| pump_q0(n) | -- | Constant discharge at all times (m3/s). Exactly one of this or pump_rule is mandatory |
| pump_rule(:,k,n) | -- | Operating-rule polyline (reference value m, discharge m3/s). Exactly one of this or pump_q0 is mandatory |
| f_pump_ref(n) | 0 | Reference of the operating rule. 0: water level eta of the representative (first) intake cell, 1: depth h of the same cell (only 1 is allowed for pond intake) |
| fn_pump_in_cell(n) / fn_pump_out_cell(n) | "" | File specification of the cell sets (from dir_data; each line "i j") |

## Culverts (&list_struct_culvert)

A buried conduit of rectangular cross section B x D crossing an
embankment, road, or levee. It is **bidirectional**: flow goes from the
higher water level side to the lower, and reverses automatically if the
levels flip. Sluice pipes and sluice gates are expressed with the gate
extension.

```
&list_struct_culvert
  culv_in_cell(:,1,1)  = 150, 60    ! upstream-side cell
  culv_out_cell(:,1,1) = 152, 60    ! downstream-side cell
  culv_width(1)  = 2.0              ! section width B (m) (mandatory)
  culv_height(1) = 2.0              ! section height D (m) (mandatory)
  culv_zin(1)  = 12.50              ! upstream invert elevation (m) (mandatory)
  culv_zout(1) = 12.30              ! downstream invert elevation (m) (mandatory)
  culv_length(1) = 25.0             ! conduit length (m) (default 0 = no friction loss)
/
```

The discharge law switches continuously among three regimes depending
on the water levels: no flow -> free surface (Honma weir formula) ->
full conduit (orifice + conduit friction).

**Sluice pipes and sluice gates (gate extension)**

```
  culv_flap(2) = 1                  ! flap gate (unpowered backflow prevention valve)
  culv_gate_ref(2) = 1              ! reference of the opening rule (0: in side, 1: out side = river side)
  culv_gate_rule(:,1,2) = 8.0, 1.0  ! (reference water level m, opening 0-1)
  culv_gate_rule(:,2,2) = 8.5, 0.0  ! closes between river levels 8.0 and 8.5 m
/
```

Constraints: cannot connect to pond cells. The downstream side cannot
be omitted (no out-of-domain drainage; use a pump for that). The
transfer is clear water (it carries no sediment) and does not register
on flux transects (record) (this "passes water only" property can be
used to approximate the outlet of an open-type check dam - see the
sabo-facilities paragraph in
[Sediment and landform change](geomorph.md)). A cross section too large for the cell size
(conveyance on the order of cell area x depth) makes the receiving side
diverge -- use realistic dimensions.

| Parameter | Default | Meaning |
|---|---|---|
| culv_in_cell(:,k,n) | -- (mandatory) | Set of upstream-side cells (i, j) (either this or fn_culv_in_cell) |
| culv_out_cell(:,k,n) | -- (mandatory) | Set of downstream-side cells (i, j). Cannot be omitted (no out-of-domain) |
| culv_width(n) | -- (mandatory) | Section width B (m) |
| culv_height(n) | -- (mandatory) | Section height D (m) |
| culv_zin(n) / culv_zout(n) | -- (mandatory) | Upstream and downstream invert elevations (m) |
| culv_length(n) | 0 | Conduit length L (m). 0 = no conduit friction loss |
| culv_manning(n) | 0.02 | In-conduit Manning roughness n |
| culv_ce(n) | 0.5 | Entrance loss coefficient |
| culv_flap(n) | 0 | 1: flap gate (an unpowered check valve blocking reverse flow out -> in) |
| culv_gate_rule(:,k,n) | none | Gate opening polyline (reference water level eta m, opening 0-1). Omitted = always fully open. The opening is a linear multiplier on the discharge |
| culv_gate_ref(n) | 1 | Reference cell of the opening rule (0: in-side representative, 1: out-side representative = river side) |
| fn_culv_in_cell(n) / fn_culv_out_cell(n) | "" | File specification of the cell sets (from dir_data; each line "i j") |

## Diversions (&list_struct_diversion)

A **one-way, passive** withdrawal from an intake cell set to out of the
domain (inter-catchment diversion = the main use) or to a delivery cell
set (intake weirs, diversion channels).

```
&list_struct_diversion
  div_in_cell(:,1,1) = 80, 30       ! intake cell (just upstream of the weir)
  div_rule(:,1,1) = 10.2, 0.0       ! rating of (water level eta m, discharge m3/s)
  div_rule(:,2,1) = 10.8, 20.0
/
```

- Operation is either `div_q0(n)` (constant) or `div_rule` (a rating on
  the water level eta of the representative intake cell), one or the
  other. The reference is the water level eta only.
- The difference from a pump is **passivity**: when a delivery target
  is specified, the diversion stops automatically if the delivery-side
  water level is at or above the intake side (gravity cannot climb). To
  force the transfer, use a pump.

| Parameter | Default | Meaning |
|---|---|---|
| div_in_cell(:,k,n) | -- (mandatory) | Set of intake cells (i, j) (either this or fn_div_in_cell) |
| div_out_cell(:,k,n) | none | Set of delivery cells (i, j). Omitted = diversion out of the domain. When given, the diversion stops automatically while the delivery-side level is at or above the intake side |
| div_q0(n) | -- | Constant discharge at all times (m3/s). Exactly one of this or div_rule is mandatory |
| div_rule(:,k,n) | -- | Intake rating polyline (water level eta of the representative intake cell m, discharge m3/s). Exactly one of this or div_q0 is mandatory |
| fn_div_in_cell(n) / fn_div_out_cell(n) | "" | File specification of the cell sets (from dir_data; each line "i j") |

## Dams and lakes (&list_struct_dam)

A bucket model in which the cells of the **water surface (capture
set)** absorb all arriving water every step into storage, and release
it to the outlet cells according to an operation rule (the flow and
backwater on the impounded surface are not solved). When
[water quality](wq.md) is enabled, storage lakes act as completely
mixed reservoirs and the released water carries the storage
concentration M/V (see "Reservoirs and retention ponds" in the wq
chapter). Not only dam
reservoirs but **general lakes** (natural lakes, lagoons, regulating
ponds, and lake groups sharing one water level) are handled by the
same mechanism.

**The water surface is specified in one of three ways** (per number n):

- `dam_in_cell` (namelist) / `fn_dam_in_cell` (file) -- suited to the
  capture band of a dam (a line crossing just upstream of the dam
  body).
- **`fn_dam_map` (lake-number raster; one file shared by all lakes)**
  -- suited to lakes resolved by the raster. Values <= 0 = no lake
  (negative GIS nodata is ignored), value n = the surface of structure
  n. Painting the same number on detached water bodies makes a **lake
  group sharing one water level**.

**Note on diagonal leakage**: the ENC grid exchanges water through
diagonal links too, so wherever the capture set is connected only
diagonally (e.g. a one-cell-wide diagonal line), water can slip
through a diagonal link whose both ends are outside the set. Specify
capture lines **4-neighbor connected** (no diagonal-only corners); the
program does not check this -- it is the user's responsibility.

```
&list_struct_dam
  fn_dam_map = "lake_map.txt"       ! lake-number raster (used by lake 2)
  ! dam 1: HV curve + constant-rate cut (capture line via the namelist)
  dam_in_cell(:,1,1) = 120, 44      ! capture band (a column crossing the river; allow margin beyond the wetted width)
  dam_in_cell(:,2,1) = 120, 45
  dam_in_cell(:,3,1) = 120, 46
  dam_out_cell(:,1,1) = 123, 45     ! outlet cell (the channel just downstream of the dam body)
  dam_hv(:,1,1) = 320.0, 0.0        ! HV curve: (water level m, storage volume m3)
  dam_hv(:,2,1) = 355.0, 1.5e7      !   at least 2 points: minimum level and surcharge
  f_dam_mode(1) = 2
  dam_rate(1) = 0.3                 ! constant-rate cut (release ratio 30%)
  dam_h_init(1) = 340.0             ! initial level (default = minimum level = empty)
  ! lake 2: raster surface + natural regulation (H-Q rating), auto linear HV
  dam_hmin(2) = 81.0                ! lower bound level (insensitive if below the normal level)
  f_dam_mode(2) = 3
  dam_hq_rule(:,1,2) = 84.0, 0.0    ! (level m, release m3/s); the level of Q=0
  dam_hq_rule(:,2,2) = 86.0, 400.0  !   = outlet river sill ~ the normal level
  dam_h_init(2) = 84.2              ! initial level = the normal level
  dam_out_cell(:,1,2) = 210, 95     ! the most upstream cell of the outlet river
/
```

**Operation modes (f_dam_mode)**

| Value | Operation | Parameters |
|---|---|---|
| 1 | constant release | dam_q0 (m3/s) |
| 2 | constant-rate release (inflow x r) | dam_rate (0-1). **r=1.0 is pass-through** (storage untouched, inflow = release; no HV needed) |
| 3 | natural regulation (level-release rating) | one of the following (in priority order): (a) polyline dam_hq_rule (b) orifice dimensions dam_ori_width/height/zbase (c) design maximum release dam_qmax (auto-built with the sqrt law; needs a surcharge level) |
| none (and no release cells) | **level-held lake**: all inflow vanishes; the level stays at dam_h_init (not lowered even by evaporation). A "large water surface not solved" = the inland version of the sea mask | dam_h_init (mandatory) |

**How to give HV (level-storage)**

| Given | Behavior |
|---|---|
| dam_hv (polyline) | The HV curve from references is used as is (for dams). At least 2 points = minimum level and surcharge |
| dam_hmin (+ optional dam_hsur) | **A linear HV is built automatically**: V(H) = A x (H - dam_hmin), A = number of capture cells x cell area. For lakes painted on the raster (no bathymetry data needed). Omitting dam_hsur = no upper bound (no spill; mandatory for modes 1, 2 and the sqrt law) |
| neither | Accepted only for pass-through (f_dam_mode=2, dam_rate=1.0) and level-held lakes; anything else stops with an error |

All levels are **absolute elevations**. With the linear HV the level
dynamics depend only on the surface area A and H; dam_hmin is just a
constant shift that places "the floor below which release cannot draw"
-- so for a lake of unknown depth, **any value safely below the normal
level (e.g. normal level - 5 m) suffices** (the result is insensitive
to it as long as the floor is not hit).

- **Emergency release** (modes 1, 2): when the storage level exceeds
  `dam_tadashigaki` (default = minimum + 0.9 x (surcharge - minimum)),
  the release ramps up toward the inflow over the interval up to the
  surcharge level. Any excess above the surcharge spills automatically.
- The initial level is `dam_h_init` (default = minimum level = empty;
  for multi-purpose dams specify the restricted level explicitly).
  Water below the minimum level is dead storage and cannot be drawn
  down.
- At every recording time, (t, H, V, Qin, Qout, Qspill, Qgw) is
  written to `result/dams/dam0001.csv` (a level-held lake records Qin
  = the vanished volume; Qgw is the exchange of the groundwater-head
  forcing dam_gw, 0 when unused).
- **Evaporation**: with evapotranspiration ([fn_evap](forcing.md))
  active, the storage of the capture set evaporates cell by cell by
  the cell area, the same as ponds. Painting the surface on the raster
  makes the impounded area = number of cells x cell area, i.e. the
  real area (to evaluate open-water evaporation for a capture-line
  dam, also switch to painting the surface).
- Constraints: neither the surface nor the outlet cells can be
  combined with ponds or channel-width cells. A multi-cell release is
  divided equally by the number of cells (cells may be far apart).

### Which pattern needs which parameters (pattern guide)

| Pattern | Surface | HV | Operation | Level |
|---|---|---|---|---|
| **Dam** (design data available) | capture line (dam_in_cell etc.) | dam_hv (the HV curve from references) | f_dam_mode = 1 / 2 / 3 | dam_h_init = initial level (restricted level for multi-purpose dams; omitted = empty) |
| **Storage lake** (unknown depth is fine) | paint the surface in fn_dam_map | dam_hmin = about normal level - 5 m | f_dam_mode = 3 + dam_hq_rule (level of Q=0 = outlet river sill) etc. | dam_h_init = normal level |
| **Pass-through lake** (small lake / connecting water surface with negligible retention) | either | not needed | f_dam_mode = 2, dam_rate = 1.0 | not needed (holds no level state) |
| **Level-held lake** (large surface not solved / terminal lake) | fn_dam_map | not needed | none (no release cells) | dam_h_init = the fixed level |
| **Lake group sharing one level** (lagoon group / linked ponds) | paint the same number on several surfaces | any of the above | any of the above | any of the above |
| **Multiple release works** (weir + canal + intakes) | one on the lake itself (main release) | one on the lake itself | additional ones via dam_lake(n)=lake number + each own mode | on the lake itself |

The normal level is not a constraint but **an initial value
(dam_h_init) plus a maintaining mechanism (the rating)**: place the
rating's Q=0 level near the normal level and the lake settles there in
low flow. The flood response of a storage lake is naturally expressed
as the storage attenuation A dH/dt = Qin - Q(H), so **using
pass-through (rate=1.0) for a large lake is inappropriate** (the flood
wave would be transmitted without attenuation).

### Multiple release works (dam_lake)

To give one lake several releases with different operations (e.g. Lake
Biwa's Seta weir + the Sosui canal + intakes), use a **referencing
structure** `dam_lake(n) = m`: structure n has no surface of its own
and draws from the storage of lake m with **its own operation mode and
release cells**.

```
  ! an additional release work of lake 2 (the example above): constant canal intake
  dam_lake(5) = 2                   ! draws from the storage of lake 2
  f_dam_mode(5) = 1
  dam_q0(5) = 15.0                  ! constant 15 m3/s
  dam_out_cell(:,1,5) = 150, 120    ! the inlet cell of the canal
/
```

- The referenced lake m must be a **lower-numbered lake with a main
  release** (its own mode and release cells); level-held lakes,
  pass-through lakes, and referencing structures cannot be referenced.
  Draws are applied sequentially in structure-number order (earlier
  structures draw first), and the surcharge spill goes out through the
  main release.
- The HV and levels are shared with lake m (dam_hv / dam_hmin /
  dam_h_init cannot be written on the referencing structure).
  `dam_tadashigaki(n)` can be given per release work (default = the
  lake's default).
- The CSV (`result/dams/dam0005.csv` etc.) records the referencing
  structure's own Qout and the lake's H and V after the draw (the Qin
  column is 0; the header carries the referenced lake number as
  `# lake =`).

### Forcing the groundwater head to the lake level (dam_gw)

Specifying `dam_gw(n) = 1` **fixes the groundwater head to the lake
level** on the surface cells of lake n (a Dirichlet boundary). Use it
to solve the exchange between the lake and the aquifer -- groundwater
levels in lakeside lowlands, seepage into reclaimed land, and so on.
The **lateral groundwater flow f_gwlateral = 1** of fn_gwflow is
mandatory.

- For a storage lake the exchanged volume is automatically traded with
  the lake storage V (leakage to the groundwater lowers V; a higher
  groundwater head raises it. When the lake runs dry the forcing backs
  off automatically). For a level-held lake the level stays fixed and
  only the exchange is recorded (the same semantics as the sea mask).
- The exchange appears in the `Qgw` column of the CSV (m3/s; positive
  = lake to groundwater). This column is always written for every
  dam/lake and stays 0 without dam_gw.
- Approximation: the groundwater head saturates at the ground surface
  (the excess pressure of the lake depth is not represented). At the
  start of a run an initial filling saturates the soil of the surface
  cells with lake water (for a storage lake this is real water taken
  from V).
- Combined with evapotranspiration, groundwater evaporation at the
  surface cells is replenished from the lake at the next forcing, so
  the lake effectively supplies the evapotranspiration through the
  groundwater.

| Parameter | Default | Meaning |
|---|---|---|
| dam_in_cell(:,k,n) | -- | Cells (i, j) of the surface (capture set). Mandatory through one of the three ways (fn_dam_in_cell / fn_dam_map) |
| fn_dam_map | "" | Lake-number raster (one file shared by all lakes; from dir_data). <= 0 = none, value n = the surface of structure n |
| dam_out_cell(:,k,n) | none | Set of release cells (i, j). **Omitted = a level-held lake** (inflow vanishes, level fixed) |
| dam_hv(:,k,n) | -- | HV curve (water level m, storage m3). At least 2 points (minimum level and surcharge). Monotonically increasing in both level and storage. Exclusive with dam_hmin |
| dam_hmin(n) | -- | Lower-bound level of the auto linear HV (elevation m). The alternative to dam_hv. Surface area = number of capture cells x cell area |
| dam_hsur(n) | none | Surcharge level of the auto linear HV (elevation m). Omitted = no upper bound (no spill). Mandatory for modes 1, 2 (except pass-through) and the sqrt law |
| f_dam_mode(n) | -- | Operation mode. 1: constant release, 2: constant-rate cut, 3: natural regulation. None + no release cells = a level-held lake |
| dam_lake(n) | 0 | >0: lake reference (structure n is an additional release work drawing from the storage of lake m=dam_lake(n) with its own rule and release cells). The referenced lake must be a lower-numbered lake with a main release. No surface / dam_hv / dam_hmin / dam_h_init on the referencing structure |
| dam_gw(n) | 0 | 1: fix the groundwater head to the lake level on the surface cells (see "Forcing the groundwater head" above). Requires f_gwlateral=1 of fn_gwflow. Not allowed on pass-through lakes and referencing structures |
| dam_q0(n) | -- | Constant release of mode 1 (m3/s). Mandatory in mode 1 |
| dam_rate(n) | -- | Release ratio r of mode 2 (0-1). Mandatory in mode 2. 1.0 = pass-through |
| dam_hq_rule(:,k,n) | -- | Mode 3(a): level-release polyline (m, m3/s). Levels monotonically increasing |
| dam_ori_width(n) / dam_ori_height(n) / dam_ori_zbase(n) | -- | Mode 3(b): orifice width B (m), height D (m), and invert elevation (m). Specify the three together |
| dam_ori_ce(n) | 0.5 | Entrance loss coefficient of mode 3(b) |
| dam_qmax(n) | -- | Mode 3(c): design maximum release (m3/s, at surcharge). Auto-builds the sqrt law Q(H)=Qmax*sqrt((H-invert)/(Hsur-invert)) (needs a surcharge level) |
| dam_zbase(n) | minimum level | Invert elevation of the mode 3(c) sqrt law (m). Below the surcharge level |
| dam_tadashigaki(n) | minimum + 0.9 x (surcharge - minimum) | Start level of the emergency release (m; modes 1, 2). Strictly between the minimum and surcharge levels |
| dam_h_init(n) | minimum level (empty) | Initial water level (m). Between the minimum level and the surcharge. For a level-held lake, the fixed level (mandatory) |
| fn_dam_in_cell(n) / fn_dam_out_cell(n) | "" | File specification of the cell sets (from dir_data; each line "i j") |

The former `dam_area` (direct specification of the impounded area) was
removed on 2026-08-20 (evaporation is unified to the cell-area
evaluation; specifying it stops with a namelist read error -- delete
it).

## Format samples

Annotated examples of all four types:
[examples/List_samples/list_structure.txt](../../../examples/List_samples/en/list_structure.txt).
For levee overtopping and breach and channel conveyance, see the
[channel chapter](channel.md).
