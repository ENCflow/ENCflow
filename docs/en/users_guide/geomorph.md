# Sediment and Landform Change (&list_geomorph)

> English mirror of docs/users_guide/geomorph.md (based on commit c7e801e). The Japanese file is the master copy.

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

**Policy on parameter defaults** - the material and calibration values of
every process have safe defaults that make it "just run", so **the
minimal input is the process switch (f_xxx = 1) alone**. Values adopted
while unspecified (0) are printed at startup with a **(default)** mark,
such as `geomorph: db_phi = 35.0000 deg (default)`, so they cannot go
unnoticed. Always review them against your case (guides by type of
phenomenon are in "[Recommended values by pattern](#recommended-values-by-pattern)"
at the end of this chapter). The rationale is in developer.md §62.

The evolving terrain can be output as `Z0001...` with `f_out_z = 1`
([the input/output chapter](io.md)). The probe CSV has columns for
suspended sediment hs and soil depth sd
([the measurement chapter](record.md)).

## Hillslope creep (f_creep)

| Parameter | Default | Meaning |
|---|---|---|
| creep_d | 1.6e-10 (= 0.005 m²/yr) | Creep diffusion coefficient (m²/s). Literature range 0.001-0.05 m²/yr. A geomorphic-time quantity, so interpret it together with morfac |

The minimal input to "just smooth the slopes" is `f_creep = 1` alone (no
soil depth needed; add morfac to see changes over years to millennia).

## Bedload (f_fluvial)

Riverbed erosion and deposition by a bedload transport formula.

| Parameter | Default | Meaning |
|---|---|---|
| f_qbform | 1 | Bedload formula. 1: Ashida-Michiue, 2: MPM |
| fluv_d50 | 0.01 | Representative grain size (m). The default is a middle value for sand-gravel beds (sand bed 0.0005 to mountain gravel bed 0.05) |
| fluv_tausc | 0.05 | Critical dimensionless shear stress tau*c |
| fluv_porosity | 0.4 | Riverbed porosity |
| fluv_sgrav | 1.65 | Submerged specific gravity of sediment grains |
| fluv_dzmax | 0.05 | Upper limit of bed change per update (m) (stabilization) |
| fluv_bcfeed | 0 | Sediment feed at open boundaries. 0: no feed at inflow, 1: equilibrium feed (outflow is always at transport capacity) |
| fluv_diagratio | 2/(2+sqrt(2)) | Diagonal partitioning (normally no need to change) |

The minimal input to "just move the bed" is `f_fluvial = 1` plus the
thickness of the erodible soil `sd0` (&list_geoinfo). The grain size is
the default 1 cm (the adopted value is printed at run time; guides for
sand and gravel beds are in the recommendations at the end).

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
| susp_d50 | 0.0002 | Representative grain size (m). The default is fine sand (representative of suspended load) |
| susp_wf | 0 | Settling velocity (m/s). If 0, derived from d50 by the Rubey formula |
| susp_tausc | 0.05 | Critical dimensionless shear stress for suspension |
| susp_beta | 1.0 | Near-bed concentration coefficient for settling |
| susp_esa | 1e-4 | Equilibrium concentration coefficient (used by f_esform=1; a calibration parameter; not used by Itakura-Kishi) |

The minimal input to "just carry some turbidity" is `f_suspend = 1` and
`sd0` (grain size defaults to fine sand 0.2 mm; the settling velocity is
derived automatically by the Rubey formula).

Sediment inflow from the boundaries (time series of concentration and
bedload discharge) is given by the segment inflows (inflow_cs /
inflow_qs) of [Boundary conditions](boundary.md).
Suspended sediment also serves as the partner of the Kd two-phase
partitioning (wq_kd) in [water quality](wq.md) (the particulate
fraction of sorbing substances such as heavy metals is allocated
according to the sediment concentration).

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

