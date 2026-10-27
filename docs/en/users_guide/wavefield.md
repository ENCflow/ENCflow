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
period**, and the model solves an energy balance in which the direction of travel is
split into **N_θ directional bins**. It is a rough estimate of the same level as HISWA[^hiswa],
the stationary mode of XBeach[^xbeach] and SnapWave[^snapwave]; frequency spreading,
wind growth and nonlinear wave–wave interactions are not treated.

**The feature is being implemented in stages.** The current stage (W1) is a **wave field
on a fixed bed without the effect of currents**: it only computes and writes the wave
height and related quantities. **It does not act on the flow or the bed** (the shallow
water results are the same whether or not `fn_wavefield` is written). Wave-driven
longshore currents and setup (stage W2), the change of waves by currents (stage W3), and
longshore transport and cross-shore erosion and accretion (stages W4 and W5) will be
added in later stages (docs/wavefield_plan.md §9).

It is a different feature from "longshore transport by waves" in the
[sediment and morphology chapter](geomorph.md) (`fn_wave`, a simplified mode that
gives the longshore transport in the shoreline band with a CERC-type formula, taking
the offshore waves as given).

The history of the design, the comparison of alternatives and the decisions are in
docs/wavefield_plan.md; the exception to policy 5 and the record of decisions,
implementation and verification are in developer.md §0-5 and §88.

## Enabling and configuration

Specify `fn_wavefield` in `&list_sysparam` (`"-"` means the same parameter file).

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

**The direction is the direction the waves travel to** (not the direction they come
from). It is measured counterclockwise from the x axis (east): a wave travelling north
is 90°, one travelling west is 180°. This is the same convention as `wave_dir` in the
[sediment and morphology chapter](geomorph.md), and differs by 180° from the
"coming from" (nautical) convention of SWAN and XBeach.

**The period is a single representative period.** `wf_trep` (and the period column of
`wf_val`) is used as is for σ = 2π/T in the dispersion relation. For random waves the
default interpretation is to give the energy period T_m−1,0 (developer.md §88.1 D7). If
only the peak period T_p is known, T_m−1,0 ≈ T_p/1.1 is a guide for a single-peaked
spectrum (EurOtop 2018[^eurotop]).

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
| `f_wf_outdiag` | 0 | 1: also write the distributions of the bottom orbital velocity Wu and the breaking dissipation Wb |

Defaults that are adopted are printed on screen with `(default)`.

## Trying it out (minimal input)

All that is needed is **an incident side** and **the offshore waves** (`wf_hm0`,
`wf_trep`, `wf_dir`).

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

**Typical uses**

| Use | Configuration | What to look at |
|---|---|---|
| Wave height on a beach, position of the surf zone | `wf_mode = 2` (quasi-steady; default), fixed offshore waves | Wh (height), Wb (breaking dissipation; `f_wf_outdiag = 1`) |
| Shadow behind a breakwater or an island | As above, default spreading 20° | Wh, Wa (mean direction) |
| Time-varying wave climate (preparing for morphology) | Series in `wf_val`, update interval `dt_wave`, `wf_clock = 1` for morphological time | `wavefield.csv` (ledger per update) |
| Arrival of a wave front (advanced together with a tsunami or flood) | `wf_mode = 1` (unsteady), `f_wf_init = 0` | Time change of Wh |

## How it is computed

### Governing equation

For the energy density E_m [J/m²/rad] of each directional bin m (centre direction θ_m)
the model solves

```math
\frac{\partial E_m}{\partial t} + \nabla\cdot\left(c_g\,\hat{\mathbf e}_m E_m\right)
+ \frac{\partial (c_\theta E_m)}{\partial \theta}
= -\left(D_w + D_f\right)\frac{E_m}{E},
\qquad E = \sum_m E_m\,\Delta\theta
```

This is the conservation of wave action (Bretherton & Garrett 1968[^bg68]) reduced from
the form of SWAN[^swan] to a single frequency; at stage W1 there is no current, so the
frequency is constant and the conservation of action and of energy are the same. The
group velocity $`c_g`$ and the refraction speed $`c_\theta`$ follow from the dispersion
relation of linear theory.

