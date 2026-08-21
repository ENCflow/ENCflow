#!/bin/bash
# avalanche: 流れ型雪崩(等価流体+速度比例連行)の検定(逐次実行)
#   ./Run.sh
# 合否は Check_avalanche.py(固体台帳・共動更新・連行活性・成長・停止)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" > dbinit.txt || exit 1

rc=0
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_avalanche.py" save || rc=1
rm -rf save_serial && cp -r save save_serial

if [ $rc -eq 0 ]; then
    echo "=== avalanche 検定 PASS ==="
else
    echo "=== avalanche 検定 FAIL ===" >&2
fi
exit $rc
