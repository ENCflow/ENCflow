# test/dbmix — Verification of debris flow combined with mixed grain sizes (f_debris + f_bedmix)

> English mirror of test/dbmix/README.md. The Japanese file is the master copy.

[日本語](../README.md)

developer.md §139 and §143, docs/mixed_sediment_plan.md §12 and §13 (all in Japanese). The solids of the
debris flow h_s are carried as one column per size class, and the composition of what is exchanged with the
bed (one exchange layer and one substrate) is tracked. This case verifies the computation through agreement
with the single grain size, values of formulas, the balance of each class, and byte identity of restart and
parallel runs.

By default the erosion, deposition and fluidisation of debris flow do not select grain sizes. Erosion and
fluidisation enter the flow with the composition removed from the top of the column (exchange layer first,
then the substrate), and deposition goes onto the bed with the composition of the flow in that cell. The
debris-flow formulas stay single-size with the representative size `db_d50`, so the ground elevation, the
soil thickness and the total solids of the flow are the same as in the single-size computation. The checks
use this property.

`f_dbsel = 1` and `2` (used with the Takahashi–Nakagawa laws, `f_dbed = 3`) limit the erosion by the
debris-flow law to the movable size classes. A class is movable when its grain size is not larger than the
flow depth in cells whose flow-surface slope exceeds `db_seltan` (default 0.03), and when it exceeds the
critical shear stress in cells at or below it (eqs. (19) to (21) of Takahashi, Inoue, Nakagawa & Satofuka
2000; eq. (26) and the flow regimes of Takahashi, Nakagawa, Satofuka & Kawaike 2001). With K3 the sum of the
fractions of the movable classes in the exchange layer, i the erosion rate of the size-blind law and F_k the
fraction of class k in the exchange layer, the erosion rate of class k is i K3 F_k for `1` (as printed in
the equations; the bulk erosion rate is i K3²) and i F_k for `2` (the bulk erosion rate is i K3, the form
that matches the statement in the text of the same papers that "i K3 is the bulk erosion velocity"). The
immobile classes stay on the bed and are added from the substrate each time the exchange layer moves down,
so their surface fraction grows and the erosion stops. The checks use the unchanged content of an immobile
class in every cell, the formula for the growth of its surface fraction, the ratio of the erosion in one
step, and the two limits of the criterion (all classes movable, no class movable).

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
layer 0.2, 0.5, 0.3, the substrate 0.5, 0.3, 0.2 and an exchange-layer thickness of 4 mm. The configurations
of `f_dbsel` keep the composition and the exchange-layer thickness of "graded" and change only the grain
sizes ("boulder" = 0.5 mm, 2 mm and 1 m; "sand" = 0.2, 0.5 and 1 mm).

## Configurations

