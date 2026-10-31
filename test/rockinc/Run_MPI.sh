#!/bin/bash
# rockinc: MPI 実行(N ランク)+ 同じ検定 + 逐次とのバイト一致(T6)
#   ./Run_MPI.sh [N](既定 2)
# 水路は南北向き(流れが j 方向の帯界面を横切る)、箱は放射状の流れ。逐次の Run.sh の
# 後に実行すると、save_*/ の state.dat・geomorph_rockinc.dat を save_*_serial/ と比べる。
# f_opening_dynamic = 3 の steep_s020_od3・sheet_d45_od3(帯界面を斜めに横切る面状流)は
# 出力 *.bil を result_*_serial/ と比べる
export MPIRUN_OPTS=${MPIRUN_OPTS:---bind-to none}

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

cfgs1="cover cover_dtg cover_mf cover_rt1"
cfgs2="cover_rt2 pluck pluck_mf5 pluck_mf20 pluck_rt1 pluck_rt2 hump_r02 hump_r05 hump_r08 hump_r12 uplift box"
cfgs3="t11_r02 t11_r05 t11_r08 t11_r05a"
set -o pipefail
for c in $cfgs1; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
rc=0
if mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_cover_rt2_off.txt > Screen_cover_rt2_off.log 2>&1; then
    echo "FAIL: restore of a zero soil-depth save did not stop without f_rockinc" >&2
    rc=1
elif grep -q "has no soil depth" Screen_cover_rt2_off.log; then
    echo "PASS: restore of a zero soil-depth save stops without f_rockinc"
else
    echo "FAIL: cover_rt2_off stopped for another reason (see Screen_cover_rt2_off.log)" >&2
    rc=1
fi
set -o pipefail
for c in $cfgs2 $cfgs3 steep_s020_od3 sheet_d45_od3; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""

python3 "$sdir/Check_rockinc.py" cover || rc=1
python3 "$sdir/Check_rockinc.py" pluck || rc=1
python3 "$sdir/Check_rockinc.py" hump || rc=1
python3 "$sdir/Check_rockinc.py" uplift || rc=1
python3 "$sdir/Check_rockinc.py" t11 || rc=1
python3 "$sdir/Check_rockinc.py" box Screen_box.log || rc=1
for d in pluck cover; do
    for f in state.dat geomorph_rockinc.dat; do
        if cmp -s save_$d/$f save_${d}_rt/$f; then
            echo "PASS: restart continuation matches the straight run ($d): $f"
        else
            echo "FAIL: restart continuation differs from the straight run ($d): $f" >&2
            rc=1
        fi
    done
done
if grep -q "restored soil depth is zero everywhere" Screen_cover_rt2.log; then
    echo "PASS: the zero soil-depth save was accepted with f_rockinc (cover_rt2)"
else
    echo "FAIL: cover_rt2 did not take the zero soil-depth path" >&2
    rc=1
fi

for d in save_cover save_cover_dtg save_cover_mf save_pluck save_pluck_mf5 save_pluck_mf20 \
         save_hump_r02 save_hump_r05 save_hump_r08 save_hump_r12 save_uplift save_box \
         save_t11_r02 save_t11_r05 save_t11_r08 save_t11_r05a; do
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
for d in result_steep_s020_od3 result_sheet_d45_od3; do
    if [ -d ${d}_serial ]; then
        for f in ${d}_serial/*.bil; do
            if cmp -s $f $d/$(basename $f); then
                echo "=== $d/$(basename $f) is bit-identical to the serial result ==="
            else
                echo "MISMATCH: $d/$(basename $f) != $f" >&2
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
