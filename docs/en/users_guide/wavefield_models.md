# Coastal wave field explained (supplement to the coastal wave field chapter)

> English mirror of docs/users_guide/wavefield_models.md. The Japanese file is the master copy.

[Back to the coastal wave field chapter](wavefield.md) | [Back to the user's guide index](../users_guide.md)

This page collects the governing equations behind the [coastal wave field chapter](wavefield.md),
its numerical methods, the formulations of its action on the flow and on sediment, the
empirical formulas of the swash zone, and the basis of the defaults. §12 shows separately the
other models and studies the implementation drew on and the theory and implementation original to
ENCflow. In the body as well, formulations and discretisations original to ENCflow are marked
**original** (a combination of existing techniques that is itself original is marked **original
combination**, and a simplification of an original formula **our own simplification**). Formulas
without a mark follow the forms of the literature and models in the footnotes.

The implementation is in `src/m_wavefield.f90` (the wave field, the action on the flow and the
change of waves by currents), `src/m_geomorph.f90`, `src/m_geomorph_fluvial.f90` and
`src/m_geomorph_suspend.f90` (stirring and transport), `src/m_geomorph_swash.f90` (swash-zone
transport) and `src/m_swflow_enc*.f90` (force, wave–current friction, lateral Neumann boundaries,
transport of suspended load). The history of the design and the comparison of alternatives are in
docs/wavefield_plan.md, and the exception to the policy (developer.md §0-5) and the record of
decisions, implementation and verification are in developer.md §90 (in Japanese). Development was
done in stages, so the record is written with the stage names (stage W1 = wave field, W2 = action
on the flow, W3 = change of waves by currents, W4 and W5 = action on sediment; swash-zone transport
is §90.21).

## 1. Position and overall structure

**Model class.** The model solves the balance of the energy (wave action when there is a current)
of each directional bin, phase-averaged with one representative period. It is a rough estimate of
the same class as the lineage HISWA[^hiswa] → the stationary mode of XBeach[^xbeach] →
SnapWave[^snapwave], without a frequency dimension, wind growth or nonlinear interactions. The aim
is not to compete in accuracy with these dedicated models, but to run an estimate of the same class
on the same grid and in the same time evolution as catchments, rivers, floods, tsunamis and
sediment. Why single-wave-train WKB, spectral models and phase-resolving models were not adopted is
in §12.1.

**Directions of action.** The wave field and the other processes exchange the following quantities
through the shared state. Every action is disabled by default, and when disabled no arrays or
computation are added.

| Action | Quantities exchanged | Section |
|---|---|---|
| waves → flow (`wf_flow`) | gradient of the radiation stress (waves + roller), Stokes transport, wave–current friction speed, eddy viscosity of breaking (`wf_break_visc`) | §6 |
| flow → waves (`f_wf_current`) | velocity of the shallow water flow (Doppler shift, refraction by currents, transport by currents) | §7 |
| waves → sediment (`f_wfsed`) | bottom orbital velocity, orbital amplitude, mean wave direction, onshore velocity u_a, Stokes transport (and near-bed turbulence) | §8 |
| swash zone (`f_wfswash`) | height and period of the incident waves, wave height near the shoreline | §9 |

**Position in the time loop.** The wave field is updated in every step after the tide and before
the shallow water flow, so the force and the friction use the wave field of the same step. The
quasi-steady mode (`wf_mode = 2`) computes the steady solution every `dt_wave` and holds the force,
the Stokes transport and the orbital velocity in between (the wave–current friction speed is
computed every step from the held orbital velocity and the velocity of that step). The unsteady mode
(`wf_mode = 1`) advances every step (§4.3).

## 2. Governing equations

### 2.1 Energy balance of the directional bins

For the energy density E_m [J/m²/rad] of each directional bin m (centre direction θ_m)
the model solves

```math
\frac{\partial E_m}{\partial t} + \nabla\cdot\left(c_g\,\hat{\mathbf e}_m E_m\right)
+ \frac{\partial (c_\theta E_m)}{\partial \theta}
= -\left(D_w + D_f\right)\frac{E_m}{E},
\qquad E = \sum_m E_m\,\Delta\theta
```

This is the conservation of wave action (Bretherton & Garrett 1968[^bg68]) reduced from the form of
SWAN[^swan] to a single frequency, the same form as HISWA and XBeach. Without a current the frequency
is constant, so the conservation of action and of energy are the same (with a current, the wave
action balance of §7.2). The dissipation on the right-hand side, $`D_w`$ (breaking) and $`D_f`$
(bottom friction), is the dissipation of the total energy distributed over the bins in proportion to
E_m/E (as in XBeach).

### 2.2 Dispersion relation, group velocity and refraction speed

The group velocity $`c_g`$ and the refraction speed $`c_\theta`$ follow from the dispersion
relation of linear theory.

```math
\sigma^2 = g\,k\tanh(kh),\qquad
c_g = \frac{\sigma}{2k}\left(1 + \frac{2kh}{\sinh 2kh}\right),\qquad
c_\theta = \frac{\sigma}{\sinh 2kh}\left(\sin\theta\,\frac{\partial h}{\partial x}
- \cos\theta\,\frac{\partial h}{\partial y}\right)
```

(σ = 2π/T, x east and y north.) As in SnapWave, $`c_\theta`$ is limited to |c_θ| ≤ σ/4, which
suppresses excessive refraction over steep topography. The depth gradients are central differences
along the axes, one-sided where a neighbour is not a wave cell. The dispersion relation is solved by
three Newton iterations starting from the explicit approximation of Fenton & McKee (1990)[^fm90].

### 2.3 Wave height, mean direction and orbital velocity

The wave height is H_rms = (8E/ρg)^{1/2} for random waves, written out as the significant wave height
H_m0 = √2 H_rms (Rayleigh distribution), and H = (8E/ρg)^{1/2} for regular waves (ρ = 1025 kg/m³).
The mean direction is atan2(Σ E_m sin θ_m, Σ E_m cos θ_m), and the bottom orbital velocity is
u_rms = H_rms σ/(2√2 sinh kh) (the XBeach definition).

### 2.4 Offshore waves and directional distribution

The energy of the offshore waves outside the incident sides is E_0 = ρgH_m0²/16 for
random waves and ρgH²/8 for regular waves. The directional distribution is
cos^s(θ − θ_0) (|θ − θ_0| < 90°); the exponent s is obtained from the directional
spreading σθ through the definition of Kuik et al. (1988)[^kuik88], σθ² = 2(1 − m_1),
and the distribution is normalised discretely over the bins (Σ D Δθ = 1; the same
distribution shape as SWAN). σθ = 0 is distributed linearly over the two bins that
bracket θ_0. The number of bins N_θ is restricted to multiples of 8, so the axis and
diagonal directions of x and y always lie on bin centres.

The representative period is used as is for σ = 2π/T in the dispersion relation. For random waves
the default interpretation is the energy period T_m−1,0; the guide for converting from the peak
period, T_m−1,0 ≈ T_p/1.1 (single-peaked spectrum), is from EurOtop (2018)[^eurotop].

## 3. Spatial transport (two-link upwind decomposition; original)

On the 8-neighbour ENC grid, the propagation velocity $`c_g\hat{\mathbf e}_m`$ of bin m
is **decomposed non-negatively into the two lattice directions (an axis and a diagonal)
that bracket it**, and each link carries energy upwind (the value of the sending cell).
With the grid-normalised p_x = c_g cos θ/Δx and p_y = c_g sin θ/Δy, if |p_x| ≥ |p_y| the
rate is |p_x| − |p_y| towards the x axis and |p_y| towards the diagonal (and vice versa).
This applies to the flux of wave energy the idea of D∞ (Tarboton 1997[^tarboton97]), which shares a
flow direction between two of the 8 neighbours by angle: an **original** discretisation. It is
written so that receivers gather from their senders, so the computation does not depend on the order
in which cells are processed.

- **Propagation along lattice directions (axes, diagonals) has no crosswind numerical
  diffusion.** The leading term of the modified equation of first-order upwind on a square grid with
  a uniform velocity (derived for ENCflow) is

  ```math
  D_\perp = \frac{c\,\Delta}{2}\,(\cos\varphi - \sin\varphi)\sin\varphi\cos\varphi
  ```

  (φ is the angle from the nearest axis, 0 ≤ φ ≤ 45°): zero at φ = 0° and 45°, with a maximum of
  0.096 cΔ at φ ≈ 21°. First-order upwind on ENC passage widths (finite volume) has 0.293 cΔ along an
  axis, and four-neighbour first-order upwind 0.354 cΔ at 45°.
- **The edges of shadows are smeared by this numerical diffusion.** In the steady solution of a
  half plane illuminated through a uniform medium and carried 100 cells, the width of the shadow edge
  (10–90%) was less than one cell along the axes and diagonals (practically sharp; aligned in
  test/wfshadow) and about 10–12 cells in the directions between them (the ENC finite volume combined
  with MUSCL gives 4.6–6.0 cells even along lattice directions). This is not real diffraction (waves
  bending into a shadow); this phase-averaged model does not treat diffraction. A higher-order
  correction that sharpens the edges in oblique directions (van Leer along the links) reached about
  3 cells in a prototype, but it is not adopted: in a model without diffraction, sharpening only the
  shadow edge would make shadows sharper than the smearing by real diffraction (the 10–90% width of
  the intensity of half-plane diffraction for a period of 8 s and a depth of 10 m is about 220 m at a
  distance of 1 km; first-order two-link decomposition gives 100–120 m in oblique directions with
  Δx = 10 m).
- The transport is conservative and the energy never becomes negative. The stability condition of
  the explicit update (outflow rate × Δt ≤ 1) is contained in the Courant condition of the shallow
  water flow, because the group velocity does not exceed the shallow-water wave speed √(gh) (substeps
  are used when it is exceeded).
- **A diagonal link is closed when the two cells beside it are both non-wave cells (such as land;
  original).** Waves do not slip through a one-cell-thick diagonal breakwater whose cells touch only
  at corners (the diamond enclosure of test/wfshadow). This rule deliberately differs from the ENC of
  the shallow water flow, which passes water through a one-cell-wide diagonal channel: being passable
  for water and being transparent to short waves are distinguished.

## 4. Refraction in directional space and time stepping

### 4.1 Refraction in directional space

In each cell, the advection ∂(c_θ E_m)/∂θ in θ is solved implicitly by first-order upwind (a periodic
tridiagonal system; an M-matrix, so non-negative), and a second-order correction with the van Leer
limiter[^vanleer74] is added from the previous values (deferred correction; at convergence of the
quasi-steady mode the balance of the limited second-order fluxes is satisfied). Implicit first-order
upwind and the limiter are both standard techniques; this way of combining them is an **original
combination**. First-order upwind alone delays refraction through numerical diffusion in directional
space, and the mix of central and upwind differencing (the CDD type of SWAN) produced negative energy
for a unidirectional incident wave and the quasi-steady iteration did not converge, so it is not
used.

The refraction error decreases in proportion to the bin width (first-order convergence). For waves
entering a beach of slope 1/80 with parallel depth contours at 30°, the deviation of the mean
direction from Snell's law down to 1 m depth was 1.5° with N_θ = 40 and 0.6° with N_θ = 80, and the
deviation of the wave height 0.5% and 0.3% (refr in test/wfshoal).

### 4.2 Source terms

The dissipation by breaking, bottom friction and the limit is solved semi-implicitly within the cell.
D/E is evaluated with the previous value and applied as an implicit decay
E_new = E*/(1 + Δt D/E*), so the energy never becomes negative, and the amount removed is recorded in
the ledger.

### 4.3 Quasi-steady and unsteady (one kernel, two modes)

One update is the pair of the spatial inflow and outflow (an explicit Jacobi-type update that makes
new values from the previous ones) and the refraction and sources within the cell (implicit). This
single kernel is run in two ways (**original combination**; Jacobi iteration and local time stepping
are both standard techniques).

- **Quasi-steady (`wf_mode = 2`)**: every `dt_wave`, the model iterates with a per-cell pseudo time
  step Δτ = 1/(maximum outflow rate) until the steady solution is reached (starting from the previous
  solution). The steady solution is set only by the balance of the inflow, outflow and sources and
  does not depend on Δτ. The convergence test (maximum change of wave height in one iteration /
  offshore wave height < `wf_tol`) is decided by the maximum over all ranks.
- **Unsteady (`wf_mode = 1`)**: advanced every step with the physical dt (with substeps if outflow
  rate × dt > 1). The wave front travels at the group velocity (unst in test/wfshoal). After a long
  enough time it reaches the same steady solution as the quasi-steady mode.

Neither depends on the order in which cells are updated, so the results are bit-identical regardless
of the number of MPI ranks and threads. The sweep solvers of SWAN and SnapWave (processing from the
upwind side in order to obtain the steady solution of a direction in one sweep) greatly reduce the
number of iterations, but their results depend on the processing order and bit-identical results
across rank counts would need dedicated parallel machinery, so they are not adopted (a performance
candidate if the need is shown by measurement).

### 4.4 Boundaries and wave cells

Each outer side is one of the following.

| Type | Value held by the virtual sender outside the grid | Use |
|---|---|---|
| 1 incident | Bin energy of the offshore waves | Offshore side |
| 2 lateral Neumann | Value of the cell inside the boundary | Left and right sides crossing the coast (the same sea continues outside; the same idea as the lateral boundaries of XBeach) |
| 0 absorbing | 0 | Sides with no sea outside, landward sides |

Each link has one sender, so energy is not injected twice at corners. Outgoing waves leave freely (no
reflection). For a virtual sender at a corner (outside the grid in both x and y), the type of side is
chosen with the priority incident > lateral Neumann > absorbing (**original**; the area outside the
corner of an incident side is regarded as offshore waves, which keeps the alongshore-uniform solution
of a straight coast intact).

A **wave cell** is a cell inside the domain (x > 0) that is neither a sea-mask cell (sw)
nor an absorbing cell and whose depth exceeds `wf_hmin`. Waves heading towards land,
dry cells, sea cells or absorbing cells are absorbed (no reflection; "absorbed" in the
ledger). Sea cells are boundary cells that carry the tide level and are not solved by the shallow
water flow either, so they are also excluded from the wave domain (the offshore is represented as a
"solved sea"). **Cells with a building porosity gv < 1** and **sub-grid channel width /
cross-section cells** are made explicit absorbing cells, because their relation to waves is not
represented in this version, and their number is printed at the start (an unsupported combination is
not computed silently).

## 5. Breaking, bottom friction and the limit

Breaking of **random waves** follows, by default, Baldock et al. (1998)[^baldock98]

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
excess is counted as "limit" in the ledger). The forms follow the XBeach manual and were checked
against the original forms. The Baldock formula in the public source of SnapWave has the
coefficient 0.28 and H_b = γh, unlike XBeach; this implementation follows the XBeach form.

