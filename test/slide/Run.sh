#!/bin/bash
# slide: 瞬時流動化(f_release)と斜面安定判定(f_slide)の疎通・保存則検定
#   ./Run.sh
# 構成1(param.txt): 崩壊深指定の時刻発火 → 流下・堆積(save/)
# 構成2(param_fs.txt): 降雨 → 飽和 → Fs<1 → 自動流動化(save_fs/)
# 実行後の save/, save_fs/ は *_serial/ にも複製する(Run_MPI.sh 用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

# 崩壊深分布(D=1m, i∈[5,15], j∈[5,16]。Check_slide.py の期待値と対)
python3 "$sdir/make_dbinit.py" > dbinit.txt || exit 1

rc=0

set -o pipefail
./a.out param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_slide.py" save release || rc=1
rm -rf save_serial && cp -r save save_serial

set -o pipefail
./a.out param_fs.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""
python3 "$sdir/Check_slide.py" save_fs fslide || rc=1
rm -rf save_fs_serial && cp -r save_fs save_fs_serial

if [ $rc -eq 0 ]; then
    echo "=== slide 検定 PASS ==="
else
    echo "=== slide 検定 FAIL ===" >&2
fi
exit $rc