```math
\sigma^2 = g\,k\tanh(kh),\qquad
c_g = \frac{\sigma}{2k}\left(1 + \frac{2kh}{\sinh 2kh}\right),\qquad
c_\theta = \frac{\sigma}{\sinh 2kh}\left(\sin\theta\,\frac{\partial h}{\partial x}
- \cos\theta\,\frac{\partial h}{\partial y}\right)
```

(σ = 2π/T, x east and y north; as in SnapWave, $`c_\theta`$ is limited to |c_θ| ≤ σ/4.)
The dissipation on the right-hand side, $`D_w`$ (breaking) and $`D_f`$ (bottom
friction), is the dissipation of the total energy distributed over the bins in
proportion to E_m/E (as in XBeach).

The wave height is H_rms = (8E/ρg)^{1/2} for random waves, written out as the
significant wave height H_m0 = √2 H_rms (Rayleigh distribution), and H = (8E/ρg)^{1/2}
for regular waves (ρ = 1025 kg/m³). The mean direction is
atan2(Σ E_m sin θ_m, Σ E_m cos θ_m).

### Offshore waves and directional bins

The energy of the offshore waves outside the incident sides is E_0 = ρgH_m0²/16 for
random waves and ρgH²/8 for regular waves. The directional distribution is
cos^s(θ − θ_0) (|θ − θ_0| < 90°); the exponent s is obtained from the directional
spreading σθ through the definition of Kuik et al. (1988)[^kuik88], σθ² = 2(1 − m_1),
and the distribution is normalised discretely over the bins (Σ D Δθ = 1; the same
distribution shape as SWAN). σθ = 0 is distributed linearly over the two bins that
bracket θ_0. The number of bins N_θ is restricted to multiples of 8, so the axis and
diagonal directions of x and y always lie on bin centres.

### Spatial transport (two-link upwind decomposition)

On the 8-neighbour ENC grid, the propagation velocity $`c_g\hat{\mathbf e}_m`$ of bin m
is **decomposed non-negatively into the two lattice directions (an axis and a diagonal)
that bracket it**, and each link carries energy upwind (the value of the sending cell).
With the grid-normalised p_x = c_g cos θ/Δx and p_y = c_g sin θ/Δy, if |p_x| ≥ |p_y| the
rate is |p_x| − |p_y| towards the x axis and |p_y| towards the diagonal (and vice versa).
This applies the idea of D∞ (Tarboton 1997[^tarboton97]) for flow directions to wave
energy, and is a discretisation original to this project.

- **Propagation along lattice directions (axes, diagonals) has no crosswind numerical
  diffusion.** The shadows of waves aligned with an axis or a diagonal come out exactly
  sharp (aligned in test/wfshadow).
- Between them there is crosswind numerical diffusion, at most 0.096 c_g Δx (near the
  middle between two lattice directions; the first-order upwind scheme on ENC passage
  widths has 0.293 c_g Δx along an axis). **The edges of shadows are smeared by this
  numerical diffusion.** It is not real diffraction (waves bending into a shadow); this
  phase-averaged model does not treat diffraction.
- The transport is conservative and the energy never becomes negative.
- **A diagonal link is closed when the two cells beside it are both non-wave cells
  (such as land).** Waves do not slip through a one-cell-thick diagonal breakwater whose
  cells touch only at corners (a rule deliberately different from the ENC for water;
  the diamond enclosure of test/wfshadow).

### Refraction in directional space

In each cell, the advection ∂(c_θ E_m)/∂θ in θ is solved implicitly by first-order upwind
(a periodic tridiagonal system), and a second-order correction with the van Leer
limiter[^vanleer74] is added from the previous values (deferred correction; at
convergence of the quasi-steady mode the balance of the limited second-order fluxes is
satisfied). First-order upwind alone delays refraction through numerical diffusion in
directional space, and central differencing produces negative energy for a
unidirectional incident wave, so it is not used (developer.md §88).

The refraction error decreases in proportion to the bin width. For waves entering a
beach of slope 1/80 with parallel depth contours at 30°, the deviation of the mean
direction from Snell's law down to 1 m depth was 1.5° with N_θ = 40 and 0.6° with
N_θ = 80, and the deviation of the wave height 0.5% and 0.3% (refr in test/wfshoal).

