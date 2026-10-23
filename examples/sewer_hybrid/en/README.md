# sewer_hybrid — an idealized urban-drainage experiment representing one trunk main (a line) and a branch network (an area) in a single conduit continuum layer

> English mirror of examples/sewer_hybrid/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A town's storm sewer system consists of a network of thin **branch pipes**
running under each street and thick **trunk mains** that collect their
water and carry it to a river or the sea. ENCflow represents this network
as **one underground layer**, the "conduit continuum layer"
(`f_gwconduit`). Instead of tracing each pipe individually, every cell is
given numbers for "how much water the pipes can store" and "how much can
flow to the neighbouring cell", and the underground water level (the
conduit head) is tracked cell by cell.

This example is an idealized experiment that checks **whether a thick trunk
main and thin branch pipes can share the same single layer**, and **how
much the answer then depends on how the storage coefficient is given**, by
raining 60 mm/h for one hour on a uniform slope of 400 m × 210 m (the
design record is developer.md §46.5, in Japanese). No code change is
needed; everything is assembled from input files alone. The following
explains, in order, the meaning of the parameters, the configuration of
each run, and how to read the results.

![Comparison of runs A–D](../sewer_hybrid_result.png)

## 1. The five parameters of the conduit continuum layer

Five values are given per cell. All of them are written out by gen_data.py,
which **converts them from the pipe specifications** (diameter D,
roughness n, pipe length within one cell, burial depth).

| Parameter | Meaning | Conversion (this case) |
|---|---|---|
| `cap` (storage capacity, m) | The total pipe volume divided by the cell area, a "columnar depth". The amount of water underground when the pipes are full | A·L/Δx². Branch pipe D = 0.4 m, L = 10 m → 0.0126 m (12.6 mm) |
| `cnd` (conveyance density, m²/s) | The discharge per unit width that can be conveyed when pipe-full at unit hydraulic gradient. Ease of flow to the neighbouring cell | C/Δx, C = (1/n)·A·R^(2/3). Branch 0.208, trunk 2.40 |
| `bot` (invert elevation, m) | The elevation of the pipe bottom. The datum of the head (the water level inside the pipe) | Branch pipes at ground − 2 m, trunk at ground − 5 m |
| `sy` (storage coefficient) | How many metres of columnar water are added when the head rises 1 m. The value **until the pipe is full** (unconfined): cap ÷ pipe height | Branch 0.0126/0.4 = 0.031, trunk cell 0.0911/1.0 = 0.091 |
| `slot_sy` (pseudo-slot storage coefficient) | The amount of water added when the head rises 1 m **after** the pipe is full (confined = pressurized). The smaller, the "stiffer" the pressure response | Physically ≈ 0, but 1/5 to 1/50 of sy is given for numerical stability |

In addition there are the **inlet density** (`inlet`, 1/m²), which governs
the exchange of water with the surface, and the **outfall**
(`fn_gwc_outfall`, run F), the outlet of the pipes. Rain falls on the
surface, enters the pipes through the inlets (weir type; once pipe-full,
the orifice type applies and water **erupts** only when the conduit head
rises above the surface), and collects inside the pipes toward the trunk
main.

**The pseudo slot and "phantom storage"**: when water is forced into a
pipe that is already full, in reality only the pressure rises and the
amount of water hardly increases. A numerical model treats this as a thin
slot (groove) standing on the pipe ceiling: the water is allowed to
increase by slot_sy, which corresponds to the slot width, and the pressure
(head) is computed from that (the Preissmann slot). A large slot_sy makes
the computation easier, but a large amount of non-existent water
accumulates in the slot, hiding underground the water that should have
overflowed onto the surface. This is "phantom storage", one of the main
characters of this example.

## 2. Setup

| Item | Value |
|---|---|
| Domain and grid | 400 m × 210 m, 40 × 21 cells (Δx = 10 m). Uniform slope descending eastward (gradient 0.005). Surface roughness n = 0.03. Walls on all four sides (in runs E and F the two easternmost columns are a river) |
| Rainfall | 60 mm/h for one hour (0–60 min), falling to 0 at 61 min. Total rainfall 61.0 mm |
| Branch network | Every cell: D = 0.4 m, n = 0.013, 10 m per cell (one street), buried 2 m. One inlet per cell (0.01 /m²) |
| Trunk main | D = 1.0 m, n = 0.013, buried 5 m at i = 2–38 of row j = 11. Trunk cells have the combined "trunk + branch" cap, and the head datum is the trunk invert. Pipe-full capacity 1.70 m³/s (gradient 0.005), against a rainfall runoff of 1.40 m³/s from the domain |
| Computation | dt = 0.02 s, 3 hours. The lateral flux of the conduit layer follows the square-root-gradient law (`f_gwc_fluxlaw = 2`). No other groundwater layer is used |
| Output | Distributions of surface depth H, water level E and conduit storage Hgc every 30 minutes; the water budget in Log.txt (S_surf = surface, S_grnd = in the pipes) |

