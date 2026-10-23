# test/gvchange — Unit test of the void-ratio change procedure m_state_set_gv

> English mirror of test/gvchange/README.md. The Japanese file is the master copy.

[日本語](../README.md)

This is a unit test of the procedure `m_state_set_gv`, which changes the cell
void ratio gv (the "fraction available to water", reduced when rubble,
buildings and the like occupy the water column; A1 and A2 of developer.md
§63.1). The computation core (the time loop) is not run; the procedures of
`libencflow.a` are applied directly to a small 3 × 3 band state (the same
style as [test/gtif](../../gtif/en/README.md)). There are no figures.

## Configuration

| Check | Contents |
|---|---|
| (1) Volume conservation | Column quantity × gv agrees before and after the change to machine precision (relative 1e-14) in all ledgers (h, hs, hrs, hd, cq, hss) |
| (2) Derived quantities | lm = gv + (1 − gv)·cm, e = z + h and af are updated in proportion by the gv factor alone |
| (3) No change | Cells that are not changed stay unchanged, and a call with gv_new == gv_old is a no-op (bit-unchanged) |
| (4) Optional ledgers | Does not crash when optional ledgers (wd, hbd etc.) are unallocated (allocated check) |

| File | Contents |
|---|---|
| `test_setgv.f90` | Test program (changes cell (2,2) to gv 0.95 and (1,3) to 1.0) |
| `Makefile` | Links `libencflow.a` with the compiler settings of `../../make.inc` |
| `Run.sh` | Builds and runs. The last line is `== gvchange 検定: PASS ==` |

## Running

```bash
./Run.sh      # make → ./test_setgv (1 second)
```

Even when built with MODE=mpi it calls no collectives, so it runs as a
singleton without mpirun.

## Findings

```
(3) no-op          : PASS
(1) volume balance : 0 failure(s) so far (0 = PASS)
(2) derived fields : 0 failure(s) so far (0 = PASS)
== gvchange 検定: PASS ==
```

- A change of gv is an operation that "conserves the column quantity and
  reinterprets the depth": h_new = h_old × gv_old / gv_new. The same factor
  is applied to all ledgers, so the volumes of water, sediment, driftwood,
  water quality and salt water are all conserved.
- When changing the public interface (`m_state_set_gv(p, s, i, j, gv_new)`),
  confirm this test and the follow-up of utils/ with a top-level `make`
  (§10).
- Physics module that uses the void ratio: building debris
  [test/bldgdebris](../../bldgdebris/en/README.md) (§63).

## Related documents

- developer.md §63.1 (the void ratio as a state: s%gv / s%lm, A1 and A2; in Japanese)
