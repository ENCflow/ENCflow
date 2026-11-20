#!/bin/bash
# stairbank: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)
# 格子は 8〜43 行。1 つの階段の形(8 行)は、np = 2 では、帯の境界が階段のまわりの行(4〜5)を通る

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

for g in $(python3 "$sdir/make_stairbank.py" geoms); do
    python3 "$sdir/make_stairbank.py" z $g > sb_z_$g.txt || exit 1
    python3 "$sdir/make_stairbank.py" rw $g > sb_rw_$g.txt || exit 1
done

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
: > Screen.log
for c in $(python3 "$sdir/make_stairbank.py" names); do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_stairbank.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== stairbank MPI verification PASS ==="
else
    echo "=== stairbank MPI verification FAIL ===" >&2
fi
exit $rc