| Run | Trunk | sy / slot_sy | River and outfall | Purpose |
|---|---|---|---|---|
| A | Yes | Uniform 0.0314 / 0.03 (values matched to the branch pipes) | None | The storage coefficient of the trunk cells is too small (the head rises about 3 times too high) |
| B | Yes | Uniform 0.0911 / 0.03 (values matched to the trunk) | None | The storage coefficient of the branch cells is too large (the branch response is about 3 times too sluggish) |
| C | None (all cells branch pipes) | Uniform 0.0314 / 0.03 | None | Control for seeing the effect of the trunk |
| D | Yes | **Per-cell map** (trunk 0.0911, branch 0.0314; slot = sy/5) | None | The "correct answer", consistent for both trunk and branches. `fn_gwc_sy` / `fn_gwc_slot_sy` (§46.5 (5)) |
| E | Yes | Same as D | The two easternmost columns become a river (water level fixed at 1.5 m). No outfall | Effect of surface flood water dropping into the river and leaving the system |
| F | Yes | Same as D | River + an open outfall at the trunk end (38, 11) (`fn_gwc_outfall`, Cd·A = 0.47 m²) | Conduit head and flooding when the trunk can discharge directly into the river |

The slot_sy = 0.03 of A and B is a "soft" value of the same order as sy.
At the time of the implementation in 2026-08 this was unavoidable as a
compromise with the upper limit of the explicit time step (dt ≤ 0.061 s
from the trunk conveyance). Now that subcycling (§46.5 (4)) exists, run D
and later can use the physically stiffer slot_sy (sy/5) as is (in this
configuration dt = 0.02 s is below the limit of 0.037 s, so the number of
subdivisions is N = 1).

| File | Contents |
|---|---|
| `gen_data.py` | Conversion from pipe specifications to cap / cnd / bot / sy / slot, and generation of all maps in `data_sewer/` (including the river system and outfall maps) |
| `param_A.txt` to `param_F.txt` | Parameters of each run. Output goes to `result_A/` to `result_F/` |
| `plot_sewer.py` | Two figures (`sewer_hybrid_result.png`, `sewer_hybrid_outfall.png`) |

## 3. Running

```bash
python3 gen_data.py                 # generate data_sewer/ (the converted values are printed on screen)
for r in A B C D E F; do ../../bin/encflow param_$r.txt; done   # 70–110 s each (4 cores)
python3 plot_sewer.py               # draw the figures
```

In the output of `gen_data.py`, compare the pipe-full conveyance of the
branch pipes C = 2.08 m³/s, that of the trunk 24.0 m³/s, the pipe-full
capacity of the trunk 1.70 m³/s (gradient 0.005), and the domain runoff of
1.40 m³/s from 60 mm/h of rain. The setting is "a trunk main just barely
thick enough to carry the rain".

## 4. Reading the figures (runs A–D)

**(a) Time series of the water overflowing onto the surface, S_surf.**
During the first 10 minutes of rain, 5–6 mm of rain that cannot enter the
pipes through the inlets ponds on the surface, then is drawn into the
pipes and decreases for a while. Once the pipes are full (about 35 min in
run D), the surface water starts to increase from the water **erupting**
from the inlets and the rain that cannot be absorbed, and nearly levels
off at the end of the rain (1 hour). Runs A (18.2 mm) and B (10.2 mm),
which have a trunk, flood less than run C (21.6 mm) without one, so the
trunk is indeed carrying water. Run D with consistent storage
coefficients, however, gives **36.4 mm**, 2–3.5 times A and B. Because of
their soft slot_sy, A and B were hiding the water that should have
overflowed in underground "phantom storage". **The choice of the scalar
sy (the A ↔ B difference of 8 mm) is of the same size as the effect of the
trunk itself (C − A = 3.4 mm, C − B = 11.4 mm)** and sways the answer.
This is the direct reason the feature for giving sy and slot_sy per cell
(§46.5 (5)) was built.

