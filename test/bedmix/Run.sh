#!/bin/bash
# bedmix: 混合粒径(f_bedmix)の検定(逐次実行。developer.md §84.19、docs/mixed_sediment_plan.md §6)
#   ./Run.sh
# 合否は Check_bedmix.py + 組成の指定のない給砂(nofrac)の停止 + リスタート往復(rt1 → rt2 と bank の
# 最終の保存の cmp)。save_* は save_*_serial にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for g in std deep free bank; do
    python3 "$sdir/make_init.py" z $g > zinit_$g.txt
    python3 "$sdir/make_init.py" h $g > hinit_$g.txt
    python3 "$sdir/make_init.py" sd $g > sdinit_$g.txt
done
python3 "$sdir/make_init.py" qbmix > qbmix.txt

CASES="single equal single_te equal_te armor bcfeed bank qbmix"
set -o pipefail
for c in $CASES hide1 hide2; do
    ./encflow param_$c.txt 2>&1 | tee screen_$c.log || exit 1
done
rm -rf save_rt
./encflow param_rt1.txt 2>&1 | tee screen_rt1.log || exit 1
./encflow param_rt2.txt 2>&1 | tee screen_rt2.log || exit 1
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
python3 "$sdir/Check_bedmix.py" || rc=1
for f in state.dat geomorph_bedmix.dat; do
    if cmp -s save_rt/$f save_bank/$f; then
        echo "=== restart continuation: $f is bit-identical to the straight run ==="
    else
        echo "FAIL: restart continuation differs from the straight run: $f" >&2
        rc=1
    fi
done
for c in $CASES hide rt; do rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial; done

if [ $rc -eq 0 ]; then
    echo "=== bedmix verification PASS ==="
else
    echo "=== bedmix verification FAIL ===" >&2
fi
exit $rc
