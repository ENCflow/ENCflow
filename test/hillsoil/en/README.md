# test/hillsoil — Soil on hillslopes: soil production by weathering and steady hillslopes

> English mirror of test/hillsoil/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Verification case for bedrock weathering = soil production of the landform
evolution module (`f_wthr = 1` in `&list_geomorph`;
[chapter on landform change in the users guide](../../../docs/en/users_guide/geomorph.md),
equations in
[supplement §7](../../../docs/en/users_guide/sediment.md#7-bedrock-weathering-and-uplift-f_wthr--f_uplift))
and for the distribution `fn_wthr` of the multiplier of its production rate
(developer.md §89.13, in Japanese). The soil depth sd grows as
dsd/dt = W exp(−sd/sd*) (W = W0 × multiplier) while z does not change (the
bedrock surface z − sd is lowered). The update is the exact integral of the
exponential, so it agrees with the analytical solution

  sd(T) = sd* ln(e^{sd0/sd*} + W T/sd*)

to rounding whatever the step (W1). C2 is a steady hillslope where uplift,
weathering and depth-dependent creep (`creep_hstar`) balance
(docs/mountain_stream_plan.md §11.3 and developer.md §89.15, in Japanese).
There is no reference; the case is judged by the analytical solutions,
conservation, bit identity and the messages of the stops.

The plateau of W1 is a flat dry area of 8 × 12 cells (Δx = 1 m, z = 10 m).
W0 = 50 mm/kyr (the default), sd* = 0.5 m, 100 steps of dt = 1 s with a
landform update every step × morfac 1e10 (dts = 1e10 s), i.e. 1e12 s of
morphological time (about 32,000 years).

The domain of C2 has 11 × 24 cells (Δx = 1 m). The middle column is a stream
one cell wide that falls to the south with slope 0.01 (segment inflow
Q = 0.336 m³/s at the north end, uniform-flow depth 0.3 m, free outflow at the
south edge), with hillslopes of 5 cells on each side (the east and west edges
are divides = walls). Only the hillslopes are uplifted (U = 2e-6 m/s) and
weathered (W0 = 3U and 6U, sd* = 0.5 m). The stream is a fixed bed that is
neither uplifted nor weathered (multiplier 0 of `fn_uplift` and `fn_wthr`;
`c2_hill.txt`) and carries the soil delivered by creep to the outlet as bed
load (d50 = 1 cm), so it is the base level of the hillslopes. Creep has
D = 2.3817e-5 m²/s and H_c = 0.3 m. In the steady state the bedrock surface
does not move (W(H) = U), so the soil depth is H_ss = sd* ln(W0/U), and z does
not move (∇·q = U), so the cross-slope curvature is ∇²z = −U/D_eff
(D_eff = D (1 − e^{−H_ss/H_c})); the height of the k-th cell from the stream is
(U/D_eff)(k L − k(k−1)/2) (L = 5; exact also for the discrete second
difference). The initial state is a flat plateau 0.5 m above the stream bed
(soil depth 0.3 m). dts = 40 s (morfac 400) for 5e6 s of morphological time
(about 8 times the relaxation time of the slowest mode of the hillslope,
about 6e5 s). The values are compressed in time for the check.

| Configuration | File | Contents | Judgement |
|---|---|---|---|
| W1 uniform | `param_wthr_none.txt` | No fn_wthr (W = W0 in every cell; the former equation) | Relative 1e-12 to the analytical solution in every cell, z unchanged |
| W1 distributed | `param_wthr_map.txt` | Multiplier m = 0.25 ((i + 4j) mod 9) (0 to 2; `wmap.txt`. The pattern shifts with a period of 9 rows, so a row shift in the band distribution is detected), initial soil depth 0 to 0.3 m (`sdinit.txt`) | Relative 1e-12 to the analytical solution in every cell; the soil depth of cells with multiplier 0 and z of every cell unchanged |
| Restart round trip | `param_wthr_map_rt1.txt` → `param_wthr_map_rt2.txt` | The distributed configuration saved at 50 s and continued to 100 s (the multiplier distribution is read again at the restart) | state.dat bit-identical to the straight run |
| Input errors | `param_wthr_bad.txt` / `param_wthr_nof.txt` | A negative multiplier in one cell (i = 4, j = 11; `wmap_bad.txt`) / fn_wthr given without f_wthr | The initialization stops with "fn_wthr must be >= 0" / "fn_wthr requires f_wthr=1" |
| C2 steady hillslope | `param_c2_w3.txt` / `param_c2_w6.txt` | W0 = 3U (H_ss = 0.549 m, U/D_eff = 0.100 1/m) / 6U (0.896 m, 0.0884 1/m) | Steadiness max\|dz/dt\| < 0.01 U between the last two outputs. On the hillslopes of the middle rows (j = 7 to 18) the soil depth within relative 1 % of H_ss and the cross-slope second difference (mirrored at the divide) within 5 % of −U/D_eff. The sediment budget Σ(z − z0)A = uplift − open-boundary outflow/(1 − λ) (the outflow is the ledger of developer.md §89.12) within 1e-8 of the uplifted volume. The bedrock surface z − sd of the stream unchanged (1e-9 m) |
| C2 restart round trip | `param_c2s.txt`, `param_c2s_rt1.txt` → `param_c2s_rt2.txt` | c2_w3 cut at 1000 s as a straight run, and saved at 500 s and continued | state.dat bit-identical |

| File | Contents |
|---|---|
| `make_init.py` | Generates the multiplier distribution, the distribution with a negative multiplier and the initial soil depth of W1, and the terrain, initial depth, soil depth and hillslope multiplier of C2 (constants kept in pairs with `param*.txt` and `Check_hillsoil.py`) |
| `Check_hillsoil.py wthr / c2` | The judgements above (z and sd are read in double precision from state.dat of the saves; the steadiness of C2 from Z in bil, single precision) |
| `Run.sh` / `Run_MPI.sh N` | Runs and checks all configurations. MPI compares bytes with the serial saves (`save_*_serial`). The cell with the negative multiplier lies in the band of the last rows, which checks that all ranks stop even though only that rank detects it |

## Running

```bash
make
python3 make_init.py wmap > wmap.txt   # regenerate the input (bundled; only when changed)
./Run.sh            # serial (about 1 minute; 30 s for each of the two C2 configurations)
./Run_MPI.sh 4      # MPI (after Run.sh; byte comparison with save_*_serial)
```

## Verification record (2026-10-27; gfortran 13.3 / Open MPI 4.1, default -Ofast build)

- W1: the largest relative error to the analytical solution is 1.6e-15
  (distributed) and 6.2e-16 (uniform) (tolerance 1e-12). The soil depth of the
  11 cells with multiplier 0 and z of every cell are unchanged.
- The restart round trip is bit-identical. Both configurations with input
  errors stop at the initialization.
- C2 (W0 = 3U and 6U): the largest relative difference between the soil depth
  on the hillslopes of the middle rows and H_ss is 1.2e-3 and 1.7e-4, and
  between the cross-slope second difference and −U/D_eff 9.4e-3 and 1.1e-2
  (largest at the cell next to the stream; the heights above the stream in
  row 12 are 0.4987, 0.8983, 1.1979, 1.3976 and 1.4974 m against the
  analytical 0.5, 0.9, 1.2, 1.4 and 1.5 m); steadiness 1.2e-3 U and 2.0e-4 U;
  the sediment budget closes to 3e-10 and 1e-10 of the uplifted volume; the
  bedrock surface of the stream changes by 6e-13 m. With dts = 100 s (morfac
  1000) the fluv_dzmax limit of the bed load in the stream fired and the foot
  of the hillslopes collapsed. The C2 restart round trip is bit-identical.
- np = 1, 2 and 4 are bit-identical to the serial run and pass the same checks.
  np = 2 with -fcheck=all also passes.
- The path without fn_wthr gives a state.dat bit-identical to the executable
  from before fn_wthr was added (-O2). A distribution of 1 in every cell is also
  bit-identical to no distribution (-O2; not part of the checks because the
  standard does not guarantee it).
