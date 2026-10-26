#!/bin/bash
# vzzone: MPI 実行 + 回帰テスト + 解析検定(VZ 区画・共有柱・出口。developer.md §87)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(柱は全ランクで冗長に解く。出口は所有ランク
# だけが加える)。面積平均モード(行部分和の決定的総和)、厳密モードの停止
# (全ランク同時の par_stop)、保存 → 再開も MPI で確かめる。行は 8 なので np <= 4
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=6
export FILES="Log.txt vz_zone.csv vz_column.csv"
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

python3 Check_vzzone.py base result || exit 1

np=2
for a in "$@"; do case $a in -u) ;; *) np=$a ;; esac; done
run() { mpirun -np "$np" $MPIRUN_OPTS ./encflow_mpi "$1" > "$2" 2>&1; }

rm -rf result_avg
run param_avg.txt Screen_avg.log || { echo "ERROR: param_avg run failed" >&2; exit 1; }
python3 Check_vzzone.py avg result_avg || exit 1

rm -rf result_strictfail
if timeout 300 mpirun -np "$np" $MPIRUN_OPTS ./encflow_mpi param_strictfail.txt > Screen_strictfail.log 2>&1; then
    echo "ERROR: param_strictfail should stop (rainfall differs within a column)" >&2; exit 1
fi
grep -q "rainfall differs within column" Screen_strictfail.log \
    || { echo "ERROR: param_strictfail stopped for another reason (or hung)" >&2; exit 1; }
echo "  ok   strict mode stops on all ranks when rainfall differs within a column"

rm -rf result_save result_restart save
run param_save.txt Screen_save.log || { echo "ERROR: param_save run failed" >&2; exit 1; }
run param_restart.txt Screen_restart.log || { echo "ERROR: param_restart run failed" >&2; exit 1; }
python3 Check_vzzone.py restart result result_restart || exit 1

echo "=== vzzone verification PASS ==="
