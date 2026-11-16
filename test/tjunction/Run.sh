#!/bin/bash
# tjunction: 1 セル幅の T 字の合流(逐次実行。軸に沿う合流・45° 回した合流 × f_advection_lateral 0・1 ×
# 3 つの流量比 × 乾いた岸・濡れた岸 = 24 構成と、向きを変えた 6 構成)
#   ./Run.sh
# 合否は Check_tjunction.py(定常・質量の収支・下流の等流・合流でエネルギーが増えないこと。
# f_advection_lateral = 1 では、合流の堰上げが岸の濡れによらないこと・運動量の理論の中での位置・
# 格子の向きによらないことも判定する。0 では記録する。README)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for g in ax rot; do
    for o in "" mx my xy; do
        python3 "$sdir/make_tjunction.py" z $g $o > "$(python3 -c "import sys; sys.path.insert(0, '$sdir'); import make_tjunction as m; print(m.zfile('$g', '$o'))")"
    done
done

set -o pipefail
: > Screen.log
for c in $(python3 "$sdir/make_tjunction.py" names); do
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
