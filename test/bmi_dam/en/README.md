# bmi_dam — acceptance test of the BMI exposure of dam quantities and of external operation

> English mirror of test/bmi_dam/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Through BMI you can read the level, storage volume, inflow, release and spill of
the dams (`&list_struct_dam`) and give a target release to the dams declared as
externally operated (`f_dam_mode = 6`) (developer.md §133, bmi/README.md
"Dams"). This case checks that with four dams.

The domain is 24 × 10 cells (dx = dy = 10 m). Four isolated one-cell capture
zones sit in column i = 2 (j = 2, 4, 6, 8), and internal sources feed each the
same triangular hydrograph (base 0.2 m³/s, 1.7 m³/s at 60 min, back to
0.2 m³/s at 120 min). The releases go to a flat closed pond at i = 5 to 24. All
four dams share the HV table (100 m, 0) (105 m, 2.0×10⁴ m³)
(112 m, 6.0×10⁴ m³), and 2 hours are computed with dt = 1 s.

| Dam | Operation | Checks |
|---|---|---|
| 1 | Release time series (`f_dam_mode = 4`; steps 0.3 → 0.6 at 20 min → 0.4 m³/s at 60 min) | Reference for dam 2. It is not externally operated, so the element set for it (999) is ignored |
| 2 | External operation (`dam_q0 = 0.3`). Python sets the same stepped release as dam 1 at every step | Identical to the CSV of dam 1 on every row |
| 3 | External operation (`dam_q0 = 0.2`). The sample controller `bmi/python/dam_control.py` (brings the volume back to its initial value, cap 2 m³/s, change of the target within 0.0004 m³/s/s) | The change of the target stays within that limit at every step (slower than the rise of the flood inflow, so the limit keeps acting during the flood), the level stays within 104 m ± 10 cm, and the actual release equals the target |
| 4 | Constant-release method with a restricted level (`f_dam_mode = 1`, 0.5 m³/s, `dam_hlim = 103`) | The element set for it (999) is ignored |

The test (`bmi/python/test_dam.py`) also checks the variable lists and the grid
(five dam quantities and the target release; the point grid of the dams is
"unstructured", with the nodes at the centers of the capture cells), the values
right after initialize, the rejection of a negative target and of an array of
the wrong length, the agreement of the get values with the dam CSV at the same
times, volume conservation of the closed system (S in the Log), and
re-initialize with a setting that has no externally operated dam (the target
release is not listed, and set raises BmiError).

```sh
./Run.sh        # test_dam.py, dam_control.py, the static driver, bmi-tester (if installed)
```

`dam_control.py` is also run as a command, and it must keep the externally
operated dams 2 and 3 at their initial storage (final level 104 m ± 10 cm). The
static driver `test_encflow_bmi` runs to the end while it sets, before every
step, a deterministic control that brings the volume back to its initial value,
when the target release is in the input list. It also checks that settings
that do not fit the external operation (`dam_tadashigaki` in mode 6, a negative
`dam_q0`) stop `encflow` at start-up. The input data in data_bmi_dam/ can be
regenerated with `python3 make_data.py`.

MPI: after `cd bmi && make clean && make MODE=mpi`, the result/dams/*.csv and
result/Log.txt of `mpirun -np N ../../bmi/test_encflow_bmi_mpi param.txt` must
be identical to the results of the serial static driver
(`../../bmi/test_encflow_bmi param.txt`).
