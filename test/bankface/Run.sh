#!/bin/bash
# bankface: 河岸面の掃流遮断・供給量制限の検定(逐次実行)
#   ./Run.sh
# 合否は Check_bankface.py(体積保存・乾いた河岸の不変・共動更新・活性・可動層下限)。
# 実行後の save*/ は save*_serial/ にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
./encflow param_thin.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bankface.py" save 10.0 || rc=1
python3 "$sdir/Check_bankface.py" save_thin 0.0005 || rc=1
rm -rf save_serial save_thin_serial
cp -r save save_serial && cp -r save_thin save_thin_serial

if [ $rc -eq 0 ]; then
    echo "=== bankface verification PASS ==="
else
    echo "=== bankface verification FAIL ===" >&2
fi
exit $rc
