#!/bin/bash
# splashlc: 曲率の相関長 spl_lc による谷の波長選択の検定(逐次実行)
#   ./Run.sh
# 構成 g(param_g: spl_lc = 0、格子の κ)= 短波長が速く成長 /
# 構成 l(param_l: spl_lc = 2 m)= 長波長が成長し短波長は減衰、を
# Check_select.py で検定する。実行後の save_* は save_*_serial にも複製
# (Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_terrain.py" || exit 1

set -o pipefail
./encflow param_g.txt | tee Screen.log || exit 1
./encflow param_l.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_select.py" || rc=1
rm -rf save_g_serial save_l_serial && cp -r save_g save_g_serial && cp -r save_l save_l_serial

if [ $rc -eq 0 ]; then
    echo "=== splashlc verification PASS ==="
else
    echo "=== splashlc verification FAIL ===" >&2
fi
exit $rc
