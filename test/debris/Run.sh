#!/bin/bash
# debris: 土石流(浸食起動型)の疎通・保存則検定(逐次実行)
#   ./Run.sh
# 合否は Check_debris.py(固体保存・共動更新恒等・侵食/堆積の活性)と、構成 7 の
# Check_debris_eq.py(斜面等流の平衡濃度)。
# 実行後の save/ は save_serial/ にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_debris.py" save || rc=1
rm -rf save_serial && cp -r save save_serial

# 構成2: 江頭則(E-D = 江頭・芦田1992、抵抗 = 江頭構成則)
set -o pipefail
./encflow param_eg.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_eg eg || rc=1
rm -rf save_eg_serial && cp -r save_eg save_eg_serial

# 構成3: 高橋・中川(1991)則(E-D = 式(12)(27)、抵抗 = 式(22)-(25))
set -o pipefail
./encflow param_tk.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_tk eg || rc=1
rm -rf save_tk_serial && cp -r save_tk save_tk_serial

# 構成4: 構成3 + 間隙水連行(f_dbwet=1。developer.md §28.7)
set -o pipefail
./encflow param_tkwet.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_tkwet wet || rc=1
rm -rf save_tkwet_serial && cp -r save_tkwet save_tkwet_serial

# 構成5: 構成1 + 掃流砂(f_fluvial。転置した斜面・薄い可動層。developer.md §28.13)
python3 "$sdir/make_fluv.py" > z_fluv.txt || exit 1
set -o pipefail
./encflow param_fluv.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_fluv fluv || rc=1
rm -rf save_fluv_serial && cp -r save_fluv save_fluv_serial

# 構成6: 構成1 + 地下水計算と併用する間隙水(f_dbwet=2。developer.md §28.7)
set -o pipefail
./encflow param_gw.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_debris.py" save_gw gw || rc=1
rm -rf save_gw_serial && cp -r save_gw save_gw_serial

# 構成7: 斜面等流の平衡濃度(勾配の違う 6 本の水路。高橋型の C∞ との突合。developer.md §28.15)
python3 "$sdir/make_eq.py" z > z_eq.txt || exit 1
python3 "$sdir/make_eq.py" h > h_eq.txt || exit 1
rm -rf result_eq save_eq
./encflow param_eq.txt > Screen_eq.log 2>&1 || { echo "ERROR: param_eq.txt run failed" >&2; exit 1; }
python3 "$sdir/Check_debris_eq.py" save_eq || rc=1
rm -rf save_eq_serial && cp -r save_eq save_eq_serial

if [ $rc -eq 0 ]; then
    echo "=== debris verification PASS ==="
else
    echo "=== debris verification FAIL ===" >&2
fi
exit $rc
