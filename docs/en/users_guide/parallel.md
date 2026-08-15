# Parallel Execution

> English mirror of docs/users_guide/parallel.md (based on commit 6c5acfc). The Japanese file is the master copy.

[Back to the User's Guide index](../users_guide.md)

ENCflow is designed to run from a laptop to a supercomputer from a
single source. Parallelization comes in two layers.

## OpenMP (within one machine) -- nothing to do

The normally built `encflow` has OpenMP thread parallelism enabled and
automatically uses the machine's cores when run. No configuration is
needed. Use the environment variable only when you want to control
the thread count explicitly.

```bash
OMP_NUM_THREADS=8 ./encflow param.txt
```

## MPI (multiple nodes, large-scale computation)

Switching one line in `src/make.inc` and building produces
`encflow_mpi` with OpenMP x MPI hybrid parallelism.

```
MODE	= mpi        # make.inc (default is serial)
```

```bash
cd src && make install
mpirun -np 4 ./encflow_mpi param.txt
```

- **The parameter file is exactly the same as for the serial
  version.** Domain decomposition (band decomposition in the j
  direction), communication, and output aggregation are all
  automatic.
- The basic layout is threads within a node and MPI across nodes (the
  assignment of ranks x threads follows the job scheduler and mpirun
  settings. For environment-specific notes, including the pitfall of
  Open MPI's default binding, see the
  [installation guide](../install.md)).
- `encflow` and `encflow_mpi` can coexist (both are placed in bin/,
  and each case's Makefile links to both).

## Reproducibility of results (ENCflow's guarantee)

**However you change the number of threads or MPI ranks, the results
are bitwise identical.** A verification result produced serially and a
production run on 100 ranks return exactly the same answer, and a
[restart](restart.md) also matches a run without interruption
exactly. For comparisons in numerical experiments and accountability
in practice, there is no need to worry that "results change subtly
due to parallelization".

## Real-number precision

The default is double precision. A single-precision build exists for
memory-constrained environments (`PREC = single` in `make.inc`).
Single precision changes the result values themselves, so do not mix
it with double precision in comparisons. The build system detects
mode and precision switches and prevents inconsistencies.
