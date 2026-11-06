# test/dbslope — uniform-flow check of the slope-parallel evaluation of the resistance laws of mixture flows (f_gravity_correction = 2)

> English mirror of test/dbslope/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This is the verification case of the steep-slope gravity correction
`f_gravity_correction = 2` (`&list_enc`; the default) evaluating the resistance laws of
the mixture flows of the debris-flow model (`f_debris`) with the slope-parallel speed
$`|\mathbf V_s|`$ and the bed-normal thickness $`h\cos\theta`$ (developer.md §101, in
Japanese; docs/en/users_guide/steep_slope.md §2.3). When the resistance stress
$`\tau`$ is given along the slope, the deceleration of the horizontal velocity is
$`\tau/(\rho_m h\cos\theta\,|\mathbf V_s|)\,\mathbf V`$, which, relative to the horizontal
form (1),

- multiplies the yield (Coulomb, the $`\mu`$ of Voellmy, a constant yield stress) by
  $`1/(r\cos\theta)`$ (1 for flow in the direction of steepest descent),
- multiplies the resistance proportional to the square of the velocity (the turbulent
  term of Voellmy, the laminar law of Egashira, the stony type of Takahashi and
  Nakagawa) by $`r/\cos^3\theta`$ ($`1/\cos^4\theta`$ in the direction of steepest
  descent) and the bedload-like collective flow of Takahashi and Nakagawa by
  $`r/\cos^2\theta`$

($`r = |\mathbf V_s|/|\mathbf V|`$). For example, uniform flow with Voellmy and 2 follows
the along-slope equation $`V_s^2 = \xi\,h\cos\theta\,(\sin\theta - \mu\cos\theta)`$ (as in
RAMMS). The depths of uniform flow of four resistance laws are compared with the analytic
solutions of 2 and of 1. Pass or fail is decided by the self-check `Check_dbslope.py`,
not by a reference comparison (the same type as test/slopefric and test/volcano).

## Configuration

| Item | Value |
|---|---|
| Terrain | A strip 150 m × 8 m (Δx = 1 m) of a uniform slope of gradient tan30°, descending along the x axis, surrounded by walls (`make_init.py` writes `d_slope/z.txt`) |
| Grid | 4 neighbours (`p_diagratio = 0`; removes the nonlinearity "lowered gradient × yield" of the diagonal edges, as in test/volcano; developer.md §28.8) |
| Flow | A constant inflow of 4 m³/s of water with sediment from the 8 cells of the west side (no exchange of sediment, `f_dbed = 0`, so the concentration stays at the inflow value). dt = 0.02 s, 90 s |
| Cases | 4 resistance laws × `f_gravity_correction` 1 and 2, 8 cases (a name such as `stony_g2` = stony type, 2) |

| Resistance law | Settings | Concentration C | Unit-width mixture discharge q |
|---|---|---:|---:|
| voellmy | `f_dbres = 4`, μ = 0.1, ξ = 200 m/s² | 0.444 | 0.9 m²/s |
| egashira | `f_dbres = 2`, φ = 35°, d = 0.05 m, e = 0.85 | 0.444 | 0.9 m²/s |
| stony | `f_dbres = 3`, d = 0.05 m (stony type, C > 0.4 C*) | 0.444 | 0.9 m²/s |
| collective | `f_dbres = 3`, d = 0.05 m (bedload-like collective flow, C ≤ 0.4 C*) | 0.200 | 0.625 m²/s |

| File | Content |
|---|---|
| `make_init.py` | writes the terrain `d_slope/z.txt` and the settings `p_<case>.txt` (the argument `list` prints the case names). The constants are paired with the Check |
| `Check_dbslope.py` | judges (1) and (2) below from the last output (H, Hs) (the argument `table` also prints the table of values) |

Checks:

1. The mean of the vertical mixture depth $`h_t = h + h_s`$ in the middle of the strip
   (x = 60–100 m) agrees with the analytic solution within 0.5 %, the coefficient of
   variation in the window is below 0.02, and the concentration agrees with the inflow
   value within 1e-3. The analytic solutions are the closed solutions of the balance
   written with the horizontal velocity and the vertical depth,
   $`g_e\tan\theta = a_y + f_v\,R(|\mathbf V|, h_t)`$ ($`g_e = g\cos^2\theta`$, $`a_y`$ the
   yield, $`R`$ the resistance proportional to the square of the velocity, $`f_v`$ equal to
   $`1/\cos^4\theta`$ with 2 ($`1/\cos^3\theta`$ for the bedload-like collective flow) and 1 with 1),
   together with $`q = h_t|\mathbf V|`$ (solvable for $`h_t^3`$ with Voellmy, $`h_t^5`$ with
   Egashira and the stony type, and $`h_t^4`$ with the bedload-like collective flow)
2. Discriminating power: the ratio of the analytic solutions of 2 and 1 differs from 1
   by at least 5 % (the two forms can be told apart)

