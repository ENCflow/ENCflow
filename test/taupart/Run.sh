#!/bin/bash
# taupart: 急勾配礫床の抵抗分割(f_taupart)の検定(逐次実行。developer.md §89.30)
#   ./Run.sh [-u]
# 1. param.txt(分割なし、1500 s)を reference と比較する(回帰。-u で更新)。
# 2. 各構成(off = param.txt、d044・d19・d76・d0・d19_mpm)を 1500 s と 3000 s で回し、東辺を通った
#    掃流砂の台帳の差から定常の流砂量を得て、Check_taupart.py が流砂量式と比べる(3000 s の param は
#    tt と dir_result を置き換えて生成する)。
# 3. excl(f_taupart = 1 と fluv_taufac ≠ 1 の併用)が停止することを確かめる。
# result_d19/Log.txt は Log_d19_serial.txt にも複製する(Run_MPI.sh のバイト比較用)
sdir=$(dirname "$(readlink -f "$0")")
python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt
../Scripts/Run_case.sh serial "$@"
rc=$?
cp -f Screen.log Screen_off.log
mk2() { sed -e "s|^  tt = 1500|  tt = 3000|" -e "s|dir_result = 'result\([_a-z0-9]*\)'|dir_result = 'result\1_t2'|" "$1" > "$2"; }
set -o pipefail
mk2 param.txt param_off_t2.txt
./encflow param_off_t2.txt 2>&1 | tee Screen_off_t2.log || exit 1
for c in d044 d19 d76 d0 d19_mpm; do
    ./encflow param_$c.txt 2>&1 | tee Screen_$c.log || exit 1
    mk2 param_$c.txt param_${c}_t2.txt
    ./encflow param_${c}_t2.txt 2>&1 | tee Screen_${c}_t2.log || exit 1
done
set +o pipefail
cp -f result_d19/Log.txt Log_d19_serial.txt
if ./encflow param_excl.txt > Screen_excl.log 2>&1; then
    echo "FAIL: f_taupart = 1 with fluv_taufac /= 1 did not stop" >&2
    rc=1
elif grep -q "requires fluv_taufac = 1" Screen_excl.log; then
    echo "PASS: f_taupart = 1 with fluv_taufac /= 1 stops (exclusive)"
else
    echo "FAIL: excl stopped for another reason (see Screen_excl.log)" >&2
    rc=1
fi
echo ""
python3 "$sdir/Check_taupart.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== taupart verification PASS ==="
else
    echo "=== taupart verification FAIL ===" >&2
fi
exit $rc
