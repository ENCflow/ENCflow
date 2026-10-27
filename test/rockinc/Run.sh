#!/bin/bash
# rockinc: 流水による岩盤下刻(f_rockinc)の検定(逐次実行)
#   ./Run.sh
# 構成 cover・cover_dtg・cover_mf(T2 自己被覆の解析解と更新間隔・morfac 不変)、
# pluck(T3 被覆の準定常)、hump_r02〜r12(T3 研磨の山形)、
# pluck_mf5・mf20(T7 加速係数の等価性)、pluck_rt1 → rt2(T5 裸岩からのリスタート往復)、
# cover_rt1 → rt2(全域で土層 0 の save の復元と往復。f_rockinc なしの rt2_off は
# 従来どおり停止)、uplift(T8 隆起下の定常縦断形)、box(T4 閉じた箱の保存)、
# t11_*(T11 谷頭の給砂の下の定常縦断形と土砂収支)を
# Check_rockinc.py で検定し、steep_*(T9 急勾配の等流の τ_b。記録のみ)を表にする。
# reference は持たない(解析解・保存則・バイト一致で判定)。
# 実行後の save_*/ は save_*_serial/ にも複製する(Run_MPI.sh のバイト比較用)
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

cfgs1="cover cover_dtg cover_mf cover_rt1"
cfgs2="cover_rt2 pluck pluck_mf5 pluck_mf20 pluck_rt1 pluck_rt2 hump_r02 hump_r05 hump_r08 hump_r12 uplift box"
cfgs3="t11_r02 t11_r05 t11_r08 t11_r05a"
steep="steep_s001 steep_s005 steep_s010 steep_s020 steep_s020_od0"
set -o pipefail
for c in $cfgs1; do
    ./encflow param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
# 全域で土層 0 の save の復元: f_rockinc なしは従来どおり停止する(rt2 が save を上書きする前に)
rc=0
if ./encflow param_cover_rt2_off.txt > Screen_cover_rt2_off.log 2>&1; then
    echo "FAIL: restore of a zero soil-depth save did not stop without f_rockinc" >&2
    rc=1
elif grep -q "has no soil depth" Screen_cover_rt2_off.log; then
    echo "PASS: restore of a zero soil-depth save stops without f_rockinc"
else
    echo "FAIL: cover_rt2_off stopped for another reason (see Screen_cover_rt2_off.log)" >&2
    rc=1
fi
set -o pipefail
for c in $cfgs2 $cfgs3 $steep; do
    ./encflow param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""

python3 "$sdir/Check_rockinc.py" cover || rc=1
python3 "$sdir/Check_rockinc.py" pluck || rc=1
python3 "$sdir/Check_rockinc.py" hump || rc=1
python3 "$sdir/Check_rockinc.py" uplift || rc=1
python3 "$sdir/Check_rockinc.py" t11 || rc=1
python3 "$sdir/Check_rockinc.py" box Screen_box.log || rc=1
python3 "$sdir/Check_rockinc.py" steep || rc=1

# リスタート往復(T5): 通し(save_pluck・save_cover)と分割(save_pluck_rt・save_cover_rt。
# 後者は全域で土層 0 の save からの継続)
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
    rm -rf ${d}_serial && cp -r $d ${d}_serial
done

if [ $rc -eq 0 ]; then
    echo "=== rockinc verification PASS ==="
else
    echo "=== rockinc verification FAIL ===" >&2
fi
exit $rc
