#!/bin/bash
# bedslide: 動く底層(f_bedslide)の検定(逐次実行)
#   ./Run.sh
# 構成1: 格子沿い斜面の Voellmy 速度(重心移動 vs 解析解)
# 構成2: 45° 回転斜面(構成1 との一致 = 8 近傍化の格子依存の検出器)
# 構成3: 斜面→湖の突入・水中ランアウト・造波・台帳
# 合否は Check_bedslide.py。save は save*_serial にも複製(Run_MPI 比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for k in zbench dbbench zrot dbrot z db; do
    python3 "$sdir/make_init.py" $k > $k.txt || exit 1
done

rc=0
set -o pipefail
./encflow param_bench.txt | tee Screen.log || exit 1
./encflow param_rot.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_bedslide.py" bench || rc=1
rm -rf save_bench_serial && cp -r save_bench save_bench_serial
rm -rf save_rot_serial && cp -r save_rot save_rot_serial

set -o pipefail
./encflow param.txt | tee Screen_tsunami.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_bedslide.py" tsunami || rc=1
rm -rf save_serial && cp -r save save_serial

if [ $rc -eq 0 ]; then
    echo "=== bedslide 検定 PASS ==="
else
    echo "=== bedslide 検定 FAIL ===" >&2
fi
exit $rc
