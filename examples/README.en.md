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
| [vz_tani2023/](vz_tani2023/en/README.md) | Reproduction of the VZ runoff model of Tani (2023): recomputes with the same settings all seven events of the paper (sprinkling on a small hillslope KIEX, zero-order catchment MREX and MR1, Tatsunokuchi-yama TY1 and TY2, Kiryu KI1 and KI2) and compares them with the calculated runoff rates and pressure heads of the paper (HYDRUS-1D). The numbers of the paper are extracted from the figures of the PDF obtained by the user (not shipped) | Vertical unsaturated flow (VZ) runoff fn_vz (shared column, linear distribution of soil depth) |
| [badland/](badland/en/README.md) | Badland-type landscape evolution: rainfall on a plateau and steep scarp carves valleys. Self-organisation of valleys from white noise, the valley-spacing selection rule (spl_lc), grid convergence, long-term growth of deep valleys and sharp ridges | Dry hillslope erosion f_splash (spl_lc, spl_zbase) |
| [badland_storm/](badland_storm/en/README.md) | A cliff where surface flow appears only during downpours (lower infiltration capacity): does it stop the dry erosion or turn the cliff into a gully network? (contrast to badland) | f_splash + f_wash, f_suspend, Green-Ampt, rainfall series |
| [badland_round/](badland_round/en/README.md) | Rounded-crest badlands (swelling-clay type) where lower hills become domes: the length scale L set by the ratio of advective incision to creep (diffusion) rounds the hills smaller than L first (contrast to the sharp ridges of badland); also a contrast with banded hard/soft strata (spl_strata) | f_splash + f_creep (+ spl_strata), Green-Ampt |
| [mesa/](mesa/en/README.md) | Mesa and butte formation: a cap rock (spl_strata) keeps a flat top and parallel retreat of vertical cliffs; the plateau shrinks to an isolated butte and a pinnacle. Contrasts without strata, with a hard mid layer, with saturated amplification, and with rockfall and talus (window version, support scheme = vertical cliff + step) | f_splash (spl_strata, spl_ksat) + f_creep + f_rockfall (rf_rc, rf_fface), Green-Ampt |
| [karst/](karst/en/README.md) | Formation of a doline field on a limestone plateau: under repeated representative storms, infiltrating water dissolves the surface diffusely while the water that collects in depressions and disappears underground through sinks deepens them selectively (self-organization of karst landforms and internal drainage) | limestone dissolution f_dissol, conduit continuum layer (sinks), Green-Ampt, periodic forcing t_cycle_c |
| [tower_karst/](tower_karst/en/README.md) | Bare-rock towers left standing on a plain (tower karst): the rain of the towers infiltrates on the plain at their feet, so only the plain and the feet dissolve, while lateral dissolution and rock-wall collapse make the walls retreat with debris aprons and moats. Infiltration caps the intake, so morfac can be large | limestone dissolution f_dissol (dissol_lat), rock-wall collapse f_rockfall, Green-Ampt conductivity map, periodic forcing |
| [ashfall_lahar/](ashfall_lahar/en/README.md) | Ashfall → rainfall → erosion of the ash layer → mudflow (lahar) generation and deposition | Debris flow f_debris, rainfall |
| [landslide_tsunami/](landslide_tsunami/en/README.md) | Landslides and debris flows plunging into water and the resulting tsunami: four subaerial and submarine patterns plus non-hydrostatic variants | Moving bed layer f_bedslide, non-hydrostatic correction |
| [tsunami_fault/](tsunami_fault/en/README.md) | Tsunami generation from fault parameters: hydrostatic, instantaneous and non-hydrostatic runs, and the coordinate patterns of fault2disp | Prescribed bed motion fn_bedmotion, utils/fault2disp |
| [tsunami_coast/](tsunami_coast/en/README.md) | Coastal subsidence and uplift versus the offshore fault tsunami, with their time lag; flooding of the subsided bay-head plain | Prescribed bed motion fn_bedmotion |
| [levee_breach/](levee_breach/en/README.md) | Breaching a levee present as elevation in a high-resolution DEM (a resolved levee) with prescribed bed motion; comparison with &list_channel_breach on a virtual wall | Prescribed bed motion fn_bedmotion, channel breach |
| [estuary_barrage/](estuary_barrage/en/README.md) | How the presence of an estuary barrage affects the salt wedge travelling up a tidal river and the intrusion of salt water from the bed into the surrounding aquifer (eight cases: with/without barrage × bed salt exchange none / on / mixing ratio / clogged river bed) | Fresh and salt water layers fn_salt (surface salt layer, subsurface salt zone, exchange split f_salt_exch), tide, Green-Ampt, lateral groundwater flow, river-bed exchange capacity f_gwbed |
| [nest_reflect/](nest_reflect/en/README.md) | A Gaussian wave crossing the interface of two-way nested grids at ratios 3 and 5; error and reflection coefficient against a uniform fine grid | Nesting fn_nest (docs/en/users_guide/nest.md) |
| [tsunami_town/](tsunami_town/en/README.md) | Destruction of wooden houses and the transport and deposition of debris as a tsunami runs up through a town | Building destruction and debris fn_bldgdebris, tide |
| [timberyard/](timberyard/en/README.md) | Timber influx from a log yard into a town by a storm surge (Isewan typhoon type) | Driftwood fn_driftwood, tide |
| [sewer_hybrid/](sewer_hybrid/en/README.md) | Urban drainage with a trunk main and a branch network in the same conduit continuum layer | Conduit continuum layer f_gwconduit |
| [qanat/](qanat/en/README.md) | An idealised qanat (groundwater-collecting gallery) | Conduit continuum layer, groundwater |
| [meander/](meander/en/README.md) | Meander development of a sinusoidal channel in a floodplain: outer-bank retreat and inner-bank bar growth, fixation of the bars by alternating floods and low flows, and conversion of the bars into floodplain by sediment feed; nine configurations | Bed-load direction correction fluv_slope, f_secflow, bank erosion f_berode, angle-of-repose avalanching f_repose, fixation f_fixation, sediment feed |
| [meander_cutoff/](meander_cutoff/en/README.md) | A meander loop with a narrow neck is cut off by a flood; the old loop becomes slack water and its ends start to fill | same + inflow time series |
| [delta/](delta/en/README.md) | A river-mouth delta built by a sediment-laden river entering a still basin: mouth bar, bifurcation, lobe growth and channel switching. Five configurations: fan versus bird-foot by the sand/mud ratio, and the stabilisation of distributaries by discharge variation and fixation (decay while submerged, bank coefficient). Record: docs/delta_plan.md (Japanese) | sea as ordinary cells + initial water level, capacity feed fluv_bcfeed, suspended mud inflow_cs + f_bedfines, fluv_slope, f_repose, f_fixation (fix_tdec, fix_ctau_bank), long-wave radiation edge |
| [bedrock_cover/](bedrock_cover/en/README.md) | The cover effect in the bedrock channels of mountain streams (tools and cover): the amount of supply (the hump of the steady incision rate), the timing of supply (constant supply versus pulses with the same total), the initial cover and the retreat of a step (knickpoint), compared in incised channels one cell wide placed side by side | bedrock incision by flowing water f_rockinc (plucking, cover, abrasion), bedload f_fluvial, sediment feed at a segment inflow inflow_qb |
| [mountain_valley/](mountain_valley/en/README.md) | A V-shaped valley in rising mountains where the hillslopes (soil production by weathering, depth-dependent creep) and the stream (bedrock incision, cover) move together. The steady hillslopes and stream slope are compared with the predictions for the hillslopes alone and the stream alone; the supply from the hillslopes steepens the stream and increases abrasion, and the stream and the hillslopes respond to a base-level fall with different delays. The second part compares the steady slope of a stream under the same mean supply given constantly and in pulses (pulses steepen it where abrasion matters) | weathering f_wthr (fn_wthr), depth-dependent creep creep_hstar, bedrock incision by flowing water f_rockinc, bedload f_fluvial, distributed uplift fn_uplift |
| [debris_bedrock/](debris_bedrock/en/README.md) | One debris flow is released into a stream whose slope eases in steps, to see where and how much the rock erodes. The erosion is concentrated in the steep reaches, and a deposit protects the rock until it is stripped. Effects of the resistance law and the threshold, and a comparison with a clear-water flood with the same discharge. The second half chains floods and debris flows into long-term runs: how the steady slope of an uplifting stream eases with the debris-flow frequency, and how boulder deposits hold the slope at the debris-flow equilibrium slope | debris flows f_debris (Takahashi–Nakagawa, Coulomb + Manning), rock erosion by debris flows rock_kdb of f_rockinc |

