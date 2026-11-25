# test/paddy — verification of paddy tanks, resolved plots and outlet device laws of paddy-field dams

> English mirror of test/paddy/README.md. The Japanese file is the master copy.

This case verifies the subgrid tanks on the paddy area fraction of each cell and the device laws of the outlets of
[paddy-field dams](../../../docs/en/users_guide/paddy.md) (`fn_paddy`; developer.md §119). The water balance of one
plot has exact and reference solutions, so the mean ponding depths in the ledger `paddy.csv` of the model are
compared with them. `Check_paddy.py` rewrites the device laws independently (the chord-width integral of a
circular hole is computed directly by Gauss–Legendre quadrature, while the model uses a table and an expansion)
and builds both a reference solution with the same explicit scheme and the exact solutions of the ordinary
differential equations. For representation B, which resolves the plots on a grid of 5–10 m (`fn_pd_plot`;
developer.md §119.8), the case checks the solution of the same single plot and the water tightness of the levees, the
overflow, the backflow and the conservation of water with inflow from outside.

## Configuration

| Item | Value |
|---|---|
| Domain and grid | 10 × 8 cells (Δx = Δy = 10 m), flat ground (z = 0). Two rows per rank even with np = 4 |
| Boundaries | free outflow on all four sides (the drained water leaves the domain at once; the surface water depth is below 1.5 cm and the outlets are not submerged). param_mix.txt, param_wash.txt, param_splash.txt, param_tw_back.txt, param_tw_fill.txt and param_tw_flood.txt have walls on all four sides |
| Paddy fields | every cell is a paddy field (area fraction 1). param_mix.txt has maps that change the area fraction, adoption ratio and void ratio by column |
| Time | dt = 2 s, ledger every 600 s |
| Resolved plots (`param_b_*.txt`) | Δx = Δy = 5 m, 16 × 32, 20 × 16, 20 × 20 and 20 × 12 cells, dt = 0.5 s. The inputs (plot numbers, outlets, classes, ground, initial depths) are made by `make_plots.py` in `data_paddy/b_*.txt` at the start of `Run.sh` and `Run_MPI.sh` (ignored by git) |

