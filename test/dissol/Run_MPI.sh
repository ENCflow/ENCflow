#!/bin/bash
# dissol: MPI 実行(N ランク)+ 解析解比較 + 回帰テスト(構成 A の Log.txt。
#         逐次 reference に ULP=0)
#   ./Run_MPI.sh [N](既定 2)
# 溶食は局所更新のためランク数に依らずビット一致する(逐次の result*/ の
# bil と cmp で確かめるには、逐次実行後に result* を result*_serial へ
# 複製しておく)
export ULP=${ULP:-0}
export SKIPCOLS=6
export MPIRUN_OPTS=${MPIRUN_OPTS:---bind-to none}

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")

../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXE=./encflow_mpi
export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_sink.txt | tee -a Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_rain.txt | tee -a Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_lat.txt | tee -a Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_lata.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_analytic.py" a result || rc=1
python3 "$sdir/Check_analytic.py" b result_sink || rc=1
python3 "$sdir/Check_analytic.py" c result_rain || rc=1
python3 "$sdir/Check_analytic.py" d result_lat || rc=1
python3 "$sdir/Check_analytic.py" e result_lata || rc=1

for d in result result_sink result_rain result_lat result_lata; do
    if [ -d ${d}_serial ]; then
        ok=1
        for f in ${d}_serial/*.bil; do
            cmp -s "$f" "$d/$(basename "$f")" || { echo "MISMATCH: $f" >&2; ok=0; }
        done
        if [ $ok -eq 1 ]; then
            echo "=== $d: bil fields are bit-identical to the serial result (${d}_serial) ==="
        else
            rc=1
        fi
    fi
done

"$sdir/../Scripts/Compare_ref.sh" Log.txt || rc=1

if [ $rc -eq 0 ]; then
    echo "=== dissol MPI verification PASS ==="
else
    echo "=== dissol MPI verification FAIL ===" >&2
fi
exit $rc
