#!/bin/bash
# uniflow: 乾いた地盤に挟まれた直線水路の等流(逐次実行。幅 1・5 × 振り替え off/on と、幅 1 の射流の区間流入)
#   ./Run.sh
# 合否は Check_uniflow.py

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for W in 1 5; do
    python3 "$sdir/make_init.py" z $W > zinit_w$W.txt
    python3 "$sdir/make_init.py" h $W > hinit_w$W.txt
done
python3 "$sdir/make_init.py" z 1 sc > zinit_w1_sc.txt
python3 "$sdir/make_init.py" h 1 sc > hinit_w1_sc.txt

set -o pipefail
./encflow param_w1_off.txt | tee Screen.log || exit 1
./encflow param_w1_on.txt | tee -a Screen.log || exit 1
./encflow param_w5_off.txt | tee -a Screen.log || exit 1
./encflow param_w5_on.txt | tee -a Screen.log || exit 1
./encflow param_w1_sc.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_uniflow.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== uniflow verification PASS ==="
else
    echo "=== uniflow verification FAIL ===" >&2
fi
exit $rc
