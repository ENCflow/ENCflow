#!/bin/bash
# debris: 土石流(浸食起動型)の疎通・保存則検定(逐次実行)
#   ./Run.sh
# 合否は Check_debris.py(固体保存・共動更新恒等・侵食/堆積の活性)。
# 実行後の save/ は save_serial/ にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

set -o pipefail
./a.out param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_debris.py" save || rc=1
rm -rf save_serial && cp -r save save_serial

# 構成2: 江頭則(E-D = 江頭・芦田1992、抵抗 = 江頭構成則)
set -o pipefail
./a.out param_eg.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_eg eg || rc=1
rm -rf save_eg_serial && cp -r save_eg save_eg_serial

if [ $rc -eq 0 ]; then
    echo "=== debris 検定 PASS ==="
else
    echo "=== debris 検定 FAIL ===" >&2
fi
exit $rc
