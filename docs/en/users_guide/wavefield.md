# Coastal wave field (fn_wavefield)

> English mirror of docs/users_guide/wavefield.md. The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

This feature computes the height and direction of coastal short-period waves (wind sea
and swell) on the same grid and in the same time evolution as the shallow water flow.
Offshore waves (height, period, direction of travel, directional spreading) enter from
the outer sides of the domain, and the model computes shoaling (the change of wave
height with depth), refraction (bending towards shallower water), breaking, bottom
friction and the shadows behind breakwaters and islands.

The waves are **phase-averaged** (the rise and fall of the water surface wave by wave
is not resolved; the distribution of wave energy is), with **one representative
period** and the direction of travel split into **N_θ directional bins**: a rough
estimate. Frequency spreading, wind growth, nonlinear wave–wave interactions,
diffraction and reflection are not treated.

Depending on the settings, the wave field also acts on the flow and on sediment. All
of these default to 0 (no action).

| Action | Parameter that enables it | What it represents |
|---|---|---|
| [Action on the flow](#action-on-the-flow-wf_flow) | `wf_flow` (&list_wavefield) | Wave setup (a rise of the mean water level near the shoreline), longshore currents, undertow |
| [Change of waves by currents](#change-of-waves-by-currents-f_wf_current) | `f_wf_current` (&list_wavefield) | Waves on river mouths, tidal currents and rip currents (Doppler shift, refraction by currents, blocking of propagation up a river) |
| [Action on sediment](#action-on-sediment-f_wfsed) | `f_wfsed` (&list_geomorph) | Stirring and transport of sediment by waves (longshore transport, beach erosion and recovery) |
| [Swash-zone transport](#swash-zone-transport-f_wfswash) | `f_wfswash` (&list_geomorph) | Piling up of sand above the shoreline and erosion of the foreshore (empirical formulas) |

With `wf_flow = 0` and `f_wfsed = 0` the shallow water and bed results are the same
whether or not `fn_wavefield` is written.

It is a different feature from "longshore transport by waves" in the
[sediment and morphology chapter](geomorph.md) (`fn_wave`, a simplified mode that does
not solve the waves and gives the longshore transport in the shoreline band from the
offshore waves with a CERC-type formula).

The governing equations, numerical methods and basis of the defaults, the distinction
between the other models it draws on (XBeach, SnapWave and others) and the parts
original to ENCflow, and the references are in
[Coastal wave field explained](wavefield_models.md).

## Trying it out (minimal input)

Specify `fn_wavefield` in `&list_sysparam` (`"-"` means the same parameter file) and write the
incident sides and the offshore waves in `&list_wavefield`.

```
&list_sysparam
  fn_wavefield = '-'
/
&list_wavefield
  wf_bc_side = 1, 0, 2, 2   ! type of the sides W, E, N, S (0 absorbing / 1 incident / 2 lateral Neumann)
  wf_hm0 = 1.5              ! offshore wave height (m; significant wave height H_m0 for random waves)
  wf_trep = 8.0             ! representative period (s)
  wf_dir = 0.0              ! direction of travel (deg; counterclockwise from the x axis = east, north = 90)
  wf_spread = 20.0          ! directional spreading sigma_theta (deg)
/
```

All that is needed is **an incident side** and **the offshore waves** (`wf_hm0`,
`wf_trep`, `wf_dir`).

**The direction is the direction the waves travel to** (not the direction they come
from). It is measured counterclockwise from the x axis (east): a wave travelling north
is 90°, one travelling west is 180°. This is the same convention as `wave_dir` in the
[sediment and morphology chapter](geomorph.md), and differs by 180° from the
"coming from" (nautical) convention of SWAN and XBeach.

**The period is a single representative period.** `wf_trep` (and the period column of
`wf_val`) is used as is for σ = 2π/T in the dispersion relation. For random waves the
default interpretation is to give the energy period T_m−1,0. If only the peak period
T_p is known, T_m−1,0 ≈ T_p/1.1 is a guide for a single-peaked spectrum (EurOtop 2018).

**Steps**

1. **Make the offshore a "solved sea".** Give the sea-bed topography in z and fill it
   with water by the initial water level (e.g. `f_htype = 2`; [initial conditions](initial.md)).
   **Waves do not pass through a band of sea-mask cells (sw)** (these are boundary
   cells that carry the tide level and are not computed by the shallow water flow
   either; [tide and sea level](tide.md)). If no cell along the incident sides is a wave
   cell at the start, a warning is printed.
2. **Make the offshore side incident (1).** For a fairly straight coast, make the left
   and right sides that cross the coast **lateral Neumann (2)**. Neumann treats the sea
   as continuing alongshore in the same way beyond the boundary, so no false shadow
   appears near the left and right sides. With absorbing (0), the waves that should
   enter obliquely from outside are missing and a shadow appears near the side (use it
   for sides with no sea outside, such as the back of a closed bay). The landward side
   can be anything.
3. **Start with the default number of bins and breaking coefficients**, look at the
   results (Wh, Wa) and change them only if needed.
4. **Check the results.** Look at the distributions Wh (wave height) and Wa (mean
   direction), and check that the imbalance (residual of the budget) in the ledger
   `result/wavefield.csv` is small ([output and checks](#output-and-checks)).

## Recommended values by pattern

| Use | Configuration | What to look at |
|---|---|---|
| Wave height on a beach, position of the surf zone | `wf_mode = 2` (quasi-steady; default), fixed offshore waves | Wh (height), Wb (breaking dissipation; `f_wf_outdiag = 1`) |
| Shadow behind a breakwater or an island | As above, default spreading 20° | Wh, Wa (mean direction) |
| Time-varying wave climate (preparing for morphology) | Series in `wf_val`, update interval `dt_wave`, `wf_clock = 1` for morphological time | `wavefield.csv` (ledger per update) |
| Arrival of a wave front (advanced together with a tsunami or flood) | `wf_mode = 1` (unsteady), `f_wf_init = 0` | Time change of Wh |
| Wave setup and longshore currents | `wf_flow = 2`; the left and right sides that cross the coast lateral Neumann for both waves and flow (`wf_bc_side` = 2, `f_bc_*` = 3) | E (water level), u, v (velocity), Wfx, Wfy (force) |
| Waves on river mouths, tidal currents and rip currents (blocking, steepening) | `f_wf_current = 1` (also `wf_flow = 2` for two-way coupling of waves and flow) | Wh, Wa, blocked in the ledger |
| Longshore transport, beach erosion and recovery (bed change) | `wf_flow = 2` and `f_wfsed = 1` added to the bed load and suspended load of fn_geomorph | Z (bed level), Qby, Qsy (longshore transport; `f_wf_outdiag = 1`) |
| Land building, rise of the shoreline (deltas, beach berms) | The row above plus the swash-zone transport `f_wfswash = 1` and the equilibrium foreshore slope `wfswash_tanbe` | Z |

**Key points of the settings**

- **To look at longshore currents**: give a directional spreading (default 20°;
  unidirectional waves with zero spreading refract too slowly and produce a false
  alongshore force offshore of the surf zone). The cross-shore distribution of the
  longshore current can be smoothed with the horizontal mixing by wave breaking
  `wf_break_visc` (&list_enc; its strength is a calibration quantity;
  [horizontal mixing by wave breaking](#horizontal-mixing-by-wave-breaking-wf_break_visc-of-list_enc)).
- **To combine the change of waves by currents with the wave-driven flow**
  (`f_wf_current = 1` and `wf_flow = 2`): add a small background viscosity
  (`f_diffusion_term = 2`, `p_diffusion_nu` = 0.05 m²/s or so;
  [grid-scale stripes offshore and background viscosity](#grid-scale-stripes-offshore-and-background-viscosity-with-wf_flow)).
- **To combine with morphology**: use the quasi-steady mode (default) and match the update
  interval `dt_wave` to how fast the wave climate changes. To give the offshore wave series
  in morphological time, use `wf_clock = 1` (MORFAC; [sediment and morphology](geomorph.md)).
- **To match beach erosion and recovery**: calibrate the coefficients of the onshore
  velocity `wfsed_facsk` and `wfsed_facas`
  ([calibrating beach erosion and recovery](#calibrating-beach-erosion-and-recovery)).
- **To look at land building or the rise of the shoreline**: add the swash-zone transport
  `f_wfswash = 1`, give the equilibrium foreshore slope `wfswash_tanbe` from observations at
  the site, and leave a margin in the time step `dt`
  ([swash-zone transport](#swash-zone-transport-f_wfswash)).
- **Steep beaches**: breaking with `wf_break = 2` (Janssen & Battjes 2007) corrects the
  overestimated dissipation on steep beaches.
- **Beds with large friction such as reefs**: give the bottom friction `wf_fw` (default
  0 = none; it can be more than an order of magnitude larger than the friction coefficient
  of the flow).

## Key points of the wave field settings

### Types of sides

Each outer side is one of the following (`wf_bc_side`, in the order of the sides W, E, N, S).

| Type | Waves entering from outside the side | Use |
|---|---|---|
| 1 incident | The offshore waves | Offshore side |
| 2 lateral Neumann | The same waves as the cell inside the side (the same sea continues outside) | Left and right sides crossing the coast |
| 0 absorbing | None | Sides with no sea outside, landward sides |

Outgoing waves leave freely through any type of side (no reflection). At corners the type is
chosen with the priority incident > lateral Neumann > absorbing, so even at the corner between
an incident side and a lateral Neumann side the alongshore-uniform solution of a straight coast
stays intact.

### Cells waves pass through and cells they do not

The cells in which waves are computed (**wave cells**) are the cells inside the domain (x > 0)
that are neither sea-mask cells (sw) nor absorbing cells and whose depth exceeds `wf_hmin`.
Waves heading towards land, dry cells, sea cells or absorbing cells are absorbed (no
reflection; absorbed in the ledger).

- **Cells with a building porosity gv < 1** and **sub-grid channel width / cross-section
  cells** are also treated as absorbing cells, and their number is printed at the start.
- Waves do not slip through a one-cell-thick diagonal breakwater whose cells touch only at
  corners (a diagonal does not pass waves when both cells beside it are cells that waves do not
  pass through; a rule deliberately different from the shallow water flow, which passes water
  through a one-cell-wide diagonal channel).

### Quasi-steady and unsteady

- **Quasi-steady (`wf_mode = 2`; default)**: the steady solution is computed every `dt_wave`
  (iterating from the previous solution; convergence criterion `wf_tol`, maximum number of
  iterations `wf_itmax`). It is meant for uses in which conditions change over times longer
  than the wave travel time, such as morphological computations. If a message says that it did
  not converge, raise `wf_itmax`.
- **Unsteady (`wf_mode = 1`)**: advanced every step with the physical time step. The wave front
  travels at the group velocity, and after a long enough time it reaches the same steady
  solution as the quasi-steady mode. Use it to advance together with a tsunami or flood; to
  start from calm, set `f_wf_init = 0`. It is solved at every step, so it can be heavier than
  the shallow water flow itself.

Both give bit-identical results regardless of the number of MPI ranks and threads.

### Number of directional bins and accuracy

The refraction error decreases in proportion to the bin width. For waves entering a beach of
slope 1/80 with parallel depth contours at 30°, the deviation of the mean direction from
Snell's law down to 1 m depth was 1.5° with N_θ = 40 (default) and 0.6° with N_θ = 80, and the
deviation of the wave height 0.5% and 0.3% (refr in test/wfshoal).

The shadows of waves travelling along an axis or a diagonal of the grid come out sharp, but in
the directions between them the edges of shadows are smeared by numerical diffusion. This is not
real diffraction (waves bending into a shadow).

### Choosing breaking and bottom friction

- Breaking of **random waves** (`wf_wavetype = 1`; default) is probabilistic; choose
  `wf_break = 1` (Baldock et al. 1998; default) or `2` (Janssen & Battjes 2007; corrects the
  overestimated dissipation on steep beaches). Start with the default coefficients `wf_gamma`,
  `wf_alpha` and `wf_gammax`.
- **Regular waves** (`wf_wavetype = 2`) have only saturated breaking, which removes the part of
  the wave height above γ times the depth; they are for verification against theoretical
  solutions.
- The **bottom friction** `wf_fw` defaults to 0 (none).

The formulas are in the [explanation](wavefield_models.md#5-breaking-bottom-friction-and-the-limit).

## Action on the flow (wf_flow)

With `wf_flow` set to 1 or 2, the wave field acts on the shallow water flow and produces
**wave setup (a rise of the mean water level near the shoreline), set-down offshore,
and longshore currents**. With the default 0 it does not act on the flow (the shallow
water results are the same whether or not `fn_wavefield` is written).

```
&list_wavefield
  ...
  wf_flow = 2              ! 0 no action (default) / 1 force / 2 force + GLM + wave-current friction
/
&list_bound_edge
  f_bc_n = 3               ! the left and right sides that cross the coast are lateral Neumann (longshore currents pass through)
  f_bc_s = 3
/
```

**Which to use.** Use **2** to look at longshore currents, rip currents or the
interaction with river flow. It includes the mass carried by the waves (Stokes
transport) and its return flow (the offshore-directed flow near the bed), and the bed
friction enhanced by the wave orbital velocity. 1 is a simplified form that adds only
the gradient of the radiation stress as a force (the same treatment as the classical
theory of setup); the friction is then determined by the current velocity alone. With 1
the friction of a flow close to rest is weak and the oscillation at the start lasts long
(see "Ramp-up of the force" below).

The wave force (the gradient of the radiation stress) raises and lowers the mean water level,
and the breaking of obliquely incident waves becomes an alongshore force that drives the
longshore current. With `wf_flow = 2` the shallow water velocity is read as the Lagrangian mean
velocity (the mass transport of water), and the flow at the bed (the Eulerian velocity = velocity
− Stokes transport) represents the return flow (how to read the output velocities is in
[output and checks](#output-and-checks)). The formulas are in the
[explanation](wavefield_models.md#6-action-on-the-flow-wf_flow).

### Roller (f_wf_roller, wf_beta)

The energy of breaking waves is first transferred to the surface vortex on the wave front (the
roller) and then dissipated. Because the roller stores the momentum of breaking for a while and
releases it further shoreward, **the maxima of the force, the setup and the longshore current move
shoreward of the breaker point**. It is enabled by default (`f_wf_roller = 1`, dissipation
coefficient `wf_beta = 0.1`).

### Ramp-up of the force (wf_tramp)

The quasi-steady wave field is at full strength over the whole domain at the start, so
the suddenly applied force excites an oscillation near the shoreline (a seiche). During
`wf_tramp` (default 100 s), the force and the Stokes transport are increased linearly from 0.
The ramp is counted from the origin t0 of the time axis, so a restart
(`f_state_restore = 1`) continues it. When a saved state is used as the initial condition
(`f_state_restore = 2`), the ramp starts again on the new time axis, so set `wf_tramp = 0`
to continue from a state that is already in balance.

### Horizontal mixing by wave breaking (wf_break_visc of list_enc)

Breaking turbulence also mixes momentum laterally and smooths the cross-shore distribution of
the longshore current. A positive `wf_break_visc` in the `&list_enc` of the shallow water flow
(default 0 = none) adds the eddy viscosity computed by the wave field at every update,
ν_w = M h (D/ρ)^{1/3} (of the Battjes 1975 type; M = `wf_break_visc`, D is the breaking
dissipation, or the roller dissipation with the roller), to ν of the
[diffusion term](diffusion.md) (the diffusion term is computed even with
`f_diffusion_term = 0`). M = 1 is the XBeach default, and the strength of the mixing is a
calibration quantity. ν_w peaks in the surf zone (0.54 m²/s on the beach of test/wfcurrent),
lowers the peak of the longshore current and spreads its distribution across the shore (the peak
drops by 3.3% on the same beach). The distribution can be checked with the output `Wnu`
(`f_wf_outdiag = 1`).

### Lateral boundaries (f_bc = 3)

Make the left and right sides that cross the coast **lateral Neumann for the waves
(`wf_bc_side` = 2) and lateral Neumann for the flow (`f_bc_*` = 3; [boundary
conditions](boundary.md))**. The lateral Neumann boundary of the flow treats the same coast
as continuing beyond the boundary, and the longshore current passes through the side
(with a wall the longshore current is blocked and a false circulation forms at the side).
On a coast that is uniform alongshore the boundary rows have the same solution as the
interior rows (in test/wfcurrent all rows agree to about 0.03% of the maximum velocity).
Sediment is treated the same way: suspended load (and other scalars such as water quality and
salt water) and bed load have zero gradient at the side (a coast that is uniform alongshore
stays uniform as the bed changes; test/wfsed).

Even when the flow near a side is non-uniform alongshore (near a river mouth, a delta or a
structure, with the change of waves by currents `f_wf_current = 1`, or with bed changes),
advection does not accelerate the flow entering through the side. The outside is still treated
as the same coast and topography continuing, however, so place the sides on a stretch where the
flow, the topography and the waves are as uniform alongshore as possible, and keep the area of
interest well away from the sides. param_wfsed.txt of examples/delta makes the north and south
sides walls for the flow, like the wave case it is compared with (the longshore current rises
from the wall on the inflow side and turns offshore at the wall on the other side).

## Change of waves by currents (f_wf_current)

With `f_wf_current = 1`, the shallow water flow (river flow, tidal currents, rip currents,
longshore currents, tsunami currents) changes the waves. On an opposing current (one that
faces the waves) the wavelength shortens and the wave height grows, and on a strong opposing
current the waves can no longer advance against the flow (**blocking**). On a following current
the wavelength lengthens and the wave height decreases. Where the current speed varies in space
the wave direction also turns (refraction by currents). This represents a river-mouth jet that
stops offshore waves from propagating up the river, and the steepening of waves on rip and tidal
currents.

```
&list_wavefield
  ...
  f_wf_current = 1         ! 0 none (default) / 1 action of the current on the waves
/
```

Combined with the wave-driven flow (`wf_flow`), waves and flow are coupled both ways (the
longshore current changes the waves, and those waves drive the longshore current). The velocity
used is the velocity of the shallow water flow itself (with `wf_flow = 2` the Lagrangian mean
velocity). The energy of blocked waves is recorded as blocked in the ledger `wavefield.csv` and
removed. The formulas are in the
[explanation](wavefield_models.md#7-change-of-waves-by-currents-f_wf_current).

### Grid-scale stripes offshore and background viscosity (with wf_flow)

When the change of waves by currents is combined with the wave-driven flow (`wf_flow = 2`),
oblique stripes three to four cells long (in velocity, wave height and force) can grow with time
in the quiet water offshore. They grow even without bed change (stripes in the current refract
the waves, stripes in the wave height make stripes in the force, and those strengthen the current
stripes: a positive feedback; the mechanism is in the
[explanation](wavefield_models.md#73-mechanism-of-the-grid-scale-stripes-offshore)).

A small background viscosity stops them: add a background viscosity to the zero-equation model
of the [diffusion term](diffusion.md) (`f_diffusion_term = 2` and `p_diffusion_nu` = 0.05 m²/s
or so in `&list_enc`). In wfsed of examples/delta (depth 2 m, period 6 s, Δx = 5 m) the stripes
of the offshore velocity (rms of the deviation from the 3×3 mean), which more than double in
3 hours, stay constant with ν0 = 0.05, while the velocity near the shoreline and the maximum of
the river-mouth jet hardly change (−1%).

### Cost and convergence

With a current, the dispersion relation and the decomposition of the transport are recomputed
for each cell and bin at every update, and quantities per bin are held. The memory of the wave
field becomes about three times as large (about 2.4 kB per cell with N_θ = 40). In the unsteady
mode (`wf_mode = 1`) they are recomputed at every step, which is expensive. Near blocking the
quasi-steady iteration converges slowly (about 2000 iterations for the river-mouth jet of
test/wfdoppler and about 7000 for its blocked channel). If a message says that it did not
converge, raise `wf_itmax`.

## Action on sediment (f_wfsed)

Adding `f_wfsed = 1` of `&list_geomorph` to the bed load (`f_fluvial`) and suspended load
(`f_suspend`) of [sediment and morphology](geomorph.md) lets the wave field move sediment. The
orbital motion of the waves stirs the sand on the bed (increasing the pick-up and bed load), and
the wave-driven flow (longshore current, undertow) and the onshore velocity of wave skewness and
asymmetry carry it. Longshore transport (sand moving along the shoreline), beach erosion (sand
carried offshore by the undertow of high waves) and recovery (sand carried onshore by the
asymmetry of low waves) are computed in the same time evolution as the morphology.

```
&list_geomorph
  f_fluvial = 1             ! bed load (stirred with the grain size fluv_d50)
  f_suspend = 1             ! suspended load (stirred with the grain size susp_d50)
  f_wfsed = 1               ! stirring and transport by the wave field
  !wfsed_facsk = 0.1        ! skewness coefficient f_Sk (default 0.1; 0 removes the skewness term of the onshore velocity)
  !wfsed_facas = 0.1        ! asymmetry coefficient f_As (default 0.1)
  !f_wfsed_turb = 1         ! stirring by the turbulence of wave breaking (default 0 = none)
/
```

`fn_wavefield` is required. The basic use is together with the wave-driven flow
(`wf_flow = 2`; the longshore current and the undertow carry the sand. With `wf_flow = 0` the
waves drive no flow, and only the stirring and the onshore velocity act). It cannot be used
together with [the longshore transport of fn_wave](geomorph.md) (CERC type; the run stops at
the start so that the same transport is not counted twice), nor with debris flow (`f_debris`).

- **Stirring**: the orbital velocity of the waves at the bed raises the dimensionless shear
  stress of the bed load formula and of the equilibrium concentration of suspended load to the
  combined wave–current bed shear stress (its maximum within the wave period), including the
  threshold. Without waves the formula is the same as with `f_wfsed = 0`.
- **Stirring by the turbulence of wave breaking** (`f_wfsed_turb = 1`; default 0 = none):
  strengthens the stirring near the shoreline, where breaking turbulence reaches the bed (on the
  beach of test/wfsed the stirring speed is 1.10 times larger in the shoreline cell and 1.01 times
  at the peak of breaking dissipation, and the longshore transport increases by 1.9%). The
  near-bed turbulence can be checked with the output `Wkb` (`f_wf_outdiag = 1`).
- **Transport**: the sand is carried by the Eulerian mean velocity of the wave-driven flow, i.e.
  without the Stokes transport (the offshore undertow in the surf zone), and by the onshore
  velocity u_a of wave skewness and asymmetry.

The formulas are in the [explanation](wavefield_models.md#8-action-on-sediment-f_wfsed).

### Calibrating beach erosion and recovery

Beach erosion and recovery are decided by the balance between the offshore undertow and the
onshore velocity. With high waves the undertow wins and sand is carried offshore (a bar forms);
with low waves and long-period swell the onshore velocity wins offshore of the surf zone and sand
returns onshore (storm and calm of test/wfsed). Which one wins is sensitive to the skewness and
asymmetry coefficients `wfsed_facsk` and `wfsed_facas` (default 0.1), so these two are the
calibration parameters when the morphological change is to be matched.

### Output of longshore transport and comparison with CERC

With `f_wf_outdiag = 1`, the estimate of bed load Qbx, Qby, the suspended transport Qsx, Qsy
(transport of solid volume per unit width, m²/s; directions as the velocities u, v) and the
onshore velocity Wua (m/s) are written. Integrating the alongshore component across the shore
gives the longshore transport rate. On the straight coast of test/wfsed (H_m0 = 1 m, T = 8 s,
20°) it is about 1.6 times CERC (Komar & Inman 1970) — the same order (both the CERC
coefficient and the coefficients of the process-based transport are calibrated quantities).

Make the left and right sides of a straight coast lateral Neumann (`f_bc_*` = 3), as for the
waves and the flow (zero gradient for sediment too; [lateral boundaries](#lateral-boundaries-f_bc--3)).

### Swash-zone transport (f_wfswash)

The phase-averaged wave field stops before the shoreline (wave cells have a depth of at least
`wf_hmin`) and has no swash flow, so the transport above has no process that piles up the sand
of the shallows above the shoreline (to the height the swash reaches). Adding `f_wfswash = 1` of
`&list_geomorph` gives empirical formulas for the net transport integrated over one swash cycle
on the shoreline faces (between a wet cell and a dry cell on higher ground).

```
&list_geomorph
  f_fluvial = 1
  f_wfsed = 1
  f_wfswash = 1             ! swash-zone transport
  wfswash_tanbe = 0.1       ! equilibrium foreshore slope tanβ_e (required)
  !wfswash_kc = 1.6e-3      ! cross-shore transport coefficient K_c (default 1.6e-3)
  !wfswash_kl = 1.6e-3      ! longshore transport coefficient K_l (default = K_c; 0 = no longshore transport)
  !wfswash_phim = 30.0      ! friction angle of a moving grain φ_m (deg) (default 30)
/
```

`f_wfsed = 1` and bed load `f_fluvial = 1` are required (the fluxes ride the same face-flux
mechanism as bed load). The rise of the water level at the shoreline (setup) is assumed to be
resolved by the flow, so combine it with the wave-driven flow `wf_flow = 2` (or 1) (with
`wf_flow = 0` the runup limit is lower by the setup, and a warning is printed at the start). It
cannot be combined with bedrock incision (`f_rockinc`).

**What happens.**

- **Cross-shore**: if the foreshore is milder than the equilibrium slope `wfswash_tanbe`, sand
  piles up to the height the swash reaches (a berm); if steeper, the foreshore is cut back. At
  the equilibrium slope nothing moves (the formula of Larson et al. 2004).
- **Longshore**: the swash of obliquely incident waves carries sand along the shoreline (the
  formula of Larson & Wamsley 2007). There is no longshore transport if the mean wave direction
  is 80° or more from the shoreline normal.
- **Height of the swash**: up to the swash excursion (the formula of Stockdon et al. 2006),
  which is set by the incident wave height and period and the foreshore slope, above the water
  level of the shoreline cell (which includes the setup resolved by the flow). Deposits do not
  exceed this height.
- **How the waves reach**: on shorelines that waves hardly reach, such as the lee of a delta or
  inside a channel, the swash is reduced according to the nearby wave height. Nothing moves on
  shorelines without wave cells nearby, or in front of a cliff or seawall higher than the runup.

The formulas, coefficients and mapping to the grid are in the
[explanation](wavefield_models.md#9-swash-zone-transport-f_wfswash).

**Notes on use.**

- The foreshore slope is a central difference over two cells, so it is averaged more on coarser
  grids. On a coarse grid where the swash zone (width = height of the swash / foreshore slope) is
  narrower than one cell, the sand piles up on the one dry cell next to the shoreline (a berm),
  and the dry cells beyond do not change.
- The equilibrium slope tanβ_e is given by the user (it depends on the grain size and the waves,
  steeper for coarser sand; basically give it from observations of the foreshore slope at the
  site). The default coefficient K_c is calibrated on field observations of fine sand (0.18 mm).
- The bed updates change the water level at the shoreline, so small long waves leave the
  shoreline. If the Courant number in the deep water offshore is close to 1, they can grow at the
  offshore boundary and stop the run (in test/wfswash it happened at 0.88 and was stable at
  0.44). Leave a margin in the time step `dt`.
- The amounts moved are printed at the end (solid volume moved onto the dry foreshore, volume
  moved off it, and the sum of the absolute volumes the longshore flux passed through faces; per
  rank).
- Example: wfsed of [examples/delta](../../../examples/delta/en/README.md) ("Coastal wave field" in its
  README). The swash-zone transport makes the emerged land about 1.4 times larger and piles the
  land up to the height the swash reaches (the edges of the land are ragged at the scale of one
  cell).

## Parameters

The parameters of `&list_wavefield`.

| Parameter | Default | Meaning |
|---|---|---|
| `f_wavefield` | 1 | 0 disables it temporarily while keeping it written |
| `wf_ntheta` | 40 | Number of directional bins (a multiple of 8, 8–360). Bin width 360°/N_θ (default 9°). The axis and diagonal directions lie on bin centres |
| `wf_mode` | 2 | 1: unsteady (advanced every step in physical time) / 2: quasi-steady (the steady solution is computed every `dt_wave`) |
| `dt_wave` | 3600 s | Update interval of the quasi-steady mode (rounded to an integer multiple of the time step `dt`) |
| `wf_itmax` | 4 max(nx, ny) | Maximum number of quasi-steady iterations |
| `wf_tol` | 1e-4 | Convergence criterion of the quasi-steady mode: the maximum change of wave height in one iteration / the offshore wave height (H_rms for random waves) |
| `f_wf_init` | 1 | 1: compute the quasi-steady solution at the start / 0: start from calm (no waves) |
| `wf_bc_side(1:4)` | 0, 0, 0, 0 | Type of the sides W, E, N, S. 0 absorbing / 1 incident / 2 lateral Neumann. **At least one incident side is required** |
| `wf_wavetype` | 1 | 1: random waves (height H_m0, probabilistic breaking) / 2: regular waves (height H, saturated breaking H ≤ γh; for verification) |
| `wf_hm0`, `wf_trep`, `wf_dir` | — | Offshore waves (fixed values; required when `wf_val` is not used). `wf_trep` is the representative period (interpreted as T_m−1,0 for random waves) |
| `wf_spread` | 20° (0° for regular waves) | Directional spreading σθ (0 = unidirectional; upper limit 48.8° = uniform over the half plane) |
| `wf_val(1:5, k)` | — | Time series of offshore waves: time (min), height (m), period (s), direction (deg), spreading (deg). Linear interpolation between rows (the direction is interpolated the short way). Rows that omit the spreading use the default |
| `wf_clock` | 0 | Clock of the series 0: hydraulic time / 1: morphological time (MORFAC times; [sediment and morphology](geomorph.md)) |
| `wf_break` | 1 | Breaking 1: Baldock et al. (1998) / 2: Janssen & Battjes (2007) (random waves only) |
| `wf_gamma` | 0.78 | Breaker index γ |
| `wf_alpha` | 1.0 | Dissipation coefficient α of breaking (random waves) |
| `wf_gammax` | 0.6 | Depth limit H_rms ≤ γmax h (random waves) |
| `wf_fw` | 0 | Bottom friction factor f_w (0 = no friction) |
| `wf_hmin` | 0.1 m | Minimum depth of a wave cell |
| `f_wf_outdiag` | 0 | 1: also write the distributions of the bottom orbital velocity Wu and the breaking dissipation Wb (with `wf_flow` ≥ 1 also the wave force Wfx, Wfy, the Stokes transport Wsx, Wsy and the roller Wr) |
| `wf_flow` | 0 | Action on the flow. 0: none / 1: wave force only / 2: wave force + GLM Stokes transport + wave–current bed friction (recommended). [Action on the flow](#action-on-the-flow-wf_flow) |
| `f_wf_roller` | 1 | 1: solve the energy balance of the roller (with `wf_flow` ≥ 1) |
| `wf_beta` | 0.1 | Dissipation coefficient β of the roller |
| `wf_tramp` | 100 s | Ramp-up time of the force (linear from 0 to 1 times from the origin of the time axis). 0 for no ramp |
| `f_wf_current` | 0 | 1: action of the current on the waves (Doppler shift, refraction and transport by the current, blocking). [Change of waves by currents](#change-of-waves-by-currents-f_wf_current) |

Defaults that are adopted are printed on screen with `(default)`. The basis of the
defaults is in the [explanation](wavefield_models.md#10-parameters-and-the-basis-of-their-defaults).
The parameters of the action on sediment and of the swash-zone transport
(`&list_geomorph`) are in the section [action on sediment](#action-on-sediment-f_wfsed).

## Output and checks

**Distributions** (at each output time; [input/output formats](io.md))

| Symbol | Content | Unit |
|---|---|---|
| Wh | Wave height (H_m0 for random waves, H for regular waves) | m |
| Wa | Mean direction (direction of travel, counterclockwise from the x axis; −9999 in cells without waves) | deg |
| Wu | Bottom orbital velocity u_rms = H_rms σ/(2√2 sinh kh) (the XBeach definition). `f_wf_outdiag = 1` | m/s |
| Wb | Breaking dissipation D_w (random waves). `f_wf_outdiag = 1` | W/m² |
| Wfx, Wfy | Wave force F = −∇·S (cell centres; including the roller). `wf_flow` ≥ 1 and `f_wf_outdiag = 1` | N/m² |
| Wsx, Wsy | Stokes transport velocity u^S. `wf_flow = 2` and `f_wf_outdiag = 1` | m/s |
| Wr | Roller energy E_r. `f_wf_roller = 1` and `f_wf_outdiag = 1` | J/m² |
| Qbx, Qby | Estimate of the bed load transport (solid volume per unit width; `f_wfsed = 1` and `f_fluvial = 1` of fn_geomorph). `f_wf_outdiag = 1` | m²/s |
| Qsx, Qsy | Suspended transport hs·u_s (likewise, `f_suspend = 1`). `f_wf_outdiag = 1` | m²/s |
| Wua | Onshore transport velocity u_a of wave skewness and asymmetry (positive along the mean wave direction; `f_wfsed = 1`). `f_wf_outdiag = 1` | m/s |
| Wnu | Eddy viscosity ν_w of the horizontal mixing by wave breaking (`wf_break_visc` > 0 of &list_enc). `f_wf_outdiag = 1` | m²/s |
| Wkb | Near-bed turbulence energy k_b (`f_wfsed_turb = 1` of fn_geomorph). `f_wf_outdiag = 1`. Wu is then u_rms without turbulence | m²/s² |

**The y components (Wfy, Wsy, Qby, Qsy) have the same sign convention as the velocity v (the
direction of increasing row index = south is positive).** Note that this is opposite to
the convention of the wave direction (north positive). With `wf_flow = 2` the velocities
u and v are the Lagrangian mean velocity u^L; the flow at the bed (the Eulerian velocity)
is u − Wsx, v − Wsy.

**Ledger** `result/wavefield.csv`. The quasi-steady mode writes the rates at convergence
(W) at every update; the unsteady mode writes cumulative amounts (J) at every recording
interval (`dt_recrd`).

| Column | Content |
|---|---|
| iter, residual (quasi-steady) / nsub (unsteady) | Number of iterations and the last residual / number of substeps |
| H_bc, T_bc, dir_bc | Offshore waves at that time |
| in, out | Inflow from and outflow to the boundaries (including the exchange through lateral Neumann sides) |
| absorbed | Energy lost towards land, dry and absorbing cells |
| breaking, friction | Dissipation by breaking and bottom friction |
| limit | Energy removed by the limit (H_rms ≤ γmax h for random waves, saturation for regular waves) |
| dry | Energy removed from cells whose depth fell to `wf_hmin` or less (amount, J) |
| trunc | Numerical truncation (the amount added by setting negative values to 0; normally 0 or of round-off size) |
| imbalance, storage | Residual of the budget, storage of the wave field (Σ E A) |
| blocked (`f_wf_current = 1`) | The part removed by blocking |

With `f_wf_current = 1` the ledger amounts are wave action × ω (the same as energy without a
current). The quasi-steady imbalance is the rate of change of storage in the last iteration and
approaches 0 as `wf_tol` is reduced. The unsteady imbalance is (change of storage) −
(net input) and is of round-off size. A large value indicates a defect; please report it.

## Scope and restrictions on combinations

- **Phase-averaged with one representative period.** Diffraction, reflection,
  frequency spreading, wind growth and nonlinear wave–wave interactions are not treated.
  The smearing of shadow edges is numerical diffusion, not diffraction.
- **Action on sediment (`f_wfsed`)**: by default the stirring is by the orbital velocity at
  the bed only (pick-up by breaking-induced turbulence can be added with `f_wfsed_turb = 1`).
  There is no horizontal diffusion of suspended load. The phase-averaged waves stop before
  the shoreline, so transport in the swash zone is added with empirical formulas
  (`f_wfswash = 1`; "swash-zone transport" above). By default (0) there is no process that piles
  up the sand of the shallows above the shoreline, so sand stays in the shallows and hardly
  becomes land. Dune slumping is the angle-of-repose collapse `f_repose`. There is one
  representative grain size each for bed load and suspended load. The balance between the undertow and the onshore velocity that decides
  between beach erosion and recovery is sensitive to the coefficients f_Sk and f_As
  (calibration quantities).
- **Blocked waves are only removed as wave action**; reflection at the blocking point
  (conversion to short waves) is not represented. With one representative period, blocking
  happens to all the energy at once (real waves are blocked from the short components of the
  spectrum). Breaking by the steepening before the blocking point is represented.
- Even when the current changes in time, the angular frequency ω of the offshore waves is kept
  constant (the change of ω by the time variation of the current is not included).
- **At abrupt changes of the current** (near sources, at the edges of jets), unidirectional
  waves spread by a few % into the neighbouring bins through refraction by the current
  (numerical diffusion of the first-order upwind scheme in direction space; it decreases with
  the square of the bin width).
- **Lateral mixing by breaking waves (eddy viscosity) is not included by default.** By
  default the distribution of the longshore current is smoothed by the numerical lateral
  mixing of the advection through the ENC diagonal faces (a current of a few % of the maximum
  appears at the outer edge where breaking begins). Wave-induced mixing can be added with
  `wf_break_visc` (&list_enc; of the Battjes 1975 type; "Horizontal mixing by wave breaking"
  above). The strength M of the mixing is a calibration quantity.
- **Unidirectional waves with zero spreading (including regular waves) refract more slowly
  than Snell's law** (with N_θ = 40 and 20° incidence the direction at the breaker point is
  about 1.5° too large). The alongshore radiation stress S_xy is sensitive to the direction,
  so a false alongshore force appears offshore of the surf zone (about 5% of the force in
  the surf zone; about 1% with a spreading of 20°). To look at longshore currents, give a
  directional spreading or increase the number of bins.
- **A lateral Neumann side** treats the same coast as continuing outside. If the topography
  changes alongshore near a side, or a structure touches a side, keep the area of interest
  well away from the sides ([lateral boundaries](#lateral-boundaries-f_bc--3)).
- **Sea-mask cells (sw) are outside the wave domain.** Represent the offshore by ordinary
  cells with sea-bed topography and place the incident boundary on the outer sides.
- **It cannot be combined with the STG grid or with nesting** (the run stops at the start).
- Cells with a building porosity gv < 1 and sub-grid channel width / cross-section cells
  absorb waves.
- Cost: the model holds N_θ planes, and one update is N_θ scalar transports plus a
  tridiagonal solve per cell. One quasi-steady solution takes a few hundred iterations
  (367 iterations, about 2 s for 100 × 100 cells and 40 bins with 4 threads). Solving
  every step in the unsteady mode can be heavier than the shallow water flow itself.

## Tests and examples

- [test/wfshoal](../../../test/wfshoal/en/README.md): shoaling, refraction and breaking on a
  beach profile, arrival of the front in the unsteady mode and closure of the ledger (compared
  with linear theory, Snell's law and independently written dissipation formulas).
- [test/wfshadow](../../../test/wfshadow/en/README.md): shadows of a breakwater and of an
  enclosure of diagonal walls.
- [test/wfcurrent](../../../test/wfcurrent/en/README.md): action on the flow (setup, longshore
  current, return flow, roller, horizontal mixing by wave breaking, lateral Neumann sides).
- [test/wfdoppler](../../../test/wfdoppler/en/README.md): change of waves by currents (opposing
  and following currents, blocking, river-mouth jet).
- [test/wfsed](../../../test/wfsed/en/README.md): action on sediment (stirring, longshore
  transport compared with CERC, beach erosion and recovery, conservation of sediment, stirring by
  breaking turbulence).
- [test/wfswash](../../../test/wfswash/en/README.md): swash-zone transport (agreement with the
  formulas, equilibrium slope, runup limit, in front of a cliff).
- [examples/delta](../../../examples/delta/en/README.md): a river delta exposed to waves, whose
  landform develops with longshore transport and swash-zone transport (wfsed).
- Format examples: [examples/List_samples/en/list_wavefield.txt](../../../examples/List_samples/en/list_wavefield.txt)
- All are bit-identical to the serial run with MPI np = 1, 2 and 4. The details of what each case
  checks are in the [explanation](wavefield_models.md#11-verification-cases).
