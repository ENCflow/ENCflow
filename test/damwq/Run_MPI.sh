#!/bin/bash
# damwq: MPI 実行 + 回帰テスト(水質 §30.7)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=1(reference を作ったマシンと CPU の違うマシンでは、Log.txt の S の
# 最終桁が 1 つ変わる。Run.sh の注と developer.md §10 の damwq の項)。同じマシンでは
#   ULP=0 ./Run_MPI.sh N
# でビット比較する(CLAUDE.md の検証規律の「逐次 reference に ULP=0」はこの形で確かめる)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt wq.csv"
export ULP=${ULP:-1}   # 印字の最終桁 1 つ分まで(上の注)
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

echo "Check_damwq closure: result/wq.csv"
python3 Check_damwq.py closure result/wq.csv || exit 1

echo "=== damwq verification PASS ==="
