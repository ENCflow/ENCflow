# Sediment and Landform Change (&list_geomorph)

> English mirror of docs/users_guide/geomorph.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Handles sediment transport and the temporal evolution of the terrain.
Enable it with `fn_geomorph`. The processes are **superposed, not
mutually exclusive** - the enabled ones are applied in order. The
terrain (computational elevation) and the soil depth change during the
run and feed back into the flow.

| Process | Flag | Content |
|---|---|---|
| Hillslope creep | f_creep | Slope relaxation by linear diffusion |
| Bedload | f_fluvial | Riverbed erosion and deposition (Exner equation) |
| Suspended sediment | f_suspend | Advection of concentration + entrainment and settling |
| Hillslope erosion | f_wash | Raindrop + sheet erosion (requires f_suspend) |
| Dry-slope erosion | f_splash | Rainsplash + subgrid rills without overland flow (dry cells) |
| Debris flow / landslide | f_debris / f_slide | Takahashi-type E-D, slope stability test |
| Bedrock weathering / uplift | f_wthr / f_uplift | Long-term landform evolution (millennial scale) |

## Run control (common to all processes)

| Parameter | Default | Meaning |
|---|---|---|
| dt_geomorph | 0 | Update interval of landform change (s). 0: every step |
| morfac | 1.0 | Morphological acceleration factor. Multiplies only the landform change by morfac so that a short run represents a long period (for equilibrium landforms and year-order studies; use 1 in event runs) |

The evolving terrain can be output as `Z0001...` with `f_out_z = 1`
([the input/output chapter](io.md)). The probe CSV has columns for
suspended sediment hs and soil depth sd
([the measurement chapter](record.md)).

## Hillslope creep (f_creep)

| Parameter | Meaning |
|---|---|
| creep_d | Creep diffusion coefficient (m^2/s) |

## Bedload (f_fluvial)

Riverbed erosion and deposition by a bedload transport formula.

| Parameter | Default | Meaning |
|---|---|---|
| f_qbform | 1 | Bedload formula. 1: Ashida-Michiue, 2: MPM |
| fluv_d50 | - | Representative grain size (m). **Required** |
| fluv_tausc | 0.05 | Critical dimensionless shear stress tau*c |
| fluv_porosity | 0.4 | Riverbed porosity |
| fluv_sgrav | 1.65 | Submerged specific gravity of sediment grains |
| fluv_dzmax | 0.05 | Upper limit of bed change per update (m) (stabilization) |
| fluv_bcfeed | 0 | Sediment feed at open boundaries. 0: no feed at inflow, 1: equilibrium feed (outflow is always at transport capacity) |
| fluv_diagratio | 2/(2+sqrt(2)) | Diagonal partitioning (normally no need to change) |

Combined with the subgrid channel width (fn_width), bedload
concentrates in the channel width and changes the riverbed there
([the channel chapter](channel.md)).

## Suspended sediment (f_suspend)

Advects the concentration field (columnar equivalent hs) with the flow
and exchanges with the riverbed through entrainment (E) and settling
(D).

| Parameter | Default | Meaning |
|---|---|---|
| f_esform | 1 | Equilibrium concentration formula. 1: linear excess shear (simple), 2: Itakura-Kishi |
| susp_d50 | - | Representative grain size (m). **Required** |
| susp_wf | 0 | Settling velocity (m/s). If 0, derived from d50 by the Rubey formula |
| susp_tausc | 0.05 | Critical dimensionless shear stress for suspension |
| susp_beta | 1.0 | Near-bed concentration coefficient for settling |
| susp_esa | - | Equilibrium concentration coefficient (required for f_esform=1; a calibration parameter) |

Sediment inflow from the boundaries (time series of concentration and
bedload discharge) is given by the segment inflows (inflow_cs /
inflow_qs) of [Boundary conditions](boundary.md).