| Parameter | Default | Meaning |
|---|---|---|
| wash_kr | 0.01 | Raindrop erosion coefficient (dimensionless; E = kr x rainfall intensity) |
| wash_kf | 1e-5 | Sheet erosion coefficient (m/s) |
| wash_tausc | 0.05 | Critical dimensionless shear stress for sheet erosion |

kr and kf are empirical coefficients (calibration assumed). When both
are unspecified both get their defaults; when only one is given, the 0
of the other is read as "no such term".

The minimal input to "just erode the slopes" is `f_wash = 1` +
`f_suspend = 1` (the carrier of the detached sediment) + `sd0` +
rainfall (fn_precip).

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
| spl_kr | 0.0005 | Rainsplash coefficient (dimensionless); additive term that acts even on flat plateaus (S = 0). When both kr and kt are unspecified both get defaults; when only one is given the other stays 0 |
| spl_ca | 0 | Hollow-amplification length of the splash term (m) |
| spl_kt | 0.05 | Subgrid-rill coefficient (dimensionless); multiplies S^h |
| spl_cb | 0 | Hollow-amplification length of the rill term (m); strength of the valley-deepening feedback |
| spl_h | 1.0 | Slope exponent h of the rill term |
| spl_dzmax | 0 | Erosion cap per cell per update (m) (0: off); safety valve against runaway feedback |

The minimal input to "just carve valleys into a cliff" is `f_splash = 1`
+ `sd0` + rainfall (fn_precip) (kr and kt at their defaults; if the
positive valley feedback is wanted, set spl_cb to a few to a few tens of
meters).

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
| db_phi | 35 | Internal friction angle of the sediment (deg). Used by f_dbed=1-3 or f_dbres=1,2. The default is representative of gravelly debris (tan phi ≈ 0.7) |
| db_delte / db_deltd | 0.0007 / 0.05 | Rate coefficients for erosion / deposition (calibration parameters of f_dbed=1,3) |
| f_dbres | 1 | Resistance law. 0: Manning only, 1: Coulomb + Manning combined, 2: Egashira constitutive law (db_d50, db_erest), 3: Takahashi-Nakagawa 1991 stony type (db_d50), 4: Voellmy (db_mu, db_xi), 5: constant retarding stress (db_tauy) |
| f_dbcurv | 0 | Curvature term. 1 adds the centrifugal acceleration from the terrain curvature to the normal stress and scales the yield friction by (1 + a_c/g_n) (deceleration in hollows, reduced friction on convexities). Usable with f_dbres=1-4 (not 5). The same treatment as RAMMS; set it to 1 when importing mu and xi calibrated with RAMMS |
| f_dbstop / db_vstop / db_wstop | 0 / 0.05 / 0.05 | Stopping condition by low-speed consolidation (stopped sediment is fixed to the bed elevation z; natural dam formation) |
| db_d50 | 0.05 | Representative grain size (m). Used by f_dbed=3 and f_dbres=2,3. The default is the stony-type d_L (a few cm to dm) |
| db_erest | 0.85 | Particle restitution coefficient e. Used by f_dbres=2. The customary Egashira value |
| db_mu / db_xi | 0.2 / 1000 | Voellmy mu and xi (m/s²). Used by f_dbres=4. The defaults are mid-range RAMMS values (snow avalanches). Debris avalanches are smaller, mu 0.1 and xi 200-500 (recommendations below) |
| db_tauy | 10000 | Constant retarding stress tau_y (Pa). Used by f_dbres=5. The lower side of the 5-50 kPa pyroclastic-flow applications |
| f_dbwet / db_satbed | 0 / 1.0 | Pore-water entrainment (exchange of bed pore water with surface water on erosion/deposition; a first-order bulking effect where erosion dominates. Mutually exclusive with the groundwater computation) |

