#!/bin/bash
# creep: MPI 実行(N ランク)+ 解析解比較 + 逐次結果とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# プローブ CSV は点集約方式によりランク数不変(ULP=0)なので、
# 逐次実行の result/ が存在すればバイト比較も行う

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")

../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_analytic.py" result/probes 1.0 || rc=1

if [ -d result_serial ]; then
    ok=1
    for f in result_serial/probes/probe*.csv; do
        cmp -s "$f" "result/probes/$(basename "$f")" || { echo "MISMATCH: $f" >&2; ok=0; }
    done
    if [ $ok -eq 1 ]; then
        echo "=== probe CSVs are bit-identical to the serial result (result_serial) ==="
    else
        rc=1
    fi
fi

exit $rc