### Breaking, bottom friction and the limit

Breaking of **random waves** follows Baldock et al. (1998)[^baldock98] (default)

```math
D_w = \frac{\alpha}{4}\,\rho g f\,Q_b\left(H_b^2 + H_{rms}^2\right),\qquad
Q_b = \exp\!\left[-\left(\frac{H_b}{H_{rms}}\right)^2\right]
```

or Janssen & Battjes (2007)[^jb07]

```math
D_w = \frac{3\sqrt\pi}{16}\,\alpha\rho g f\,\frac{H_{rms}^3}{h}\,Q_b,\qquad
Q_b = 1 + \frac{4}{3\sqrt\pi}\left(R^3 + \frac{3}{2}R\right)e^{-R^2} - \mathrm{erf}(R),\quad R = \frac{H_b}{H_{rms}}
```

both with the breaking wave height H_b = (0.88/k) tanh(γkh/0.88) (the Miche-type form of
Battjes & Janssen 1978) and f = 1/T (the same forms as the stationary mode of XBeach).
In addition, as in XBeach and SnapWave, the depth limit H_rms ≤ γmax h is applied (the
excess is counted as "limit" in the ledger).

**Regular waves** (`wf_wavetype = 2`) have only the saturation H ≤ γh (saturated
breaking) and no probabilistic breaking. They are for verification against theoretical
solutions.

**Bottom friction** is D_f = c ρ f_w u_orb³ with u_orb = πH_rms/(T sinh kh) (H for regular
waves) and c = 0.28 (random) or 0.21 (regular) (coefficients of the third velocity
moment of Guza & Thornton 1985[^gt85]; the XBeach formulation). The default is
f_w = 0 (no friction; the default of the XBeach stationary mode).

The dissipation is solved semi-implicitly within the cell (D/E is evaluated with the
previous value and applied as an implicit decay).

### Boundaries and wave cells

Each outer side is one of the following.

| Type | Value held by the virtual sender outside the grid | Use |
|---|---|---|
| 1 incident | Bin energy of the offshore waves | Offshore side |
| 2 lateral Neumann | Value of the cell inside the boundary | Left and right sides crossing the coast (the same sea continues outside) |
| 0 absorbing | 0 | Sides with no sea outside, landward sides |

Each link has one sender, so energy is not injected twice at corners. For a virtual
sender at a corner (outside the grid in both x and y), the type of side is chosen with
the priority incident > lateral Neumann > absorbing (the area outside the corner of an
incident side is regarded as offshore waves, which keeps the alongshore-uniform
solution of a straight coast intact). Outgoing waves leave freely (no reflection).

A **wave cell** is a cell inside the domain (x > 0) that is neither a sea-mask cell (sw)
nor an absorbing cell and whose depth exceeds `wf_hmin`. Waves heading towards land,
dry cells, sea cells or absorbing cells are absorbed (no reflection; "absorbed" in the
ledger). In this version, **cells with a building porosity gv < 1** and **sub-grid
channel width / cross-section cells** are also treated as absorbing cells, and their
number is printed at the start.

### Quasi-steady and unsteady

One update is the pair of the spatial inflow and outflow (an explicit update that makes
new values from the previous ones) and the refraction and sources within the cell
(implicit). This single kernel is run in two ways.

- **Quasi-steady (`wf_mode = 2`; default)**: every `dt_wave`, the model iterates with a
  per-cell pseudo time step Δτ = 1/(maximum outflow rate) until the steady solution is
  reached (starting from the previous solution). The steady solution does not depend on
  Δτ. It is meant for uses in which conditions change over times longer than the wave
  travel time, such as morphological computations.
- **Unsteady (`wf_mode = 1`)**: advanced every step with the physical dt (with substeps
  if outflow rate × dt > 1). The wave front travels at the group velocity (unst in
  test/wfshoal). After a long enough time it reaches the same steady solution as the
  quasi-steady mode.

Neither depends on the order in which cells are updated, so the results are
bit-identical regardless of the number of MPI ranks and threads.

## Output and checks

**Distributions** (at each output time; [input/output formats](io.md))

