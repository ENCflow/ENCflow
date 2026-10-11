#!/bin/bash
# bmi_vars: 機能依存の BMI 変数(動的変数表)と hg・swe の set の受け入れ試験
#   ./Run.sh
#
#   1. bmi/ をビルド(libencflow_bmi.so と検証ドライバ test_encflow_bmi)
#   2. python3 ../../bmi/python/test_vars.py --set — 構成 none / full / ga で
#      変数表の内容・get の値(解析値・分布出力との一致)・再 initialize・
#      同値 set の不変性・受理条件を検査(developer.md §76)
#   3. 静的ドライバ test_encflow_bmi で full を完走(全変数のメタデータ・get)
#   4. bmi-tester(インストール済みのとき)を full に対して実行
#   逐次のみ(Python 用の共有ライブラリは逐次ビルド)。MPI は
#   test_encflow_bmi_mpi で full を走らせ Log が逐次と一致することを確認する
cd "$(dirname "$0")" || exit 1
../Scripts/Check_mode.sh serial || exit 1
make -s -C ../../bmi || exit 1
rm -rf result_* Log_full_noset.txt
python3 ../../bmi/python/test_vars.py --set || { echo "=== bmi_vars FAIL (test_vars.py) ==="; exit 1; }
../../bmi/test_encflow_bmi param_full.txt > Screen_driver.log 2>&1 || { echo "=== bmi_vars FAIL (driver full) ==="; tail -5 Screen_driver.log; exit 1; }
if cmp -s Log_full_noset.txt result_full/Log.txt; then
    echo "bmi_vars: static driver: Log == Python run (identical)"
else
    echo "=== bmi_vars FAIL: static driver Log != Python run ==="; exit 1
fi
if python3 -c "import bmi_tester, bmipy" 2>/dev/null; then
    ../../bmi/python/check_bmi.sh param_full.txt || { echo "=== bmi_vars FAIL (bmi-tester) ==="; exit 1; }
else
    echo "bmi_vars: bmi-tester not installed; conformance test skipped"
fi
echo "=== bmi_vars PASS ==="
