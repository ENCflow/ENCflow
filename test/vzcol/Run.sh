#!/bin/bash
# vzcol: 逐次実行 + 回帰テスト + 解析検定(VZ 共有参照柱。developer.md §87)
#   ./Run.sh [-u]
# param.txt は reference 比較(Log.txt・vz_zone.csv・vz_column.csv、ULP=0)と
# Check_vzcol.py base。param_fixed.txt(固定圧下端の定常解)・
# param_tight.txt(時間収束)・param_avg.txt(面積平均モード)は
# Check_vzcol.py の検定のみ(reference 非依存)
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export SKIPCOLS=6      # 検査対象外とする列番号(Log の Runge 列)
export FILES="Log.txt vz_zone.csv vz_column.csv"
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

python3 Check_vzcol.py base result || exit 1

for tag in fixed tight avg; do
    rm -rf result_$tag
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag run failed" >&2; exit 1; }
done
python3 Check_vzcol.py fixed result_fixed || exit 1
python3 Check_vzcol.py tight result result_tight || exit 1
python3 Check_vzcol.py avg result result_avg || exit 1

echo "=== vzcol verification PASS ==="
