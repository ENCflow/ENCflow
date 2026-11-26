#!/bin/sh
# examples/coarse_channel: 系列のケースを runs/ で計算する(make が呼ぶ)
#   ./run_series.sh 系列 [並列数]
# 粗い格子のケースは 1 ケース 1 スレッドで並列数(既定 4)ずつ、細かい格子のケース(名前が _fine で終わる)は
# 1 ケースずつ並列数のスレッドで計算する。計算済み(最後の出力がある)ケースは飛ばす。
set -e
se=$1
np=${2:-4}
cd "$(dirname "$0")/runs"
[ -f cases_$se.txt ] || { echo "runs/cases_$se.txt がない(make gen を先に)"; exit 1; }
done_case() {   # 最後の出力: 細かい格子は 4 時間、粗い格子は 8 時間
    case $1 in *_fine) [ -f result_$1/E0004.txt ] ;; *) [ -f result_$1/E0008.txt ] ;; esac
}
todo=""
for c in $(grep -v '_fine$' cases_$se.txt); do done_case $c || todo="$todo $c"; done
if [ -n "$todo" ]; then
    echo $todo | tr ' ' '\n' | OMP_NUM_THREADS=1 xargs -P $np -I{} sh -c \
        './encflow param_{}.txt > Screen_{}.log 2>&1 || { echo "FAIL: {}(runs/Screen_{}.log)"; exit 255; }'
fi
for c in $(grep '_fine$' cases_$se.txt || true); do
    done_case $c && continue
    echo "$c(細かい格子)"
    OMP_NUM_THREADS=$np ./encflow param_$c.txt > Screen_$c.log 2>&1 || { echo "FAIL: $c(runs/Screen_$c.log)"; exit 1; }
done
echo "$se: $(wc -l < cases_$se.txt) ケース計算済み"
