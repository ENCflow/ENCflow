# Sediment transport, hillslope and long-term processes (supplement to the sediment chapter)

> English mirror of docs/users_guide/sediment.md. The Japanese file is the master copy.

[Back to the sediment chapter](geomorph.md) | [Back to the user's guide index](../users_guide.md)

This page gives the equations and the basis of the default values for the
processes of the [sediment and landform chapter](geomorph.md) that move
sediment with the flow or shape hillslopes over long times: hillslope
creep, bedload, suspended sediment, hillslope erosion, dry-slope erosion,
bedrock weathering and uplift, and the acceleration of morphological time.
Debris flows, slope failure and the moving bed layer are in
[Debris flow, slope failure and moving bed layer](massflow.md). The
implementation is in `src/m_geomorph*.f90` (one submodule per process).

## 1. Common framework

**State variables.** The bed elevation $`z`$, the thickness of the erodible
soil layer $`s_d`$ (`sd`; the base $`z - s_d`$ is the bedrock surface) and
the sediment in the water column expressed as a column thickness of solid
volume, $`h_s`$ (`hs`). When the bed moves by $`\Delta z`$, $`s_d`$ moves by
the same $`\Delta z`$ (**co-moving update**), so the bedrock surface never
moves by erosion or deposition. The total solid
$`\sum h_s + (1-\lambda)\sum(z - z_0)`$ is conserved to machine precision
($`\lambda`$ is the bed porosity `fluv_porosity`).

**Acceleration of morphological time (MORFAC).** The landform is updated
every $`n = \mathrm{NINT}(\texttt{dt\_geomorph}/\Delta t)`$ steps and the
processes receive the effective time step

```math
\Delta t_s = n\,\Delta t\,\cdot\,\texttt{morfac}
```

while the hydraulic clock is not accelerated. This is the MORFAC method
standard in coastal and river morphodynamics[^roelvink06]: one run
represents `morfac` repetitions of the same hydraulic event. All processes
share one `morfac` (different factors per process would break the
simultaneity of hillslope supply and channel deposition); the suspended
load and the hillslope erosion evaluate the exchange with the water column
with the unaccelerated $`\Delta t_w = n\Delta t`$ and apply `morfac` to the
bed side only.

**Dimensionless shear stress.** Bedload, suspended load and hillslope
erosion share the bed shear stress closed with the Manning law,
$`\tau = \rho g n^2 |\mathbf{V}|^2/h^{1/3}`$, made dimensionless with the
grain size $`d`$ and the submerged specific gravity $`s`$ (`fluv_sgrav`,
default 1.65):

```math
\tau_* = \frac{\tau}{\rho\, s\, g\, d} = \frac{n^2 |\mathbf{V}|^2}{s\, d\, h^{1/3}}
```

(gravity cancels). The critical value $`\tau_{*c}`$ = 0.05 is the
representative value of the Shields curve[^shields36] for coarse sand to
gravel.

**Boundary with the sea mask.** The terrain is not updated on the sea
cells of the sea mask (fn_sw), and bedload, creep and the moving bed layer
do not cross the edges against sea cells (a wall). Suspended sediment and
the solid fraction of debris flows disappear outside the system once they
leave into a sea cell (inflow from the sea is clear water). Represent any
area where the sea bottom must be solved as ordinary cells + an initial
water level rather than with the sea mask ("The sea mask and the fate of
sediment" in [Sediment and landform change](geomorph.md)).

## 2. Hillslope creep (f_creep)

```math
\frac{\partial z}{\partial t} = D\,\nabla^2 z,
\qquad
D\,\Delta t_s\left(\frac{1}{\Delta x^2} + \frac{1}{\Delta y^2}\right) \le \frac{1}{2}
```

The classical linear-diffusion model of soil creep[^culling60], solved
explicitly with four-neighbour conservative fluxes (five-point Laplacian).
The inequality is the explicit stability condition, checked at
initialisation. Only $`z`$ is updated and $`s_d`$ is left unchanged (this is
not a model that transports a soil layer of finite thickness), so creep
acts even where $`s_d = 0`$ and moves the soil base too. The default
$`D`$ = 0.005 m²/yr is the middle of the published range of hillslope
diffusivities, 0.001 to 0.05 m²/yr[^fernandes97]. It is a quantity of
morphological time, to be read together with `morfac`. Verification:
[test/creep](../../../test/creep/en/README.md) (Gaussian hill, maximum error
7.8e-5 m against the analytical solution, `morfac` = 2 equivalence 2.3e-4 m).

**Depth-dependent creep (`creep_hstar` > 0)**:

```math
\mathbf{q} = -D\left(1 - e^{-H/H_c}\right)\nabla z,
\qquad
\frac{\partial z}{\partial t} = \frac{\partial s_d}{\partial t} = -\nabla\cdot\mathbf{q}
```

Only the soil layer moves. $`H`$ is the soil depth $`s_d`$ of the supplying
(higher) cell of each edge and $`H_c`$ is the transport decay depth
(`creep_hstar`). It expresses transport proportional to both slope and soil
depth[^johnstone15] in the same form $`K H_* (1 - e^{-H/H_*})`$ as Landlab's
DepthDependentDiffuser; reading $`D = K H_*`$, it reduces to the linear
diffusion above in the limit of a thick soil ($`H \gg H_c`$) (the meaning of
$`D`$ = `creep_d` is unchanged). Because $`z`$ and $`s_d`$ move by the same
amount, the bedrock surface $`z - s_d`$ does not change, and nothing is
carried out of bare rock ($`s_d = 0`$). Evaluating $`H`$ in the supplying cell
and passing the flux, converted to solid volume, through the supply limiter
shared with bedload (a cell never gives more than its soil depth in one
update) are discretisation choices of this model. The effective diffusivity
does not exceed $`D`$, so the stability condition is the same as above.
Verification: the four depth-dependent creep configurations of
[test/creep](../../../test/creep/en/README.md) (agreement with the
conventional linear diffusion to 1.8e-15 m under a thick soil, the bedrock
surface $`z - s_d`$ unchanged to 4e-14 m, conservation of the total soil,
$`s_d \ge 0`$, no change on bare rock). The steady hillslope combined with
soil production (§7) is to be checked in a coupled experiment with a stream at
the foot of the slope (docs/mountain_stream_plan.md §5, in Japanese).

## 3. Bedload (f_fluvial)

**Transport formula.** On each edge the dimensionless transport rate
$`q_{b*}`$ is computed from the two-cell mean $`\tau_*`$ and scaled to
$`q_b = q_{b*}\sqrt{s\,g\,d_{50}^3}`$ (solid volume per unit width).

```math
q_{b*} = 17\,\tau_*^{3/2}\left(1 - \frac{\tau_{*c}}{\tau_*}\right)\left(1 - \sqrt{\frac{\tau_{*c}}{\tau_*}}\right)
\quad(\texttt{f\_qbform} = 1,\ \text{Ashida–Michiue}),
\qquad
q_{b*} = 8\,(\tau_* - \tau_{*c})^{3/2}
\quad(\texttt{f\_qbform} = 2,\ \text{MPM})
```

The Ashida–Michiue formula[^ashida72] is the standard of river-bed
computations in Japan and the Meyer-Peter & Müller formula[^mpm48] the
most used one internationally; both vanish for $`\tau_* \le \tau_{*c}`$. The
edge transport is the projection of the flow direction on the edge normal,
$`u_e/|\mathbf{V}|_e`$, times the passage width $`L_k`$
([ENC grid](encgrid.md) §2): $`Q_k = q_b\,(u_e/|\mathbf{V}|_e)\,L_k`$. The
adaptation length of bedload is taken as short compared with the grid, so
the equilibrium transport is used directly (suspended load, with its long
adaptation length, is handled by a transport equation instead).

![Bedload formulas and equilibrium concentration](../../figs/sediment_laws_en.png)

Panel (a) shows the two formulas ($`\tau_{*c}`$ = 0.05); panel (b) is the
equilibrium concentration of [the debris-flow page](massflow.md) §3.

**Exner equation.** The bed moves with the divergence of the transport.

```math
(1 - \lambda)\frac{\partial z}{\partial t} = -\nabla\cdot\mathbf{q}_b
\quad\Longrightarrow\quad
\Delta z_{i,j} = -\frac{\Delta t_s}{(1-\lambda)\,\Delta x\,\Delta y}\sum_{k=1}^{8} Q_k
```

This is Exner's bed continuity equation[^exner25]. Numerical overshoot is
prevented in this order: (1) an edge never erodes more than the soil
thickness $`s_d`$ of its upwind cell, (2) the bed change per update is
limited by `fluv_dzmax` (default 0.05 m; the analogue of a Courant
condition for bed waves; the number of events is reported at the end),
(3) where the simultaneous outflow through several edges would exceed the
soil thickness of a cell, every bed-load flux leaving that cell is scaled
down by the same factor (supply limiter; the sediment volume stays exactly
conserved and the number of limited cells is reported at the end),
(4) whatever still crosses the bedrock surface by round-off is clipped and
the lost volume is reported (normally none). On open boundaries the
outflow is always at capacity and the inflow is fed when `fluv_bcfeed = 1`
(the supply through the inflow face equals the net outflow of the inflow
cell times `fluv_bcfeed_fac`; factor 1 fixes the bed of the inlet). Inflow
segments also take a bed-load discharge series `inflow_qb` (a source to the
bed) and the equilibrium concentration feed `inflow_cs_eq` of the suspended
sediment ([boundary conditions](boundary.md)). Bed load rolls on the bed surface: a dry cell never
supplies it and it is never carried onto ground above the water surface
of the supplying cell (a bank face; developer.md §84.2).

**Direction of the bed load (correction in bends).** By default the
direction is the depth-averaged flow direction $`\hat{\mathbf t}`$. With
`fluv_slope = 1` and `f_secflow = 1` it becomes

```math
\mathbf{q}_b = q_b\left(\hat{\mathbf t} + r\,\hat{\mathbf n} - \gamma\nabla z\right),\qquad
\gamma = \sqrt{\frac{\tau_{*c}}{\mu_s\mu_k\tau_*}},\qquad
r = N_* h\,\kappa
```

where $`\hat{\mathbf n}`$ is the left normal of the flow direction and
$`\kappa`$ the streamline curvature of the depth-averaged velocity field
(positive for a left turn; $`\kappa\hat{\mathbf n}`$ points to the centre of
curvature, so $`r\hat{\mathbf n}`$ always points to the inside of the bend).
$`\gamma\nabla z`$ is the transport down the slope (Hasegawa 1981 type, the
same form as the bed-slope correction of Nays2DH) and $`r\hat{\mathbf n}`$
the effect of the near-bed secondary flow pointing to the inside of the
bend (equilibrium secondary flow of the Engelund type). The secondary flow
carries sediment to the inner bank and the slope term brings it back down
the transverse slope that forms; the balance gives a cross section with a
deep outer and a shallow inner side, $`\partial z/\partial n \approx
r/\gamma`$. The curvature is evaluated only in cells whose four
neighbours are all wet ($`r = 0`$ along banks and boundary columns), and
bank-face steps are excluded from $`\nabla z`$. The coefficients
$`\mu_s = 1.0, \mu_k = 0.45`$ (Asahi et al. 2013 eq. (22), Hasegawa 1984) and $`N_* = 7.0`$ (Engelund 1974) are the defaults (literature check in §84.12). `fluv_taufac` is a simple separation of
the effective shear stress: a fixed fraction of the total-resistance
$`\tau_*`$ is passed to the transport formula. Verification:
[test/bendsed](../../../test/bendsed/en/README.md).

**Bank retreat and collapse.** A bank face (a neighbouring cell b whose
ground is at or above the water surface $`z_w + h_w`$ of a wet cell w)
retreats with `f_berode = 1` at

```math
E_b = K_b\,\max\!\left(\frac{\tau_{*w}}{\tau_{*c,b}} - 1,\,0\right)^{m},\qquad
Q_{b\to w} = (1-\lambda)\,E_b\,h_w\,L_k
```

($`\tau_{*w}`$ is the dimensionless shear stress of the toe cell, $`h_w`$
the submerged bank height, equal to the toe depth, and $`L_k`$ the passage
width). The eroded volume is deposited on the toe cell and carried on by
the bed load (applied as an edge flux through the same conservative path;
the soil-depth supply limiter also bounds the erodible layer of the bank).
The angle-of-repose avalanching of `f_repose = 1` moves, per update, a
height $`\mathrm{relax}\cdot e/16`$ from the higher to the lower cell
for the part $`e`$ of the height difference between neighbours that exceeds
$`\tan\phi_r \cdot d_k`$ (a conservative relaxation that does not
overshoot with eight directions at once; one sweep per update).
Verification: [test/berode](../../../test/berode/en/README.md),
[test/repose](../../../test/repose/en/README.md).

**Fixation.** The cell fixation degree $`a`$ of `f_fixation = 1` grows while
the cell is dry (h ≤ dd) as

```math
a \leftarrow 1 - (1 - a)\,e^{-\Delta t_m / T_\mathrm{fix}}
```

($`\Delta t_m`$ is the morphological update interval, morfac included) and
returns to 0 while submerged once the cumulative erosion below the fixation
surface (the ground level when the cell was last dry, pushed up by
deposition) exceeds `fix_dzreset`. Its only effect is to replace
$`\tau_{*c}`$ by $`\tau_{*c}(1 + c_\tau a)`$ in the threshold and the
transport formula of the bed load supplied by that cell and in the bank
erosion of that cell as the bank, to reduce the entrainment term of the
suspended sediment by the same ratio ($`\tau_{*c,s}(1 + c_\tau a)`$ for the
excess-shear form, $`C_{eq}/(1 + c_\tau a)`$ for Itakura-Kishi; settling is
unchanged), and, with `fix_cn` > 0, to make the Manning n of the flow
friction $`n(1 + c_n a)`$ (the $`\tau_*`$ of the sediment keeps the original
n; elevations and volumes are untouched). Verification:
[test/fixation](../../../test/fixation/en/README.md).

**Defaults.** `fluv_d50` = 0.01 m lies near the geometric mean of a sand
bed (0.5 mm) and a mountain gravel bed (5 cm); values for sand and gravel
beds are in the recommended values at the end of the chapter.
`fluv_porosity` = 0.4 and `fluv_sgrav` = 1.65 are the standard values of
sand and gravel. Verification: [test/fluvial](../../../test/fluvial/en/README.md)
(total solid 4.6e-16, co-moving update 1.2e-14),
[test/sedinflow](../../../test/sedinflow/en/README.md) (closure of the
sediment supplied through the boundary).

## 4. Suspended sediment (f_suspend)

**Transport.** The concentration $`C = h_s/h`$ is the solid volume per
water volume; the water-column advection is done inside the shallow water
step with the same edge fluxes as the water (the scheme is
`f_scalar_scheme` of [the advection explanation](advection.md) §7, by default
the link-wise MUSCL; a uniform concentration stays uniform by construction). The exchange with the bed is
evaluated per cell at the landform update:

```math
\Delta h_s = w_f\left(C_{eq} - \beta\,C\right)\Delta t_w,
\qquad
\Delta z = -\frac{\texttt{morfac}}{1-\lambda}\,\Delta h_s
```

The first term is the entrainment $`E = w_f C_{eq}`$, the second the
settling $`D = w_f\,\beta\,C`$ (near-bed concentration factor $`\beta`$ =
`susp_beta`, default 1). In dry cells ($`h \le d_d`$) all suspended sediment
returns to the bed. In channel cells with a cross-section shape σ the
exchange is multiplied by the wetted-width fraction $`\sigma(h)`$.

**Equilibrium concentration.** `f_esform` = 1 is the simple calibration
form $`C_{eq} = \texttt{susp\_esa}\,(\tau_*/\tau_{*c} - 1)`$; `f_esform` = 2 is
the Itakura–Kishi entrainment formula[^itakura80]:

```math
C_{eq} = \frac{\max(q_{su}, 0)}{w_f},
\qquad
q_{su} = K\left[\frac{\alpha_*}{s+1}\,\frac{s\,g\,d}{u_*}\,\Omega - w_f\right],
\qquad
\Omega = \frac{\tau_*}{B_*}\,\frac{e^{-a'^2}}{\sqrt{\pi}\,\mathrm{erfc}(a')} + \frac{\tau_*}{B_*\eta_0} - 1,
\quad a' = \frac{B_*}{\tau_*} - \frac{1}{\eta_0}
```

$`K`$ = 0.008, $`\alpha_*`$ = 0.14, $`B_*`$ = 0.143 and $`\eta_0`$ = 0.5 are the
constants of the original formula and $`u_* = \sqrt{\tau_* s g d}`$. It gives
the entrainment of sand without a calibration parameter, so 2 is
recommended for sand.

**Settling velocity.** With `susp_wf` = 0 it is derived from the grain size
with Rubey's formula[^rubey33]:

```math
w_f = \left[\sqrt{\frac{2}{3} + \frac{36\nu^2}{s g d^3}} - \sqrt{\frac{36\nu^2}{s g d^3}}\right]\sqrt{s g d},
\qquad \nu = 10^{-6}\ \mathrm{m^2/s}
```

Rubey's formula does not apply to clay and silt flocs; for mud give the
effective settling velocity in `susp_wf` directly and read the simple form
$`E = w_f\,\texttt{esa}\,(\tau_*/\tau_{*c} - 1)`$ as the Partheniades erosion
law[^partheniades65] $`E = M(\tau/\tau_{ce} - 1)`$, calibrating `susp_esa`
and `susp_tausc`.

**Defaults.** `susp_d50` = 0.2 mm is fine sand, the representative grain
size of suspended load; `susp_esa` = 1e-4 is the coefficient of the simple
form, which has no published value, calibrated in
[test/suspend](../../../test/suspend/en/README.md) (**empirical**).
Verification: the same test, total solid conserved to 2.2e-15 with both
equilibrium formulas.

## 5. Hillslope erosion (f_wash)

Wet ($`h > d_d`$) cells outside channels ($`r_w = 0`$) release sediment by
raindrop and sheet erosion into the suspended load $`h_s`$ (`f_suspend` is
required).

```math
E = k_r\,P + k_f\,\max\!\left(\frac{\tau_*}{\tau_{*c}} - 1,\ 0\right)
\qquad[\mathrm{m/s},\ \text{solid volume}]
```

$`P`$ is the rainfall intensity reaching the ground, $`k_r`$ (`wash_kr`,
dimensionless) the detached volume per rainfall and $`k_f`$ (`wash_kf`, m/s)
the coefficient of sheet erosion linear in the excess shear, with
$`\tau_*`$ evaluated with the suspended grain size. It is a USLE-type
empirical law written with the grid variables; the defaults 0.01 and
1e-5 m/s are the values of [test/wash](../../../test/wash/en/README.md)
(**empirical, to be calibrated**). The detached volume is subtracted from
$`z`$ and $`s_d`$ co-movingly and erosion stops at $`s_d = 0`$ (exposed
bedrock). Outside channels the entrainment $`E`$ of the suspended load and
the $`k_f`$ term overlap conceptually; when both are used, manage the
overlap through the calibration.

**Width scale (`wet_lw`).** Sheet erosion and entrainment are both
proportional to $`\tau_*`$, and the positive feedback that erodes only the
one cell where the flow has gathered has no length scale, so the width and
spacing of gullies are set by the grid spacing. When `wet_lw` $`= \ell_w`$
is given, the detachment depth $`e_j`$ evaluated per cell is spread with a
Gaussian kernel $`K`$ of standard deviation $`\ell_w`$ before it is applied
to the bed ($`\Delta z_i = -\sum_j K_{ij}\,e_j`$; the kernel is symmetric and
the shares that would fall outside the domain or on sea cells are returned
to the source cell, so $`\sum_i \Delta z_i = -\sum_j e_j`$: the total solid is
conserved). The suspended sediment $`h_s`$ enters the source cell $`j`$.
$`\ell_w`$ is the width of the rills (flow paths), approximated as a fixed
value independent of discharge.

## 6. Dry-slope erosion (f_splash)

Valley formation on highly permeable slopes without surface flow
(badlands, cliffs of pyroclastic cones) is parameterised as a sub-grid
process acting on dry ($`h \le d_d`$) cells outside channels:

```math
E = P\left[k_r\,(1 + c_a\,\kappa) + k_t\,(1 + c_b\,\kappa)\,S^{h}\right],
\qquad
S = |\nabla z|,\quad \kappa = \max(\nabla^2 z, 0)
```

The first term is raindrop splash (active on a plateau too), the second
the slope-dependent erosion by grain aggregates rolled by raindrops
[^trottet25] and by sub-grid rills; the positive feedback in concave
terrain ($`\kappa > 0`$; `spl_ca`, `spl_cb`) grows valleys. The detached
sediment cannot be carried without flow, so it is **exported out of the
system** (the total is reported at the end) and $`z`$, $`s_d`$ are reduced
co-movingly. A concavity feedback without smoothing grows fastest at the
shortest wavelength (the infinite-wavenumber problem of Smith &
Bretherton[^smith72]): with the curvature taken on the grid (`spl_lc` = 0)
the valley spacing sticks to 2-3 grid cells (adding a diffusion term only
decides whether perturbations grow at all, since both amplification and
diffusion scale with $`k^2`$; creep is not a mechanical model and is not
combined with it). When the curvature is taken from $`z`$ smoothed over a
correlation length $`\ell`$ (`spl_lc`, the collection scale of the sub-grid
rills), the growth rate of a perturbation

```math
\sigma(k) = D_a\,k^2\,e^{-\ell^2 k^2/2},\qquad
D_a = P\,k_t\,c_b\,S^{h}
```

has a maximum at the finite wavenumber $`k^* = \sqrt{2}/\ell`$, so the
valley spacing $`\lambda^* = 2\pi\ell/\sqrt{2} \approx 4.4\,\ell`$ is set
by $`\ell`$ alone (where Perron et al.'s $`\lambda \propto \sqrt{K_s/K}`$
[^perron09] sets the spacing by the ratio of amplification to diffusion,
here the smoothing scale itself sets it). The curvature at a V-shaped valley floor is also bounded by
$`\sim 2S/\ell`$ (the speed of the deep-valley stage, where the walls
steepen to one-cell steps, still depends on the grid through $`S`$;
examples/badland).
`spl_zbase` is the erosion base level (the sea level when the cliff foot is
the sea) and `spl_dzmax` a safety valve. With `spl_ksat` the $`\kappa`$ in the
amplification is replaced by the effective curvature
$`\tilde\kappa = \kappa/(1 + \kappa/\kappa_s)`$, which saturates the amplification
at strong hollows (the foot of a cliff) at $`1 + c\,\kappa_s`$ (the spacing selection
of the linear stage is unchanged; verification:
[test/splashsat](../../../test/splashsat/en/README.md)). A table of horizontal strata
`spl_strata` (bottom elevation and erodibility factor per layer) multiplies
$`E`$ by the factor of the layer in which the cell's surface elevation lies
(banded hard/soft beds, benches, cap rock; a layer with factor 0 does not
erode; verification: [test/splashstrata](../../../test/splashstrata/en/README.md)).
The defaults $`k_r`$ = 0.0005 and $`k_t`$ = 0.05 are the medians of the tests
(**empirical**); verification is
[test/splash](../../../test/splash/en/README.md) (all digits agree with the
analytical form $`\Delta z = P(k_r + k_t S)T`$ without amplification; the
export ledger equals the analytical sum) and
[test/splashslide](../../../test/splashslide/en/README.md) (contrast of a
cohesive and a loose cliff). The full reasoning and trials are in
docs/splash_plan.md.

## 7. Bedrock weathering and uplift (f_wthr / f_uplift)

**Soil production.** Weathering keeps $`z`$ and thickens $`s_d`$ (the
bedrock surface descends) following an exponential law that slows with
soil thickness[^heimsath97]:

```math
\frac{d s_d}{dt} = W_0\,e^{-s_d/s_*}
\quad\Longrightarrow\quad
s_d^{\,n+1} = s_d + s_*\ln\!\left(1 + \frac{W_0\,\Delta t_s}{s_*}\,e^{-s_d/s_*}\right)
```

The update is the propagator of the exact solution of the ordinary
differential equation, so it is unconditionally stable for any `morfac`.
$`W_0`$ (`wthr_p0`, default 50 mm/kyr) is the middle of the bare-rock soil
production rates 0.01 to 0.1 mm/yr and $`s_*`$ (`wthr_sdstar`, default
0.5 m) a representative decay depth. With `fn_wthr`, the rate becomes
$`W_0 f_w`$ with a cell-wise multiplier distribution (differences in
lithology; cells with multiplier 0 do not weather. Use it where the bedrock
surface should be lowered by fluvial incision rather than by weathering,
such as the bedrock of mountain streams). The multiplier acts on the
production rate only; the decay depth $`s_*`$ is common to the whole domain.

**Uplift.** $`z \mathrel{+}= U\,\Delta t_s`$ ($`s_d`$ unchanged: the bedrock
rises as a rigid body). $`U`$ (`uplift0`, default 1 mm/yr) is the lower end
of the representative values of orogenic belts; negative values are
subsidence. Sea-mask cells are the base level and are excluded. With
`fn_uplift`, the rate becomes $`U f_u`$ with a cell-wise multiplier
distribution (0 at the outlet cells fixes the base level, negative values
lower it; differential uplift of fault blocks can also be given).
Long-term landscape evolution is meant to be run as "representative
hydrology repeated × MORFAC × restart chains", the CAESAR-Lisflood style
[^coulthard13] (developer.md §32).

### Limestone dissolution (f_dissol)

**Chemical denudation.** Limestone dissolving in water is the counterpart
of weathering (it lowers $`z`$ and keeps $`s_d`$) and is proportional to
the water entering the rock[^white84][^gabrovsek09]:

```math
\frac{dz}{dt} = -\,k_d\, f_{\rm sol}\,(q_{\rm r} + f_{\rm sink}\, q_{\rm sink}),
\qquad k_d = \frac{c_{\rm eq}}{\rho_{\rm r}}
```

$`q_{\rm r}`$ is the diffuse recharge flux (infiltration, `dissol_src = 1`,
rainfall on the ground, `dissol_src = 2`, or infiltration plus the runoff
generated on bare rock $`f_{\rm surf}\, f_b\,(P - I)`$, `dissol_src = 3`,
with $`f_b = \max(0, 1 - s_d/s_{\rm surf})`$ the bare-rock factor), $`q_{\rm sink}`$ the inflow
flux into the sinks (inlets) of the conduit continuum layer
(`dissol_sink = 1`) and $`f_{\rm sol}`$ the soluble fraction of the cell
(`fn_dissol`). One geomorphic update dissolves
$`w = k_d f_{\rm sol} F \cdot \texttt{morfac}`$ from the water $`F`$ (m)
accumulated over the update interval, and leaves the insoluble residue
fraction $`f_{\rm res}`$ (`dissol_fres`) in the soil:
$`z \leftarrow z - (1 - f_{\rm res}) w`$,
$`s_d \leftarrow s_d + f_{\rm res} w`$. Local and linear, hence
unconditionally stable.

**Lateral dissolution** (`dissol_lat` = $`p`$). Of the capacity $`W_w`$ of
a ponded cell w, the share $`p`$ goes to the land cells n among its 8
neighbours whose floor is above the water surface $`e_w`$ (rock walls), in
proportion to the contact width $`L_k`$ (Δx on the axes, Δx·2/(2+√2) on
the diagonals), and $`1-p`$ to the floor (a cell without walls gives
everything to the floor):

```math
\Delta z_n = -\,f_{{\rm sol},n}\, p\, W_w \frac{L_k}{\sum_{m\in{\rm walls}(w)} L_m},
\qquad \Delta z_w = -\,f_{{\rm sol},w}(1-p)\,W_w
```

The total capacity is unchanged (a partition) and wall retreat is
represented by lowering the wall cell. $`p`$ is the ratio of floor to wall
dissolution; with `dissol_lat = −1` it is set per cell from the wetted-area
ratio $`p_w = h_w \sum L / (h_w \sum L + \Delta x \Delta y)`$ (recommended:
deeper ponding gives the walls a larger share). A fixed value should follow
the ratio of ponding depth to cell size (about 0.8 for h = 5 m, Δx = 10 m).

$`c_{\rm eq}`$ (`dissol_ceq`, default 100 mg/L as CaCO₃) is the
**effective dissolution capacity**: the equilibrium solubility minus the
concentration already carried by the inflowing water, i.e. the mass of
rock dissolved by 1 m³ of water. The carbonate equilibrium is not solved;
soil CO₂ and temperature are folded into this single value (50 to 80 for
rain on bare rock, 100 to 300 mg/L under a soil cover). With
$`\rho_{\rm r}`$ (`dissol_rho`, default 2500 kg/m³) this gives
$`k_d`$ = 4×10⁻⁵ m/m, i.e. 40 mm/kyr for a recharge of 1 m/yr, inside the
published range of karst denudation rates of 20 to 100 mm/kyr
[^gabrovsek09]. Water always dissolves its full $`c_{\rm eq}`$
(undersaturated, constant rate), so the decay of dissolution by
saturation along the flow path is not represented. Conduit (cave) growth
is a separate, not yet implemented stage (docs/karst_plan.md §5).

### Bedrock incision by flowing water (f_rockinc)

**Plucking, abrasion and cover.** The bedrock surface $`R = z - s_d`$ is
lowered by plucking by the flow and by abrasion by the transported gravel
(the tools effect), and the mobile layer $`H = s_d`$ suppresses the incision
through the exposure $`e^{-H/H_*}`$:

```math
\tau_b = \frac{\rho_w g n^2 |V|^2}{h_e^{1/3}},\qquad
E_{p0} = f_r\,k_p \max\!\left(\frac{\tau_b}{\tau_c} - 1,\ 0\right)^{m},\qquad
E_{a0} = f_r\,\beta\,q_c\,F_s(H)
```

```math
\frac{dR}{dt} = -(E_{p0} + E_{a0})\,e^{-H/H_*},\qquad \frac{dH}{dt} = E_{p0}\,e^{-H/H_*}
```

$`\tau_b`$ uses the same Manning closure as bedload
($`h_e = \max(h, d_v)`$), and $`f_r`$ is the erodibility multiplier
(`fn_rock`). The plucking term writes the excess-shear-stress form
$`E = k_e(\tau_b - \tau_c)^m`$ of the type that expresses the erosion rate of
bedrock channels by the bed shear stress[^howard83] in ratio form with
$`k_p = k_e \tau_c^m`$, so $`k_p`$ is "the incision rate of bare rock at
$`\tau_b = 2\tau_c`$" (m/s) (the source of the thresholded form is still
being checked). Expressing the cover as an exponential of the layer
thickness is the same as in SPACE[^shobe17] and Landlab's
GravelBedrockEroder. The plucked rock becomes a mobile layer of the same
thickness ($`z`$ is unchanged), and bulking is absorbed into $`k_p`$ (the
same 1:1 conversion as weathering; **our own simplification**). In the
abrasion term, $`q_c`$ is the bedload capacity of the cell (solid transport
rate per unit width), and $`q_c F_s`$ is the bedload leaving the cell, taken
as the amount of gravel striking the bed (the same form as "abrasion = β ×
transport rate × exposure" of GravelBedrockEroder). The abraded material
leaves the system as fines ($`z`$ is lowered) and is not added to the cover.

**Thin-layer transport.** The edge flux of bedload is multiplied by the
availability $`F_s = 1 - e^{-H/H_*}`$ of the supplying cell. In a steady
state with a uniform capacity $`q_c`$ and a constant transport rate
$`q_s`$, $`F_s = q_s/q_c`$, and the exposure is $`1 - q_s/q_c`$, i.e. it
agrees with the cover written as a supply ratio[^sklar04][^turowski07], and
the incision rate by abrasion becomes the hump $`E = \beta q_s (1 - q_s/q_c)`$
(largest at $`q_s/q_c = 1/2`$, and 0 with full cover at 1 and above; the same
form as the linearization of the saltation–abrasion model of Sklar and
Dietrich). The
idea of setting the cover by the ratio of the alluvial thickness to the bed
relief[^zhang15] is written as a closure that uses the same $`H_*`$ for the
exposure and the availability; this combination and the dimensional form are
**our own** (docs/mountain_stream_plan.md §4.3). The steady state in which
the plucked rock joins the transport downstream follows from solving
$`q_i = q_{i-1} + (1-\lambda)\Delta x\,E_{p0}(1 - q_i/q_c)`$ cell by cell
(T3 of test/rockinc).

**Time integration.** The hydraulics are frozen at the start of an update
and the exposure is integrated exactly:

```math
H^{n+1} = H^n + B_p,\qquad
B_p = H_*\ln\!\left(1 + \frac{E_{p0}\,\Delta t_s}{H_*}\,e^{-H^n/H_*}\right),\qquad
B_a = \frac{E_{a0}}{E_{p0}}\,B_p
```

(the same form as the weathering propagator; $`F_s`$ of the abrasion is frozen
at its value at the start of the update, and with $`E_{p0} = 0`$,
$`B_a = E_{a0}\,\Delta t_s\,e^{-H^n/H_*}`$). Changing the update interval
or `morfac` gives the same result, and it is unconditionally stable. The
outflow from a thin layer is explicit, with the time scale
$`H_*(1-\lambda)\Delta x / q_c`$.

## 8. Parameters and the basis of their defaults

The labels in the Basis column are explained in [How to read the basis of a default](../users_guide.md#how-to-read-the-basis-of-a-default).

| Parameter | Default | Meaning | Basis |
|---|---:|---|---|
| dt_geomorph / morfac | 0 / 1 | update interval (s) / acceleration of morphological time (§1) | **method** MORFAC method[^roelvink06]; 1 for event runs |
| creep_d | 0.005 m²/yr | creep diffusivity $`D`$ (§2) | **literature value** middle of the published range 0.001–0.05 m²/yr[^fernandes97] |
| creep_hstar | 0 (conventional linear diffusion) | decay depth $`H_c`$ of depth-dependent creep (m) (§2) | **calibration value** no standard value. Does not affect the result under a thick soil |
| f_qbform | 1 | bedload formula (§3) | **method** 1: Ashida–Michiue[^ashida72], 2: MPM[^mpm48] |
| fluv_d50 | 0.01 m | representative grain size of bedload | **empirical** near the geometric mean of sand and gravel beds |
| fluv_tausc / susp_tausc / wash_tausc | 0.05 | critical dimensionless shear stress (§1) | **literature value** representative value of the Shields curve for coarse sand to gravel[^shields36] |
| fluv_porosity / fluv_sgrav | 0.4 / 1.65 | bed porosity / submerged specific gravity | **customary value** standard values of sand and gravel |
| fluv_dzmax | 0.05 m | bed change per update (§3) | **numerical** safety valve (Courant condition of bed waves) |
| fluv_bcfeed | 0 | feeding at open boundaries (§3) | **method** 0: no feeding, 1: capacity feeding (net outflow of the inflow cell times the factor) |
| fluv_bcfeed_fac | 1.0 | factor of the capacity feed | 1 = fixed inlet bed, 0 = no feed |
| f_esform | 1 | equilibrium concentration (§4) | **method** 1: simple (calibration), 2: Itakura–Kishi[^itakura80] (recommended for sand) |
| susp_d50 / susp_wf | 0.2 mm / 0 | grain size / settling velocity | **customary value** fine sand / **derived** 0 uses the Rubey formula[^rubey33] |
| susp_beta | 1.0 | near-bed concentration factor $`\beta`$ | **method** 1 = vertically uniform approximation |
| susp_esa | 1e-4 | coefficient of the simple form | **verification case** calibrated in [test/suspend](../../../test/suspend/en/README.md) (weak basis) |
| f_bedfines / fines_la / fines_frac0 | 0 / required / 0 | ledger of fines in the bed (§4) | **method** two-component stock. L_a is a numerical mixing thickness (a few cm to 0.1 m); the fraction is a given |
| wash_kr / wash_kf | 0.01 / 1e-5 m/s | raindrop / sheet erosion coefficients (§5) | **empirical** values of [test/wash](../../../test/wash/en/README.md); to be calibrated |
| wet_lw | 0 m | correlation length $`\ell_w`$ of the lateral spreading of the detachment depth (§5) | **given** 0 = off. A guide is the width of the rills (flow paths); with Δx ≤ ℓ_w/2 the gully spacing no longer depends on the grid ([test/wetlw](../../../test/wetlw/en/README.md)) |
| spl_kr / spl_kt / spl_h | 5e-4 / 0.05 / 1 | dry-erosion coefficients and slope exponent (§6) | **empirical** medians of the tests |
| spl_ca / spl_cb | 0 / 0 m | concavity amplification lengths | **given** 0 = no amplification; a few to tens of metres to grow valleys |
| spl_dzmax | 0 | erosion limit per update | **numerical** 0 = off; safety valve against runaway |
| spl_lc | 0 m | correlation length $`\ell`$ of the curvature | **given** 0 = curvature on the grid (grid-dependent spacing); about one fifth of the valley spacing (examples/badland) |
| spl_zbase | none | erosion base level | **given** the sea level when the cliff foot is the sea |
| spl_ksat | 0 | saturation curvature $`\kappa_s`$ of the amplification | **given** 0 = no saturation; 0.05-0.2 1/m keeps benches at the foot of cliffs (examples/mesa) |
| spl_strata | none | table of horizontal strata (bottom elevation, erodibility factor) | **given** hard/soft contrast of the stratigraphy; factor 0 = cap rock |
| wthr_p0 / wthr_sdstar | 50 mm/kyr / 0.5 m | soil production rate / decay depth (§7) | **literature value** middle of the published range of the Heimsath function[^heimsath97] |
| fn_wthr | none (1 everywhere) | distribution of the multiplier of the soil production rate | **given** differences in lithology, cells without weathering (0; the bedrock of mountain streams, for example) |
| uplift0 | 1 mm/yr | uplift rate | **customary value** lower end of orogenic belts |
| fn_uplift | none (1 everywhere) | distribution of the uplift multiplier | **given** fixed (0) or falling (negative) base level, fault blocks |
| dissol_ceq / dissol_rho | 100 mg/L / 2500 kg/m³ | effective dissolution capacity / rock density (§7) | **literature value** representative CaCO₃ concentration of recharge in limestone areas[^white84] and the density of limestone. k_d = 4e-5 m/m, i.e. 40 mm/kyr for a recharge of 1 m/yr (published range 20-100)[^gabrovsek09] |
| dissol_src / dissol_sink | 1 / 0 | water source / sink term | **method** 1: infiltration, 2: rainfall on the ground, 3: infiltration + runoff on bare rock. The sink term is the inlet inflow of the conduit continuum layer |
| dissol_fsurf / dissol_sdsurf | 0.3 / 0.1 m | capacity ratio of the runoff in the surface source / soil thickness counted as bare rock | **literature value** ratio of rain on bare rock (50-80 mg/L) to recharge under soil (100-300) / **numerical setting** |
| dissol_dzmax | 0 | cap on the dissolution per cell and update | **numerical setting** 0 = off. A safety valve of the fluv_dzmax type (the excess is discarded as saturation) |
| dissol_fsink / dissol_fres | 1.0 / 0 | capacity ratio of the sink inflow / residue fraction | **empirical value** to be calibrated / **given** 0 = no residue |
| dissol_lat | 0 | share p of lateral dissolution | **method** 0 = floor only, −1 = automatic from the wetted-area ratio (recommended). A fixed value follows the ratio of ponding depth to cell size |
| rock_kp / rock_tauc | 0 (no plucking) / none | plucking rate coefficient (m/s) / threshold (Pa) (bedrock incision of §7) | **calibration value** no standard value. k_p is the incision rate of bare rock at τ_b = 2τ_c |
| rock_m | 1 | plucking exponent | **conventional value** linear (same as berode_m of bank erosion) |
| rock_beta | 0 (no abrasion) | abrasion coefficient β (1/m) | **calibration value** no standard value. The largest incision rate by abrasion (cover fraction 1/2) is β q_c / 4 |
| rock_hstar | none | cover length H* | **given** a measure of the relief of the bedrock surface and the grain size (a few cm to tens of cm). Shared by the exposure and the availability |
| fn_rock | none (1 everywhere) | erodibility multiplier of the bedrock | **given** lithological contrast. 0 = not eroded |

**Where to look when revising the defaults**

- Grain size (d50), porosity and specific gravity come directly from
  bed-material surveys (sieve analysis); read the critical Shields stress
  from the Shields curve[^shields36] at the grain Reynolds number
  (0.03–0.06 for sand to gravel).
- Choose the bedload formula and its coefficients from measured transport
  rates when available; otherwise Ashida–Michiue[^ashida72] is customary
  for sand–gravel beds and MPM[^mpm48] for coarse gravel.
- Creep, soil production and uplift are long-term quantities: take them
  from cosmogenic-nuclide erosion and soil-production studies[^heimsath97]
  and from regional uplift rates (levelling, dated terraces).
- Sheet and dry erosion coefficients have no universal value; calibrate
  them on sediment-yield observations (turbidity, reservoir sedimentation)
  or on the measured landform change of past events.

## 9. Verification cases

| Case | Content | Point |
|---|---|---|
| [test/creep](../../../test/creep/en/README.md) | diffusion of a Gaussian hill | maximum error 7.8e-5 m, morfac equivalence. Depth-dependent creep: bedrock surface unchanged, soil conserved, no change on bare rock |
| [test/fluvial](../../../test/fluvial/en/README.md) | dam break and bed change in a closed domain | total solid and co-moving update to machine precision |
| [test/suspend](../../../test/suspend/en/README.md) | two equilibrium formulas | total solid 2.2e-15 |
| [test/sedinflow](../../../test/sedinflow/en/README.md) | sediment supplied through the boundary | ledger closure ~1e-16 |
| [test/wash](../../../test/wash/en/README.md) | rain + dam break hillslope erosion | total solid 1.7e-13 |
| [test/splash](../../../test/splash/en/README.md) | dry erosion on a slope with a break | all digits agree with the analytical form, export ledger agrees |
| [test/splashslide](../../../test/splashslide/en/README.md) | cohesive / loose cliff | relief growth ×1.34 / ×0.77 |
| [examples/badland](../../../examples/badland/) | valley formation on a plateau edge | valleys grow from the cliff edge with zero surface flow |
| [test/rockinc](../../../test/rockinc/en/README.md) | bedrock incision by flowing water | analytic self-cover solution 9e-8, quasi-steady cover 4e-4, hump of abrasion 7e-4, conservation in a closed box (9 digits with the ledger), the steady slope under a supply at the head within 1.5 % of the quasi-analytic solution with the sediment budget to 4e-10 |
| [examples/bedrock_cover](../../../examples/bedrock_cover/en/README.md) | cover effect in bedrock channels | steady incision rates of the 3 models within 2.3 % of the theory, constant versus pulsed supply with the same total, initial cover, retreat of a step |
| [test/hillsoil](../../../test/hillsoil/en/README.md) | soil production by weathering | 1.6e-15 to the analytical solutions with a uniform and a distributed (fn_wthr) rate, cells with multiplier 0 unchanged |

## References

[^roelvink06]: Roelvink, J. A. (2006): Coastal morphodynamic evolution techniques. *Coastal Eng.*, 53, 277–287. (MORFAC)
[^shields36]: Shields, A. (1936): Anwendung der Ähnlichkeitsmechanik und der Turbulenzforschung auf die Geschiebebewegung. Mitt. Preuss. Versuchsanst. Wasserbau Schiffbau, 26, Berlin.
[^culling60]: Culling, W. E. H. (1960): Analytical theory of erosion. *J. Geol.*, 68, 336–344. (linear diffusion of hillslopes)
[^fernandes97]: Fernandes, N. F. and Dietrich, W. E. (1997): Hillslope evolution by diffusive processes: The timescale for equilibrium adjustments. *Water Resour. Res.*, 33, 1307–1318. (range of diffusivities)
[^johnstone15]: Johnstone, S. A. and Hilley, G. E. (2015): Lithologic control on the form of soil-mantled hillslopes. *Geology*, 43(1), 83–86. doi:10.1130/G36052.1 (checked against the abstract: when transport scales with both slope and soil depth, rock type shows up in the form of soil-mantled hillslopes. The form of the equation and the doi follow the description of Landlab's DepthDependentDiffuser)
[^ashida72]: Ashida, K. and Michiue, M. (1972): Study on hydraulic resistance and bed-load transport rate in alluvial streams. *Proc. JSCE*, 206, 59–69 (in Japanese).
[^mpm48]: Meyer-Peter, E. and Müller, R. (1948): Formulas for bed-load transport. *Proc. 2nd Meeting IAHSR*, Stockholm, 39–64.
[^exner25]: Exner, F. M. (1925): Über die Wechselwirkung zwischen Wasser und Geschiebe in Flüssen. *Sitzungsber. Akad. Wiss. Wien, Math.-Naturwiss. Kl.*, 134, 165–204.
[^itakura80]: Itakura, T. and Kishi, T. (1980): Open channel flow with suspended sediments. *J. Hydraul. Div. ASCE*, 106(HY8), 1325–1343. (implemented in the form of eqs. (3)–(5) of chapter 4 of the iRIC textbook "Practical river hydraulics")
[^rubey33]: Rubey, W. W. (1933): Settling velocities of gravel, sand, and silt particles. *Am. J. Sci.*, 25, 325–338.
[^partheniades65]: Partheniades, E. (1965): Erosion and deposition of cohesive soils. *J. Hydraul. Div. ASCE*, 91(HY1), 105–139.
[^trottet25]: Trottet, B., Noto, D., Jerolmack, D. J. and Ulloa, H. N. (2025): Sandball genesis from raindrops. *Proc. Natl. Acad. Sci. USA*, 122(52), e2519392122. (grain aggregates rolled by raindrops)
[^smith72]: Smith, T. R. and Bretherton, F. P. (1972): Stability and the conservation of mass in drainage basin evolution. *Water Resour. Res.*, 8, 1506–1529.
[^perron09]: Perron, J. T., Kirchner, J. W. and Dietrich, W. E. (2009): Formation of evenly spaced ridges and valleys. *Nature*, 460, 502–505.
[^heimsath97]: Heimsath, A. M., Dietrich, W. E., Nishiizumi, K. and Finkel, R. C. (1997): The soil production function and landscape equilibrium. *Nature*, 388, 358–361.
[^coulthard13]: Coulthard, T. J., Neal, J. C., Bates, P. D., Ramirez, J., de Almeida, G. A. M. and Hancock, G. R. (2013): Integrating the LISFLOOD-FP 2D hydrodynamic model with the CAESAR model: implications for modelling landscape evolution. *Earth Surf. Process. Landforms*, 38, 1897–1906.
[^white84]: White, W. B. (1984): Rate processes: chemical kinetics and karst landform development. In: La Fleur, R. G. (ed.) *Groundwater as a Geomorphic Agent*, Allen & Unwin, 227–248. (maximum denudation rate D = (P − E) c_eq/ρ)
[^gabrovsek09]: Gabrovšek, F. (2009): On concepts and methods for the estimation of dissolutional denudation rates in karst areas. *Geomorphology*, 106, 9–14.
[^howard83]: Howard, A. D. and Kerby, G. (1983): Channel changes in badlands. *Geol. Soc. Am. Bull.*, 94, 739–752. (Erosion rate of bedrock channels expressed by the bed shear stress during floods; checked against the abstract)
[^shobe17]: Shobe, C. M., Tucker, G. E. and Barnhart, K. R. (2017): The SPACE 1.0 model. *Geosci. Model Dev.*, 10, 4577–4604. doi:10.5194/gmd-10-4577-2017 (the exponential cover form checked in the Landlab source)
[^sklar04]: Sklar, L. S. and Dietrich, W. E. (2004): A mechanistic model for river incision into bedrock by saltating bed load. *Water Resour. Res.*, 40, W06301. doi:10.1029/2003WR002496
[^turowski07]: Turowski, J. M., Lague, D. and Hovius, N. (2007): Cover effect in bedrock abrasion. *J. Geophys. Res.*, 112, F04006. doi:10.1029/2006JF000697
[^zhang15]: Zhang, L., Parker, G., Stark, C. P., Inoue, T., Viparelli, E., Fu, X. and Izumi, N. (2015): Macro-roughness model of bedrock–alluvial river morphodynamics. *Earth Surf. Dynam.*, 3, 113–138. doi:10.5194/esurf-3-113-2015 (checked against the abstract)
