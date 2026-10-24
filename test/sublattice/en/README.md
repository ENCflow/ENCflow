# test/sublattice — decay rate of the diagonal sub-lattice (checkerboard) mode in momentum-conservative advection

> English mirror of test/sublattice/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The diagonal links of the ENC grid connect only cells with the same parity of
$`i+j`$. A diagonal circulation rotating oppositely on the even and odd
sub-lattices is divergence-free and does not change the water level (the
pressure term has no effect), and as long as the control volumes of the
diagonal edges in momentum-conservative advection
(`f_advection_scheme = 2, 3`) were built only from cells and links of the same
parity, the advection term did not act on it either (developer.md §68.36).
This case places that mode as the initial condition in a frictionless closed
basin and measures the decay rate directly for each scheme.

## Configuration

| Item | Value |
|---|---|
| Domain and grid | 1 km × 1 km, Δx = Δy = 10 m (100 × 100), flat, frictionless, walls on all four sides, h0 = 5 m |
| Initial velocity | Single-cell gyre ψ = A sin(πx/L) sin(πy/L), maximum V0 = 0.2 m/s (user_initial `gyre_*`) |
| `param.txt` | Only the sub-lattice mode, the gyre multiplied by (−1)^(i+j) (`gyre_alternating`). The initial velocity on the normal edges is 0, being the mean of the two cells |
| `param_smooth.txt` | Control: the undivided gyre (`gyre_smooth`). A physical gyre that should be preserved |
| `param_mixed.txt` | The sub-lattice mode (amplitude 0.5) superposed on the smooth gyre (amplitude 1) (`gyre_mixed`). Linear decay rate through the flux of the background flow = the situation in real cases |
| `param_*_s1/s2.txt` | Comparison of schemes 1 and 2 (`./Run.sh -s`) |
| Time | dt = 0.5 s (Cn = 0.35), 1 hour, output every 5 minutes (u and v distributions) |

`Check_sublattice.py` tabulates the time evolution of the amplitudes obtained
by projecting the u and v distributions onto the initial patterns, a_alt (the
sub-lattice mode; $`\sum s\,(u u_p + v v_p)/\sum(u_p^2+v_p^2)`$,
s = (−1)^(i+j)) and a_sm (the smooth gyre), and estimates the e-folding times.
The pass criterion is that 50 % or more of the smooth gyre remains after
1 hour in smooth and mixed (the background flow is not destroyed). The decay
time of the sub-lattice mode is reported as measured (1094 s even under a
background flow before the fix of the conservative form, 88 s after it).

## Running

```bash
make
./Run.sh          # param.txt, param_smooth.txt, param_mixed.txt
./Run.sh -s       # also the comparison of schemes 1 and 2
./Run_MPI.sh 2    # bit identity of the Log between np=2 and the serial run
```

## Results (2026-10-18; gfortran -Ofast; after the revision that treats the one-sided links of the lateral faces as walls. developer.md §68.37)

Amplitude of the sub-lattice mode (ratio to the initial value 1 or 0.5) and
e-folding time τ.

| Configuration | Scheme 3 (before the fix) | Scheme 3 (after the fix) | Scheme 2 (after the fix) | Scheme 1 |
|---|---|---|---|---|
| alternating: after 5 min / 60 min | 0.57 / 0.33 (τ 4570 s) | 0.18 / 0.07 (τ 2240 s) | 0.18 / 0.07 (τ 2200 s) | 0.40 / 0.10 (τ 1940 s) |
| mixed: τ of the sub-lattice mode | 1094 s (still present after 60 min, changing sign) | **88 s** (0.03 at 5 min) | 87 s | 364 s |
| mixed: remaining background gyre (60 min) | 0.72 | 0.90 | 0.89 | 0.92 |
| smooth: remaining gyre (60 min) | 0.96 | 0.97 | 0.97 | 0.99 |

- In the configuration with the sub-lattice mode alone (alternating), the
  damping by the advection term is proportional to the flux |q_t|, and since
  the only flux is the mode itself, it weakens in proportion to the amplitude
  (algebraic decay), so τ is only a guide. With a background flow (mixed) the
  decay is linear, and after the fix the mode vanishes within 5 minutes.
- Before the fix the sub-lattice mode interfered with the background gyre
  without decaying and cost the background gyre 28 %. After the fix the loss is
  comparable to smooth (11 %).
- Because the initial velocity is given at the cell centers, the component that
  does not fit on the normal edges is lost in the first 5 minutes (the step in
  which the KE of alternating drops to 0.33 or 0.06). This is the consistency
  of the initial condition and is not included in the decay rate.
