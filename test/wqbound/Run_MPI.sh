#!/bin/bash
# wqbound: MPI 実行 + 回帰テスト(水質の系外との出入りの台帳と水位規定セル。§30.9)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

python3 Check_wqbound.py closure result || exit 1
python3 Check_wqbound.py paths result || exit 1

echo "=== wqbound verification PASS ==="