The minimal input to "just run a debris flow" is `f_debris = 1` + `sd0`
(the movable layer = erodible soil) + a source. The source is one of:
a collapse-depth distribution `fn_dbinit` (instantaneous mobilization),
a sediment-laden segment inflow at the upstream end
([Boundary conditions](boundary.md)), or the slope stability test
`f_slide = 1` (together with the groundwater computation). The
resistance law and E-D closure run as the simple debris flow of the
defaults (f_dbed=1, f_dbres=1, phi=35 deg). When the type is known, go
to the recommendations at the end of the chapter.

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

**Lahars (volcanic mudflows)** - generated by eruption-driven snow and
glacier melt or by the breach of a crater lake, they descend the valley
taking up deposits and water (bulking), then dilute downstream and
grade into a flood. They are treated not as an equivalent fluid but as a
**mixture whose concentration changes** (this is where using ENCflow
pays off).

- **Typical setup**: `f_debris = 1`; for the E-D use `f_dbed = 1`
  (Takahashi-type relaxation; delta_d sets how fast it deposits) or
  `f_dbed = 2` (Egashira-Ashida); for the resistance law use
  **`f_dbres = 4` (Voellmy, mu 0.05-0.1, xi 500) for fine ash slurries**
  or `f_dbres = 1` (Coulomb + Manning, phi 30-35 deg). The laminar
  resistance of the Egashira law (`f_dbres = 2`) scales with (h/d)^-2, so
  **with d50 of a millimetre or less the resistance vanishes and the
  velocity blows up** (it suits stony flows with d50 of centimetres or
  more). For boulder-dominated flows (sector-collapse origin, stony type
  descending a torrent) use `f_dbed = 3` + `f_dbres = 3`
  (Takahashi-Nakagawa). `f_dbwet = 1` (uptake of path pore water) is
  recommended as the first-order bulking effect. Working example:
  [examples/ashfall_lahar](../../../examples/ashfall_lahar/) (ash-thickness
  distribution → rainfall → mudflow → fan deposition).
- **How to initiate**: **erosion of an ash layer given as soil depth sd**
  (rain runoff on a steep slope picks up the ash to the equilibrium
  concentration — no source needs to be specified; examples/ashfall_lahar),
  a **sediment-laden segment inflow** at the
  upstream end (the supply hydrograph; inflow_cs of
  [Boundary conditions](boundary.md)), or a **chain** in which deposits
  from an earlier stage form a natural dam and breach (deposits fixed by
  f_dbstop=1 → overtopping breach → entrainment of downstream deposits).
  The collapse-depth distribution fn_dbinit is for sector-collapse
  origins.
- **Limits**: the thermal interaction of hot pyroclasts with snow and
  ice (the melt volume) is out of scope; give the meltwater as an inflow
  hydrograph. Dilute systems (pyroclastic surges) are out of scope
  (debris_plan.md §5).

**Curvature term (f_dbcurv)** - at bends, valley exits and knickpoints
the centrifugal acceleration from terrain curvature raises or lowers the
normal stress, changing the Coulomb friction (mu N). `f_dbcurv = 1` puts
this effect into the yield term (deceleration in hollows, reduced
friction on convexities; friction is cut to zero where the flow would
leave the ground). RAMMS calibrates mu and xi with this term included,
so set it to 1 in comparison runs that use those values. Curvature picks
up fine DEM roughness, so match the grid resolution to the model you
compare with. There is no effect on straight slopes (test/curvature).

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
  soil layer of cells with Fs < 1. Strength is given by `slide_c`
  (effective cohesion, Pa; default 0), `slide_phi` (shear resistance
  angle, deg; default 30) and `slide_gamma` (saturated unit weight,
  N/m^3; default 18000); the pore water pressure
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
  filling, sediment passes downstream by crest overflow. The map-scale
  generation, transport and deposition of driftwood is handled by
  [Driftwood](driftwood.md) (culverts carry no wood either, so the
  trapping is likewise an upper-bound estimate; geometric size-selective
  trapping by member spacing vs. log length is out of scope of the
  driftwood module as well).

## Moving bed layer / landslide tsunami (f_bedslide)

