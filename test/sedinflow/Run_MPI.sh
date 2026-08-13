#!/bin/bash
# sedinflow: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# state.dat は gather → rank0 書きのためランク数不変(バイト一致)のはず

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_sedinflow.py" save || rc=1

if [ -d save_serial ]; then
    if cmp -s save/state.dat save_serial/state.dat; then
        echo "=== state.dat は逐次結果(save_serial)とビット一致 ==="
    else
        echo "MISMATCH: save/state.dat != save_serial/state.dat" >&2
        rc=1
    fi
fi
exit $rc