| Settings | Contents | Check (`Check_paddy.py`) |
|---|---|---|
| `param.txt` | drainage over a water-level board only (rectangular weir; crest 0.03 m, width 0.30 m, C = 0.6) for 12 h, from a ponding depth of 0.25 m, plot 3000 m² | `weir`: exact solution (H − z)^−1/2 = (H0 − z)^−1/2 + (k/2A) t and the reference solution of the explicit scheme, closure of the ledger, outflow = decrease of storage |
| `param_open.txt` | a V-notch (60°) and a circular hole (φ50) of the integrated type in the same cells with adoption ratio 0.5; plot 500 m², 24 h | `open`: exact solution H^−3/2 = H0^−3/2 + (3/2)(k/A) t for the V-notch, reference solution for the circle (H > 0.01 m) |
| `param_sep.txt` | a rectangular hole (gate-shaped; 12 cm × 5 cm, bottom 0.03 m) and the separated type (water-level board + φ50 + overflow of the outflow control plate with crest 0.20 m) | `sep`: reference solutions. The separated type passes both the interval with the overflow and the interval with the hole only |
| `param_steady.txt` | constant rain of 20 mm/h for 48 h; normal outlets and separated type, decrease in depth 5 mm/d | `steady`: equilibrium H* = z + ((r − perc)A/k)^(2/3) for the normal outlets; for the paddy-field dams the maximum flow of the hole is below the rain → full, rate of overflow = area × ((r − perc) − Q(levee height)/A) |
| `param_spill.txt` | 80 mm/h for 6 h, then no rain for 6 h; all separated type (default device) | `spill`: ponding depth ≤ levee height, rate of overflow while full, falls below the levee height after the rain, ledger |
| `param_mix.txt` | maps of area fraction, adoption ratio and void ratio of buildings, walls on all four sides, 10 mm/h for 2 h | `mix`: paddy area of each class, water conservation against the same run without paddy fields (increase of S + decrease in depth = rain), ledger |
| `param_dflt.txt` | minimal input with the paddy area fraction only | `dflt`: defaults adopted and shown (no defaults shown for an absent class). Run.sh also checks bit identity with the same values given explicitly |
| `param_wash.txt` | combination with landform change, part 1: a box with walls on all four sides filled with water 0.05 m deep, 50 mm/h for 1 h. Only the raindrop term of hillslope erosion on wet cells (`wash_kr` = 0.01, no sheet erosion, settling of the suspended sediment practically stopped). The area fraction is the same map by column as param_mix.txt | `wash`: on every cell, lowering of the ground = (1 − area fraction) × raindrop erosion coefficient × rain × time (the rain on the paddy part falls into the ponded water on the fields; developer.md §119.5). No erosion on cells with area fraction 1 |
| `param_splash.txt` | combination with landform change, part 2: a box where the infiltration capacity (Green-Ampt 72 mm/h) exceeds the rain of 30 mm/h and every cell stays dry, with only the raindrop term of dry-slope erosion (`spl_kr` = 0.003, morfac = 5) | `splash`: on every cell, lowering of the ground = (1 − area fraction) × `spl_kr` × rain × time × morfac |
| `param_tw_back.txt` | two-way mode (`f_pd_exchange = 1`), part 1: a box with walls on all four sides, area fraction 0.6 in every cell. Surface water depth 0.15 m (below the levees), empty paddy fields. Water of the drains flows back into the paddy fields over the water-level board for 4 h | `tw_back`: ponding depth = reference solution of the same explicit scheme (step-shaped cross-section, device law in both directions, caps), conservation of S, equilibrium level 0.06 m |
| `param_tw_fill.txt` | two-way mode, part 2: surface water depth 0.50 m (above the levees), ponding depth 0.03 m | `tw_fill`: in the first step the water above the levees fills the paddy fields (ponding depth = levee height, surface water depth 0.338 m, inflow over the levees 1296 m³), S = depth of the merged water (no double counting) |
| `param_tw_flood.txt` | two-way mode, part 3: maps of area fraction 0–0.9 (frac_tw.txt) and adoption ratio, flood water of 1.0 m³/s for 2 h from a cell in the west column | `tw_flood`: increase of S + decrease in depth = flood water let in, inflow through the outlets and over the levees, all paddy fields full at the end |
| `param_tw_drain.txt` | two-way mode, part 4: from surface water depth 0.50 m and full paddy fields, the flood recedes through free outflow on all four sides for 12 h (adoption ratio 0.5) | `tw_drain`: ponding depth ≤ levee height and falling, normal outlets drain faster. Run.sh also checks bit identity between save at 6 h → restart and a continuous run |
| `param_b_drain.txt` | resolved plots, part 1: two plots of 10 × 12 cells (3000 m²; class 1 = water-level board, class 2 = integrated type with a circular hole φ50) drain into the drain on the east (ground −0.5 m, free outflow on the east side) for 12 h, from a ponding depth of 0.25 m | `b_drain`: mean depth of each class agrees with the exact (weir) and reference (hole, RK4) solutions of a single plot, closure of the ledger, outlet outflow = water drained from the plots, no flow over the levees |
| `param_b_tight.txt` | resolved plots, part 2: five plots without outlets (a diagonal staircase boundary, two pools inside a plot touching at a checkerboard corner, two cells of a plot on a diagonal inside another plot), with different initial depths in plots and pools, 20 mm/h for 1 h | `b_tight`: in every cell the change of depth = rain (water does not pass the levees or checkerboard corners), closure of the ledger |
| `param_b_over.txt` | resolved plots, part 3: 60 mm/h for 1 h on a plot with ponding depth 0.28 m in a closed domain (overflow of the levees), decrease in depth 5 mm/d | `b_over`: increase of S + decrease in depth = rain, outflow over the levees > 0, falls to just above the crest after the rain |
| `param_b_back.txt` | resolved plots, part 4: outside level 0.20 m (below the crest of 0.30 m), backflow through the outlet into a plot at 0.05 m for 12 h | `b_back`: S conserved, the levels of all cells even out at the end (0.1625 m from the volume balance), gain of plot water = net inflow. Run.sh also checks bit identity between save at 6 h → restart and a continuous run |
| `param_b_ext.txt` | resolved plots, part 5: outside level 0.40 m (above the crest), 2 h | `b_ext`: inflow over the levees > 0, levels even out (0.3125 m), S conserved |
| `param_b_bank.txt` | resolved plots, part 6: a channel (bank crest = ground + 0.1 m) next to the east of the plot, outside level 0.20 m | `b_bank`: the plot depth stays 0.05 m (the shared edge has the levee crest of 0.30 m; with the bank crest alone water would flow in) |
| `param_b_chain.txt` | resolved plots, part 7: the outlet of plot A (depth 0.25 m) points to the neighbouring plot B (0) (drainage from plot to plot), 6 h | `b_chain`: both even out at 0.125 m, loss of A = gain of B, outlet outflow = inflow, S conserved |
| `param_wq_a.txt` | water quality (`fn_wq`), part 1: the drainage of param.txt plus a concentration of the ponding before the run `pd_wq_c0` = 10 mg/L, first-order decay with a half-life of 6 h, and a decrease in depth of 5 mm/d | `wq_a`: tank concentration = 10 × 2^(−t/6 h) (outlet flow and decrease in depth leave at the tank concentration and do not change it), mass balance of wq.csv (tanks and surface + outflow through open edges + decay + substance taken out by the decrease in depth = initial mass). Run.sh also checks agreement between save at 6 h → restart and a continuous run, and the stop of a restart without water quality |
| `param_wq_rain.txt` | water quality, part 2: param_steady.txt (constant rain of 20 mm/h for 48 h) with a rain concentration of 2 mg/L | `wq_rain`: the tank concentrations of both classes approach 2 mg/L monotonically, mass balance (input = substance of the rain) |
| `param_wq_tw.txt` | water quality, part 3: param_tw_back.txt (backflow in the two-way mode) with an initial concentration `wq_c0` = 5 mg/L of the surface water | `wq_tw`: concentration of the water entering by backflow = initial surface concentration (initial mass / volume of the surface water), mass conserved in the closed box |
| `param_wq_b.txt` | water quality, part 4: param_b_over.txt (overflow of resolved plots, closed domain) with a concentration of the ponding before the run of 10 mg/L and a rain concentration of 2 mg/L | `wq_b`: concentration of the plot water between 2 and 10 mg/L, mass balance (substance taken out by the decrease in depth > 0) |
| `param_sed_tw.txt` | sediment (landform change `fn_geomorph`), part 1: param_tw_flood.txt (two-way mode, 1.0 m³/s of flood water for 2 h) with suspended sediment at a volume concentration of 0.002 in the flood water (no entrainment, practically no settling) | `sed_tw`: solids conserved (suspended + rise of the bed × (1 − porosity) = sediment fed in), the suspended sediment of the water entering the tanks settles only on the paddy cells, in the amount of sed in paddy.csv. Run.sh also checks bit identity between save at 1 h → restart and a continuous run with a landform step of 7 s, and the stop of a restart without suspended sediment |
| `param_b_sed.txt` | sediment, part 2: param_b_ext.txt (the outside level rises above the crest and water flows into the plot for 2 h) with bed load (d50 1 mm, soil depth 1 m) | `b_sed`: total bed change of the plot = 0 (bed load does not cross the edges of the levees and outlets), bed load acts inside the plot |

