#!/bin/bash
# damwq: MPI 実行 + 回帰テスト(水質 §30.7)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

echo "Check_damwq closure: result/wq.csv"
python3 Check_damwq.py closure result/wq.csv || exit 1

echo "=== damwq verification PASS ==="
