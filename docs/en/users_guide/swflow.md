# Shallow water flow computation (&list_enc and numerical constants)

> English mirror of docs/users_guide/swflow.md. The Japanese file is the master copy.

[Back to the user's guide index](../users_guide.md)

Tuning parameters for the core surface water computation (the shallow
water equations on the ENC grid). **The defaults are set so that the
model runs reasonably as is** -- the settings in this chapter are for
accuracy/cost tuning and numerical experiments; in ordinary
computations the only one you may need to touch is the threshold of the
adaptive Runge-Kutta scheme. The equations and the basis of the defaults for
the grid geometry, the continuity equation, the cell-velocity reconstruction,
the terms of the momentum equation, the adaptive Runge-Kutta scheme, the
Courant number and the numerical constants are in
[ENC grid and time integration](encgrid.md); the advection term, the
diffusion term and the non-hydrostatic correction have their own pages.

![ENC grid and adaptive Runge-Kutta](../../figs/swflow_enc_en.png)

**(a) ENC grid.** Depth h and ground elevation z are at cell centres.
Edges to the eight surrounding cells (four axis and four diagonal directions)
carry the normal velocity uv and flux per unit width mn. Filled squares mark
axis-edge quantities; open squares mark diagonal-edge quantities. Cell-centre
velocities u, v are reconstructed by combining edge velocities with geometric
weights. p_diagratio controls the allocation of diagonal passage widths;
its default makes the eight passage widths equal ([explanation](encgrid.md) §2 and §4).
The formulation and verification of the grid are in the original paper[^tada26].

**(b) STG grid.** This is a four-neighbour staggered grid for legacy comparisons.
Depth and ground elevation are at cell centres (internal arrays D and H).
The x-direction flux per unit width M is on east/west faces (squares), and
the y-direction flux per unit width N is on north/south faces (diamonds).
Output cell velocities u, v are the mean flux on the two opposing faces divided
by cell depth (zero below the threshold depth). Restart, subgrid channels and
levees, and internal hydraulic structures are unsupported in STG.

Panels (a)/(b) are square-cell schematics highlighting the connections and
quantity locations associated with the central cell. **(c) Adaptive Runge-Kutta
decision band.** The explicit candidate flux per unit width is compared with
its previous-step value; edges outside the threshold band are recomputed with
four RK stages. The decision rule, the stages and the Runge statistic are
in [the explanation](encgrid.md) §6.

## Just try it (minimal input)

Everything in this chapter **runs with the defaults** - fn_enc need not be
written. The defaults enable the wet/dry front stabilization
(f_exflux_reduction), the steep-slope gravity correction
(f_gravity_correction) and the adaptive Runge-Kutta (threshold 1.5), a
safe combination for tsunamis, inundation and flood runoff alike.

## Choice of scheme (&list_sysparam)

| Parameter | Default | Meaning |
|---|---|---|
| f_gridsystem | 0 | 0: ENC grid (default), 1: STG (staggered grid; legacy-compatible, for comparison only. New features and restart are not supported) |
| f_govequation | 0 | 0: dynamic wave (advection + pressure; default), 1: diffusive wave (pressure only), 2: kinematic wave |
| f_check_cfl | 1 | Courant number monitoring. 0: monitor only (no stop), 1: display the state and stop when Cn > 1 (default), 2: judge and stop on the advective Courant number ignoring the wave speed (the definition of the Cn column and Cn output also switches to the advective Cn) ([explanation](encgrid.md) §7) |

The diffusive and kinematic waves are for sensitivity experiments and
comparison with other models. For inundation and runup involving
wetting and drying, keep the dynamic wave.

## Numerical constants (&list_sysparam)

| Parameter | Default | Meaning (basis in [the explanation](encgrid.md) §8) |
|---|---|---|
| dd | 0.001 | threshold depth (m). An edge whose two cells are both below it carries no flux |
| dv | 0.001 | lower bound of the depth used in the friction term (m) |
| vv | 0.01 | lower bound of the velocity used in the friction term (m/s) |
| gg | 9.8 | gravitational acceleration (m/s^2) |
| cm / cd / kk | 2.0 / 1.0 / 0.5 | added-mass coefficient, drag coefficient and shielding factor of building clusters (used together with gv/bb of the geographic information; [geographic information chapter](geoinfo.md)) |

## Tuning the ENC computation (&list_enc)

Enabled via `fn_enc` (even without it, the core runs with the
defaults).

```
&list_enc
  p_adprunge_thresh = 1.1        ! threshold of the adaptive Runge-Kutta scheme (1.1 ~)
/
```

**Time integration (adaptive Runge-Kutta)** (details in [§6 of the explanation](encgrid.md#6-time-integration-and-the-adaptive-runge-kutta-scheme))

Only the edges whose explicit flux per unit width leaves the band between
1/thr and thr times the previous-step value (reversals included) are
recomputed with four Runge-Kutta stages. The mechanism avoids shrinking dt
for the whole domain because of a few extreme cells; if the **Runge column**
on the screen (share of recomputed edges) reaches tens of percent, reducing
dt is the proper remedy. The effect of the threshold is demonstrated in
[tutorial Step 2](../../../tutorials/wave/en/README.md#step-2-setting-enc-parameters).

| Parameter | Default | Meaning (details in the § of [the explanation](encgrid.md)) |
|---|---|---|
| f_adaptive_runge | 1 | adaptive Runge-Kutta: only edges whose flux leaves the band are recomputed with four RK stages (the advection term stays at time level n) (§6) |
| p_adprunge_thresh | 1.5 | threshold thr of the recomputation (1.1 or more; smaller values recompute more edges. Accuracy is better gained by reducing dt) (§6) |

**Flux and stabilization**

| Parameter | Default | Meaning (details in the § of [the explanation](encgrid.md)) |
|---|---|---|
| f_gravity_correction | 1 | effective gravity g cos²θ on steep slopes (Ni et al. 2019); no effect on gentle slopes (§5) |
| f_exflux_reduction | 1 | suppression of excessive outflow. Prevents negative depths at fronts advancing over dry ground (keep on in computations with dry beds) (§5) |
| f_hcap_upwind | 1 | edge depth. 0: mean of both cells, 1: the mean capped by the upwind depth (default), 2: the upwind depth itself (removes the spike at a bore front; required in non-hydrostatic cases with breaking or bores. It increases the outflow onto dry ground, so check ex_flux in inundation runs) (§3, [advection](advection.md) §5) |
| f_friction_fastmath | 0 | table approximation of h^(-4/3) in the friction term. 0: exact (default), 1-5: coarser and faster (relative error 2e-4 to 6%) (§8) |
| p_diagratio | 2/(2+sqrt(2)) | share of the passage width given to the diagonal edges; the default makes the eight passage widths equal (normally no need to change) (§2) |

**Advection and diffusion terms**

The advection (inertia) term, with the default momentum-conservative
scheme plus MUSCL (scheme 3), handles bores, hydraulic jumps and flood
waves on real terrain correctly and normally needs no change. The
diffusion term (horizontal diffusion of momentum by an eddy viscosity) is
off by default and is not needed for numerical stability. The equations,
schemes and stencils are explained in [Advection schemes](advection.md),
the eddy-viscosity models, discretisation and stability condition in
[Diffusion term](diffusion.md).

To just try the diffusion term, one line is enough (zero-equation model;
the coefficient follows from the flow and the roughness).

```
&list_enc
  f_diffusion_term = 2    ! diffusion term (zero-equation model; advection stays at the default)
/
```

**Practical points** (details in [§5 of the advection page](advection.md#5-properties-and-choice) and [§6 of the diffusion page](diffusion.md#6-where-to-use-it-and-cautions))

- **Leave the advection term at the defaults** (scheme 3 +
  `f_opening_dynamic = 1` + `f_dry_head_cap = 1`). Only to reproduce cases
  calibrated with older versions use `f_advection_scheme = 1`,
  `f_opening_dynamic = 0`, `f_dry_head_cap = 0` (the defaults before
  2026-10-03; moving to scheme 3 needs a roughness recalibration).
- **If real-terrain results are later and smaller than observed** (with a
  channel mask) try `f_advection_donor = 1`. **Inundation, incised terrain
  and dam breaks without a channel mask**: `f_opening_dynamic = 2`.
- **The diffusion term is for** the transverse velocity distribution of
  channels and circulation in bays. With `f_diffusion_term = 2` no
  coefficient is needed; the roughness n sets the size of ν (typically
  0.01–0.1 m²/s). The constant viscosity (model 1) requires an explicit
  `p_diffusion_nu`, kept below the explicit bound Δx²/(2.83 dt) (a warning
  is printed above it).
- **Mass** is conserved exactly whatever the advection and diffusion
  settings. Schemes 2 and 3 cost +12–27% over scheme 1; the diffusion term
  costs nothing when off.
- **Verification cases**: bores [test/dambreak](../../../test/dambreak/README.md),
  bends, steps and lateral inflow [test/bendloss](../../../test/bendloss/README.md),
  hillslope flow [test/hillslope](../../../test/hillslope/README.md), real
  terrain [test/chichibu](../../../test/chichibu/README.md) (READMEs in
  Japanese); analytical benchmark of the diffusion term
  [test/diffusion](../../../test/diffusion/README.md) (diffusion of a Gaussian
  jet, error below 0.14%).

| Parameter | Default | Meaning (details in the § of the explanation pages) |
|---|---|---|
| f_advection_scheme | 3 | scheme of the advection term. 3: momentum-conservative + MUSCL (default), 2: momentum-conservative, first-order upwind, 1: cell-centre gradient (former default; non-conservative, bores lag, no grid convergence on real terrain) ([advection](advection.md) §3–5) |
| f_advection_donor | 0 | 1: on edges between channel cells, limit the upwind donor in the flow direction to channel cells (against the artificial loss at bends and confluences; requires the channel mask fn_rw; judge against observations) (§4.4) |
| f_scalar_scheme | 3 | advection scheme of the scalar transport (suspended sediment, water quality, salt layer, driftwood, debris). 3: link-wise MUSCL (default), 1: first-order upwind (former default; numerical diffusion 3–5 times longitudinally and 14 times laterally; kept for comparison) ([Advection](advection.md) §7) |
| f_dry_head_cap | 1 | cap the edge depth toward a dry cell by the energy head (water does not climb onto dry ground above the water surface; prevents leaks and blow-ups at bore fronts and in incised channels; inactive at ordinary wet/dry fronts, identical to 0 there) (§5) |
| f_opening_dynamic | 1 | dynamic reassignment of blocked diagonal openings. 1: edges between channel cells (default; inactive without the channel mask), 2: all edges, 0: off. Corrects the excessive edge velocity of the ENC grid in one-cell channels and along walls (§5) |
| p_adv_upwind_index | 0.5 | upwinding index of scheme 1 only (0: central difference, 1: first-order upwind) (§3) |
| f_diffusion_term | 0 | diffusion term. 0: none (default), 2: zero-equation model ν = ν0 + α·u*·h (recommended), 1: constant viscosity ([diffusion](diffusion.md) §2) |
| p_diffusion_nu | -- | ν0 (m²/s). For model 1 a positive value must be given explicitly (unset is an error stop); for model 2 an optional background viscosity (§2) |
| p_diffusion_alpha | 0.41/6 | coefficient α of the zero-equation model (default is the Elder type; calibrate within 0.15–0.6 for stronger transverse mixing) (§2) |

**Non-hydrostatic correction (research option)**

The one-layer non-hydrostatic correction is a research option for
phenomena in which frequency dispersion (shorter waves travel more slowly)
is essential: soliton fission and undular bores of tsunamis running up
rivers, near-field generation of landslide tsunamis, solitary waves in
reservoirs. Rainfall runoff, flood inundation, storm surges and ordinary
long-wave tsunamis do not need it, and the default is hydrostatic (when off
there is no extra computation, memory or communication and the results are
bit-identical to before). The equations, the projection algorithm, the
active set, breaking, the bottom terms, and the models and literature the
implementation drew on are explained on a separate page,
[Non-hydrostatic correction](nonhydrostatic.md).

To just try it, one line is enough (CG solver, whole-domain solve,
flat-bed one-layer model).

```
&list_enc
  f_nonhydrostatic = 1    ! one-layer non-hydrostatic correction (everything else at the defaults)
/
```

**Practical points** (details in [§8 of the explanation](nonhydrostatic.md#8-range-of-validity-and-practical-points))

- **Grid spacing at most half the depth** (Δx ≲ H/2; the verification used
  H/4–H/8). On a coarser grid the correction is buried in the numerical
  dispersion of the grid and meaningless. The cost is set by this
  resolution requirement rather than by the solver.
- **Add options step by step as needed**: `f_nh_adaptive = 1` to limit the
  cost (solve only where dispersion matters). With breaking or bores,
  `f_nh_breaking = 1` + `f_hcap_upwind = 2` (required); for quantitative
  run-up add `nh_break_visc = 1.44` and friction n ≈ 0.01 and check
  convergence at Courant ≲ 0.1 and Δx ≲ H/8. `f_nh_slope = 1` for abrupt
  bathymetry (shelves, submarine landslides), `f_nh_bottom = 1` for the
  near field of landslide tsunamis.
- **Where it degrades to hydrostatic automatically**: depth below nh_hmin,
  the sea mask, levee walls, sub-grid channel width and cross-section,
  building-occupied cells, breaking cells, the neighbourhood of forced
  boundaries (nh_bc_margin).
- **Restrictions**: cannot be combined with debris flow (f_debris). A
  restart is a cold start (the private non-hydrostatic state is not saved).
  A nested child receives the parent's φ in the band
  ([Nesting](nest.md), nest_nh).
- **Cost**: solved on the whole domain, 2–3 times the hydrostatic run
  (10–90 CG iterations per step). With the active set the regions of long
  waves, steady flow and inundation carry no cost.
- **Verification cases**: dispersion relation of standing waves
  [test/nhwave_nh](../../../test/nhwave_nh/README.md), solitary wave
  [test/nhsolitary](../../../test/nhsolitary/README.md), undular bore
  [test/nhbore](../../../test/nhbore/README.md), soliton fission on a shelf
  [test/nhshelf](../../../test/nhshelf/README.md), breaking run-up
  [test/nhbreak](../../../test/nhbreak/README.md), moving bottom
  [test/nhbottom](../../../test/nhbottom/README.md) (READMEs in Japanese; the
  results are summarised in §8 of the explanation).

| Parameter | Default | Meaning (details in the § of the [explanation](nonhydrostatic.md)) |
|---|---|---|
| f_nonhydrostatic | 0 | 0: hydrostatic (default), 1: one-layer non-hydrostatic correction (β = h²/4, projection at the end of the step; §2–3) |
| nh_hmin | 0.1 | cells shallower than this depth (m) stay hydrostatic; must exceed dd (§4) |
| nh_solver | 2 | iterative solver. 2: CG (default), 1: Jacobi (for comparison; slow for Δx ≪ H) (§3) |
| nh_itmax | 500 | maximum number of iterations (a warning is printed and the run continues when exceeded) |
| nh_tol | 1e-6 | relative convergence criterion |
| nh_bc_margin | 0 | margin kept hydrostatic next to forced boundaries (prescribed stage, reach inflow, free outflow, radiation); cells, 0: automatic 2H/Δx (§4) |
| f_nh_adaptive | 0 | active set. 1: solve only on the detected cells plus a margin (§5) |
| nh_detector | 1 | detector. 1: dispersion ratio χ (default), 2: absolute form (for comparison) (§5) |
| nh_chi_on | 0.06 | detection threshold (the level of a 3% phase-speed difference) (§5) |
| nh_margin | 0 | width of the margin (cells; 0: automatic 2H/Δx) (§5) |
| nh_amin | 1e-5 | absolute floor of the detector (m/s²) (§5) |
| nh_arel | 1e-3 | relative floor of the detector (fraction of the domain maximum) (§5) |
| f_nh_breaking | 0 | breaking switch. 1: breaking cells and their margin become hydrostatic and dissipate as a bore. Required for breaking waves running up a slope; use with f_hcap_upwind=2 (§6) |
| nh_break_type | 3 | breaking detector. 1: surface rise rate (SWASH type), 2: Froude number, 3: surface slope (default) (§6) |
| nh_break_alpha | 0.6 | onset threshold α of detector 1 |
| nh_break_beta | 0.3 | threshold β of detector 1 for cells adjacent to breaking cells |
| nh_break_fr | 0.6 | Froude threshold of detector 2 |
| nh_break_slope | 0.3 | surface-slope threshold of detector 3 |
| nh_break_margin | 0 | hydrostatic margin around breaking cells (cells; 0: automatic 2H/Δx) (§6) |
| nh_break_visc | 0 | breaking eddy-viscosity coefficient δ_b² (0: off; 1.44 corresponds to the literature value). Dissipates through the [diffusion term](diffusion.md) (§6) |
| f_nh_slope | 0 | bottom-slope terms (Version 2). 1: for waves over slopes, shelves and abrupt bathymetry; about twice the iterations (§7) |
| f_nh_bottom | 0 | moving-bottom acceleration term. 1: for the near field of landslide tsunamis (one-layer approximation of the Kajiura filter); acts on f_bedslide, fn_bedmotion, morphological change and API updates of z (§7) |

**Others**

| Parameter | Default | Meaning |
|---|---|---|
| f_rivermouth_drop | 0 | free overfall from the river mouth to the sea (legacy scheme; cannot be combined with the tide feature fn_tide -- using [tide](tide.md) + [boundary conditions](boundary.md) is now recommended) |

## Recommended values by pattern

| Type | Recommended settings | Why |
|---|---|---|
| Tsunami / storm-surge run-up | Defaults (p_adprunge_thresh 1.2-1.5); f_check_cfl=1 to watch Cn | The default stabilization handles both the front over dry ground and the reflected waves |
| Steep mountain floods, debris flows | f_gravity_correction=1 (default); dt such that Cn_max stays below about 0.5 | Corrects the slope-direction gravity term. Sediment is in [landform change](geomorph.md) |
| River low flow, velocity distribution of gentle flow | f_diffusion_term=2 (no coefficient needed) | Flow-scaled eddy viscosity smooths the transverse velocity distribution |
| Urban inundation (building clusters) | Defaults + fn_gv/fn_bb ([geographic information](geoinfo.md)); cm/cd/kk at the defaults | Storage loss and drag are expressed on the geographic side |
| Wide-area / long runs (cost first) | p_adprunge_thresh 2-3, f_friction_fastmath 3-5, f_govequation=1 (diffusive wave) if needed | Cuts the recomputation rate and the friction cost. The diffusive wave ignores inertia, so not for inundation fronts or tsunamis |
| Accuracy checks, numerical experiments | p_adprunge_thresh 1.1, f_friction_fastmath 0, dt such that Cn_max stays below about 0.5 | High-accuracy side; a few tens of percent more cost. Reducing dt is more reliable than lowering the threshold (the threshold cannot close the gap between dt 0.01 and 0.05; tutorials/wave Step 2) |
| Bores, hydraulic jumps, tsunami run-up (flows with discontinuities) | default (f_advection_scheme 3) | Momentum-conservative advection: correct bore speed and no oscillations behind the bore. The former default 1 lags the bore and oscillates behind it |
| Inundation, incised channels, dam breaks without a channel mask | f_opening_dynamic 2 | the default 1 acts only on edges between channel cells; 2 corrects the conveyance along walls and in incised channels on every edge |
| Reproducing cases calibrated with older versions | f_advection_scheme 1, f_opening_dynamic 0, f_dry_head_cap 0 | the defaults before 2026-10-03. Moving to scheme 3 needs a roughness recalibration (the momentum-conservative form resolves the jump losses and the momentum exchange with the valley floor, so it is slower and lower) |

## Output and monitoring

The three ways a field gets written (automatic / flag / riding on a flag) and the area basis of column quantities are explained in [Input and output formats](io.md#how-state-variables-are-written); a reverse lookup from the quantity you want to the output is at the end of that section.

**Fields** (rasters in `result/`, every `dt_file`)

| File | How | Contents |
|---|---|---|
| H / E | f_out_h (default on) / f_out_e | depth (m, pore-area basis) / water level (m) |
| u / v / V | f_out_u / v / vv | components and magnitude of the cell velocity (m/s) |
| m / n / Q / Qd | f_out_m / n / qq / qd | components and magnitude of the unit-width discharge (m²/s) and direction (rad) |
| Fr / Cn | f_out_fr / f_out_cn | Froude / Courant number fields |
| H9999 / Ht9999 / V9999 / Q9999 / Qt9999 / Qd9999 | f_out_hmax (default on) and others | run maxima of depth, speed and discharge, their times (min) and direction |

**Ledgers and log** (budget and numerical health)

- Columns of Log.txt: `time, progress, S(m), Runge, ex_flux, Cn_max, h_max,
  V_max` (with groundwater, snow or glaciers S splits into S_surf / S_grnd
  / S_total; `f_disp_*` selects the displayed columns). S is the
  domain-mean storage depth (m; with the gv conversion and pond/dam
  storage, sea cells excluded), `Runge` the fraction of edges recomputed
  by the adaptive Runge-Kutta, `ex_flux` the count of suppressed excessive
  outflow fluxes, `Cn_max` the domain maximum Courant number.

**Measurements** (probe and transect columns)

- Probes: `z, h, u, v, |V|, q` (+ hg, hs, sd and the water-quality C, cq).
  Transects: `Q, Hmax, Vmax, B` (+ the water-quality L, Lcum). At the end
  `summary.csv` collects Qmax and Hmax of all points and transects
  ([the measurement chapter](record.md)).

**Restart**

- Depth and discharge are in the core state save; the ENC edge quantities
  (velocities, fluxes, dynamic re-assignment of openings) are handled
  automatically by the private file `swflow_enc.dat`. The non-hydrostatic
  correction cold-starts at restart.

**How to read and check**

- Time-step health: `Cn_max` must not exceed 1 (the run stops by default),
  `Runge` should not stay above some tens of percent, `ex_flux` should not
  keep growing. If any applies, reduce dt ([Courant number and time
  step](courant.md)).
- Water budget: in a closed domain without boundary conditions S is
  constant (all significant digits with `f_disp_debug = 1`). If it
  changes, look at boundaries, sea cells, structures and evapotranspiration.
- The maximum statistics are updated every step, so they differ from
  maxima picked from the `dt_file` frames. Use H9999 for inundation hazard
  maps.

## Format examples

Annotated list of all parameters (with the defaults spelled out):
[examples/List_samples/list_enc.txt](../../../examples/List_samples/en/list_enc.txt).

## Relation to verification

Many of these switches change the computed results. The regression
tests (reference in [test/](../../../test/)) were created with the defaults, so compare
results obtained with modified settings against your own baseline.

## References

[^tada26]: Tada, T. (2026): An eight-neighborhood connected collocated grid scheme for overland flow simulation. *Hydrological Research Letters*, 20(2), 113–118. doi:10.3178/hrl.25-00052. (the original paper of the ENC grid: the eight-neighborhood connected collocated grid and the passage-width allocation)
