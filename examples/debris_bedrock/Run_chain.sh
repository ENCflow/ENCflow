#!/bin/bash
# examples/debris_bedrock 後半: 1 つの構成(long/<構成>/)で、出水と土石流を交互に回す
#   ./Run_chain.sh 構成 サイクル数
# 最初の出水(param_flood0.txt。新しく始める)のあと、各サイクルで土石流(param_debris.txt。
# 出水だけの構成にはない)と出水(param_flood.txt)を f_state_restore = 2 でつなぐ。どの段も同じ
# save_chain/ を読んで書く。各段の後に、台帳の表示と save のセルごとの z・Ri・sd を track.csv に
# 1 行足す(make_long.py track)。計算本体は変えない(docs/mountain_stream_plan.md §13)。
name=$1
ncyc=$2
root=$(dirname "$(readlink -f "$0")")
cd "$root/long/$name" || exit 1
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
rm -rf save_chain result track.csv
run() {   # $1 = 段, $2 = サイクル
    if ! "$root/encflow" "param_$1.txt" > "Screen_$1.log" 2>&1; then
        echo "FAIL: $name $1 (cycle $2); see long/$name/Screen_$1.log" >&2
        exit 1
    fi
    python3 "$root/make_long.py" track save_chain "$1" "$2" "Screen_$1.log" >> track.csv || exit 1
}
run flood0 0
for c in $(seq 1 "$ncyc"); do
    if [ -f param_debris.txt ]; then run debris "$c"; fi
    run flood "$c"
done
echo "$name: $ncyc cycles done"
