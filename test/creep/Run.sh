#!/bin/bash
# creep: 斜面クリープのガウス丘・解析解ベンチマーク(逐次実行)
#   ./Run.sh
#
# reference 比較ではなく解析解との定量比較で合否を判定する:
#   1) morfac=1, tt=50s  → 解析解と比較
#   2) morfac=2, tt=25s  → 同じ地形時間 τ=50s の解析解と比較(加速の妥当性)
# 判定は Check_analytic.py(最大絶対誤差 < 5e-3 m = 丘高の 0.5%)

sdir=$(dirname "$(readlink -f "$0")")

# ビルドモードの整合性確認
../Scripts/Check_mode.sh serial || exit 1

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
./encflow param_morfac2.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_analytic.py" result/probes 1.0 || rc=1
python3 "$sdir/Check_analytic.py" result_morfac2/probes 2.0 || rc=1

if [ $rc -eq 0 ]; then
    echo "=== creep ベンチマーク PASS ==="
else
    echo "=== creep ベンチマーク FAIL ===" >&2
fi
exit $rc