In addition, `Run.sh` checks bit identity between a run saved at 6 h and restarted to 12 h and a continuous run
(`restart`), and the following stops: paddy fields on a channel cell, area fraction > void ratio, adoption ratio out
of range, outflow control plate given for type 0, area fraction given both as a
map and as a uniform value, ponding depth before the run > levee height, restart with the feature disabled while the
saved file remains, and in the two-way mode a non-paddy share below 0.05, a pond cell, combination with debris flows
or the non-hydrostatic correction, restart with a different exchange mode from the saved state, and restart with
suspended sediment enabled differently from the saved state; and for the resolved
plots, input errors (a plot cell on the outer rows and columns, an outlet pointing to the same plot or given on a cell that
is not a plot cell, different classes within a plot, a non-integer plot number, an outlet pointing to a cell higher than
the crest, outlets facing each other), combination with inputs of A only, with the non-hydrostatic correction or with
debris flows, restart with a different representation from the saved state, and restart with water quality enabled differently from
the saved state.

| File | Contents |
|---|---|
| `Run.sh` | compares Log.txt of param.txt with the reference (ULP = 0) → checks of each setting, save → restart and stops |
| `Run_MPI.sh [np]` | the same comparison with MPI (ULP = 0 against the serial reference), byte identity of paddy.csv, maps and paddy.dat with np = 1, conservation in the closed domain, the two checks of raindrop erosion (the ground elevation also byte-identical with np = 1), the three checks of the two-way mode (paddy.csv, Log, depth and ponding depth byte-identical with np = 1), the seven checks of the resolved plots (paddy.csv, Log and depth byte-identical with np = 1; plots, outlets and checkerboard corners cross the band boundaries), the three checks of water quality (paddy.csv, Log and wq.csv byte-identical with np = 1) and save → restart of the pools, the two checks of sediment (paddy.csv, Log and ground elevation byte-identical with np = 1), stops found by rank 0 and in the bands |
| `Check_paddy.py` | checks (Python standard library only) |
| `make_plots.py` | makes the inputs of the resolved plots (Python standard library only) |
| `data_paddy/` | maps for param_mix.txt and param_tw_flood.txt and for the checks of stops (the `b_*.txt` of the resolved plots are made by `make_plots.py`) |

## Results (2026-11-24; gfortran 13.3, -Ofast, 4 threads)

