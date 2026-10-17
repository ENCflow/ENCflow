#!/bin/bash
# bendsed: 90° 湾曲水路の流砂方向補正の検定(逐次実行。4 構成)
#   ./Run.sh
# 合否は Check_bendsed.py。実行後の save_*/ は save_*_serial/ にも複製する
# (Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for t in left right; do
    python3 "$sdir/make_init.py" z $t > zinit_$t.txt
    python3 "$sdir/make_init.py" h $t > hinit_$t.txt
done

set -o pipefail
: > Screen.log
for c in left_on right_on left_off right_off; do
    ./encflow param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bendsed.py" || rc=1
for c in left_on right_on left_off right_off; do
    rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial
done

if [ $rc -eq 0 ]; then
    echo "=== bendsed verification PASS ==="
else
    echo "=== bendsed verification FAIL ===" >&2
fi
exit $rc
