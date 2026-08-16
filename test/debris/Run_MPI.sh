#!/bin/bash
# debris: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# state.dat は gather → rank0 書きのためランク数不変(バイト一致)のはず

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./a.out param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_debris.py" save || rc=1

if [ -d save_serial ]; then
    if cmp -s save/state.dat save_serial/state.dat; then
        echo "=== state.dat は逐次結果(save_serial)とビット一致 ==="
    else
        echo "警告: save/state.dat が逐次ビルドと不一致(-Ofast の fast-math" >&2
        echo "      ビルド間差の可能性。ビット検証は -O2 厳密数学で行うこと — §28.3)" >&2
    fi
fi

# 構成2: 江頭則
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./a.out param_eg.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_eg eg || rc=1
if [ -d save_eg_serial ]; then
    if cmp -s save_eg/state.dat save_eg_serial/state.dat; then
        echo "=== 江頭則: state.dat は逐次結果とビット一致 ==="
    else
        echo "警告: save_eg/state.dat が逐次ビルドと不一致(同上)" >&2
    fi
fi

# 構成3: 高橋・中川則
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./a.out param_tk.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_tk eg || rc=1
if [ -d save_tk_serial ]; then
    if cmp -s save_tk/state.dat save_tk_serial/state.dat; then
        echo "=== 高橋・中川則: state.dat は逐次結果とビット一致 ==="
    else
        echo "警告: save_tk/state.dat が逐次ビルドと不一致(同上)" >&2
    fi
fi
exit $rc
