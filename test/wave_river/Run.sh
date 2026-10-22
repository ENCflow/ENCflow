#!/bin/bash
# wave_river: 河口の規則 wave_vmax の検定(逐次実行。nowave / novmax / vmax)
#   ./Run.sh
# 合否は Check_wave_river.py。save_* は save_*_serial にも複製(Run_MPI.sh の比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" sd > sdinit.txt

set -o pipefail
./encflow param_nowave.txt | tee Screen.log || exit 1
./encflow param_novmax.txt | tee -a Screen.log || exit 1
./encflow param_vmax.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_wave_river.py" || rc=1
for c in nowave novmax vmax; do rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial; done

if [ $rc -eq 0 ]; then
    echo "=== wave_river verification PASS ==="
else
    echo "=== wave_river verification FAIL ===" >&2
fi
exit $rc
