> English mirror of tutorials/chichibu/README.md (based on commit c664f1c). The Japanese file is the master copy.

# Tutorial 2: chichibu -- rain on a real-terrain catchment

We cover the Chichibu catchment in the upper Arakawa River basin
(about 715 km^2) with a 200 m grid, apply a heavy rainstorm
(200 mm/h x 30 min), and compute rainfall runoff and flood wave
propagation. You will learn the standard workflow of a practical
computation with real terrain data, in the following order.

- **Step 1**: Minimal configuration with real terrain data; why
  depression filling is necessary
- **Step 2**: GeoTIFF input/output, channel mask and roughness
- **Step 3**: Measurement (probes and flux transects) and distributed
  output
- **Step 4**: Parameter tuning -- how to read ex_flux, threshold depth,
  upwinding of advection
- **Step 5**: Rainfall interception and subsurface infiltration (bucket
  model), the three water-storage columns
- **Step 6**: Boundary condition at the catchment outlet; understanding
  discharge oscillations caused by real terrain data

We assume you have completed the [wave tutorial](../../wave/README.md)
first (it explains how to run the model, the meaning of each screen
column, and the structure of parameter files). All work below is done
in the case directory (`tutorials/chichibu`); run the English parameter
files from there as `./encflow en/param_step1.txt` etc.

## A look at the data

`../data_chichibu/` contains the following raster data.

| Data | Contents |
|---|---|
| `Chichibu_200m_filled.*` | Ground elevation (m), with D8 depression filling applied in GIS software |
| `Chichibu_200m_raw.tif` | Ground elevation (m), original data without depression filling (for a comparison experiment) |
| `Chichibu_200m_basin.*` | Catchment mask (1: inside the catchment, 0: outside) |
| `Chichibu_200m_river.*` | Channel mask (1: channel cell) |

All of them sit on the same grid of **280 x 150 cells (dx = dy =
200 m)** (a 56 km x 30 km domain). Each dataset is provided with the
same contents in three formats -- text (`.txt`), bil (`.bil` + `.hdr`),
and GeoTIFF (`.tif`) -- for practicing the input/output formats.

