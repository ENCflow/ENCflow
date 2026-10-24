# test/wetlw — Lateral spreading of the detachment depth of wet erosion, wet_lw

> English mirror of test/wetlw/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Sheet erosion by surface flow (`f_wash`) and entrainment (`f_suspend`) are
proportional to the cell value of τ*, so when the flow collects into a
one-cell-wide path only that cell erodes and collects still more water. This
positive feedback has no length scale, so the width and spacing of gullies
are set by the grid spacing and do not converge under grid refinement
(examples/badland_storm, result 4). `wet_lw = ℓ_w` is an option that
distributes the detachment depth evaluated in each cell to the neighbouring
cells with a Gaussian kernel of standard deviation ℓ_w before subtracting it
from `z` and `sd` (the suspended sediment `hs` enters the source cell;
developer.md §84.16). The kernel is symmetric, and the share that would fall
outside the domain or on sea cells is returned to the cell itself, so the
total solid volume is conserved.

This test runs the same configuration as test/wash (flat bed, closed-domain
dam break + uniform rainfall 50 mm/h, 8 s) without `wet_lw` (configuration 0)
and with `wet_lw = 3 m` (configuration l), and checks the following.

| Check | Contents |
|---|---|
| Conservation (both configurations) | `../suspend/Check_suspend.py`: total solids Σhs + (1−λ)Σ(z−z0) = 0, co-moving update sd − sd0 = z − z0, activity |
| Smoothing (`Check_spread.py`) | (1) the grid-scale roughness of the erosion depth Δz (sum of squares of the 5-point Laplacian) is at most half in configuration l, (2) the maximum erosion depth is smaller in configuration l, (3) the ratio of the total erosion is 0.5–2 (it only redistributes and does not change the amount) |
| MPI | `state.dat` for np = 2, 4 is byte-identical to the serial run (the halo is exchanged in each pass of the smoothing) |

## Running

```bash
make
./Run.sh          # configuration 0 → l → checks (a few seconds)
./Run_MPI.sh 4    # MPI. state.dat is byte-identical to the serial run
python3 Fig.py    # figs/wetlw.png
```

## Figure

![wetlw](../figs/wetlw.png)

Left: erosion depth Δz = z0 − z of configuration 0; centre: configuration l;
right: profile along the central row. The ring-shaped erosion carved by the
dam-break front is, with ℓ_w = 3 m, spread over a width ≈ ℓ_w, so the peak is
lower and the flanks are wider, and the uneroded hole at the centre is also
filled in (the total is the same).

## Findings

| Quantity | Configuration 0 (no wet_lw) | Configuration l (ℓ_w = 3 m) |
|---|---|---|
| Total solids Σhs + (1−λ)Σ(z−z0) | 0.000e+00 | 0.000e+00 |
| Grid-scale roughness of the erosion depth (sum of squares of the Laplacian, m²) | 4.19e−05 | 7.47e−06 (0.18 times) |
| Maximum erosion depth (m) | 5.58e−03 | 4.61e−03 |
| Ratio of the total erosion | 1 | 1.002 |

## Related documents

- [test/wash](../../wash/en/README.md) (smoke test and conservation in the same configuration), [test/suspend](../../suspend/en/README.md)
- [examples/badland_storm](../../../examples/badland_storm/en/README.md) results 4 and 5 (grid convergence of the gully spacing)
- [docs/users_guide/geomorph.md](../../../docs/en/users_guide/geomorph.md) — `wet_lw`
- developer.md §84.16, docs/splash_plan.md §6.9 (in Japanese)
