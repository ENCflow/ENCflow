#!/bin/bash
# gwseep: MPI 実行 + 回帰テスト(水質 W3)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

python3 Check_gwseep.py closure result/wq.csv || exit 1

echo "=== gwseep verification PASS ==="
