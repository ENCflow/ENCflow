# test/wfswash — Verification of swash-zone transport (f_wfswash)

> English mirror of test/wfswash/README.md. The Japanese file is the master copy.

[日本語](../README.md)

The phase-averaged coastal wave field (fn_wavefield) stops short of the shoreline, so the net
transport integrated over one swash cycle is given by empirical formulas on the shoreline faces
(between a wet cell and a dry cell on higher ground; developer.md §90.21, in Japanese). The
cross-shore part is Eq. (8) of Larson, Kubota & Erikson (2004), the longshore part is Eq. (4) of
Larson & Wamsley (2007), and the runup height is the swash part of Eq. (19) of Stockdon et al.
(2006), R = 1.1 S/2 (the flow resolves the setup). This test checks the formulas and their
mapping to the grid (the four-neighbour shoreline faces and the longshore band) against values
built independently from the formulas in double precision, and it checks the approach to the
equilibrium slope, the runup limit, conservation, restart and agreement independent of the
number of ranks.

The case has no reference (pass/fail comes from the checks in Check_wfswash.py, the byte
comparisons of the restart round trip and of the parallel runs, and the stops on invalid
settings).

## Setup

A north-south shoreline (60 columns, Δx = Δy = 5 m; offshore to the west, land to the east)
with random waves H_m0 = 1 m, T = 8 s. Bed load is stopped by a large critical Shields stress
(fluv_tausc = 100) so that only the swash transport acts (f_wfsed = 1 is a prerequisite). The
equilibrium slope is wfswash_tanbe = 0.1; K_c, K_l and φ_m take their defaults (1.6e-3, K_c,
30°). The cases rate to cliff have no wave force on the flow (wf_flow = 0; the still water level
stays at η = 0, so the height the swash reaches follows from the setup). The time step is
0.25 s (Courant number 0.44 at the offshore depth of 7.9 m; with 0.5 s (0.88) the small long
waves that the bed updates generate at the shoreline grew at the offshore boundary and the run
stopped).

| Case | Topography and waves | Role |
|---|---|---|
| rate | uniform slope 1/40 (milder than equilibrium), normal incidence, one update (5 s) | amount of one update against the formula |
| diag | the slope of rate rotated by 45° on 60 × 60 (land to the south-east), normal incidence at 315°, one update | independence of the shoreline orientation |
| eq | foreshore at the equilibrium slope 0.1, normal incidence, 10 min × morfac 10 | no change at the equilibrium slope |
| mild | as rate, 30 min × morfac 10 | onshore build-up (berm formation) |
| steep | foreshore 0.15, 30 min × morfac 10 | offshore transport (the foreshore is cut back and flattens) |
| obl | foreshore 0.1 (no cross-shore transport) with waves 20° oblique, 16 rows, 10 min | total longshore transport |
| cliff | obl with the land behind the shoreline made a cliff (top 2.0 m, above the runup limit η + R ≈ 1.19 m) | no movement at a shoreline without a swash zone (in front of a cliff or seawall) |
| flow | uniform slope 1/40, closed basin (walls on all four sides of the flow), wave force on the flow wf_flow = 2 (roller), bed load and suspension, a wave height series 0.8 → 1.2 m, 30 min × morfac 5 | conservation and runup limit in the coupled run |
| rt1 → rt2 | flow split at 930 s and restarted | byte-identical to the straight run |
| bad1–4 | no f_wfsed, no wfswash_tanbe, tanβ_e ≥ tanφ_m, f_wfswash = 2 | must stop |

## Checks (Check_wfswash.py)

1. rate: the gain of the dry shoreline cell and the loss of the wet one equal −q_c Δt/Δx
   computed from the initial topography and wave heights (outputs Wh and H) (relative 1e-6;
   measured 5e-15). q_c = −2.756e-4 m²/s (onshore), R = 0.3625 m, z = 0.0625 m. The other
   cells do not change.
2. diag: the gain of every shoreline cell follows the face rule (−q_c (n̂·ê) × side length on
   each four-neighbour face; relative 1e-6). The total per unit length over the 40 central
   cells equals q_c Δt (measured 6e-9): a 45° shoreline gets the same as an axis-aligned one
   (with the diagonal faces as well, a coarse grid would give 1/√2; §90.21).
3. eq: the bed does not change (|Δz| < 1e-12; measured 0).
4. mild: conservation (Σ Δz ΔA = 1e-15 m³); the dry shoreline cell builds up and the wet one
   loses the same (±0.241 m); no other cell changes; the slope of the shoreline face goes
   0.025 → 0.049 toward the equilibrium slope without passing it; the top of the deposit
   (0.304 m) stays below the runup limit η + R (0.402 m) and above the next dry cell (a berm).
5. steep: conservation; the dry cell is cut and the wet one gains (±0.260 m); the slope of the
   shoreline face flattens 0.15 → 0.124 without passing the equilibrium slope (the dry cell
   drops below the still water level, the shoreline moves landward, and the next dry cell is
   higher than the swash reaches, so the process stops).
6. obl: the volume moved into the northern half (2.2075 m³) equals the total longshore swash
   transport Q_l × 600 s computed from the wave height and direction at the shoreline
   (outputs Wh and Wa; incidence 9.68° at the shoreline) (relative 1e-4; measured 8e-7); it
   balances the loss of the southern half; the middle rows stay practically unchanged (the end
   changes spread inward slowly; < 1e-5 m).
7. cliff: the cliff top is above the runup limit (2.0 m > R = 1.186 m), and although the waves
   are oblique enough that the same formula would give a longshore transport
   Q_l = 1.2×10⁻² m³/s (7.2 m³ in 600 s), the bed does not change (|Δz| < 1e-12; measured 0). A
   version that also placed the longshore vector on shoreline cells without a swash zone moved
   0.13 m (the band carried sand in front of the cliff; developer.md §90.21, in Japanese).
8. flow: all values are finite; sediment is conserved (morfac Σ hs + (1 − λ) Σ Δz = 4e-14; this
   form because the suspension exchange runs on hydraulic time in the water column and × morfac
   on the bed); deposits on dry cells stay below the runup limit (H_inc ≤ 1.2 m, R with the
   upper bound E = 1).
9. The restart round trip is byte-identical to the straight run in state.dat, swflow_enc.dat,
   wavefield.dat and the final fields (the incident wave height is passed every step as a
   function of time, so it is not saved; Run.sh).
10. The invalid settings bad1–4 stop, each for its own reason (Run.sh).
11. MPI: the same checks run at the same number of ranks, and state.dat and the final fields of
    every case are byte-identical to np = 1; so is the restart round trip (Run_MPI.sh).

## Running

```bash
make
./Run.sh          # topography → 10 runs → checks → restart comparison → invalid settings (about 30 s)
./Run_MPI.sh 4    # MPI; np <= 4 because some cases have 8 rows
```
