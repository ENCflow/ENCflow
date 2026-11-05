#!/bin/bash
# stencil9: MPI 実行(N ランク)+ 検定 + 逐次結果(Run.sh が残す save_*_serial)との state.dat のバイト比較
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")

../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXPECT_NP="$NP"
CASES="gauss_c9 hill_c5 hill_c9 strip1_c9 strip3_c9 hill_s5 hill_s9 hill_lc_s5 hill_lc_s9"
set -o pipefail
: > Screen.log
for c in $CASES; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_stencil9.py" || rc=1
for c in $CASES; do
    if [ -d save_${c}_serial ]; then
        if cmp -s save_$c/state.dat save_${c}_serial/state.dat; then
            echo "=== $c: state.dat is bit-identical to the serial result ==="
        else
            echo "MISMATCH: save_$c/state.dat" >&2
            rc=1
        fi
    fi
done
exit $rc
