#!/bin/bash
# tide: 逐次実行 + 回帰テスト(潮位境界の疎通)
#   ./Run.sh [-u]
#
# 使い方:  ./Run.sh        実行して reference と比較(なければ作成)
#          ./Run.sh -u     実行して reference を更新

# --- ケース固有の設定(必要に応じて) ---
#export PARAM=param.txt
#export FILES="Log.txt"
export ULP=1      # 印字の最終桁を単位とした許容誤差

#export OMP_NUM_THREADS=24
#export OMP_PROC_BIND=close
#export OMP_PLACES=cores

export SKIPCOLS=4      # 検査対象外とする列番号

../Scripts/Run_case.sh serial "$@" || exit 1

# 構成2: 最小入力(空の &list_tide = 固定潮位 0 m)と構成2'(既定値の明示)の
# 同値検定(developer.md §67)
rc=0
set -o pipefail
./encflow param_min.txt | tee Screen_min.log || exit 1
./encflow param_minx.txt | tee Screen_minx.log || exit 1
set +o pipefail
echo ""
if diff -r -x 'param_*.txt' result_min result_minx > /dev/null; then
    echo "=== defaults: result/ is bit-identical between the minimal input and the explicit defaults ==="
else
    echo "FAIL: minimal input (defaults) and explicit defaults differ" >&2
    rc=1
fi
grep -q "titype = 1 (default" Screen_min.log || { echo "FAIL: default titype line not printed" >&2; rc=1; }
[ $rc -eq 0 ] && echo "=== tide verification PASS ===" || echo "=== tide verification FAIL ===" >&2
exit $rc
