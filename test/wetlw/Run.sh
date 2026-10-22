#!/bin/bash
# wetlw: 湿潤侵食の剥離深の横方向拡散 wet_lw の検定(逐次実行)
#   ./Run.sh
# 構成 0(param_0: wet_lw なし = test/wash と同じ)と構成 l(param_l:
# wet_lw = 3 m)を走らせ、両構成の保存則(../suspend/Check_suspend.py)と
# 拡散の効き(Check_spread.py)を検定する。実行後の save_* は save_*_serial
# にも複製(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

set -o pipefail
./encflow param_0.txt | tee Screen.log || exit 1
./encflow param_l.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/../suspend/Check_suspend.py" save_0 || rc=1
python3 "$sdir/../suspend/Check_suspend.py" save_l || rc=1
python3 "$sdir/Check_spread.py" save_0 save_l || rc=1
rm -rf save_0_serial save_l_serial && cp -r save_0 save_0_serial && cp -r save_l save_l_serial

if [ $rc -eq 0 ]; then
    echo "=== wetlw verification PASS ==="
else
    echo "=== wetlw verification FAIL ===" >&2
fi
exit $rc
