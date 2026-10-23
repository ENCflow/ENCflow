# Writing user routines

> English mirror of docs/users_guide/user_routines.md. The Japanese file is the master copy.

User routines are the mechanism for giving the topography or the
initial condition **by formulas or code** instead of files (idealized
experiments, comparison with analytical solutions, benchmarks). You add a
Fortran procedure to one of two files in `src/`, rebuild, and select it by
name with `f_user_routine` in the parameter file. They are not used in
ordinary computations with real data, where topography, masks and the
initial field all come from files ([Geographic information](geoinfo.md),
[Initial conditions](initial.md)).

This page walks through adding one routine of your own and running it.

## The two hooks

| Hook | File | What it modifies | When it runs | Namelist |
|---|---|---|---|---|
| Topography | `src/user_geoinfo.f90` | elevation `g%z`, domain mask `g%x`, sea mask `g%sw`, channel mask `g%rw` (and, if needed, coefficients such as `g%rn`) | right after all topography, mask and coefficient files have been read and the channel has been excavated; before levee and seawall crests are built | `f_user_routine` in `&list_geoinfo` |
| Initial field | `src/user_initial.f90` | depth `s%h`, velocity `s%u`, `s%v`, and if needed `s%z`, `s%hrs`, `s%hg`, `s%hs` | right after the default initial field (`f_htype` etc., including depression filling and channel depth) has been built; before the band is cut out | `f_user_routine` in `&list_initial` |

Both can be used together (for example a slope from the topography hook
and a solitary wave from the initial-field hook, as in `test/nhshelf`).

- The topography hook runs **on rank 0 only**; its result (z, x, sw, rw)
  is then distributed to all ranks (the coefficients exist only on rank 0).
- The initial-field hook runs **redundantly on every rank** with the same
  computation.
- **On restart (f_state_restore > 0) the initial-field hook is not run**:
  the saved state is authoritative. The effect of the topography hook is
  part of the saved topography, so nothing is lost.

## Procedure (three steps plus a build)

The example is a topography routine `my_slope` that makes a uniform slope
falling to the east. The initial-field hook follows the same steps; only
the file and template names differ.

### 1. Copy the template and write the body

Duplicate `geoinfo_template` at the end of `src/user_geoinfo.f90`, rename it
and implement it.

```fortran
!----------------------------------------------------------------------
! Example: uniform slope falling eastward (z = slope * lx at the west
! edge, 0 at the east edge)
!----------------------------------------------------------------------
subroutine geoinfo_my_slope(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: i, j
  real :: x
  real, parameter :: slope = 0.001
  if (p%initialized) continue  ! suppress the unused-argument warning

  do j = lbound(g%z, 2), ubound(g%z, 2)
    do i = lbound(g%z, 1), ubound(g%z, 1)
      x = (i - 0.5) * g%dx            ! x of the cell centre (m)
      g%z(i,j) = slope * (g%lx - x)
    end do
  end do
end subroutine
```

