#!/bin/bash
# stageside: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)
# 格子は 8 行。np = 2 では、側方 Neumann の北の辺(行 1)と南の辺(行 8)を別のランクが持ち、np = 4 では
# 帯が 2 行ずつになる(境界として与えたセルの印は、各ランクが自分の確保範囲の分を付ける)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_stageside.py" > ss_z.txt || exit 1

export ENCFLOW_EXPECT_NP="$NP"
rm -rf result_s3 result_s4 result_q3 result_q4
: > Screen.log
rc=0
for c in s3 s4 q3 q4; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt >> Screen.log 2>&1 \
        || { echo "ERROR: param_$c run failed (see Screen.log)" >&2; rc=1; }
done
echo ""

python3 "$sdir/Check_stageside.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== stageside MPI verification PASS ==="
else
    echo "=== stageside MPI verification FAIL ===" >&2
fi
exit $rc
