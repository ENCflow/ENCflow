#!/bin/bash
# dbrock: MPI 実行(N ランク)+ 同じ検定 + 逐次とのバイト一致(DB4)
#   ./Run_MPI.sh [N](既定 2)
# 水路・箱とも流れが j 方向の帯界面を横切る。逐次の Run.sh の後に実行すると、save_*/ の
# state.dat・geomorph_rockinc.dat を save_*_serial/ と比べる
export MPIRUN_OPTS=${MPIRUN_OPTS:---bind-to none}

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1
export ENCFLOW_EXPECT_NP="$NP"

cfgs="db1 db1_dtg db3_cmin db3_vstop db2"
set -o pipefail
for c in $cfgs; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_dbrock.py" db1 || rc=1
python3 "$sdir/Check_dbrock.py" db3 || rc=1
python3 "$sdir/Check_dbrock.py" db2 Screen_db2.log || rc=1

# DB7: 入力の誤りは全ランクが初期化で停止する
for c in db7_kp db7_tauc db7_cmin db7_nodb db7_none; do
    if mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt > Screen_$c.log 2>&1; then
        echo "FAIL: $c did not stop" >&2
        rc=1
    else
        echo "PASS: $c stops"
    fi
done

for c in $cfgs; do
    if [ -d save_${c}_serial ]; then
        for f in state.dat geomorph_rockinc.dat; do
            if cmp -s save_$c/$f save_${c}_serial/$f; then
                echo "=== save_$c/$f is bit-identical to the serial result ==="
            else
                echo "MISMATCH: save_$c/$f != save_${c}_serial/$f" >&2
                rc=1
            fi
        done
    fi
done

if [ $rc -eq 0 ]; then
    echo "=== dbrock MPI verification PASS ==="
else
    echo "=== dbrock MPI verification FAIL ===" >&2
fi
exit $rc
