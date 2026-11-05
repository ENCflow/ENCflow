# test/stencil9 — isotropy of the 9-point creep and of the curvature of dry hillslope erosion, and the reassignment at walls

> English mirror of test/stencil9/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Hillslope creep (`f_creep` of `&list_geomorph`) and the curvature κ of dry
hillslope erosion (`f_splash`) are solved on the 8-neighbour 9-point stencil with the
diagonal share d (`creep_diagratio`, `spl_diagratio`; default 1/3). d = 1/3 makes
the leading discretisation error isotropic. The 4-neighbour 5-point Laplacian with
d = 0 (the default before 2026-11-05) is biased by the grid direction at short
wavelengths close to the cell size (the difference between the decay rates at 45°
and 0° for the same wavenumber is +2.6 % at a wavelength of 8Δ and +11 % at 4Δ)
(developer.md §93, in Japanese;
[the sediment models page of the user's guide](../../../docs/en/users_guide/sediment.md) §2 and §6).
This case is a self-checking test of that isotropy, the normalisation of the weights
and the reassignment at walls, against analytical solutions, exact discrete solutions
and differences between grid directions (it has no reference).

## Configurations

| Configuration | Files | Content | Check (Check_stencil9.py) |
|---|---|---|---|
| gauss | `param_gauss_c9.txt` | the same well-resolved Gaussian hill as test/creep (σ = 10Δ, 101 × 101) with d = 1/3 for 50 s | all cells within 5e-3 m of the analytical solution (normalisation of the weights) |
| hill | `param_hill_c5.txt`, `param_hill_c9.txt` | an under-resolved hill (σ = 2Δ, 81 × 81, `z_hill2.txt`) with d = 0 (control) and 1/3 for 4 s | the difference between the axis-side and diagonal cells at the same distance from the centre (r² = 25: (5,0) and (4,3); r² = 50: (7,1) and (5,5)) is below 0.3 % with d = 1/3 and above 1 % with d = 0 (the detector works) |
| strip | `param_strip1_c9.txt`, `param_strip3_c9.txt` | z = cos(π(j − 0.5)/40) in strips one and three cells wide and 40 m long (walls on all sides) with d = 1/3 for 100 s | the amplitude of every cell agrees within a relative 1e-9 with the exact discrete solution (1 − λΔt)^N obtained when the diagonal shares blocked by walls are reassigned to the axis edges (without the reassignment the effective diffusivity would be 1 − d or (2(1 − d/2) + 1)/3 times) |
| splash | `param_hill_s5.txt`, `param_hill_s9.txt`, `param_hill_lc_s5.txt`, `param_hill_lc_s9.txt` | one step of rain on the same hill, one update with the raindrop term E = P k_r (1 + c_a κ) only (no rill term); ℓ = 0 and 2 m (`spl_lc`), d = 0 (control) and 1/3 | κ read from the ratio of the erosion depth to that of a flat cell; the difference between cells at the same distance is below 0.5 % with d = 1/3 and above 2 % with d = 0 (r² = 25) |

The hill, the strips and the coefficients are paired between `make_terrain.py`,
`param_*.txt` and `Check_stencil9.py`. z is read from the save (double precision) at
the end.

## Running

```bash
make              # links and z_*.txt (make_terrain.py)
./Run.sh          # runs the 9 configurations and checks with Check_stencil9.py (a few seconds)
./Run_MPI.sh 4    # after Run.sh; compares the MPI state.dat bytewise with the serial save_*_serial
```

## Results (gfortran 13.3, the default release build of make.inc, 2026-11-05)

| Quantity | 5-point (d = 0) | 9-point (d = 1/3) |
|---|---:|---:|
| Creep: difference between the axis-side and diagonal cells at the same distance (r² = 25 / 50) | −0.49 % / −1.92 % | −0.01 % / −0.03 % |
| Curvature (ℓ = 0): same (r² = 25 / 50) | −8.42 % / −14.71 % | −0.27 % / +0.26 % |
| Curvature (ℓ = 2 m): same (r² = 25 / 50) | +3.27 % / −0.17 % | +0.13 % / −0.03 % |
| Difference of the strip decay from the exact discrete solution (width 1 / 3) | -- | 6e-15 / 1e-14 |
| Largest difference from the analytical solution for the well-resolved hill (all cells) | 7.6e-4 m | 7.5e-4 m |

- The 9-point stencil almost removes the bias by grid direction. What becomes
  isotropic is the direction of the error, not its size. The largest difference over
  all cells for the well-resolved hill is the same as with the 5-point stencil (the
  tail near the walls dominates), and at the centre of the hill the 9-point stencil
  comes out larger (+1.7e-4 m against +6.3e-5 m; a difference in how much the spatial
  and temporal discretisation errors cancel).
- The decay in the strips agrees with the one-dimensional exact discrete solution to
  rounding error, which shows that the diffusivity next to the walls is the same as
  in the interior.
- With `-Og -fcheck=all`, MPI np = 2 runs all 9 configurations without runtime errors
  and passes the checks. With the release build, the state.dat of MPI np = 1, 2 and 4
  is bytewise identical to the serial one for all 9 configurations.
