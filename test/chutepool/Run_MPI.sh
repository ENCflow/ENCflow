#!/bin/bash
# chutepool: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)
# 切り出しは 21 行(池は行 11〜15)。np = 2・4 とも、帯の境界が池の北の端(行 10〜12 の間)を通る

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

for k in z rw mask; do python3 "$sdir/make_chutepool.py" $k > cp_$k.txt || exit 1; done

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
: > Screen.log
for c in $(python3 "$sdir/make_chutepool.py" names); do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_chutepool.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== chutepool MPI verification PASS ==="
else
    echo "=== chutepool MPI verification FAIL ===" >&2
fi
exit $rc
