# test/dbmix — Verification of debris flow combined with mixed grain sizes (f_debris + f_bedmix)

> English mirror of test/dbmix/README.md. The Japanese file is the master copy.

[日本語](../README.md)

developer.md §139, docs/mixed_sediment_plan.md §12 (both in Japanese). The solids of the debris flow h_s are
carried as one column per size class, and the composition of what is exchanged with the bed (one exchange
layer and one substrate) is tracked. This case verifies the computation through agreement with the single
grain size, values of formulas, the balance of each class, and byte identity of restart and parallel runs.

The erosion, deposition and fluidisation of debris flow do not select grain sizes. Erosion and fluidisation
enter the flow with the composition removed from the top of the column (exchange layer first, then the
substrate), and deposition goes onto the bed with the composition of the flow in that cell. The debris-flow
formulas stay single-size with the representative size `db_d50`, so the ground elevation, the soil thickness
and the total solids of the flow are the same as in the single-size computation. The checks use this
property.

The terrain is a slope with a break, 20 × 60 cells (dx = dy = 1 m): slope 0.4 for y < 40 m and flat
downstream. The flow runs in the j direction (southward) and crosses the interfaces of the MPI bands. The
inputs and the settings are made by make_init.py. The settings are written to p_<configuration>.txt by
replacing lines of four templates (replaced and added lines carry a note).

| Template | How the debris flow starts | Soil layer | Boundaries |
|---|---|---|---|
| param_e.txt | sheet flow from rain of 200 mm/h erodes the soil layer of the slope | uniform 0.3 m | closed |
| param_r.txt | the failure area on the slope (12 × 12 cells) is fluidised at the start of the run (`fn_dbinit`) | 1 m in the failure area only, bedrock elsewhere | closed |
| param_s.txt | infiltration of rain of 500 mm/h saturates the soil layer, and the slope-stability test (`f_slide`) fluidises 0.2 m from the top at a time | uniform 0.5 m | closed |
| param_b.txt | a flow carrying sediment (3 m³/s, volume concentration 0.3) enters through 6 cells of the north edge; the downstream slope is 0.1 | none (bedrock) | free outflow at the south edge |

Two mixed-size beds are used. "Equal sizes" has three classes that are all 2 mm (the grain size of the
single-size configurations) and differ only in composition. "Graded" has 0.5, 2 and 8 mm with the exchange
layer 0.2, 0.5, 0.3, the substrate 0.5, 0.3, 0.2 and an exchange-layer thickness of 4 mm.

## Configurations

