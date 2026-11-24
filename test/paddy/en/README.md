# test/paddy — verification of paddy tanks and outlet device laws of paddy-field dams

> English mirror of test/paddy/README.md. The Japanese file is the master copy.

This case verifies the subgrid tanks on the paddy area fraction of each cell and the device laws of the outlets of
[paddy-field dams](../../../docs/en/users_guide/paddy.md) (`fn_paddy`; developer.md §119). The water balance of one
plot has exact and reference solutions, so the mean ponding depths in the ledger `paddy.csv` of the model are
compared with them. `Check_paddy.py` rewrites the device laws independently (the chord-width integral of a
circular hole is computed directly by Gauss–Legendre quadrature, while the model uses a table and an expansion)
and builds both a reference solution with the same explicit scheme and the exact solutions of the ordinary
differential equations.

## Configuration

| Item | Value |
|---|---|
| Domain and grid | 10 × 8 cells (Δx = Δy = 10 m), flat ground (z = 0). Two rows per rank even with np = 4 |
| Boundaries | free outflow on all four sides (the drained water leaves the domain at once; the surface water depth is below 1.5 cm and the outlets are not submerged). param_mix.txt, param_wash.txt and param_splash.txt have walls on all four sides |
| Paddy fields | every cell is a paddy field (area fraction 1). param_mix.txt has maps that change the area fraction, adoption ratio and void ratio by column |
| Time | dt = 2 s, ledger every 600 s |

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

In addition, `Run.sh` checks bit identity between a run saved at 6 h and restarted to 12 h and a continuous run
(`restart`), and the following stops: paddy fields on a channel cell, area fraction > void ratio, adoption ratio out
of range, combination with water quality (fn_wq), outflow control plate given for type 0, area fraction given both as a
map and as a uniform value, ponding depth before the run > levee height, and restart with the feature disabled while the
saved file remains.

| File | Contents |
|---|---|
| `Run.sh` | compares Log.txt of param.txt with the reference (ULP = 0) → checks of each setting, save → restart and stops |
| `Run_MPI.sh [np]` | the same comparison with MPI (ULP = 0 against the serial reference), byte identity of paddy.csv, maps and paddy.dat with np = 1, conservation in the closed domain, the two checks of raindrop erosion (the ground elevation also byte-identical with np = 1), stops found by rank 0 and in the bands |
| `Check_paddy.py` | checks (Python standard library only) |
| `data_paddy/` | maps for param_mix.txt and for the checks of stops |

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

The difference from the exact solutions is the time-step error of the explicit scheme (dt = 2 s; the time scale of the
ponding depth is hours). The difference for raindrop erosion is the rounding when the ground elevation is written as a
single-precision binary. MPI np = 1, 2, 4 agree with the serial reference with ULP = 0, and paddy.csv is byte-identical
with np = 1. With -Og -fcheck=all all checks also pass, and np = 2 is bit-identical with the serial run.

The reference (Log.txt) was placed provisionally on the basis of the analytic checks passing. It is confirmed by a
human visual check (handoff 00ae).

## What this case does not check

- Situations strongly coupled with the shallow water flow (deep surface water with the outlets of many cells submerged
  or stopped): param_mix.txt checks water conservation, but there is no check of the accuracy of the submerged
  formulas themselves.
- The size of the effect in real basins and drainage districts (the example is planned; docs/paddy_plan.md §8).
