#!/bin/bash
# wave_shore: 波浪による沿岸漂砂の検定(逐次実行。low / high / high0 / bar / bar0 / off / nowave)
#   ./Run.sh
# 合否は Check_wave_shore.py。save_* は save_*_serial にも複製(Run_MPI.sh の比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" sd > sdinit.txt
python3 "$sdir/make_init.py" z bar > zinit_bar.txt
python3 "$sdir/make_init.py" sd bar > sdinit_bar.txt

set -o pipefail
./encflow param_low.txt | tee Screen.log || exit 1
./encflow param_high.txt | tee -a Screen.log || exit 1
./encflow param_high0.txt | tee -a Screen.log || exit 1
./encflow param_bar.txt | tee -a Screen.log || exit 1
./encflow param_bar0.txt | tee -a Screen.log || exit 1
./encflow param_off.txt | tee -a Screen.log || exit 1
./encflow param_nowave.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_wave_shore.py" || rc=1
if cmp -s save_off/state.dat save_nowave/state.dat; then
    echo "=== off: state.dat is bit-identical to nowave (zero cost when disabled) ==="
else
    echo "FAIL: f_wave_longshore = 0 differs from the run without fn_wave" >&2
    rc=1
fi
for c in low high high0 bar bar0 off nowave; do rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial; done

if [ $rc -eq 0 ]; then
    echo "=== wave_shore verification PASS ==="
else
    echo "=== wave_shore verification FAIL ===" >&2
fi
exit $rc
