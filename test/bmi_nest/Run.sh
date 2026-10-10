#!/bin/bash
# bmi_nest: BMI の多格子公開(ネスト系 = 1 component、格子は grid id)の受け入れ試験
#   ./Run.sh
#
#   1. bmi/ をビルド(libencflow_bmi.so と検証ドライバ test_encflow_bmi)
#   2. python3 ../../bmi/python/test_nest.py — 格子情報・変数表・比 1:1 双方向の
#      恒等(子の内部 == ルートの足元、ルート == 単独ラン)・再 initialize・
#      同値 set を同一プロセスで検査(子の初期水深ファイル hinit_child.txt を生成)
#   3. 静的ドライバ test_encflow_bmi でネストと単独を走らせ Log が一致すること
#   4. bmi-tester(インストール済みのとき)をネスト系に対して実行
#      (pip install bmi-tester bmipy 'pytest<8' 'gimli.units==0.3.*')
#   逐次のみ(Python 用の共有ライブラリは逐次ビルド)。MPI でのネスト系の
#   BMI は test_encflow_bmi_mpi で確認する(bmi/README.md)。
cd "$(dirname "$0")" || exit 1
../Scripts/Check_mode.sh serial || exit 1
make -s -C ../../bmi || exit 1
rm -rf result_* hinit_child.txt
python3 ../../bmi/python/test_nest.py || { echo "=== bmi_nest FAIL (test_nest.py) ==="; exit 1; }
# 静的ドライバ: ネストのルート Log == 単独 Log(ビット一致)
../../bmi/test_encflow_bmi param_single.txt > Screen_single.log 2>&1 || { echo "=== bmi_nest FAIL (driver single) ==="; tail -5 Screen_single.log; exit 1; }
../../bmi/test_encflow_bmi param_root.txt > Screen_root.log 2>&1 || { echo "=== bmi_nest FAIL (driver nested) ==="; tail -5 Screen_root.log; exit 1; }
if cmp -s result_single/Log.txt result_root/Log.txt; then
    echo "bmi_nest: static driver: root Log == single Log (identical)"
else
    echo "=== bmi_nest FAIL: static driver root Log != single Log ==="; exit 1
fi
if python3 -c "import bmi_tester, bmipy" 2>/dev/null; then
    ../../bmi/python/check_bmi.sh param_root.txt nest.txt param_child.txt hinit_child.txt \
        || { echo "=== bmi_nest FAIL (bmi-tester) ==="; exit 1; }
else
    echo "bmi_nest: bmi-tester not installed; conformance test skipped"
fi
echo "=== bmi_nest PASS ==="
