#!/bin/bash
# fluvial: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
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
python3 "$sdir/Check_fluvial.py" save || rc=1

if [ -d save_serial ]; then
    if cmp -s save/state.dat save_serial/state.dat; then
        echo "=== state.dat is bit-identical to the serial result (save_serial) ==="
    else
        echo "MISMATCH: save/state.dat != save_serial/state.dat" >&2
        rc=1
    fi
fi

# クリープ併用(帯界面のハロ。developer.md §19.9)
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_creep.txt | tee Screen_creep.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_fluvial.py" save_creep nosd || rc=1
if [ -d save_creep_serial ]; then
    if cmp -s save_creep/state.dat save_creep_serial/state.dat; then
        echo "=== creep: state.dat is bit-identical to the serial result (save_creep_serial) ==="
    else
        echo "MISMATCH: save_creep/state.dat != save_creep_serial/state.dat" >&2
        rc=1
    fi
fi
exit $rc
