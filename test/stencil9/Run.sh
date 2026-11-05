#!/bin/bash
# stencil9: 9 点のクリープ・乾式斜面侵食の曲率の等方性と壁際の振り替えの検定(逐次。developer.md §93)
#   ./Run.sh
# reference 比較ではなく、解析解・厳密な離散解・格子の向きの差で合否を判定する(Check_stencil9.py)。
# save_* は save_*_serial にも複製する(Run_MPI.sh の比較用)

sdir=$(dirname "$(readlink -f "$0")")

../Scripts/Check_mode.sh serial || exit 1

CASES="gauss_c9 hill_c5 hill_c9 strip1_c9 strip3_c9 hill_s5 hill_s9 hill_lc_s5 hill_lc_s9"
set -o pipefail
: > Screen.log
for c in $CASES; do
    ./encflow param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_stencil9.py" || rc=1
for c in $CASES; do
    rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial
done

if [ $rc -eq 0 ]; then
    echo "=== stencil9 verification PASS ==="
else
    echo "=== stencil9 verification FAIL ===" >&2
fi
exit $rc
