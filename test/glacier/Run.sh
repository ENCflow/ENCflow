#!/bin/bash
# glacier: 氷河モジュールの検証(逐次実行)
#   ./Run.sh
#
# reference 比較ではなく解析解・不変量で合否を判定する:
#   1) Halfar ドーム(param.txt): SIA 相似解との定量比較+氷体積保存
#   2) カール形成スモーク(param_cirque.txt): 全プロセス疎通
#      (氷河形成・氷河下侵食・NaN なし)
# 判定は Check_halfar.py / Check_cirque.py

sdir=$(dirname "$(readlink -f "$0")")

# ビルドモードの整合性確認
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/Make_input.py" || exit 1

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
./encflow param_cirque.txt | tee Screen_cirque.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_halfar.py" result Screen.log || rc=1
python3 "$sdir/Check_cirque.py" result_cirque || rc=1

if [ $rc -eq 0 ]; then
    echo "=== glacier verification PASS ==="
else
    echo "=== glacier verification FAIL ===" >&2
fi
exit $rc