| Symbol | Content | Unit |
|---|---|---|
| Wh | Wave height (H_m0 for random waves, H for regular waves) | m |
| Wa | Mean direction (direction of travel, counterclockwise from the x axis; −9999 in cells without waves) | deg |
| Wu | Bottom orbital velocity u_rms = H_rms σ/(2√2 sinh kh) (the XBeach definition). `f_wf_outdiag = 1` | m/s |
| Wb | Breaking dissipation D_w (random waves). `f_wf_outdiag = 1` | W/m² |

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

The quasi-steady imbalance is the rate of change of storage in the last iteration and
approaches 0 as `wf_tol` is reduced. The unsteady imbalance is (change of storage) −
(net input) and is of round-off size. A large value indicates a defect; please report it.

## Scope and restrictions on combinations

- **Phase-averaged with one representative period.** Diffraction, reflection,
  frequency spreading, wind growth and nonlinear wave–wave interactions are not treated.
  The smearing of shadow edges is numerical diffusion, not diffraction.
- **Stage W1 does not act on the flow or the bed.** Wave-driven longshore currents, setup
  and sediment transport come in later stages. The change of waves by currents (river
  flow, tidal currents, tsunamis), such as the Doppler shift and blocking, is not yet
  included either.
- **Sea-mask cells (sw) are outside the wave domain.** Represent the offshore by ordinary
  cells with sea-bed topography and place the incident boundary on the outer sides.
- **It cannot be combined with the STG grid or with nesting** (the run stops at the start).
- Cells with a building porosity gv < 1 and sub-grid channel width / cross-section cells
  absorb waves.
- Cost: the model holds N_θ planes, and one update is N_θ scalar transports plus a
  tridiagonal solve per cell. One quasi-steady solution takes a few hundred iterations
  (367 iterations, about 2 s for 100 × 100 cells and 40 bins with 4 threads). Solving
  every step in the unsteady mode can be heavier than the shallow water flow itself.

## Parameters and the basis of defaults

| Parameter | Default | Basis |
|---|---|---|
| `wf_gamma` | 0.78 | **Literature value**: default of the XBeach stationary mode[^xbeach] (a customary value that derives from the breaking limit of a solitary wave) |
| `wf_alpha` | 1.0 | **Literature value**: default of the XBeach stationary mode[^xbeach] |
| `wf_gammax` | 0.6 | **Literature value**: default of the XBeach stationary mode[^xbeach] (limit of H_rms relative to depth). SnapWave[^snapwave] has a limit of the same form and value |
| `wf_fw` | 0 | **Calibration**: the default 0 (no friction) is the XBeach default[^xbeach]. On reefs and similar beds it can be more than an order of magnitude larger than the friction coefficient of the flow (XBeach manual) |
| Friction coefficient c | 0.28, 0.21 | **Literature value**: velocity moments of Guza & Thornton (1985)[^gt85] (the XBeach formulation). Not a setting |
| `wf_break` | 1 | **Method**: Baldock et al. (1998), the same as the default of the XBeach stationary mode. On steep beaches Janssen & Battjes (2007) corrects the overestimated dissipation |
| `wf_mode` | 2 | **Method**: the default is set for use with morphology (conditions change more slowly than the wave travel time) |
| `wf_hmin` | 0.1 m | **Numerical**: default of SnapWave[^snapwave] |
| `dt_wave` | 3600 s | **Numerical**: default update interval of SnapWave[^snapwave] |
| `wf_ntheta` | 40 (9°) | **Numerical**: a multiple of 8 close to the 10° default of XBeach and SnapWave. The refraction error is as measured above (proportional to the bin width) |
| `wf_tol` | 1e-4 | **Numerical**: original (relative change of wave height; in the verification the difference of solutions was checked with 1e-6 to 1e-8) |
| `wf_spread` | 20° | **Empirical**: a guideline of this project (original). A value placed between the typical spreading of wind sea and swell; if wave observations exist for the site, give their directional spreading |
| ρ | 1025 kg/m³ | **Customary value**: density of sea water (the XBeach default). Not a setting |

The dispersion relation is solved by three Newton iterations starting from the explicit
approximation of Fenton & McKee (1990)[^fm90].

## Verification and examples