Represents the failed mass as "a bed layer hb that moves as part of the
terrain z (and the soil sd)" and runs it as an inertia-free,
friction-dominated flow (Voellmy law) from land into water. When the
layer moves, the bed z rises and falls while the water depth h is kept,
so the water surface lifts (or draws down) - **generation, propagation
and run-up of a landslide tsunami are chained without any extra
settings** (the moving-seabed approach; design in
docs/landslide_tsunami_plan.md). The difference from the debris-flow
model above (a mixture bound to the water column) is that **it runs
underwater even where the water surface is flat** (driving head
Phi = z + (rho_w/rho_s) h; buoyancy reduces driving and friction
together). Use it for debris avalanches and sector collapses plunging
into lakes or the sea, and for prescribed submarine landslides.
Represent the water body as a "solved sea" (no sea mask: real bathymetry
plus an initial water level f_htype=2, long-wave radiation f_bc_*=2 on
the edges).

| Parameter | Default | Meaning |
|---|---|---|
| f_bedslide | 0 | 1 enables it (morfac=1 required) |
| fn_bsinit | - | Collapse-depth distribution (m). **Required** (the trigger is given data; z is unchanged and hb = min(D, sd) becomes movable) |
| bs_reltime | 0 | Release time (s) |
| bs_rho | 2000 | Bulk density of the mass (kg/m³, pores included; buoyancy ratio r = 1000/rho_s). The default is representative of saturated soil and rock debris (r = 0.5). 0 uses the default and init prints the adopted value with "(default)" |
| f_bsres | 1 | Resistance law. 1: Voellmy (inertia-free; V = sqrt(xi hb (S - mu b))). 2 (Bingham) is reserved |
| bs_mu / bs_xi | 0.15 / 500 | Voellmy mu and xi (m/s²). The defaults are the calibrated values of the inertia-free bed layer (as in examples/landslide_tsunami). Named separately from the mixture's db_mu/db_xi (calibration differs with and without inertia) |
| bs_vstop | 0.05 | Velocity threshold for stopping (m/s; hb of cells below it is fixed to the terrain; irreversible) |
| bs_tstop | 0 | Duration of slow motion required before fixing (s). 0 = immediate. To avoid false fixing during the ten-odd seconds in which the shoreline zone dewaters and the layer stalls on plunging, 10-15 s (longer than the dewatering) is recommended for plunging cases |
| bs_eps_s | 0.02 | Linearization width near yield (dimensionless slope; smaller means more subcycles) |
| bs_diagratio | 0.5858 | Diagonal share of the 8-direction partitioning (0 for 4 neighbors; for analytic comparisons) |
| bs_cfl / bs_nsubmax | 0.4 / 10000 | Safety factor and cap of the subcycling |
| bs_hplunge | 0 | Ponded-depth threshold (m) for the **handover** from the mixture (hs of the debris-flow model) to the bed layer. 0 = none. Needs f_debris=1. When given, fn_bsinit may be omitted (the trigger is the handover only) |
| f_bsvplunge | 0 | Velocity condition of the handover. 1 hands over only after the mixture has slowed to the terminal velocity of the bed layer after handover (the momentum of a fast plunge is passed to the water column while still a mixture; recommended for fast plunges from land) |
| f_bsplunge | 0 | Ponded depth used for the handover test. 0: the current depth h, 1: the still-water depth (initial surface minus the current bed z; only cells initially wet). Use 1 to hand over even when the shoreline zone dewaters temporarily on plunging |

The minimal input to "just give a collapse-depth map and run" is
`f_bedslide = 1` and `fn_bsinit` (material and calibration values at
the defaults above; the adopted values are printed at run time, so
always review them against your case. Make the soil depth sd0 at least
the collapse depth).

Working example: [examples/landslide_tsunami](../../../examples/landslide_tsunami/)
(a debris avalanche, debris flow → handover, mixture only, and a
submarine landslide on the same terrain, with figures and the reasons
for the settings).

