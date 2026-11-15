#!/bin/bash
# tjunction: 1 セル幅の T 字の合流(逐次実行。3 つの流量比 × 乾いた岸・濡れた岸 = 6 構成)
#   ./Run.sh
# 合否は Check_tjunction.py(定常・質量の収支・下流の等流・合流でエネルギーが増えないこと)。
# 合流の 1 セル上流の水深の、運動量の理論の中での位置は、判定せずに記録する(現行の限界。README)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_tjunction.py" z > tj_z.txt

set -o pipefail
: > Screen.log
for c in m800_dry m800_wet m500_dry m500_wet m200_dry m200_wet; do
    ./encflow param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_tjunction.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== tjunction verification PASS ==="
else
    echo "=== tjunction verification FAIL ===" >&2
fi
exit $rc
