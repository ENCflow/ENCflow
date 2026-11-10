#!/bin/bash
# vshaped: MPI 実行(N ランク)+ 理論解との比較 + 逐次結果とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# 測線 CSV は点集約方式によりランク数不変(ULP=0)なので、逐次実行(Run.sh)の控え
# result_serial/ が存在すればバイト比較も行う

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")

../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" || exit 1

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_r0.txt | tee Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_r45.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_vshaped.py" result_r0 result_r45 || rc=1

if [ -d result_serial ]; then
    ok=1
    for c in r0 r45; do
        for f in result_serial/$c/fluxes/flux*.csv; do
            cmp -s "$f" "result_$c/fluxes/$(basename "$f")" || { echo "MISMATCH: $f" >&2; ok=0; }
        done
    done
    if [ $ok -eq 1 ]; then
        echo "=== flux CSVs are bit-identical to the serial result (result_serial) ==="
    else
        rc=1
    fi
fi

if [ $rc -eq 0 ]; then
    echo "=== vshaped verification PASS (np=$NP) ==="
else
    echo "=== vshaped verification FAIL (np=$NP) ===" >&2
fi
exit $rc