| Check | Max relative difference | Tolerance |
|---|---:|---:|
| water-level board vs exact solution | 9.2×10⁻⁵ | 2×10⁻³ |
| water-level board vs reference of the explicit scheme | 9.9×10⁻¹⁶ | 1×10⁻⁹ |
| V-notch vs exact solution | 1.3×10⁻⁴ | 2×10⁻³ |
| V-notch vs reference solution | 7.0×10⁻¹⁶ | 1×10⁻⁷ |
| circular hole vs reference (table and expansion vs direct quadrature) | 1.1×10⁻⁸ | 1×10⁻⁶ |
| rectangular hole vs reference solution | 1.9×10⁻¹⁵ | 1×10⁻⁷ |
| separated type vs reference solution | 3.2×10⁻⁸ | 1×10⁻⁶ |
| equilibrium H* under constant rain | 7.6×10⁻⁷ | 5×10⁻⁶ |
| water conservation in the closed domain | 6.7×10⁻¹⁵ m | 1×10⁻¹² m |
| raindrop erosion (wet slopes) vs (1 − area fraction) × analytic solution | 4.7×10⁻⁸ | 1×10⁻⁶ |
| raindrop erosion (dry slopes) vs (1 − area fraction) × analytic solution | 2.7×10⁻⁸ | 1×10⁻⁶ |
| two-way: backflow through the outlets vs reference solution | 8.9×10⁻¹⁶ | 1×10⁻⁹ |
| two-way: water conservation with incoming flood water | 8.3×10⁻¹⁴ m | 1×10⁻⁹ of 0.9 m |
| resolved plots: water-level board vs exact solution | 8.7×10⁻⁴ | 2×10⁻³ |
| resolved plots: circular hole vs reference solution | 2.0×10⁻⁷ | 2×10⁻³ |
| resolved plots: water tightness of the levees (change of depth − rain) | 7.3×10⁻⁹ m | 1×10⁻⁶ m |
| resolved plots: water conservation in the closed domain with overflow | 2.7×10⁻¹⁴ m | 1×10⁻¹² m |
| resolved plots: difference of levels after backflow and inflow from outside | 2.4×10⁻⁸ m and 5.4×10⁻⁷ m | 2×10⁻³ m |
| water quality: first-order decay of the tank concentration vs exact solution | 4.4×10⁻¹³ | 1×10⁻⁹ |
| water quality: concentration of the water entering by backflow vs initial surface concentration | 0 | 1×10⁻⁶ |
| water quality: mass balance of wq.csv (largest of the 4 settings) | 5.1×10⁻⁸ | 1×10⁻⁶ |
| sediment: conservation of solids (suspended + deposited vs sediment fed in) | 1.7×10⁻⁹ | 1×10⁻⁶ |
| sediment: total bed change of the plot (bed load) | 9.1×10⁻¹² m | 1×10⁻⁶ of the movement inside the plot (3.2×10⁻² m) |

The difference from the exact solutions is the time-step error of the explicit scheme (dt = 2 s; the time scale of the
ponding depth is hours). The difference of the weir of the resolved plots is the drawdown of the water surface where the
flow gathers to the outlet cell (a systematic difference of about 3×10⁻⁵ m; the resolved plot drains a little more
slowly). The results of the resolved plots are from 2026-11-25. The results of water quality and sediment are also from 2026-11-25; the
difference of the mass balance is the rounding to the 8 significant digits of wq.csv, and that of the conservation of
solids the rounding of the single-precision binaries of the ground elevation and the suspended sediment. The difference for raindrop erosion
is the rounding when the ground elevation is written as a single-precision binary. MPI np = 1, 2, 4 agree with the serial reference with ULP = 0, and paddy.csv is byte-identical
with np = 1. With -Og -fcheck=all all checks also pass, and np = 2 is bit-identical with the serial run.

The reference (Log.txt) was placed provisionally on the basis of the analytic checks passing. It is confirmed by a
human visual check (handoff 00ae).

## What this case does not check

- Situations strongly coupled with the shallow water flow (deep surface water with the outlets of many cells submerged
  or stopped): param_mix.txt checks water conservation, but there is no check of the accuracy of the submerged
  formulas themselves.
- The size of the effect in real basins and drainage districts (the example [examples/paddy_dam](../../../examples/paddy_dam/en/README.md) uses schematic values on synthetic terrain).
- Resolved plots: outlets pointing to channel cells (without banks), the stop for outlets on diagonals with
  p_diagratio = 0, and the stops for combination with landform change, evapotranspiration and groundwater (only the
  messages exist; the stops are not checked).
- Water quality: settling in the pools of the tanks (`wq_vs`), combination with two-phase partitioning (`wq_kd`), and
  comparison of the concentrations of A and B for the same district.
- Sediment: deposit in the tanks while entrainment and settling of suspended sediment act (the check stops
  entrainment), and hillslope creep and slope failure at the levees.
