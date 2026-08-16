> English mirror of tutorials/wave/README.md (based on commit c664f1c). The Japanese file is the master copy.

# Tutorial 1: wave -- waves spreading over still water

A "mound of water" placed on a still water surface collapses and spreads
as concentric waves -- the minimal example of ENCflow. With a single
square basin, no terrain and no rainfall, you will learn:

- **Step 1**: how to run the model, how to read the output, and the
  structure of parameter files
- **Step 2**: time step and accuracy, the adaptive Runge-Kutta method
  (ENC parameters)
- **Step 3**: setting boundary conditions (walls and long-wave radiation)
- **Step 4**: wall properties unique to the ENC grid (impermeable and
  semi-permeable walls)

See the [installation guide](../../../docs/en/install.md) for preparing a
compiler. Visualization uses gnuplot (see section 2.5 of the same
guide for installation). All commands below are run in the case directory
(`tutorials/wave`), one level above this `en/` directory; the English
parameter files are passed as `en/param_step1.txt` etc.

> A case with the same name also exists in `test/wave`, but that one is
> a regression test for development (automatic comparison against
> reference values). Tutorials are done here under `tutorials/`.

## Step 1: first steps

### Preparation

In the case directory, run

```bash
make
```

This creates a symbolic link to the executable `encflow` (if you have
not built it yet, the build in `src/` runs automatically first).

### Running

Run with the parameter file `en/param_step1.txt`.

```bash
./encflow en/param_step1.txt
```

The computation finishes in a few tens of seconds, and a display like
the following appears (execution environment lines such as
`number of threads` will vary with your machine).

```
reading list_sysparam in en/param_step1.txt
reading list_geoinfo in en/param_step1.txt
reading list_initial in en/param_step1.txt
number of processes : 1
number of threads : 4
real precision : 64 bit
number of valid cells : 90000
time, progress, S(m), Runge, ex_flux, Cn_max, h_max(m), V_max(m/s)
  0:00:00.00   0.0%    1.0210   0.0%      0    0.1328    1.9994    0.0000
  0:00:01.00  12.5%    1.0210   8.0%      0    0.1386    1.9993    0.8665
  0:00:02.00  25.0%    1.0210   3.7%      0    0.1394    1.6615    1.0814
  0:00:03.00  37.5%    1.0210   4.1%      0    0.1358    1.2632    1.0533
  0:00:04.00  50.0%    1.0210   4.6%      0    0.1289    1.2380    0.8270
  0:00:05.00  62.5%    1.0210   5.5%      0    0.1251    1.2190    0.7192
  0:00:06.00  75.0%    1.0210   5.7%      0    0.1225    1.2044    0.6512
  0:00:07.00  87.5%    1.0210   6.2%      0    0.1206    1.1967    0.6026
  0:00:08.00 100.0%    1.0210   6.6%      0    0.1214    1.2093    0.6062
```

The columns of the table mean the following.

| column | meaning |
|---|---|
| time | time within the computation |
| progress | progress ratio |
| S(m) | total amount of water in the domain (expressed as depth averaged over the valid cells). In a closed domain it stays constant, which serves as a check of mass conservation |
| Runge | fraction of flux computations recomputed by the Runge-Kutta method (explained in Step 2) |
| ex_flux | number of times an excessive outflow flux was detected and suppressed (stays 0 in this example) |
| Cn_max | maximum Courant number (an indicator of numerical stability) |
| h_max(m) | maximum water depth |
| V_max(m/s) | maximum velocity |

ENCflow results are reproduced bit for bit no matter how you change the
number of threads or MPI ranks. Even if your `number of threads` value
differs, the numbers in the table should match the above exactly.

### Results

The results are saved, by default, in a directory named `result`.

```
$ ls result/
E0000.txt
E0001.txt
...
E0008.txt
E9998.txt
FILENUMBER.csv
H0000.txt
...
H0008.txt
H9998.txt
H9999.txt
Log.txt
Z0000.txt
param_step1.txt
```

Their contents are as follows. Each distribution is a matrix text laid
out the same way as the computational grid, directly readable with GIS,
Python, Excel, and so on.