Outputs Hb (layer thickness) and Vb (layer velocity; diagnostic) are
added automatically. Restart uses the private file
`geomorph_bedslide.dat`.

**Run time**: the layer advances in small steps (subcycles) within the
water time step to satisfy its stability conditions (advection and a
diffusion-type condition near yield), so while the mass is moving the
**total run time is about 1.5-2.5 times** (2.7 s → 4-6 s in
examples/landslide_tsunami). This is not an anomaly. At the end,
"bedslide subcycles total = ... (max ... per update)" reports the count.
If the count is extreme or the run stops on exceeding bs_nsubmax, the
first remedy is a larger bs_eps_s (0.02 → 0.05) (mechanism and order of
remedies in developer.md §61.10).

**How to give the failure surface**: give fn_bsinit as a "planar slip
surface that daylights at the slope foot" (depth going to 0 toward the
foot). A box of constant depth becomes a pit with a wall on the
downstream side and the mass cannot leave it (a surface-slope-driven
inertia-free flow cannot climb a step - the same holds for the
debris-flow model).

**Properties to be aware of (deliberate simplifications)**:
- Inertia-free: it moves at terminal velocity right from release (the
  10-20 s acceleration phase is omitted). **The direction of the bias
  flips with the case**: for a submarine landslide released underwater
  the near-field wave is on the high side; for a fast plunge from land
  the layer drops at once to its underwater terminal velocity, so the
  near-field wave is on the low side. For the latter, use the handover
  route "on land = debris-flow model (mixture, with inertia), underwater
  = bed layer" together with f_bsvplunge=1, and check the size of the
  bias with the "plunge speeds" in the Log (mixture and layer velocities
  at handover). Stopping is immediate on yield (bs_tstop can require a
  duration).
- The surface of a layer that has not stopped spreads until its slope
  falls below mu (it also flows back into the scar under its own
  weight). A small mu spreads thin.
- No water drag or added mass (fold them into xi). No non-hydrostatic
  or dispersive effects (SWE).
- Along walls, the 8-direction partitioning produces a boundary layer of
  reduced throughput (closed within the row for grid-aligned walls,
  spreading inward for 45-degree walls). Harmless at the edges of real
  terrain, but mind the section location in narrow idealized flumes.
- **Combination with the debris-flow model (handover)**: run the flow on
  land with the debris-flow model (mixture hs) and, in cells with
  ponded depth h >= bs_hplunge, convert hs to bulk volume hs/(1-lambda)
  and move it to the bed layer hb (the surface height conserves the
  solids; the pore fraction is buried from the water column with
  f_dbwet=1, or raises the surface with 0). The mixture's momentum is
  lost (the layer has no inertia). Right after plunging, the water of
  the shoreline zone is pushed offshore and dewaters temporarily, and
  the layer stalls. With bs_tstop=0 it is fixed there and a lobe is left
  on the shoreline, so combine with bs_tstop (10-15 s). The part of the
  mixture arriving during dewatering that is left behind because it is
  below bs_hplunge can be reduced with f_bsplunge=1 (test with the
  still-water depth). A dry large-scale collapse is more naturally given
  as a bed layer from the start with fn_bsinit. In test/bedslide
  configuration 4, without handover (mixture only) the material piles up
  near the shoreline and never reaches the lake bottom, whereas with
  handover it runs to the flat lake bottom and deposits there.

## Long-term landform evolution (f_wthr / f_uplift)

Processes for millennial-scale landform evolution experiments (used in
combination with morfac and restart chains).

| Parameter | Default | Meaning |
|---|---|---|
| wthr_p0 | 50 | Soil production rate on bare bedrock (mm/kyr). The middle of the literature range 0.01-0.1 mm/yr |
| wthr_sdstar | 0.5 | Decay depth of production (m) (an exponential law: the thicker the soil, the slower the weathering) |
| uplift0 | 1.0 | Uplift rate (mm/yr). Negative for subsidence. The lower end of representative orogenic values |

