#!/bin/bash
# bldgdrag: 家屋のある水路の等流(逐次実行。3 構成)
#   ./Run.sh
# 合否は Check_bldgdrag.py

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt
for c in shallow deep dense; do
    python3 "$sdir/make_init.py" gv $c > gv_$c.txt
    python3 "$sdir/make_init.py" bb $c > bb_$c.txt
done

set -o pipefail
./encflow param_shallow.txt | tee Screen.log || exit 1
./encflow param_deep.txt | tee -a Screen.log || exit 1
./encflow param_dense.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bldgdrag.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== bldgdrag verification PASS ==="
else
    echo "=== bldgdrag verification FAIL ===" >&2
fi
exit $rc