**Tsunami / storm-surge resuspension and deposition in the run-up zone
(tsunami deposits)** - resuspension of bay-bottom mud or sand and its
deposition in the run-up zone can be represented with f_suspend. One
important condition: **sea-mask (fn_sw) cells do not solve the flow,
and none of the landform-change processes act on sea cells**. Represent
the water body to be resuspended not as a sea mask but as ordinary
cells with real bathymetry z plus an initial water level (f_htype=2 in
[Initial conditions](initial.md)), and let the tsunami enter through
the long-wave radiation edge boundary (type 2) or
water-level-prescribed cells ([Boundary conditions](boundary.md)).
Give the thickness and extent of the erodible layer as the soil depth
sd (sd=0 means non-erodible).

- **Sand**: the model's native regime. f_esform=2 (Itakura-Kishi) with
  susp_wf=0 (Rubey-derived) works without calibration parameters.
  Where the bedload contribution matters (run-up front, shallow
  high-velocity return flow), superpose f_fluvial.
- **Mud (cohesive)**: handled by reinterpretation. Give the effective
  floc settling velocity directly as susp_wf (on the order of
  1e-4 to 1e-3 m/s; the Rubey derivation is unrealistic at clay grain
  sizes), regard the f_esform=1 law E = wf*esa*(tau*/tau*c - 1) as
  identical in form to the Partheniades law E = M(tau/tau_ce - 1), and
  calibrate susp_esa and susp_tausc to the mud's erosion rate constant
  and critical shear stress. Flocculation and consolidation are not
  represented explicitly.

In the run-up zone settling dominates as the flow decelerates, and in
cells that dry out the entire suspended load is fixed to the bed. The
deposit thickness is obtained as the before/after difference of z
(f_out_z; the probe CSV also has hs and sd columns). Being single
grain size, the scope is deposit thickness and extent - the spatial
grain-size distribution (inland fining) is not represented. hs is a
passive scalar under the dilute assumption; high-concentration mud
flows (density currents) are out of scope.

**The sea mask (fn_sw) and the fate of sediment** - sea cells behave
as the following boundary for sediment: **suspended sediment leaving
into a sea cell is treated as lost from the system** (a perfect sink;
inflow from the sea to the land is always clear water), and **bedload
does not cross an edge bordering a sea cell** (a wall; sand piles up
artificially along the seaward front). Wherever you want deposition on
the sea bottom or seaward landform change to be solved (formation of a
river-mouth terrace, the tsunami deposits above), represent that area
as ordinary cells + an initial water level, and if you use a sea mask,
place it offshore of the area of interest.

## Hillslope erosion (f_wash)

Detaches sediment from hillslopes by raindrop erosion and sheet
erosion and carries it as suspended sediment (**f_suspend is
required**). Detachment reduces the soil depth sd.

| Parameter | Meaning |
|---|---|
| wash_kr | Raindrop erosion coefficient (dimensionless; E = kr x rainfall intensity) |
| wash_kf | Sheet erosion coefficient (m/s) |
| wash_tausc | Critical dimensionless shear stress for sheet erosion |

## Dry-slope erosion (f_splash)

Erosion and valley formation on **slopes without overland flow**. On
highly permeable slopes where all rainfall infiltrates (badlands,
pyroclastic cliffs), the terrain is carved by raindrop impact and by
subgrid-scale rills and grain rolling that the grid cannot resolve.
The erosion efficiency increases in hollows (incipient valleys) — a
positive feedback that lets **valleys grow from cliff margins without
any surface runoff**.

The erosion rate is (P: rainfall intensity reaching the ground, S:
slope, kappa: curvature, positive in hollows):

E = P [ spl_kr (1 + spl_ca kappa) + spl_kt (1 + spl_cb kappa) S^spl_h ]

It acts on **dry cells only** (h <= dd) and is complementary to f_wash
(wet cells); combining them does not double-count. Detached sediment
is not transported but **exported out of the system** (an
approximation of open systems where steep cliffs shed to the sea; the
total exported volume is reported at the end). Detachment reduces the
soil depth sd, and erosion stops at sd = 0 (bedrock exposure), closing
the budget with weathering (f_wthr). Whether valleys form at all
depends on cliff cohesion (slopes that cannot stand steeper than the
angle of repose do not preserve hollows) — combine with f_slide to
represent this.

