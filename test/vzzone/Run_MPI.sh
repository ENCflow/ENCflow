#!/bin/bash
# vzzone: MPI 実行 + 回帰テスト + 解析検定(VZ 区画・共有柱・出口。developer.md §87)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は Log.txt を ULP=0、CSV は np=1 とバイト比較(柱は全ランクで
# 冗長に解く。出口は所有ランクだけが加える)。面積平均モード(行部分和の決定的総和)、厳密モードの停止
# (全ランク同時の par_stop)、保存 → 再開も MPI で確かめる。行は 8 なので np <= 4
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=6
export FILES=${FILES:-Log.txt}
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

python3 Check_vzzone.py base result || exit 1

np=2
for a in "$@"; do case $a in -u) ;; *) np=$a ;; esac; done

# vz_zone.csv・vz_column.csv の並列数不変性: 同じバイナリの np=1 とバイト比較する
# (同一ホスト・同一バイナリなので CPU 差の影響を受けない厳密な検査。
# reference との比較は Log.txt だけ = Run.sh の注記)
if [ "$np" != 1 ]; then
    tmp=$(mktemp)
    sed "s/dir_result = 'result'/dir_result = 'result_np1'/" param.txt > "$tmp"
    rm -rf result_np1
    mpirun -np 1 $MPIRUN_OPTS ./encflow_mpi "$tmp" > Screen_np1.log 2>&1
    rc=$?
    rm -f "$tmp"
    [ $rc -eq 0 ] || { echo "ERROR: np=1 run failed" >&2; exit 1; }
    for f in vz_zone.csv vz_column.csv; do
        cmp -s "result/$f" "result_np1/$f" \
            || { echo "ERROR: result/$f differs between np=$np and np=1" >&2; exit 1; }
        echo "  ok   $f identical between np=$np and np=1"
    done
fi
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
