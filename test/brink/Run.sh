#!/bin/bash
# brink: 池の出口の段落ち(1 セル幅の水路)と、屈曲直後の辺の風上値 f_advection_bend(逐次実行。6 構成)
#   ./Run.sh
# 合否は Check_brink.py(直線の水路は限界流と不等流の理論、段落ちの直前が斜めの水路は棚のエネルギー水頭が
# 池を超えないこと、等流の階段状の水路は f_advection_bend の 0 と 1 で水深が変わらないこと)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for k in straight diag stair; do
    python3 "$sdir/make_brink.py" z $k > br_z_$k.txt || exit 1
done

set -o pipefail
: > Screen.log
for c in st0 st1 dg0 dg1 sr0 sr1; do
    ./encflow param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

if python3 "$sdir/Check_brink.py"; then
    echo "=== brink verification PASS ==="
else
    echo "=== brink verification FAIL ===" >&2
    exit 1
fi
