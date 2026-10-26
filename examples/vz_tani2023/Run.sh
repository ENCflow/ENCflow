#!/bin/bash
# examples/vz_tani2023: 谷(2023)の VZ 計算の再現(KIEX・MREX・MR1・TY1・TY2・KI1・KI2)
#   ./Run.sh <論文の PDF>     抽出 → 格子入力 → 計算(7 事例)→ 比較
#   ./Run.sh                  data/ に抽出済みなら計算と比較だけ
set -e
cd "$(dirname "$(readlink -f "$0")")"
if [ $# -ge 1 ]; then
    python3 extract_tani2023.py "$1" data
fi
EVENTS="KIEX MREX MR1 TY1 TY2 KI1 KI2"
for EV in $EVENTS; do
    if [ ! -e data/precip_$EV.txt ]; then
        echo "data/precip_$EV.txt がありません。論文の PDF を指定して ./Run.sh <PDF> を実行してください" >&2
        exit 1
    fi
done
make
for EV in $EVENTS; do
    ev=$(echo "$EV" | tr 'A-Z' 'a-z')
    ./encflow param_$ev.txt > Screen_$ev.log 2>&1 || { echo "ERROR: param_$ev.txt" >&2; exit 1; }
done
python3 compare_tani2023.py $EVENTS
