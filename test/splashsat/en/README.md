# test/splashsat — Analytical verification of the saturation of the hollow amplification (spl_ksat)

> English mirror of test/splashsat/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This is an analytical verification of the **saturating form** `spl_ksat`
(developer.md §48.6), which replaces κ in the hollow amplification 1 + c κ of
dry-slope erosion `f_splash` by the effective curvature
κ̃ = κ / (1 + κ/κ_s). A parabolic trough uniform in the x direction,
z = 0.05 (y − ly/2)² (user routine `parabolic_trough`; the curvature
κ = 2a = 0.1 1/m is constant in all cells — the 5-point difference of a
quadratic is exact), is given uniform rainfall 30 mm/h and Green-Ampt
72 mm/h (h = 0 at all times); the rill term is switched off (`spl_kt = 0`)
and the amplification `spl_ca = 10` m is applied to the raindrop term alone.

| Quantity | Value |
|---|---|
| κ / κ_s / κ̃ | 0.1 / 0.1 / 0.05 1/m |
| Φ_A = 1 + ca κ̃ | 1.5 (2.0 without saturation) |
| Δz = P kr Φ_A T_geo | 8.333e-6 × 0.004 × 1.5 × 18,000 = **0.9 mm** (1.2 mm without saturation) |

Since κ is halved in the boundary rows (j = 1, ny) by the mirror image, the
analysis covers the interior rows.

```bash
make
./Run.sh                   # compare Log.txt (water ledger) with the reference (ULP = 0)
python3 Check_analytic.py  # compare Sd0000 − Sd9998 in the interior rows with 0.9 mm (PASS/FAIL)
./Run_MPI.sh 2; ./Run_MPI.sh 4
```

Check_analytic.py agrees with the theoretical value to machine precision in
all cells of the interior rows. The reference (Log.txt) is the water ledger
and was fixed on the basis of the analytical agreement.

## Related

- [test/splash](../../splash/en/README.md) (analytical verification without amplification), [test/splashlc](../../splashlc/en/README.md) (wavelength selection)
- A working example: [examples/mesa](../../../examples/mesa/en/README.md) (keeps the bench at the foot of the cliff)
