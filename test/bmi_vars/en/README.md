# bmi_vars — acceptance test of feature-dependent BMI variables and of set on hg and swe

> English mirror of test/bmi_vars/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The BMI variable list is a dynamic list that "carries a quantity only on the
grids where the feature producing it is enabled" (developer.md §76,
bmi/README.md "Exposed variables"). This case checks that with three
configurations. The terrain is flat (z=0), the domain closed, with uniform
rainfall 36 mm/h and an initial depth of 5 cm.

| Configuration | Contents | Checks |
|---|---|---|
| param_none.txt | No features | Groundwater storage hg and snow water equivalent swe are absent from the variable list, and get / set raise BmiError. Roughness rn (always present; §77): get = rn0, a same-value set is accepted, a negative value rejected |
| param_full.txt | Bucket groundwater (infiltration capacity 10 mm/h) + temperature −5 ℃ + snow (initial 100 mm) | hg and swe are listed. The values agree with the analytical values (a constant increment every step) and with the distribution outputs (Hg/Sw/H). Invariance under a same-value set (all Log lines identical). A set of a negative value raises BmiError |
| param_ga.txt | Same, but Green-Ampt (soil depth 1 m) | hg, swe and sd are listed. set of hg is rejected (inconsistent with the private cumulative infiltration); set of swe is accepted |

It also checks that re-initialize in the same process (none → full → none)
rebuilds the list.

```sh
./Run.sh        # test_vars.py --set, the static driver, bmi-tester (if available)
```

MPI: after `cd bmi && make clean && make MODE=mpi`, the result_full/Log.txt of
`mpirun -np N ../../bmi/test_encflow_bmi_mpi param_full.txt` must agree with
the serial Log.