**(b) Distribution of surface depth at the end of the rain.** On a uniform
slope the surface water flows east and, since all four sides are walls,
ponds at the eastern end (the dashed line is the trunk). Every run has the
same shape of distribution; only the amounts differ. Keep in mind that
this is not an experiment for seeing "which blocks get flooded" but one
for comparing totals and time series.

**(c) Filling ratio of the pipes hgc / cap at the end of the rain.** 1 is
pipe-full. With the soft slot_sy of A and B, the branch pipes (dotted)
hold 3–5 times and the trunk (solid) 1.7–2.3 times the pipe-full volume in
the "slot". The part beyond the pipe volume is non-existent water. With
the stiff slot_sy of D, both trunk and branches stay within 1.5–1.9 times,
and the excess has overflowed onto the surface (that it is still nearly 2
is because sy/5 is still soft; in practice sy/50 is the default. §64).

## 5. Effect of the river and the outfall (runs E, F)

![Comparison of runs D, E and F](../sewer_hybrid_outfall.png)

A–D are closed boxes with walls on all four sides and no outlet for the
pipes. In a real sewer system the end of the trunk opens into a river or
the sea through an **outfall**. In E and F the two easternmost columns are
made a "river" (the sea mask `fn_sw` with the water level fixed at 1.5 m
by the tide module), so that the surface water drops from the cliff into
the river and leaves the system. F additionally places an open outfall at
the trunk end (38, 11) (the receiving head is the water level of the
adjacent river; with a backflow-prevention flap). The trunk invert at its
end is 1.125 m, so the outfall sits slightly above the river surface.

**(a) Water inside the pipes, S_grnd.** In run E, with only the river, the
pipes are full (25 mm) after 30 minutes, and 22 mm stays in the pipes even
after the rain stops (there is no outlet, so it cannot drain). In run F
with the outfall, the water in the pipes stays at most 6 mm and drains to
1 mm within 30 minutes after the rain stops. The effect of **the trunk
being able to discharge into the river** is seen directly.

**(b) Water on the land surface.** S_surf in the Log is the mean over the
land cells only (before 2026-10-22 it also included the water column of
the river cells of the sea mask, so the figure subtracted the t = 0 value
to obtain the land share. That subtraction is no longer needed, and the
figure shows the same values). In run E,
after about 6 mm ponds during the first 10 minutes of rain, the surface
stays nearly dry. The full pipes have their head right around the surface,
carry the rain that enters through the inlets through the pipes to the
downstream end, and **erupt** it from the inlets near the river to drop it
into the river. The network works as "a conveyor passing water while
pipe-full": numerically no flooding occurs, but in reality this is a state
in which every inlet is spouting. In run F, 6–7 mm of water lies on the
land during the rain. Inflow into pipes that are not full follows the weir
type (q = cw·h^1.5), and swallowing 60 mm/h of rain needs about 7 mm of
depth around the inlets. After the rain stops it falls below 1 mm within
30 minutes.

**(c) Longitudinal profile of the trunk filling ratio.** D and E stay at
1.5–1.8 times pipe-full (pressurized in the pseudo slot), unchanged for
3 hours. In F it is 0.1–1.0 at the end of the rain, lower downstream (0.7
near the outfall), and after 3 hours the upstream side is nearly empty
(0.01); only the water set by the river level remains in the 100 m reach
from the outfall (the outfall invert 1.125 m < river level 1.5 m, so the
pipe below the river surface does not empty).

Summarizing where the water goes (out of the total rainfall of 61.0 mm):
in E, 38.6 mm goes from the cliff into the river and 22.4 mm remains in
the pipes; in F, 55.9 mm goes **from the outfall into the river**, 3.8 mm
from the cliff into the river, and 1.3 mm remains in the pipes (recomputed
on 2026-10-22). The trunk of F carries more than 90 % of the rain,
consistent with the estimate pipe-full capacity 1.70 m³/s ≳ runoff
1.40 m³/s.

## 6. Findings (numbers)

| Run | Final S_surf (surface, mm) | Final S_grnd (in pipes, mm) | S_total (mm) | Remarks |
|---|---:|---:|---:|---|
| A | 18.2 | 42.8 | 61.0 | Flooding underestimated by phantom storage |
| B | 10.2 | 50.8 | 61.0 | Ditto (more strongly) |
| C | 21.6 | 39.4 | 61.0 | No trunk |
| D | 36.4 | 24.6 | 61.0 | Consistent storage coefficients |
| E | 0.0 (land) | 22.4 | 22.4 | With river. 38.6 mm from the cliff into the river |
| F | 0.1 (land) | 1.2 | 1.3 | River + outfall. 55.9 mm (4459 m³) from the outfall into the river, 3.8 mm from the cliff |

