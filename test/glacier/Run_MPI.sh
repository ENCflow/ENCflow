#!/bin/bash
# glacier: MPI 実行(N ランク)+ 解析解比較 + 逐次結果とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# 分布出力(Hi/Z)は rank0 集約方式によりランク数不変(ULP=0)なので、
# 逐次実行の result*_serial/ が存在すればバイト比較も行う
# (逐次側を取っておくには: ./Run.sh 後に
#    mv result result_serial; mv result_cirque result_cirque_serial)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")

../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/Make_input.py" || exit 1

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_cirque.txt | tee Screen_cirque.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_halfar.py" result Screen.log || rc=1
python3 "$sdir/Check_cirque.py" result_cirque || rc=1

for pair in "result result_serial" "result_cirque result_cirque_serial"; do
    set -- $pair
    if [ -d "$2" ]; then
        ok=1
        for f in "$2"/*.txt; do
            cmp -s "$f" "$1/$(basename "$f")" || { echo "MISMATCH: $f" >&2; ok=0; }
        done
        if [ $ok -eq 1 ]; then
            echo "=== $1 is bit-identical to the serial result ($2) ==="
        else
            rc=1
        fi
    fi
done

exit $rc
