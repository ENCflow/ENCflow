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
| [List_samples/](List_samples/) | Annotated samples of every namelist (one file per group), used as a dictionary of settings and defaults (English in en/) | All features |
| [benchmark/](benchmark/) | Three rainfall-runoff problems (plane slope, V-shaped catchment, V-shaped valley) checked against analytical solutions | Shallow water, rainfall |
| [vz_tani2023/](vz_tani2023/en/README.md) | Reproduction of the VZ runoff model of Tani (2023): runoff rates and pressure heads of all seven events compared with the paper | Vertical unsaturated flow (VZ) runoff fn_vz (shared column, linear distribution of soil depth) |
| [badland/](badland/en/README.md) | Badland formation as rainfall carves valleys into a plateau and scarp: self-organised valleys, their spacing rule and sharp ridges | Dry hillslope erosion f_splash (spl_lc, spl_zbase) |
| [badland_storm/](badland_storm/en/README.md) | A low-infiltration cliff where surface flow appears only in downpours: does dry erosion stop or become a gully network? (contrast to badland) | f_splash + f_wash, f_suspend, Green-Ampt, rainfall series |
| [badland_round/](badland_round/en/README.md) | Rounded-crest (swelling-clay) badlands: hills lower than the length scale set by incision versus creep become domes | f_splash + f_creep (+ spl_strata), Green-Ampt |
| [mesa/](mesa/en/README.md) | A cap rock keeps a flat top and vertical cliffs whose parallel retreat shrinks the plateau to a mesa, a butte and a pinnacle | f_splash (spl_strata, spl_ksat) + f_creep + f_rockfall (rf_rc, rf_fface), Green-Ampt |
| [karst/](karst/en/README.md) | A doline field on a limestone plateau: water that collects in depressions and sinks underground deepens those spots selectively | limestone dissolution f_dissol, conduit continuum layer (sinks), Green-Ampt, periodic forcing t_cycle_c |
| [tower_karst/](tower_karst/en/README.md) | Bare-rock towers on a plain (tower karst): only the plain and their feet dissolve, so the towers rise above the plain and moats and holes form at the feet | limestone dissolution f_dissol (dissol_lat), rock-wall collapse f_rockfall, Green-Ampt conductivity map, periodic forcing |
| [stone_forest/](stone_forest/en/README.md) | Stone forest: a joint map (soluble fraction × 6) splits a flat limestone plateau into pillars and clefts; the clefts deepen, the walls collapse and fill them, the talus dissolves and the pillar height saturates | limestone dissolution f_dissol (multiplier map fn_dissol), bedrock collapse f_rockfall (rf_bedrock), talus dissolution, quasi-steady forcing |
| [ashfall_lahar/](ashfall_lahar/en/README.md) | Rain on an ash-covered, low-infiltration slope erodes the ash into a lahar that deposits on the fan; effect of a check dam | Debris flow f_debris (pore water with the groundwater computation f_dbwet=2), Green-Ampt infiltration capacity, rainfall, check dam (terrain), four-neighbour grid p_diagratio |
| [landslide_tsunami/](landslide_tsunami/en/README.md) | Tsunamis from subaerial and submarine landslides and debris flows entering water: four patterns plus non-hydrostatic variants | Moving bed layer f_bedslide, non-hydrostatic correction |
| [tsunami_fault/](tsunami_fault/en/README.md) | A tsunami generated from fault parameters: hydrostatic, instantaneous and non-hydrostatic runs and coordinate patterns compared | Prescribed bed motion fn_bedmotion, utils/fault2disp |
| [tsunami_coast/](tsunami_coast/en/README.md) | How the time lag between coastal subsidence/uplift and the offshore fault tsunami changes flooding of a subsided bay-head plain | Prescribed bed motion fn_bedmotion |
| [levee_breach/](levee_breach/en/README.md) | A flood overtops and breaches a levee, the landside floods and houses are swept away; effect of a secondary levee | Prescribed bed motion fn_bedmotion (breach of a resolved levee), building damage fn_bldgdebris (load criterion), building porosity fn_gv, channel breach &list_channel_breach (supplement) |
| [estuary_barrage/](estuary_barrage/en/README.md) | How an estuary barrage affects the salt wedge in a tidal river and salt intrusion from the bed into the surrounding aquifer | Fresh and salt water layers fn_salt (surface salt layer, subsurface salt zone, exchange split f_salt_exch), tide, Green-Ampt, lateral groundwater flow, river-bed exchange capacity f_gwbed |
| [nest_reflect/](nest_reflect/en/README.md) | A Gaussian wave crossing two-way nested grids (ratios 3 and 5): error and reflection against a uniform fine grid | Nesting fn_nest (docs/en/users_guide/nest.md) |
| [tsunami_town/](tsunami_town/en/README.md) | A tsunami destroys wooden houses, carries the debris inland and back to sea with the backwash; effect of raising the seawall | Building destruction and debris fn_bldgdebris (depth criterion, porosity feedback), building porosity fn_gv, tide fn_tide, driftwood fn_driftwood (supplement) |
| [timberyard/](timberyard/en/README.md) | A storm surge floats timber out of a timber yard over the seawall into a town (Ise Bay typhoon type); effect of countermeasures | Driftwood fn_driftwood (hydraulic release, deposition, refloating), building porosity fn_gv, tide fn_tide |
| [sewer_hybrid/](sewer_hybrid/en/README.md) | A schematic urban drainage run: a trunk main and branch network in one conduit continuum layer, with surcharge and drainage | Conduit continuum layer f_gwconduit |
| [qanat/](qanat/en/README.md) | The outflow of a qanat collecting the groundwater of a mountain-foot fan, and how a nearby pumping well makes it dwindle and dry up | Conduit continuum layer f_gwconduit (exchange-capacity map fn_gwc_leak, open outfall fn_gwc_outfall), layer 2 f_gwlayer2, well pumping f_gwpump |
| [catchment_metal/](catchment_metal/en/README.md) | Where heavy metals from a mine effluent and farmland go in a catchment and how the river concentration changes, adding one mechanism at a time (surface water, groundwater flow, sorption delay, tanks, particulate form), and whether tanks matter for dissolved and particulate metals | Water quality fn_wq (point and area sources, transport with infiltration, retardation wq_rg, settling wq_vs, re-suspension wq_wash_kf, ledger of export to the sea), Green-Ampt, lateral groundwater flow, subgrid channel width, sea mask |
| [meander/](meander/en/README.md) | Meander growth of a sinusoidal channel in a floodplain: outer-bank retreat, inner-bar growth and fixation, and conversion to floodplain | Bed-load direction correction fluv_slope, f_secflow, bank erosion f_berode, angle-of-repose avalanching f_repose, fixation f_fixation, sediment feed |
| [meander_cutoff/](meander_cutoff/en/README.md) | Meander loops are cut off by overbank flow in a flood or by bank retreat alone; the old loop becomes slack water and starts to fill | same + slump blocks f_rockfall, inflow time series |
| [delta/](delta/en/README.md) | A river-mouth delta built by a sediment-feeding river entering a basin: starting from a river mouth without waves, the sand/mud ratio, floods and vegetation, oblique waves, the wave field and tides are added one at a time to see which mechanisms each type of delta needs and how the shape changes | sea as ordinary cells + initial water level, capacity feed fluv_bcfeed, suspended mud inflow_cs + f_bedfines, fluv_slope, f_repose, f_fixation (fix_tdec, fix_ctau_bank), longshore transport fn_wave, coastal wave field fn_wavefield (f_wfsed, f_wfswash), tide level fn_tide |
| [bedrock_cover/](bedrock_cover/en/README.md) | Whether the amount, timing and initial cover of sediment supply speed up or hinder bedrock incision (tools and cover effects) | bedrock incision by flowing water f_rockinc (plucking, cover, abrasion), bedload f_fluvial, sediment feed at a segment inflow inflow_qb |
| [mountain_valley/](mountain_valley/en/README.md) | A V-shaped valley in rising mountains with weathering and creep on the hillslopes and bedrock incision in the stream, to a steady form | weathering f_wthr (fn_wthr), depth-dependent creep creep_hstar, bedrock incision by flowing water f_rockinc, bedload f_fluvial, distributed uplift fn_uplift |
| [debris_bedrock/](debris_bedrock/en/README.md) | Where and how much a debris flow erodes bedrock, and how debris-flow frequency changes the steady slope of the stream | debris flows f_debris (Takahashi–Nakagawa, Coulomb + Manning), rock erosion by debris flows rock_kdb of f_rockinc |
| [shield_volcano/](shield_volcano/en/README.md) | A shield volcano growing as the lava flows of intermittent eruptions with shifting vents and volumes pile up; the yield stress sets the shape. A lava dome of viscous lava compared with the analytic solution as a supplement | Lava flow fn_lavaflow (several vents lv_cell, lv_val, Bingham yield stress lv_tauy, solidification lv_wsol, lv_vsol) |
| [stratovolcano/](stratovolcano/en/README.md) | Lava flow → ashfall → storm erosion repeated 10 times builds a stratovolcano of stacked lava and ash layers; how the style of eruption (lava/ash proportion) and erosion change the shape and the internal layering. Finally, one lava flow with temperature is run over the terrain of the grown volcano, showing how its path is set by the unevenness of the terrain and how it stops as it cools | Lava flow fn_lavaflow (burying the soil layer under solidified lava; the temperature mode f_lvtemp in the final stage), ashfall by preprocessing, Green-Ampt, bedload f_fluvial + morfac, a driver chaining one computation per stage |