## Examples of chained processes

Set-ups that show ENCflow's characteristic "several processes chained in
one run" (for reference after reading the chapters).

- Tsunami → house destruction → debris: [tsunami_town/](tsunami_town/en/README.md). Storm surge → driftwood → town: [timberyard/](timberyard/en/README.md).
- Ashfall → rainfall → lahar: [ashfall_lahar/](ashfall_lahar/en/README.md). Rainfall → dry-slope erosion → landscape evolution: [badland/](badland/en/README.md). A cliff where surface flow joins only during downpours: [badland_storm/](badland_storm/en/README.md). Hills rounded by creep: [badland_round/](badland_round/en/README.md). Cap-rock mesa to butte: [mesa/](mesa/en/README.md). Storm → ponding → sinks → dissolution → dolines: [karst/](karst/en/README.md). Bare-rock towers → dissolution at the feet → collapse → tower retreat: [tower_karst/](tower_karst/en/README.md). Sediment supply → cover and tools → bedrock incision: [bedrock_cover/](bedrock_cover/en/README.md). Uplift → weathering → creep → cover and incision in the stream → a steady valley: [mountain_valley/](mountain_valley/en/README.md). Debris flow → stripping of the deposit → rock erosion → steady slope by frequency: [debris_bedrock/](debris_bedrock/en/README.md).
- Fault → tsunami → inundation: [tsunami_fault/](tsunami_fault/en/README.md), [tsunami_coast/](tsunami_coast/en/README.md). Slope failure → entry into water → tsunami: [landslide_tsunami/](landslide_tsunami/en/README.md).
- Flood → levee breach → inundation: [levee_breach/](levee_breach/en/README.md).
- Tide → salt wedge travelling upstream → infiltration through the bed → salinization of the banks (blocked by an estuary barrage): [estuary_barrage/](estuary_barrage/en/README.md).
- Rainfall → sewer (conduits) → surcharge and drainage: [sewer_hybrid/](sewer_hybrid/en/README.md). Groundwater → qanat collection: [qanat/](qanat/en/README.md).
- Single-feature analytical benchmarks: [benchmark/](benchmark/). Grid refinement (nesting): [nest_reflect/](nest_reflect/en/README.md).

To find the feature combination for a phenomenon, see the
[use-case gallery](../docs/en/users_guide/usecases.md); for the settings of
each feature, the [User's Guide](../docs/en/users_guide.md).