Data sources: the elevation data were derived from the Digital
Elevation Model of the Fundamental Geospatial Data by the Geospatial
Information Authority of Japan (GSI); the channel mask was derived from
stream-order data
([DOI:10.3178/jjshwr.36.1812](https://doi.org/10.3178/jjshwr.36.1812))
built from the river data of Kokudo Suuchi Jouhou (National Land
Numerical Information).

![Terrain (inside the catchment mask)](../figs/step1_z.png)

The northeast corner (elevation around 100 m) is the outlet of the
catchment, and peaks of the 2,500 m class line up along the main ridge
in the southwest. Most of the catchment is steep mountainous terrain.

## Step 1: Minimal configuration with real terrain data

### Running

As in wave, create the link to the executable with `make`, then run
`en/param_step1.txt` from the case directory (`tutorials/chichibu`).

```bash
make
./encflow en/param_step1.txt
```

```
reading list_sysparam in en/param_step1.txt
reading list_geoinfo in en/param_step1.txt
 reading data_chichibu/Chichibu_200m_basin.txt
 reading data_chichibu/Chichibu_200m_filled.txt
reading list_precip in en/param_step1.txt
number of processes : 1
number of threads : 4
real precision : 64 bit
number of valid cells : 17885
time, progress, S(m), Runge, ex_flux, Cn_max, h_max(m), V_max(m/s)
  0:00:00.00   0.0%    0.0000   0.0%      0    0.0000    0.0000    0.0000
  0:30:00.00   8.3%    0.0487  97.7%      0    0.3876    2.3735   10.3884
  1:00:00.00  16.7%    0.1000   6.0%      0    0.6716    8.0311   18.2975
  1:30:00.00  25.0%    0.1000   3.5%      1    0.7116    8.6295   19.6093
  2:00:00.00  33.3%    0.1000   1.9%     15    0.6868   14.8529   18.9331
  ...
  6:00:00.00 100.0%    0.1000   0.9%    190    0.5896   33.0043    6.7073
```

The parameter file is structured almost identically to Step 1 of wave;
the only differences are that `&list_geoinfo` reads the terrain and the
catchment mask from files, and that `&list_precip` makes it rain.

```
&list_geoinfo
  nx = 280
  ny = 150
  dx = 200.0
  dy = 200.0

  f_ztype = 1          ! ground elevation type (0: default constant, 1: file)
  f_masktype = 1       ! domain mask (0: none, 1: catchment mask)

  fn_z = "Chichibu_200m_filled.txt"        ! ground elevation file name
  fn_mask = "Chichibu_200m_basin.txt"      ! domain mask file name
/

&list_precip
  prtype = 1
  ! precipitation time series (time (min), intensity (mm/h))
  prval(:,1) =   0,   0
  prval(:,2) =  30, 200
  prval(:,3) =  60,   0
/
```

The screen output tells us the following.

- `number of valid cells : 17885` -- the full grid has 280 x 150 =
  42,000 cells, but thanks to the catchment mask only 17,885 cells are
  actually computed. Cells outside the mask consume neither memory nor
  computation time.
- The S column grows with the rain and, at t = 1:00 when the rain ends,
  stops exactly at **0.1000** m (= 200 mm/h x 30 min = total rainfall
  of 100 mm averaged over the catchment), remaining constant
  afterwards. By default the outer rim of the computational domain is
  an impermeable wall, so this catchment is a **closed vessel with no
  water outlet**; the constant S column confirms mass conservation.
- Meanwhile the h_max column keeps growing from 8 m to 33 m: the water
  that cannot get out keeps accumulating somewhere.

The depth distribution at the final time (`result/H9998.txt`) shows
where it accumulates.

![Step 1: depth after 6 hours](../figs/step1_hend.png)

Just upstream of the catchment outlet (the northeast corner), ponded
water over 30 m deep has grown. This ponding of runoff dammed by the
wall will be resolved in Step 6 by setting a boundary condition. Until
then we proceed with the outlet ponding as a known artifact (it hardly
affects the measurements further upstream).

### Why depression filling is necessary

If you replace `fn_z` in `&list_geoinfo` with `Chichibu_200m_raw.tif`,
you can run on the original DEM without depression filling (since this
reads a GeoTIFF, the easiest way is to try it in Step 2's
`en/param_step2.txt`). Comparing the maximum depth distributions:

| Depression-filled (filled) | Unprocessed (raw) |
|---|---|
| ![filled](../figs/step1_hmax_filled.png) | ![raw](../figs/step1_hmax_raw.png) |

With the filled DEM, tributaries gather into the main stem and a single
river network heading for the outlet is drawn; with the raw DEM the
water gets trapped in depressions all over the catchment and the river
network is chopped into pieces. The maximum velocity also drops to
about 1.5 m/s toward the end, showing that the flow has died across the
whole catchment.

In general, when the terrain slope is steep and the cell size is large,
the step-like jumps of the DEM become large. Once the jumps exceed the
order of the water depth, the flow is severely obstructed, so **prior
depression filling is essential for runoff computations**.

Note that in ordinary structured-grid models, where water cannot move
diagonally across the grid, a DEM filled with the common D8
(eight-direction flow) method of GIS software can still leave water
stuck on diagonal flow paths, requiring extra depression processing or
higher resolution. The ENC grid exchanges water in eight directions, so
it is a natural match for D8: **a D8-filled DEM can be used as is**.

## Step 2: GeoTIFF input/output and representing the channel

`en/param_step2.txt` switches the input/output to GeoTIFF and adds the
channel mask and roughness.

```
&list_sysparam
  ...
  f_input_mode = 4           ! matrix input format (1: text, 2: bil, 4: geotiff)
  f_output_mode = 5          ! matrix output format (1: text, 2: bil, 4: geotiff)
/

&list_geoinfo
  ...
  f_rntype = 0         ! roughness type (0: default constant, 1: file, 2: from land use)
  rn0 = 0.05           ! constant roughness value
  rn0_rw = 0.02        ! constant roughness for channel-mask cells

  fn_z = "Chichibu_200m_filled.tif"        ! ground elevation file name
  fn_mask = "Chichibu_200m_basin.tif"      ! domain mask file name
  fn_rw = "Chichibu_200m_river.tif"        ! channel mask file name
/
```

- With `f_input_mode = 4` / `f_output_mode = 5`, distributed data are
  read and written as GeoTIFF (output mode 5 writes both text and
  GeoTIFF). The output `.tif` files carry over the coordinate reference
  information, so **you can simply drag them into a GIS such as QGIS
  and they overlay on the map**.
- Roughness is a two-tier setup: the base value `rn0 = 0.05`
  (mountain/wildland-like) is overridden on channel cells by
  `rn0_rw = 0.02` (channel-like). `rn0_rw` overrides channel cells
  regardless of how roughness is given (constant, file, or land-use
  conversion).
- At this stage the channel mask `fn_rw` is used only to swap the
  roughness. From here you can refine step by step toward incision
  below the terrain (`depth_rw`) or subgrid channels (`fn_channel`)
  ([users guide](../../../docs/en/users_guide.md)).

When you run it, the numbers on screen change slightly from Step 1
(because the roughness changed). The result directory now contains
`H0001.tif` and friends.

## Step 3: Measurement and distributed output

Places where you want time series of discharge or depth are specified
in advance with **probes** (points) and **flux transects** (lines).
`en/param_step3.txt` places four of each along the main stem.

```
&list_sysparam
  ...
  dt_recrd_c = "1 min"       ! probe output interval

  f_out_h = 1                ! file output (depth H0001)
  f_out_vv = 1               ! file output (velocity magnitude V0001)
  f_out_qq = 1               ! file output (discharge magnitude Q0001)
  f_out_cn = 1               ! file output (Courant number Cn0001)
  f_out_hmax = 1             ! file output (maximum depth H9999)
  f_out_vvmax = 1            ! file output (maximum velocity V9999)
/

&list_record
  ! probe position type (0: cell indices, 1: real coordinates (m))
  ! probe positions (x, y)
  pbxytype = 0
  pbxy(:,1) =  82, 105
  pbxy(:,2) = 107, 102
  pbxy(:,3) = 147, 103
  pbxy(:,4) = 216,  40

  ! flux transect coordinate type (0: cell indices, 1: real coordinates (m))
  ! flux transect endpoints (right-bank x, right-bank y, left-bank x, left-bank y)
  flxytype = 0
  flxy(:,1) =  82, 106,   82, 103
  flxy(:,2) = 107, 103,  107, 100
  flxy(:,3) = 147, 105,  147, 102
  flxy(:,4) = 216,  43,  216,  37
/
```

Cell indices are **1-based**, Fortran style (raster row/column numbers
in QGIS are 0-based, so add 1 when using cell indices looked up in a
GIS). For a transect, "the right side looking from the start point
toward the end point is positive", so writing it in the right-bank to
left-bank direction makes downstream discharge positive. Specification
in real coordinates (m) (`pbxytype = 1` / `flxytype = 1`) is also
available ([the record chapter of the users
guide](../../../docs/en/users_guide/record.md)).

When you run it, the numbers on screen match Step 2 **exactly**:
measurement and file output have no effect whatsoever on the
computation itself. The results now include `fluxes/flux0001.csv`
(transect discharge time series) and `probes/probe0001.csv` (probe
depth and velocity time series).

```bash
gnuplot -p -c Plot_flux.plt result
```

displays the hydrographs of the four transects in turn (the bundled
`../Plot_flux.plt` / `../Plot_map.plt` are scripts for visual
inspection of results; run them from the case directory).

![Step 3: hydrographs at each transect](../figs/step3_transects.png)

We obtained catchment-scale flood routing at 1-minute resolution, with
the flood wave growing and lagging from upstream transect 1 to
downstream transect 4.

## Step 4: Parameter tuning

Looking closely at the screen output of Step 3, **the ex_flux column
grows over time** (up to 190 counts per 30 minutes near the end).
ex_flux counts the events where "the outflow computed from the momentum
equation was about to exceed the water volume of the cell and was
therefore limited". It is a safety device, so mass is conserved, but
frequent triggering is a sign that the computation is getting rough. In
this case the usual remedies -- reducing the time step dt, reducing the
adaptive Runge-Kutta threshold `p_adprunge_thresh` -- do not help. What
worked was **reducing the threshold depth dd and the virtual depth
dv**.

```
&list_sysparam
  ...
  dd = 0.0001                ! water movement is computed above this depth (threshold depth)
  dv = 0.0001                ! depths below this are forced to this value (virtual depth)
/
```

The defaults (both 0.001) are reduced to 1/10. The smaller these
values, the more carefully thin films of water are treated, which
improves accuracy; but there are also cases where more wetted cells
mean longer computation time. Choose them as a balance of accuracy and
speed (in this example, running `en/param_step4.txt` brings ex_flux
down to 0).

The other adjustment is **upwinding of the advection term**.

```
&list_enc
  p_adv_upwind_index = 0.0        ! upwind differencing fraction (0.0 ~ 1.0)
  p_adprunge_thresh = 1.5         ! adaptive Runge-Kutta threshold (1.1 ~)
/
```

In computations with large cells the contribution of the advection term
becomes relatively small compared to the other terms, while the
numerical diffusion of upwind differencing (the default is a
`p_adv_upwind_index = 0.5` blend) blunts the flood waveform
excessively. So we reduce the upwind fraction as far as stability
allows (here 0 = central differencing). Solving with the diffusive wave
(`f_govequation = 1` in `&list_sysparam`), which drops the advection
term altogether, is another option.

![Step 4: effect of parameter tuning](../figs/step4_hydro.png)

After tuning (`en/param_step4.txt`), the peak stands up and the blunted
waveform becomes sharp (an 18% difference in peak discharge at transect
4). In real-terrain computations on coarse grids, **waveform blunting
is sensitive to the numerical settings** like this. Before tuning
roughness against observed hydrographs, it is important to remove the
blunting that comes from the numerical settings.

## Step 5: Rainfall interception and subsurface infiltration

So far, all the rain that fell has run off. In a real catchment,
interception by the canopy and infiltration into the ground reduce the
runoff. `en/param_step5.txt` stacks the two simplest loss models.

```
&list_sysparam
  ...
  fn_intercept = "-"         ! rainfall interception settings file
  fn_gwflow = "-"            ! groundwater settings file
/

&list_intercept
  f_icmodel = 1              ! 1: fixed interception rate model
/
&list_intercept_fixed
  ic_alpha = 0.2             ! interception rate (effective rainfall = (1-alpha)P)
/

&list_gwflow
  f_gwvertical = 1           ! 1: bucket model
/
&list_gwflow_bucket
  gw_infil_mmh = 5.0         ! infiltration capacity (mm/h)
  gw_capacity = 0.2          ! subsurface storage capacity (water-column equivalent depth) (m)
/
```

Enabling features follows the common ENCflow convention: write `fn_*`
to enable, omit it to disable completely (zero additional memory and
computation time). When you run it, the water storage display on screen
changes from one column to **three columns**.

```
time, progress, S_surf(m), S_grnd(m), S_total(m), Runge, ex_flux, Cn_max, h_max(m), V_max(m/s)
  0:00:00.00   0.0%    0.0000     0.0000     0.0000    0.0%      0    0.0000    0.0000    0.0000
  0:30:00.00   8.3%    0.0365     0.0024     0.0389   97.7%      0    0.2246    0.8761    5.3816
  1:00:00.00  16.7%    0.0751     0.0049     0.0800   11.5%      0    0.4056    4.2749   11.3883
  1:30:00.00  25.0%    0.0728     0.0072     0.0800   26.3%  17319    0.4968    5.5541   12.6021
  ...
  6:00:00.00 100.0%    0.0689     0.0111     0.0800   10.3%   7285    0.6518   27.0961   11.8937
```

- `S_surf` is surface water, `S_grnd` is subsurface storage, and
  `S_total` is their sum. After the rain ends, S_total stays constant
  at **0.0800** m -- 80% of the 100 mm total rainfall, i.e. it matches
  the effective rainfall after removing the interception rate
  alpha = 0.2, confirming that the total is conserved even as water
  moves between the surface and the subsurface.
- S_surf decreases and S_grnd increases over time -- you can read the
  progress of infiltration directly.

![Step 5: effect of interception and infiltration](../figs/step5_hydro.png)

In the hydrograph the peak discharge roughly halves (6,080 to 2,970
m^3/s). Interception cuts the total by 20%, and infiltration keeps
sucking up the thinly spread hillslope water, so both the rising limb
and the recession drop.

Two changes catch the eye: the ex_flux column jumps to 10,000-20,000
counts per 30 minutes, and **fine oscillations** appear on the
hydrograph. These are explained together in the second half of Step 6.

## Step 6: Boundary condition at the catchment outlet

We now resolve the outlet ponding (h_max of about 27 m) that we have
been turning a blind eye to since Step 1. The catchment outlet is not
on the outer rim (the four edges) of the computational domain but in
its interior, so instead of an edge boundary condition we use
**prescribed-stage cell groups**. `en/param_step6.txt` fixes the water
level of the two outlet channel cells at a low value, turning them into
a "drain".

```
&list_sysparam
  ...
  fn_boundary = "-"          ! boundary condition settings file
/

&list_bound_stage
  ! group 1: catchment outlet (level below the bed for perfect drainage)
  stage_cell(:,1,1) = 239, 19
  stage_cell(:,2,1) = 240, 19
  stage_eta(1) = 111.0
/
```

The outlet cell indices were determined by overlaying the channel mask
and the DEM in a GIS and reading off "the most downstream channel cells
inside the catchment mask" (remember to convert to 1-based indices as
noted above). `stage_eta` is specified as an elevation. Cells whose
prescribed level is below the bed are always empty, acting as a
"perfect drain" (here 111 m, lower than the 113 m bed of the upstream
neighbor cell, so arriving water is removed from the system
immediately). Running it gives:

```
time, progress, S_surf(m), S_grnd(m), S_total(m), Runge, ex_flux, Cn_max, h_max(m), V_max(m/s)
  ...
  3:00:00.00  50.0%    0.0650     0.0095     0.0745   20.5%  14129    0.4305    5.8031    9.8904
  6:00:00.00 100.0%    0.0317     0.0110     0.0428   10.3%   7278    0.3185    4.7565    5.6587
```

- S_total now decreases -- that is the water that left the system
  through the outlet.
- h_max drops from 27 m to 4.8 m. The disappearance of the ponding can
  also be confirmed in the depth distribution.

| Step 5 (no outlet) | Step 6 (perfect drain) |
|---|---|
| ![step5](../figs/step6_hend_step5.png) | ![step6](../figs/step6_hend.png) |

The hydrographs at the upstream transects 1-4 barely change from Step 5
(the outlet ponding affects only a very small area at the far
downstream end).

Note that if you prescribe the water level as a time series
(`stage_val`), this also serves as an open boundary supplying a
downstream river stage or a tide level. For the use of edge boundaries
(free outflow, long-wave radiation), inflow boundaries, and so on, see
[the boundary condition chapter of the users
guide](../../../docs/en/users_guide/boundary.md).

### About the fine oscillations in the hydrograph

From Step 5 on, the 1-minute hydrographs carry fine oscillations. They
do not disappear when the infiltration capacity is changed, and they
remain in Step 6 with the outlet in place. This is not a defect of the
model but **a phenomenon you will universally encounter in runoff
computations using real terrain data**, so let us explain what it is.

![Step 6: 1-minute discharge oscillations and moving average](../figs/step6_osc.png)

The cause lies in the terrain data. Along the channels of a
depression-filled DEM, "perfectly flat reaches" appear here and there
(places where the original DEM recorded a river water surface, a gorge,
or a reservoir as flat, or where a depression was filled in). In the
computation, a "pond" several meters deep forms on such a flat reach,
and the pond becomes an oscillator with responses such as seiching and
fluctuating overtopping. When a **spatially distributed loss** such as
subsurface infiltration is added, the water balance between the ponds
and the rapids connecting them is constantly perturbed, and the
oscillations, amplified toward downstream, ride on the hydrograph. At
the same time, cells whose water film has been thinned by infiltration
frequently trip the safety device, so ex_flux also jumps up -- but this
is the protection mechanism working normally, and mass is conserved
(as the S_total column confirms).

Deal with it in stages.

1. **For the time being, post-processing (smoothing) of the output is
   sufficient.** The oscillations do not harm the water balance of the
   computation and do not affect the time scales that matter in runoff
   analysis (tens of minutes and longer). Overlay a moving average when
   plotting.

   ```gnuplot
   set datafile separator comma
   N = 11                     # window width (points) = 11 minutes
   array A[N]
   ma(x) = (A[(int($0) % N) + 1] = x, $0 < N-1 ? NaN : (sum [i=1:N] A[i]) / N)
   plot "result/fluxes/flux0004.csv" us 2:3 w l title "1-min values", \
        "" us ($2 - (N-1)/2.0):(ma($3)) w l lw 2 title "11-min moving average"
   ```

   This works with the array feature of gnuplot 5.2 and later alone. A
   ring buffer indexed by the row number `$0` takes the trailing N-point
   average, and the x coordinate is shifted back by (N-1)/2 minutes to
   center it (so the peak time does not shift). Drawing the raw values
   on top also shows the reader what the smoothing removed.

   ![Same, zoomed](../figs/step6_osc_zoom.png)

2. **The fundamental remedy is improving the terrain data.**
   Preprocessing the channels so that the longitudinal profile is
   monotone (eliminating the flat reaches), or moving the channels to
   subgrid channels (`fn_channel`) with an independently specified bed
   profile, removes the flat ponds themselves.

3. The choice of measurement locations also mitigates it. A transect
   placed on a flat reach (pond) several meters deep picks up the
   pond's surface motion directly, so **place transects on ordinary
   channel reaches with a longitudinal slope**.

## Closing remarks

In this tutorial we went once around the standard workflow of a
catchment computation with real terrain data: data preparation
(depression filling) -> minimal configuration -> measurement -> tuning
of numerical settings -> adding physical processes -> boundary
conditions. From here:

- Refining the groundwater model (Green-Ampt, lateral flow), roughness
  distribution from land use, subgrid channels, and more --
  [users guide](../../../docs/en/users_guide.md)
- How to write the namelists of each feature --
  [examples/List_samples/](../../../examples/List_samples/)
- To run a large computation in parallel with MPI:
  `mpirun -np 4 ./encflow_mpi en/param_step6.txt` (the results match
  the serial run bit for bit)

The figures of this document (`../figs/`) can be regenerated in one go
with `./Fig_chichibu.sh` run from the case directory (gnuplot is
required; it runs the same computations as in the text, in order, and
draws the figures).
