# test/wfshadow — two-dimensional verification of the coastal wave field (fn_wavefield)

> English mirror of test/wfshadow/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Two-dimensional verification of the coastal wave field
([User's Guide chapter](../../../docs/en/users_guide/wavefield.md), developer.md §88).
The shadow of a breakwater, blocking by diagonal walls whose cells touch only at corners,
and the virtual senders outside the grid (incident, lateral Neumann, absorbing and the
corner priority) are compared with a discrete solution implemented independently in
`Check_wfshadow.py`. The results of `param.txt` are also compared with the reference
Log.txt, wavefield.csv and Wh0001.txt (ULP=0).

## Configuration

100 × 100 cells (Δx = Δy = 10 m), uniform depth 10 m (`make_z.py`). Land (+3 m) is

- a breakwater: row 60, columns 1..50 (a one-cell-thick breakwater extending from the
  west side)
- a diamond: the cells with |i − 75| + |j − 30| = 8 (one-cell-thick diagonal walls whose
  cells touch only at corners enclose a water area)

Waves travelling north (90°) enter from the south side. The east and west sides are
lateral Neumann and the north side is absorbing. The depth is uniform, so there is no
refraction, and breaking and friction do not act (H_rms/h = 0.07).

| Configuration | File | Content |
|---|---|---|
| Base | `param.txt` | Random waves H_m0 = 1 m, T = 8 s, spreading 20°. wf_tol = 1e-6 |
| Unidirectional along a lattice direction | `param_aligned.txt` | Same topography, unidirectional waves travelling north (spreading 0; bin 11 = centre at 90°) |

## Checks (Check_wfshadow.py)

- **Agreement with an independently implemented discrete solution** (base): the discrete
  steady equations c_g(q_a + q_b) E_ij = Σ q_l c_g E_sender are solved directly by a sweep
  in the order in which the senders are determined (from upstream of the propagation; no
  iteration; c_g cancels for uniform depth). The two-link decomposition, the virtual senders
  outside the grid (incident, Neumann, absorbing and the corner priority) and the rule of
  closed diagonals are the rules of m_wavefield rewritten in this script. The bin energies of
  the offshore waves are also built independently from the cos^s distribution and the
  definition of directional spreading of Kuik et al. (1988). The difference in wave height is
  below 2e-4 m in all wave cells.
- **Blocking by diagonal walls** (base): the wave height is exactly 0 in the 113 cells
  inside the diamond (a diagonal link is closed when both cells beside it are land; a rule
  different from the ENC for water).
- **Waves aligned with a lattice direction** (aligned): the two-link decomposition has no
  crosswind numerical diffusion for propagation along an axis, so H = 0 holds exactly inside
  the geometric shadows of the breakwater and the diamond and H = H_0 = 1 m everywhere else.
- **Difference from the geometric-optics solution** (base; printed only): the difference
  from the line-of-sight solution in which each bin travels straight is a measure of the
  crosswind numerical diffusion at the shadow edges (not used for pass/fail; the correctness
  of the implementation is established by the agreement with the sweep solution above, and
  this difference is recorded as a property of the scheme).

## Running

```bash
make
./Run.sh          # serial + reference comparison + checks (about 8 s)
./Run_MPI.sh 4    # MPI. ULP=0 against the reference (the shadow, the walls and the lateral Neumann sides cross rank boundaries)
```

## Verification record (2026-10-27; gfortran 13.3 / Open MPI 4.1.6, Ubuntu 24.04)

The difference from the sweep solution is at most 2.8e-5 m (in the westmost column with the
lateral Neumann side, which converges slowly; 367 iterations with wf_tol = 1e-6), all 113
cells inside the diamond are exactly 0, and the waves aligned with a lattice direction give
H = 1 m (difference 0) in the 6426 cells outside the shadows and 0 in the 3492 cells inside.
The difference from the geometric-optics solution behind the breakwater (rows 20–58) is at
most 0.18 m with an rms of 0.037 m (numerical diffusion at the shadow edges). With
`-Og -fcheck=all` the serial run and np = 2 and 4 agree; with release builds np = 1, 2 and 4
are ULP=0 against the serial reference.
