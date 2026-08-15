# Groundwater (&list_gwflow and model-specific settings)

> English mirror of docs/users_guide/gwflow.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

Handles infiltration, storage, lateral flow, and exfiltration by
shallow groundwater. Enable it with `fn_gwflow`, choose the models in
the common settings `&list_gwflow`, and write the chosen models'
specific setting groups in the same file (groups for unused models may
remain in the file and are ignored - A/B comparisons only require
switching the selectors).

Groundwater in ENCflow is a **shallow two-layer** scheme for runoff
analysis (soil layer + weathered bedrock layer; confined aquifers and
well-scale resource analyses are out of scope).

## Overall configuration (&list_gwflow)

Choose the vertical part (surface <-> subsurface exchange) and the
lateral part (horizontal subsurface movement) independently, and stack
a second layer if needed.

| Parameter | Default | Meaning |
|---|---|---|
| f_gwvertical | 0 | Vertical model. 0: none (temporarily disabled), 1: bucket, 2: Green-Ampt |
| f_gwlateral | 0 | Lateral model. 0: none, 1: nonlinear Boussinesq |
| f_gwlayer2 | 0 | 1: enable the weathered bedrock layer (second layer) |
| dt_gwflow | 0 | Update interval of the groundwater computation (s). 0: every step. If specified, must be at least dt (consistency is maintained through the effective time step) |

**Soil depth sd and specific yield sy0 belong to the geographic
information side** (f_sdtype/sd0/fn_sd, sy0 in &list_geoinfo; see
[the geographic information chapter](geoinfo.md)). They are read only
when a model that needs soil depth (Green-Ampt or lateral) is selected.

**Typical configurations**

| Purpose | Configuration |
|---|---|
| Infiltration losses in an event flood | f_gwvertical=2 (Green-Ampt) only |
| Catchment hydrology (up to interflow) | f_gwvertical=2 + f_gwlateral=1 |
| Down to baseflow / low-flow recession | The above + f_gwlayer2=1 |
| Simplest loss model | f_gwvertical=1 (bucket) |

## Bucket model (f_gwvertical=1, &list_gwflow_bucket)

The simplest model: moves surface water into per-cell subsurface
storage at a constant infiltration capacity.

| Parameter | Meaning |
|---|---|
| gw_infil_mmh | Infiltration capacity (mm/h) |
| gw_capacity | Subsurface storage capacity (columnar water depth, m) |

The infiltration in each step is the minimum of "infiltration capacity
x time", the surface water depth, and the remaining capacity.
**Cannot be combined with the lateral model** (it stops because the
capacity would be doubly defined; if you need a constant infiltration
capacity with soil depth as the capacity, use Green-Ampt with
gw_psif=0).

## Green-Ampt (f_gwvertical=2, &list_gwflow_greenampt)

Moves surface water into the soil layer at the infiltration capacity
of the Green-Ampt formula (piston approximation)
f_v = K_sv (1 + psi_f n_e / F). The storage capacity is soil depth x
specific yield. Saturated cells stop infiltrating, and the excess is
handled by the shallow-water side as surface water.

| Parameter | Meaning |
|---|---|
| gw_ksv_mmh | Vertical saturated hydraulic conductivity K_sv (mm/h) |
| gw_psif | Capillary pressure head at the wetting front psi_f (m). 0 degenerates to a constant infiltration capacity K_sv |

## Lateral flow (f_gwlateral=1, &list_gwflow_lateral)

Lateral Darcy flow in the saturated zone (2D, 8-neighbor; the same
diagonal partitioning as the ENC core). Groundwater moves along the
gradients of the terrain and the soil-layer base, and the excess of
cells exceeding the saturation capacity exfiltrates to the surface
(return flow = generation of saturation-excess overland flow).

| Parameter | Default | Meaning |
|---|---|---|
| gw_ksh_mmh | - | Lateral saturated hydraulic conductivity (mm/h) |
| gw_eps | 1e-3 | Regularization thickness for the dry test and suppression of excessive outflow (m) |
| gw_diagratio | 2/(2+sqrt(2)) | Diagonal partitioning (normally no need to change; 0 is equivalent to 4 neighbors) |

The stability condition of the explicit scheme is checked at
initialization; if dt exceeds the limit, the limit value is printed
and the run stops (lower dt or thin the updates with dt_gwflow).

## Weathered bedrock layer (f_gwlayer2=1, &list_gwflow_layer2)

Inserts a second layer directly below the soil layer to hold a
slow-recession component (baseflow) with a long residence time. Water
percolates down from layer 1, moves laterally within layer 2, the
saturation excess returns to layer 1, and the excess of layer 1
exfiltrates to the surface.

| Parameter | Default | Meaning |
|---|---|---|
| gw2_depth | - | Layer thickness (m) |
| gw2_sy | - | Specific yield (effective porosity) |
| gw2_infil_mmh | - | Infiltration capacity from layer 1 to layer 2 (mm/h) |
| gw2_ksh_mmh | - | Lateral saturated hydraulic conductivity of layer 2 (mm/h). 0 disables lateral flow (a capacity buffer) |
| gw2_sat0 | 0 | Initial saturation [0,1]. In event runs, a calibration parameter that sets the baseflow discharge |

- **Cannot be combined with the bucket vertical model.**
- For long runs, instead of specifying the initial saturation, we
  recommend **spin-up -> save -> reuse as the initial condition**
  (f_state_restore=2 in [Suspend and restart](restart.md)).
- Evapotranspiration does not touch layer 2.

## Output and monitoring

- The distribution of subsurface storage depth can be output as
  `Hg0001` with `f_out_hg = 1` (also `Hg2` when layer 2 is enabled).
- With groundwater enabled, the S column on the screen and in the log
  splits into three columns, **S_surf / S_grnd / S_total**, so the
  surface, subsurface, and total water budgets can be tracked
  separately.
- Restarting models with internal state is handled automatically
  through private state files (the models enabled at save time must
  also be enabled at restart time).

## Worked examples of the format

Annotated examples of all groups:
[examples/List_samples/list_gwflow.txt](../../../examples/List_samples/en/list_gwflow.txt).
For the overall picture of runoff computations combined with rainfall,
see [the rainfall and meteorology chapter](forcing.md).
