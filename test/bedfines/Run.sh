#!/bin/bash
# bedfines: 河床の細粒分の帳簿の検定(逐次実行。off / all / mix / coarse / feed / bfeed
#   + リスタート分割 rt1 → rt2(mix と同じ設定))
#   ./Run.sh
# 合否は Check_bedfines.py + all と off の state.dat の cmp。save_* は save_*_serial にも複製

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt
python3 "$sdir/make_init.py" sd > sdinit.txt
python3 "$sdir/make_init.py" sdfeed > sdfeed.txt

set -o pipefail
./encflow param_off.txt | tee Screen.log || exit 1
./encflow param_all.txt | tee -a Screen.log || exit 1
./encflow param_mix.txt | tee -a Screen.log || exit 1
./encflow param_coarse.txt | tee -a Screen.log || exit 1
./encflow param_feed.txt | tee -a Screen.log || exit 1
./encflow param_bfeed.txt | tee -a Screen.log || exit 1
rm -rf save_rt
./encflow param_rt1.txt | tee -a Screen.log || exit 1
./encflow param_rt2.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bedfines.py" || rc=1
if cmp -s save_all/state.dat save_off/state.dat; then
    echo "=== all (fines 100 %) is bit-identical to off ==="
else
    echo "FAIL: all (fines 100 %) differs from off: state.dat" >&2
    rc=1
fi
for f in state.dat geomorph_fines.dat; do
    if cmp -s save_rt/$f save_mix/$f; then
        echo "=== restart continuation: $f is bit-identical to the straight run ==="
    else
        echo "FAIL: restart continuation differs from the straight run: $f" >&2
        rc=1
    fi
done
for c in off all mix coarse feed bfeed; do rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial; done

if [ $rc -eq 0 ]; then
    echo "=== bedfines verification PASS ==="
else
    echo "=== bedfines verification FAIL ===" >&2
fi
exit $rc
