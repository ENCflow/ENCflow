#!/bin/bash
# rockfall: 崩落と崖錐の検定(逐次実行)
#   ./Run.sh
# 合否は Check_rockfall.py。save/ は save_serial/ にも複製(Run_MPI.sh の比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" > zinit.txt

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_rockfall.py" save || rc=1
rm -rf save_serial && cp -r save save_serial
# 窓版(rf_rc = 3 m)
./encflow param_rc.txt | tee Screen_rc.log || exit 1
echo ""
python3 "$sdir/Check_rockfall.py" save_rc result_rc rc=3 || rc=1
rm -rf save_rc_serial && cp -r save_rc save_rc_serial

if [ $rc -eq 0 ]; then
    echo "=== rockfall verification PASS ==="
else
    echo "=== rockfall verification FAIL ===" >&2
fi
exit $rc
