#!/bin/bash
# sublattice: 斜め副格子モードの減衰率ベンチマーク(逐次実行)
#   ./Run.sh [-s]   -s: スキーム 1・2 の比較ケース(param_s1/s2、param_smooth_s1/s2)も走らせる
#
# reference 比較ではなく、初期パターンへの射影振幅の時間変化で判定する:
#   param.txt         副格子で逆回転の渦(スキーム 3)→ e-folding 時間を表示(現状は無減衰の記録)
#   param_smooth.txt  対照の滑らかな渦(スキーム 3)→ 1 時間後に 50 % 以上残ること(PASS 条件)
# developer.md §68.36
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1
set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
./encflow param_smooth.txt | tee -a Screen.log || exit 1
./encflow param_mixed.txt | tee -a Screen.log || exit 1
if [ "$1" = "-s" ]; then
  for s in 1 2; do
    ./encflow param_s$s.txt | tee -a Screen.log || exit 1
    ./encflow param_smooth_s$s.txt | tee -a Screen.log || exit 1
    ./encflow param_mixed_s$s.txt | tee -a Screen.log || exit 1
  done
fi
set +o pipefail
echo ""
rc=0
python3 "$sdir/Check_sublattice.py" result alternating || rc=1
python3 "$sdir/Check_sublattice.py" result_smooth smooth || rc=1
python3 "$sdir/Check_sublattice.py" result_mixed mixed || rc=1
if [ "$1" = "-s" ]; then
  for s in 1 2; do
    python3 "$sdir/Check_sublattice.py" result_s$s alternating
    python3 "$sdir/Check_sublattice.py" result_smooth_s$s smooth
    python3 "$sdir/Check_sublattice.py" result_mixed_s$s mixed
  done
fi
rm -rf result_serial; mkdir -p result_serial; cp result_mixed/Log.txt result_serial/
if [ $rc -eq 0 ]; then echo "=== sublattice verification PASS ==="; else echo "=== sublattice verification FAIL ===" >&2; fi
exit $rc