- `E000n.txt` / `H000n.txt` -- distributions of water level and water
  depth at each file output interval (`dt_file`) (the correspondence
  between `n` and time is in `FILENUMBER.csv`)
- `E9998.txt` / `H9998.txt` -- distributions of water level and water
  depth at the final time step
- `H9999.txt` -- distribution of the maximum water depth over the whole
  computation period
- `Z0000.txt` -- distribution of the ground elevation at the start of
  the computation
- `Log.txt` -- computation log (same content as the screen display)
- `param_step1.txt` -- a copy of the parameter file used for the
  computation (the input copied verbatim, so that the settings can be
  checked afterwards)

### Visualization

The bundled gnuplot script displays the water level `E9998.txt` at the
final time.

```bash
gnuplot Plot_wave.plt
```

A 3D view and a plan view appear in turn (press Enter to advance to the
next figure; pressing Enter on the last figure exits).

| Initial water level (t = 0 s) | Final water level (t = 8 s) |
|---|---|
| ![initial water level](../figs/step1_init.png) | ![final water level](../figs/step1_dt001.png) |

The cosine-shaped mound of water, radius 15 m and height 1 m, placed as
the initial condition (left) collapses and spreads as concentric
ripples (right).

> The figures in this document can be regenerated in one batch with the
> bundled `./Fig_wave.sh` (gnuplot required).

### Inside the parameter file

Now let's look inside the parameter file.

```
!======================================================================
! System parameter settings
!======================================================================
&list_sysparam
  dt = 0.01                 ! time step (s)
  !dt = 0.05                 ! time step (s)
  tt = 8.0                  ! end time of computation (s)
  dt_disp = 1.0             ! screen display interval (s)
  dt_file = 1.0             ! file output interval (s)
  f_out_e = 1               ! water level distribution file output
  fn_geoinfo = "-"          ! geographic information settings file
  fn_initial = "-"          ! initial condition settings file
/

!======================================================================
! Geographic information settings
!======================================================================
&list_geoinfo
  lx = 100.0, ly = 100.0    ! size of computational domain (m)
  nx = 300, ny = 300        ! number of grid cells
/

!======================================================================
! Initial condition settings
!======================================================================
&list_initial
  h0 = 1.0                       ! fixed initial water depth (m)
  f_user_routine = "wave_hump"   ! user routine identifier (circular cosine-shaped initial water level)
/
```

The parameter file is in Fortran namelist format: everything from
`&groupname` to `/` forms one group, and everything after `!` is a
comment. Three groups are used here.

- `&list_sysparam` -- system settings such as the time step, end time
  and output intervals, plus the settings file names for each feature.
  Specifying `"-"` for a file name parameter such as `fn_geoinfo` means
  "**read it from within the same file**"; this example keeps all
  settings in a single file (in practical use, terrain data and the
  like can be split into separate files).
- `&list_geoinfo` -- computational domain and grid. A 100 m square is
  covered with a 300x300 grid (cell size about 33 cm).
- `&list_initial` -- initial conditions. Onto still water 1 m deep, the
  user routine `wave_hump` superimposes a circular cosine-shaped mound
  of water level.

### Coarsening the time step

Let's lengthen the time step in `en/param_step1.txt` from 0.01 s to
0.05 s and run `./encflow en/param_step1.txt` again. Just swap the
comment `!` marks.

```
  !dt = 0.01                 ! time step (s)
  dt = 0.05                 ! time step (s)
```

```
time, progress, S(m), Runge, ex_flux, Cn_max, h_max(m), V_max(m/s)
  0:00:00.00   0.0%    1.0210   0.0%      0    0.6640    1.9994    0.0000
  0:00:01.00  12.5%    1.0210   8.0%      0    0.6921    1.9974    0.8616
  0:00:02.00  25.0%    1.0210   9.6%      0    0.6961    1.6338    1.0799
  0:00:03.00  37.5%    1.0210  11.4%      0    0.6770    1.2628    1.0440
  0:00:04.00  50.0%    1.0210  12.7%      0    0.6444    1.2387    0.8249
  0:00:05.00  62.5%    1.0210  14.9%      0    0.6262    1.2205    0.7203
  0:00:06.00  75.0%    1.0210  14.5%      0    0.6137    1.2067    0.6550
  0:00:07.00  87.5%    1.0210  14.6%      0    0.6129    1.2194    0.6337
  0:00:08.00 100.0%    1.0210  14.4%      0    0.6274    1.2475    0.6909
```

