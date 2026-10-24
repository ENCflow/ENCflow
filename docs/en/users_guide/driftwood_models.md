# Driftwood models explained (supplement to the driftwood chapter)

> English mirror of docs/users_guide/driftwood_models.md. The Japanese file is the master copy.

[Back to the driftwood chapter](driftwood.md) | [Back to the user's guide index](../users_guide.md)

This page gives the transfer rules of the three-ledger model of the
[driftwood chapter](driftwood.md), the draft of the representative log, the
area bases and the volume budget, the sources of the practical values and
the basis of the defaults. The implementation is in `src/m_driftwood.f90`;
the design history and literature checks are in developer.md §50 (in
Japanese).

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

After advection and landform updates the local order is ② → ① → ③ → ④ →
dam capture → period-maximum update. A cell passing the dry-cell test is
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
(apart from numerical error).

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

## 6. Verification cases

- [test/driftwood](../../../test/driftwood/en/README.md): volume conservation, transport and deposition for both erosion entrainment and hydraulic recruitment, and comparison of saved states from split and uninterrupted runs.
- [examples/timberyard](../../../examples/timberyard/en/README.md): timber influx from a log yard by storm surge (sensitivity of the deposition parameters and the impact-force postprocessing).
- [examples/tsunami_town](../../../examples/tsunami_town/en/README.md): coastal forest and log yard in a tsunami, chained with house destruction.

## References

[^braudrick00]: Braudrick, C. A. and Grant, G. E. (2000): When do logs move in rivers? *Water Resour. Res.*, 36(2), 571–583. (flume experiments on draft and onset of motion)
[^nilim904]: NILIM (2016): Guidelines for sabo master planning (debris flow and driftwood), commentary. *NILIM Technical Note*, No. 904 (in Japanese; title translated). (practical values and generation mechanisms)
[^nilim905]: NILIM (2016): Technical standard for the design of debris-flow and driftwood countermeasures, commentary. *NILIM Technical Note*, No. 905 (in Japanese; title translated). (log impact force, §4.3)
