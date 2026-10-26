#!/bin/bash
# vzcol: 逐次実行 + 回帰テスト + 解析検定(VZ 共有参照柱。developer.md §87)
#   ./Run.sh [-u]
# param.txt は reference 比較(Log.txt、ULP=0)と
# Check_vzcol.py base。param_fixed.txt(固定圧下端の定常解)・
# param_tight.txt(時間収束)・param_avg.txt(面積平均モード)・
# param_sd0.txt(土層厚 0 のセルを含む区画)・param_hydro.txt(静水圧の初期条件)は
# Check_vzcol.py の検定のみ(reference 非依存)
# reference 比較は Log.txt(ULP=0)。vz_zone.csv・vz_column.csv は 16 桁で書くため
# CPU(-march=native のベクトル化)が違うと最終桁が変わり(Zen3 向けビルドで確認)、
# 他ホストの CI では ULP=0 が成立しない。CSV の内容は Check_*.py の解析検定で
# 確かめる。同じホストで作った reference と CSV もビット比較したいときは
#   FILES="Log.txt vz_zone.csv vz_column.csv" ./Run.sh
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export SKIPCOLS=6      # 検査対象外とする列番号(Log の Runge 列)
export FILES=${FILES:-Log.txt}
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

python3 Check_vzcol.py base result || exit 1

for tag in fixed tight avg sd0 hydro; do
    rm -rf result_$tag
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag run failed" >&2; exit 1; }
done
python3 Check_vzcol.py fixed result_fixed || exit 1
python3 Check_vzcol.py tight result result_tight || exit 1
python3 Check_vzcol.py avg result result_avg || exit 1
python3 Check_vzcol.py sd0 result_sd0 || exit 1
python3 Check_vzcol.py hydro result_hydro || exit 1

echo "=== vzcol verification PASS ==="
