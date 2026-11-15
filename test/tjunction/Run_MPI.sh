#!/bin/bash
# tjunction: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)
# 本川(行 13)と支川の口(行 12)の間が、np = 2 で帯の境界になる(合流の周りの辺がハロのセルを読む)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_tjunction.py" z > tj_z.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
: > Screen.log
for c in m800_dry m800_wet m500_dry m500_wet m200_dry m200_wet; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_tjunction.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== tjunction MPI verification PASS ==="
else
    echo "=== tjunction MPI verification FAIL ===" >&2
fi
exit $rc
