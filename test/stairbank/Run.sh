#!/bin/bash
# stairbank: 格子に斜めの 1 セル幅の河道と、脇の高いセル(段・角のセル)(逐次実行。7 つの形 × 規則 2 組 = 14 構成)
#   ./Run.sh
# 合否は Check_stairbank.py(壁だけの河道が定常で、流量の上げ下げで同じ水深になること、質量の収支。
# 段・角のセルのある形は、既定の規則では、同じ流量での 2 つの状態・せき上げ・最大流速を限界として記録し、
# 4 つの値の組み合わせ(構成名の末尾が 4)では、上げ下げの一致・エネルギーが増えないこと・流量の揺れを判定する。README)
# 入力は make_stairbank.py が作る

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for g in $(python3 "$sdir/make_stairbank.py" geoms); do
    python3 "$sdir/make_stairbank.py" z $g > sb_z_$g.txt || exit 1
    python3 "$sdir/make_stairbank.py" rw $g > sb_rw_$g.txt || exit 1
done

set -o pipefail
: > Screen.log
for c in $(python3 "$sdir/make_stairbank.py" names); do
    ./encflow param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_stairbank.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== stairbank verification PASS ==="
else
    echo "=== stairbank verification FAIL ===" >&2
fi
exit $rc
