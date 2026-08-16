#!/bin/bash
# volcano: 火山流動(等価流体モード)の検定(逐次実行)
#   ./Run.sh
# 構成1: Voellmy 定常等流ベンチマーク(解析解 + 台帳)
# 構成2: 一定停止応力 τ_y のランアウト・停止検定
# 合否は Check_volcano.py。save は save*_serial にも複製(Run_MPI 比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" db > dbinit.txt

rc=0

# 構成1: Voellmy(f_dbed=0 + f_dbres=4。定常等流の解析解検定)
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_volcano.py" save voellmy || rc=1
rm -rf save_serial && cp -r save save_serial

# 構成2: τ_y 一定停止応力(f_dbed=0 + f_dbres=5 + f_release + f_dbstop)
set -o pipefail
./encflow param_ty.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_volcano.py" save_ty tauy || rc=1
rm -rf save_ty_serial && cp -r save_ty save_ty_serial

if [ $rc -eq 0 ]; then
    echo "=== volcano 検定 PASS ==="
else
    echo "=== volcano 検定 FAIL ===" >&2
fi
exit $rc
