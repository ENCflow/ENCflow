#!/bin/bash
# bedmix: 混合粒径(f_bedmix)の検定(逐次実行。developer.md §84.19、docs/mixed_sediment_plan.md §6)
#   ./Run.sh
# 合否は Check_bedmix.py + 初期化で止まる構成(組成の指定のない給砂 nofrac、浮遊砂の粒径の食い違い su_d50、
# 斜面浸食との併用 su_wash、崩落の河岸モード rfstop_bank、基岩の崩落の岩屑の組成の欠落 rfstop_frac)+
# リスタート往復(rt1 → rt2 と bank、surt1 → surt2 と susp、rfrt1 → rfrt2 と rfb3 の最終の保存の cmp)。
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
python3 "$sdir/make_init.py" mesa z > zinit_mesa.txt
python3 "$sdir/make_init.py" mesa cap > sdinit_mesa_cap.txt
python3 "$sdir/make_init.py" mesa seaz > zinit_mesa_sea.txt
python3 "$sdir/make_init.py" mesa sw > sw_mesa_sea.txt
python3 "$sdir/make_init.py" shore z > zinit_shore.txt
python3 "$sdir/make_init.py" shore sd > sdinit_shore.txt

CASES="single equal single_te equal_te single_tp equal_tp tpmix1 tpfix1 tpmix tpfix single_su equal_su susp suw sueq armor bcfeed bclim bank qbmix rfs1 rfs3 rfb1 rfb3 rfsea1 rfsea3 cr1 cr3 ls1 ls3"
set -o pipefail
for c in $CASES hide1 hide2; do
    ./encflow param_$c.txt 2>&1 | tee screen_$c.log || exit 1
done
rm -rf save_rt save_surt save_rfrt
./encflow param_rt1.txt 2>&1 | tee screen_rt1.log || exit 1
./encflow param_rt2.txt 2>&1 | tee screen_rt2.log || exit 1
./encflow param_surt1.txt 2>&1 | tee screen_surt1.log || exit 1
./encflow param_surt2.txt 2>&1 | tee screen_surt2.log || exit 1
./encflow param_rfrt1.txt 2>&1 | tee screen_rfrt1.log || exit 1
./encflow param_rfrt2.txt 2>&1 | tee screen_rfrt2.log || exit 1
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
# 浮遊砂の粒径の食い違いと斜面浸食との併用(段 2a。§122)、崩落の河岸モードとの併用と基岩の崩落の岩屑の組成の
# 欠落(段 2b。§123)も初期化で止まる
for st in "su_d50:susp_d50 must be omitted or equal to bmix_d(1)" "su_wash:cannot be combined with f_wash" \
          "rfstop_bank:cannot be combined with rf_bank=1" "rfstop_frac:requires rf_frac"; do
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
for pair in "rt:bank" "surt:susp" "rfrt:rfb3"; do
    a=${pair%%:*}; b=${pair#*:}
    for f in state.dat geomorph_bedmix.dat geomorph_rockfall.dat; do
        [ -e save_$b/$f ] || continue
        if cmp -s save_$a/$f save_$b/$f; then
            echo "=== restart continuation ($a): $f is bit-identical to the straight run ==="
        else
            echo "FAIL: restart continuation ($a) differs from the straight run: $f" >&2
            rc=1
        fi
    done
done
for c in $CASES hide rt surt rfrt; do rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial; done

if [ $rc -eq 0 ]; then
    echo "=== bedmix verification PASS ==="
else
    echo "=== bedmix verification FAIL ===" >&2
fi
exit $rc
