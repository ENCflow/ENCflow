#!/bin/bash
# fixation: 定着の検定(逐次実行。off / on / weak / rough / susp_off / susp_on / susp_on2
#   + リスタート分割 rt1 → rt2(rough と同じ設定))
#   ./Run.sh
# 合否は Check_fixation.py。save_* は save_*_serial にも複製(Run_MPI.sh の比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt
python3 "$sdir/make_init.py" sd > sdinit.txt

set -o pipefail
./encflow param_off.txt | tee Screen.log || exit 1
./encflow param_on.txt | tee -a Screen.log || exit 1
./encflow param_weak.txt | tee -a Screen.log || exit 1
./encflow param_rough.txt | tee -a Screen.log || exit 1
./encflow param_susp_off.txt | tee -a Screen.log || exit 1
./encflow param_susp_on.txt | tee -a Screen.log || exit 1
./encflow param_susp_on2.txt | tee -a Screen.log || exit 1
rm -rf save_rt
./encflow param_rt1.txt | tee -a Screen.log || exit 1
rm -rf save_rt1 && cp -r save_rt save_rt1       # 前半(t = 600 s)の保存値は成長則の検定が読む
./encflow param_rt2.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_fixation.py" || rc=1
for f in state.dat geomorph_fixation.dat; do
    if cmp -s save_rt/$f save_rough/$f; then
        echo "=== restart continuation: $f is bit-identical to the straight run ==="
    else
        echo "FAIL: restart continuation differs from the straight run: $f" >&2
        rc=1
    fi
done
for c in off on weak rough susp_off susp_on susp_on2; do rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial; done

if [ $rc -eq 0 ]; then
    echo "=== fixation verification PASS ==="
else
    echo "=== fixation verification FAIL ===" >&2
fi
exit $rc
