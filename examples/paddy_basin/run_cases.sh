#!/bin/sh
# examples/paddy_basin: runs/cases.txt のケースを runs/ で計算する(make run が呼ぶ)
#   ./run_cases.sh [並列数]
# 1 ケース 1 スレッドで、並列数(既定 4)のケースを同時に計算する。計算済み(最後の分布 H0008.bil がある)ケースは
# 飛ばす
set -e
np=${1:-4}
cd "$(dirname "$0")/runs"
[ -f cases.txt ] || { echo "runs/cases.txt がない(make を先に)"; exit 1; }
todo=""
for c in $(cat cases.txt); do [ -f result_$c/H0008.bil ] || todo="$todo $c"; done
if [ -n "$todo" ]; then
    echo $todo | tr ' ' '\n' | OMP_NUM_THREADS=1 xargs -P $np -I{} sh -c \
        './encflow param_{}.txt > Screen_{}.log 2>&1 || { echo "FAIL: {}(runs/Screen_{}.log)"; exit 255; }'
fi
echo "$(wc -l < cases.txt) ケース計算済み"
