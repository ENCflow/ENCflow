#!/bin/bash
# sliver: 幅が 0 に近いサブグリッド河道のセルが、そのセルの無い構成と同じ流れになることの検定(逐次実行。developer.md §136)
#   ./Run.sh
# make_sliver.py が 4 ケース(45° の 1 列に 1 セルの河道と、格子に沿う 2 行の河道に、幅 0.01 m の河道のセルを
# 添える・添えない)の入力と設定を生成し、全ケースを実行して Check_sliver.py が判定する。
# reference は持たない。画面出力は Screen.log
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_sliver.py" || exit 1
cases=$(python3 "$sdir/make_sliver.py" list)

: > Screen.log
for c in $cases; do
    echo "--- $c"
    if ! ./encflow p_$c.txt >> Screen.log 2>&1; then
        echo "FAIL: $c の実行が異常終了した(Screen.log)" >&2
        exit 1
    fi
done
echo ""

rc=0
python3 "$sdir/Check_sliver.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== sliver verification PASS ==="
else
    echo "=== sliver verification FAIL ===" >&2
fi
exit $rc
