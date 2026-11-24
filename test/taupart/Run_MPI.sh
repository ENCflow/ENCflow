#!/bin/bash
# taupart: MPI 実行(N ランク)。param.txt の回帰(reference と比較)と、d19・te の Log.txt が逐次
# (Run.sh が残す Log_d19_serial.txt・Log_te_serial.txt)とバイト一致することを確かめる
#   ./Run_MPI.sh [N](既定 2)
NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt
../Scripts/Run_case.sh mpi "$@"
rc=$?
export ENCFLOW_EXPECT_NP="$NP"
for c in d19 te; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt > Screen_${c}_mpi.log 2>&1 || exit 1
    if [ -f Log_${c}_serial.txt ]; then
        if cmp -s result_$c/Log.txt Log_${c}_serial.txt; then
            echo "=== $c: Log.txt is bit-identical to the serial result ==="
        else
            echo "MISMATCH: result_$c/Log.txt != Log_${c}_serial.txt" >&2
            rc=1
        fi
    else
        echo "(Log_${c}_serial.txt not found: run ./Run.sh first for the serial comparison)"
    fi
done
exit $rc
