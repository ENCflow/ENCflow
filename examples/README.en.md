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

"Contents" summarises what each example shows; the setup, results and limits are in the README
of each example.

| Directory | Contents | Main features |
|---|---|---|
| [List_samples/](List_samples/) | Annotated samples of every namelist (one file per group); a dictionary of settings and defaults (English in en/) | All features |
| [benchmark/](benchmark/en/README.md) | Two reference problems of rainfall runoff: the outlet discharge of a V-shaped catchment against the kinematic-wave theory, and the pseudo-depressions of a valley floor oblique to the grid | Shallow water, rainfall (default settings), diagonal share p_diagratio, sub-grid channel width (addendum) |
| [chichibu_flood/](chichibu_flood/en/README.md) | A heavy-rain flood in the Chichibu mountains represented by surface flow only, varying the terrain preprocessing, the grid resolution, the treatment of the advection term and more | Shallow water, rainfall, interception and infiltration fn_intercept and fn_gwflow, sub-grid channel width fn_width, 4-neighbour comparison p_diagratio, diffusion wave f_govequation |
| [source_area/](source_area/en/README.md) | A headwater catchment: rain passing through the soil to the stream from the saturated valley floors, and the runoff source area growing and shrinking; also compared with an equivalent roughness, VZ runoff and the storage function method | Green-Ampt, lateral flow in the soil f_gwlateral, layer 2 f_gwlayer2, diffusion wave f_govequation, VZ runoff fn_vz, storage function method fn_sfm |
| [vz_tani2023/](vz_tani2023/en/README.md) | Reproduction of the VZ runoff model of Tani (2023): runoff rates and pressure heads of all seven events compared with the paper | Vertical unsaturated flow (VZ) runoff fn_vz (shared column, linear distribution of soil depth) |
| [badland/](badland/en/README.md) | Badland formation as rainfall carves valleys into a plateau and scarp: self-organised valleys, their spacing rule and sharp ridges | Dry hillslope erosion f_splash (spl_lc, spl_zbase) |
| [badland_storm/](badland_storm/en/README.md) | A low-infiltration cliff where surface flow appears only in downpours: does dry erosion stop or become a gully network? (contrast to badland) | f_splash + f_wash, f_suspend, Green-Ampt, rainfall series |
| [badland_round/](badland_round/en/README.md) | Rounded-crest (swelling-clay) badlands: hills lower than the length scale set by incision versus creep become domes | f_splash + f_creep (+ spl_strata), Green-Ampt |
| [mesa/](mesa/en/README.md) | A cap rock keeps a flat top and vertical cliffs whose parallel retreat shrinks the plateau to a mesa, a butte and a pinnacle | f_splash (spl_strata, spl_ksat) + f_creep + f_rockfall (rf_rc, rf_fface), Green-Ampt |
| [karst/](karst/en/README.md) | A doline field on a limestone plateau: water that collects in depressions and sinks underground deepens those spots selectively | limestone dissolution f_dissol, conduit continuum layer (sinks), Green-Ampt, periodic forcing t_cycle_c |
| [tower_karst/](tower_karst/en/README.md) | Bare-rock towers on a plain (tower karst): only the plain and their feet dissolve, so the towers rise above the plain and moats and holes form at the feet | limestone dissolution f_dissol (dissol_lat), rock-wall collapse f_rockfall, Green-Ampt conductivity map, periodic forcing |
| [stone_forest/](stone_forest/en/README.md) | A stone forest: a limestone plateau dissolved along its joints splits into pillars and clefts; the clefts deepen and wall collapse caps the pillar height | limestone dissolution f_dissol (multiplier map fn_dissol), bedrock collapse f_rockfall (rf_bedrock), talus dissolution, quasi-steady forcing |
| [ashfall_lahar/](ashfall_lahar/en/README.md) | Rain on an ash-covered, low-infiltration slope erodes the ash into a lahar that deposits on the fan; effect of a check dam | Debris flow f_debris (pore water with the groundwater computation f_dbwet=2), Green-Ampt infiltration capacity, rainfall, check dam (terrain), four-neighbour grid p_diagratio |
| [landslide_tsunami/](landslide_tsunami/en/README.md) | Tsunamis from subaerial and submarine landslides and debris flows entering water: four patterns plus non-hydrostatic variants | Moving bed layer f_bedslide, non-hydrostatic correction |
| [tsunami_fault/](tsunami_fault/en/README.md) | A tsunami generated from fault parameters: hydrostatic, instantaneous and non-hydrostatic runs and coordinate patterns compared | Prescribed bed motion fn_bedmotion, utils/fault2disp |
| [tsunami_coast/](tsunami_coast/en/README.md) | How the time lag between coastal subsidence/uplift and the offshore fault tsunami changes flooding of a subsided bay-head plain | Prescribed bed motion fn_bedmotion |
| [tsunami_meander/](tsunami_meander/en/README.md) | Flume experiments of bores in meandering channels (Kobayashi et al. 2019, 2021) computed with the hydrostatic and the non-hydrostatic model; the wave heights along the banks are compared with the measurements | Domain mask (staircase side walls), initial water-level map fn_hinit, non-hydrostatic correction f_nonhydrostatic, probes |
| [levee_breach/](levee_breach/en/README.md) | A flood overtops and breaches a levee, the landside floods and houses are swept away; effect of a secondary levee | Prescribed bed motion fn_bedmotion (breach), building damage fn_bldgdebris (load criterion), building porosity fn_gv, channel breach (supplement) |
| [confluence_backwater/](confluence_backwater/en/README.md) | The main-river backwater overtops the tributary's lower levees and floods the landside; compared for combinations of floods and measures (raising the levees, a gate and pumps) | Shallow-water flow (resolved channels and levees), gate (culvert) and pumps, three ways of making the channel mask on a coarse grid (channel mask fn_rw, subgrid channel width fn_width, virtual-wall levees fn_bank; supplement) |
| [coarse_channel/](coarse_channel/en/README.md) | How to make the channel mask and channel width of a river on a coarse grid (Δx = 100 m), compared by conveyance over river width, direction and bends, with a guide to choosing | Channel mask fn_rw, subgrid channel width fn_width, virtual-wall levees fn_bank, rainfall |
| [estuary_barrage/](estuary_barrage/en/README.md) | How an estuary barrage affects the salt wedge in a tidal river and salt intrusion from the bed into the surrounding aquifer | Fresh and salt water layers fn_salt (surface salt layer, subsurface salt zone, exchange split f_salt_exch), tide, Green-Ampt, lateral groundwater flow, river-bed exchange capacity f_gwbed |
| [nest_reflect/](nest_reflect/en/README.md) | A Gaussian wave crossing two-way nested grids (ratios 3 and 5): error and reflection against a uniform fine grid | Nesting fn_nest (docs/en/users_guide/nest.md) |
| [tsunami_town/](tsunami_town/en/README.md) | A tsunami destroys wooden houses, carries the debris inland and back to sea with the backwash; effect of raising the seawall | Building destruction and debris fn_bldgdebris (depth criterion, porosity feedback), building porosity fn_gv, tide fn_tide, driftwood fn_driftwood (supplement) |
| [timberyard/](timberyard/en/README.md) | A storm surge floats timber out of a timber yard over the seawall into a town (Ise Bay typhoon type); effect of countermeasures | Driftwood fn_driftwood (hydraulic release, deposition, refloating), building porosity fn_gv, tide fn_tide |
| [bridge_wood_jam/](bridge_wood_jam/en/README.md) | Driftwood jams at a bridge and backs up the water upstream, and the overflow bypasses the bridge over the floodplain; the spread of the results with the capture assumption | Driftwood fn_driftwood (capture and jamming at structures fn_dwtrap, dw_jamgrow; drag of the jam f_dwjam, dw_jamphi), inflow time series, probes and transects |
| [sewer_hybrid/](sewer_hybrid/en/README.md) | A schematic urban drainage run: a trunk main and branch network in one conduit continuum layer, with surcharge and drainage | Conduit continuum layer f_gwconduit |
| [coastal_compound_flood/](coastal_compound_flood/en/README.md) | The storm surge closes the outfall and stormwater from the sewers surcharges from the inlets of a lowland town; heavy rain, surge and a high water table are added one at a time | Conduit continuum layer f_gwconduit (sea outfall fn_gwc_outfall), pump drawing from the conduits f_pump_src, tide fn_tide and seawall, Green-Ampt |
| [paddy_dam/](paddy_dam/en/README.md) | In a lowland drainage district (inland flooding), how paddy-field dams change the inundation of a settlement and the fate of a substance in the field water, compared on a fine and a coarse grid | Paddy-field dams fn_paddy (resolved plots fn_pd_plot, two-way f_pd_exchange, catchment fraction fn_pd_catch), pump, water quality fn_wq |
| [paddy_basin/](paddy_basin/en/README.md) | In a sloping basin, the peak cut at the outlet by paddy-field dams, computed for different paddy fractions and rain and compared with the estimation formula of the guide to paddy-field dams | Paddy-field dams fn_paddy (representation A one-way, adoption ratio pd_adopt), channel mask fn_rw, subgrid channel width fn_width, stage boundary, transect |
| [qanat/](qanat/en/README.md) | The outflow of a qanat collecting the groundwater of a mountain-foot fan, and how a nearby pumping well makes it dwindle and dry up | Conduit continuum layer f_gwconduit (exchange-capacity map fn_gwc_leak, open outfall fn_gwc_outfall), layer 2 f_gwlayer2, well pumping f_gwpump |
| [catchment_metal/](catchment_metal/en/README.md) | Where heavy metals from a mine effluent and farmland go in a catchment and how the river concentration changes, adding one mechanism at a time; the effects of tanks and evapotranspiration | Water quality fn_wq (point and area sources, transport with infiltration, retardation wq_rg, settling wq_vs, re-suspension wq_wash_kf), Green-Ampt, lateral groundwater flow, evapotranspiration fn_evap |
| [meander/](meander/en/README.md) | Meander growth of a sinusoidal channel in a floodplain: outer-bank retreat, inner-bar growth and fixation, and conversion to floodplain | Bed-load direction correction fluv_slope, f_secflow, bank erosion f_berode, angle-of-repose avalanching f_repose, fixation f_fixation, sediment feed |
| [meander_cutoff/](meander_cutoff/en/README.md) | Meander loops are cut off by overbank flow in a flood or by bank retreat alone; the old loop becomes slack water and starts to fill | same + slump blocks f_rockfall, inflow time series |
| [joganji_flume/](joganji_flume/en/README.md) | The NILIM 1/100 movable-bed model of the Joganji River computed with mixed grain sizes; water levels, bed change and surface composition compared with the measurements and with a single-size run | mixed grain sizes f_bedmix (per-class feed fn_inflow_qbmix), bed load f_fluvial, repose collapse f_repose, inflow discharge series |
| [delta/](delta/en/README.md) | A river-mouth delta built in a basin by a sediment-feeding river; the sand/mud ratio, floods and vegetation, waves and tides are added one at a time to see which mechanisms each type needs and how the shape differs | capacity feed fluv_bcfeed, suspended mud f_bedfines, fixation f_fixation, longshore transport fn_wave, wave field fn_wavefield, tide level fn_tide |
| [bedrock_cover/](bedrock_cover/en/README.md) | Whether the amount, timing and initial cover of sediment supply speed up or hinder bedrock incision (tools and cover effects) | bedrock incision by flowing water f_rockinc (plucking, cover, abrasion), bedload f_fluvial, sediment feed at a segment inflow inflow_qb |
| [mountain_valley/](mountain_valley/en/README.md) | A V-shaped valley in rising mountains with weathering and creep on the hillslopes and bedrock incision in the stream, to a steady form | weathering f_wthr (fn_wthr), depth-dependent creep creep_hstar, bedrock incision by flowing water f_rockinc, bedload f_fluvial, distributed uplift fn_uplift |
| [debris_bedrock/](debris_bedrock/en/README.md) | Where and how much a debris flow erodes bedrock, and how debris-flow frequency changes the steady slope of the stream | debris flows f_debris (Takahashi–Nakagawa, Coulomb + Manning), rock erosion by debris flows rock_kdb of f_rockinc |
| [debris_fan/](debris_fan/en/README.md) | A debris flow that starts from a slope failure and deposits in a residential area on the fan, compared across grid spacings, valley orientations and the eight- and four-neighbour versions | debris flows f_debris (Takahashi–Nakagawa), instantaneous fluidization fn_dbinit, output of the maximum flow depth and force, four-neighbour control p_diagratio |
| [debris_dam/](debris_dam/en/README.md) | A rain-triggered slope failure, the natural dam, its breach by overtopping and the flood downstream in one computation, comparing the conditions that make the breach rapid and the effects of the grain-size grading | slope-stability test f_slide, debris flows f_debris (Takahashi–Nakagawa) + bed load f_fluvial, mixed grain sizes f_bedmix with the erosion selector f_dbsel, Green-Ampt, house destruction fn_bldgdebris, culvert |
| [debris_fan_flume/](debris_fan_flume/en/README.md) | A flume experiment (Takahashi, Nakagawa and Yamashiki 1991) in which a debris flow of mixed-size sediment builds a fan that clear water then erodes, compared with values read from the published figures | debris flows f_debris (Takahashi–Nakagawa) combined with mixed grain sizes f_bedmix, the selector f_dbsel that limits the erosion to the movable size classes, restore into a configuration without debris flow (alternating runs), in-reach inflow, domain mask |
| [snow_avalanche/](snow_avalanche/en/README.md) | A dense snow avalanche running down a gully grows by taking up the track snow and deposits on the fan; the effect of a deflecting dam and the limits of how entrainment is given | debris flows f_debris read as snow (Voellmy law f_dbres=4, entrainment f_dbed=4 and 5, momentum f_dbmom=1, instantaneous fluidization fn_dbinit), deflecting dam (terrain) |
| [shield_volcano/](shield_volcano/en/README.md) | A shield volcano growing as the lava flows of intermittent eruptions pile up, with the yield stress setting the shape (a lava dome as a supplement) | Lava flow fn_lavaflow (several vents lv_cell, lv_val, Bingham yield stress lv_tauy, solidification lv_wsol, lv_vsol) |
| [stratovolcano/](stratovolcano/en/README.md) | Lava flow, ashfall and storm erosion repeated 10 times build a stratovolcano; how the style of eruption and erosion change the shape and the internal layers | Lava flow fn_lavaflow (temperature mode f_lvtemp), ashfall by preprocessing, Green-Ampt, bedload f_fluvial + morfac, a driver chaining the stages |
| [glacier_valley/](glacier_valley/en/README.md) | A glacier grown in a fluvial V-shaped valley: where and how fast 6000 years of erosion act; a supplement with ten times the erosion shows basins, lakes and hanging valleys | Glacier fn_glacier (mass balance, avalanching f_glava, SIA flow f_glflow, sliding f_glslide, erosion f_glero), snow cover, time acceleration gl_morfac |

