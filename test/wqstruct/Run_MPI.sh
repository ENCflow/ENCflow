#!/bin/bash
# wqstruct: MPI 実行 + 回帰テスト(構造物・取水が運ぶ水質の質量。§30.10)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)。取水セルと送り先は
# 北と南の区画に分かれ、2 ランク以上では別のランクの帯に載る(構造物の水と
# 質量の総和が帯をまたぐ)。param_gw.txt の MPI 一致は Log.txt・wq.csv を
# 逐次の result_gw と直接比べて確かめる(README)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

AREA=28900
for k in 1 2; do
    python3 Check_wqstruct.py conc result $k || exit 1
done
python3 Check_wqstruct.py tank result 2 3 11 || exit 1
python3 Check_wqstruct.py ledger result || exit 1
python3 Check_wqstruct.py intake result $AREA 1e-6 || exit 1
python3 Check_wqstruct.py active result 2 || exit 1

echo "=== wqstruct verification PASS ==="