Because the time step is now 5 times longer, the Courant numbers in the
Cn_max column have grown from the 0.1 range to the 0.6 range. The plan
view looks unchanged at first glance, but if you zoom in on the wave
front and compare the water level profiles along the 0-degree direction
(along the x axis) and the 45-degree direction (along the diagonal),
the difference shows up clearly.

![zoomed comparison of the wave front (dt = 0.05)](../figs/step1_profile.png)

With `dt = 0.01` (gray) the waveform is the same in every direction --
clean concentric circles -- but with `dt = 0.05` numerical oscillations
arise at the wave front, and their shape differs between the 0-degree
direction (blue) and the 45-degree direction (red). The waveform that
should be concentric is breaking down depending on the orientation of
the computational grid.

The orthodox ways to reduce this kind of error are to shrink the time
step or to switch the time integration to a higher-order scheme, but
either one inevitably increases the computational cost. The ENC
computation module of ENCflow implements an **adaptive Runge-Kutta
method** that keeps the loss of accuracy to a minimum at little
computational cost. Let's try it in the next Step.

## Step 2: setting ENC parameters

### Changing the application criterion of the adaptive Runge-Kutta method

The adaptive Runge-Kutta method first computes each time step with the
explicit Euler method, then recomputes with the 4-stage Runge-Kutta
method only those cells whose velocity variation ratio exceeds a
threshold. It cuts the amount of computation drastically compared with
applying Runge-Kutta to all cells, though because of the selective
application its accuracy does not quite reach that of full Runge-Kutta
-- the approach is to "invest high-order accuracy only where it is
needed".

To change this threshold, first add a setting that reads the parameter
file of the ENC computation module. Where `fn_geoinfo` and `fn_initial`
are written inside `&list_sysparam`, add the following line.

```
  fn_enc = "-"              ! ENC parameter settings file
```

Since `"-"` (read from the same file) was specified as the file name,
append the following at the end of the same file.

```
!======================================================================
! ENC computation conditions
!======================================================================
&list_enc
  p_adprunge_thresh = 1.1        ! threshold of the adaptive Runge-Kutta method (1.1 ~)
/
```

`p_adprunge_thresh = 1.1` specifies that any cell whose velocity varied
by a factor of 1.1 or more, or 1/1.1 or less, within one time step is
recomputed with the Runge-Kutta method. The default when unspecified is
1.5, so this setting applies the Runge-Kutta method to smaller
variations as well.

A parameter file with these changes applied is provided as
`en/param_step2.txt` (the time step stays at `dt = 0.05`). Let's run it.

```bash
./encflow en/param_step2.txt
```

```
time, progress, S(m), Runge, ex_flux, Cn_max, h_max(m), V_max(m/s)
  0:00:00.00   0.0%    1.0210   0.0%      0    0.6640    1.9994    0.0000
  0:00:01.00  12.5%    1.0210  10.8%      0    0.6907    1.9974    0.8448
  0:00:02.00  25.0%    1.0210  15.5%      0    0.6952    1.6429    1.0749
  0:00:03.00  37.5%    1.0210  20.4%      0    0.6773    1.2620    1.0442
  0:00:04.00  50.0%    1.0210  25.2%      0    0.6442    1.2383    0.8252
  0:00:05.00  62.5%    1.0210  33.0%      0    0.6262    1.2210    0.7198
  0:00:06.00  75.0%    1.0210  37.2%      0    0.6141    1.2090    0.6556
  0:00:07.00  87.5%    1.0210  41.8%      0    0.6089    1.2075    0.6218
  0:00:08.00 100.0%    1.0210  45.6%      0    0.6074    1.2070    0.6134
```

