#!/bin/bash
# evapdry: MPI 実行 + 回帰テスト(土の乾き具合で抑える地下水の段の蒸発散。§27.2)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)。解析解の検定も行う
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt evap.csv"
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=6
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

AREA=10000
PET=48
python3 Check_evapdry.py decay result $PET 0.02 || exit 1
python3 Check_evapdry.py evbal result $AREA || exit 1
python3 Check_evapdry.py ledger result || exit 1

echo "=== evapdry verification PASS ==="