**Regular waves** (`wf_wavetype = 2`) have only the saturation H ≤ γh (saturated
breaking) and no probabilistic breaking. They are for verification against theoretical
solutions.

**Bottom friction** is D_f = c ρ f_w u_orb³ with u_orb = πH_rms/(T sinh kh) (H for regular
waves) and c = 0.28 (random) or 0.21 (regular) (coefficients of the third velocity
moment of Guza & Thornton 1985[^gt85]; the XBeach formulation). The default is
f_w = 0 (no friction; the default of the XBeach stationary mode).

## 6. Action on the flow (wf_flow)

### 6.1 Radiation stress and force

From the energy of the directional bins, the radiation stress (Longuet-Higgins & Stewart 1964[^lhs64])

```math
S_{xx} = n\sum_m E_m\cos^2\theta_m\,\Delta\theta + \left(n - \tfrac12\right)E + E_r\cos^2\bar\theta,\qquad
S_{xy} = n\sum_m E_m\cos\theta_m\sin\theta_m\,\Delta\theta + E_r\cos\bar\theta\sin\bar\theta
```

(S_yy likewise; n = c_g/c, θ̄ is the mean wave direction, E_r the roller energy) is formed, and the
wave force $`F_i = -\partial S_{ij}/\partial x_j`$ is differenced at the cell centres (central
differences when both neighbours are wave cells, one-sided when one is). For waves arriving normal to
the coast the mean water level falls offshore of the surf zone (set-down) and rises in the surf zone
(set-up; Longuet-Higgins & Stewart 1962[^lhs64], Bowen et al. 1968[^bowen68]). For oblique waves, the
decrease of S_xy by breaking becomes the alongshore force that drives the longshore current.

**Projection onto the faces (original).** On each face of the shallow water flow, the mean of the
forces of the two cells is projected onto the direction of the face and $`F_k/(\rho h)`$ is added as
an acceleration, with h the mean depth of the two cells. In a one-dimensional setup that varies only
in x, axis faces and diagonal faces obey the same balance equation (the diagonal only multiplies both
sides by the same direction cosine), so no false circulation arises between faces. With the upwind
depth of the face used by the friction (which switches with the direction of the velocity), the force
switched every time the sign of the velocity flickered in a balance close to rest, a different drive
remained in each row and a circulation grew slowly; the mean depth, which does not depend on the sign,
is therefore used.

### 6.2 Roller

The energy of breaking waves is first transferred to the surface vortex on the wave
front (the roller) and then dissipated. The roller energy E_r (J/m²) is carried with the
mean wave direction at the phase speed c (= σ/k), and

```math
\frac{\partial E_r}{\partial t} + \nabla\cdot\left(c\,\hat{\mathbf e}_{\bar\theta}E_r\right) = D_b - D_r,\qquad
D_r = \frac{2\beta g E_r}{c}
```

is solved (Svendsen 1984[^svendsen84], Reniers & Battjes 1997[^rb97]; D_b is the breaking
dissipation and the part removed by the limit). The radiation stress of the roller,
E_r cos²θ̄ and so on, is the approximation of Nairn et al. (1990)[^nairn90], the same form
as XBeach. Because the roller stores the momentum of breaking for a while and releases it further
shoreward, the maxima of the force, the setup and the longshore current move shoreward (the delay
with which the current builds up just after the breaker point). The spatial transport is the two-link
upwind scheme along the mean wave direction (§3) and the dissipation is semi-implicit; the
quasi-steady mode solves the steady state and the unsteady mode advances with the same time step.

### 6.3 GLM and wave–current bed friction (wf_flow = 2)

The velocity of the shallow water flow is read as the **Lagrangian mean velocity u^L**
(the mean distance a water particle travels in a wave period; it represents mass
transport), and the bed friction acts on the **Eulerian velocity** u^E = u^L − u^S
(depth-averaged GLM; Andrews & McIntyre 1978[^am78], Walstra et al. 2000[^walstra00]; the
same as XBeach). The Stokes transport velocity is

```math
\mathbf u^S = \frac{\sum_m E_m\hat{\mathbf e}_m\,\Delta\theta + 2E_r\,\hat{\mathbf e}_{\bar\theta}}{\rho h c}
```

(the second term on the right is the mass transport of the roller 2E_r/c; Svendsen 1984).
On a closed beach the net cross-shore flux becomes 0 (u^L ≈ 0) and the Eulerian velocity
u^E = −u^S represents the **return flow** (the offshore-directed flow near the bed). The
friction speed includes the wave orbital velocity,

```math
\tau_b = \rho\,\frac{g n_m^2}{h^{1/3}}\,\sqrt{|\mathbf u^E|^2 + (1.16\,u_{rms})^2}\;\mathbf u^E
```

(Ruessink et al. 2001[^ruessink01]; n_m is the Manning roughness), so that in the surf
zone the orbital velocity strongly increases the friction. Only the friction speed of the Manning law
is replaced; the drag of buildings and the yield term of debris flow keep the flow speed (the
velocity they act on is the Eulerian velocity in every case).

