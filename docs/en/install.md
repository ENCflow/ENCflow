> English mirror of docs/install.md (based on commit 7401b91). The Japanese file is the master copy.

# Installation Guide

Installing ENCflow amounts to "get a Fortran compiler and run
`make install`". No external libraries are required, and no
administrator privileges (sudo) are needed. The products are simply
placed in `bin/` inside the repository, so if you ever want them
gone, deleting the whole directory restores your system exactly.

- Just want it running -> [1. Up and running in 5 minutes](#1-up-and-running-in-5-minutes)
- Plotting in the tutorials -> [2. Installing the visualization tools](#2-installing-the-visualization-tools-gnuplot-paraview)
- Faster on multiple cores -> it is parallel with no action needed ([3.3](#33-openmp-parallelism-is-on-from-the-start))
- On a cluster or supercomputer -> [4. Building the MPI hybrid version](#4-building-the-mpi-hybrid-version)
- With a compiler other than gfortran -> [5. Switching compilers](#5-switching-compilers)
- Got an error -> [7. Troubleshooting](#7-troubleshooting)

## 1. Up and running in 5 minutes

All you need are git and gfortran.

**Ubuntu / Debian / WSL** (on Windows, Ubuntu under WSL is recommended;
for setting up WSL and a Unix-beginner guide, see
[Using ENCflow on Windows](windows.md)):

```bash
sudo apt install -y git gfortran make
```

**macOS** (Homebrew):

```bash
brew install gcc    # gfortran ships with gcc
```

Then, on any platform. `git clone` copies (clones) a repository
published on GitHub — the whole project, with source code, examples,
and documentation — onto your own PC:

```bash
git clone https://github.com/ENCflow/ENCflow.git   # copy the whole repository here
cd ENCflow/src                                     # move into the source directory
make install                                       # build -> ../bin/encflow is created
```

Verify the installation (this runs the first example and
automatically compares it against the verified results):

```bash
cd ../test/wave    # move into the first example's directory
./Run.sh           # run and auto-compare against the verified results
```

If the last line reads `=== regression test PASS ===`, your build of
ENCflow produces the same answers as the development environment.
Installation is complete. Next stop: the
[tutorial](../../tutorials/wave/en/README.md) (the tutorials use
gnuplot to plot the results, so it is smoothest to install it first —
[Sec. 2](#2-installing-the-visualization-tools-gnuplot-paraview)).

## 2. Installing the visualization tools (gnuplot, ParaView)

ENCflow itself does not depend on any visualization tool (results are
plain matrix text or GeoTIFF, readable by GIS, Python, Excel, and so
on). The tutorials and the bundled plot scripts (`Plot_*.plt`),
however, use **gnuplot** (5.2 or later), so install it if you plan to
follow the tutorials.

**Pick the single command that matches your environment** (pasting
several of these lines at once will produce errors).

Ubuntu / Debian (including WSL):

```bash
sudo apt install -y gnuplot
```

macOS (Homebrew):

```bash
brew install gnuplot
```

Fedora / RHEL family:

```bash
sudo dnf install -y gnuplot
```

`gnuplot --version` confirms the installation and version.

For 3D visualization and animation (Step 7 of the chichibu tutorial),
we use **ParaView**. Installing the binaries from the
[official site](https://www.paraview.org/download/) (Windows / macOS /
Linux) is the most reliable route; package managers also work (again,
pick the one line for your environment):

Ubuntu / Debian:

```bash
sudo apt install -y paraview
```

macOS (Homebrew):

```bash
brew install --cask paraview
```

If you compute inside WSL, install ParaView **on the Windows side**
and open the result files through the Explorer path `\\wsl$\...` (or
place results under `/mnt/c/...`); with WSLg enabled, ParaView inside
WSL also works.

## 3. How the installation works

### 3.1 What gets created where

- Running `make install` in `src/` builds the executable
  **`encflow`** and copies it to **`bin/`** at the repository root.
  Nothing is written to system directories.
- Running `make` in an example directory (`test/wave` etc.) creates a
  symbolic link to the executable in `bin/` (the test Run scripts
  create it automatically when needed). Execution is always of the
  form `./encflow parameterfile`.
- Running `make install` at the repository root builds, in addition
  to the main program, the pre/post-processing utilities in `utils/`
  (you do not need them at first).

### 3.2 Build configuration in a single make.inc

All build settings -- compiler, optimization, parallel mode -- are
collected in **`make.inc`** at the repository root (switched by
commenting lines in and out). The default is "gfortran, optimized,
serial (OpenMP) version", which you can use as-is. When you edit
`make.inc`, the next make automatically rebuilds everything, so a
manual `make clean` is normally unnecessary (for the exception, see
[Sec. 7](#7-troubleshooting)).

### 3.3 OpenMP parallelism is on from the start

`encflow` has OpenMP thread parallelism enabled by default and uses
all cores of the machine with no configuration. Set an environment
variable only when you want to control the thread count:

```bash
export OMP_NUM_THREADS=4    # example: limit to 4 threads
```

### 3.4 Run your computations anywhere

There is no additional installation step before starting your own
computations. **Just place a symbolic link to `encflow` in `bin/`
(`encflow_mpi` for the MPI version) -- or a copy of it -- in the
directory where you want to run.** That directory may be outside the
repository.

```bash
mkdir ~/mycase && cd ~/mycase
ln -s ~/ENCflow/bin/encflow .     # create a link (recommended)
./encflow param.txt
```

- All input and output are relative to the directory you run in
  (results appear in `result/`). There is no need to modify PATH or
  install anything system-wide. The `make` in the example directories
  merely automates this link creation.
- **Link (recommended)**: after a rebuild (`make install`), the new
  executable is used automatically.
- **Copy**: a copy is better when you want to freeze the executable
  used for a computation at a specific version (freezing
  reproducibility in long-term projects).
- For large grids, remove the shell's stack limit first
  (`ulimit -s unlimited`; with the default limit the run may die with
  a silent Segmentation fault —
  [Sec. 7](#7-troubleshooting)).

For how to write parameter files, see the
[tutorial](../../tutorials/wave/en/README.md) and the
[user's guide](users_guide.md).

## 4. Building the MPI hybrid version

To compute across nodes on a workstation or supercomputer, build the
MPI version **`encflow_mpi`**. An MPI library (OpenMPI or MPICH) is
required:

```bash
sudo apt install -y openmpi-bin libopenmpi-dev    # Ubuntu example
```

Build and run:

```bash
cd ENCflow/src
make MODE=mpi install       # -> ../bin/encflow_mpi
cd ../test/wave
./Run_MPI.sh 2              # run with 2 ranks and auto-compare against the verified results
```

To run manually, use `mpirun -np <ranks> ./encflow_mpi param.txt`.
This is **hybrid parallelism** -- OpenMP threads within a node, MPI
across nodes -- so the basic rule is ranks x threads = total cores.

**Open MPI pitfall -- threads squeezed onto one core**:
Open MPI's mpirun pins (binds) each rank to specific cores by
default. If you run as-is, **all the OpenMP threads of each rank land
on a single core**, and although no error appears, the parallelism
has no effect (symptom: CPU usage per rank stays pinned around 100%,
and adding threads does not speed things up). Release the binding
with `--bind-to none`:

```bash
export OMP_NUM_THREADS=6
mpirun -np 4 --bind-to none ./encflow_mpi param.txt
```

The test script (Run_MPI.sh) already has this configured. When tuning
for performance, an explicit placement such as
`--map-by l3cache:pe=$OMP_NUM_THREADS --bind-to core` is also
effective instead of unbinding (advantageous on NUMA systems).
Note that MPICH's mpiexec does not bind by default, so this problem
does not occur there. For job scripts, follow the documentation of
your system.

Notes:

- `encflow` and `encflow_mpi` **can coexist** in `bin/`. When you
  switch back and forth between the serial and MPI versions, only the
  side you switched to is rebuilt (the build system automatically
  detects mixed intermediate files and rebuilds).
- ENCflow is designed so that **the results match bit-for-bit
  regardless of the number of ranks**. `./Run_MPI.sh 4` gives the
  same PASS.
- If you want the MPI version to be the permanent default, you may
  change `MODE = serial` to `MODE = mpi` in `make.inc`.
- The apt-packaged MPICH of Ubuntu 24.04 has a known defect in which
  all processes become rank 0 even with the bundled mpiexec
  (Debian Bug #1066735). On Ubuntu, OpenMPI is the safe choice. An
  incorrect launch is also detected and stopped on the ENCflow side
  ([Sec. 7](#7-troubleshooting)).

## 5. Switching compilers

Just switch the comments in the compiler block of `make.inc`. The
following have been verified:

| Compiler | FC in make.inc | Notes |
|---|---|---|
| GNU gfortran | `gfortran` | Default. Free of charge |
| Intel oneAPI | `ifx` | Free distribution available |
| NVIDIA HPC SDK | `nvfortran` | Free distribution available |
| AMD AOCC | `flang` | Free distribution available |
| LLVM Flang | `flang-22` | Free of charge |
| NEC SDK | `nfort` | For SX-Aurora TSUBASA (vector machine) |

Each block comes with recommended optimization flags and debug flags.
**Only when you switch the compiler itself while staying in serial
mode**, run `make clean` in `src/` after the switch (all other
switches -- optimization flags, MODE, precision -- are detected
automatically).

## 6. Configuration reference (make.inc)

| Setting | Default | Description |
|---|---|---|
| `MODE` | `serial` | `serial` (OpenMP version encflow) / `mpi` (hybrid version encflow_mpi). Can also be overridden on the command line as `make MODE=mpi` |
| `PREC` | `double` | Real precision. `single` halves the memory (results will not match double) |
| `FC` / `FC_MPI` | gfortran / mpifort | Compiler proper and MPI wrapper |
| `FFLAGS` | optimized | Switch comments for a debug build (with runtime checks) |

For details of the build system relevant to contributors (the safety
interlocks of mode switching, the correspondence between LTO and the
archiver, etc.), see [developer.md](../developer.md) (in Japanese),
Sec. 1-3.

## 7. Troubleshooting

**`gfortran: command not found`**
The compiler is not installed. Install it with the commands in
[Sec. 1](#1-up-and-running-in-5-minutes).

**`ERROR: ../../bin/encflow not found; run 'make MODE=serial install' in src first`**
The executable has not been built. Run the command shown in the
message in `src/` (for the MPI version, `make MODE=mpi install`).

**`ERROR: the src build does not match the current environment` / `may not have been installed`**
The build state of `src/` disagrees with the mode or environment you
are trying to run. Running the remedy command shown in the message
(`make MODE=... install`) as-is resolves it. This can also appear
after switching modules on a supercomputer (align the module
environment with the one used at build time).

**A large computation stops with nothing but `Segmentation fault`**
The shell's stack size limit is the most likely cause. Fortran
compilers may place work arrays and expression temporaries on the
stack, and with the default limit (8192 KB on WSL and many Linux
systems) a large grid exceeds it during input reading or computation
and the run dies without any message. Running

```bash
ulimit -s unlimited
```

before the computation resolves it. Instead of typing it every time,
**we recommend putting it in `~/.bashrc`** (takes effect in every new
shell from then on):

```bash
echo 'ulimit -s unlimited' >> ~/.bashrc
```

- macOS does not accept unlimited; use `ulimit -s hard` (raise to the
  hard limit) instead.
- If the symptom persists in OpenMP thread-parallel runs, also set
  the per-thread stack limit: `export OMP_STACKSIZE=512m`.
- On supercomputers, batch jobs may not read `~/.bashrc`; put the
  line in the job script.

**The MPI version does not get faster with more threads (CPU usage
stays pinned around 100% per rank)**
Open MPI's default binding is squeezing all threads onto one core.
Add `mpirun --bind-to none`
([Sec. 4](#4-building-the-mpi-hybrid-version)).

**An MPI run stops immediately with a rank-count mismatch**
The combination of mpirun and the MPI library is inconsistent, and
all processes started independently (when launched via the test
scripts, ENCflow detects this automatically and stops). Use the
mpirun of the same implementation as the MPI used for the build. If
the cause is the defect in Ubuntu 24.04's apt-packaged MPICH itself,
switch to OpenMPI ([Sec. 4](#4-building-the-mpi-hybrid-version)).

**Masses of errors after switching compilers**
Switching the compiler itself in serial mode is the one change that
is not detected automatically. Run `make clean` in `src/`, then
`make install`.

**The regression test does not PASS**
Even with a different compiler or machine, each test should PASS
within its default tolerance (one unit in the last displayed digit).
If it FAILs, check the build configuration (in particular whether
`PREC=single` is set, and any changes to `make.inc`). If that does
not resolve it, please file an Issue with your environment details
(OS, compiler and version, changes to `make.inc`).

## Uninstalling

Just delete the repository directory. ENCflow installs nothing on
your system.
