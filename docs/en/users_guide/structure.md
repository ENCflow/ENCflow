# Internal hydraulic structures (&list_struct_pump / culvert / diversion / dam)

> English mirror of docs/users_guide/structure.md (based on commit 248804f). The Japanese file is the master copy.

[Back to the user's guide index](../users_guide.md)

Handles drainage pumps, culverts (sluice pipes and sluice gates),
diversions, and dams. Enabled via `fn_structure`, with one namelist
group per type (absence of a group = no structures of that type).

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
on flux transects (record). A cross section too large for the cell size
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

## Dams (&list_struct_dam)

A bucket model in which a **capture band** of cells crossing the river
just upstream of the dam body absorbs all arriving water every step
into storage, and releases it to the outlet cells according to an
operation rule (the flow on the reservoir surface is not solved).

```
&list_struct_dam
  dam_in_cell(:,1,1) = 120, 44      ! capture band (a column crossing the river; allow margin beyond the wetted width)
  dam_in_cell(:,2,1) = 120, 45
  dam_in_cell(:,3,1) = 120, 46
  dam_out_cell(:,1,1) = 123, 45     ! outlet cell (the channel just downstream of the dam body)
  dam_hv(:,1,1) = 320.0, 0.0        ! HV curve: (water level m, storage volume m3)
  dam_hv(:,2,1) = 355.0, 1.5e7      !   at least 2 points: minimum level and surcharge
  f_dam_mode(1) = 2
  dam_rate(1) = 0.3                 ! constant-rate cut (release ratio 30%)
  dam_h_init(1) = 340.0             ! initial level (default = minimum level = empty)
  dam_area(1) = 8.0e5               ! reservoir area (used only with evapotranspiration; optional)
/
```

**Operation modes (f_dam_mode)**

| Value | Operation | Parameters |
|---|---|---|
| 1 | constant release | dam_q0 (m3/s) |
| 2 | constant-rate release (inflow x r) | dam_rate (0-1) |
| 3 | natural regulation (level-release rating) | one of the following (in priority order): (a) polyline dam_hq_rule (b) orifice dimensions dam_ori_width/height/zbase (c) design maximum release dam_qmax (auto-built with the sqrt law) |

- **Emergency release** (modes 1, 2): when the storage level exceeds
  `dam_tadashigaki` (default = minimum + 0.9 x (surcharge - minimum)),
  the release ramps up toward the inflow over the interval up to the
  surcharge level. Any excess above the surcharge spills automatically.
- The initial level is `dam_h_init` (default = minimum level = empty;
  for multi-purpose dams specify the restricted level explicitly).
  Water below the minimum level is dead storage and cannot be drawn
  down.
- At every recording time, (t, H, V, Qin, Qout, Qspill) is written to
  `result/dams/dam0001.csv`.
- **Reservoir surface evaporation (dam_area)**: when
  evapotranspiration ([fn_evap](forcing.md)) is active, specifying
  `dam_area` (reservoir surface area in m2) subtracts open-water
  evaporation E x dam_area directly from the storage and stops the
  individual evaporation of the capture band cells (prevents double
  counting). When omitted, the capture band cells evaporate by their
  cell areas, the same as ponds. With evapotranspiration inactive,
  neither choice has any effect.
- Constraints: neither the capture band nor the outlet cells can be
  combined with ponds or channel-width cells.

| Parameter | Default | Meaning |
|---|---|---|
| dam_in_cell(:,k,n) | -- (mandatory) | Set of capture band cells (i, j) (either this or fn_dam_in_cell) |
| dam_out_cell(:,k,n) | -- (mandatory) | Set of release cells (i, j) |
| dam_hv(:,k,n) | -- (mandatory) | HV curve (water level m, storage m3). At least 2 points (minimum level and surcharge). Monotonically increasing in both level and storage |
| f_dam_mode(n) | -- (mandatory) | Operation mode. 1: constant release, 2: constant-rate cut, 3: natural regulation |
| dam_q0(n) | -- | Constant release of mode 1 (m3/s). Mandatory in mode 1 |
| dam_rate(n) | -- | Release ratio r of mode 2 (0-1). Mandatory in mode 2 |
| dam_hq_rule(:,k,n) | -- | Mode 3(a): level-release polyline (m, m3/s). Levels monotonically increasing |
| dam_ori_width(n) / dam_ori_height(n) / dam_ori_zbase(n) | -- | Mode 3(b): orifice width B (m), height D (m), and invert elevation (m). Specify the three together |
| dam_ori_ce(n) | 0.5 | Entrance loss coefficient of mode 3(b) |
| dam_qmax(n) | -- | Mode 3(c): design maximum release (m3/s, at surcharge). Auto-builds the sqrt law Q(H)=Qmax*sqrt((H-invert)/(Hsur-invert)) |
| dam_zbase(n) | minimum level | Invert elevation of the mode 3(c) sqrt law (m). Below the surcharge level |
| dam_tadashigaki(n) | minimum + 0.9 x (surcharge - minimum) | Start level of the emergency release (m; modes 1, 2). Strictly between the minimum and surcharge levels |
| dam_h_init(n) | minimum level (empty) | Initial water level (m). Between the minimum level and the surcharge |
| dam_area(n) | none | Reservoir surface area (m2). An optional parameter used only when evapotranspiration (fn_evap) is active (see "Reservoir surface evaporation" above). Must be positive when specified |
| fn_dam_in_cell(n) / fn_dam_out_cell(n) | "" | File specification of the cell sets (from dir_data; each line "i j") |

## Format samples

Annotated examples of all four types:
[examples/List_samples/list_structure.txt](../../../examples/List_samples/en/list_structure.txt).
For levee overtopping and breach and channel conveyance, see the
[channel chapter](channel.md).
