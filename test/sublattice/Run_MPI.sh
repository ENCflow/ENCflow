#!/bin/bash
# sublattice: MPI 実行(N ランク)+ 判定 + 逐次結果(result_serial)との Log のビット一致確認
#   ./Run_MPI.sh [N](既定 2)
NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1
export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_mixed.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
rc=0
python3 "$sdir/Check_sublattice.py" result_mixed mixed || rc=1
if [ -f result_serial/Log.txt ]; then
  if cmp -s result_serial/Log.txt result_mixed/Log.txt; then
    echo "=== Log.txt is bit-identical to the serial result (result_serial) ==="
  else
    echo "MISMATCH: result_mixed/Log.txt differs from result_serial/Log.txt" >&2; rc=1
  fi
fi
exit $rc
