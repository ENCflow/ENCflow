# Storage function runoff of zones (fn_sfm)

> English mirror of docs/users_guide/sfm.md. The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

This feature computes the rainfall-runoff response of mountains and small catchments
with the **storage function method** (a method that regards a catchment as one tank and
routes the runoff with the relation S = K·q^P between storage and runoff; Kimura
1961[^kimura1961]). It is built in the same way as the
[vertical unsaturated flow (VZ) runoff](vz.md) and is handled on the ENCflow grid as the
following three parts.

- **Zone**: a group of cells with the same number in the zone number raster. Each zone
  has one **tank** (storage function), and the rain on all cells of the zone enters that
  tank. There is no per-cell quantity such as the soil depth of VZ, and **all cells of a
  zone have the same runoff** (per unit area).
- **Tank**: solves the relation S = K·q^P between the storage S per unit area and the
  runoff rate q (S in mm, q in mm/h) together with the continuity equation
  dS/dt = r − q.
- **Outlets**: state explicitly whether the runoff of a zone is moved to surface cells
  (a channel, a valley floor, etc.) or out of the system. The delay of the movement
  from the zone to the outlet is not solved (**instantaneous delivery**). The outlets
  and the baseflow are given in the same way as for VZ.

The storage function method is a **conceptual model** that condenses the response of a
catchment into two parameters K and P, and it does not represent where in the
catchment the runoff arises. K and P are calibrated with observations for each
catchment. A series of studies by Tani discusses that the relation between storage and
runoff of the storage function approximates the vertical infiltration in the soil layer
of hillslopes (the relation to VZ runoff). Because the zones are connected to the
shallow water flow and the channels, mountains can be solved as storage function zones
and the channels and the floodplain as surface flow. Cells not made into a zone (zone
number 0) behave as before. If the zones do not overlap with those of VZ, some zones
can be VZ and the others storage function in the same computation. The background of
the design and the decisions are in developer.md §106.

## Enabling and settings

Set `fn_sfm` in `&list_sysparam` (`"-"` for the same parameter file). The settings
are two groups.

```
&list_sfm                   ! common settings
  fn_sfm_zone = 'zone.asc'  ! zone number raster (integer; 0 = not applied)
/
&list_sfm_zone              ! zones (indexed by the zone number)
  sfm_k(1) = 30.0           ! storage coefficient K (S [mm] = K·q[mm/h]^P); required
  sfm_p(1) = 0.6            ! storage exponent P (0.6 when omitted)
  sfm_q0_mmh(1) = 0.1       ! initial runoff rate (mm/h; 0.1 when omitted)
  sfm_out_kind(1) = 1       ! outlet 1: move to surface cells / 2: out of the system
  sfm_out_cell(:,1,1) = 120, 80   ! outlet cell (i, j)
/
```

