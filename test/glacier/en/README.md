# test/glacier — glacier module: Halfar dome similarity solution, cirque-formation smoke test, and isotropy of the avalanche redistribution

> English mirror of test/glacier/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This is the verification case of the glacier module (`fn_glacier`,
[the glacier chapter of the users guide](../../../docs/en/users_guide/glacier.md)).
It consists of four configurations (docs/glacier_plan.md §7, developer.md §45).

1. **Halfar dome** (`param.txt`): an ice cap on a flat bed with zero mass
   balance spreads by shallow-ice-approximation (SIA) flow. A quantitative
   benchmark against the similarity solution of Halfar (1983).
2. **Cirque-formation smoke test** (`param_cirque.txt`): a conical mountain is
   given a temperature lapse rate and elevation-dependent precipitation, and
   the whole chain snow → avalanche redistribution → firnification → SIA flow
   + Weertman sliding → glacial erosion is enabled, to confirm that "a glacier
   forms and erosion occurs beneath it" and that the conserved quantities are
   sound.
3. **Equivalence check of the defaults** (`param_min.txt` / `param_minx.txt`):
   the save and the Log of the configuration that omits four material
   constants and of the configuration that writes them explicitly are
   byte-identical (§65).
4. **Isotropy of the avalanche redistribution** (`param_ava.txt`): uniform
   snow (SWE 1000 mm) is placed over the whole conical mountain of
   configuration 2 and only the avalanche redistribution runs for one day
   (24 times, once an hour). Confirms that the snow amount on a circle around
   the summit does not depend on the direction (no bias from the grid
   orientation) and that the water equivalent is conserved (developer.md
   §45.2).

## Configuration

| Item | Halfar dome | Cirque formation |
|---|---|---|
| Domain and grid | 1525 m × 1525 m, 61 × 61 cells (Δx = 25 m), flat | 81 × 81 cells, conical mountain (`data/zcone.txt`) |
| Initial ice thickness | Similarity solution at t = t₀, H(r) = H₀ [1 − (r/R₀)^{4/3}]^{3/7}, H₀ = 200 m, R₀ = 600 m (`data/hi0.txt`) | None (formed from snow by firnification) |
| Meteorology | Constant temperature −30 ℃ (no melt or precipitation; zero mass balance) | With the temperature lapse rate the summit side receives snow; precipitation is scaled with elevation, more toward the summit |
| Flow | SIA, Glen A = 1e-16 Pa⁻³ yr⁻¹ (n = 3) | SIA + Weertman sliding (gl_as = 1e-13) + erosion (gl_kg = 1e-4). The firnification time constant is made tiny for acceleration |
| Time | dt = 60 s, 1 day. Landform-time factor gl_morfac = 80 → flow for 80 days ≈ 2 t₀ (t₀ = 40.1 days) | dt = 30 s, 1 day × 500 ≈ 1.4 years |

Halfar similarity solution: H(r, t) = H₀ (t₀/t)^{1/9} [1 − ((t₀/t)^{1/18} r/R₀)^{4/3}]^{3/7},
t₀ = (1/(18Γ)) (7/4)³ R₀⁴/H₀⁷, Γ = 2A(ρ_i g)³/(n + 2). Advancing 80 days of
landform time from the initial state (t₀) gives t ≈ 3 t₀, where the central
thickness goes from 200 to 177 m and the radius spreads from 600 to 640 m.

| File | Contents |
|---|---|
| `Make_input.py` | Generates `data/hi0.txt` (Halfar initial ice thickness) and `data/zcone.txt` (conical mountain) |
| `Check_halfar.py` | Judges the mean, maximum and central errors of the final ice thickness Hi9998 against the similarity solution, the ratio of the ice volumes in the sectors along the grid axes and the diagonals (isotropy), and the conservation of S_total (water equivalent of the ice) |
| `Check_cirque.py` | Judges glacier formation (max Hi > 1 m), subglacial erosion (dz < −0.01 m), no uplift, and no NaN |
| `Check_ava.py` | Configuration 4: judges the coefficient of variation of SWE on circles of radius 800–1600 m (< 0.08), the mean SWE on the 400 m circle (below 90% of the initial value, i.e. the redistribution works), and the conservation of the water equivalent |
| `Fig.py` | Draws the figures `en/figs/*.png` below (`python3 Fig.py en`; `figs/*.png` are the Japanese versions) |

## Running

```bash
make
./Run.sh          # generate inputs → Halfar → cirque → avalanche → the 3 Checks → equivalence check of the defaults. PASS when all pass
./Run_MPI.sh 4
python3 Fig.py en # en/figs/halfar.png, en/figs/cirque.png, en/figs/avalanche.png
```

## Figures

![Halfar dome](figs/halfar.png)

Left: the ice thickness along the central row. The computation after 80 days of
flow (blue dots) from the initial state (grey) lies over the similarity
solution (black). Right: the distribution of the computed ice thickness minus
the similarity solution. Most of the error is concentrated in the one-cell
width at the ice margin (the similarity solution has an infinite gradient at
the margin, so even a half-cell positional offset gives a thickness difference
of tens of metres). More than two cells inside the margin the error is −0.8 to
+0.4 m, with no difference between the grid axes and the diagonals. Before the
fix of 2026-11-03 the diffusivity was evaluated with the gradient normal to the
edge only, and the interior showed a pattern of −8.9 to +6.0 m with opposite
signs along the grid axes and the diagonals (developer.md §45.1).

