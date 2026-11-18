#!/bin/bash
# cascade: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)
# 切り出しは 55 行。河道は南西の端から北東へ下るので、np = 2・4 とも、帯の境界が河道を横切る

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

for k in z rw mask; do python3 "$sdir/make_cascade.py" $k > cs_$k.txt || exit 1; done

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
: > Screen.log
for c in $(python3 "$sdir/make_cascade.py" names); do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_cascade.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== cascade MPI verification PASS ==="
else
    echo "=== cascade MPI verification FAIL ===" >&2
fi
exit $rc
