#!/bin/bash
# sedfeed: 給砂の検定(逐次実行。nofeed / feed1 / feed05 / qb / cseq / nofeed_creep)
#   ./Run.sh
# 合否は Check_sedfeed.py。save_* は save_*_serial にも複製(Run_MPI.sh の比較用)。
# 構成ごとの画面出力(台帳の行を含む)は Screen_<構成>.log にも残す(検定 7 が読む)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt

set -o pipefail
for c in nofeed feed1 feed05 qb cseq nofeed_creep; do
    ./encflow param_$c.txt 2>&1 | tee Screen_$c.log | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_sedfeed.py" || rc=1
for c in nofeed feed1 feed05 qb cseq nofeed_creep; do rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial; done

if [ $rc -eq 0 ]; then
    echo "=== sedfeed verification PASS ==="
else
    echo "=== sedfeed verification FAIL ===" >&2
fi
exit $rc
