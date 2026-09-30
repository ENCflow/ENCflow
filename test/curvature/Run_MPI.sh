#!/bin/bash
# curvature: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" z > zinit.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_off.txt | tee Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_on.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
rc=0
python3 "$sdir/Check_curvature.py" save_off save_on || rc=1
for c in off on; do
    if [ -d save_${c}_serial ]; then
        if cmp -s save_$c/state.dat save_${c}_serial/state.dat; then
            echo "=== $c: state.dat は逐次結果とビット一致 ==="
        else
            echo "警告: save_$c/state.dat が逐次ビルドと不一致(-Ofast の fast-math" >&2
            echo "      ビルド間差の可能性。ビット検証は -O2 厳密数学で — §28.3)" >&2
        fi
    fi
done
exit $rc
