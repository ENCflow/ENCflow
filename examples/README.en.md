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
| [nest_reflect/](nest_reflect/) | A Gaussian wave crossing the interface of two-way nested grids at ratios 3 and 5; error and reflection against a uniform fine grid; one-way band vs Flather; non-hydrostatic band | Nesting fn_nest (docs/en/users_guide/nest.md) |
| [tsunami_town/](tsunami_town/) | Destruction of wooden houses and the transport and deposition of debris as a tsunami runs up through a town | Building destruction and debris fn_bldgdebris, tide |
| [timberyard/](timberyard/) | Timber influx from a log yard into a town by a storm surge (Isewan typhoon type) | Driftwood fn_driftwood, tide |
| [sewer_hybrid/](sewer_hybrid/) | Urban drainage with a trunk main and a branch network in the same conduit continuum layer | Conduit continuum layer f_gwconduit |
| [qanat/](qanat/) | An idealised qanat (groundwater-collecting gallery) | Conduit continuum layer, groundwater |

## Suggested order by level

- **Beginner**: [benchmark/](benchmark/) (shallow water and rainfall only; compared with analytical solutions).
- **Intermediate** (one feature at a time): [sewer_hybrid/](sewer_hybrid/) and [qanat/](qanat/) (groundwater and conduits), [nest_reflect/](nest_reflect/) (nesting).
- **Advanced** (chains of processes and comparisons): [tsunami_fault/](tsunami_fault/) → [tsunami_coast/](tsunami_coast/) → [landslide_tsunami/](landslide_tsunami/) (tsunami generation and the non-hydrostatic correction), [tsunami_town/](tsunami_town/) and [timberyard/](timberyard/) (house destruction and driftwood), [ashfall_lahar/](ashfall_lahar/) and [badland/](badland/) (sediment and landscape evolution).

The full learning path by level is in the "Learning path" of [docs/en/tutorial.md](../docs/en/tutorial.md).
To find the feature combination for a phenomenon, see the
[use-case gallery](../docs/en/users_guide/usecases.md); for the settings of
each feature, the [User's Guide](../docs/en/users_guide.md).
