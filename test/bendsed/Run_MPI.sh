#!/bin/bash
# bendsed: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

for t in left right; do
    python3 "$sdir/make_init.py" z $t > zinit_$t.txt
    python3 "$sdir/make_init.py" h $t > hinit_$t.txt
done

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
: > Screen.log
for c in left_on right_on left_off right_off; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bendsed.py" || rc=1
for c in left_on right_on left_off right_off; do
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
