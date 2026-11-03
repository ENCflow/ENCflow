#!/bin/bash
# gwwidth: MPI 実行 + 回帰テスト(地下⇔地表の水の受け渡しの体積換算。§26.1)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)。param_gwc.txt の
# MPI 一致は Log.txt を逐次の result_gwc と直接比べて確かめる(README)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=6
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

AREA=9600
python3 Check_gwwidth.py conserve result || exit 1
python3 Check_gwwidth.py rain result $AREA || exit 1
python3 Check_gwwidth.py conc result 6 || exit 1
python3 Check_gwwidth.py ledger result || exit 1

echo "=== gwwidth verification PASS ==="
