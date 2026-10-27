# test/hillsoil — Soil on hillslopes: soil production by weathering

> English mirror of test/hillsoil/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Verification case for bedrock weathering = soil production of the landform
evolution module (`f_wthr = 1` in `&list_geomorph`;
[chapter on landform change in the users guide](../../../docs/en/users_guide/geomorph.md),
equations in
[supplement §7](../../../docs/en/users_guide/sediment.md#7-bedrock-weathering-and-uplift-f_wthr--f_uplift))
and for the distribution `fn_wthr` of the multiplier of its production rate
(developer.md §88.13, in Japanese). The soil depth sd grows as
dsd/dt = W exp(−sd/sd*) (W = W0 × multiplier) while z does not change (the
bedrock surface z − sd is lowered). The update is the exact integral of the
exponential, so it agrees with the analytical solution

  sd(T) = sd* ln(e^{sd0/sd*} + W T/sd*)

to rounding whatever the step. There is no reference; the case is judged by the
analytical solution, bit identity and the messages of the stops. The steady
form of hillslopes (balance of weathering, depth-dependent creep and uplift;
C2 of docs/mountain_stream_plan.md §11, in Japanese) will be added to the same
case later.

The plateau is a flat dry area of 8 × 12 cells (Δx = 1 m, z = 10 m).
W0 = 50 mm/kyr (the default), sd* = 0.5 m, 100 steps of dt = 1 s with a
landform update every step × morfac 1e10 (dts = 1e10 s), i.e. 1e12 s of
morphological time (about 32,000 years).

| Configuration | File | Contents | Judgement |
|---|---|---|---|
| W1 uniform | `param_wthr_none.txt` | No fn_wthr (W = W0 in every cell; the former equation) | Relative 1e-12 to the analytical solution in every cell, z unchanged |
| W1 distributed | `param_wthr_map.txt` | Multiplier m = 0.25 ((i + 4j) mod 9) (0 to 2; `wmap.txt`. The pattern shifts with a period of 9 rows, so a row shift in the band distribution is detected), initial soil depth 0 to 0.3 m (`sdinit.txt`) | Relative 1e-12 to the analytical solution in every cell; the soil depth of cells with multiplier 0 and z of every cell unchanged |
| Restart round trip | `param_wthr_map_rt1.txt` → `param_wthr_map_rt2.txt` | The distributed configuration saved at 50 s and continued to 100 s (the multiplier distribution is read again at the restart) | state.dat bit-identical to the straight run |
| Input errors | `param_wthr_bad.txt` / `param_wthr_nof.txt` | A negative multiplier in one cell (i = 4, j = 11; `wmap_bad.txt`) / fn_wthr given without f_wthr | The initialization stops with "fn_wthr must be >= 0" / "fn_wthr requires f_wthr=1" |

| File | Contents |
|---|---|
| `make_init.py` | Generates the multiplier distribution, the distribution with a negative multiplier and the initial soil depth (constants kept in pairs with `param*.txt` and `Check_hillsoil.py`) |
| `Check_hillsoil.py wthr` | The judgements above (z and sd are read in double precision from state.dat of the save) |
| `Run.sh` / `Run_MPI.sh N` | Runs and checks all configurations. MPI compares bytes with the serial saves (`save_*_serial`). The cell with the negative multiplier lies in the band of the last rows, which checks that all ranks stop even though only that rank detects it |

## Running

```bash
make
python3 make_init.py wmap > wmap.txt   # regenerate the input (bundled; only when changed)
./Run.sh            # serial (under 1 second)
./Run_MPI.sh 4      # MPI (after Run.sh; byte comparison with save_*_serial)
```

## Verification record (2026-10-27; gfortran 13.3 / Open MPI 4.1, default -Ofast build)

- W1: the largest relative error to the analytical solution is 1.6e-15
  (distributed) and 6.2e-16 (uniform) (tolerance 1e-12). The soil depth of the
  11 cells with multiplier 0 and z of every cell are unchanged.
- The restart round trip is bit-identical. Both configurations with input
  errors stop at the initialization.
- np = 1, 2 and 4 are bit-identical to the serial run and pass the same checks.
  np = 2 with -fcheck=all also passes.
- The path without fn_wthr gives a state.dat bit-identical to the executable
  from before fn_wthr was added (-O2). A distribution of 1 in every cell is also
  bit-identical to no distribution (-O2; not part of the checks because the
  standard does not guarantee it).
