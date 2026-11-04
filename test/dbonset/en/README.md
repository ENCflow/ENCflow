# test/dbonset — check that rest and onset of motion under the yield do not depend on the slope direction

> English mirror of test/dbonset/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This is the verification case of **rest and onset of motion** under the yield
(Coulomb friction; $`a_y = g_e\tan\phi\,sC/(1+sC)`$ of `f_dbres = 1`) in the
mixture flow (`f_debris = 1` of `&list_geomorph`; debris flows, avalanches,
pyroclastic flows and the like) (developer.md §28.16). A layer laid over the
whole of a uniform slope stays at rest if the slope G is smaller than the yield
slope μ = a_y/g_e, and slides as one body if it is larger. The case checks,
against the analytic solution of a rigid sliding block, that this threshold and
the speed and direction after the onset are the same for every combination of
the downslope direction (0°, 22.5° and 45° from the x axis of the grid) and the
8- or 4-neighbour stencil. Pass or fail is decided by the self-check
`Check_dbonset.py`, not by comparison with a reference (the same type as
test/curvature).

## Setup

| Item | Value |
|---|---|
| Terrain | A uniform slope 60 m square (slope G, downslope direction θ), walls on all four sides (`make_init.py` writes `d_<case>/z.txt`) |
| Grid | 60 × 60 cells (Δx = 1 m). 8-neighbour (default `p_diagratio`) and 4-neighbour (`p_diagratio = 0`) |
| Layer | A failure depth of 1 m over the whole area (`fn_dbinit`). `db_reltime = 0` fluidizes it at the start of the run and `db_relsat = 1` fills the pores with water (mixture concentration C = C* = 0.6) |
| Flow law | `f_dbed = 0` (no exchange with the bed; C is kept), `f_dbres = 1` (φ = 35°, s = 1.65 → μ = tanφ sC/(1+sC) = 0.3483), Manning roughness 0.01 (hardly affects the sliding of the interior), `f_dbstop = 0`, `db_vstop = 0.05` m/s |
| Cases | 18 cases of G = 0.9 μ, 1.1 μ and 1.3 μ × θ = 0°, 22.5° and 45° × 8- and 4-neighbour (a name such as `r1p1_t22p5_n8` means 1.1 μ, 22.5°, 8-neighbour) |
| Time | dt = 0.0005 s, 2 s. The final state is saved to `save_<case>/state.dat` |

Away from the walls the interior moves as a rigid sliding block of a uniform layer:

  at rest if G < μ; V(t) = g (G − μ) t if G > μ (in the downslope direction)

(after 2 s, 0.6828 m/s at 1.1 μ and 2.0483 m/s at 1.3 μ).

- The time step is small because the yield friction is put in semi-implicitly
  ($`a_y/\max(|\mathbf{V}|, v_v)`$ in the denominator), and the resulting delay of
  the onset is proportional to the time step. The speed at 1.1 μ after 2 s was
  0.80 times the analytic value with dt = 0.01 s, 0.96 times with 0.002 s and
  0.995 times with 0.0005 s. With the time steps of ordinary runs the onset is
  delayed by about this much.
- The steep-slope gravity correction (`f_gravity_correction`) is off. The
  correction takes the effective gravity g_e from the slope in the normal
  direction of each edge, so g_e comes out large on edges oblique to the slope
  (+6.8 % for 4-neighbour, 45°, 1.1 μ), which by itself makes the sliding speed
  depend on the direction (the threshold of rest and onset does not change,
  because the same g_e multiplies both the drive and the yield). This case
  isolates the yield check alone. The direction dependence of the gravity
  correction is a separate issue recorded in
  [docs/handoff.md](../../../docs/handoff.md).

| File | Content |
|---|---|
| `make_init.py` | Writes the inputs `d_<case>/` (z.txt, dbinit.txt, sd.txt) and the settings `p_<case>.txt` of all cases (the argument `list` prints the case names). The constants pair with Check |
| `Check_dbonset.py` | Reads the velocity of the interior at 18 m or more from the walls (24 × 24 cells) from the last output (u, v) of each case and judges (1) to (4) below (the argument `table` also prints a table of the values) |

Criteria:

