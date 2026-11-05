#!/bin/bash
# glacier: 氷河モジュールの検証(逐次実行)
#   ./Run.sh
#
# reference 比較ではなく解析解・不変量で合否を判定する:
#   1) Halfar ドーム(param.txt): SIA 相似解との定量比較+氷体積保存
#   2) カール形成スモーク(param_cirque.txt): 全プロセス疎通
#      (氷河形成・氷河下侵食・NaN なし)
#   4) 雪崩再配分の等方性(param_ava.txt): 円錐の雪が方向によらず再配分される
#      こと+水当量の保存
#   5) 侵食の結合長 gl_lc(param_lc.txt・param_lc2.txt・param_lc0.txt・
#      param_lc02.txt): V 字谷の侵食の形が gl_lc > 0 では格子によらず氷の幅に
#      広がること(gl_lc = 0 との比較)
#   6) Halfar ドームを SIA 流動の 4 近傍(gl_diagratio = 0。既定は 8 近傍の 9 点。§99)で計算する対照
#      (param_d4.txt。判定は 1) と同じ)
#   7) 谷の氷の流れの向きによる差(param_ch*.txt。8 近傍の 9 点と塞がれた配分の
#      振り替え。0° と 45° の 1 セル幅・3 セル幅の谷。45° の 3 本は 4 近傍の対照つき。§99)
# 判定は Check_halfar.py / Check_cirque.py / Check_ava.py / Check_lc.py / Check_chan.py

sdir=$(dirname "$(readlink -f "$0")")

# ビルドモードの整合性確認
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/Make_input.py" || exit 1

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
./encflow param_cirque.txt | tee Screen_cirque.log || exit 1
./encflow param_ava.txt | tee Screen_ava.log || exit 1
for c in lc lc2 lc0 lc02; do
    ./encflow param_$c.txt | tee Screen_$c.log || exit 1
done
./encflow param_d4.txt | tee Screen_d4.log || exit 1
for c in ch0w1 ch45w1 ch0w3 ch45w3 ch45w3q; do
    ./encflow param_$c.txt | tee Screen_$c.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_halfar.py" result Screen.log || rc=1
python3 "$sdir/Check_cirque.py" result_cirque || rc=1
python3 "$sdir/Check_ava.py" result_ava Screen_ava.log || rc=1
python3 "$sdir/Check_lc.py" || rc=1
python3 "$sdir/Check_halfar.py" result_d4 Screen_d4.log || rc=1
python3 "$sdir/Check_chan.py" || rc=1

# 構成3: 最小入力(既定値)と構成3'(既定値の明示)の同値検定(§65)
set -o pipefail
./encflow param_min.txt | tee Screen_min.log || exit 1
./encflow param_minx.txt | tee Screen_minx.log || exit 1
set +o pipefail
echo ""
if diff -r -I '^! ENCflow restart save' save_min save_minx > /dev/null && cmp -s result_min/Log.txt result_minx/Log.txt; then
    echo "=== defaults: save/ and Log.txt are bit-identical between the minimal input and the explicit defaults ==="
else
    echo "FAIL: minimal input (defaults) and explicit defaults differ" >&2
    rc=1
fi
ndef=$(grep -c "(default)" Screen_min.log)
[ "$ndef" -eq 5 ] || { echo "FAIL: expected 5 '(default)' lines, got $ndef" >&2; rc=1; }

if [ $rc -eq 0 ]; then
    echo "=== glacier verification PASS ==="
else
    echo "=== glacier verification FAIL ===" >&2
fi
exit $rc
