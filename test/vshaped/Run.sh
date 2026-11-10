#!/bin/bash
# vshaped: V 字流域の降雨流出を運動学的波の理論解と比べる(逐次実行。格子 20 m、向き 0° と 45°)
#   ./Run.sh
#
# reference 比較ではなく理論解との定量比較で合否を判定する(Check_vshaped.py。
# 出口の流量の NRMSE ≤ 0.04、ピークが格子上の流域の面積 × 降雨強度に 1 % 以内、
# 立ち上がりの時刻が理論の ±3 分、水収支が 1 % 以内)。
# 逐次結果の測線 CSV は result_serial/ に控えを置き、Run_MPI.sh のバイト一致確認に使う。

sdir=$(dirname "$(readlink -f "$0")")

../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" || exit 1

set -o pipefail
./encflow param_r0.txt | tee Screen.log || exit 1
./encflow param_r45.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_vshaped.py" result_r0 result_r45 || rc=1

rm -rf result_serial
mkdir -p result_serial/r0 result_serial/r45
cp -r result_r0/fluxes result_serial/r0/
cp -r result_r45/fluxes result_serial/r45/

if [ $rc -eq 0 ]; then
    echo "=== vshaped verification PASS ==="
else
    echo "=== vshaped verification FAIL ===" >&2
fi
exit $rc