| Configuration | Setting | Check |
|---|---|---|
| e1 → e3 | Template e. A single size of 2 mm, and equal sizes with a uniform composition (0.3, 0.4, 0.3) | ground elevation, soil thickness and h_s agree (< 1e-12 m), and the composition of the flow and of the bed stays at its initial value (< 1e-11). The sum of the columns carried one by one = the result of carrying one field |
| u1 → u3 | e1, and equal sizes with different classes in the exchange layer and the substrate (exchange layer 1, 0, 0; substrate 0, 1, 0; exchange-layer thickness 2 mm). Both with first-order upwind (`f_scalar_scheme = 1`) | ground elevation, soil thickness and h_s agree (< 1e-12 m). First-order upwind is linear, so the sum does not change even where the composition varies in space. The two classes mix in the flow, and class 3, which was not placed, stays 0 |
| m3 | the same bed as u3 with MUSCL (the default) | the difference in ground elevation from e1 is within 2 % of the landform change (the limiter acts on each class separately; the difference is not 0). The balance of each class closes |
| w3 | Template e, graded | the residuals of the balance of each class (bed and flow) < 1e-9 m³; the exchange counted on the bed side and on the flow side agree; the total of each class counted from the save (bed + flow) = the initial total; the sum of the columns = h_s; the composition is within 0 to 1 and sums to 1 |
| tk3 | w3 with the Takahashi–Nakagawa laws (`f_dbed = 3`, `f_dbres = 3`, `db_d50` = 1 cm) | as w3 |
| tkb3 | tk3 with the soil layer on the slope only (the flat part is bedrock) | the balance of each class closes, the totals counted from the save equal the initial totals, and the sediment reaches the bedrock of the flat part and the run completes. The rain wets the whole domain, so the front of the flow advances over bedrock it cannot erode, preceded by a very small solid column. In a build with bounds checking (which keeps subnormal numbers) the deposition formula of the Takahashi–Nakagawa laws overflowed and stopped in a cell where that concentration had become subnormal (guards against the recurrence of the bug of developer.md §142) |
| sel3, sel3b | tk3 with the "boulder" sizes and `f_dbsel` = 1 (sel3) and 2 (sel3b), started with water 2 cm deep | class 3 (1 m, always larger than the flow depth) never enters the flow (0 in the ledger and in the columns). Its content is unchanged in every cell (< 1e-12 m). In cells that were only eroded its surface fraction agrees with F_3 = F_3(0) + F_sub,3 Δ / L_a (Δ is the erosion depth; < 1e-11). The erosion stops as F_3 approaches 1 and the erosion depth does not exceed (1 − F_3(0)) L_a / F_sub,3 = 14 mm (after 30 s, F_3 > 0.99 in more than 400 cells for sel3b, and F_3 > 0.9 for sel3, whose erosion rate is proportional to K3²). The deposit carries no class 3. The balance of each class is checked as in w3 |
| selp0 → selp1, selp2 | "boulder" sizes, one step from water 2 cm deep, `f_dbsel` = 0, and 1 and 2 | with K3 = F_1 + F_2 = 0.7, the bulk erosion on the slope is K3² (selp1) and K3 (selp2) times that of selp0 (< 1e-12 m). Classes 1 and 2 enter the flow at K3 times (selp1) and exactly (selp2) the amounts of selp0, class 3 not at all. The composition of the exchange layer is the value "movable classes removed, substrate taken in". On the flat part (bed-load regime) no class exceeds the critical shear stress and nothing is eroded |
| sela0 → sela1 | tk3 with the "sand" sizes (all classes not larger than the threshold depth of 1 mm), `f_dbsel` = 0 and 1 (`db_seltan = 0`, the flow-depth criterion everywhere) | all classes are movable, so every value of the save (flow, bed, composition, columns) equals that of sela0 |
| selb0 → selb1 | tk3 with a critical Shields number of 1e-30, `f_dbsel` = 0 and 2 (`db_seltan = 10`, the shear-stress criterion everywhere) | all classes exceed the critical shear stress, so the save agrees with that of selb0 within round-off (< 1e-12 m). It is not bit-identical: at the front of the starting flow there are cells whose velocity is practically zero (below 1e-15 m/s), and only there does the shear stress fall below even 1e-30 so that the criterion acts (less than 1 % of the eroding cell-updates) |
| selc3 | tk3 with a critical Shields number of 1e30, `f_dbsel = 2`, `db_seltan = 10` | no class is movable and the debris-flow law erodes nothing (amount to the flow and landform change are 0) |
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
| selstop1 | w3 (Takahashi-type erosion law) with `f_dbsel = 1` | stops at initialization (`f_dbsel` = 1 and 2 need `f_dbed = 3`) |
| selstop2 | the single-size Takahashi–Nakagawa laws with `f_dbsel = 2` | stops at initialization (`f_dbsel` = 1 and 2 need the mixed-size bed) |

Typical values of the checks: difference in ground elevation between e3 and e1 2e-15 m (landform change
2.9 mm), between u3 and u1 4e-16 m, between m3 and e1 8.4e-6 m (0.3 % of the landform change); residual of
each class in w3, tk3 and s3 at most 2e-13 m³ (s3 fluidises 6002 cell-updates in total); difference of the
composition in r3 4e-15, difference in ground elevation between r3 and r1 3e-5 m, difference of the columns
in rp3 7e-18 m; inflow of b3 27.000000 m³ and outflow 0.0865 m³; inflow of bt3 8.9910, 0 and 18.0090 m³
(1e-9 m³ from the value of the formula). For the configurations of `f_dbsel`: difference of the content of
the immobile class in sel3 and sel3b 6e-16 m, difference from the formula of the surface fraction 1e-13
(F_3 > 0.99 in 760 cells and an erosion depth of 14.000 mm in sel3b; at most 0.966 and 13.3 mm in sel3),
difference of the erosion of one step in selp1 and selp2 4e-17 m, difference in ground elevation between
selb1 and selb0 9e-121 m (the criterion acted 1855 times).

The tolerance between r1 and r3 is loose because the instantaneous-release configuration crosses the
stopping tests (yield, low-speed coagulation) and amplifies round-off differences. The single-size r1
itself differs by 2 cm between the optimised build and the build with bounds checking. Agreement within
round-off is verified with e1 → e3 and u1 → u3.

## Running

```
make
./Run.sh            # serial. Check_dbmix.py + configurations that stop at initialization (bstop1, bstop2, selstop1, selstop2) + cmp of the restart
./Run_MPI.sh 2      # MPI (np=2). Also checks bit identity with the serial save
```

The inputs z_slope.txt / z_out.txt / sd_rel.txt / sd_zero.txt / sd_slope.txt / sd_film.txt / dbinit.txt / dbinit_half.txt /
dbinit_film.txt / csfrac.txt and the settings of the configurations, p_<configuration>.txt, are generated by make_init.py (not tracked).
There is no reference; pass or fail is decided by the checks in Check_dbmix.py and by the byte identity of
serial, MPI and restart runs.
