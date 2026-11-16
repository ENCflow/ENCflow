#!/bin/bash
# tjunction: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)
# 軸に沿う合流は、本川(行 13)と支川の口(行 12)の間が、np = 2 で帯の境界になる(合流の周りの辺がハロのセルを
# 読む)。45° 回した合流は、本川と支川の対角線が帯の境界を斜めに横切る(f_advection_lateral = 1 は、斜めエッジの
# 流入元のセルの流量をエッジ行 j − 3 まで読む)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

for g in ax rot; do
    for o in "" mx my xy; do
        python3 "$sdir/make_tjunction.py" z $g $o > "$(python3 -c "import sys; sys.path.insert(0, '$sdir'); import make_tjunction as m; print(m.zfile('$g', '$o'))")"
    done
done

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
: > Screen.log
for c in $(python3 "$sdir/make_tjunction.py" names); do
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
