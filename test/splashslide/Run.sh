#!/bin/bash
# splashslide: 固結/未固結の対照実験(逐次実行)
#   ./Run.sh
# 構成1(param_c: f_splash のみ)= 谷が成長 / 構成2(param_l:
# + f_debris/f_slide, c'=0)= 谷が維持されない、を Check_contrast.py で
# 検定する。実行後の save_* は save_*_serial にも複製(Run_MPI.sh の
# バイト比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_terrain.py" || exit 1

set -o pipefail
./encflow param_c.txt | tee Screen.log || exit 1
./encflow param_l.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_contrast.py" || rc=1
rm -rf save_c_serial save_l_serial && cp -r save_c save_c_serial && cp -r save_l save_l_serial

if [ $rc -eq 0 ]; then
    echo "=== splashslide verification PASS ==="
else
    echo "=== splashslide verification FAIL ===" >&2
fi
exit $rc
