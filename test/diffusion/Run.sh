#!/bin/bash
# diffusion: 拡散項のガウス形ジェット・解析解ベンチマーク(逐次実行)
#   ./Run.sh
#
# reference 比較ではなく解析解との定量比較で合否を判定する:
#   1) param.txt      Δx = 1 m、dt = 0.05 s  → 解析解と比較
#   2) param_fine.txt Δx = 0.5 m、dt = 0.02 s → 同じ解析解と比較(格子収束の確認)
# 判定は Check_analytic.py(各プローブの最大絶対誤差 < 5e-4 m/s = U0 の 1%)。
# 逐次結果のプローブ CSV は result_serial/ に控えを置き、Run_MPI.sh の
# ビット一致確認に使う。

sdir=$(dirname "$(readlink -f "$0")")

# ビルドモードの整合性確認
../Scripts/Check_mode.sh serial || exit 1

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
./encflow param_fine.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_analytic.py" result/probes 1.0 || rc=1
python3 "$sdir/Check_analytic.py" result_fine/probes 0.5 || rc=1

rm -rf result_serial
mkdir -p result_serial
cp -r result/probes result_serial/

if [ $rc -eq 0 ]; then
    echo "=== diffusion verification PASS ==="
else
    echo "=== diffusion verification FAIL ===" >&2
fi
exit $rc
