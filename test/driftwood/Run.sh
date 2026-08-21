#!/bin/bash
# driftwood: 流木ラスタ場の疎通・保存則・リスタート往復検定(逐次実行)
#   ./Run.sh
# 合否は Check_driftwood.py(材積保存・流木化/堆積の活性・平坦部到達)。
# 実行後の save 系は save*_serial/ にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

# 構成1: 土石流+流木(侵食連行)
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_driftwood.py" save || rc=1
rm -rf save_serial && cp -r save save_serial

# 構成2: 洪水氾濫での流木(水理的流失。geomorph なし)
set -o pipefail
./encflow param_flood.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_driftwood.py" save_flood || rc=1
rm -rf save_flood_serial && cp -r save_flood save_flood_serial

# 構成3: リスタート分割継続(0→15 + 復元 15→30 が通し 0→30 と一致するか。
# 本ケースはバイト一致で成立する(2026-08-21 実測)。将来一致が崩れた
# 場合は §28.4 の「継続等価は ULP 水準」に該当するか原因を特定すること)
rm -rf save_rt
set -o pipefail
./encflow param_rt1.txt | tee -a Screen.log || exit 1
./encflow param_rt2.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
for f in driftwood.dat state.dat; do
    if cmp -s save_rt/$f save/$f; then
        echo "=== restart continuation: $f is bit-identical to the straight run ==="
    else
        echo "FAIL: restart continuation differs from the straight run: $f" >&2
        rc=1
    fi
done

if [ $rc -eq 0 ]; then
    echo "=== driftwood verification PASS ==="
else
    echo "=== driftwood verification FAIL ===" >&2
fi
exit $rc
