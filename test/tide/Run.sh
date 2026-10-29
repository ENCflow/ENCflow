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

# 構成3: 分布ファイルのリスト(titype = 4)で構成 1 と同じ潮位を与える。時間間隔を
# 数値の分(map)・単位を省いた文字列(mapc。分)・単位付きの文字列(maps)で
# 与えた 3 つが一致し、構成 1 の系列と S が一致すること(developer.md §88.5)
for tag in map mapc maps; do
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 \
        || { echo "ERROR: param_$tag run failed (see Screen_$tag.log)" >&2; exit 1; }
    grep -q "tide: dt_timaplist = 1.00000 min" Screen_$tag.log \
        || { echo "FAIL: $tag: 'tide: dt_timaplist = 1.00000 min' not printed" >&2; rc=1; }
done
for tag in mapc maps; do
    if diff -r -x 'param_*.txt' result_map result_$tag > /dev/null; then
        echo "=== map list: result_$tag is bit-identical to result_map ==="
    else
        echo "FAIL: result_$tag differs from result_map" >&2
        rc=1
    fi
done
if awk 'NR == FNR { if (FNR > 1) s[FNR] = $3; next }
        FNR > 1 { n++; d = $3 - s[FNR]; if (d < 0) d = -d
                  if (d > 1e-9 * ($3 < 0 ? -$3 : $3)) bad++ }
        END { exit (n < 20 || bad > 0) }' result/Log.txt result_map/Log.txt; then
    echo "=== map list: S agrees with the series of configuration 1 (rel 1e-9) ==="
else
    echo "FAIL: S of the map list run differs from configuration 1" >&2
    rc=1
fi
[ $rc -eq 0 ] && echo "=== tide verification PASS ===" || echo "=== tide verification FAIL ===" >&2
exit $rc
