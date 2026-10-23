#!/bin/bash
# berode: 側岸侵食の検定(逐次実行。K_b と 2 K_b、定着の河岸係数 fix0 / fix1、崩落土塊 slump / slump0)
#   ./Run.sh
# 合否は Check_berode.py。save_* は save_*_serial にも複製(Run_MPI.sh の比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt

set -o pipefail
./encflow param_kb1.txt 2>&1 | tee Screen.log || exit 1
./encflow param_kb2.txt 2>&1 | tee -a Screen.log || exit 1
./encflow param_fix0.txt 2>&1 | tee -a Screen.log || exit 1
./encflow param_fix1.txt 2>&1 | tee -a Screen.log || exit 1
./encflow param_slump.txt 2>&1 | tee -a Screen.log || exit 1
./encflow param_slump0.txt 2>&1 | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_berode.py" || rc=1
for c in kb1 kb2 fix0 fix1 slump slump0; do rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial; done

if [ $rc -eq 0 ]; then
    echo "=== berode verification PASS ==="
else
    echo "=== berode verification FAIL ===" >&2
fi
exit $rc
