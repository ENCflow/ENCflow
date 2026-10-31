#!/bin/bash
# prmap: MPI 実行(N ランク)+ 解析検定 + 逐次結果とのビット一致確認
#   ./Run_MPI.sh [N](既定 2。行は 8 なので N <= 4)
# 逐次の Log.txt(Run.sh が result_serial/ に残す)があれば、全構成の Log.txt が
# それとバイト一致することも確かめる
NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXPECT_NP="$NP"
tags="p2_def p2_min p2_c1h p2_c60 p2_prio p3_def p3_c30 p3_unit p3_prupdate p1_rr p2_rr p3_rr"
for tag in $tags; do
    rm -rf result_$tag
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$tag.txt > Screen_$tag.log 2>&1 \
        || { echo "ERROR: param_$tag run failed (see Screen_$tag.log)" >&2; exit 1; }
done
# prtype = 3 をフレームの途中(45 min)で保存し、再開する
rm -rf save result_p3_save result_p3_restart
for tag in p3_save p3_restart; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$tag.txt > Screen_$tag.log 2>&1 \
        || { echo "ERROR: param_$tag run failed (see Screen_$tag.log)" >&2; exit 1; }
done
python3 "$sdir/Check_prmap.py" $tags restart || exit 1

if [ -d result_serial ]; then
    for tag in $tags p3_restart; do
        cmp -s result_$tag/Log.txt result_serial/Log_$tag.txt \
            || { echo "ERROR: result_$tag/Log.txt differs from the serial run" >&2; exit 1; }
    done
    echo "  ok   Log.txt of all configurations identical to the serial run (np=$NP)"
fi
echo "=== prmap verification PASS (np=$NP) ==="
