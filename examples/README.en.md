# examples/ — sample configurations and worked examples

[日本語](README.md)

A collection of examples for learning how to use ENCflow. Each directory
holds a README, parameter files, scripts that build the inputs and
scripts that plot the results. Verification cases with regression
references are in [test/](../test/README.en.md); step-by-step teaching
material is in [tutorials/](../tutorials/).

Every example runs the same way.

```bash
cd examples/<name>
make            # link the executables from bin/ and build the inputs
./encflow param.txt
python3 plot_results.py   # plotting (where provided)
```

| Directory | Contents | Main features |
|---|---|---|
| [List_samples/](List_samples/) | Annotated samples of every namelist (one file per group; English in en/) | All features |
| [benchmark/](benchmark/) | Three rainfall-runoff benchmarks with analytical solutions: a plane slope (h-plane), a V-shaped catchment (v-shaped) and a V-shaped valley (v-valley) | Shallow water, rainfall |
| [badland/](badland/) | Badland-type landscape evolution: rainfall on a plateau and steep scarp carves valleys | Dry hillslope erosion f_splash |
| [ashfall_lahar/](ashfall_lahar/) | Ashfall → rainfall → erosion of the ash layer → mudflow (lahar) generation and deposition | Debris flow f_debris, rainfall |
| [landslide_tsunami/](landslide_tsunami/) | Landslides and debris flows plunging into water and the resulting tsunami: four subaerial and submarine patterns plus non-hydrostatic variants | Moving bed layer f_bedslide, non-hydrostatic correction |
| [tsunami_fault/](tsunami_fault/) | Tsunami generation from fault parameters: hydrostatic, instantaneous and non-hydrostatic runs, and the coordinate patterns of fault2disp | Prescribed bed motion fn_bedmotion, utils/fault2disp |
| [tsunami_coast/](tsunami_coast/) | Coastal subsidence and uplift versus the offshore fault tsunami, with their time lag; flooding of the subsided bay-head plain | Prescribed bed motion fn_bedmotion |
| [levee_breach/](levee_breach/) | Breaching a levee present as elevation in a high-resolution DEM (a resolved levee) with prescribed bed motion; comparison with &list_channel_breach on a virtual wall | Prescribed bed motion fn_bedmotion, channel breach |
| [nest_reflect/](nest_reflect/) | A Gaussian wave crossing the interface of two-way nested grids at ratios 3 and 5; error and reflection against a uniform fine grid; one-way band vs Flather; non-hydrostatic band | Nesting fn_nest (docs/en/users_guide/nest.md) |
| [tsunami_town/](tsunami_town/) | Destruction of wooden houses and the transport and deposition of debris as a tsunami runs up through a town | Building destruction and debris fn_bldgdebris, tide |
| [timberyard/](timberyard/) | Timber influx from a log yard into a town by a storm surge (Isewan typhoon type) | Driftwood fn_driftwood, tide |
| [sewer_hybrid/](sewer_hybrid/) | Urban drainage with a trunk main and a branch network in the same conduit continuum layer | Conduit continuum layer f_gwconduit |
| [qanat/](qanat/) | An idealised qanat (groundwater-collecting gallery) | Conduit continuum layer, groundwater |
| [meander/](meander/) | How a sinusoidal channel in a floodplain deforms under bed load, the direction correction and angle-of-repose avalanching (outer-bank pools, inner-bank bars, bank retreat). Stage 4 of the meander plan | bed load f_fluvial, fluv_slope, f_secflow, f_repose, f_berode |
| [meander_cutoff/](meander_cutoff/) | A meander loop with a narrow neck is cut off by a flood; the old loop becomes slack water and its ends start to fill | same + inflow time series |

## Examples of chained processes

Set-ups that show ENCflow's characteristic "several processes chained in
one run" (for reference after reading the chapters).

- Tsunami → house destruction → debris: [tsunami_town/](tsunami_town/). Storm surge → driftwood → town: [timberyard/](timberyard/).
- Ashfall → rainfall → lahar: [ashfall_lahar/](ashfall_lahar/). Rainfall → dry-slope erosion → landscape evolution: [badland/](badland/).
- Fault → tsunami → inundation: [tsunami_fault/](tsunami_fault/), [tsunami_coast/](tsunami_coast/). Slope failure → entry into water → tsunami: [landslide_tsunami/](landslide_tsunami/).
- Flood → levee breach → inundation: [levee_breach/](levee_breach/).
- Rainfall → sewer (conduits) → surcharge and drainage: [sewer_hybrid/](sewer_hybrid/). Groundwater → qanat collection: [qanat/](qanat/).
- Single-feature analytical benchmarks: [benchmark/](benchmark/). Grid refinement (nesting): [nest_reflect/](nest_reflect/).

To find the feature combination for a phenomenon, see the
[use-case gallery](../docs/en/users_guide/usecases.md); for the settings of
each feature, the [User's Guide](../docs/en/users_guide.md).
