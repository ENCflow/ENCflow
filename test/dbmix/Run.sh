#!/bin/bash
# dbmix: 土石流(f_debris)と混合粒径(f_bedmix)の併用の検定(逐次実行。developer.md §139)
#   ./Run.sh
# 合否は Check_dbmix.py + 初期化で止まる構成(流入土砂の組成のない bstop1、土石流なしに組成だけを与えた
# bstop2)+ リスタート往復(rt1 → rt2 と w3 の最終の保存の cmp)。交互計算(alt2・alt3)は rt1 の保存
# (流れに土砂が残る)の写しから、土石流のない構成で復元する。
# save_* は save_*_serial にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" || exit 1
CASES=$(python3 "$sdir/make_init.py" list)
set -o pipefail
for c in $CASES; do
    ./encflow p_$c.txt 2>&1 | tee screen_$c.log || exit 1
done
rm -rf save_rt save_alt2 save_alt3
./encflow p_rt1.txt 2>&1 | tee screen_rt1.log || exit 1
cp -r save_rt save_alt2
cp -r save_rt save_alt3
./encflow p_rt2.txt 2>&1 | tee screen_rt2.log || exit 1
./encflow p_alt2.txt 2>&1 | tee screen_alt2.log || exit 1
./encflow p_alt3.txt 2>&1 | tee screen_alt3.log || exit 1
set +o pipefail
echo ""

rc=0
# 境界から入る土砂の組成は与件(既定を置かない)。組成だけを土石流なしで与えても止まる
for st in "bstop1:needs its composition (inflow_csfrac)" "bstop2:require the mixed-size bed with debris flow"; do
    c=${st%%:*}; msgp=${st#*:}
    if ./encflow p_$c.txt > screen_$c.log 2>&1; then
        echo "FAIL: $c did not stop" >&2
        rc=1
    elif grep -qF "$msgp" screen_$c.log; then
        echo "=== $c stops at initialisation ==="
    else
        echo "FAIL: $c stopped for another reason:" >&2
        tail -3 screen_$c.log >&2
        rc=1
    fi
done
python3 "$sdir/Check_dbmix.py" || rc=1
for f in state.dat geomorph_bedmix.dat swflow_enc.dat; do
    if cmp -s save_rt/$f save_w3/$f; then
        echo "=== restart continuation (rt): $f is bit-identical to the straight run ==="
    else
        echo "FAIL: restart continuation (rt) differs from the straight run: $f" >&2
        rc=1
    fi
done
for c in $CASES rt alt2 alt3; do rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial; done

if [ $rc -eq 0 ]; then
    echo "=== dbmix verification PASS ==="
else
    echo "=== dbmix verification FAIL ===" >&2
fi
exit $rc