### 6.4 Horizontal mixing by wave breaking (wf_break_visc of list_enc)

Breaking turbulence also mixes momentum laterally and smooths the cross-shore distribution of the
longshore current. With `wf_break_visc` = M > 0, the wave field computes at every update the eddy
viscosity

```math
\nu_w = M\,h\left(\frac{D}{\rho}\right)^{1/3}
```

(Battjes 1975[^battjes75]; D is the roller dissipation D_r with the roller and the breaking
dissipation D_w without it, ρ = 1025 kg/m³) and adds it to ν of the [diffusion term](diffusion.md)
(the diffusion term is computed even with `f_diffusion_term = 0`). The formula has the same form as
nuhfac of XBeach, whose default is M = 1[^xbeach] (the original paper of Battjes 1975 has not been
checked). How XBeach combines it with the background viscosity has not been checked, so this
implementation takes the sum (ν = ν_model + ν_b + ν_w), like the breaking eddy viscosity of the
non-hydrostatic correction `nh_break_visc` (**original combination**). In the quasi-steady mode ν_w is
held between updates of the wave field. On the beach of test/wfcurrent, ν_w peaks at 0.54 m²/s in the
surf zone, the peak of the longshore current drops by 3.3% and the spread of its distribution grows by
3.8%.

### 6.5 Ramp-up of the force

The quasi-steady wave field is at full strength over the whole domain at the start, so the suddenly
applied force excites an oscillation near the shoreline (a seiche). The force and the Stokes transport
are multiplied by a factor that grows linearly from the origin t0 of the time axis,
r = min(1, (t − t0)/`wf_tramp`) (the same idea as the taper of XBeach). On a beach of slope 1/80,
without the ramp the shoreline velocity reached 0.2 m/s two minutes after the start, and with a ramp
of 600 s it was 0.03 m/s.

### 6.6 Lateral Neumann boundaries (f_bc = 3; original)

A lateral Neumann side for longshore currents (the same coast and flow continue outside = zero normal
gradient) solves the momentum equation of a boundary face with the same formula as an interior face,
taking the partner outside the grid as the cell moved into the grid along the normal of the side (the
mirror cell; **original**). So that the boundary rows have the same solution as the interior rows for
an alongshore-uniform flow, the following are aligned with the interior faces.

- **Wetting and limiting**: the face is closed only when both sides are dry, and the decision of the
  adaptive Runge–Kutta scheme and the limiting of excessive outflow are the same as for interior faces
  (for inflow the mirror cell is the sender).
- **Reassignment of the passage width of blocked openings**: the outside is judged with the mirror
  cell, and the coefficients of the boundary face are copied from the face one cell inward (treating
  the outside as a wall would add the diagonal share of the passage width only to the axis faces of the
  boundary rows).
- **Advection term**: the control volume of the boundary face is computed with the same formula as an
  interior face, reading positions outside the grid from the mirror cells. The inflow face of a flow
  entering from outside contributes 0, so advection does not accelerate the flow entering through the
  side. In an alongshore-uniform field it is identical in form to the control volume of the face one
  cell inward shifted alongshore.
- **Diffusion term**: the diffusion of cells touching the side is computed with the neighbours outside
  replaced by mirror cells, and the boundary face adds the mean of the diffusion of its own cell and of
  the mirror cell.
- **Sediment**: suspended load and other scalars flow in with the concentration of the mirror cell
  (the MUSCL reconstruction also reads the mirror values outside the grid), and bed load takes the flux
  of the face one cell inward along the side normal.

For the longshore current on the beach of test/wfcurrent, all rows including the boundary rows agree
to about 0.03% of the maximum velocity. Among the forms not adopted, copying the velocity and flux of a
boundary face from the face one cell inward diverged through a positive feedback between the water
level and the flux of the boundary rows. Copying the advection term of a boundary face from the face
one cell inward (the first version) could let the inflow keep strengthening at the inflow side of a
flow that is non-uniform alongshore, so it was replaced by the control volume above (developer.md
§90.16 and §90.19).

## 7. Change of waves by currents (f_wf_current)

### 7.1 Doppler shift and blocking

The dispersion relation of waves on a current $`\mathbf U`$ is, with the current component
$`U_m = \mathbf U\cdot\hat{\mathbf e}_m`$ along the direction $`\hat{\mathbf e}_m`$ of
directional bin m,

```math
(\omega - k U_m)^2 = g k \tanh kh
```

(Bretherton & Garrett 1968[^bg68]). ω is the angular frequency of the offshore waves; on a steady
current it does not change, by the conservation of wave crests. For each cell and bin this relation is
solved on the branch that is continuous as U_m → 0, giving the intrinsic angular frequency
$`\sigma_m = \omega - k_m U_m`$ and the intrinsic group velocity c_g,m = n σ_m/k_m. It is solved by
Newton's method from the root without a current; σ_0(k) + kU_m − ω is concave, so the iteration
approaches the root monotonically without overshooting it. On an opposing current (U_m < 0) k_m is
larger and σ_m > ω; on a following current the reverse. When the opposing current is so strong that
the group velocity and the current cancel (c_g,m + U_m ≤ 0) or the root disappears, the waves of that
bin are **blocked**: the wave action that arrives there is recorded as blocked in the ledger and
removed.

XBeach advances the wavenumber in time with the eikonal equations, which on a steady current give the
same root. With a single representative frequency, the absolute angular frequency ω is constant on a
steady current, so fixing ω and solving the wavenumber of each directional bin directly is consistent
(**original**). The change of ω by a current that varies in time is not included (**our own
simplification**).

### 7.2 Wave action balance

On a current the wave energy is not conserved, but the **wave action N = E/σ** is (Bretherton &
Garrett 1968).

```math
\frac{\partial N_m}{\partial t} + \nabla\cdot\left[(c_{g,m}\hat{\mathbf e}_m + \mathbf U)N_m\right]
+ \frac{\partial (c_\theta N_m)}{\partial\theta} = -\frac{D_m}{\sigma_m}
```

The spatial transport carries the velocity $`c_{g,m}\hat{\mathbf e}_m + \mathbf U`$, decomposed for
each cell and bin, with the same two-link upwind scheme as §3 (the decomposition differs from sender
to sender, so a receiver examines the senders among its 8 neighbours and gathers from them). A term
due to the gradient of the current speed is added to the refraction speed in direction space (x east,
y north; the same form as SWAN[^swan] and XBeach[^xbeach]; the gradients follow the same rules as
§2.2).

```math
c_\theta = \frac{\sigma}{\sinh 2kh}\left(\frac{\partial h}{\partial x}\sin\theta - \frac{\partial h}{\partial y}\cos\theta\right)
+ \cos\theta\left(\sin\theta\frac{\partial u}{\partial x} - \cos\theta\frac{\partial u}{\partial y}\right)
+ \sin\theta\left(\sin\theta\frac{\partial v}{\partial x} - \cos\theta\frac{\partial v}{\partial y}\right)
```

Breaking, bottom friction and the limit are evaluated with the same formulas as §5, using the
energy $`E_m = \sigma_m N_m`$ and the energy-weighted mean wavenumber and intrinsic angular
frequency. Wave action is conserved even in a current that changes in time (an adiabatic
invariant), so the state of the computation is held as wave action and carried over unchanged
when the current changes (the unsteady ledger also closes while the current changes in time). The
ledger amounts are wave action × ω.

The velocity used is the velocity of the shallow water flow itself (with `wf_flow = 2` the Lagrangian
mean velocity u^L; the same as wci of XBeach[^xbeach]). The roller is also carried by the current
(velocity c ê + U, c = σ̄/k̄), and the radiation stress and the Stokes transport use the intrinsic
n_m and c_m of each bin.

### 7.3 Mechanism of the grid-scale stripes offshore

The refraction speed by currents takes the current gradients by central differences, so its response
is largest for current stripes four cells long. Combined with the wave-driven flow (`wf_flow = 2`),
stripes in the current refract the waves, stripes in the wave height make stripes in the force, and
those strengthen the current stripes: by this positive feedback, oblique stripes three to four cells
long can grow with time in the quiet water offshore (they grow even without bed change). The wave
action balance is an equation for a medium (depth and current) that varies slowly compared with the
wavelength (WKB), and letting current variations at the grid scale (about 17 m in examples/delta),
shorter than the wavelength (about 27 m for a depth of 2 m and a period of 6 s), act on the waves is
outside that premise.

The countermeasure chosen is a setting that adds background viscosity ("Grid-scale stripes offshore
and background viscosity" in the chapter). In the configuration of wfsed of examples/delta (made a
fixed bed to isolate the cause), the stripes did not grow with a background viscosity
ν0 = 0.05 m²/s, the mean velocity within 3 cells of the shoreline did not change, and the maximum of
the river-mouth jet changed by −1% (−6% with 0.2 m²/s). A structural countermeasure that removes
scales shorter than the wavelength from the current passed to the waves stopped the stripes in a
prototype, but it is not adopted, because the setting already stops them and the choice of the
smoothing width would need discussion (developer.md §90.20).

### 7.4 Cost and convergence

