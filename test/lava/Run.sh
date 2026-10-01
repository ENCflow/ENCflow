#!/bin/bash
# lava: 溶岩流(Bingham 粘性重力流)の検定(逐次実行)
#   ./Run.sh
# 構成1: Huppert 相似解ベンチマーク(Newton 極限 + 台帳)
# 構成2: Bingham 停止・固化(h∞ 解析解 + 固化台帳)
# 合否は Check_lava.py。save は save*_serial にも複製(Run_MPI 比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" > zinit.txt

rc=0

# 構成1: Huppert(τ_y=0 の Newton 極限。相似解検定)
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save huppert || rc=1
rm -rf save_serial && cp -r save save_serial

# 構成2: Bingham 停止・固化
set -o pipefail
./encflow param_ty.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_lava.py" save_ty bingham || rc=1
rm -rf save_ty_serial && cp -r save_ty save_ty_serial

# 構成3: 最小入力(既定値)と構成3'(既定値の明示)の同値検定(§66)
set -o pipefail
./encflow param_min.txt | tee Screen_min.log || exit 1
./encflow param_minx.txt | tee Screen_minx.log || exit 1
set +o pipefail
echo ""
if diff -r save_min save_minx > /dev/null && cmp -s result_min/Log.txt result_minx/Log.txt; then
    echo "=== defaults: save/ and Log.txt are bit-identical between the minimal input and the explicit defaults ==="
else
    echo "FAIL: minimal input (defaults) and explicit defaults differ" >&2
    rc=1
fi
ndef=$(grep -c "(default)" Screen_min.log)
[ "$ndef" -eq 2 ] || { echo "FAIL: expected 2 '(default)' lines, got $ndef" >&2; rc=1; }

if [ $rc -eq 0 ]; then
    echo "=== lava 検定 PASS ==="
else
    echo "=== lava 検定 FAIL ===" >&2
fi
exit $rc