The depths are printed with four decimals (0.1 mm), so the concentration departs by about
1e-4 through rounding.

## Running

```bash
make            # links to the executables
./Run.sh        # runs the 8 cases and judges them (about 30 seconds with 1 thread)
./Run_MPI.sh 2  # MPI (if Run.sh has been run first, state.dat is compared byte by byte with the serial save)
```

## Results (2026-11-06)

| Case | Resistance law | Value | $`\langle h_t\rangle`$ (m) | Analytic (m) | Error | Coefficient of variation | Concentration |
|---|---|---:|---:|---:|---:|---:|---:|
| voellmy_g1 | Voellmy | 1 | 0.2039 | 0.2040 | −0.01 % | 0.0002 | 0.4444 |
| voellmy_g2 | Voellmy | 2 | 0.2471 | 0.2471 | +0.00 % | 0.0001 | 0.4444 |
| egashira_g1 | Egashira | 1 | 0.2185 | 0.2185 | −0.00 % | 0.0003 | 0.4444 |
| egashira_g2 | Egashira | 2 | 0.2452 | 0.2452 | +0.03 % | 0.0033 | 0.4444 |
| stony_g1 | Stony type | 1 | 0.2858 | 0.2858 | −0.01 % | 0.0026 | 0.4444 |
| stony_g2 | Stony type | 2 | 0.3206 | 0.3206 | −0.01 % | 0.0002 | 0.4445 |
| collective_g1 | Bedload-like collective flow | 1 | 0.3285 | 0.3285 | −0.00 % | 0.0000 | 0.2000 |
| collective_g2 | Bedload-like collective flow | 2 | 0.3659 | 0.3659 | −0.01 % | 0.0000 | 0.2001 |

Ratios of the analytic solutions of 2 and 1 (depth for the same discharge): Voellmy 1.211
($`\cos^{-4/3}30°`$), Egashira and the stony type 1.122 ($`\cos^{-4/5}30°`$), the bedload-like collective
flow 1.114 ($`\cos^{-3/4}30°`$).

## Findings

- For all four resistance laws, 2 agrees in the printed digits with the uniform flow of
  the along-slope equations and 1 with that of the horizontal equations. On the 30°
  slope the uniform flow of 2 is 11–21 % deeper than that of 1, and the velocity is lower
  by the same ratio (compared at the same depth, the slope-parallel speed of Voellmy is
  $`\cos^2\theta`$ = 0.75 times).
- For flow in the direction of steepest descent the factor of the yield is 1, so stopping
  that is decided by the yield alone (the rigid sliding of test/dbonset) is the same with
  2 and with 1.

## What it cannot do and limits

- Only uniform flow in the direction of steepest descent on a uniform slope along a grid
  axis is checked. How $`r`$ acts when the flow crosses the slope obliquely (the yield up to
  $`1/\cos\theta`$ times) is built in the same way as the factor of the Manning friction
  and relies on the direction checks of test/slopefric.
- With 8 neighbours, the nonlinearity "lowered gradient × yield" of the diagonal edges
  makes the uniform flow of resistance laws with a yield depart from the one-dimensional
  analytic solution (the note of test/volcano; developer.md §28.8).
- A constant yield stress (`f_dbres = 5`) is not included: its yield factor is 1 in the
  direction of steepest descent and its Manning term has the factor of §93. Exchange of
  sediment (erosion, deposition) and the curvature term are not covered.
- The Voellmy law of the inertia-free bed layer (`f_bedslide`) stays in the horizontal
  form ("not applied" in developer.md §101).

## Related documents

- docs/en/users_guide/steep_slope.md §2.3 and §6.2, docs/en/users_guide/massflow.md
  (resistance laws), developer.md §93 and §101 (in Japanese)
- [test/slopefric](../../slopefric/en/README.md) (friction and sediment shear of water
  flow), [test/volcano](../../volcano/en/README.md) (uniform flow of Voellmy and the
  runout with τ_y), [test/dbonset](../../dbonset/en/README.md) (rigid sliding on a slope)

## References

- Voellmy, A. (1955): Über die Zerstörungskraft von Lawinen. *Schweizerische Bauzeitung*, 73, 159–165, 212–217,
  246–249, 280–285.
- Christen, M., Kowalski, J. and Bartelt, P. (2010): RAMMS: Numerical simulation of dense snow avalanches in
  three-dimensional terrain. *Cold Reg. Sci. Technol.*, 63, 1–14.
- Egashira, S. (1993): Mechanism of stopping and deposition of debris flow (2). *J. Jpn. Soc. Erosion Control
  Eng.*, 46(2) (in Japanese). (original form of the constitutive law of Egashira et al. (1989) and of the yield
  stress)
- Takahashi, T. and Nakagawa, H. (1991): Prediction of stony debris flow induced by severe rainfall. *J. Jpn. Soc.
  Erosion Control Eng.*, 44(3), 12–19 (in Japanese).