- [test/wfshoal](../../../test/wfshoal/en/README.md): a beach profile of slope 1/80.
  Shoaling and saturated breaking of regular waves (agreement with linear theory),
  refraction (Snell's law and first-order convergence in the directional bins), breaking
  of random waves (Baldock, Janssen & Battjes; agreement with the discrete solution built
  with dissipation formulas written independently in Python, 1% difference from the
  energy balance integrated with a fine step), the arrival of the front and the steady
  state in the unsteady mode, closure of the ledger, byte-identical continuation after a
  restart, identical flow with and without the wave field, and the interpolation of the
  offshore wave series.
- [test/wfshadow](../../../test/wfshadow/en/README.md): a breakwater and an enclosure of
  diagonal walls. Agreement with an independently implemented sweep solution, blocking by
  the diagonal walls, and exactly sharp shadows for waves aligned with a lattice direction.
- Both are bit-identical to the serial run with MPI np = 1, 2 and 4.

## References

[^baldock98]: Baldock, T. E., Holmes, P., Bunker, S. & Van Weert, P. (1998) Cross-shore hydrodynamics within an unsaturated surf zone. Coastal Engineering 34, 173–196.
[^bg68]: Bretherton, F. P. & Garrett, C. J. R. (1968) Wavetrains in inhomogeneous moving media. Proc. R. Soc. Lond. A 302, 529–554.
[^eurotop]: EurOtop (2018) Manual on wave overtopping of sea defences and related structures, 2nd ed. Van der Meer, J. W., Allsop, N. W. H., Bruce, T., De Rouck, J., Kortenhaus, A., Pullen, T., Schüttrumpf, H., Troch, P. & Zanuttigh, B. www.overtopping-manual.com
[^fm90]: Fenton, J. D. & McKee, W. D. (1990) On calculating the lengths of water waves. Coastal Engineering 14, 499–513.
[^gt85]: Guza, R. T. & Thornton, E. B. (1985) Velocity moments in nearshore. J. Waterway, Port, Coastal, Ocean Eng. 111(2), 235–256.
[^hiswa]: Holthuijsen, L. H., Booij, N. & Herbers, T. H. C. (1989) A prediction model for stationary, short-crested waves in shallow water with ambient currents. Coastal Engineering 13, 23–54.
[^jb07]: Janssen, T. T. & Battjes, J. A. (2007) A note on wave energy dissipation over steep beaches. Coastal Engineering 54, 711–716. The form of the breaking wave height H_b is the Miche type of Battjes, J. A. & Janssen, J. P. F. M. (1978) Energy loss and set-up due to breaking of random waves. Proc. 16th ICCE, 569–587 (the same as the XBeach formulation).
[^kuik88]: Kuik, A. J., van Vledder, G. Ph. & Holthuijsen, L. H. (1988) A method for the routine analysis of pitch-and-roll buoy wave data. J. Phys. Oceanogr. 18, 1020–1034.
[^snapwave]: Roelvink, D., van Ormondt, M., Reyns, J. & van der Lugt, M. (2025) SnapWave: fast, implicit wave transformation from offshore to nearshore. Geosci. Model Dev. 18, 9469–9495. doi:10.5194/gmd-18-9469-2025 (defaults from the public source code)
[^swan]: Booij, N., Ris, R. C. & Holthuijsen, L. H. (1999) A third-generation wave model for coastal regions: 1. Model description and validation. J. Geophys. Res. 104(C4), 7649–7666.
[^tarboton97]: Tarboton, D. G. (1997) A new method for the determination of flow directions and upslope areas in grid digital elevation models. Water Resour. Res. 33(2), 309–319.
[^vanleer74]: van Leer, B. (1974) Towards the ultimate conservative difference scheme. II. Monotonicity and conservation combined in a second-order scheme. J. Comput. Phys. 14, 361–370.
[^xbeach]: Roelvink, D., Reniers, A., van Dongeren, A., van Thiel de Vries, J., McCall, R. & Lescinski, J. (2009) Modelling storm impacts on beaches, dunes and barrier islands. Coastal Engineering 56, 1133–1152. Formulations and defaults are from the XBeach manual (xbeach.readthedocs.io) and the public source code (params.F90).
