# test/splashstrata — Analytical verification of horizontal strata (spl_strata) in dry-slope erosion

> English mirror of test/splashstrata/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This is an analytical verification of dry-slope erosion `f_splash` given the
**erodibility factors of horizontal strata** `spl_strata` (a table of the
bottom elevation and the factor of each layer; developer.md §48.5). On the
same slope with a slope break as [test/splash](../../splash/en/README.md)
(slope_break: z = 0.4(30 − x), flat for x ≥ 30 m), with the same rainfall
30 mm/h and Green-Ampt 72 mm/h (h = 0 at all times), the factors of 3 layers
are superposed on the coefficients without amplification (kr = 0.004,
kt = 0.02).

| Layer | Elevation | Factor | Columns concerned |
|---|---|---|---|
| 3 | z ≥ 10 m | 0 (cap rock that does not erode) | x ≤ 4.5 m |
| 2 | 6 ≤ z < 10 m | 0.5 | x = 5.5–14.5 m |
| 1 | 0 ≤ z < 6 m | 1 | the slope at x = 15.5–29.5 m and the flat part |

Since the erosion depth (≤ 1.8 mm) is much smaller than the margin to the
layer boundaries (≥ 0.2 m), each column stays in the same layer, and the
erosion depth is analytically Δz = f(z)·P·(kr + kt S)·T_geo
(T_geo = 18,000 s). The coefficients are chosen so that Δz is an integer
multiple of the printed digit of the Sd output (1e-4 m).

| Column class | S | Theoretical Δz (mm) |
|---|---|---|
| Hard layer (factor 0) | 0.4 | 0 |
| Layer with factor 0.5 | 0.4 | 0.9 |
| Slope with factor 1 | 0.4 | 1.8 |
| Column at the slope break (x = 29.5 m; the slope of the face by steepest descent) | 0.2 | 1.2 |
| Flat part | 0 | 0.6 |

## Running

```bash
make
./Run.sh                   # compare Log.txt (water ledger) with the reference (ULP = 0)
python3 Check_analytic.py  # compare Sd0000 − Sd9998 with the analytical values by column class (PASS/FAIL)
./Run_MPI.sh 2; ./Run_MPI.sh 4
```

Check_analytic.py agrees with the theoretical values to machine precision
(maximum error 4e-16 m) in all column classes. The reference (Log.txt) is the
water ledger, and since the rainfall–infiltration system is the same as in
test/splash regardless of the strata, it was fixed on the basis of the
analytical agreement.

## Related

- [test/splash](../../splash/en/README.md) (analytical verification without strata), developer.md §48 and §48.5 (in Japanese)
- [docs/users_guide/geomorph.md](../../../docs/en/users_guide/geomorph.md) — `spl_strata`
- A working example: [examples/badland_round](../../../examples/badland_round/en/README.md) (bands of alternating hard and soft beds)