The K of the example only shows the form. K changes by orders of magnitude from one
catchment to another, so always give it (see [Parameters and the basis of their
defaults](#parameters-and-the-basis-of-their-defaults) below). `f_sfm = 0` disables the
feature temporarily while keeping the settings. Zone numbers are consecutive 1, 2, …,
and `sfm_out_kind` and `sfm_k` must be given for every zone.

## Getting started (minimum input)

Three things are needed.

1. **Zone number raster** `fn_sfm_zone` (under `dir_data`, on the same grid as the
   terrain). A number of 1 or more on cells to be treated by the storage function,
   0 elsewhere.
2. **Storage coefficient** `sfm_k` (per zone). **There is no default** (it is a
   quantity to calibrate for each catchment).
3. **Outlet** `sfm_out_kind` (and `sfm_out_cell`).

When the storage exponent `sfm_p` is omitted, 0.6 is used, and when the initial runoff
rate `sfm_q0_mmh` is omitted, 0.1 mm/h is used; the adopted values are shown on the
screen with `(default)`.

Give the rainfall as in [rainfall and weather](forcing.md). To see only the runoff of a
small catchment, make all cells of the catchment one zone with `sfm_out_kind = 2`
(outflow from the system); the runoff of the zone is then the catchment runoff
(`sfm_zone.csv`).

**Patterns of use**

| Pattern | Configuration | What to look at |
|---|---|---|
| Runoff of a small mountain catchment | whole catchment as one zone, `sfm_out_kind = 2` | q (runoff rate, mm/h) in `sfm_zone.csv`; time difference of vdrain = runoff. To add a baseflow separated from observations, give the zone a baseflow ([Baseflow](#baseflow) below) |
| Mountains by the storage function, channels by the shallow water flow | split zones by tributary valleys and put the outlet on the channel cell at the outlet of each valley (`sfm_out_kind = 1`) | channel discharge (measurement lines). The delay of propagation in the channel is solved by the shallow water flow |
| Rain with a spatial distribution | `f_sfm_rain = 1` (area average within a zone) | the input of a zone is the mean rainfall within the zone ([Handling of rain](#handling-of-rain) below) |
| Comparing with VZ runoff | with the same rain, make some zones VZ and the others storage function (zones must not overlap) | runoff in `vz_zone.csv` and `sfm_zone.csv` |

## How it works

### The tank (storage function)

The tank of zone g solves, for the storage S [mm] and the runoff rate q [mm/h] per unit
area,

```math
\frac{dS}{dt} = r(t) - q,
\qquad
S = K\,q^{P}
```

(r is the ground rainfall on the zone). The unit of K, matching the units of S and q, is
mm^{1−P}·h^P (with P = 1, K is a time [h], the time constant of a linear reservoir). The
runoff increases with the storage, and a measure of the response time is
dS/dq = K·P·q^{P−1} (the larger the runoff, the faster the response).

P = 0.6 is the value conventionally used in the storage function method[^kimura1961]. If
steady sheet flow on a uniform slope is represented by the kinematic wave with Manning's
law, the depth is proportional to the 3/5 power of the distance downslope, and the mean
depth on the slope (storage per unit area) is proportional to the 3/5 power of the
runoff rate (S ∝ q^{0.6}). P = 0.6 corresponds to this relation (this derivation is an
explanation given in this guide).

All rain enters the tank and there is no loss. The **lag time T_L**, the **separation
of effective rainfall with the primary runoff ratio f1 and the saturation rainfall
R_sa** (treating part of the rain as a loss that does not contribute to runoff) of the
full form of Kimura's method, and **two-valued storage functions** (Prasad type, Hoshi
and Yamaoka type) are not included
([Scope and restrictions on combinations](#scope-and-restrictions-on-combinations)).

The numerical solution is backward Euler (a scalar Newton method protected by bisection
of the interval). The internal time step is adjusted automatically from the difference of
the storage obtained from the same state by "one step of h" and "two steps of h/2", and
the accepted step takes the local extrapolation (second order) (this combination is a
choice of ENCflow). Because the runoff is defined as "previous storage + rain − new
storage", the water balance of the tank closes except for rounding. The time accuracy is
checked by comparison with analytic and reference solutions
([Verification](#verification-and-examples)).

### Handling of rain

Rain falling on the cells of a zone is first put on the surface by the shallow water
flow as usual and is then recovered within the same step as the input of the tank (the
same method as VZ; the processing of the shallow water flow and the rainfall does not
change, and functions that read the ground rainfall, such as the soil water index, can
be used as they are). Only the rain of that step is removed, so the surface water on the
cells of a zone is **only what flowed in from upstream**, and that does not enter the
tank (it flows on as surface flow).

The input of the tank is chosen from two options with `f_sfm_rain`.

- `f_sfm_rain = 0` (default): checks every time that the ground rainfall on the cells
  of the zone is **identical** and uses that value. If it differs, the computation
  stops (with a rainfall distribution, choose 1 or split the zones within areas of
  uniform rain).
- `f_sfm_rain = 1`: uses the **area average** over all cells of the zone. The total
  amount of rain is conserved, but this is an approximation of "replacement by the mean
  input". It follows the same idea as the usual use of the storage function method,
  which computes the runoff from the catchment-mean rainfall.

### Outlets

`sfm_out_kind = 1` moves the runoff of the zone to the cells of `sfm_out_cell` (added to
the surface water depth with the same conversion as rain and boundary sources). With
several cells it is split by the ratios `sfm_out_w` (sum 1; may be omitted for one cell;
no implicit equal split). Several zones may use the same outlet cell, and the addition is
made once. Outlets cannot be placed on zone cells, sea cells or water level boundary
cells (when combined with VZ, not on VZ cells either).

`sfm_out_kind = 2` is outflow from the system (no receiving cell is needed). Sending
directly to the end of a large basin also omits the delay of the channels, so in
wide-area computations put the outlet of a mountain zone on the channel cell at the
outlet of the tributary valley and leave the rest to the shallow water flow.

### Baseflow

A time series of baseflow can be given for each zone (optional). It is given and
handled in the same way as for VZ ([Baseflow of VZ](vz.md#baseflow)).

```
&list_sfm_zone
  sfm_out_kind(1) = 2
  sfm_base(:,1,1) = 0, 0.1          ! (time (min), baseflow (mm/h))
  sfm_base(:,2,1) = 1440, 0.5
  !fn_sfm_base(1) = 'base1.txt'     ! long series in a file (one line "time(min) mm/h")
/
```

- The rate is **mm/h per zone area**. The series is interpolated linearly and the end
  values are held outside its range (two points at the same time make a step). A
  series with decreasing times and negative values stop the computation. The namelist
  holds up to 100 points per zone; use `fn_sfm_base(z)` (relative to `dir_data`; takes
  precedence over the namelist) for long series.
- For each synchronisation interval, the integral over the interval × zone area is
  added to the runoff and passed to the outlet. The baseflow is a quantity given from
  outside and does not enter the storage of the tank or the balance residual. The
  baseflow of `sfm_out_kind = 1` increases S_total, and that of `= 2` goes from outside
  to outside and does not appear in S_total.
- Separating the baseflow (which line to draw) is the user's preprocessing.

### Synchronisation and time step

At every `dt_sfm`, the tank is advanced with the rain of each step in the interval as a
piecewise-constant input, and the runoff of the interval is passed to the outlet
together at the end of the interval (future rain is not used). The default
`dt_sfm = 0` is every step. The tank is one value per zone, so the cost is negligible
even at every step.

## Output and checks

**Ledger and log**

- The **storage of the tanks is counted in S_grnd** of the Log (Σ S·A of the zones
  divided by the number of cells, as a column-equivalent depth, including the rain
  recovered and waiting for the next synchronisation). Watching the conservation of
  S_total checks the water balance including the tanks. S_total decreases by the
  outflow from the system (`sfm_out_kind = 2`). The storage of the tanks is a different
  quantity from the groundwater `hg` and is not in the Hg distribution output.

**Time series** (`result/`, at `dt_recrd` intervals; values at the latest
synchronisation)

| File | Contents |
|---|---|
| sfm_zone.csv | per zone: rain (rain of the latest step, mm/h), q (runoff rate, mm/h), S (storage, mm), and cumulative water volumes (m³): vin (rain × zone area), vstore (current storage), vdrain (runoff of the zone), vsurface (transfer to surface cells), vexternal (outflow from the system), residual (balance residual = vstore − vstore₀ − vin + vdrain). When a zone has a baseflow, vbase is added as the last column, and vsurface and vexternal are runoff + baseflow |

The runoff of a zone [m³/s] is q × zone area / 3.6×10⁶, or the time difference of vdrain
divided by the recording interval. Check that residual is at the rounding level (about
10⁻¹² of the input).

**Screen**: at initialisation, a zone check table is shown (per zone: number of cells,
area, K, P, initial q and S, outlets and distribution ratios, number of baseflow points
and the first and last values).

**Restart**: the storage of the tanks, the internal step, the cumulative diagnostics
(including the baseflow) and the carry-over of the outlets are saved to and restored
from `sfm.dat`. When saving at a synchronisation time (a step that is a multiple of
`dt_sfm`), the computation after the restart is bit-identical to the continuous one.
When a computation ending in the middle of an interval is saved, the rest is
synchronised before saving (the recovered rain is not discarded). If fn_sfm is removed
at a restart while `sfm.dat` remains, the computation stops (so as not to discard the
storage of the tanks silently). It also stops if the configuration of zones, K, P or
outlets differs from the time of saving.

## Scope and restrictions on combinations

**Features that cannot be combined** in the first version (initialisation stops if they
are set): groundwater (`fn_gwflow`), snow (`fn_snow`), glaciers (`fn_glacier`),
landform change (`fn_geomorph`), water quality (`fn_wq`), the two freshwater–saltwater
layers (`fn_salt`), nesting and the STG grid (the same as VZ).
**It can be combined with VZ runoff (`fn_vz`)**. However, initialisation stops if the
cells of the zones overlap, or if an outlet of one is on a zone cell of the other.

**What cannot be placed on zone cells**: cells of channels (fn_rw), the sea (fn_sw),
boundary conditions, sources and structures.

**What it cannot do and the limits of accuracy**

- There is no lag time T_L, no separation of effective rainfall (f1, R_sa) and no
  two-valued storage function. A delay of the rise and hysteresis (different storage at
  the same discharge in the rising and falling limbs) cannot be represented.
- All rain enters the tank and eventually runs off. There is no loss by
  evapotranspiration or deep percolation, so in long computations the total runoff is
  overestimated (suited to event computations).
- Where in the zone the runoff arises (the contributing area) is not represented. The
  runoff of a zone moves to the outlet instantaneously and is not hindered when the
  outlet is flooded (backwater is not solved).
- Surface water that flows from upstream into the cells of a zone does not enter the
  tank (one-way).
- K and P are quantities calibrated for each catchment. Even if a plausible hydrograph
  is obtained, it cannot be used as a prediction of runoff without comparison with
  observations.
- States that stop the computation: negative input (rain), and the internal step falling
  below `sfm_dt_min` (normally does not happen). P is limited to 0 < P ≤ 1.

## Parameters and the basis of their defaults

The labels in the Basis column are explained in [How to read the basis of a default](../users_guide.md#how-to-read-the-basis-of-a-default).

**&list_sfm**

| Parameter | Default | Meaning | Basis |
|---|---:|---|---|
| f_sfm | 1 | 0 disables temporarily | **Method** |
| fn_sfm_zone | — | zone number raster (integer; 0 = not applied) | **Given** required |
| dt_sfm | 0 s | synchronisation interval for advancing the tanks (0 = every step) | **Numerical setting** every step, because a tank is a scalar and its cost is negligible |
| f_sfm_rain | 0 | 0: require identical rainfall within a zone / 1: area average within a zone | **Method** the side that stops and tells when not identical is the default |
| sfm_tol | 1e-4 | relative tolerance of the time error of the internal steps (ratio to the runoff rate) | **Verification case** in [test/sfzone](../../../test/sfzone/), the storage with every-step synchronisation is within 3×10⁻⁷ (relative) of the reference solution, and 1.5×10⁻⁵ with `dt_sfm = 60` s |
| sfm_dt_min | 0.001 s | lower limit of the internal step (stops below it) | **Numerical setting** |

**&list_sfm_zone** (indexed by the zone number z; up to 50 zones)

| Parameter | Default | Meaning | Basis |
|---|---:|---|---|
| sfm_k(z) | none | storage coefficient K (S [mm] = K·q[mm/h]^P; unit mm^{1−P}·h^P) | **Calibrated** required; changes by orders of magnitude between catchments |
| sfm_p(z) | 0.6 | storage exponent P (0 < P ≤ 1; 1 = linear reservoir) | **Conventional** the value conventionally used in the storage function method[^kimura1961]; corresponds to S ∝ q^{0.6} of the steady kinematic wave with Manning's law ([The tank](#the-tank-storage-function)) |
| sfm_q0_mmh(z) | 0.1 mm/h | initial runoff rate; the initial storage is S0 = K·q0^P (0 = dry) | **Empirical** a guide to the runoff rate before rain (the same as `vz_q0_mmh` of VZ) |
| sfm_out_kind(z) | none | outlet 1: surface cells / 2: out of the system | **Given** required |
| sfm_out_cell(1:2, k, z) | none | outlet cells (i, j) (up to 99) | **Given** required with sfm_out_kind = 1 |
| sfm_out_w(k, z) | 1 (one cell) | distribution ratios of the outlets (sum 1) | **Given** required with several cells |
| sfm_base(1:2, k, z) | none (no baseflow) | time series of baseflow (time (min), mm/h; per zone area; up to 100 points) | **Given** e.g. values separated from observations (the user's preprocessing) |
| fn_sfm_base(z) | none | file of the baseflow time series (one line "time(min) mm/h"; takes precedence over sfm_base) | **Given** |

**Hints for revising the defaults**

- **Calibrate K with the observed hydrograph**. A starting point is to choose K so that
  the measure of the response time K·P·q^{P−1} (h) matches the peak lag and the speed of
  the recession of the catchment. Doubling K doubles the response time at the same
  runoff rate.
- Changing P changes how the speed of the response depends on the size of the runoff
  (the smaller P, the faster the response to large floods and the slower to small ones).
  P = 1 is a linear reservoir with a constant time constant K [h] independent of the
  runoff.
- The initial runoff rate `sfm_q0_mmh` affects the response to the first rain. If the
  discharge before rain is observed, give it divided by the zone area. A long spin-up
  that is saved and used as the initial state through a restart is also possible
  ([interruption and restart](restart.md)).
- Checking that the result does not change when the time error tolerance `sfm_tol` is
  made 1/10 is a simple check of the numerical accuracy.

## Verification and examples

- [test/sfzone](../../../test/sfzone/): three zones (P = 0.6, 1, 0.4), several outlets and a
  shared receiving cell, outflow from the system. `Check_sfzone.py` tests: zone input =
  area × rain; storage of the linear reservoir (P = 1) = exact solution (relative
  3×10⁻⁷); storage and runoff rate with P = 0.6 and 0.4 = RK4 reference solution with
  fine steps (relative about 10⁻⁷); recession after the rain = analytic solution; steady
  state q → r and S = K·r^P under constant rain; depth of the receiving cells = transfers
  by the distribution ratios + rain; S_total balance; rain distribution and area
  averaging; stop of the strict mode; baseflow; display of defaults; synchronisation
  interval `dt_sfm = 60` s; save → restart agreement (including the middle of an
  interval); combination with VZ and stop on overlapping zones.
- Results are bit-identical regardless of the number of MPI processes (the tanks are
  computed identically on all ranks, and only the owner rank adds to the outlets).

## References

[^kimura1961]: Kimura, T. (1961): Flood runoff routing by the storage function method (in Japanese: 貯留関数法による洪水流出追跡法). Public Works Research Institute, Ministry of Construction. (The original of the storage function method. The bibliography is from web search results; the text has not been checked. That P = 0.6 has been conventionally used is also from secondary sources.)
