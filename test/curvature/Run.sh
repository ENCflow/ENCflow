#!/bin/bash
# curvature: 曲率項(f_dbcurv)の検定(逐次実行)
#   ./Run.sh
# 構成 off/on を同じ地形・土塊で走らせ、終端の重心位置を質点モデルと比較する。
# 合否は Check_curvature.py。save は save*_serial にも複製(Run_MPI 比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" z > zinit.txt

set -o pipefail
./encflow param_off.txt | tee Screen.log || exit 1
./encflow param_on.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
rc=0
python3 "$sdir/Check_curvature.py" save_off save_on || rc=1
rm -rf save_off_serial save_on_serial
cp -r save_off save_off_serial && cp -r save_on save_on_serial

if [ $rc -eq 0 ]; then
    echo "=== curvature 検定 PASS ==="
else
    echo "=== curvature 検定 FAIL ===" >&2
fi
exit $rc