| Parameter | Default | Meaning |
|---|---|---|
| spl_kr | 0 | Rainsplash coefficient (dimensionless); additive term that acts even on flat plateaus (S = 0) |
| spl_ca | 0 | Hollow-amplification length of the splash term (m) |
| spl_kt | 0 | Subgrid-rill coefficient (dimensionless); multiplies S^h |
| spl_cb | 0 | Hollow-amplification length of the rill term (m); strength of the valley-deepening feedback |
| spl_h | 1.0 | Slope exponent h of the rill term |
| spl_dzmax | 0 | Erosion cap per cell per update (m) (0: off); safety valve against runaway feedback |

Working example: [examples/badland](../../../examples/badland/) (in
Japanese; long-duration rain on a plateau-and-cliff terrain grows
valleys from the cliff margin with zero surface runoff). The
cohesion contrast (whether valleys form at all) is in
[test/splashslide](../../../test/splashslide/).

## Debris flow / landslide (f_debris / fn_dbinit / f_slide)

Handles debris flows as a single-layer mixture of surface water and
sediment (flow depth = h + hs). The erosion-deposition (E-D) closure
and the resistance law are each selectable. **Mutually exclusive with
f_suspend** (to avoid double-counting the same concentration field),
and **morfac=1 is required** (event runs). For steep terrain we
recommend `f_gravity_correction = 1` in &list_enc.

| Parameter | Default | Meaning |
|---|---|---|
| f_dbed | 1 | E-D closure. 0: no exchange (equivalent fluid; see volcanic flows below), 1: relaxation to the equilibrium concentration (simplified), 2: Egashira-Ashida 1992, 3: Takahashi-Nakagawa 1991 (requires db_d50), 4: velocity-proportional entrainment E = δe·|V| (path entrainment for avalanches and debris avalanches; entrainment only — deposition via f_dbstop; see the snow-avalanche paragraph below) |
| db_phi | - | Internal friction angle of the sediment (deg). **Required** when f_dbed>=1 or f_dbres=1,2 |
| db_delte / db_deltd | 0.0007 / 0.05 | Rate coefficients for erosion / deposition (calibration parameters of f_dbed=1,3) |
| f_dbres | 1 | Resistance law. 0: Manning only, 1: Coulomb + Manning combined, 2: Egashira constitutive law (requires db_d50, db_erest), 3: Takahashi-Nakagawa 1991 stony type (requires db_d50), 4: Voellmy (requires db_mu, db_xi), 5: constant retarding stress (requires db_tauy) |
| f_dbstop / db_vstop / db_wstop | 0 | Stopping condition by low-speed consolidation (stopped sediment is fixed to the bed elevation z; natural dam formation) |
| f_dbwet / db_satbed | 0 / 1.0 | Pore-water entrainment (exchange of bed pore water with surface water on erosion/deposition; a first-order bulking effect where erosion dominates. Mutually exclusive with the groundwater computation) |

**Volcanic flows (debris avalanches, dense pyroclastic flows,
lahars)** - density flows without bed erosion can be approximated with
the "equivalent fluid" setup `f_dbed = 0` (no exchange) plus
`f_dbres = 4` (Voellmy) or `5` (constant retarding stress) - the same
formulation level as dedicated volcanic-flow models. Initiate them with the
instantaneous mobilization below (fn_dbinit) or with a
sediment-laden inflow boundary (eruption supply rate), and fix stopped
material to the terrain with f_dbstop=1. Deposition, natural dam
formation, dam-break flooding, and rainfall-triggered secondary lahars
are all chained within a single run. If **entrainment of path
deposits** is needed (a debris avalanche growing by incorporating
colluvium or pyroclastic deposits along its path), use
`f_dbed = 4` (velocity-proportional entrainment E = δe·|V|) and give
the entrainable layer thickness as the soil depth sd (the mechanism
and setup are the same as in the snow-avalanche paragraph below —
only the reinterpretation of the entrainable layer differs). Dilute
phenomena (pyroclastic surges, plumes, atmospheric ash transport) are
out of scope by design (see debris_plan.md §5).

