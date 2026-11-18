#!/bin/bash
# river_flowline: 河道マスクを標高の落水線に載せ直す前処理(utils/river_flowline)の検定
#   ./Run.sh
# (1) 秩父の 4 つの格子(50・100・200・500 m)の元の河道マスクを載せ直し、置いてある載せ直し済みのマスク
#     (test/chichibu/data_chichibu*/…_river_flowline.txt)とバイト比較する。落水線の集水面積の最大が
#     領域のセル数に一致すること(終点が 1 つの領域では、全てのセルが終点へ流れる)も確かめる
# (2) 200 m の格子は bil と GeoTIFF(tutorials/chichibu/data_chichibu)でも回す。表示する内訳がテキストと
#     同じこと、書いたファイルを元の河道マスクとして読み直したときの内訳がテキストと同じこと(書いた
#     ラスタの中身の確認)、bil の出力が置いてある bil とバイト一致することを確かめる
# 計算は回さない(encflow は使わない)。ビルドの設定は ../../make.inc に従う
cd "$(dirname "$0")" || exit 2
make -s -C ../../utils/river_flowline || exit 2
X=../../utils/river_flowline/river_flowline
C=../chichibu
U=../../tutorials/chichibu/data_chichibu
rc=0
fail() { echo "FAIL: $*" >&2; rc=1; }
stats() { grep -E '^(domain|original|  on the flowlines)' "$1"; }     # 表示する内訳の 3 行

# (1) テキスト: 4 つの格子
for g in "50m data_chichibu_50m Chichibu_50m_filled.txt" "100m data_chichibu Chichibu_100m_filled2.txt" \
         "200m data_chichibu_200m Chichibu_200m_filled.txt" "500m data_chichibu_500m Chichibu_500m_filled.txt"; do
    set -- $g
    n=$1; d=$C/$2; z=$3; b=${z%%_filled*}
    if ! $X param_$n.txt $d/$z $d/${b}_basin.txt $d/${b}_river.txt wrk_$n.txt wrk_acc_$n.txt > wrk_$n.log 2>&1; then
        fail "$n: river_flowline stopped (see wrk_$n.log)"
        continue
    fi
    if cmp -s wrk_$n.txt $d/${b}_river_flowline.txt; then
        echo "PASS: $n: re-mapped mask is byte-identical to $2/${b}_river_flowline.txt" \
             "($(sed -n 's/^original channel mask \([0-9]*\) cells -> re-mapped channel mask \([0-9]*\) cells/\1 -> \2 cells/p' wrk_$n.log))"
    else
        fail "$n: re-mapped mask differs from $2/${b}_river_flowline.txt"
    fi
    nd=$(sed -n 's/^domain \([0-9]*\) cells.*/\1/p' wrk_$n.log)
    ne=$(sed -n 's/.*flowline end points \([0-9]*\)$/\1/p' wrk_$n.log)
    amax=$(awk '{ for (i = 1; i <= NF; i++) if ($i > m) m = $i } END { print m + 0 }' wrk_acc_$n.txt)
    if [ "$ne" = 1 ] && [ "$amax" = "$nd" ]; then
        echo "PASS: $n: largest catchment area = $amax cells = the whole domain (one end point)"
    else
        fail "$n: largest catchment area $amax cells, domain $nd cells, end points $ne"
    fi
done

# (2) bil・GeoTIFF: 200 m の格子。比べる相手は、テキストの 1 回目と、その出力をもう一度載せ直した 2 回目
d=$C/data_chichibu_200m
$X param_200m.txt $d/Chichibu_200m_filled.txt $d/Chichibu_200m_basin.txt wrk_200m.txt wrk_200m_twice.txt \
    > wrk_200m_twice.log 2>&1 || fail "200m: second pass (text) stopped (see wrk_200m_twice.log)"
for f in bil tif; do
    if ! $X param_200m_$f.txt $U/Chichibu_200m_filled.$f $U/Chichibu_200m_basin.$f $U/Chichibu_200m_river.$f \
            wrk_200m.$f > wrk_200m_$f.log 2>&1; then
        fail "200m $f: river_flowline stopped (see wrk_200m_$f.log)"
        continue
    fi
    if [ -n "$(stats wrk_200m_$f.log)" ] && [ "$(stats wrk_200m_$f.log)" = "$(stats wrk_200m.log)" ]; then
        echo "PASS: 200m $f: same breakdown as text"
    else
        fail "200m $f: breakdown differs from text (wrk_200m_$f.log, wrk_200m.log)"
    fi
    if $X param_200m_$f.txt $U/Chichibu_200m_filled.$f $U/Chichibu_200m_basin.$f wrk_200m.$f \
            wrk_200m_twice.$f > wrk_200m_twice_$f.log 2>&1 \
       && [ -n "$(stats wrk_200m_twice_$f.log)" ] \
       && [ "$(stats wrk_200m_twice_$f.log)" = "$(stats wrk_200m_twice.log)" ]; then
        echo "PASS: 200m $f: the written raster, read back as the channel mask, gives the same breakdown as text"
    else
        fail "200m $f: the written raster does not read back like the text result (wrk_200m_twice_$f.log)"
    fi
done
if cmp -s wrk_200m.bil $U/Chichibu_200m_river_flowline.bil; then
    echo "PASS: 200m bil: byte-identical to tutorials/chichibu/data_chichibu/Chichibu_200m_river_flowline.bil"
else
    fail "200m bil: differs from tutorials/chichibu/data_chichibu/Chichibu_200m_river_flowline.bil"
fi

if [ $rc -eq 0 ]; then
    echo "=== river_flowline verification PASS ==="
else
    echo "=== river_flowline verification FAIL ===" >&2
fi
exit $rc
