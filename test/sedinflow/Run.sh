#!/bin/bash
# sedinflow: 区間流入の土砂濃度時系列の台帳検定(逐次実行)
#   ./Run.sh
# 合否は Check_sedinflow.py(体積保存・共動更新恒等・活性確認)。
# 実行後の save/ は save_serial/ にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_sedinflow.py" save || rc=1
rm -rf save_serial && cp -r save save_serial

# 流砂量指定(inflow_qs = C・Q と同量)でも同じ台帳が閉じることを検定
# (期待値は同じ C・Q・tt = Qs・tt。save は上書きされる)
set -o pipefail
./encflow param_qs.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_sedinflow.py" save || rc=1

if [ $rc -eq 0 ]; then
    echo "=== sedinflow 検定 PASS ==="
else
    echo "=== sedinflow 検定 FAIL ===" >&2
fi
exit $rc