**Snow avalanches (dense flow)** - the same equivalent-fluid setup is
also the standard formulation for dense-flow snow avalanches. The
Voellmy law (μ + gV²/ξ) was originally developed for avalanches, and
the workflow is the same as operational avalanche models: give the
release area and fracture depth, and compute runout and deposition.
Voellmy dynamics are density-independent (both driving and resistance
are in acceleration form, so density cancels), which is why snow being
much lighter than water does not affect the runout computation.
Avalanches **borrow** the sediment-flow model, reinterpreting its
reservoirs in snow terms (the parameter names keep their sediment
vocabulary):

| Model quantity (sediment name) | Reinterpretation for avalanches |
|---|---|
| sd (soil depth = movable layer) | entrainable snow depth along the path |
| hs (sediment column) | (net) volume of flowing snow |
| z (elevation) | snow-surface elevation (z − sd is the ground) |
| fluv_porosity λ | snow-porosity interpretation (keep it small so hs ≈ snow depth) |
| collapse depth D of fn_dbinit | fracture depth of the release area |
| bed fixing of f_dbstop | deposition of the stopped snow (debris) |

Through this reuse, the verified conservation machinery (solid budget
and the co-update identity) applies to snow as well. Dense-flow snow
avalanches and sediment density flows are the same "granular
shallow-water flow", so the reuse rests on an identity of
formulation, not on appearances.

- **Typical setup**: `f_debris = 1`, `f_dbed = 4`
  (**velocity-proportional entrainment** of path snow, E = δe·|V|; use
  0 if entrainment is not needed), `f_dbres = 4`
  (μ = db_mu ≈ 0.15-0.3 and ξ = db_xi ≈ 1000-3000 m/s² are the
  customary avalanche ranges), `f_dbstop = 1` (fix stopped material to
  the terrain). Give the release area and fracture depth (snow
  thickness) with `fn_dbinit`, and the release time with
  `db_reltime`. The **entrainable snow depth along the path is given
  as the soil depth sd** (sd0 / fn_sd; z is the snow-surface
  elevation and z−sd the ground; the entrainment coefficient
  `db_delte` is a calibration parameter, typically 0.01-0.05).
  A small `fluv_porosity` (e.g., 0.1) makes hs read
  approximately as snow thickness. Keep `db_relsat` small (e.g.,
  0.1-0.15) - the mixture model carries a small amount of water as the
  carrier fluid, and that water remains and drains after the avalanche
  stops (a minor artifact if the amount is small). Steep terrain, so
  `f_gravity_correction = 1` is recommended.
- **What it cannot do (honest limits)**: (1) powder-snow
  avalanches are out of scope (an air suspension - outside the
  shallow-water approximation), (2) release is not predicted (the
  release area and fracture depth are inputs - the same as dedicated
  avalanche models, where release is given as a scenario), (3) impact
  pressures need conversion (F9999 is normalized by the freshwater
  density; use the flowing-snow density of 200-400 kg/m³ for avalanche
  impact pressures), (4) no automatic coupling with the snow (SWE)
  module (to chain from a winter snowpack run, convert SWE to sd in
  preprocessing).
- A verified example is [test/avalanche](../../../test/avalanche/)
  (release → growth to 1.5x by entrainment → stopping on the flat;
  solid ledger at machine precision). The Voellmy steady uniform-flow
  analytic benchmark (0.04% agreement) is continuously tested in
  [test/volcano](../../../test/volcano/) configuration 1 (the same
  resistance law). Comparison with observed avalanche runouts has not
  been done. The "avalanche redistribution" in the glacier module is a
  slow slope redistribution of snow for accumulation - a different
  thing from the dynamic avalanche flow described here.

**There are two ways to trigger a debris flow** (they can be combined):

- **Instantaneous mobilization (fn_dbinit)** - give a distribution
  file of collapse depths; the soil layer is mobilized at
  `db_reltime` (s). `db_relsat` is the saturation of the collapsed
  mass (if the groundwater computation is enabled, its water is used
  instead).
- **Slope stability test (f_slide=1)** - evaluates the infinite-slope
  safety factor Fs at every update and automatically mobilizes the
  soil layer of cells with Fs < 1. `slide_c` (effective cohesion, Pa),
  `slide_phi` (shear resistance angle, deg), and `slide_gamma`
  (saturated unit weight, N/m^3) are required; the pore water pressure
  is taken from the saturated thickness of the groundwater computation
  (rainfall -> groundwater rise -> slope failure -> debris flow are
  linked in a single time evolution). `f_slide = 2` is a
  **judge-only** diagnostic mode (no mobilization) for producing an
  undisturbed hazard map.

