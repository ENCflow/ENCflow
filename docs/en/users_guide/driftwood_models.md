# Driftwood models explained (supplement to the driftwood chapter)

> English mirror of docs/users_guide/driftwood_models.md. The Japanese file is the master copy.

[Back to the driftwood chapter](driftwood.md) | [Back to the user's guide index](../users_guide.md)

This page gives the transfer rules of the three-ledger model of the
[driftwood chapter](driftwood.md), the draft of the representative log, the
area bases and the volume budget, the sources of the practical values and
the basis of the defaults, and capture and jamming at structures (the fourth
ledger; §6). The implementation is in `src/m_driftwood.f90` (the drag term of the
jam in `src/m_swflow_enc.f90`); the design history and literature checks are in
developer.md §50 (in Japanese).

## 1. Ledgers and transfer rules

Three ledgers are used: the standing stock $`w_{st}`$, the moving wood
$`h_d`$ and the deposited wood $`w_d`$; only $`h_d`$ is advected
conservatively with the water (or the water–sediment mixture in debris
flow). The mixed flow depth used for the tests is $`H = h + \max(h_s, 0)`$
and $`V`$ is the cell speed; distinguish them from the water-only dry-cell
test $`h \le d_d`$.

| Path | Condition | Transfer |
|---|---|---|
| ① hydraulic recruitment $`w_{st} \to h_d`$ | $`H >`$ dw_hrec and $`V >`$ dw_vrec | rate dw_wrec |
| ② erosion entrainment $`w_{st} \to h_d`$ | $`z_{ref} - z >`$ dw_droot (net lowering from the reference) | all of the remainder |
| ③ stopping / deposition $`h_d \to w_d`$ | all if $`h \le d_d`$; otherwise $`H < h_f`$ or $`V <`$ dw_vstop | rate dw_wstop |
| ④ refloating $`w_d \to h_d`$ | with dw_wfloat > 0, $`H >`$ dw_rfloat $`\times h_f`$ and $`V >`$ dw_vfloat | rate dw_wfloat |

For each rate $`w`$ (m³/m²/s) the transfer in one step is capped by the
remaining amount $`S`$ of the source ledger:

```math
\Delta = \min\left(w\,\Delta t,\ S\right)
```

After advection and landform updates the local order is ② → ① → (⑤ capture at
structures; §6) → ③ → ④ → dam capture → period-maximum update. A cell passing the dry-cell test is
still tested for refloating in ④ if enabled. The entrainment test uses the
net lowering from the reference elevation $`z_{ref}`$ (at initialisation;
the saved value on restart), not the accumulated erosion increments, and
does not distinguish which process lowered $`z`$.

## 2. Draft of the representative log

The draft $`h_f`$ is the buoyancy balance of a horizontal cylinder of
diameter $`D`$ = dw_dlog and specific gravity $`s_g`$ = dw_sglog (submerged
area fraction = specific gravity)[^braudrick00]. With $`\theta`$ the
central angle of the submerged segment,

```math
\frac{\theta - \sin\theta}{2\pi} = s_g,\qquad
h_f = \frac{D}{2}\left(1 - \cos\frac{\theta}{2}\right)
```

so $`s_g = 0.5`$ gives $`\theta = \pi`$ and $`h_f = D/2`$ (half submerged).
In general $`h_f \ne s_g D`$ ($`s_g = 0.3`$ gives $`h_f \approx 0.34 D`$).

## 3. Area bases and volume budget

$`w_{st}`$ is wood volume per geometric cell area; $`h_d`$ and $`w_d`$ use
the same effective area as the water. With $`A = \Delta x\,\Delta y`$ and
$`f = g_v\,w_{frac}`$ ($`w_{frac} = 1`$ without specified channel widths),
the volume in the domain is

```math
Q = \sum_{i,j} A\left[w_{st,ij} + f_{ij}\,(h_{d,ij} + w_{d,ij})\right]
```

Recruitment subtracts $`\Delta w`$ from $`w_{st}`$ and adds $`\Delta w / f`$
to $`h_d`$. The rate dw_wrec uses the geometric area; dw_wstop and
dw_wfloat use the effective area (m³/m²/s). In a closed domain without dam
capture the sum of the current stocks $`Q`$ preserves the initial volume
(apart from numerical error). The jammed wood $`w_j`$ (§6) is a column quantity per the
same effective area as $`h_d`$ and $`w_d`$; when capture cells are given,
$`f_{ij}\,w_{j,ij}`$ joins the sum.

## 4. Sources of the practical values

Guides based on the Japanese sabo planning manual[^nilim904].

- **dw_dlog**: the manual estimates the mean driftwood diameter as roughly
  the mean diameter at breast height (DBH) of the standing trees upstream;
  survey DBH values can be used directly.
- **Standing stock**: from the single-tree volume $`V_1`$ and the tree
  density $`N`$ (trees/m²), $`w_{st} = N\,V_1`$ with
  $`V_1 = \tfrac{\pi}{4} D_{bh}^2 H_t f_s`$ ($`D_{bh}`$ breast-height
  diameter, $`H_t`$ tree height, $`f_s`$ form factor 0.3–0.7), converted to
  m³/m² in preprocessing. Observed envelopes of generated driftwood in
  torrents are about 1,000 m³/km² (= 0.001 m³/m²) for conifer and about
  100 m³/km² (= 0.0001 m³/m²) for broadleaf forests.
- **Validation metric**: the manual cites field evidence that, without
  countermeasure works, 80–90 % of the generated driftwood reached the
  valley outlet (outflow ratio 0.8–0.9).
- **Erosion entrainment (dw_droot)** follows the same idea as the manual's
  generation estimate (standing trees within the failure/debris-flow area
  become driftwood).
- **Hydraulic recruitment**: thresholds and rates are calibration
  parameters (the manual has no depth/velocity washout criterion, so no
  standard values exist).
- **Refloating**: flume experiments show that logs parallel to the flow or
  with rootwads move at about 1.2 times their buoyant depth, while logs
  oblique to the flow move below the buoyant depth by
  pivoting[^braudrick00]. The default dw_rfloat = 1.5 is on the stable side.
- **Impact forces** (postprocessing): the design standard[^nilim905]
  applies the boulder impact formula with the flow velocity and the maximum
  log diameter. Feeding the maximum velocity V9999 and the representative
  log properties into that formula (or the FEMA P-646 log impact formula)
  gives a standard-consistent impact-force map.

## 5. Parameters and the basis of their defaults

The labels in the Basis column are explained in [How to read the basis of a default](../users_guide.md#how-to-read-the-basis-of-a-default).

| Parameter | Default | Meaning | Basis |
|---|---:|---|---|
| standing stock | 0.001 m³/m² (uniform on land cells) | default when neither input is given | **literature value** envelope of generated driftwood in conifer torrents, 1,000 m³/km² (broadleaf 1/10)[^nilim904]; a magnitude guide when the forest location is unknown |
| dw_dlog / dw_sglog | 0.3 m / 0.5 | representative diameter and specific gravity | **literature value** middle of the manual's estimate (mean DBH 0.2–0.4 m)[^nilim904] and a middle specific gravity of green wood; draft 0.15 m |
| dw_wrec / dw_hrec / dw_vrec | 1e-5 m/s / 0.5 m / 1.0 m/s | hydraulic recruitment | **empirical** no practical standard; middle values meant for calibration |
| dw_droot | 0.5 m | rooting depth | **empirical** representative rooting depth relative to shallow-failure and channel-scour depths |
| dw_wstop | 0.01 m/s | grounding deposition rate | **empirical** near-immediate deposition after grounding |
| dw_vstop / dw_wfloat | 0 / 0 | slow-flow deposition and refloat | **empirical** depth criterion only and no refloat = upper bound of reach (conservative) |
| dw_rfloat | 1.5 | refloat buoyancy margin | **literature value** on the stable side of the onset of motion ≈ 1.2 × draft[^braudrick00] |
| the two recruitment paths | both default when neither is given | dw_wrec / dw_droot | **method** erosion entrainment never fires unless the terrain moves, so it is harmless; giving only one disables the other (explicit intent respected) |
| fn_dwtrap | — (enables when given) | map of the capture ratio E | **given** set by the log length and the opening width; the module carries no length (§6) |
| f_dwjam | 1 | effect of the jam on the flow | **method** 1 = drag in the cells holding the jam; 0 is the ledger only (the flow equals a run without driftwood; for comparison) |
| dw_jamcd / dw_jamphi | 1.0 / 0.3 | drag coefficient and packing ratio of the jam | **empirical** the structure of the coefficient follows the porous-obstruction formula[^follett20]; the values are provisional, checked neither against the original text nor against measured backwater; to be calibrated (§6) |
| dw_jamgrow | none | cells whose jammed amount reaches it get a capture ratio of 1; until then the capture ratio rises in proportion to the jammed amount | **given** approximates wood catching more easily once a jam has started (§6); the guide is a multiple of the packing ratio times the representative diameter (one layer of logs); not given = constant capture ratio |

**Where to look when revising the defaults**

- The most direct source for the standing stock is the stand volume
  (m³/ha) of forest registers or forest-resource data, divided by
  1 ha = 10⁴ m². The fraction that is actually recruited can be estimated
  from the generation rates of the driftwood countermeasure
  guideline[^nilim904].
- The representative diameter and specific gravity depend on species
  (conifer / broadleaf) and stand age; the same guideline tabulates them in
  its estimation method.

Verification (developer.md §50.6): in [test/driftwood](../../../test/driftwood/en/README.md)
an empty &list_driftwood and a configuration with every default written
explicitly give byte-identical saved states.

## 6. Capture and jamming at structures

Giving the map of the capture ratio `fn_dwtrap` enables path ⑤, from the moving wood
$`h_d`$ to the jammed wood $`w_j`$, and the drag of the jam. $`w_j`$ is an immobile ledger
that only grows. A culvert, whose opening is narrower than a cell, takes the jam at its inlet
as a loss in its discharge law with the per-culvert selector `culv_jam = 1` ("Loss at a culvert
inlet" in this section).

**Capture rule (own).** The capture ratio $`E`$ is "the share of the driftwood passing a
capture cell once that is caught". The computation stays inside the cell. In a well-mixed
cell, if capture proceeds at a constant rate $`k`$ during the residence time
$`\Delta x / |V|`$, the captured share of the passing wood is $`k\tau/(1 + k\tau)`$. Setting
$`k\tau = E/(1-E)`$ so that this equals $`E`$, the amount captured in one step is

```math
\Delta = h_d\,\frac{r}{1+r},\qquad r = \frac{E}{1-E}\,\frac{|V|\,\Delta t}{\Delta x}
```

($`\Delta x`$ is the shorter side of the cell). $`E \ge 1`$ takes all of $`h_d`$ at that
moment; applied after the advection, it means "stop all the wood that has entered". Capture
is applied after
the recruitment (① ②) and before the grounding deposition (③). In a steady uniform flow
along a grid axis, the captured share equals $`E`$ even with the discretization that applies
advection and capture in turn. With changing or oblique flow it is an approximation; the
verification case gives 0.304 for $`E = 0.3`$.

**Wood catching more easily as the jam grows (own).** Logs that are already caught hold the
logs that follow, so the capture ratio rises as the jam grows. When `dw_jamgrow` is given, the
capture ratio becomes a function of the jammed amount $`w_j`$ of the cell.

```math
E_{\text{eff}}(w_j) = E + (1 - E)\,\min\!\left(\frac{w_j}{w_{\text{full}}},\ 1\right),
\qquad w_{\text{full}} = \texttt{dw\_jamgrow}
```

Without a jam it is the given $`E`$, it is 1 once the jammed amount has reached
$`w_{\text{full}}`$, and it is linear in between. The argument is the jammed amount (the
amount covering the water surface) because driftwood arrives at the surface; with the share of
the water column occupied, $`w_j/(\varphi h)`$, as the argument, wood would catch less easily
as the water rises. $`\varphi d`$ (the packing ratio times the representative diameter)
corresponds to the amount with which the jam covers the water surface with one layer of logs.
The functional form and this guide are ENCflow's own simplifications, not formulas from the
literature. A flume experiment is reported in which the captured share is small while few logs
have been caught and all the logs fed are caught once the number caught exceeds a certain
value[^mlit23]; the original text has not been checked.

With $`A`$ the cumulative wood that has arrived per area of the capture cells,
$`dw_j/dA = E_{\text{eff}}(w_j)`$, and the solution is

```math
w_j = \frac{E\,w_{\text{full}}}{1-E}\left[\exp\!\left(\frac{(1-E)\,A}{w_{\text{full}}}\right) - 1\right]
\quad (A \le A^*),
\qquad
w_j = w_{\text{full}} + (A - A^*) \quad (A > A^*),
\qquad A^* = \frac{w_{\text{full}}}{1-E}\ln\frac{1}{E}
```

$`A^*`$ is the amount that arrives before the capture ratio becomes 1. In the verification
cases the jammed share agrees with this solution within 1 % (§7).

**Drag of the jam.** The jam is treated as a porous obstruction. Following the idea that the
momentum loss by a wood jam is a drag proportional to the log diameter, the degree of packing
and the length of the jam[^follett20], a drag of the same form as its structural coefficient
$`C_A = L\,C_D\,a/(1-\varphi)^3`$ ($`L`$: length of the jam, $`a`$: frontal area per unit
volume, $`\varphi`$: solid volume fraction; $`a = 4\varphi/(\pi d)`$ for cylinders) is put
into the semi-implicit term of the momentum equation (the discretization is ENCflow's own).
The pore velocity inside the jam is $`u/(1-\varphi)`$, so the deceleration with respect to
the superficial velocity $`u`$ is $`\dfrac{C_D\,a}{2(1-\varphi)^3}|u|u`$. Assuming that the
jam of a cell occupies the whole depth with the packing ratio $`\varphi`$ and blocks the
fraction $`(w_j/h)/\varphi`$ of the cell length, the drag term of an edge becomes

```math
F_{\text{jam}} = -\,\kappa_0 \min\!\left(\frac{w_e}{h_f},\ \varphi\right)|\mathbf{V}|_e,
\qquad \kappa_0 = \frac{2\,C_D}{\pi\,d\,(1-\varphi)^3}\ \ [\mathrm{m^{-1}}]
```

$`w_e`$ is the mean of $`w_j`$ of the two cells of the edge, $`h_f`$ the same edge depth as
in the friction term and $`|\mathbf{V}|_e`$ the speed on the edge. The $`\min`$ expresses
that wood that does not fit in the water column adds no drag. Being a semi-implicit term, it
adds no time-step restriction. In cells with a channel width (`fn_width`) the velocity is the
in-channel velocity and the jammed amount is per plan area of the channel, so the same
expression applies unchanged.

In steady one-dimensional flow this adds one term to the gradually-varied-flow equation,
which is the analytical solution used for verification.

```math
\frac{dh}{dx} = \frac{S_0 - \dfrac{n^2 q^2}{h^{10/3}} - \kappa_0 \min\!\left(\dfrac{w}{h},\ \varphi\right)\dfrac{q^2}{g\,h^2}}{1 - \dfrac{q^2}{g\,h^3}}
```

**Loss at a culvert inlet (own).** The opening of a [culvert](structure.md) is narrower than a
cell, and the cell flow converging on the inlet is far slower than the flow inside the opening,
so the edge drag above cannot express the blockage of the opening (the loss scales with the
square of the velocity; in a trial with a 10 m grid and a 1 m × 1 m opening, a jam of 100 m³
placed in the inlet cell reduced the discharge by only 0.1 %). A culvert with `culv_jam = 1`
therefore takes the jam as a loss coefficient on the velocity in the opening.

- **Capture (ENCflow's own).** A culvert passes no driftwood, so the wood that would have
  entered with the water is taken to pile up at the inlet. In each cell of the cell group on
  the side the culvert is drawing from in that step (the intake cell group for a positive
  discharge, the outlet cell group for a negative one), the same share of the moving wood
  $`h_d`$ as the water drawn by the culvert is transferred to $`w_j`$. With $`\Delta h`$ the
  depth drawn from the cell (the culvert discharge split equally over the cell group) and
  $`h`$ the depth after drawing,

  ```math
  \Delta w_j = h_d\,\frac{\Delta h}{h + \Delta h}
  ```

  (cells with a cross-section shape σ are counted by volume, i.e. the rectangular-equivalent
  depth; this is the same share with which structures carry the substance of
  [water quality](wq.md)). Nothing is transferred in a step with zero discharge. The capture
  does not change the concentration of wood in the cell (per volume of water), so in a steady
  flow the concentration of the intake cells equals the concentration arriving from upstream,
  and the jammed share is the ratio $`Q_c/Q_{\text{in}}`$ of the culvert discharge $`Q_c`$ to
  the discharge $`Q_{\text{in}}`$ entering the intake cell group from upstream. Where all the
  water of the cells heads for the culvert ($`Q_c = Q_{\text{in}}`$) all the wood jams, at a
  pace set by the time it takes to replace the water of the cell (the water volume of the cell
  ÷ the discharge drawn).
- **Loss coefficient.** Consider a jam of thickness $`L`$ and packing ratio $`\varphi`$
  covering the section $`B \times D`$ of the opening. Its solid volume is
  $`V_j = \varphi L B D`$, so the structural coefficient of the same form as above becomes

  ```math
  C_A = \frac{L\,C_D\,a}{(1-\varphi)^3} = \frac{4\,C_D}{\pi d\,(1-\varphi)^3}\,\frac{V_j}{BD}
      = 2\,\kappa_0\,\frac{V_j}{BD}
  ```

  $`V_j`$ is the sum of the solid volumes of $`w_j`$ in the cell group on the higher-water
  side (m³).
- **Full pipe.** $`C_A`$ is added to the sum of losses of the energy equation:
  $`Q_p = BD\sqrt{2g\,\Delta\eta' / (1 + c_e + f_L + C_A)}`$.
- **Free surface (weir).** A loss $`C_A u_c^2/2g`$ is assumed just upstream of the
  critical-flow section. With the upstream head $`H`$ and the critical depth $`y_c`$,
  $`H = y_c + (1 + C_A)\,u_c^2/2g`$ and $`u_c^2 = g\,y_c`$ give $`y_c = H/(1.5 + C_A/2)`$.
  The discharge is proportional to $`y_c^{3/2}`$, so it becomes

  ```math
  \left(\frac{1.5}{1.5 + C_A/2}\right)^{3/2} = \left(1 + \frac{C_A}{3}\right)^{-3/2}
  ```

  times the discharge without the loss. This multiplier is applied to the weir discharge of
  the Honma formula (free and submerged overflow). The critical depth $`d_c`$ used for the
  downstream head of the pipe formula is computed from the discharge after the multiplier is
  applied.

With the default coefficients ($`d`$ = 0.3 m, $`\varphi`$ = 0.3, $`C_D`$ = 1, giving
$`\kappa_0`$ = 6.19 m⁻¹), $`c_e`$ = 0.5 and conduit length 0, a 1 m × 1 m opening gives
$`C_A`$ = 0.74 for a solid volume of 0.06 m³ (weir × 0.72, full pipe × 0.82) and $`C_A`$ = 6.2
for 0.5 m³ (weir × 0.19, full pipe × 0.44).

The limits of this formulation are as follows.

- The loss is a function of $`V_j/(BD)`$ only. The ratio of the log length to the size of the
  opening, the shape of the jam and the position of the jam relative to the water level are not
  considered.
- The weir multiplier rests on the assumption that the loss is estimated with the velocity
  $`u_c`$ at the critical-flow section. The jam sits in the deeper water in front of the
  opening, so the loss comes out larger than if it were estimated with the velocity there. For
  a large $`C_A`$ the weir multiplier (proportional to $`C_A^{-3/2}`$) falls faster than the
  full-pipe multiplier (proportional to $`C_A^{-1/2}`$). No measurement to compare it with is
  available yet.
- The capture assumes that the wood heads for the inlet in the same share as the water (a
  well-mixed cell). Differences between the motion of water and wood, such as wood floating at
  the surface and passing in front of the inlet, being drawn towards the inlet, being stopped
  by a screen, or thin wood passing through, are not expressed. The captured share cannot be
  given.
- The jam never shrinks, and the discharge does not fall to zero. When the flow reverses, only
  the jam in the cell group on the higher-water side is read.

**Coefficients and limits.**

- $`C_D`$ and $`\varphi`$ are calibration values. $`\varphi`$ acts through
  $`(1-\varphi)^3`$, so the sensitivity is large, and flume experiments report that the share
  of branches, leaves and fine organic matter changes the backwater greatly[^schalko18]. The
  defaults 1.0 and 0.3 are provisional. The original texts of the two references could not be
  obtained in this work; the form of the formula and the statements come from secondary
  material. The lumped formula of the literature (relating the depths upstream and downstream
  of the jam) and the integral of the distributed drag used here need not give the same
  backwater for the same coefficient, so calibrated values from the literature cannot be
  carried over as they are. The model has not yet been compared with measured backwater.
- The drag is set by the solid volume of the jam. For the same solid volume per unit channel
  width, changing the placement and the grid spacing changed the backwater by less than 1 %
  (trial computations during development).
- The drag of the jam is not included in the bed shear (sediment transport), because it is a
  form drag, not a shear acting on the grains.
- What it cannot do (judging whether a log gets caught, the shape and collapse of the jam,
  pressure flow under a deck, blockage of openings narrower than a cell, and so on) is listed
  in [the driftwood chapter](driftwood.md#capture-and-jamming-at-structures-fn_dwtrap).

## 7. Verification cases

- [test/driftwood](../../../test/driftwood/en/README.md): volume conservation, transport and deposition for both erosion entrainment and hydraulic recruitment, and comparison of saved states from split and uninterrupted runs. Capture and jamming at structures are checked in a straight channel: volume conservation (including the jam), agreement of the backwater from the drag of the jam with the solution of the gradually-varied-flow equation above (ratio of the rises 1.003; 0.982 where the packing limit is active), the capture ratio (0.304 for 0.3), the capture ratio rising with the jam through `dw_jamgrow` (jammed shares 0.439 and 0.933 for the solutions 0.4345 and 0.928 above), byte identity of the flow with `f_dwjam = 0` with a run without driftwood, and split continuation. The loss at a culvert inlet is checked in a set-up that drains an upstream pool through a single culvert: the discharge obtained from the decrease of the storage agrees with the discharge law including the loss of the jam at that time (within 0.04 % in the weir regime with $`C_A`$ = 6.2, and within 0.12 % through the full-pipe and weir regimes with $`C_A`$ = 0.74), the flow with `culv_jam = 0` and with `f_dwjam = 0` is byte-identical to a run without driftwood, and split continuation. The capture at the inlet is checked in a set-up with a culvert that draws 15 % of the main flow: the jammed share (0.1503) agrees with the share of the water drawn (0.1505).
- [examples/bridge_wood_jam](../../../examples/bridge_wood_jam/en/README.md): backwater and bypass flooding from driftwood jammed at a bridge (comparison of no driftwood, a jam that does not act on the flow and a jam with drag; spread from the capture assumption and the packing ratio; the relation between the jam volume and the backwater compared with the gradually-varied-flow formula above).
- [examples/timberyard](../../../examples/timberyard/en/README.md): timber influx from a log yard by storm surge (comparison of countermeasures: delaying the release, moving the yard away, raising the seawall; a supplement compares the deposition parameters; the impact-force postprocessing).
- [examples/tsunami_town](../../../examples/tsunami_town/en/README.md): coastal forest and log yard in a tsunami, chained with house destruction (supplement).

## References

[^braudrick00]: Braudrick, C. A. and Grant, G. E. (2000): When do logs move in rivers? *Water Resour. Res.*, 36(2), 571–583. (flume experiments on draft and onset of motion)
[^nilim904]: NILIM (2016): Guidelines for sabo master planning (debris flow and driftwood), commentary. *NILIM Technical Note*, No. 904 (in Japanese; title translated). (practical values and generation mechanisms)
[^nilim905]: NILIM (2016): Technical standard for the design of debris-flow and driftwood countermeasures, commentary. *NILIM Technical Note*, No. 905 (in Japanese; title translated). (log impact force, §4.3)
[^follett20]: Follett, E., Schalko, I. and Nepf, H. (2020): Momentum and energy predict the backwater rise generated by a large wood jam. *Geophys. Res. Lett.*, 47(17), e2020GL089346. (momentum equation treating a jam as a porous obstruction and its structural coefficient; original text not checked)
[^mlit23]: Report of the regional-issue (sabo) programme of the river and sabo technology research and development of the Ministry of Land, Infrastructure, Transport and Tourism, Japan (https://www.mlit.go.jp/river/gijutsu/tiiki_sabou/pdf/r5_tiiki_report4.pdf). The statement on the flume experiment (number of logs caught and captured share) comes from a search summary; the original text has not been checked (title and authors not confirmed either)
[^schalko18]: Schalko, I., Schmocker, L., Weitbrecht, V. and Boes, R. M. (2018): Backwater rise due to large wood accumulations. *J. Hydraul. Eng.*, 144(9), 04018056. (flume experiments on the backwater due to accumulations; original text not checked)