With a current, the dispersion relation and the decomposition of the transport are recomputed for
each cell and bin at every update, and quantities per bin (wavenumber, intrinsic angular frequency,
outflow rates and their targets, refraction speed) are held (the memory is given in "Cost and
convergence" of the chapter). Near blocking, wave action moves slowly in the bins where the group
velocity and the current cancel, and in an alongshore-uniform field the component that circulates
through the lateral Neumann sides is hardly damped, so the quasi-steady iteration converges slowly. A
per-bin pseudo time step (speeding up the slow bins) oscillated in combination with the nonlinear
breaking evaluated with the previous values and did not converge, so it is not adopted.

## 8. Action on sediment (f_wfsed)

### 8.1 Stirring (wave–current bed shear stress)

From the amplitude of the orbital velocity at the bed u_w = √2 u_rms (the representative amplitude of
random waves of Soulsby; u_rms is the output Wu) and the orbital amplitude A = u_w/σ̄ (σ̄ is the
intrinsic angular frequency), the wave bed shear stress and its combination with the current shear
stress are computed with the formulas of Soulsby (1997)[^soulsby97].

```math
\tau_w = \tfrac12 \rho f_w u_w^2,\quad f_w = \min\left(1.39\,(A/z_0)^{-0.52},\ 0.3\right),\quad z_0 = d_{50}/12
```

```math
\tau_m = \tau_c\left[1 + 1.2\left(\frac{\tau_w}{\tau_c + \tau_w}\right)^{3.2}\right],\quad
\tau_{max} = \sqrt{(\tau_m + \tau_w|\cos\varphi|)^2 + (\tau_w\sin\varphi)^2}
```

τ_c is the shear stress of the current alone (the existing Manning closure
τ* = n² V²/(s d h^{1/3}), with V the speed of the Eulerian mean velocity u^E of §8.3), φ the angle
between the current and the mean wave direction, and τ_max the maximum shear stress within the wave
period. τ*_max is used as the dimensionless shear stress of the bed load formula (`f_qbform`) and of
the equilibrium concentration of suspended load (`f_esform`), including the threshold (following
Soulsby's recommendation of τ_max for the threshold and for pick-up). z0 is the grain roughness
(z0 = k_s/30 with k_s = 2.5 d50), and the upper limit 0.3 is the value of Swart (1974)[^swart74] for
small A. Without waves τ*_max = τ*_c, the same formula as with `f_wfsed = 0`.

### 8.2 Stirring by the turbulence of wave breaking (f_wfsed_turb)

Near the shoreline, where breaking turbulence reaches the bed, turbulence picks up sand besides the
orbital motion. The surface turbulence k_s = (D_r/ρ)^{2/3} produced by the roller dissipation D_r
(Battjes 1975[^battjes75]) decays exponentially towards the bed over the roller thickness
L_mix = √(2E_r T/(ρc)) (Svendsen 1984[^svendsen84]; T is the representative period;
Roelvink & Stive 1989[^rs89]),

```math
k_b = \frac{k_s}{\exp(h/L_{mix}) - 1},\qquad u_{rms,2} = \sqrt{u_{rms}^2 + 1.45\,k_b}
```

and u_w of §8.1 becomes √2 u_rms,2 (van Thiel de Vries 2009[^vtdv09]; the same form as `turb` =
wave_averaged of XBeach[^xbeach]). Without the roller (`f_wf_roller = 0`), k_s = (D_w/ρ)^{2/3} and
L_mix = H_rms. The orbital amplitude A, the onshore velocity u_a and the wave–current bed friction
keep u_rms without turbulence (as in XBeach); only adding it to u_w is **our own simplification**
(XBeach adds it to the velocity of the equilibrium concentration formula). The turbulence acts near
the shoreline, where the roller is thick compared with the depth (on the beach of test/wfsed the
stirring speed is 1.10 times larger in the shoreline cell and 1.01 times at the peak of breaking
dissipation, and the longshore transport increases by 1.9%).

### 8.3 Transport velocity (Eulerian mean velocity and onshore velocity)

The velocity that carries the sand is u_s = u^E + u_a ê_θ (ê_θ is the unit vector of the mean
wave direction).

- **Eulerian mean velocity u^E = u^L − u^S**: with `wf_flow = 2` the shallow water velocity is
  the Lagrangian mean u^L (the mass transport of water), and the Stokes transport u^S is
  concentrated above the wave troughs. Suspended sediment is concentrated near the bed, so the
  sand moves with the Eulerian mean velocity without the Stokes transport (Reniers et al.
  2004[^reniers04]; the same as XBeach[^xbeach]). In the surf zone u^E is the offshore undertow,
  which carries sand offshore. Dissolved substances (water quality, salt water) are uniform over the
  depth, so they keep u^L.
- **Onshore velocity u_a**: in shallow water the crests of the waves become peaked (skewness
  S_k) and the waves lean forward (asymmetry A_s), so the onshore orbital velocity is stronger
  and the net sand transport is onshore. As in XBeach, u_a = (f_Sk S_k − f_As A_s) u_rms of van
  Thiel de Vries (2009)[^vtdv09] is used, with S_k and A_s from the parameterization of
  Ruessink et al. (2012)[^ruessink12] by the Ursell number Ur = (3/8)√2 H_rms k/(kh)³
  (S_k = B cos ψ, A_s = B sin ψ, B = p₂/(1 + exp((p₃ − log₁₀ Ur)/p₄)), ψ = −90° + 90° tanh(p₅/Ur^{p₆})).
  f_Sk and f_As (`wfsed_facsk`, `wfsed_facas`) are calibration coefficients; the default 0.1 is the
  default of XBeach (facua).

**Check against Ruessink et al. (2012).** The forms of the formulas (Eqs. (6)–(10) of the paper) and
the definition of the Ursell number (a_w = 0.5√2 H_rms, k the linear-theory wavenumber for the period
T = T_m−1,0, the same as the default interpretation of the representative period in this model) agree
with the paper. The coefficients are the same values as XBeach, p₂ = 0.7939, p₃ = −0.6065,
p₄ = 0.3539, p₅ = 0.6373 and p₆ = 0.5995 (public XBeach source morphevolution.F90), which differ from
the best-fit values of the paper, p₂ = 0.857 ± 0.016, p₃ = −0.471 ± 0.025, p₄ = 0.297 ± 0.021,
p₅ = 0.815 ± 0.055 and p₆ = 0.672 ± 0.073 (p₁ = 0; ± is the 95% confidence interval), all lying
outside the confidence intervals. The equation numbers and error ranges noted in the XBeach source
do not match the published paper either, and the source of the XBeach values has not been
identified. With the values of the paper, u_a becomes 0.6–0.8 times as large for Ur ≈ 0.1–0.3
(offshore of the surf zone), about the same for Ur ≈ 1, and about 1.1 times for Ur ≈ 2–20 (surf
zone) (with f_Sk = f_As).

The parameterization of the paper was fitted to field observations of mostly directionally spread
waves (H_s 0.05–3.99 m, T 3.1–13.9 s, depth 0.25–11.2 m, Ur 0.004–24.8, bed slopes generally milder
than 1/30, no swash zone); it may underestimate the skewness for swell that is narrow in direction and
for unidirectional laboratory waves, and its use on beds steeper than 1/30 is not advised.

**Beach erosion and recovery** are decided by the balance between the offshore undertow u^E and
the onshore u_a. With high waves the undertow wins and sand is carried offshore (a bar forms);
with low waves and long-period swell u_a wins offshore of the surf zone and sand returns onshore
(storm and calm of test/wfsed).

### 8.4 Form of the suspended and bed load transport

Suspended load is carried with the shallow water face fluxes minus h(u^S − u_a ê_θ) (the mean of the
two cells; it moves with a velocity different from the water). Faces with zero water flux (walls,
closed openings, levees) get no subtraction either (sediment alone does not pass through a wall). Bed
load

```math
q_b = q^*(\tau^*_{max})\sqrt{\tau^*_s/\tau^*_{max}}\,\sqrt{s g d^3}
```

is carried in the direction of u_s (τ*_s is the Manning shear stress of the speed of u_s). It
carries the bed load amount that a current with τ*_max would carry at the speed of u_s: without
waves it agrees with the existing formula, with waves and no current it moves in the direction
of u_a, and when the waves are stronger than the current the transport is proportional to the
speed of u_s (the same idea as "equilibrium concentration × transport velocity" of XBeach). This is
an **original combination**, so it was compared with the wave–current bed load formula of Soulsby
(1997): under the bed load conditions of test/wfsed (depth 2.2 m, current 0.45 m/s, H_m0 0.5 m,
T 6 s, φ = 30°) the dimensionless transport of the model is Φ = 0.92 against 0.98 from Soulsby's
formula (0.41 from MPM with the current alone).

### 8.5 Comparison with CERC

The longshore transport rate (the cross-shore integral of Qby and Qsy) on the straight coast of
test/wfsed (H_m0 = 1 m, T = 8 s, 20°) is about 1.6 times CERC (Komar & Inman 1970[^ki70]) computed from
the waves at the breaker point of the model — the same order (both the CERC coefficient and the
coefficients of the process-based transport are calibrated quantities). A path that inserts the local
waves into the CERC formula is not offered as an option, because it risks counting the same transport
twice with the process-based transport (simple longshore transport without solving the waves is
fn_wave).

## 9. Swash-zone transport (f_wfswash)

The phase-averaged wave field stops before the shoreline (wave cells have a depth of at least
`wf_hmin`) and has no swash flow, so the transport of §8 has no process that piles up the sand of the
shallows above the shoreline (to the height the swash reaches). Empirical formulas for the net
transport integrated over one swash cycle are given on the shoreline faces (between a wet cell and a
dry cell on higher ground). The formulas were checked against the original papers.

### 9.1 Cross-shore (Larson et al. 2004)

On a frictionless ballistic swash (initial swash velocity u_s, runup height R = u_s²/2g), a bed load
transport proportional to the cube of the velocity with an up/down asymmetry on the slope (Madsen's
formula) is integrated over one swash cycle to give the net transport (Larson, Kubota & Erikson
2004[^larson04], Eq. (8); positive offshore; bulk volume per unit width):

```math
q_c = K_c\, 2\sqrt{2g}\, R^{3/2}\left(1 - \frac{z}{R}\right)^2 \frac{\tan\phi_m}{\tan^2\phi_m - \tan^2\beta}\,(\tan\beta - \tan\beta_e)
```

z is the height above the still water level, tanβ the foreshore slope, tanβ_e the equilibrium
slope and φ_m the friction angle of a moving grain. The transport is onshore if the foreshore is
milder than equilibrium, offshore if steeper, and zero at the equilibrium slope. The default
K_c = 1.6×10⁻³ is the mean of the values Larson et al. calibrated on four field experiments at
Hasaki Beach (fine sand, 0.18 mm) (a representative value for fine sand; 1.0–2.3×10⁻³ in the
individual runs). The formula assumes a mild foreshore and a swash period similar to the
incident wave period (Iribarren number ξ0 ≳ 1).

### 9.2 Longshore (Larson & Wamsley 2007)

The swash of obliquely incident waves has an initial longshore velocity v_s = u_s tanθ (θ = angle
between the shoreline normal and the wave direction), and

```math
q_l = K_l \frac{\tan\phi_m}{\tan^2\phi_m - \tan^2\beta}\,\frac{u_o^2 v_o}{g}\,\frac{t_o}{T},\qquad
u_o = u_s\sqrt{1 - z/R},\quad \frac{t_o}{T} = \sqrt{1 - z/R},\quad v_o = v_s
```

(Larson & Wamsley 2007[^lw07], Eqs. (4), (6) and (7)) integrated over the swash width R/tanβ is
carried along the shoreline. The default K_l equals K_c (the assumption of Larson & Wamsley, shown to
agree with the longshore transport in the swash of movable-bed experiments in the large basin LSTF
(Wang et al. 2002[^wang02])). There is no longshore transport if the mean wave direction is 80° or more from
the shoreline normal.

### 9.3 Runup height and exposure

Of the 2% exceedance runup of Eq. (19) of Stockdon et al. (2006)[^stockdon06],
R2 = 1.1 (⟨η⟩ + S/2) with S = √(H0 L0 (0.563 β² + 0.004)), the setup ⟨η⟩ is resolved by the flow and
included in the water level of the shoreline cell, so the swash part R = 1.1 S/2 is measured from that
level. H0 is the incident wave height at the offshore boundary (not back-computed to deep water),
L0 = gT²/2π (T is the representative period `wf_trep` or the period column of `wf_val`) and β the
foreshore slope of the shoreline cell.

On shorelines that waves hardly reach, such as the lee of a delta or inside a channel, H0 is
multiplied by the largest ratio, over the wave cells within ±2 cells of the shoreline cell, of the
wave height to the saturated height min(H_inc, γ_s h) (γ_s = √2 `wf_gammax` for random waves,
`wf_gamma` for regular waves; exposure E, capped at 1; **original**). On an open beach the wave
height at the shoreline is saturated by the depth and E = 1. Without wave cells nearby there is no
swash.

Larson et al. calibrated K_c with R from the formulas of Mayer & Kriebel (1994)[^mk94] and Hunt (1959)[^hunt59]
(significant wave height); combining it with the swash of Stockdon et al. is an **original
combination** (the meaning of the K_c value can shift by the difference in the definition of R).

### 9.4 Mapping to the grid (original)

The following rules, which map the empirical formulas onto the ENCflow grid, are all **original**.

- A shoreline cell is a wet cell with a dry cell on higher ground among its four neighbours
  (east, west, north, south). The cross-shore flux is given on each of those four-neighbour faces
  as the projection of the offshore-directed vector q_c on the face direction times the side
  length of the cell, with the mean G of the gradients (central differences) of the two cells of
  the face as the foreshore slope (tanβ = |G|). The boundary between the wet and dry regions is a
  staircase of four-neighbour faces, so on a planar beach the transport per unit length is q_c
  whatever the shoreline orientation (checked for a 45° shoreline by diag of test/wfswash; with
  the diagonal faces as well, a 45° shoreline on a coarse grid would get 1/√2).
- z is the height of the ground of the dry cell above the water level of the shoreline cell; for
  z ≥ R there is no flux = deposits do not exceed the runup limit η + R. As an exception to the
  rules of bed load (sediment does not climb above the water surface; a dry cell gives no
  sediment), sand deposits on and is cut from the dry cell. The deposit of one face in one bed
  update is reduced to the margin up to the runup limit and to `fluv_dzmax` (at the flux stage,
  so conservation holds).
- The longshore flux is placed in a band one cell wide along the shoreline cells; the width of the
  band is set from the shoreline orientation so that the total through the band equals the total
  longshore swash transport, and it is passed to the 8-direction faces with the same projection as the
  longshore transport of fn_wave (CERC type). Because the swash zone straddles the shoreline, faces to
  dry cells at heights the swash reaches are also passed. A shoreline cell without a dry neighbour
  (among its four neighbours) at a height the swash reaches (in front of a cliff or seawall higher than
  the runup) has no swash zone, so no longshore flux is placed there either (placed there, the band
  would become a conveyor belt that carries sand far along the cliff; cliff of test/wfswash).
- The width factors of water paths (width of sub-grid channels, reassignment of blocked
  openings) are not applied (the swash fluxes are set by the shoreline length and the band width,
  not by the face widths).

## 10. Parameters and the basis of their defaults

The labels in the Basis column are explained in [How to read the basis of a default](../users_guide.md#how-to-read-the-basis-of-a-default).

| Parameter | Default | Meaning | Basis |
|---|---|---|---|
| `wf_gamma` | 0.78 | breaker index γ | **Literature value**: default of the XBeach stationary mode[^xbeach] (a customary value that derives from the breaking limit of a solitary wave) |
| `wf_alpha` | 1.0 | dissipation coefficient α of breaking | **Literature value**: default of the XBeach stationary mode[^xbeach] |
| `wf_gammax` | 0.6 | depth limit H_rms ≤ γmax h | **Literature value**: default of the XBeach stationary mode[^xbeach] (limit of H_rms relative to depth). SnapWave[^snapwave] has a limit of the same form and value |
| `wf_break` | 1 | breaking formula (1: Baldock et al. / 2: Janssen & Battjes) | **Method**: Baldock et al. (1998), the same as the default of the XBeach stationary mode. On steep beaches Janssen & Battjes (2007) corrects the overestimated dissipation |
| `wf_fw` | 0 | bottom friction factor f_w | **Calibration**: the default 0 (no friction) is the XBeach default[^xbeach]. On reefs and similar beds it can be more than an order of magnitude larger than the friction coefficient of the flow (XBeach manual) |
| Friction coefficient c | 0.28, 0.21 | coefficient of the bottom friction dissipation (random, regular waves) | **Literature value**: velocity moments of Guza & Thornton (1985)[^gt85] (the XBeach formulation). Not a setting |
| `wf_hmin` | 0.1 m | minimum depth of a wave cell | **Numerical**: default of SnapWave[^snapwave] |
| `wf_mode` | 2 | 1: unsteady / 2: quasi-steady | **Method**: the default is set for use with morphology (conditions change more slowly than the wave travel time) |
| `dt_wave` | 3600 s | update interval of the quasi-steady mode | **Numerical**: default update interval of SnapWave[^snapwave] |
| `wf_ntheta` | 40 (9°) | number of directional bins | **Numerical**: a multiple of 8 close to the 10° default of XBeach and SnapWave. The refraction error is as measured in §4.1 (proportional to the bin width) |
| `wf_tol` | 1e-4 | convergence criterion of the quasi-steady mode | **Numerical**: original (relative change of wave height; in the verification the difference of solutions was checked with 1e-6 to 1e-8) |
| `wf_spread` | 20° | directional spreading σθ | **Empirical**: a guideline of this project (original). A value placed between the typical spreading of wind sea and swell; if wave observations exist for the site, give their directional spreading |
| ρ | 1025 kg/m³ | density of sea water | **Customary value**: density of sea water (the XBeach default). Not a setting |
| `wf_flow` | 0 | action on the flow (0 none / 1 force / 2 force + GLM + wave–current friction) | **Method**: by default the flow is not acted on (writing the wave field leaves the flow unchanged). When used, 2 is recommended (the same GLM and wave–current friction as XBeach) |
| `f_wf_roller` | 1 | solve the energy balance of the roller | **Method**: the XBeach default[^xbeach] (roller = 1). Its effect of moving the maximum of the force shoreward agrees with observations (Reniers & Battjes 1997[^rb97]) |
| `wf_beta` | 0.1 | dissipation coefficient β of the roller | **Literature value**: the XBeach default[^xbeach] (range 0.05–0.3); the 0.1 of Reniers & Battjes (1997)[^rb97] |
| `wf_tramp` | 100 s | ramp-up time of the force | **Numerical**: the default of XBeach's taper[^xbeach] (the start-up in the same situation, where a steady wave field is applied to the whole domain at once) |
| Coefficient of the friction speed | 1.16 | coefficient of u_rms in the wave–current friction speed | **Literature value**: the wave–current friction of Ruessink et al. (2001)[^ruessink01] (the XBeach formulation). Not a setting |
| `wf_break_visc` (&list_enc) | 0 | coefficient M of the breaking eddy viscosity | **Calibration**: the default 0 (no mixing). M = 1 is the default of nuhfac of XBeach[^xbeach]. The formula is from Battjes 1975[^battjes75] |
| `f_wf_current` | 0 | action of the current on the waves | **Method**: by default the current does not act. The formulation is the wave action balance of Bretherton & Garrett (1968)[^bg68]; the refraction by currents and the velocity used (Lagrangian mean) are the same as wci of XBeach[^xbeach]. Solving the dispersion relation directly for each directional bin is original (XBeach advances the wavenumber in time with the eikonal equations) |
| `f_wfsed` (&list_geomorph) | 0 | stirring and transport by the wave field | **Method**: by default there is no action on sediment. The stirring is the wave–current shear stress combination of Soulsby (1997)[^soulsby97] (the upper limit 0.3 of f_w from Swart 1974[^swart74]); carrying suspended load with the Eulerian mean velocity is the same as Reniers et al. (2004)[^reniers04] and XBeach[^xbeach]. The combination for bed load, "the amount of τ*_max times the speed of u_s", is original (§8.4) |
| `wfsed_facsk`, `wfsed_facas` (&list_geomorph) | 0.1 | skewness and asymmetry coefficients f_Sk, f_As of the onshore velocity | **Calibration**: the default is facua of XBeach[^xbeach]. The formula is van Thiel de Vries (2009)[^vtdv09], with S_k and A_s from the parameterization of Ruessink et al. (2012)[^ruessink12] (the coefficients p₂ to p₆ are the values of the public XBeach source, which differ from the values of Eqs. (9) and (10) of the paper; §8.3) |
| `f_wfsed_turb` (&list_geomorph) | 0 | stirring by breaking turbulence | **Compatibility**: the default 0 (no turbulence = the same results as before turbulence was added). 1 is the form of `turb` = wave_averaged of XBeach (the XBeach default with the Ruessink waveform[^xbeach]). The coefficient 1.45 is from van Thiel de Vries (2009)[^vtdv09] |
| `f_wfswash` (&list_geomorph) | 0 | swash-zone transport | **Method**: by default no swash-zone transport. The cross-shore part is Eq. (8) of Larson et al. (2004)[^larson04], the longshore part Eq. (4) of Larson & Wamsley (2007)[^lw07], and the runup height the swash part of Eq. (19) of Stockdon et al. (2006)[^stockdon06]. The exposure, the mapping to the grid (four-neighbour faces, longshore band) and the combination using the swash of Stockdon et al. for R are original (§9.3, §9.4) |
| `wfswash_kc` (&list_geomorph) | 1.6×10⁻³ | cross-shore transport coefficient K_c | **Calibration**: the mean of the calibrations of Larson et al. (2004) on four runs at Hasaki Beach (fine sand, 0.18 mm) (1.0–2.3×10⁻³ in the individual runs; 3×10⁻³ from the regression on the transport at the seaward end of the swash zone). It depends on the grain size and on the interaction between waves in the swash |
| `wfswash_kl` (&list_geomorph) | = K_c | longshore transport coefficient K_l | **Calibration**: the assumption K_l ≈ K_c of Larson & Wamsley (2007) (10⁻³ agrees in the LSTF experiments) |
| `wfswash_tanbe` (&list_geomorph) | (required) | equilibrium foreshore slope tanβ_e | **Given**: supplied by the user (the "give the physical quantities used in the computation directly" of policy §0). 0.035–0.057 for the fine sand of Hasaki (Table 1 of Larson et al. 2004) |
| `wfswash_phim` (&list_geomorph) | 30° | friction angle of a moving grain φ_m | **Literature value**: the friction angle of a moving grain of Larson et al. (2004) |

**Where to look when revising the defaults**

- The breaking coefficients (`wf_gamma`, `wf_alpha`, `wf_gammax`) are the XBeach defaults; use them
  unchanged first. They are the quantities to examine when the position of the surf zone or the decay
  of the wave height does not match observations. On steep beaches try `wf_break = 2` first.
- For the directional spreading `wf_spread`, give the spreading from wave observations at the site
  (directional spectra) if they exist.
- The direction and speed of beach erosion and recovery are sensitive to `wfsed_facsk` and
  `wfsed_facas`. Calibrate them against observed profiles (offshore movement in eroding periods,
  recovery in calm periods).
- Give the equilibrium foreshore slope `wfswash_tanbe` from observations of the foreshore slope at the
  site (steeper for coarser sand). The coefficient `wfswash_kc` comes from field observations of fine
  sand, so check the sensitivity when the grain size differs.
- Match the strength of the horizontal mixing by wave breaking `wf_break_visc` to observations of the
  cross-shore distribution of the longshore current, if available.

## 11. Verification cases

| Case | Content | Points checked |
|---|---|---|
| [test/wfshoal](../../../test/wfshoal/en/README.md) | A beach profile of slope 1/80 | Shoaling and saturated breaking of regular waves (agreement with linear theory), refraction (Snell's law and first-order convergence in the directional bins), breaking of random waves (Baldock, Janssen & Battjes; agreement with the discrete solution built with dissipation formulas written independently in Python, 1% difference from the energy balance integrated with a fine step), the arrival of the front and the steady state in the unsteady mode, closure of the ledger, byte-identical continuation after a restart, identical flow with and without the wave field, and the interpolation of the offshore wave series |
| [test/wfshadow](../../../test/wfshadow/en/README.md) | A breakwater and an enclosure of diagonal walls | Agreement with an independently implemented sweep solution, blocking by the diagonal walls, and exactly sharp shadows for waves aligned with a lattice direction |
| [test/wfcurrent](../../../test/wfcurrent/en/README.md) | Action on the flow | The per-face discrete balance of the setup, the set-down offshore (Longuet-Higgins & Stewart) and the slope in the surf zone (Bowen et al.), agreement of the longshore current and the friction of the return flow on a uniform depth with the closed form, the integral momentum balance of the longshore current on a beach, the budget of the roller and its shoreward shift, alongshore uniformity at lateral Neumann sides, agreement with a grid rotated by 90°, and byte-identical continuation after a restart. Also the balances and budgets of the two-way coupling with the action of the current on the waves, the horizontal mixing by wave breaking (agreement of ν_w with the formula, alongshore uniformity and the integral momentum balance) and the diffusion at lateral Neumann sides |
| [test/wfdoppler](../../../test/wfdoppler/en/README.md) | Change of waves by currents | Conservation of the wave action flux on opposing and following currents (with an independently solved dispersion relation), the position of blocking by an opposing current and the ledger, with and without the current effect, the unsteady mode (the wave action ledger closes while the current spins up), a river-mouth jet that stops the waves from propagating up the river, and byte-identical continuation after a restart |
| [test/wfsed](../../../test/wfsed/en/README.md) | Action on sediment | The equilibrium concentration of suspended load and the bed load transport under stirring (agreeing with the formulas of Soulsby 1997 assembled independently), the direction, cross-shore distribution and alongshore uniformity of longshore transport on a beach and its order of magnitude against CERC (Komar & Inman 1970), the onshore velocity u_a (agreeing with the formula of Ruessink et al. 2012), the direction of erosion by high waves and of recovery by low waves, conservation of sediment in a closed basin, the stirring by breaking turbulence (agreement of k_b with the formula and the increase of longshore transport), and byte-identical continuation after a restart |
| [test/wfswash](../../../test/wfswash/en/README.md) | Swash-zone transport | The amount of one bed update agrees with the formula of Larson et al. (2004) in double precision, a 45° shoreline gets the same amount per unit length as an axis-aligned one, no change at the equilibrium slope, the build-up of a mild foreshore (a berm) and the cut-back of a steep one approach the equilibrium slope without passing it, deposits do not exceed the runup limit, the total longshore transport under oblique waves agrees with the formula of Larson & Wamsley (2007), nothing moves in front of a cliff higher than the runup, conservation of sediment in a coupled closed basin, byte-identical restart continuation |
| [examples/delta](../../../examples/delta/en/README.md) | A river delta (wfsed) | A morphological run of 1500 h combining the wave field, process-based sediment transport, swash-zone transport and background viscosity, and the comparison with and without the swash-zone transport |

All are bit-identical to the serial run with MPI np = 1, 2 and 4.

## 12. Models the implementation drew on and the parts original to ENCflow

No conceptual novelty is claimed for this feature. The wave field is built on the existing class of
phase-averaged wave action balances with a representative period and directional bins (HISWA, the
stationary mode of XBeach, SnapWave); many of the formulations and defaults of breaking, friction,
the roller, GLM, wave–current friction, stirring and the transport velocity follow the XBeach
formulation, and the swash-zone transport follows the empirical formulas of Larson et al. and
Stockdon et al. What is specific to ENCflow is the discretisation that puts it on the 8-direction ENC
grid (two-link upwind decomposition, closure of diagonals, projection of the force onto faces, the
mirror of lateral Neumann sides), the structure of a solver that gives bit-identical results across
rank counts, the connection to ENCflow's existing sediment formulas (the form of bed load transport,
how turbulence is added), the rules that map the empirical swash formulas onto the grid, and the way
it is integrated: run on the same grid and in the same time evolution as the shallow water flow and
sediment, with zero overhead when disabled.

### 12.1 Other models and studies the implementation drew on

| Model / study | What this implementation took from it | Differences |
|---|---|---|
| **HISWA**[^hiswa] | the class of directional-bin wave action balances without discretised frequencies for waves in shallow water with currents (the starting point of the lineage) | this implementation uses one representative period (ω fixed) and is also used unsteadily |
| **The stationary mode of XBeach**[^xbeach] | the formulas and coefficients of breaking (Baldock et al., Janssen & Battjes, the Miche-type H_b), the depth limit and bottom friction, the distribution of dissipation over the bins (E_m/E), the defaults (γ, α, γmax, f_w) | it has nothing corresponding to the surfbeat mode of XBeach (wave groups, infragravity waves) or its non-hydrostatic mode |
| **The flow and sediment formulations of XBeach**[^xbeach] | the roller (the radiation-stress approximation of Nairn et al. 1990, β, enabled by default), depth-averaged GLM, the wave–current friction speed (1.16), the ramp of the force (taper), the refraction by currents and the velocity used (wci), the breaking eddy viscosity (nuhfac), breaking turbulence (turb = wave_averaged), suspended transport with the Eulerian mean velocity, the onshore velocity (facua and the coefficients of Ruessink et al. 2012) | the wavenumber is not advanced with the eikonal equations but solved directly from the dispersion relation for each directional bin (§7.1); turbulence is added not to the equilibrium concentration formula but to the velocity of Soulsby's wave shear stress (§8.2); sediment amounts use ENCflow's existing bed load and equilibrium concentration formulas with τ*_max (§8.1, §8.4); the eddy viscosity is added to the background viscosity (§6.4) |
| **SnapWave**[^snapwave] | solving refraction in directional space implicitly with a tridiagonal system per cell, the limit of the refraction speed \|c_θ\| ≤ σ/4, the defaults (minimum depth 0.1 m, update interval 3600 s) | SnapWave interpolates with distance weights from two upwind points and solves with four sweeps (public source); this implementation solves a conservative two-link decomposition (§3) with Jacobi-type iteration (§4.3). The breaking formula follows XBeach rather than the form in the public SnapWave source (coefficient 0.28, H_b = γh) (§5). It has the action of currents (§7) |
| **SWAN**[^swan] | the form of the wave action balance (reduced to one frequency), the shape of the cos^s directional distribution, the formula of the refraction speed by currents | no frequency dimension, wind or nonlinear interactions; the mix of central and upwind differencing in directional space (CDD type) and the sweep solver are not adopted (§4.1, §4.3) |
| D∞ (Tarboton 1997)[^tarboton97] | the idea of sharing a flow direction between two of the 8 neighbours by angle | not the flow direction of terrain but the flux of the propagation velocity of each directional bin, decomposed non-negatively into two lattice directions (§3) |
| Bretherton & Garrett (1968)[^bg68] | conservation of wave action and the dispersion relation on a current | — |
| Kuik et al. (1988)[^kuik88], Fenton & McKee (1990)[^fm90], van Leer (1974)[^vanleer74] | the definition of directional spreading, the explicit approximation of the dispersion relation, the limiter | the approximation is the initial value of Newton's method; the limiter is used for the deferred correction in directional space (§2.2, §4.1) |
| Longuet-Higgins & Stewart (1962, 1964)[^lhs64], Bowen et al. (1968)[^bowen68] | radiation stress, set-down and set-up | integrated over the directional bins, differenced at cell centres and projected onto faces (§6.1) |
| Svendsen (1984)[^svendsen84], Reniers & Battjes (1997)[^rb97], Nairn et al. (1990)[^nairn90] | the energy balance, dissipation, mass transport and radiation stress of the roller | — |
| Andrews & McIntyre (1978)[^am78], Walstra et al. (2000)[^walstra00], Ruessink et al. (2001)[^ruessink01] | the Lagrangian mean flow and depth-averaged GLM, the wave–current friction speed | — |
| Battjes (1975)[^battjes75] | the eddy viscosity of breaking, the surface turbulence | the form of the formula follows the XBeach implementation (the original paper has not been checked) |
| Soulsby (1997)[^soulsby97], Swart (1974)[^swart74] | the wave friction factor and the combination of wave and current shear stresses | — |
| Reniers et al. (2004)[^reniers04] | carrying suspended load with the Eulerian mean velocity | — |
| van Thiel de Vries (2009)[^vtdv09], Ruessink et al. (2012)[^ruessink12], Roelvink & Stive (1989)[^rs89] | the onshore velocity u_a and the parameterization of skewness and asymmetry, the turbulence coefficient 1.45, the decay of turbulence towards the bed | the coefficients p₂ to p₆ are the values of the public XBeach source, which differ from the best-fit values of the paper (§8.3) |
| Larson et al. (2004)[^larson04] | Eq. (8) for cross-shore swash transport, the values of K_c and φ_m | the runup height uses the swash of Stockdon et al. (§9.3) |
| Larson & Wamsley (2007)[^lw07] | Eq. (4) for longshore swash transport, K_l ≈ K_c | placed in a band along the shoreline and passed to the 8-direction faces (§9.4) |
| Stockdon et al. (2006)[^stockdon06] | the swash part of the runup height R = 1.1 S/2 | the setup is resolved by the flow, so only the swash part is used, multiplied by the exposure (§9.3) |
| CERC (Komar & Inman 1970)[^ki70] | checking the order of magnitude of the longshore transport rate (verification) | not included in the model (§8.5) |
| single-wave-train WKB (ROMS/CROCO; Uchiyama et al. 2010[^uchiyama10]) | following the change of wavenumber and frequency by currents with a wavenumber vector (a candidate for future combined use) | **not adopted**: behind bars, islands and river mouths, where rays cross, the wavenumber field becomes multivalued, and it cannot hold directional spreading or a wave direction that changes in time |
| vortex-force formalism (McWilliams et al. 2004[^mcwilliams04], Uchiyama et al. 2010) | another formulation of wave–current interaction | **not adopted**: depth-averaged, it represents the same physics as GLM, and GLM fits the structure of the ENC momentum equations (force and friction per face) more naturally |
| spectral models (SWAN and others) | — | **not adopted**: hundreds to a thousand unknowns of frequency × direction are too heavy for running all processes on the same grid. Read external results if needed |
| phase-resolving models (SWASH[^zijlema11], FUNWAVE-TVD[^shi12], the non-hydrostatic mode of XBeach) | — | **not adopted**: a grid of about 1/20 of the wavelength and time steps orders of magnitude smaller do not suit the time scales of morphology. Dispersion of long waves is handled by the [non-hydrostatic correction](nonhydrostatic.md) |
| energy balance with discretised frequencies and a diffraction term (CMS-Wave; Mase 2001[^mase01]) | an approximation of diffraction (a future candidate) | **not adopted** (for now): a class above this implementation; an approximation of diffraction has low priority |
| ENC finite volume + link-direction MUSCL (the same form as the shallow water flow and scalar transport) | — | **not adopted**: in the test of shadow-edge widths it was worse than the two-link decomposition along lattice directions and not worth its cost in oblique directions (§3) |

### 12.2 Theory and implementation original to ENCflow

| Original part | Content | Reason | What was checked |
|---|---|---|---|
| Two-link upwind decomposition (§3) | puts the directional bins on the 8-direction ENC grid by a non-negative decomposition into the two lattice directions that bracket the propagation velocity | no crosswind numerical diffusion along lattice directions; conservative and positive | the comparison of shadow-edge widths, test/wfshadow (independent sweep solution, sharp shadows along lattice directions), test/wfshoal |
| Closure of diagonals (§3) | a diagonal whose two side cells are both non-wave cells is closed | waves do not slip through a one-cell-thick diagonal breakwater | the diamond enclosure of test/wfshadow |
| Solving directional space (§4.1) | implicit first-order upwind + deferred limited second-order correction of van Leer (original combination) | reduces the delay of refraction without producing negative energy | refr of test/wfshoal (Snell's law, first-order convergence) |
| One kernel, two modes (§4.3) | the Jacobi-type update shared by the quasi-steady mode with local pseudo time steps and the unsteady mode in physical time (original combination) | bit-identical results regardless of rank and thread counts | bit identity of np = 1, 2, 4 in all verification cases, unst of test/wfshoal |
| Corners of boundaries, absorbing cells (§4.4) | virtual senders at corners take incident > lateral Neumann > absorbing; building-porosity and sub-grid channel cells are absorbing cells; sea cells are outside the domain | keeps the uniformity of a straight coast; unsupported combinations are not computed silently | test/wfshoal (alongshore uniformity) |
| Projection of the force onto faces (§6.1) | the cell-centre force averaged over the two cells, projected onto the face and divided by the mean depth of the two cells | axis and diagonal faces obey the same balance and no false circulation arises; the force does not switch with the sign of the velocity | test/wfcurrent (per-face discrete balance, agreement with a grid rotated by 90°) |
| Lateral Neumann sides (§6.6) | mirror cells give the momentum equation, the advection control volume, the diffusion and the sediment inflow of boundary faces with the same formulas as interior faces | the same coast is treated as continuing outside: the longshore current passes through the side, and inflow is not accelerated | test/wfcurrent, test/wfsed (alongshore uniformity) |
| Combination of the eddy viscosity (§6.4) | the sum with the background viscosity | how XBeach combines them is unchecked; the same treatment as the existing breaking eddy viscosity | mix of test/wfcurrent |
| Dispersion relation per bin (§7.1) | ω fixed, the dispersion relation on a current solved directly for each directional bin (the change of ω on a current varying in time is not included = our own simplification) | consistent with a wave action balance with one representative period; no wavenumber field is needed | test/wfdoppler (independently solved dispersion relation, position of blocking) |
| Handling of the grid-scale stripes (§7.3) | identifying the grid-scale positive feedback between flow → waves and waves → flow, and handling it with background viscosity | stops a grid-scale response outside the WKB premise | the isolation of the cause in examples/delta (developer.md §90.20) |
| Form of bed load transport (§8.4) | the amount of τ*_max carried at the speed of u_s (original combination) | connects waves to the existing bed load formulas and agrees with the existing formula without waves | the same order as the wave–current bed load formula of Soulsby (1997) (0.92 against 0.98 under the conditions of test/wfsed) |
| How turbulence is added (§8.2) | near-bed turbulence added to the velocity of Soulsby's wave shear stress (our own simplification) | uses the existing stirring path as it is | turb of test/wfsed (agreement of k_b with the formula) |
| Runup height and exposure (§9.3) | the swash of Stockdon et al. multiplied by the exposure E and combined with the formula of Larson et al. (original combination) | the setup is resolved by the flow; the swash is reduced on shorelines that waves hardly reach | test/wfswash (agreement with the formulas) |
| Mapping the swash zone onto the grid (§9.4) | shoreline cells, cross-shore fluxes on four-neighbour faces, longshore fluxes in the shoreline band, the swash-zone condition, deposition on dry cells and the runup limit | keeps the amount per unit length whatever the shoreline orientation, and carries no sand in front of cliffs | test/wfswash (diag, eq, mild, steep, obl, cliff, flow) |
| Integration (§1) | the same grid and time evolution as the shallow water flow and sediment, coupling through the shared state, zero overhead when disabled, choice of the morphological-time (MORFAC) clock | runs together with the other processes as an integrated model | the results of existing cases that do not use the feature are unchanged (comparison with the references) |

### 12.3 Processes not treated and extensions considered

Diffraction, reflection, frequency spreading, wind growth, nonlinear interactions and the change of
frequency by a current varying in time are not treated. The candidate extensions (combined use of a
wavenumber field, an approximation of diffraction, wind growth, sweep solvers) and the decisions are
in docs/wavefield_plan.md §9 and developer.md §90.17. The bibliography and the status of checks
against the originals are in docs/wavefield_plan.md §11 and §12 and developer.md §90.

## References

[^am78]: Andrews, D. G. & McIntyre, M. E. (1978) An exact theory of nonlinear waves on a Lagrangian-mean flow. J. Fluid Mech. 89, 609–646.
[^baldock98]: Baldock, T. E., Holmes, P., Bunker, S. & Van Weert, P. (1998) Cross-shore hydrodynamics within an unsaturated surf zone. Coastal Engineering 34, 173–196.
[^battjes75]: Battjes, J. A. (1975) Modeling of turbulence in the surf zone. Proc. Symposium on Modeling Techniques, ASCE, San Francisco, 1050–1061. (Eddy viscosity of wave breaking ν = M h (D/ρ)^{1/3}; the form of the formula follows the nuhfac implementation of XBeach; the original paper has not been checked)
[^bg68]: Bretherton, F. P. & Garrett, C. J. R. (1968) Wavetrains in inhomogeneous moving media. Proc. R. Soc. Lond. A 302, 529–554.
[^bowen68]: Bowen, A. J., Inman, D. L. & Simmons, V. P. (1968) Wave 'set-down' and set-up. J. Geophys. Res. 73(8), 2569–2577.
[^eurotop]: EurOtop (2018) Manual on wave overtopping of sea defences and related structures, 2nd ed. Van der Meer, J. W., Allsop, N. W. H., Bruce, T., De Rouck, J., Kortenhaus, A., Pullen, T., Schüttrumpf, H., Troch, P. & Zanuttigh, B. www.overtopping-manual.com
[^fm90]: Fenton, J. D. & McKee, W. D. (1990) On calculating the lengths of water waves. Coastal Engineering 14, 499–513.
[^gt85]: Guza, R. T. & Thornton, E. B. (1985) Velocity moments in nearshore. J. Waterway, Port, Coastal, Ocean Eng. 111(2), 235–256.
[^hiswa]: Holthuijsen, L. H., Booij, N. & Herbers, T. H. C. (1989) A prediction model for stationary, short-crested waves in shallow water with ambient currents. Coastal Engineering 13, 23–54.
[^ki70]: Komar, P. D. & Inman, D. L. (1970) Longshore sand transport on beaches. J. Geophys. Res. 75(30), 5914–5927.
[^jb07]: Janssen, T. T. & Battjes, J. A. (2007) A note on wave energy dissipation over steep beaches. Coastal Engineering 54, 711–716. The form of the breaking wave height H_b is the Miche type of Battjes, J. A. & Janssen, J. P. F. M. (1978) Energy loss and set-up due to breaking of random waves. Proc. 16th ICCE, 569–587 (the same as the XBeach formulation).
[^kuik88]: Kuik, A. J., van Vledder, G. Ph. & Holthuijsen, L. H. (1988) A method for the routine analysis of pitch-and-roll buoy wave data. J. Phys. Oceanogr. 18, 1020–1034.
[^larson04]: Larson, M., Kubota, S. & Erikson, L. (2004) Swash-zone sediment transport and foreshore evolution: field experiments and mathematical modeling. Marine Geology 212, 61–79. doi:10.1016/j.margeo.2004.08.004 (Eqs. (5) and (8); the calibration of K_c in Sections 6 and 8)
[^lw07]: Larson, M. & Wamsley, T. V. (2007) A formula for longshore sediment transport in the swash. Proc. Coastal Sediments '07, ASCE. (Eqs. (3), (4), (6) and (7))
[^lhs64]: Longuet-Higgins, M. S. & Stewart, R. W. (1964) Radiation stresses in water waves; a physical discussion, with applications. Deep-Sea Research 11, 529–562. The set-down offshore is from Longuet-Higgins, M. S. & Stewart, R. W. (1962) Radiation stress and mass transport in gravity waves, with application to 'surf beats'. J. Fluid Mech. 13, 481–504.
[^mase01]: Mase, H. (2001) Multi-directional random wave transformation model based on energy balance equation. Coastal Engineering Journal 43(4), 317–337.
[^mcwilliams04]: McWilliams, J. C., Restrepo, J. M. & Lane, E. M. (2004) An asymptotic theory for the interaction of waves and currents in coastal waters. J. Fluid Mech. 511, 135–178.
[^nairn90]: Nairn, R. B., Roelvink, J. A. & Southgate, H. N. (1990) Transition zone width and implications for modelling surfzone hydrodynamics. Proc. 22nd ICCE, 68–81.
[^rb97]: Reniers, A. J. H. M. & Battjes, J. A. (1997) A laboratory study of longshore currents over barred and non-barred beaches. Coastal Engineering 30, 1–22.
[^reniers04]: Reniers, A. J. H. M., Roelvink, J. A. & Thornton, E. B. (2004) Morphodynamic modeling of an embayed beach under wave group forcing. J. Geophys. Res. 109, C01030.
[^rs89]: Roelvink, J. A. & Stive, M. J. F. (1989) Bar-generating cross-shore flow mechanisms on a beach. J. Geophys. Res. 94(C4), 4785–4800. (Exponential decay of breaking turbulence towards the bed; the form of the formula follows the turb implementation of XBeach)
[^ruessink01]: Ruessink, B. G., Miles, J. R., Feddersen, F., Guza, R. T. & Elgar, S. (2001) Modeling the alongshore current on barred beaches. J. Geophys. Res. 106(C10), 22451–22463.
[^ruessink12]: Ruessink, B. G., Ramaekers, G. & van Rijn, L. C. (2012) On the parameterization of the free-stream non-linear wave orbital motion in nearshore morphodynamic models. Coastal Engineering 65, 56–63. (Eqs. (6)–(10); the best-fit coefficients on p. 58)
[^shi12]: Shi, F., Kirby, J. T., Harris, J. C., Geiman, J. D. & Grilli, S. T. (2012) A high-order adaptive time-stepping TVD solver for Boussinesq modeling of breaking waves and coastal inundation. Ocean Modelling 43–44, 36–51.
[^stockdon06]: Stockdon, H. F., Holman, R. A., Howd, P. A. & Sallenger, A. H. Jr. (2006) Empirical parameterization of setup, swash, and runup. Coastal Engineering 53, 573–588. doi:10.1016/j.coastaleng.2005.12.005 (Eqs. (9)–(12) and (19))
[^snapwave]: Roelvink, D., van Ormondt, M., Reyns, J. & van der Lugt, M. (2025) SnapWave: fast, implicit wave transformation from offshore to nearshore. Geosci. Model Dev. 18, 9469–9495. doi:10.5194/gmd-18-9469-2025 (defaults and solver from the public source code)
[^soulsby97]: Soulsby, R. L. (1997) Dynamics of Marine Sands: A Manual for Practical Applications. Thomas Telford, London. Wave friction factor (eq. 62a), combination of wave and current shear stresses (eqs. 69 and 70).
[^svendsen84]: Svendsen, I. A. (1984) Wave heights and set-up in a surf zone. Coastal Engineering 8, 303–329.
[^swan]: Booij, N., Ris, R. C. & Holthuijsen, L. H. (1999) A third-generation wave model for coastal regions: 1. Model description and validation. J. Geophys. Res. 104(C4), 7649–7666.
[^swart74]: Swart, D. H. (1974) Offshore sediment transport and equilibrium beach profiles. Delft Hydraulics Laboratory, Publication No. 131.
[^tarboton97]: Tarboton, D. G. (1997) A new method for the determination of flow directions and upslope areas in grid digital elevation models. Water Resour. Res. 33(2), 309–319.
[^uchiyama10]: Uchiyama, Y., McWilliams, J. C. & Shchepetkin, A. F. (2010) Wave–current interaction in an oceanic circulation model with a vortex-force formalism: Application to the surf zone. Ocean Modelling 34, 16–35. doi:10.1016/j.ocemod.2010.04.002
[^vanleer74]: van Leer, B. (1974) Towards the ultimate conservative difference scheme. II. Monotonicity and conservation combined in a second-order scheme. J. Comput. Phys. 14, 361–370.
[^vtdv09]: van Thiel de Vries, J. S. M. (2009) Dune erosion during storm surges. PhD thesis, Delft University of Technology.
[^walstra00]: Walstra, D. J. R., Roelvink, J. A. & Groeneweg, J. (2000) Calculation of wave-driven currents in a 3D mean flow model. Proc. 27th ICCE, 1050–1063.
[^xbeach]: Roelvink, D., Reniers, A., van Dongeren, A., van Thiel de Vries, J., McCall, R. & Lescinski, J. (2009) Modelling storm impacts on beaches, dunes and barrier islands. Coastal Engineering 56, 1133–1152. Formulations and defaults are from the XBeach manual (xbeach.readthedocs.io) and the public source code (params.F90).
[^zijlema11]: Zijlema, M., Stelling, G. and Smit, P. (2011) SWASH: An operational public domain code for simulating wave fields and rapidly varied flows in coastal waters. Coastal Engineering 58, 992–1012.
[^hunt59]: Hunt, I. A. (1959) Design of seawalls and breakwaters. J. Waterways and Harbors Div. ASCE 85(3), 123–152. (Hunt's runup formula; cited by Larson et al. (2004); the paper itself not checked)
[^mk94]: Mayer and Kriebel (1994) Wave runup on composite-slope and concave beaches. Proc. 24th Int. Conf. Coastal Eng. (Coastal Engineering Proceedings 1(24)). Cited by Larson et al. (2004); the title checked in the proceedings index (the authors' initials, the pages and the paper itself not checked)
[^wang02]: Wang, P., Smith, E. R. & Ebersole, B. A. (2002) Large-scale laboratory measurements of longshore sediment transport under spilling and plunging breakers. J. Coastal Res. 18(1), 118–135. (LSTF experiments; under spilling breakers the longshore transport peaks in the swash zone. Not yet matched against the reference list of Larson & Wamsley (2007))