**Hazard outputs** - output switches in &list_sysparam provide
statistical fields representing sediment-hazard intensity (see also
the table in [Input and output](io.md)): `f_out_fs` (safety factor Fs
distribution and its period minimum Fs9999 = slope failure hazard
map; **requires f_slide = 1 or 2**), `f_out_dmax` (maximum flow depth
h+hs, D9999 = debris flow inundation depth), `f_out_fmax` (maximum
fluid force (ρm/ρw)·(h+hs)·V², F9999 = a standard indicator for
building damage; includes the mixture density, and for water-only
runs it equals the conventional u²h), and `f_out_hs` (sediment column frames). If the hazard map
is all you need, the recommended pair is **f_slide = 2 (judge only)
with f_out_fs = 1** - with f_slide = 1 the failures alter the terrain
and groundwater, so the subsequent Fs field reflects the disturbed
state (Fs9999 still keeps the pre-failure hazard). The saturation
ratio - a precursor indicator for shallow slope failure - can be
derived in post-processing as hg/(sy0·sd) from the Hg (`f_out_hg`)
and Sd outputs. The operational warning indicator itself - the JMA
Soil Water Index - can be computed in a dedicated run
([Soil Water Index](swi.md)).

**Representing sabo facilities (sediment-retarding basins, check
dams)** - the effect of a countermeasure facility is studied as a
two-case comparison (with / without). The difference is only in the
inputs (terrain and settings), and results are bit-reproducible
regardless of rank or thread count, so the difference between the two
cases is exactly the facility's effect, cleanly separated from
numerical noise.

- **Sediment-retarding basin (yusachi)**: just carve the excavation
  and widening into the terrain z in preprocessing. Deposition by
  slope reduction and deceleration (fixed to the terrain with
  f_dbstop=1) acts automatically, and the trap efficiency (deposit
  volume inside the facility / sediment inflow) and the sediment load
  passed downstream can be quantified from the time evolution of Hs
  and z and from D9999/F9999.
- **Closed-type check dam**: add the dam body to the terrain z and set
  the soil depth there to sd=0 (non-erodible). The time evolution of
  sedimentation -> filling -> crest overflow emerges automatically
  (the same framework as landslide-dam formation and overtopping). To
  represent the body as a wall thinner than a cell, the channel levee
  (bank; [Channels](channel.md)) can be used - on overtopping the
  sediment (hs) crosses together with the water as a real flux.
- **Open-type (slit / grid) check dam**: being single grain size, the
  size selectivity ("trap coarse boulders and driftwood, pass fines
  and water") cannot be represented. Giving the dam body
  (non-erodible terrain) an outlet with a culvert
  ([Structures](structure.md); it transfers clear water only and
  carries no sediment) yields the approximation "passes water, traps
  all sediment" = an **upper-bound estimate of trapping**. After
  filling, sediment passes downstream by crest overflow. Driftwood is
  not modeled.

## Long-term landform evolution (f_wthr / f_uplift)

Processes for millennial-scale landform evolution experiments (used in
combination with morfac and restart chains).

| Parameter | Meaning |
|---|---|
| wthr_p0 | Soil production rate on bare bedrock (mm/kyr). **Required** |
| wthr_sdstar | Decay depth of production (m) (an exponential law: the thicker the soil, the slower the weathering) |
| uplift0 | Uplift rate (mm/yr). **Required** |

## Examples

Annotated list of all parameters:
[examples/List_samples/list_geomorph.txt](../../../examples/List_samples/en/list_geomorph.txt).
Verified test cases exist per process:
[test/creep](../../../test/creep/) (analytical-solution benchmark),
[test/fluvial](../../../test/fluvial/), [test/suspend](../../../test/suspend/),
[test/wash](../../../test/wash/), [test/debris](../../../test/debris/),
[test/slide](../../../test/slide/), [test/avalanche](../../../test/avalanche/),
[test/sedinflow](../../../test/sedinflow/) (boundary sediment supply).