The minimal input to "just let the landscape evolve" is `f_wthr = 1`
(+ `sd0`) and `f_uplift = 1`, with `f_creep = 1` for the slopes,
`f_fluvial = 1` for the rivers, and `morfac` (acceleration of geomorphic
time). The defaults are quantities on year-to-millennium scales, so first
decide how many years the run time tt x morfac represents.

## Recommended values by pattern

The defaults are middle-of-the-road values that make the model "run".
When the type of phenomenon is known, start from the following
(calibration quantities; sources in developer.md §28 and §62).

| Type | Resistance / E-D | mu | xi (m/s²) | tau_y (kPa) | d50 (m) | phi (deg) | Notes |
|---|---|---|---|---|---|---|---|
| Dense-flow snow avalanche | f_dbed=4 + f_dbres=4 | 0.15-0.3 | 1000-3000 | - | - | - | Larger events: smaller mu, larger xi (Swiss guideline tables) |
| Debris avalanche (sector collapse) | f_dbed=0 or 4 + f_dbres=4 | 0.05-0.15 | 200-500 | - | - | - | The apparent friction H/L falls with volume → give it directly through mu |
| Dense pyroclastic flow | f_dbed=0 + f_dbres=5 | - | - | 5-50 | - | - | VolcFlow-type applications |
| Stony debris flow (Japanese type) | f_dbed=3 + f_dbres=3 | - | - | - | 0.05-0.3 | 35 | Takahashi-Nakagawa 1991. Grain size = representative boulders of the front |
| Mudflow, fine sediment flow | f_dbed=2 + f_dbres=2 | - | - | - | 0.001-0.01 | 30-35 | Egashira constitutive law. e ≈ 0.85 |
| Lahar (volcanic mudflow) | f_dbed=1 or 2 + f_dbres=4 (fine) / 1; 3+3 when boulder-dominated | 0.05-0.1 | 500-1000 | - | 0.001-0.01 | 30-35 | Initiated by erosion of the ash layer (sd), a sediment-laden segment inflow or a breach chain. f_dbwet=1 recommended. The Egashira laminar law is not usable for fine material. See the "Lahars" paragraph above and examples/ashfall_lahar |
| Simple debris flow (calibration-driven) | f_dbed=1 + f_dbres=1 | - | - | - | - | 30-35 | Calibrate the runout with delta_e and delta_d |
| Bed change of a sand-bed river | f_fluvial (+ f_suspend) | - | - | - | 0.0003-0.001 | - | Large contribution of suspended load |
| Bed change of a gravel-bed river | f_fluvial | - | - | - | 0.02-0.1 | - | Bedload dominates |
| Long-term landform evolution | f_creep + f_wthr + f_uplift | - | - | - | - | - | creep_d 0.001-0.05 m²/yr, p0 10-100 mm/kyr, uplift 0.1-5 mm/yr. Together with morfac |
| Landslide tsunami (bed layer) | f_bedslide | 0.1-0.2 | 300-1000 | - | - | - | mu and xi of the inertia-free bed layer (bs_mu/bs_xi). Calibrated separately from the mixture values |

## Examples

Annotated list of all parameters:
[examples/List_samples/list_geomorph.txt](../../../examples/List_samples/en/list_geomorph.txt).
Verified test cases exist per process:
[test/creep](../../../test/creep/) (analytical-solution benchmark),
[test/fluvial](../../../test/fluvial/), [test/suspend](../../../test/suspend/),
[test/wash](../../../test/wash/), [test/debris](../../../test/debris/),
[test/slide](../../../test/slide/), [test/avalanche](../../../test/avalanche/),
[test/sedinflow](../../../test/sedinflow/) (boundary sediment supply),
[test/bedslide](../../../test/bedslide/) (moving bed layer: analytic
velocity, grid-dependence detection on a 45-degree slope, plunge into a
lake and wave generation).
