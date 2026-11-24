#!/bin/bash
# bedmix: 混合粒径(f_bedmix)の検定(逐次実行。developer.md §84.19、docs/mixed_sediment_plan.md §6)
#   ./Run.sh
# 合否は Check_bedmix.py + 初期化で止まる構成(組成の指定のない給砂 nofrac、浮遊砂の粒径の食い違い su_d50、
# 斜面浸食との併用 su_wash)+ リスタート往復(rt1 → rt2 と bank、surt1 → surt2 と susp の最終の保存の cmp)。
# save_* は save_*_serial にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for g in std deep free bank; do
    python3 "$sdir/make_init.py" z $g > zinit_$g.txt
    python3 "$sdir/make_init.py" h $g > hinit_$g.txt
    python3 "$sdir/make_init.py" sd $g > sdinit_$g.txt
done
python3 "$sdir/make_init.py" qbmix > qbmix.txt
python3 "$sdir/make_init.py" rw > rw_suw.txt
python3 "$sdir/make_init.py" width > width_suw.txt

CASES="single equal single_te equal_te single_tp equal_tp tpmix1 tpfix1 tpmix tpfix single_su equal_su susp suw armor bcfeed bank qbmix"
set -o pipefail
for c in $CASES hide1 hide2; do
    ./encflow param_$c.txt 2>&1 | tee screen_$c.log || exit 1
done
rm -rf save_rt save_surt
./encflow param_rt1.txt 2>&1 | tee screen_rt1.log || exit 1
./encflow param_rt2.txt 2>&1 | tee screen_rt2.log || exit 1
./encflow param_surt1.txt 2>&1 | tee screen_surt1.log || exit 1
./encflow param_surt2.txt 2>&1 | tee screen_surt2.log || exit 1
set +o pipefail
echo ""

rc=0
# 組成の指定のない給砂は初期化で止まる(与件なので既定を置かない。plan §10 の 3)
if ./encflow param_nofrac.txt > screen_nofrac.log 2>&1; then
    echo "FAIL: nofrac (bed-load feed without its composition) did not stop" >&2
    rc=1
elif grep -q "needs its composition" screen_nofrac.log; then
    echo "=== nofrac stops at initialisation (the feed composition is required) ==="
else
    echo "FAIL: nofrac stopped for another reason:" >&2
    tail -3 screen_nofrac.log >&2
    rc=1
fi
# 浮遊砂の粒径の食い違いと斜面浸食との併用も初期化で止まる(段 2。§122)
for st in "su_d50:susp_d50 must be omitted or equal to bmix_d(1)" "su_wash:cannot be combined with f_wash"; do
    c=${st%%:*}; msgp=${st#*:}
    if ./encflow param_$c.txt > screen_$c.log 2>&1; then
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
python3 "$sdir/Check_bedmix.py" || rc=1
for pair in "rt:bank" "surt:susp"; do
    a=${pair%%:*}; b=${pair#*:}
    for f in state.dat geomorph_bedmix.dat; do
        if cmp -s save_$a/$f save_$b/$f; then
            echo "=== restart continuation ($a): $f is bit-identical to the straight run ==="
        else
            echo "FAIL: restart continuation ($a) differs from the straight run: $f" >&2
            rc=1
        fi
    done
done
for c in $CASES hide rt surt; do rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial; done

if [ $rc -eq 0 ]; then
    echo "=== bedmix verification PASS ==="
else
    echo "=== bedmix verification FAIL ===" >&2
fi
exit $rc