## Examples of chained processes

Set-ups that show ENCflow's characteristic "several processes chained in
one run" (for reference after reading the chapters).

- Tsunami → house destruction → debris transport and deposition → back to sea with the backwash (changed by the seawall and closing its opening): [tsunami_town/](tsunami_town/en/README.md).
- Storm surge → timber floats out of a timber yard → enters and settles in the town (changed by countermeasures): [timberyard/](timberyard/en/README.md).
- Ashfall → lowered infiltration → rainfall → lahar → deposition on the fan (trapped by a check dam): [ashfall_lahar/](ashfall_lahar/en/README.md).
- Rainfall → dry-slope erosion → landscape evolution: [badland/](badland/en/README.md).
- Downpour → surface flow beyond the infiltration capacity → dry erosion versus gullying of a cliff: [badland_storm/](badland_storm/en/README.md).
- Rainfall → incision versus creep → rounded crests and dome-shaped hills: [badland_round/](badland_round/en/README.md).
- Rainfall → erosion of soft layers → retreat of the cap-rock cliffs → mesa → butte: [mesa/](mesa/en/README.md).
- Storm → ponding → sinks → dissolution → dolines: [karst/](karst/en/README.md).
- Bare-rock towers → dissolution at the feet → collapse → tower retreat: [tower_karst/](tower_karst/en/README.md). Dissolution along joints → clefts → pillars → wall collapse: [stone_forest/](stone_forest/en/README.md).
- Sediment supply → cover and tools → bedrock incision: [bedrock_cover/](bedrock_cover/en/README.md).
- Uplift → weathering → creep → cover and incision in the stream → a steady valley: [mountain_valley/](mountain_valley/en/README.md).
- Debris flow → stripping of the deposit → rock erosion → steady slope by frequency: [debris_bedrock/](debris_bedrock/en/README.md).
- Intermittent eruptions → lava flows → stopping and solidification → piling up on the terrain → a shield volcano: [shield_volcano/](shield_volcano/en/README.md).
- Lava flow → burial of ash → ashfall → storm erosion → redeposition at the foot, repeated → a stratovolcano: [stratovolcano/](stratovolcano/en/README.md).
- Fault → tsunami → inundation: [tsunami_fault/](tsunami_fault/en/README.md), [tsunami_coast/](tsunami_coast/en/README.md).
- Slope failure → entry into water → tsunami: [landslide_tsunami/](landslide_tsunami/en/README.md).
- Flood → overtopping → levee breach → inundation → houses swept away (held back by a secondary levee): [levee_breach/](levee_breach/en/README.md).
- Tide → salt wedge travelling upstream → infiltration through the bed → salinization of the banks (blocked by an estuary barrage): [estuary_barrage/](estuary_barrage/en/README.md).
- Sediment feed → mouth bar → bifurcation → lobes → the shape of the delta changed by vegetation fixation, wave-driven longshore transport and tides: [delta/](delta/en/README.md).
- Rainfall → sewer (conduits) → surcharge and drainage: [sewer_hybrid/](sewer_hybrid/en/README.md).
- Recharge from the mountains → fan groundwater → qanat collection and outflow (dwindling with a pumping well): [qanat/](qanat/en/README.md).
- Rain → surface runoff and infiltration → groundwater flow → seepage (baseflow) → heavy-metal concentration in the river (changed by sorption delay, tanks and settling of particulate metal): [catchment_metal/](catchment_metal/en/README.md).
- Single-feature analytical benchmarks: [benchmark/](benchmark/).
- Grid refinement (nesting): [nest_reflect/](nest_reflect/en/README.md).

To find the feature combination for a phenomenon, see the
[use-case gallery](../docs/en/users_guide/usecases.md); for the settings of
each feature, the [User's Guide](../docs/en/users_guide.md).
