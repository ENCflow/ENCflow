#!/bin/bash
# vzcol: MPI 実行 + 回帰テスト + 解析検定(VZ 共有参照柱。developer.md §87)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律。柱は全ランクで冗長に
# 解くので並列数によらずビット一致する)。面積平均モード(param_avg.txt)は
# 行部分和の決定的総和(par_sum_rows)を通るので、MPI でも厳密モードと一致する
# ことを確かめる。行は 8 なので 2 行/ランクの制約から np <= 4
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=6
export FILES="Log.txt vz_zone.csv vz_column.csv"
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

python3 Check_vzcol.py base result || exit 1

np=2
for a in "$@"; do case $a in -u) ;; *) np=$a ;; esac; done
rm -rf result_avg
mpirun -np "$np" $MPIRUN_OPTS ./encflow_mpi param_avg.txt > Screen_avg.log 2>&1 \
    || { echo "ERROR: param_avg run failed" >&2; exit 1; }
python3 Check_vzcol.py avg result result_avg || exit 1

echo "=== vzcol verification PASS ==="