The Courant number is almost unchanged, but the Runge-Kutta application
ratio in the Runge column has grown sharply from the 14% range up to
45.6%, and the h_max and V_max values are approaching those of
`dt = 0.01`. Zooming in on the wave front:

![zoomed comparison of the wave front (threshold 1.1)](../figs/step2_profile.png)

The discrepancy between the 0-degree and 45-degree directions has
shrunk, and the waveform is approaching the concentric circles of
`dt = 0.01` (gray). The time step is still 5 times longer, and fewer
than half of the cells are recomputed -- this is exactly what the
adaptive Runge-Kutta method aims for.

### Extending the computation time

This time, let's extend the end time of `en/param_step2.txt` and watch
the behavior after the wave reaches the edges of the domain.

```
  tt = 14.0                 ! end time of computation (s)
```

```
time, progress, S(m), Runge, ex_flux, Cn_max, h_max(m), V_max(m/s)
  0:00:11.00  78.6%    1.0210  40.3%      0    0.5974    1.1933    0.5656
  0:00:12.00  85.7%    1.0210  33.9%      0    0.5923    1.3292    0.5425
  0:00:13.00  92.9%    1.0210  27.4%      0    0.5871    1.3270    0.5196
  0:00:14.00 100.0%    1.0210  24.0%      0    0.5945    1.3205    0.4956
```

From t = 12 s on, h_max -- which should have kept decreasing -- jumps
up to 1.33 m. Visualizing the result shows the wave reflecting off the
four sides of the computational domain.

![reflection at closed walls (t = 14 s)](../figs/step2_tt14.png)

The outer rim of the ENCflow computational domain is, by default, an
**impermeable wall** (this is why the S column stays constant -- no
water leaves the domain at all). For a water tank computation this is
the correct behavior, but in a computation that cuts out part of a wide
water surface, we would rather have the wave simply leave the domain.
That is the theme of the next Step.

## Step 3: setting boundary conditions

### Setting the four walls to a transmissive condition

To set boundary conditions, add to `&list_sysparam` the reading of a
boundary condition settings file (again `"-"` = read from the same
file),

```
  fn_boundary = "-"         ! boundary condition settings file
```

and append at the end of the file a `&list_bound_edge` group that
specifies the boundary condition type for each of the four edges of the
outer rim of the computational domain.

```
!======================================================================
! Edge boundary conditions: boundary condition type for each of the
!   four edges of the outer rim of the computational domain
!   0: impermeable (wall; default)
!   1: free outflow (for flood inundation)
!   2: long-wave radiation (for tsunami / wave propagation)
!   Correspondence between compass directions and grid indices
!   (raster row order = north to south):
!     west = i=1 (left edge), east = i=nx (right edge),
!     north = j=1 (top edge), south = j=ny (bottom edge)
!======================================================================
&list_bound_edge
  f_bc_w = 2
  f_bc_e = 2
  f_bc_n = 2
  f_bc_s = 2
/
```

Type `2` (long-wave radiation) is a condition that lets long waves
reaching the boundary escape from the domain without reflection. The
radiation condition suits wave propagation like this example; to let
flood water drain out of the domain in a flood inundation computation,
use type `1` (free outflow). The four edges can each be specified
independently.

A parameter file with these changes applied is provided as
`en/param_step3.txt` (with `tt = 14` also applied). Let's run it.

```
time, progress, S(m), Runge, ex_flux, Cn_max, h_max(m), V_max(m/s)
  0:00:11.00  78.6%    1.0210  40.3%      0    0.5974    1.1933    0.5656
  0:00:12.00  85.7%    1.0183  33.9%      0    0.5923    1.1860    0.5495
  0:00:13.00  92.9%    1.0106  26.2%      0    0.5871    1.1777    0.5401
  0:00:14.00 100.0%    1.0019  20.7%      0    0.5821    1.1700    0.5196
```

This time h_max does not jump after t = 12 s; instead, the total amount
of water in the S column starts to decrease -- the wave passes through
the boundary and leaves the domain, and the corresponding loss of water
from the system can be tracked in the S column. Let's compare visually.

