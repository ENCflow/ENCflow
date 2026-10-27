#!/bin/bash
# fluvial: 掃流砂 Exner の疎通・保存則検定(逐次実行)
#   ./Run.sh
# 合否は Check_fluvial.py(体積保存・共動更新恒等・活性確認)。
# param_creep.txt(クリープ併用)は体積保存・活性だけを見る(クリープは sd を動かさない)。
# param_creep_hs.txt(深さ依存クリープ併用。z と sd を共動更新)は 3 項目すべてを見る。
# 実行後の save*/ は save*_serial/ にも複製する(Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_fluvial.py" save || rc=1
rm -rf save_serial && cp -r save save_serial
# クリープ併用(帯界面のハロ。developer.md §19.9)
set -o pipefail
./encflow param_creep.txt | tee Screen_creep.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_fluvial.py" save_creep nosd || rc=1
rm -rf save_creep_serial && cp -r save_creep save_creep_serial
# 深さ依存クリープ併用(供給側の近傍の sd も読む。developer.md §88.8)
set -o pipefail
./encflow param_creep_hs.txt | tee Screen_creep_hs.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_fluvial.py" save_creep_hs || rc=1
rm -rf save_creep_hs_serial && cp -r save_creep_hs save_creep_hs_serial

if [ $rc -eq 0 ]; then
    echo "=== fluvial verification PASS ==="
else
    echo "=== fluvial verification FAIL ===" >&2
fi
exit $rc
