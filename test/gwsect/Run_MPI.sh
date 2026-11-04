#!/bin/bash
# gwsect: MPI 実行 + 回帰テスト(断面形 σ のセルでの水の受け渡しの体積。§26.2)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)。ほかの構成の MPI 一致は
# Log.txt を逐次の結果と直接比べて確かめる(README)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=6
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

AREA=9600
python3 Check_gwsect.py conserve result || exit 1
python3 Check_gwsect.py rain result $AREA || exit 1
python3 Check_gwsect.py conc result 6 || exit 1
python3 Check_gwsect.py ledger result || exit 1

echo "=== gwsect verification PASS ==="
