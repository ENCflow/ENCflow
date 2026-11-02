#!/bin/bash
# taupart: MPI 実行(N ランク)。param.txt の回帰(reference と比較)と、d19 の Log.txt が逐次
# (Run.sh が残す Log_d19_serial.txt)とバイト一致することを確かめる
#   ./Run_MPI.sh [N](既定 2)
NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt
../Scripts/Run_case.sh mpi "$@"
rc=$?
export ENCFLOW_EXPECT_NP="$NP"
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_d19.txt > Screen_d19_mpi.log 2>&1 || exit 1
if [ -f Log_d19_serial.txt ]; then
    if cmp -s result_d19/Log.txt Log_d19_serial.txt; then
        echo "=== d19: Log.txt is bit-identical to the serial result ==="
    else
        echo "MISMATCH: result_d19/Log.txt != Log_d19_serial.txt" >&2
        rc=1
    fi
else
    echo "(Log_d19_serial.txt not found: run ./Run.sh first for the serial comparison)"
fi
exit $rc