## Examples of chained processes

Set-ups that show ENCflow's characteristic "several processes chained in
one run" (for reference after reading the chapters).

- Tsunami → house destruction → debris transport and deposition → back to sea with the backwash (changed by the seawall and closing its opening): [tsunami_town/](tsunami_town/en/README.md).
- Storm surge → timber floats out of a timber yard → enters and settles in the town (changed by countermeasures): [timberyard/](timberyard/en/README.md).
- Flood → driftwood recruitment → jam at a bridge → backwater → flooding of the floodplain bypassing the bridge (changed by the capture assumption): [bridge_wood_jam/](bridge_wood_jam/en/README.md).
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
- Snowfall → conversion to ice → glacier flow and sliding → glacial erosion → (over long times) closed basins with lakes and the step of a hanging valley, and shortening of the glacier by erosion: [glacier_valley/](glacier_valley/en/README.md).
- Fault → tsunami → inundation: [tsunami_fault/](tsunami_fault/en/README.md), [tsunami_coast/](tsunami_coast/en/README.md).
- Bore from a sudden gate opening → propagation in a meandering channel → wave height at the outer bank (comparison with flume measurements; when to use the hydrostatic and the non-hydrostatic model): [tsunami_meander/](tsunami_meander/en/README.md).
- Slope failure → entry into water → tsunami: [landslide_tsunami/](landslide_tsunami/en/README.md).
- Flood → overtopping → levee breach → inundation → houses swept away (held back by a secondary levee): [levee_breach/](levee_breach/en/README.md).
- Main-river flood → the narrows raise the stage at the confluence → backwater and reverse flow up the tributary → overtopping of the tributary's lower levees → landside flooding (more when the peaks coincide; changed by raising the levees of the backwater section or by a gate and drainage pumps): [confluence_backwater/](confluence_backwater/en/README.md).
- Tide → salt wedge travelling upstream → infiltration through the bed → salinization of the banks (blocked by an estuary barrage): [estuary_barrage/](estuary_barrage/en/README.md).
- Sediment feed → mouth bar → bifurcation → lobes → the shape of the delta changed by vegetation fixation, wave-driven longshore transport and tides: [delta/](delta/en/README.md).
- Rainfall → sewer (conduits) → surcharge and drainage: [sewer_hybrid/](sewer_hybrid/en/README.md).
- Heavy rain + storm surge → outfall closed → surcharge of water that came through the sewers → flooding of the lowland (more with a high water table, longer when the rain comes first, less with pumps): [coastal_compound_flood/](coastal_compound_flood/en/README.md).
- Heavy rain → storage in paddy fields (restricted by the outlets of paddy-field dams) → drains → pumping station → inland flooding of a settlement (changed by backflow from the drains into the paddies, by where the dams are adopted, and by the grid size and representation): [paddy_dam/](paddy_dam/en/README.md).
- Heavy rain → storage in paddy fields (paddy-field dams) → runoff from hillslopes and paddies → channels → peak at the basin outlet (changed by the paddy fraction, the rain and the adoption ratio; compared with the estimation formula of the guide): [paddy_basin/](paddy_basin/en/README.md).
- Recharge from the mountains → fan groundwater → qanat collection and outflow (dwindling with a pumping well): [qanat/](qanat/en/README.md).
- Rain → infiltration → lateral flow in the soil → growth and shrinkage of the saturated valley floors → seepage → channel → outlet discharge (compared with overland flow with an equivalent roughness): [source_area/](source_area/en/README.md).
- Rain → surface runoff and infiltration → groundwater flow → seepage (baseflow) → heavy-metal concentration in the river (changed by sorption delay, tanks, settling of particulate metal and evapotranspiration): [catchment_metal/](catchment_metal/en/README.md).
- Reference problems of rainfall runoff with a theoretical solution, and the check of valley orientation and neighbour count: [benchmark/](benchmark/en/README.md).
- Slope failure → debris flow → residential area on the fan (dependence on the grid spacing and the valley orientation; eight versus four neighbours on coarse grids): [debris_fan/](debris_fan/en/README.md).
- Heavy rain → slope failure → debris flow → natural dam → ponding → overtopping → breach → flood → houses swept away (prevented by a drain; comparison of the conditions that make the breach rapid): [debris_dam/](debris_dam/en/README.md).
- Water supply → erosion of mixed-size sediment → debris flow → fan → erosion by clear water and coarsening of the surface (compared with values read from the figures of a flume experiment; what the debris-flow laws and the bed-load formula each cover): [debris_fan_flume/](debris_fan_flume/en/README.md).
- Avalanche release → flow down a gully → entrainment of the track snow → deposit on the fan (deflected by a dam; a large avalanche overtops it): [snow_avalanche/](snow_avalanche/en/README.md).
- Grid refinement (nesting): [nest_reflect/](nest_reflect/en/README.md).

To find the feature combination for a phenomenon, see the
[use-case gallery](../docs/en/users_guide/usecases.md); for the settings of
each feature, the [User's Guide](../docs/en/users_guide.md).