| Impermeable (default) | Long-wave radiation |
|---|---|
| ![closed walls](../figs/step2_tt14.png) | ![radiation boundary](../figs/step3_radiation.png) |

The reflection at the walls is gone, and the wave simply flows out of
the domain.

## Step 4: observing the characteristics of the ENC grid

Finally, let's look at a property unique to the **ENC grid
(eight-neighbor connected collocated grid)**, from which ENCflow takes
its name. In the ENC grid, each cell is connected not only to its four
neighbors up, down, left and right but also to its **four diagonal
neighbors**, exchanging water through links in eight directions. When
linear obstacles such as walls and levees are represented on a raster
grid, this shows up as a property that four-connected models do not
have.

`en/param_step4.txt` uses a user routine in `&list_geoinfo` to place a
wall -- cells with ground elevation 1.5 m, excluded from the
computation -- crossing the computational domain diagonally at 45
degrees.

```
&list_geoinfo
  lx = 100.0, ly = 100.0    ! size of computational domain (m)
  nx = 300, ny = 300        ! number of grid cells

  ! user routine identifier (no obstacle if unspecified)
  f_user_routine = "wave_solid_wall"   ! diagonal impermeable wall (2 cells thick)
  !f_user_routine = "wave_leaky_wall"   ! diagonal semi-permeable wall (1 cell thick)
/
```

### A wall that is impermeable

First, run with the **2-cell-thick** wall `wave_solid_wall` as
provided.

```bash
./encflow en/param_step4.txt
```

In the startup display, `number of valid cells` has dropped from 90000
to 89550 -- the cells turned into the wall are excluded from the
computation and consume neither memory nor computation time.

![impermeable wall (2 cells thick)](../figs/step4_solid.png)

The wave is completely blocked by the wall and spreads, while
reflecting, only on the near side of the wall. The far side remains
still water.

### A wall that is semi-permeable

Next, switch the user routine in `en/param_step4.txt` to the
**1-cell-thick** wall `wave_leaky_wall` (swap the comment `!` marks)
and run again.

![semi-permeable wall (1 cell thick)](../figs/step4_leaky.png)

The wall is in the same place, yet this time the wave **passes
through** it and spreads to the far side as well.

This is the eight-directional connectivity of the ENC grid at work.
When a 45-degree diagonal wall is laid out one cell thick, the wall
cells touch each other only corner to corner. The ENC grid has
**diagonal links** that cross these corners, so the water cells on both
sides of the wall stay connected diagonally and water passes through.
With a thickness of two cells, no link crosses a corner and the wall
becomes impermeable (walls parallel to the x or y axis are impermeable
even at one cell thick).

When representing thin linear structures such as levees and breakwaters
in terrain data, watch out for this property -- the safe practice is to
**rasterize diagonal sections at least two cells thick**. Note that for
real-world river levees and seawalls, dedicated virtual wall features
(`fn_bank` / `fn_seawall`) that do not require thickening cells are
also available.

## Closing

This tutorial started from running ENCflow and reading its output, and
went on to time integration accuracy and the adaptive Runge-Kutta
method, boundary conditions, and the wall properties of the ENC grid.
From here:

- [Tutorial 2: chichibu](../../chichibu/en/README.md) -- on to
  rainfall-runoff computation of a catchment with real terrain data;
  the standard workflow of practical computations is taught there
- [examples/](../../../examples/) -- a collection of setup samples
- [test/](../../../test/) -- verified example cases (they double as
  regression tests)
- To run with MPI parallelism, use the `encflow_mpi` executable built
  with the corresponding `make.inc` settings, e.g.
  `mpirun -np 4 ./encflow_mpi en/param_step1.txt`
  ([installation guide](../../../docs/en/install.md)). The results, of
  course, match the serial run bit for bit.

The figures in this document (`../figs/`) can be regenerated in one
batch with `./Fig_wave.sh` (gnuplot required; it runs the same
computations as in the text, in order, and draws the figures).
