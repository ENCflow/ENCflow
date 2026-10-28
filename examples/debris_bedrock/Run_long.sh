#!/bin/bash
# examples/debris_bedrock 後半の全構成を並列に回す(long/configs.txt。make_long.py が書く)
#   ./Run_long.sh [並列数](既定 4)
root=$(dirname "$(readlink -f "$0")")
cd "$root" || exit 1
[ -e encflow ] || make > /dev/null || exit 1
[ -f long/configs.txt ] || python3 make_long.py || exit 1
np=${1:-4}
t0=$(date +%s)
if xargs -P "$np" -L 1 ./Run_chain.sh < long/configs.txt; then
    echo "all configurations done ($(( $(date +%s) - t0 )) s)"
else
    echo "some configurations failed" >&2
    exit 1
fi
