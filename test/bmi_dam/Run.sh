#!/bin/bash
# bmi_dam: ダムの量の BMI 公開と外部運転(f_dam_mode = 6)の受け入れ試験
#   ./Run.sh
#
#   1. bmi/ をビルド(libencflow_bmi.so と検証ドライバ test_encflow_bmi)
#   2. python3 ../../bmi/python/test_dam.py — 変数表とダムの点の格子・外部運転の
#      等価性(ダム 2 = ダム 1)・見本の制御器(ダム 3)・外部運転でないダムへの
#      set の無視・get と CSV の一致・体積保存・再 initialize を検査(developer.md §133)
#   3. 見本 dam_control.py をコマンドとして実行し、外部運転のダム 2・3 の最終水位が
#      初期水位 104 m の ±10 cm に収まること
#   4. 静的ドライバ test_encflow_bmi で完走(ダムの格子の情報・ダムの量の get・
#      目標放流量の set を毎歩)
#   5. 外部運転と合わない設定(モード 6 の dam_tadashigaki、負の dam_q0)が encflow の
#      起動時に止まること
#   6. bmi-tester(インストール済みのとき)
#   逐次のみ(Python 用の共有ライブラリは逐次ビルド)。MPI は test_encflow_bmi_mpi で
#   静的ドライバを走らせ、ダムの CSV が逐次と一致することを確認する(README.md)。
cd "$(dirname "$0")" || exit 1
../Scripts/Check_mode.sh serial || exit 1
make -s -C ../../bmi || exit 1
rm -rf result result_* wrk_* Screen_*.log
python3 ../../bmi/python/test_dam.py || { echo "=== bmi_dam FAIL (test_dam.py) ==="; exit 1; }
python3 ../../bmi/python/dam_control.py param.txt --csv wrk_dam_control.csv > Screen_control.log 2>&1 \
    || { echo "=== bmi_dam FAIL (dam_control.py) ==="; tail -5 Screen_control.log; exit 1; }
if awk '/^dam [23]: final level/ { n++; d = $5 - 104.0; if (d < 0) d = -d; if (d > 0.10) bad = 1 }
        END { exit !(n == 2 && !bad) }' Screen_control.log; then
    echo "bmi_dam: dam_control.py: $(grep -E '^dam [23]:' Screen_control.log | tr '\n' ' ')"
else
    echo "=== bmi_dam FAIL: dam_control.py did not keep dams 2 and 3 at 104 m +- 10 cm ==="
    cat Screen_control.log; exit 1
fi
../../bmi/test_encflow_bmi param.txt > Screen_driver.log 2>&1 \
    || { echo "=== bmi_dam FAIL (static driver) ==="; tail -5 Screen_driver.log; exit 1; }
echo "bmi_dam: static driver: $(grep 'all checks passed' Screen_driver.log)"
# 外部運転と合わない設定は起動時に止まる(BMI を使わない encflow で)
stop_check() {   # stop_check <置き換える行> <置き換え後> <期待するメッセージ>
    rm -rf result_bad
    python3 - "$1" "$2" <<'EOF' || exit 1
import sys
s = open("param.txt").read()
old, new = sys.argv[1] + "\n", sys.argv[2] + "\n"
assert s.count(old) == 1 and s.count("dir_result = 'result'") == 1, old
s = s.replace(old, new).replace("dir_result = 'result'", "dir_result = 'result_bad'")
open("wrk_param_bad.txt", "w").write(s)
EOF
    if ./encflow wrk_param_bad.txt > Screen_bad.log 2>&1; then
        echo "=== bmi_dam FAIL: [$2] should stop ==="; exit 1
    fi
    grep -q "$3" Screen_bad.log \
        || { echo "=== bmi_dam FAIL: [$2] stopped for another reason ==="; tail -3 Screen_bad.log; exit 1; }
    echo "bmi_dam: stops: $3"
}
stop_check "  dam_h_init(2) = 104.0" "  dam_h_init(2) = 104.0
  dam_tadashigaki(2) = 110.0" "dam_tadashigaki of dam 2 does not apply to f_dam_mode=6"
stop_check "  dam_q0(3) = 0.2" "  dam_q0(3) = -0.1" \
    "dam_q0 of dam 3 (mode 6: the release until a target is set from outside) must be >= 0"
rm -rf result_bad
if python3 -c "import bmi_tester, bmipy" 2>/dev/null; then
    ../../bmi/python/check_bmi.sh param.txt data_bmi_dam/mask.txt data_bmi_dam/z.txt \
        || { echo "=== bmi_dam FAIL (bmi-tester) ==="; exit 1; }
else
    echo "bmi_dam: bmi-tester not installed; conformance test skipped"
fi
echo "=== bmi_dam PASS ==="
