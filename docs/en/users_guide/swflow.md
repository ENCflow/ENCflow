# Shallow water flow computation (&list_enc and numerical constants)

> English mirror of docs/users_guide/swflow.md (based on commit b501c3c). The Japanese file is the master copy.

[Back to the user's guide index](../users_guide.md)

Tuning parameters for the core surface water computation (the shallow
water equations on the ENC grid). **The defaults are set so that the
model runs reasonably as is** -- the settings in this chapter are for
accuracy/cost tuning and numerical experiments; in ordinary
computations the only one you may need to touch is the threshold of the
adaptive Runge-Kutta scheme.

## Choice of scheme (&list_sysparam)

| Parameter | Default | Meaning |
|---|---|---|
| f_gridsystem | 0 | 0: ENC grid (default), 1: STG (staggered grid; legacy-compatible, for comparison only. New features and restart are not supported) |
| f_govequation | 0 | 0: dynamic wave (advection + pressure; default), 1: diffusive wave (pressure only), 2: kinematic wave |
| f_check_cfl | 1 | Courant number monitoring. 0: monitor only (no stop), 1: display the state and stop when Cn > 1 (default), 2: judge and stop on the advective Courant number ignoring the wave speed (the definition of the Cn column and Cn output also switches to the advective Cn) |

The diffusive and kinematic waves are for sensitivity experiments and
comparison with other models. For inundation and runup involving
wetting and drying, keep the dynamic wave.

## Numerical constants (&list_sysparam)

| Parameter | Default | Meaning |
|---|---|---|
| dd | 0.001 | threshold depth (m). Water movement is computed on cells at or above this depth |
| dv | 0.001 | virtual depth (m). Computational lower bound for depths below this |
| vv | 0.01 | lower bound of the velocity in the friction term (m/s) |
| gg | 9.8 | gravitational acceleration (m/s^2) |
| cm / cd / kk | 2.0 / 1.0 / 0.5 | added-mass coefficient, drag coefficient, and drag correction factor of building clusters (used together with gv/bb of the geographic information; [geographic information chapter](geoinfo.md)) |

## Tuning the ENC computation (&list_enc)

Enabled via `fn_enc` (even without it, the core runs with the
defaults).

```
&list_enc
  p_adprunge_thresh = 1.1        ! threshold of the adaptive Runge-Kutta scheme (1.1 ~)
/
```

**Time integration (adaptive Runge-Kutta)**

| Parameter | Default | Meaning |
|---|---|---|
| f_adaptive_runge | 1 | adaptive Runge-Kutta (recompute with 4-stage RK only the edges with large velocity variation; the advection term stays at its time-level-n value in the recomputation stages). Its purpose is to avoid shrinking dt for the whole domain because of a few extreme cells; if the Runge column reaches tens of percent, reducing dt is the proper remedy |
| p_adprunge_thresh | 1.5 | threshold of the velocity variation rate that triggers recomputation (smaller = more accurate and more costly; 1.1 and up) |

The meaning and effect of the threshold are demonstrated in
[tutorial Step 2](../../../tutorials/wave/en/README.md#step-2-setting-enc-parameters).
The Runge column on the screen shows the application rate.

**Flux and stabilization**

| Parameter | Default | Meaning |
|---|---|---|
| f_gravity_correction | 1 | gravity correction (corrects the slope-direction gravity error on steep terrain) |
| f_exflux_reduction | 1 | suppression of excessive outgoing fluxes. Prevents negative depths at fronts advancing over dry ground (recommended to keep on in computations with dry beds) |
| f_hcap_upwind | 1 | depth at the cell interface (mass flux). 0: mean of both cells, 1: the mean capped by the upwind-side depth (default), 2: the upwind-side depth itself (as in the continuity equation of Stelling & Duinmeijer; removes the one-cell pile-up spike at a bore front. It increases the outflow of a front onto dry ground, so check ex_flux and the front propagation in inundation runs) |
| f_friction_fastmath | 0 | fast evaluation of the friction term. 0: exact (default), 1-5: table approximation (larger = coarser and faster) |
| p_diagratio | 2/(2+sqrt(2)) | weight of the diagonal components in the 8-direction fluxes (normally no need to change) |

**Advection and diffusion terms**

| Parameter | Default | Meaning |
|---|---|---|
| f_advection_scheme | 3 | scheme of the advection term. 1: cell-centre gradient (former default; a weighted 3×3 gradient projected onto the edge by averaging both cells. Non-conservative: bores lag and on real terrain the runoff gets faster and larger with grid refinement without converging), 2: momentum-conservative, first-order upwind, 3: momentum-conservative + MUSCL (van Leer; default). Schemes 2 and 3 extend the staggered-grid formulation of Stelling & Duinmeijer (2003) to the 8-direction ENC edges and give the correct speed of bores and hydraulic jumps (wet-bed dam break: bore position error 1%, versus a 15% lag with the former default 1). p_adv_upwind_index acts on scheme 1 only |
| f_advection_donor | 0 | restriction of the upwind momentum donors of the momentum-conservative advection (f_advection_scheme 2, 3). 0: every wet cell (default), 1: on edges between channel cells (fn_rw mask, rw > 0) the donor in the flow direction is limited to channel cells (a flow-direction face whose donor is a non-channel cell uses ū = u_e; lateral faces are not affected, so the deceleration by lateral inflow from the hillslopes remains). Prevents the artificial loss that accumulates at bends, confluences and irregular 2-cell-wide reaches when the upwind edge on the control-volume line falls onto a flooded valley-floor or hillslope cell whose slow water then becomes the momentum donor (developer.md §68.18). In the real-terrain test (chichibu 100 m) the outlet peak rises by 16% and arrives 0.5 h earlier, closing about 40% of the gap to the non-conservative scheme 1. It also cuts the momentum exchange between the main channel and flooded valley-floor cells, so judge its validity against observations. Requires the channel mask; no effect with scheme 1 || f_dry_head_cap | 1 | cap the edge depth toward a dry cell by the energy head. 0: off, 1: on (default). When the receiving cell is dry (h < dd) the depth an edge can carry is capped at max(η + u_n²/2g − z_receiver, 0); an edge that cannot be overtopped gets zero velocity. Water never climbs onto dry ground above the water surface plus velocity head (leaks and blow-ups in 1–2 cell wide incised channels). Never triggers in the wave/dambreak/chichibu tests |
| f_opening_dynamic | 1 | dynamic reassignment of blocked openings. 0: off, 1: edges between channel cells only (default; inactive without the channel mask fn_rw), 2: all edges. Passage-width shares that cannot be used because the diagonal neighbour's ground is above the water surface are reassigned to the open edges every step (edge velocity would otherwise be about 2.4× the cell velocity in a 1-cell channel, which amplifies the advection term). Use 2 for inundation, incised channels and dam breaks without a channel mask |
| p_adv_upwind_index | 0.5 | upwinding index of the advection term (0-1; scheme 1 only, unused with the default scheme 3). 0: central difference, 1: first-order upwind difference |
| f_diffusion_term | 0 | diffusion term. 0: none (default), 1: constant viscosity, 2: zero-equation model (nu = nu0 + alpha * u_star * h) |
| p_diffusion_nu | -- | kinematic eddy viscosity nu0 (m^2/s). **For model 1 a positive value must be specified explicitly** (unset is an error stop). For model 2 an optional background viscosity |
| p_diffusion_alpha | 0.41/6 | coefficient alpha of the zero-equation model (default is the Elder type) |

If you just want to try adding a diffusion term, **model 2 is
recommended** -- without specifying a single coefficient, a viscosity
that scales physically with the flow, nu = alpha * u_star * h (alpha
defaults to the Elder type), takes effect. The constant viscosity of
model 1 depends on the grid spacing and the scale of the flow, so there
is no universally recommended value and an explicit value is mandatory
(forgetting to set it stops the run at initialization, so it never
becomes silently inactive).

**Non-hydrostatic correction (research option)**

| Parameter | Default | Meaning |
|---|---|---|
| f_nonhydrostatic | 0 | one-layer non-hydrostatic correction. 0: hydrostatic (default), 1: on. The hydrostatic step (adaptive RK, advection, friction, levees and structures included) is kept as the predictor; at the end of the step a cell-wise non-hydrostatic potential φ is solved and the edge velocities and fluxes are corrected (one-layer model with β = h²/4; the linear dispersion relation is ω² = gHk²/(1 + (kH)²/4), equivalent to the one-layer SWASH). Intended for phenomena governed by frequency dispersion -- soliton fission and undular bores of tsunamis running up rivers, near-field generation by landslide tsunamis, solitary waves in reservoirs -- and not needed for rainfall runoff, flood inundation or ordinary long-wave tsunamis. **The grid should be finer than half the depth (Δx ≲ H/2)**: on coarser grids the numerical dispersion of the grid exceeds the physical dispersion and the correction is meaningless. When off there is no extra computation, memory or communication and the results are bit-identical to before (docs/nonhydrostatic_plan.md) |
| nh_hmin | 0.1 | cells shallower than this depth (m) stay hydrostatic (wet/dry fronts, very shallow water and bores after breaking are handled hydrostatically). Must exceed dd. Sea-mask (sw), levee-wall, sub-grid channel-width, σ-section and building-occupied (gv < 1) cells and edges also stay hydrostatic |
| nh_solver | 2 | iterative solver for φ. 1: Jacobi, 2: CG (default; the inner products use the deterministic row sum, so results are bit-identical for any thread or rank count). Jacobi converges slowly when Δx ≪ H and is kept for comparison |
| nh_itmax | 500 | maximum number of iterations (a warning is printed and the run continues when exceeded) |
| nh_tol | 1e-6 | relative convergence criterion (CG: residual norm / right-hand-side norm, Jacobi: max residual / max right-hand side) |
| f_nh_adaptive | 0 | active set. 0: solve on the whole NH mask (default), 1: solve only on the cells whose detector exceeds the threshold (seeds) plus a margin of nh_margin cells around them; the rest stays hydrostatic ("only where needed", like the adaptive RK). The elliptic correction decays by a factor e over half the depth, so a margin of about 2H keeps the difference from the full solve below 1% of the correction. Long waves, steady flow and inundation areas cost nothing. No state is kept between steps, so restarts are bit-reproducible |
| nh_detector | 1 | detector. 1: dispersion type χ = \|βDa*\| / (\|a*\| + \|βDa*\|) (ratio of the non-hydrostatic correction to the hydrostatic acceleration a*; for long waves χ ≈ (kH)²/4, independent of the amplitude and zero for long waves and steady flow; default), 2: absolute type \|βDa*\|/g (for comparison) |
| nh_chi_on | 0.06 | detection threshold (cells with χ > nh_chi_on are seeds; 0.06 corresponds to a 3% phase-speed difference from hydrostatic; for the absolute type a fraction of g) |
| nh_margin | 0 | width of the margin (cells). 0 = automatic 2H/Δx (four times the decay length H/2) |
| nh_amin | 1e-5 | absolute floor (m/s²): cells whose correction \|βDa*\| is below it are never seeds |
| nh_arel | 1e-3 | relative floor: cells whose \|βDa*\| is below this fraction of the domain maximum of the step are never seeds (the ratio detector is amplitude-independent, so this keeps round-off precursors of the explicit scheme from being flagged) |
| f_nh_breaking | 0 | breaking switch. 0: off, 1: cells detected as breaking (plus nh_break_margin cells around them) become hydrostatic, so the front dissipates as a bore in the hydrostatic ENC (momentum-conservative advection). **Required for breaking waves running up a slope**: without it the one-layer NH carries the wave unbroken as a thin tongue and the run-up follows the non-breaking law (3-4 times the measured). Use together with f_hcap_upwind=2 to avoid the bore-front spike (§68.7) |
| nh_break_type | 3 | breaking detector. 1: surface rise rate ∂η/∂t > nh_break_alpha·√(gh) (SWASH type; neighbours with nh_break_beta; keeps the state until the crest passes, so the first step after a restart has no history), 2: Froude number \|V\|/√(gh) > nh_break_fr, 3: surface slope \|∇η\| > nh_break_slope (maximum over the 8 neighbours; default; local, Galilean-invariant, stateless). On this grid type 1 fires too late (∂η/∂t does not reach α√(gh) before the front hits the shoreline); 2 and 3 give similar results |
| nh_break_alpha | 0.6 | onset threshold α of detector 1 |
| nh_break_beta | 0.3 | threshold β of detector 1 for cells adjacent to breaking cells |
| nh_break_fr | 0.6 | Froude threshold of detector 2 |
| nh_break_slope | 0.3 | surface-slope threshold of detector 3 (0.15-0.3 give nearly the same run-up for the solitary wave) |
| nh_break_margin | 0 | width of the hydrostatic margin around breaking cells (cells; 0 = automatic 2H/Δx). Turns the crest as well as the front hydrostatic so the NH pressure does not keep pushing the breaking front |

With standing waves in a closed basin (test/nhwave_nh) the periods for
kH = 0.25-2 agree with the one-layer theory within 0.2% (hydrostatic
periods are 12-42% shorter). CG takes 10-90 iterations per step (more
for smaller Δx/H). With the active set (f_nh_adaptive=1) an isolated hump
in a 200 m basin differs from the full solve by 0.1-0.3% of the
correction (margins of 4-16 cells) with 40-60% of the cells active.

For a breaking solitary wave running up a beach (test/nhbreak, Synolakis
1987, a/H = 0.28, slope 1:19.85) the maximum run-up R/H is 0.39
hydrostatic, 0.62 NH with the breaking switch and 0.81 NH alone
(f_hcap_upwind=2), against the empirical 0.42: NH overpredicts. The
hydrostatic ENC gets close by breaking early on the flat part and losing
energy, whereas NH reaches the breaking point unbroken and runs up
higher. For run-up with breaking, hydrostatic (or NH only in deep water)
is recommended for now; NH plus the switch is a research option.

**Others**

| Parameter | Default | Meaning |
|---|---|---|
| f_rivermouth_drop | 0 | free overfall from the river mouth to the sea (legacy scheme; cannot be combined with the tide feature fn_tide -- using [tide](tide.md) + [boundary conditions](boundary.md) is now recommended) |

## Just try it (minimal input)

Everything in this chapter **runs with the defaults** - fn_enc need not be
written. The defaults enable the wet/dry front stabilization
(f_exflux_reduction), the steep-slope gravity correction
(f_gravity_correction) and the adaptive Runge-Kutta (threshold 1.5), a
safe combination for tsunamis, inundation and flood runoff alike.

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

## Format examples

Annotated list of all parameters (with the defaults spelled out):
[examples/List_samples/list_enc.txt](../../../examples/List_samples/en/list_enc.txt).

## Relation to verification

Many of these switches change the computed results. The regression
tests (reference in test/) were created with the defaults, so compare
results obtained with modified settings against your own baseline.
