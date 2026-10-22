#!/bin/bash
# wave_shore: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" sd > sdinit.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_low.txt | tee Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_high.txt | tee -a Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_off.txt | tee -a Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_nowave.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_wave_shore.py" || rc=1
for c in low high off nowave; do
    if [ -d save_${c}_serial ]; then
        if cmp -s save_$c/state.dat save_${c}_serial/state.dat; then
            echo "=== $c: state.dat is bit-identical to the serial result ==="
        else
            echo "MISMATCH: save_$c/state.dat != save_${c}_serial/state.dat" >&2
            rc=1
        fi
    fi
done
exit $rc
