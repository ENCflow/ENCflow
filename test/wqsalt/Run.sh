#!/bin/bash
# wqsalt: 塩分まわりの水質の追加(水平の混合 wq_diff・析出と溶解 wq_csat / wq_kdis・海から入る水の濃度
#         wq_sea_conc・初期濃度の分布 fn_wq_c0)と、可能蒸発散の時系列入力(f_evmodel = 5)の検定
#         (逐次実行。developer.md §139)
#   ./Run.sh
# 12 ケース(param_<名前>.txt)を実行し、Check_cases.sh(Check_wqsalt.py)が解析解と保存則で判定する。
# reference は持たない。画面出力は Screen.log
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

cases="mix mixflow mixwall mixgv mixwd sat dis disk inf sea c0map evts"
: > Screen.log
for c in $cases; do
    echo "--- $c"
    rm -rf result_$c
    if ! ./encflow param_$c.txt >> Screen.log 2>&1; then
        echo "FAIL: $c の実行が異常終了した(Screen.log)" >&2
        exit 1
    fi
done
echo ""

rc=0
"$sdir/Check_cases.sh" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== wqsalt verification PASS ==="
else
    echo "=== wqsalt verification FAIL ===" >&2
fi
exit $rc
