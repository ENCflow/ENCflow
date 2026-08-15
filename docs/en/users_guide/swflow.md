# Shallow water flow computation (&list_enc and numerical constants)

> English mirror of docs/users_guide/swflow.md (based on commit 6c5acfc). The Japanese file is the master copy.

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
| f_adaptive_runge | 1 | adaptive Runge-Kutta (recompute with 4-stage RK only the cells with large velocity variation) |
| p_adprunge_thresh | 1.5 | threshold of the velocity variation rate that triggers recomputation (smaller = more accurate and more costly; 1.1 and up) |

The meaning and effect of the threshold are demonstrated in
[tutorial Step 2](../../../tutorials/wave/en/README.md#step-2-setting-enc-parameters).
The Runge column on the screen shows the application rate.

**Flux and stabilization**

| Parameter | Default | Meaning |
|---|---|---|
| f_gravity_correction | 1 | gravity correction (corrects the slope-direction gravity error on steep terrain) |
| f_exflux_reduction | 1 | suppression of excessive outgoing fluxes. Prevents negative depths at fronts advancing over dry ground (recommended to keep on in computations with dry beds) |
| f_hcap_upwind | 1 | limiting the cell-interface depth by the upwind-side depth |
| f_friction_fastmath | 0 | fast evaluation of the friction term. 0: exact (default), 1-5: table approximation (larger = coarser and faster) |
| p_diagratio | 2/(2+sqrt(2)) | weight of the diagonal components in the 8-direction fluxes (normally no need to change) |

**Advection and diffusion terms**

| Parameter | Default | Meaning |
|---|---|---|
| f_advection_tvd | 0 | use a TVD scheme for the advection term |
| p_adv_upwind_index | 0.5 | upwinding index of the advection term (0-1). 0: central difference, 1: first-order upwind difference |
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

**Others**

| Parameter | Default | Meaning |
|---|---|---|
| f_rivermouth_drop | 0 | free overfall from the river mouth to the sea (legacy scheme; cannot be combined with the tide feature fn_tide -- using [tide](tide.md) + [boundary conditions](boundary.md) is now recommended) |

## Format examples

Annotated list of all parameters (with the defaults spelled out):
[examples/List_samples/list_enc.txt](../../../examples/List_samples/en/list_enc.txt).

## Relation to verification

Many of these switches change the computed results. The regression
tests (reference in test/) were created with the defaults, so compare
results obtained with modified settings against your own baseline.
