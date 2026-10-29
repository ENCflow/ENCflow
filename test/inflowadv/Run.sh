#!/bin/bash
# inflowadv: 区間流入の外縁セルに接するエッジの移流項の規則(逐次実行。河道だけの領域の振動 2 構成と、流入区間の端の横溢)
#   ./Run.sh
# 合否は Check_inflowadv.py

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for c in osc5 osc3 side; do
    python3 "$sdir/make_init.py" z $c > z_$c.txt
    python3 "$sdir/make_init.py" h $c > h_$c.txt
done

set -o pipefail
./encflow param_osc5.txt | tee Screen.log || exit 1
./encflow param_osc3.txt | tee -a Screen.log || exit 1
./encflow param_side.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_inflowadv.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== inflowadv verification PASS ==="
else
    echo "=== inflowadv verification FAIL ===" >&2
fi
exit $rc
