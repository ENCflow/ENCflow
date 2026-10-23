#!/bin/bash
# berode: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_kb1.txt 2>&1 | tee Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_kb2.txt 2>&1 | tee -a Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_fix0.txt 2>&1 | tee -a Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_fix1.txt 2>&1 | tee -a Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_slump.txt 2>&1 | tee -a Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_slump0.txt 2>&1 | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_berode.py" || rc=1
for c in kb1 kb2 fix0 fix1 slump slump0; do
    if [ -d save_${c}_serial ]; then
        for f in state.dat geomorph_rockfall.dat; do
            [ -f save_${c}_serial/$f ] || continue
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
