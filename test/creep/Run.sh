#!/bin/bash
# creep: 斜面クリープのガウス丘・解析解ベンチマーク(逐次実行)
#   ./Run.sh
#
# reference 比較ではなく解析解との定量比較で合否を判定する:
#   1) morfac=1, tt=50s  → 解析解と比較
#   2) morfac=2, tt=25s  → 同じ地形時間 τ=50s の解析解と比較(加速の妥当性)
#   3) 深さ依存クリープ(creep_hstar。developer.md §88.8)の 4 構成: 厚い土層(解析解と
#      従来の線形拡散に一致)・薄い土層・供給量制限・裸岩(不変)
# 判定は Check_analytic.py(最大絶対誤差 < 5e-3 m = 丘高の 0.5%)と Check_hstar.py
# (岩盤面の不変・土層の保存・sd >= 0 ほか)。save_hstar_* は save_hstar_*_serial にも
# 複製(Run_MPI.sh の比較用)

sdir=$(dirname "$(readlink -f "$0")")

# ビルドモードの整合性確認
../Scripts/Check_mode.sh serial || exit 1

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
./encflow param_morfac2.txt | tee -a Screen.log || exit 1
for c in thick thin lim bare; do
    ./encflow param_hstar_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_analytic.py" result/probes 1.0 || rc=1
python3 "$sdir/Check_analytic.py" result_morfac2/probes 2.0 || rc=1
python3 "$sdir/Check_analytic.py" result_hstar_thick/probes 1.0 || rc=1
for c in thick thin lim bare; do
    python3 "$sdir/Check_hstar.py" $c || rc=1
    rm -rf save_hstar_${c}_serial && cp -r save_hstar_$c save_hstar_${c}_serial
done

if [ $rc -eq 0 ]; then
    echo "=== creep verification PASS ==="
else
    echo "=== creep verification FAIL ===" >&2
fi
exit $rc
