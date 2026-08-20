#!/bin/bash
# swi: MPI 実行(N ランク)+ 検定 + 逐次結果とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# タンク状態は swi.dat(gather → rank0 書き)、Swi 出力もランク数不変のはず

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXPECT_NP="$NP"
rc=0
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_swi.py" result || rc=1
if [ -d save_serial ]; then
    for f in state.dat swi.dat; do
        if cmp -s save/$f save_serial/$f; then
            echo "=== swi: save/$f は逐次結果とビット一致 ==="
        else
            echo "警告: save/$f が逐次ビルドと不一致(-Ofast の fast-math" >&2
            echo "      ビルド間差の可能性。ビット検証は -O2 厳密数学で — §28.3)" >&2
        fi
    done
    for f in Swi9998.txt Swi9999.txt Swit9999.txt; do
        if cmp -s result/$f save_serial/$f; then
            echo "=== swi: $f は逐次結果とビット一致 ==="
        else
            echo "警告: result/$f が逐次ビルドと不一致(同上)" >&2
        fi
    done
fi
exit $rc