| Configuration | Setting | Check |
|---|---|---|
| e1 → e3 | Template e. A single size of 2 mm, and equal sizes with a uniform composition (0.3, 0.4, 0.3) | ground elevation, soil thickness and h_s agree (< 1e-12 m), and the composition of the flow and of the bed stays at its initial value (< 1e-11). The sum of the columns carried one by one = the result of carrying one field |
| u1 → u3 | e1, and equal sizes with different classes in the exchange layer and the substrate (exchange layer 1, 0, 0; substrate 0, 1, 0; exchange-layer thickness 2 mm). Both with first-order upwind (`f_scalar_scheme = 1`) | ground elevation, soil thickness and h_s agree (< 1e-12 m). First-order upwind is linear, so the sum does not change even where the composition varies in space. The two classes mix in the flow, and class 3, which was not placed, stays 0 |
| m3 | the same bed as u3 with MUSCL (the default) | the difference in ground elevation from e1 is within 2 % of the landform change (the limiter acts on each class separately; the difference is not 0). The balance of each class closes |
| w3 | Template e, graded | the residuals of the balance of each class (bed and flow) < 1e-9 m³; the exchange counted on the bed side and on the flow side agree; the total of each class counted from the save (bed + flow) = the initial total; the sum of the columns = h_s; the composition is within 0 to 1 and sums to 1 |
| tk3 | w3 with the Takahashi–Nakagawa laws (`f_dbed = 3`, `f_dbres = 3`, `db_d50` = 1 cm) | as w3 |
| s3 | Template s, graded | as w3 (a balance that includes fluidisation by the slope-stability test) |
| r1 → r3 | Template r. A single size, and equal sizes with the exchange layer 0.6, 0.3, 0.1, the substrate 0.1, 0.3, 0.6 and an exchange-layer thickness of 5 cm. The whole soil layer (1 m) of the failure area is fluidised | the composition of the fluidised column, {L_a A + (D − L_a) B}/D = 0.125, 0.3, 0.575, is kept everywhere in the flow and in the deposited bed (< 1e-11). The difference in ground elevation from r1 is compared with a loose tolerance (1 cm) |
| rp3 | r3 with a release depth of 0.5 m (the upper half of the soil layer), one step | the columns of the failure area are (1 − λ){L_a A + (D − L_a) B} = 0.045, 0.09, 0.165 m, and the exchange layer and the substrate of the remaining soil have the composition B |
| film3 | Template r. The soil layer of the failure area is a film whose thickness is close to the lower limit of double precision (4.6e-308 m), and its upper half is fluidised; one step. Equal sizes, exchange layer 0.4, 0.3, 0.3, substrate 0.3, 0.3, 0.4 | the composition of the exchange layer and of the substrate stays valid in every cell (not negative, summing to 1). The optimised build sets values below the smallest normal number to 0, so every product of the film thickness and a fraction becomes 0. If all fractions became 0, the mean grain size would be 0 and the hiding function of the bed load would divide by zero (guards against the defect of developer.md §139.7) |
| b3 | Template b, equal sizes, composition of the inflowing sediment `inflow_csfrac` = 0.2, 0.3, 0.5 | total inflow = Q · cs · T = 27 m³; the class ratios of the inflow, the outflow, the flow and the deposit equal the given composition; the balance of each class closes |
| bt3 | Template b, graded, composition series `fn_inflow_csfrac` (1, 0, 0 at 0 s; 0, 0, 1 from 20 s) | the inflow of each class agrees with Q · cs · Σ f_k(t_n) Δt (the fractions at the end of each step) (< 1e-6 m³); the balance closes |
| rt1 → rt2 | w3 split at 24 s | state.dat, geomorph_bedmix.dat and swflow_enc.dat are byte-identical to w3 |
| rt1 → alt2 | the save of rt1 (solids remain in the flow) restored into a mixed-size configuration without debris flow (`f_state_restore = 2`) | the columns of the solids of the flow go onto the bed with their composition (initial stock of the bed = bed + flow of rt1). The total of each class counted from the save stays at the initial total |
| rt1 → alt3 | alt2 with suspended sediment, `f_suspend = 1` | class 1 stays in the flow as suspended load and classes 2 and 3 go onto the bed. The totals are the same |
| bstop1 | Template b, equal sizes, no composition for the inflowing sediment | stops at initialization (the composition of the inflowing sediment is given data, so there is no default) |
| bstop2 | b3 without debris flow | stops at initialization (the composition has a meaning only in the combination) |

Typical values of the checks: difference in ground elevation between e3 and e1 2e-15 m (landform change
2.9 mm), between u3 and u1 4e-16 m, between m3 and e1 8.4e-6 m (0.3 % of the landform change); residual of
each class in w3, tk3 and s3 at most 2e-13 m³ (s3 fluidises 6002 cell-updates in total); difference of the
composition in r3 4e-15, difference in ground elevation between r3 and r1 3e-5 m, difference of the columns
in rp3 7e-18 m; inflow of b3 27.000000 m³ and outflow 0.0865 m³; inflow of bt3 8.9910, 0 and 18.0090 m³
(1e-9 m³ from the value of the formula).

The tolerance between r1 and r3 is loose because the instantaneous-release configuration crosses the
stopping tests (yield, low-speed coagulation) and amplifies round-off differences. The single-size r1
itself differs by 2 cm between the optimised build and the build with bounds checking. Agreement within
round-off is verified with e1 → e3 and u1 → u3.

## Running

```
make
./Run.sh            # serial. Check_dbmix.py + configurations that stop at initialization (bstop1, bstop2) + cmp of the restart
./Run_MPI.sh 2      # MPI (np=2). Also checks bit identity with the serial save
```

The inputs z_slope.txt / z_out.txt / sd_rel.txt / sd_zero.txt / sd_film.txt / dbinit.txt / dbinit_half.txt /
dbinit_film.txt / csfrac.txt and the settings of the configurations, p_<configuration>.txt, are generated by make_init.py (not tracked).
There is no reference; pass or fail is decided by the checks in Check_dbmix.py and by the byte identity of
serial, MPI and restart runs.
