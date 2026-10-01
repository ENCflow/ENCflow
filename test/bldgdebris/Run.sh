#!/bin/bash
# bldgdebris: 家屋破壊・瓦礫ラスタ場の疎通・保存則・片方向結合・リスタート往復検定(逐次実行)
#   ./Run.sh
# 合否は Check_bldgdebris.py(材積保存・破壊/堆積の活性・平坦部到達)と、
# 構成2(流木+瓦礫)と構成2'(流木のみ)の state.dat/driftwood.dat バイト一致
# (片方向結合 = 瓦礫モジュールは流れと流木を変えない)、リスタート往復。
# 実行後の save 系は save*_serial/ にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1
rc=0

# 構成1: 浸水深判定(片方向)
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_bldgdebris.py" save || rc=1
rm -rf save_serial && cp -r save save_serial

# 構成2: 流木+瓦礫(荷重判定)と構成2': 流木のみ
set -o pipefail
./encflow param_dw.txt | tee -a Screen.log || exit 1
./encflow param_dwonly.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_bldgdebris.py" save_dw || rc=1
for f in state.dat driftwood.dat; do
    if cmp -s save_dw/$f save_dwonly/$f; then
        echo "=== one-way coupling: $f is bit-identical with and without the debris module ==="
    else
        echo "FAIL: $f differs between the debris+driftwood run and the driftwood-only run" >&2
        rc=1
    fi
done
rm -rf save_dw_serial && cp -r save_dw save_dw_serial

# 構成3: リスタート分割継続(0→30 s 保存、復元して 30→60 s)
rm -rf save_rt
set -o pipefail
./encflow param_rt1.txt | tee -a Screen.log || exit 1
./encflow param_rt2.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
for f in bldgdebris.dat state.dat; do
    if cmp -s save_rt/$f save/$f; then
        echo "=== restart continuation: $f is bit-identical to the straight run ==="
    else
        echo "FAIL: restart continuation differs from the straight run: $f" >&2
        rc=1
    fi
done

if [ $rc -eq 0 ]; then
    echo "=== bldgdebris verification PASS ==="
else
    echo "=== bldgdebris verification FAIL ===" >&2
fi
exit $rc
