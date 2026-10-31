#!/bin/bash
# gwtani: 逐次実行 + 検定(谷(Tani)型のシナリオ: 急勾配・薄い土層の斜面の地下水。developer.md §16.7)
#   ./Run.sh
# reference は持たない(合否は Check_gwtani.py の検定)。構成 1〜4(param_uni_thin・uni_thick・
# thin_toe・thin_toe_k2)は一定の雨を受ける斜面で、雨の初期の地下貯留の一様な上昇と飽和の時刻
# (鉛直到達時間 T_v = d sy / r。鉛直浸透支配)、定常の地下水位と飽和域(側方流支配)を運動学的な
# 予測と比べる。構成 5(param_l2only)は層2の側方流だけで同じ定常の予測と比べる(塞がれた斜めの
# 配分の振り替えが層2だけの構成でも効くこと)。構成 R0〜R2(param_rt0・rt1・rt2)は側方流を
# 有効にしたリスタート往復
sdir=$(dirname "$(readlink -f "$0")")
"$sdir/../Scripts/Check_mode.sh" serial || exit 1
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}   # 41 セルの格子なのでスレッドの起動の方が重い
python3 "$sdir/make_data.py"

cfgs="uni_thin uni_thick thin_toe thin_toe_k2 l2only rt0 rt1 rt2"
rm -rf save_rt0 save_rt
for c in $cfgs; do
    rm -rf result_$c
    ./encflow param_$c.txt > Screen_$c.log 2>&1 || { echo "ERROR: param_$c.txt run failed" >&2; exit 1; }
done

rc=0
for c in uni_thin uni_thick thin_toe thin_toe_k2 l2only kcompare restart; do
    python3 "$sdir/Check_gwtani.py" $c || rc=1
done
if [ $rc -eq 0 ]; then
    echo "=== gwtani verification PASS ==="
else
    echo "=== gwtani verification FAIL ===" >&2
fi
exit $rc
