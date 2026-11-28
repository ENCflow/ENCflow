# test/saltledger — Salt-water ledger of the fresh and salt water layers, and transfer of the salt layer by structures

> English mirror of test/saltledger/README.md. The Japanese file is the master copy.

[日本語](../README.md)

Verification of the ledger of salt-water volume `salt.csv` of the
[fresh and salt water layers](../../../docs/en/users_guide/salt.md) and of the transfer of the surface
salt layer by structures and sinks `f_salt_struct` (developer.md §140). Every case is a small setup
with one or two paths of salt water, and checks the closure of the ledger and the analytical value of
each path. There is no reference.

| Case (param_<name>.txt) | Path | Setup | Criterion |
|---|---|---|---|
| sea | Inflow from and outflow to the sea (surface) | Dry land with the sea at the west end (24 × 8 cells). The tide level moves 0 → 2 m → 1.3 m | `in_sea_m3`, `out_sea_m3` > 0. The surface balance closes |
| evap | Evaporation lowers the depth below the salt layer | Still water 0.5 m deep, entirely salt, evaporated at 0.1 m/h for 2 hours | The volume by which the salt layer shrinks appears in `lost_surf_m3` (evaporation rate × time × area; one step late) |
| pump0 | Structures do not carry the salt layer (`f_salt_struct = 0`, the default) | A box 1 m deep (the bottom 0.3 m is salt) pumped down to 0.2 m by a pump drawing from all cells to outside the domain | The salt layer stays, and the 0.1 m by which the depth falls below it appears in `lost_surf_m3` |
| pump1 | Bottom layer first (`f_salt_struct = 1`) | Same | All 0.3 m of salt water appears in `out_struct_m3` |
| pump2 | By mixing ratio (`f_salt_struct = 2`) | Same | 30 % of the 0.8 m pumped (0.24 m) appears in `out_struct_m3` and 0.06 m stays |
| xfer | Transfer inside the domain (`f_salt_struct = 1`) | Two ponds divided by a ridge. 0.5 m of water is sent from the west (the bottom 0.3 m is salt) to the east (fresh) | The total salt-water volume does not change; the salt layer becomes 0 in the west and 0.3 m in the east |
| exin | Fresh/salt split of infiltration (surface → ground) | Water 1 m deep (the bottom 0.4 m is salt) infiltrates into an empty aquifer with a capacity of 0.3 m | `infil_m3` = 0.3 m × area; 0.1 m stays on the surface and 0.3 m is underground |
| exout | Fresh/salt split of seepage (ground → surface) | An aquifer entirely salt flows down a slope and seeps out in a depression | `seep_m3` > 0. The balance closes for the surface and for the ground separately |
| gwsea | Subsurface sea boundary and well pumping | Seawater intrudes into a dry aquifer next to the sea. An inland well pumps (the aquifer holds no fresh water) | `in_sea_gw_m3` > 0. All the water the well pumps (90 % or more of the demand of 0.2 m³) appears in `out_pump_m3` and `lost_gw_m3` is 0. The subsurface balance closes |

The closure of the ledger is checked for every case (all recorded rows; within a relative 2e-6, the
precision of the CSV).

| File | Content |
|---|---|
| `Run.sh` | Runs the 9 cases serially and judges them with `Check_cases.sh` (about 10 seconds) |
| `Run_MPI.sh N` | Runs the 9 cases on N ranks and on 1 rank, judges them, and compares Log.txt, salt.csv and the last salt-water fields (Hss, Hgs) byte by byte |
| `Check_cases.sh` | Judges all cases (calls `Check_saltledger.py` with the arguments of each case) |
| `Check_saltledger.py` | The checks themselves (Python standard library only) |
| `make_data.py` | Regenerates the inputs in `data_saltledger/` (sea mask, ground elevation, depth, salt layer, soil thickness, intake and outlet cells) |

## How to run

```bash
make
./Run.sh
./Run_MPI.sh 2
```

## Findings

- Evaporation (evap) removes water only, but the fresh and salt water layers hold only the volume of
  salt water, so the salt layer shrinks when the depth falls below it. More concentrated salt water
  and precipitated salt cannot be represented (only the volume appears in `lost_surf_m3`). To follow
  the salinity and precipitation, use [Water quality](../../../docs/en/users_guide/wq.md).
- With the default, in which structures do not carry the salt layer (pump0), all pumped water is
  treated as fresh and the salt water stays on the intake side. For runs that drain seawater through
  pumping stations or sluices, specify `f_salt_struct = 1`.
- A well (gwsea) pumps after the lateral groundwater flow and before the transport of the salt
  water, so at the time of pumping it is not yet decided whether the water that flowed in is fresh
  or salt. The ledger counts the part that salt water fills after the pumping as pumped
  (`out_pump_m3`). In this setup, where the aquifer holds only salt water, all the pumped water
  appears in `out_pump_m3`.