The loops use **`lbound`/`ubound`** rather than `1, g%nx`; the reason is
explained under [The index contract](#the-index-contract-most-important).

### 2. Register the identifier

Add the identifier to `routine_names` at the top of the same file and
increase the array size by one (snake_case; this is the string you write
in `f_user_routine`).

```fortran
  character(len=*), parameter :: routine_names(1:10) = [ character(len=32) :: &
      "wave_solid_wall",  &
      ...
      "my_slope",         &   ! added
      "template"          ]
```

### 3. Add one branch

Add a branch to the `select case` in `resolve` in the same file.

```fortran
    case ("my_slope")
      fp => geoinfo_my_slope
```

If the list and the branches disagree, the run stops with an "undefined
identifier" message that lists the registered names.

### 4. Build and select

```
cd src && make
```

```
&list_geoinfo
  f_ztype = 0                 ! no terrain file: fill with z0, then let the hook overwrite
  f_user_routine = "my_slope"
/
```

A terrain file can also be read first and then modified by the hook
(`f_ztype = 1` with `fn_z`). The initial-field hook is selected the same
way in `&list_initial`.

## Arguments and what you can use

The topography hook receives `(p, g)`, the initial-field hook `(p, g, s)`.

| Variable | Main components | Meaning |
|---|---|---|
| `p` | `p%dt`, `p%t0`, ... | system parameters (read only) |
| `g` | `g%nx`, `g%ny` | number of cells |
| | `g%dx`, `g%dy`, `g%lx`, `g%ly` | cell size (m) and domain length (m) |
| | `g%z(i,j)` | elevation (m). **Window-shaped** (see below) |
| | `g%x(i,j)` | domain mask (1 = computed, 0 = outside / wall). Full domain `(0:nx+1, 0:ny+1)` |
| | `g%sw(i,j)`, `g%rw(i,j)` | sea mask, channel mask (1 = yes). Full domain `(1:nx, 1:ny)` |
| | `g%rn`, `g%gv`, `g%bb`, `g%lm`, `g%rscap` | coefficients (topography hook only; window-shaped) |
| `s` | `s%h(i,j)` | **total water depth** (m; not the water level). Window-shaped |
| | `s%u(i,j)`, `s%v(i,j)` | x and y velocity (m/s, cell centre) |
| | `s%z(i,j)` | computational elevation (m; initially a copy of `g%z`) |
| | `s%hrs`, `s%hg`, `s%hs` | reservoir depth, groundwater storage, suspended sediment (only when those features are used) |

Coordinate conventions:

- The centre of cell (i, j) is at `x = (i − 0.5) * dx`, `y = (j − 0.5) * dy`.
- **i=1 is the west edge, i=nx the east edge, j=1 the north edge (top row
  of the raster), j=ny the south edge.** This is the file's row order; y
  increases southward.
- To prescribe a water level η, convert it to a depth:
  `s%h(i,j) = max(eta - s%z(i,j), 0.0)`.

## The index contract (most important)

Inside a hook you read and write arrays with **global indices** (the same
i, j as the row and column of the input files). However, **the allocated
range of an array is not necessarily the whole grid**.

ENCflow derives a computational **window** (the range of rows and columns
containing valid cells) from the domain mask (`fn_mask`) and allocates
the elevation, the coefficients and the initial-field arrays only over
that window plus two cells of margin, so that memory is proportional to
the window area when a small mask sits in a large grid (developer.md §82).
The indices stay global, so `g%z(i,j)` means the same thing, but **(i, j)
outside the window is not allocated**.

Therefore:

- Loop from **`lbound(g%z, 1)` to `ubound(g%z, 1)` and from `lbound(g%z, 2)`
  to `ubound(g%z, 2)`** (use `s%h` in the initial-field hook). When the
  window is the whole grid (no mask, `f_masktype = 0`, or everything
  valid) these are exactly `1 .. nx` and `1 .. ny`, so idealized cases
  look and behave the same as before.
- `do i = 1, g%nx` writes outside the array whenever the window is not the
  whole grid; the run is silently corrupted or, in a debug build, stops.
- When writing to specific cells (placing a wall, for example), check that
  (i, j) is inside the allocated range first
  (`if (i >= lbound(g%z,1) .and. ...)`).
- The masks `g%x`, `g%sw`, `g%rw` are **full-domain arrays** and can be
  read anywhere with global indices.

### When you change the mask

The topography hook may set `g%x` to 0 to place walls (`wave_solid_wall`
is the example). It **cannot make cells outside the window valid
(x = 1)**: their elevation and coefficients were never read from the
files, and the program stops with

```
geoinfo: user routine my_walls made cells valid outside the window read from the domain mask (...); extend the domain mask (fn_mask) to cover them instead
```

Make such cells valid in the mask file instead.

## Rules and pitfalls

- **Never call `par_stop` inside the topography hook.** It runs on rank 0
  only, so the collective `par_stop` cannot complete; use `par_abort` with
  a message. The initial-field hook runs on all ranks, so `par_stop` is
  fine there.
- **Initialisation in a declaration (`real :: pi = 3.14`) implies SAVE.**
  Use `parameter` for true constants and an executable assignment for
  computed values (`pi = acos(-1.0)`).
- The elevation of sea cells (`g%sw > 0`) is forced to 0 when the file is
  read. If the hook overwrites z there, the new value is used only when
  there is no tide (fn_tide); with fn_tide, the initial application of
  the tide overwrites it with z = tide − hsea0. Leave sea cells alone
  unless that is intended.
- Keep depths non-negative (`max(..., 0.0)`). Decide whether the
  initial-field hook *replaces* or *adds to* the default field
  (`wave_hump` adds: `s%h = max(s%h + η − z, 0)`).
- The hooks run **after** the input files are read and validated. Probe
  and boundary positions are validated after the hook, so changing the
  mask stays consistent (only making cells valid outside the window is
  impossible).
- Units are m, m/s and seconds. Parameter-file values are available
  through `p`. To pass your own numbers, use a `parameter` inside the
  routine or register several identifiers for variants
  (as `wave_solitary28_toe` does).

## Checking the result

- Run a small grid for a short time and plot `Z0000` (elevation) and
  `H0000` (initial depth) to confirm the intent
  ([Input and output formats](io.md)).
- One run with a debug build (`-fcheck=all` in the `make.inc` FFLAGS)
  detects out-of-range accesses immediately.
- Models to copy: topography `shelf_slope` (slope and shelf),
  `gaussian_hill` (analytical benchmark), `wave_solid_wall` (walls in the
  mask); initial field `wave_hump` (added to the default field),
  `dambreak_step` (step), `solitary_profile` (sech² solitary wave; several
  identifiers sharing one body). Each runs in a `test/` case (`nhshelf`,
  `creep`, `wave`, `dambreak`, `nhsolitary`).

## Related

- The registered identifiers are listed in `routine_names` at the top of
  each file.
- [Geographic information](geoinfo.md) (`&list_geoinfo`),
  [Initial conditions](initial.md) (`&list_initial`),
  [the wave tutorial](../../../tutorials/wave/) (minimal setup using
  `wave_hump` and `wave_solid_wall`).
- The developer-side contract (window-shaped arrays, zone lifecycle) is in
  developer.md §11 and §82.
