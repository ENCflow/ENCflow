#!/bin/bash
# bldgdebris: 家屋破壊・瓦礫ラスタ場の疎通・保存則・片方向結合・リスタート往復・空隙率帰還の検定(逐次実行)
#   ./Run.sh
# 合否は Check_bldgdebris.py(材積保存・破壊/堆積の活性・平坦部到達)と、
# 構成2(流木+瓦礫)と構成2'(流木のみ)の state.dat/driftwood.dat バイト一致
# (片方向結合 = 瓦礫モジュールは流れと流木を変えない)、リスタート往復、
# 空隙率帰還あり/なしの総貯水量 S(t) の一致(体積保存)。
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

# 構成4: 空隙率への帰還あり(gv=0.6 の平坦部)と構成4'(同一設定で帰還なし)
set -o pipefail
./encflow param_gv.txt | tee -a Screen.log || exit 1
./encflow param_gv0.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_bldgdebris.py" save_gv || rc=1
# 閉領域・降雨入力のみなので総貯水量 S の時系列は帰還の有無によらず同一
# (空隙率の変更が体積を保存する検定。f_disp_debug=1 で全有効桁)
if diff <(awk 'NR>1 {print $1, $3}' result_gv/Log.txt) <(awk 'NR>1 {print $1, $3}' result_gv0/Log.txt) > /dev/null; then
    echo "=== void-ratio feedback: total storage S(t) is identical with and without feedback ==="
else
    echo "FAIL: total storage S(t) differs between f_bdgv=1 and f_bdgv=0 (volume not conserved)" >&2
    rc=1
fi
rm -rf save_gv_serial && cp -r save_gv save_gv_serial

if [ $rc -eq 0 ]; then
    echo "=== bldgdebris verification PASS ==="
else
    echo "=== bldgdebris verification FAIL ===" >&2
fi
exit $rc
