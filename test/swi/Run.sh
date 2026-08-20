#!/bin/bash
# swi: 土壌雨量指数(気象庁3段タンク)の参照解ベンチマーク(逐次実行)
#   ./Run.sh
# 合否は Check_swi.py(RK4 高分解能積分の参照解と比較)。
# 実行後の save/ と Swi 出力は *_serial に複製する(Run_MPI.sh 比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

rc=0
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_swi.py" result || rc=1
rm -rf save_serial && cp -r save save_serial
cp -f result/Swi9998.txt result/Swi9999.txt result/Swit9999.txt save_serial/

if [ $rc -eq 0 ]; then
    echo "=== swi 検定 PASS ==="
else
    echo "=== swi 検定 FAIL ===" >&2
fi
exit $rc
