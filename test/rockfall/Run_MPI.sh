#!/bin/bash
# rockfall: MPI 実行(N ランク)+ 漸化式の検定 + 回帰テスト(逐次 reference に ULP=0)
#   ./Run_MPI.sh [N](既定 2)
# 逐次の result/ を result_serial に複製しておくと bil のバイト比較も行う
export ULP=${ULP:-0}
export SKIPCOLS=4
export MPIRUN_OPTS=${MPIRUN_OPTS:---bind-to none}

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")

../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXE=./encflow_mpi
export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_rockfall.py" result || rc=1
if [ -d result_serial ]; then
    ok=1
    for f in result_serial/*.bil; do
        cmp -s "$f" "result/$(basename "$f")" || { echo "MISMATCH: $f" >&2; ok=0; }
    done
    if [ $ok -eq 1 ]; then
        echo "=== bil fields are bit-identical to the serial result (result_serial) ==="
    else
        rc=1
    fi
fi
"$sdir/../Scripts/Compare_ref.sh" Log.txt || rc=1

if [ $rc -eq 0 ]; then
    echo "=== rockfall MPI verification PASS ==="
else
    echo "=== rockfall MPI verification FAIL ===" >&2
fi
exit $rc
