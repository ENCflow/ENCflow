#!/bin/bash
# brink: MPI 実行(N ランク)+ 検定
#   ./Run_MPI.sh [N](既定 2)
# 段落ちの構成は 12 行で、水路(行 6。斜めの構成の池は行 7)が np = 2 の帯の境界に当たる(経路の値が
# 面のセルの 8 リンクをハロから読む)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

for k in straight diag stair; do
    python3 "$sdir/make_brink.py" z $k > br_z_$k.txt || exit 1
done

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
: > Screen.log
for c in st0 st1 dg0 dg1 sr0 sr1; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

if python3 "$sdir/Check_brink.py"; then
    echo "=== brink MPI verification PASS ==="
else
    echo "=== brink MPI verification FAIL ===" >&2
    exit 1
fi
