#!/bin/bash
# rockinc: 流水による岩盤下刻(f_rockinc)の検定(逐次実行)
#   ./Run.sh
# 構成 cover・cover_dtg・cover_mf(T2 自己被覆の解析解と更新間隔・morfac 不変)、
# pluck(T3 被覆の準定常)、pluck_mf5・mf20(T7 加速係数の等価性)、
# pluck_rt1 → rt2(T5 裸岩からのリスタート往復)、box(T4 閉じた箱の保存)を
# Check_rockinc.py で検定し、steep_*(T9 急勾配の等流の τ_b。記録のみ)を表にする。
# reference は持たない(解析解・保存則・バイト一致で判定)。
# 実行後の save_*/ は save_*_serial/ にも複製する(Run_MPI.sh のバイト比較用)
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

cfgs="cover cover_dtg cover_mf pluck pluck_mf5 pluck_mf20 pluck_rt1 pluck_rt2 box"
steep="steep_s001 steep_s005 steep_s010 steep_s020 steep_s020_od0"
set -o pipefail
for c in $cfgs $steep; do
    ./encflow param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_rockinc.py" cover || rc=1
python3 "$sdir/Check_rockinc.py" pluck || rc=1
python3 "$sdir/Check_rockinc.py" box Screen_box.log || rc=1
python3 "$sdir/Check_rockinc.py" steep || rc=1

# リスタート往復(T5): 通し(save_pluck)と分割(save_pluck_rt)
for f in state.dat geomorph_rockinc.dat; do
    if cmp -s save_pluck/$f save_pluck_rt/$f; then
        echo "PASS: restart continuation matches the straight run: $f"
    else
        echo "FAIL: restart continuation differs from the straight run: $f" >&2
        rc=1
    fi
done

for d in save_cover save_cover_dtg save_cover_mf save_pluck save_pluck_mf5 save_pluck_mf20 save_box; do
    rm -rf ${d}_serial && cp -r $d ${d}_serial
done

if [ $rc -eq 0 ]; then
    echo "=== rockinc verification PASS ==="
else
    echo "=== rockinc verification FAIL ===" >&2
fi
exit $rc
