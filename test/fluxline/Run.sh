#!/bin/bash
# fluxline: 逐次実行 + 検定(流量測線の角度掃引。developer.md §24.3)
#   ./Run.sh
# reference は持たない(合否は Check_fluxline.py)。同じ定常の流れを、構成 1(param_stair.txt)は
# セル番号指定、構成 2(param_xy.txt)は実座標指定の測線で測る(各 30 秒ほど)。
# 結果は result_*_serial/ にも複製する(Run_MPI.sh のバイト比較用)
sdir=$(dirname "$(readlink -f "$0")")
"$sdir/../Scripts/Check_mode.sh" serial || exit 1
python3 "$sdir/make_init.py"

rc=0
for tag in stair xy; do
    rm -rf result_$tag
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag.txt run failed" >&2; exit 1; }
    python3 Check_fluxline.py $tag || rc=1
    rm -rf result_${tag}_serial && cp -r result_$tag result_${tag}_serial
done

if [ $rc -eq 0 ]; then
    echo "=== fluxline verification PASS ==="
else
    echo "=== fluxline verification FAIL ===" >&2
fi
exit $rc
