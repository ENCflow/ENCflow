#!/bin/bash
# stageside: 境界として与えたセルの列(水位規定セル・湧き出し)から流れ出す水と、側方 Neumann の辺(逐次実行。
#   東端の列が水位規定セル = s3・s4、湧き出し = q3・q4。移流項の規則は、古い値 3・1・1・3 と、4 つの値 4・2・2・4)
#   ./Run.sh
# 合否は Check_stageside.py(4 構成とも最後まで計算して定常になること、岸沿いに一様なこと、規則の違う 2 構成の
# 結果が一致すること)。reference は持たない

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_stageside.py" > ss_z.txt || exit 1

rm -rf result_s3 result_s4 result_q3 result_q4
: > Screen.log
rc=0
for c in s3 s4 q3 q4; do
    # 計算が止まっても(発散)、検定に回して、どの項目が落ちたかを表示する
    ./encflow param_$c.txt >> Screen.log 2>&1 || { echo "ERROR: param_$c run failed (see Screen.log)" >&2; rc=1; }
done
echo ""

python3 "$sdir/Check_stageside.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== stageside verification PASS ==="
else
    echo "=== stageside verification FAIL ===" >&2
fi
exit $rc