![Cirque-formation smoke test](figs/cirque.png)

Left: the initial conical mountain. Centre: the ice thickness after 1 day
(1.4 years of landform time). The whole mountain is covered with ice (maximum
93 m). Right: the terrain change. Negative everywhere (erosion only, no
uplift). This is not a quantitative benchmark but a figure for checking the
connectivity of the whole chain and the soundness of the signs. The mountain
is a cone, so the result is close to axisymmetric (the square outer rim is the
effect of the domain edges). On circles 800–1600 m from the summit, the
coefficient of variation with direction is 0.001–0.004 for the ice thickness
and 0.008–0.018 for the erosion depth. Before the two fixes of 2026-11-03,
radial streaks from the grid orientation appeared: streaks along the 4 grid
axes from the distortion of the SIA diffusivity (developer.md §45.1; without
avalanches, the ice along the grid axes was 19% thicker than along the
diagonals and the erosion 42% deeper), and streaks along the 8 directions of
the grid axes and diagonals because the avalanche redistribution sent snow to
the single steepest of the 8 neighbours (§45.2; coefficients of variation
0.012–0.030 for the ice thickness and 0.073–0.088 for the erosion depth).

![Isotropy of the avalanche redistribution](figs/avalanche.png)

Configuration 4. Left: the SWE after 1 day. The snow moves down the slope,
decreases near the summit, and collects at the domain edges (where the domain
cuts off the foot of the cone). Right: the SWE on circles around the summit.
The lines are nearly flat, with coefficients of variation of 0.017–0.042 with
direction. Narrow peaks along the grid axes and diagonals (0°, 45°, 90°, ...)
remain, as does a slope rising from one grid axis to the next. One reason is
that on a perfectly symmetric cone, facets with the same slope occur on the
symmetry lines and at the summit, and the rule of taking the first of them
breaks the symmetry (remaining limitations of developer.md §45.2). Before the
fix, when the snow went to the single steepest of the 8 neighbours, 1000 mm of
snow remained along the grid axes and diagonals and the amount fell to 100 mm
in the directions in between (coefficients of variation 0.230–0.350).

## Findings

| Check | Computed value | Criterion | Verdict |
|---|---|---|---|
| Halfar mean absolute error | 0.32 m (0.16% of H₀) | < 4 m | PASS |
| Halfar maximum absolute error | 12.5 m (ice margin) | < 45 m (equivalent to a 1.5-cell offset of the margin) | PASS |
| Halfar central error | 0.13 m | < 6 m (23 m without flow) | PASS |
| Halfar isotropy (ratio of the ice volumes in the diagonal and axis sectors, relative to the analytic ratio) | +0.59% | < 2% (−5.49% with the code before the fix) | PASS |
| Relative change of the ice volume S_total | ~1e-15 | Machine precision | PASS |
| Cirque: max Hi / min dz / max dz | 92.7 m / −0.012 m / 0 | > 1 m / < −0.01 m / ≤ 0 | PASS |
| Avalanche: coefficient of variation of SWE on circles of radius 800–1600 m | 0.017–0.042 | < 0.08 (0.230–0.350 with the code before the fix) | PASS |
| Avalanche: mean SWE on the 400 m circle | 408 mm | < 900 mm (90% of the initial 1000 mm) | PASS |
| Avalanche: relative change of the water equivalent S_total | 0 (unchanged in all displayed digits) | < 1e-12 | PASS |
| Equivalence check of the defaults | save and Log byte-identical, 4 "(default)" lines | — | PASS |

- The SIA flow agrees with the similarity solution to 0.16% of H₀ on average,
  and the ice volume is conserved at machine precision owing to the
  antisymmetric flux accounting. Before the fix of 2026-11-03 (the diffusivity
  is evaluated with the magnitude of the gradient at the edge; developer.md
  §45.1), the mean error was 1.2%, the central error 4.7 m and the maximum
  error 38.6 m, and the diagonal sectors held 5.5% less ice.
- The cirque formation is a connectivity check that "a glacier forms and the
  upper part of the mountain is eroded"; the eroded material is discharged out
  of the system (the WARNING line on the screen gives its amount;
  glacier_plan.md §7 "known compromises").
- Ice temperature and polythermal structure, calving, subglacial hydrology and
  the like are not included. A long-term case that quantitatively confirms
  cirque formation on the 10⁴-year scale is a candidate for future extension
  (ibid. §7).

## Related documents

- [docs/users_guide/glacier.md](../../../docs/en/users_guide/glacier.md) — parameters of `&list_glacier`, recommended values
- [docs/glacier_plan.md](../../../docs/glacier_plan.md) (in Japanese) — design plan, §7 verification and known compromises
- developer.md §45 (implementation of the glacier module), §65 (preparation of the defaults)
