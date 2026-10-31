#!/bin/bash
# suspend: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# state.dat は gather → rank0 書きのためランク数不変(バイト一致)のはず。
# 構成 1(param.txt)と構成 3・4(param_eq.txt・param_eq_ik.txt。水路は 1000 行)を回し、
# 逐次の Run.sh が残した save_serial・save_eq*_serial とバイト比較する

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_suspend.py" save || rc=1

if [ -d save_serial ]; then
    if cmp -s save/state.dat save_serial/state.dat; then
        echo "=== state.dat is bit-identical to the serial result (save_serial) ==="
    else
        echo "MISMATCH: save/state.dat != save_serial/state.dat" >&2
        rc=1
    fi
fi

# 構成 3・4: 等流の水路の平衡と適応
python3 "$sdir/make_eq.py" z > zinit_eq.txt
python3 "$sdir/make_eq.py" h > hinit_eq.txt
for tag in eq eq_ik; do
    rm -rf result_$tag save_$tag
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$tag.txt > Screen_$tag.log 2>&1 \
        || { echo "ERROR: param_$tag.txt (np=$NP) run failed" >&2; exit 1; }
    echo ""
    python3 "$sdir/Check_suspend.py" $tag || rc=1
    if [ -d save_${tag}_serial ]; then
        if cmp -s save_$tag/state.dat save_${tag}_serial/state.dat; then
            echo "=== save_$tag/state.dat is bit-identical to the serial result (save_${tag}_serial) ==="
        else
            echo "MISMATCH: save_$tag/state.dat != save_${tag}_serial/state.dat" >&2
            rc=1
        fi
    fi
done
exit $rc
