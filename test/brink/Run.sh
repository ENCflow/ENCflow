#!/bin/bash
# brink: 池の出口の段落ち(1 セル幅の水路)と、屈曲直後の辺の風上値 f_advection_bend(逐次実行。17 構成 × 2 組 =
# 古い値の組み合わせ 3・1・1・3 の組と、4 つの値の組み合わせ 4・2・2・4 の組。どちらも 4 つのスイッチを明示)
#   ./Run.sh
# 合否は Check_brink.py(直線の水路は限界流と不等流の理論、段落ちの直前が斜めの水路は棚のエネルギー水頭が
# 池を超えないこと、等流の階段状の水路と幅 2 セルの水路は f_advection_bend の 0 と 1(新しい組は 2)で水深が変わらないこと、
# 落差の先の池は跳水の位置が理論と合い、足元の直後が斜めの水路が直線の水路と同じ水面形になること、合流部の
# 池は、定常な流入に対して水面が定常に落ち着くかどうか)

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for k in straight diag stair pstraight pfoot pbrink wide jpond jtee; do
    python3 "$sdir/make_brink.py" z $k > br_z_$k.txt || exit 1
done

set -o pipefail
: > Screen.log
for c in st0 st1 dg0 dg1 sr0 sr1 ps1 pf0 pf1 pb0 pb1 wd0 wd1 jp0 jp1 jt0 jt1 \
         st0n st2 dg0n dg2 sr0n sr2 ps2 pf0n pf2 pb0n pb2 wd0n wd2 jp0n jp2 jt0n jt2; do
    ./encflow param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_brink.py" old || rc=1      # 古い値の組み合わせの組
python3 "$sdir/Check_brink.py" new || rc=1      # 4 つの値の組み合わせの組
if [ $rc -eq 0 ]; then
    echo "=== brink verification PASS ==="
else
    echo "=== brink verification FAIL ===" >&2
    exit 1
fi
