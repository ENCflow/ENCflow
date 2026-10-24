# test/rockfall — checks of rockfall and talus (f_rockfall)

> English mirror of test/rockfall/README.md. The Japanese file is the master copy.

[日本語](../README.md)

A square plateau on a plain (side 20 m, height 10 m, vertical free face) is acted on
only by **rockfall and talus** `f_rockfall` (developer.md §48.7), with no water and no
rainfall. Because the 10 m free face exceeds the critical height H_c = 4 m, the rim
collapses and the fallen material spreads at the foot as talus (repose angle 35°).

| Item | Value |
|---|---|
| Domain and grid | 41 × 41 m, Δx = 1 m (closed domain with walls on all four sides) |
| Terrain | make_init.py: plateau z = 10 m (\|x\|, \|y\| ≤ 10 m), z = 0 around it |
| Rockfall | rf_hc = 4 m, rf_phi = 35°, rf_relax = 0.5, fluv_dzmax = 0.5 m |
| Time | dt = 0.1 s, 60 s (600 terrain updates, morfac = 1) |

Checks (Check_rockfall.py; z and sd of save/state.dat and result/Ht9998.txt):

1. Sediment volume conservation: |Σ(z − z₀)| < 1e-9 (result 8e-13)
2. Final maximum height difference among the 8 neighbours ≤ H_c + 1e-3 (allows a residual of about 1e-4 from the geometric convergence of the relaxation; 1e-2 for the windowed variant)
3. Talus budget: ht ≥ (z − z₀)⁺ in every cell (net deposition is booked as talus), Σht > 0
4. Co-moving update: max|(sd − sd₀) − (z − z₀)| < 1e-10

Windowed variant (param_rc.txt, `rf_rc = 3 m`): a check of the rule that measures the
free-face height as the drop to the lowest point within a square window of 3 cells. At the
end, the in-window drop of the cells that have an edge steeper than the talus repose angle
is ≤ H_c (pass `rc=3` to Check_rockfall.py). Run.sh / Run_MPI.sh run both.

Supported-face mode (param_face.txt, `rf_fface = 0`, window `rf_rc = 3 m`): a check of the
rule that turns the collapse into a column collapse in which "the column at the top of the
face falls to the foot" (there is no dry erosion, so the factor is not used). The columns
fall one at a time; the bedrock of a fallen column is buried as a shelf at the height of the
talus top, and the collapse comes to rest once the talus has thickened so that the in-window
drop is ≤ H_c (converges in 1500 updates). The check restricts (2) to "cells with no step
higher than H_c above them (cells where a column can start)" and adds (6) steps steeper than
the repose angle remain in cells without talus (the bedrock face) (`rc=3 face=1`). Under MPI,
besides state.dat, the private save geomorph_rockfall.dat (talus thickness and
collapsing-column flags) is also compared with the serial run.

Undercut variant (param_uc.txt, `rf_uc = 0.5 m`, rainfall 10 mm/h fully infiltrating + dry
erosion (raindrop term kr = 0.1, rill term kt = 0.05), the top 2 m of the plateau capped
(spl_strata factor 0.1), H_c = 15 m > face 10 m): on a plateau that does not collapse by its
face height, once dry erosion cuts back the bedrock of the foot (the plain), which is softer
than the column, by u_c, the rim column falls, the debris buries the foot and u returns to 0,
and the next column does not fall until the talus (erodibility factor 1) has been removed and
the bedrock cut back by u_c again (a talus-limited cycle). The check replaces (1) by
"Σ(z − z₀) = −(export of dry erosion out of the system (ledger)) × 1/(1 − λ)" and adds (7) the
ledger of columns started by undercutting > 0 and the number of plateau-surface cells
(z ≥ 9.5 m) decreases (`rc=3 face=1 uc=Screen_uc.log hc=15`). In 5000 updates the 80 rim
columns (one full circuit of the perimeter) fall, the plain is lowered by 2.3 m, and the rim
retreats by 1 cell while remaining a vertical face. Under MPI, geomorph_rockfall.dat (talus thickness, column flags and undercut depth) is
also compared with the serial run.

Sea-cell variant (param_sea.txt, `make_init.py --sea`): the west side x < 10 m is made sea
cells (sw = 1, z = 0), so that the west wall of the plateau faces the sea. The volume that
falls into the sea leaves the system, so the checks are replaced by (1) the volume decrease on
land = the ledger "rockfall exported to sea cells" and (5) the z of the sea cells is unchanged.

Bedrock variant (param_bed.txt, `rf_bedrock = 1`): the same plateau is given without a soil
layer (a zero map for `fn_sd`; make_init.py --sdzero) and collapsed by bedrock rockfall. It
checks that it collapses to the same z as param.txt (sd0 = 20 m), in which the supply limit
never acts ((8) 0 in exact arithmetic, 2e-15 in the last digit with -Ofast), and that only the
fallen material becomes sd (sd = talus ht; (4')) (`bed=save`).

```bash
make
./Run.sh            # serial + checks (copies save/ to save_serial/; also the bedrock, windowed, supported-face, undercut and sea-cell variants)
./Run_MPI.sh 2      # MPI + checks + bit-identity check of save/state.dat against the serial run (also the bedrock, windowed, supported-face, undercut and sea-cell variants)
./Run_MPI.sh 4
```

## Related

- [test/repose](../../repose/en/README.md) (angle-of-repose avalanching; the same numerical form), developer.md §48.7, §84.4
- [docs/users_guide/geomorph.md](../../../docs/en/users_guide/geomorph.md) — `f_rockfall`
- Working example: [examples/mesa](../../../examples/mesa/en/README.md) (retreat of cap-rock cliffs and talus)
