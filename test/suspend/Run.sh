#!/bin/bash
# suspend: 浮遊砂の疎通・保存則検定(逐次実行)
#   ./Run.sh
# 合否は Check_suspend.py(体積保存・共動更新恒等・活性確認)。
# 実行後の save/ は save_serial/ にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_suspend.py" save || rc=1
rm -rf save_serial && cp -r save save_serial

# 板倉・岸(f_esform=2)でも同じ保存則検定を通す(save は上書きされる。
# MPI 比較用の save_serial は上で確保済み)
set -o pipefail
./encflow param_ik.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_suspend.py" save || rc=1

if [ $rc -eq 0 ]; then
    echo "=== suspend 検定 PASS ==="
else
    echo "=== suspend 検定 FAIL ===" >&2
fi
exit $rc