- In the closed runs A–D, S_total = the total rainfall of 61.0 mm is
  conserved to a rounding of 1e-13. The S columns of the Log in E and F are
  means over the land (798 cells), excluding the river cells of the sea
  mask (before 2026-10-22 the water column of the river cells, 1.5 m × 42
  cells divided by the land area = 78.9 mm, was added on top), and S_total
  decreases only by the water that left into the river (the drop from the
  cliff and the outfall discharge). The cumulative volume discharged from
  the outfall into the river is printed on screen at the end of the run
  (F: "outfall discharge total = 4.4591E+03 m3").
- The trunk conveyance governs the upper limit of the explicit time step
  (24 m³/s per edge; dt ≤ 0.061 s at Δx = 10 m, and 0.037 s with the stiff
  slot_sy). This example stays within the limit at dt = 0.02 s, but with a
  stiffer slot_sy or a finer grid the subcycling subdivides the step
  automatically ("subcycles = N" on screen).
- The same configuration turned into a short 30-minute regression test is
  [test/sewer_wq](../../../test/sewer_wq/en/README.md), which adds the
  water-quality module and follows the spread of coliform bacteria in the
  erupted water as sewage. Drainage of a system below sea level (negative
  inverts, sea outfalls, pumping stations) is in
  [test/coastal_drain](../../../test/coastal_drain/en/README.md), and
  groundwater collection by a gallery in
  [examples/qanat](../../qanat/en/README.md).

## 7. What this experiment decided (design record)

The experiment was run on 2026-08-23 and became the basis of the following
decisions in developer.md §46.5. All of them have since been implemented.

1. **The conversion from pipe specifications to parameters is done in
   preprocessing** (code unchanged). `pipe_params()` in gen_data.py is the
   model to follow.
2. **Open outfalls** (§46.5 (3), (8b) → `fn_gwc_outfall`). Before the
   implementation, the only path from the conduits to the surface was the
   eruption while pressurized, and the water in the pipes did not drain
   after the rain (S_grnd of A–D stays at 25–51 mm). Run F demonstrates
   this feature.
3. **Per-cell sy and slot_sy** (§46.5 (5) → `fn_gwc_sy` / `fn_gwc_slot_sy`).
   The basis was that the A ↔ B difference was of the same order as the
   effect of the trunk. Run D demonstrates it.
4. **Subcycling** (§46.5 (4)). The prerequisite for being able to use a
   stiff slot_sy.
5. **Trunk and branch pipes coexisting in the same instance works
   mechanically.** The conveyance between cells takes the smaller of the
   two at the edge (the min convention), so the branch → trunk connection
   being limited on the branch side is represented naturally. Multiple
   instances are unnecessary unless separate systems must be used in the
   same cell (sewers × bedrock).
6. At the time, negative values in the invert-elevation map were rejected,
   so the ground datum was raised by +8 m to avoid them (`z_of` in
   gen_data.py). Negative values are now accepted (§46.5 (7)), and inverts
   below sea level can be given as they are.

## 8. Limitations and extensions

- Being an idealized experiment with a uniform gradient and closed
  boundaries, it is not suited to verifying the spatial pattern of
  inundation. For a real city, combine elevation data, per-cell maps
  converted from the sewer network drawings, and a receiving river or sea
  (the procedure is in the urban-sewer section of
  [users_guide/gwflow.md](../../../docs/en/users_guide/gwflow.md)).
- Since the pipes are represented by a single head, the head difference
  between trunk and branch pipes within one cell (the loss in the
  connecting pipe) cannot be represented. Whether to build a quasi-1-D
  "buried channel" module with a cross-section shape will be decided once
  a comparison with an SWMM reference solution shows a deficiency (end of
  §46.5).

## Related documents

- [docs/users_guide/gwflow.md](../../../docs/en/users_guide/gwflow.md) — all parameters of the conduit continuum layer (`&list_gwflow_conduit`), outfalls and conversion formulas
- [docs/users_guide/tide.md](../../../docs/en/users_guide/tide.md) — the tide module that fixes the river or sea level (runs E and F)
- developer.md §46.5 (decisions on the extension policy and implementation record), §64 (default values) (in Japanese)
- [docs/gwconduit_plan.md](../../../docs/gwconduit_plan.md) (in Japanese) — the plan for the conduit layer (staged proposal)
