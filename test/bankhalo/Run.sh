#!/bin/bash
# bankhalo: 堤防の越流の追い越し上限と実効平面積率 af(逐次実行。2 構成 = 河道幅、河道幅 + 断面形 σ。developer.md §120)
#   ./Run.sh
# reference を持たない検定型。合否は Check_bankhalo.py(閉じた箱の水の保存と、深く潜った堤防を越えて
# 両岸の水位差が縮まること)。ランク数によらないことは Run_MPI.sh が確かめる

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for k in z rw w e; do
    python3 "$sdir/make_bankhalo.py" $k > bh_$k.txt
done

set -o pipefail
: > Screen.log
for c in param param_sect; do
    ./encflow $c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bankhalo.py" result result_sect || rc=1
if [ $rc -eq 0 ]; then
    echo "=== bankhalo verification PASS ==="
else
    echo "=== bankhalo verification FAIL ===" >&2
fi
exit $rc
