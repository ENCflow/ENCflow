#!/bin/bash
# repose: 安息角崩落の検定(逐次実行)
#   ./Run.sh
# 合否は Check_repose.py。save/ は save_serial/ にも複製(Run_MPI.sh の比較用)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" > zinit.txt

set -o pipefail
./encflow param.txt | tee Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_repose.py" save || rc=1
rm -rf save_serial && cp -r save save_serial

if [ $rc -eq 0 ]; then
    echo "=== repose verification PASS ==="
else
    echo "=== repose verification FAIL ===" >&2
fi
exit $rc
