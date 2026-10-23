# test/bmi_nest — acceptance test of multi-grid exposure through BMI (a nested system = one component)

> English mirror of test/bmi_nest/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Checks that a nested system can be handled as it is as a single BMI model
(bmi/README.md, docs/users_guide/nest.md §BMI), using the same 1:1
self-nesting as test/nest_identity (wave 385², child 121², parent cells
133..253, two-way nest_fb = 2).

```
./Run.sh          # serial only (the shared library for Python is a serial build)
```

1. Build bmi/ (libencflow_bmi.so and the verification driver test_encflow_bmi).
2. `python3 ../../bmi/python/test_nest.py` (initialize in turn in the same process):
   - A: single run (param_single.txt). Take the depth at t0 through BMI, cut out
     the footprint of the child, and write the child's initial-depth file
     hinit_child.txt. Save the final depth hA and the Log.
   - B: nest (param_root.txt). Check the grid information (`grids = [0, 1]`,
     shape, spacing and origin; the origin of the child is the origin of the
     parent + the alignment position), the variable list (16 outputs, 6 inputs,
     qualified names with `~grid1`), and var_grid. At every step the depth and
     speed in the interior of the child (outside the boundary strip) must be
     bit-identical to the footprint on the root, the final root depth must
     agree with hA, and the Log must agree with A in every line. Misuse (a
     non-existent grid, a size mismatch, set of a negative depth) must raise
     BmiError.
   - C: initialize the nest again, and midway get the child's h and the root's z
     and set them back as they are (same-value set). The final depth must agree
     with hA and the Log must agree with A in every line.
3. Run the nest and the single run with the static driver test_encflow_bmi; the
   Logs must agree.
4. Run bmi-tester (when installed) against the nested system (check_bmi.sh).

All verdicts are strict agreement (ULP 0). The configuration diagram of the
identity is test/nest_identity/figs/identity.png.
