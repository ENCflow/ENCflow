#!/bin/bash
# damops: MPI 実行 + 回帰テスト(ダムの運転則。developer.md §131)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=1(reference を作ったマシンと CPU の違うマシンでは、Log.txt の S の
# 最終桁が変わり得る。Run.sh の注)。同じマシンでは
#   ULP=0 ./Run_MPI.sh N
# でビット比較する(CLAUDE.md の検証規律の「逐次 reference に ULP=0」はこの形で確かめる)
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt dams/dam0001.csv dams/dam0002.csv dams/dam0003.csv dams/dam0004.csv dams/dam0005.csv dams/dam0006.csv dams/dam0007.csv"
export ULP=${ULP:-1}   # 印字の最終桁 1 つ分まで(上の注)
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

echo "Check_damops rules: result"
python3 Check_damops.py rules result || exit 1

echo "=== damops verification PASS ==="