1. Rest: in all cases with G = 0.9 μ, the largest speed in the interior is 0
2. Speed: in all cases with G = 1.1 μ and 1.3 μ, the mean speed of the interior is within 1.5 % of the analytic value
3. Uniformity: (largest − smallest)/mean of the speed in the interior is within 1 % (the whole layer slides as one body)
4. Direction: the direction of the mean velocity of the interior is within 0.5° of the downslope direction

Near the walls the layer is pushed against a wall (downslope side), pulls away
from a wall (upslope side) or flows along a wall (lateral sides), and the
disturbance reaches about 13 m inward in 2 s. The criteria are applied inside
that.

## Running

```bash
make
./Run.sh          # generate inputs → run the 18 cases → Check_dbonset.py (PASS/FAIL and a table of values)
./Run_MPI.sh 4    # MPI. The rule is that save_<case>/state.dat is byte-identical to the serial run
```

The 18 serial cases take about a minute and a half (optimized build, 4 threads).

## Findings

Mean speed of the interior (m/s, after 2 s). With G = 0.9 μ the speed is 0
(rest) in all cases.

| G/μ | Analytic | 8-nb 0° | 22.5° | 45° | 4-nb 0° | 22.5° | 45° |
|---|---|---|---|---|---|---|---|
| 1.1 | 0.6828 | 0.6825 | 0.6825 | 0.6825 | 0.6825 | 0.6825 | 0.6825 |
| 1.3 | 2.0483 | 2.0412 | 2.0412 | 2.0411 | 2.0412 | 2.0412 | 2.0411 |

- The threshold, speed and direction agree regardless of the slope direction
  and the number of neighbours. The difference of the speed from the analytic
  value (−0.04 % at 1.1 μ, −0.35 % at 1.3 μ) is the delay of the onset due to
  the semi-implicit friction plus the Manning resistance. The spread of the
  speed in the interior is within the printed digits of the output
  (0.0001 m/s) and the difference in direction below 0.01°.
- With the yield check before the fix (until 2026-11-04) the same check gave
  the following (in the downslope direction except where a direction is given
  in parentheses).

| G/μ | Analytic | 8-nb 0° | 22.5° | 45° | 4-nb 0° | 22.5° | 45° |
|---|---|---|---|---|---|---|---|
| 1.1 | 0.6828 | 0.0046 | 0.0094 (26.6°) | 0.0065 | 0.6825 | 0.4587 | 0.0000 |
| 1.3 | 2.0483 | 0.0054 | 1.9672 | 0.0076 | 2.0412 | 2.0170 | 0.0000 |

  Before the fix, only the drive in the normal direction of each edge was
  compared with a_y. On an edge at an angle α to the downslope direction the
  normal component of the drive drops to G cos α, so edges oblique to the slope
  were stopped even with G > μ. The cell speed |V| assembled from the edges,
  stopped ones included, came out small, and the yield friction a_y u_n/|V| on
  the moving edges acted too strongly, so the layer did not move or lagged, by
  an amount that changed with the slope direction and the stencil (8-neighbour
  at 0° and 45° and 4-neighbour at 45° do not move even at 1.3 μ). This does not
  change when the grid is refined.
- After the fix, the magnitude of the drive is compared: the drive in the normal
  direction of the edge (advection + gravity, a difference across the edge)
  combined with the gradient of the flow surface (the average of the two cells)
  projected onto the tangent of the edge (the Coulomb yield is a condition on
  the magnitude of the drive vector; the same idea as §51.4 for lava flows).
- With MPI np = 2 and 4, `state.dat` of all cases is byte-identical to the
  serial run.

## Related documents

- [docs/users_guide/massflow.md](../../../docs/en/users_guide/massflow.md) — the resistance laws `f_dbres` of the mixture flow and the check of rest under the yield (§2)
- developer.md §28.16 (the fix that makes the rest check use the magnitude of the drive: phenomenon, cause, decision, verification), §28.11 (the fix that makes the low-speed check use the edge speed)
- Self-check of the same type: [test/curvature](../../curvature/en/README.md) (steady one-dimensional check of the curvature term)
- Example of grid dependence: [examples/debris_fan](../../../examples/debris_fan/en/README.md)
