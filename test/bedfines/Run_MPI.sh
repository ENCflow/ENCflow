#!/bin/bash
# bedfines: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt
python3 "$sdir/make_init.py" sd > sdinit.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
for c in off all mix coarse feed; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
rm -rf save_rt
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_rt1.txt | tee -a Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_rt2.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bedfines.py" || rc=1
cmp -s save_all/state.dat save_off/state.dat || { echo "FAIL: all differs from off" >&2; rc=1; }
for f in state.dat geomorph_fines.dat; do
    cmp -s save_rt/$f save_mix/$f || { echo "FAIL: restart continuation differs: $f" >&2; rc=1; }
done
for c in off all mix coarse feed; do
    if [ -d save_${c}_serial ]; then
        for f in state.dat geomorph_fines.dat; do
            [ -e save_$c/$f ] || continue
            if cmp -s save_$c/$f save_${c}_serial/$f; then
                echo "=== $c: $f is bit-identical to the serial result ==="
            else
                echo "MISMATCH: save_$c/$f != save_${c}_serial/$f" >&2
                rc=1
            fi
        done
    fi
done
exit $rc
