#!/bin/bash
# rockinc: MPI 実行(N ランク)+ 同じ検定 + 逐次とのバイト一致(T6)
#   ./Run_MPI.sh [N](既定 2)
# 水路は南北向き(流れが j 方向の帯界面を横切る)、箱は放射状の流れ。逐次の Run.sh の
# 後に実行すると、save_*/ の state.dat・geomorph_rockinc.dat を save_*_serial/ と比べる
export MPIRUN_OPTS=${MPIRUN_OPTS:---bind-to none}

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

cfgs="cover cover_dtg cover_mf pluck pluck_mf5 pluck_mf20 pluck_rt1 pluck_rt2 hump_r02 hump_r05 hump_r08 hump_r12 box"
set -o pipefail
for c in $cfgs; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_rockinc.py" cover || rc=1
python3 "$sdir/Check_rockinc.py" pluck || rc=1
python3 "$sdir/Check_rockinc.py" hump || rc=1
python3 "$sdir/Check_rockinc.py" box Screen_box.log || rc=1
for f in state.dat geomorph_rockinc.dat; do
    if cmp -s save_pluck/$f save_pluck_rt/$f; then
        echo "PASS: restart continuation matches the straight run: $f"
    else
        echo "FAIL: restart continuation differs from the straight run: $f" >&2
        rc=1
    fi
done

for d in save_cover save_cover_dtg save_cover_mf save_pluck save_pluck_mf5 save_pluck_mf20 \
         save_hump_r02 save_hump_r05 save_hump_r08 save_hump_r12 save_box; do
    if [ -d ${d}_serial ]; then
        for f in state.dat geomorph_rockinc.dat; do
            if cmp -s $d/$f ${d}_serial/$f; then
                echo "=== $d/$f is bit-identical to the serial result ==="
            else
                echo "MISMATCH: $d/$f != ${d}_serial/$f" >&2
                rc=1
            fi
        done
    fi
done

if [ $rc -eq 0 ]; then
    echo "=== rockinc MPI verification PASS ==="
else
    echo "=== rockinc MPI verification FAIL ===" >&2
fi
exit $rc
