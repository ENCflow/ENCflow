#!/bin/bash
# suspend: 浮遊砂の疎通・保存則検定と、等流の水路の平衡・適応の解析検定(逐次実行)
#   ./Run.sh
# 合否は Check_suspend.py。構成 1・2(param.txt・param_ik.txt)は体積保存・共動更新恒等・
# 活性確認、構成 3・4(param_eq.txt・param_eq_ik.txt。各 40 秒ほど)は平衡濃度と適応の
# 減衰率(developer.md §19.11)。
# 実行後の save/ は save_serial/ に、save_eq*/ は save_eq*_serial/ にも複製する
# (Run_MPI.sh のバイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_suspend.py" save || rc=1
rm -rf save_serial && cp -r save save_serial

# 板倉・岸(f_esform=2)でも同じ保存則検定を通す(save は上書きされる。
# MPI 比較用の save_serial は上で確保済み)
set -o pipefail
./encflow param_ik.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_suspend.py" save || rc=1

# 構成 3・4: 等流の水路(入力は make_eq.py が書く)。平衡濃度式 1 と板倉・岸式
python3 "$sdir/make_eq.py" z > zinit_eq.txt
python3 "$sdir/make_eq.py" h > hinit_eq.txt
for tag in eq eq_ik; do
    rm -rf result_$tag save_$tag
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag.txt run failed" >&2; exit 1; }
    echo ""
    python3 "$sdir/Check_suspend.py" $tag || rc=1
    rm -rf save_${tag}_serial && cp -r save_$tag save_${tag}_serial
done

if [ $rc -eq 0 ]; then
    echo "=== suspend verification PASS ==="
else
    echo "=== suspend verification FAIL ===" >&2
fi
exit $rc
