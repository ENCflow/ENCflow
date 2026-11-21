#!/bin/bash
# wetbank: 雨で濡れた河岸が斜めのラスタ河道の水深を変えないことの検定(逐次実行)
#   ./Run.sh
# make_init.py が 108 ケース(形 9 = Δx 50 m・1 セル幅の θ 0・10・22.5・30・45°、θ 22.5° の 1 セル幅の
# Δx 100・25 m、幅 100 m の 2・4 セル × 乾いた河岸・雨 20 mm/h × 移流項の構成 6 つ = 古い値の組み合わせ
# 3・1・1・3 の組(f_advection_donor 0・3、3 に f_advection_lateral = 0)と、4 つの値の組み合わせ 4・2・2・4 の
# 組(同じ 3 つ)。どれも 4 つのスイッチを明示)の入力と設定を生成し、全ケースを実行して
# Check_wetbank.py が判定する。reference は持たない。画面出力は Screen.log
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" || exit 1
cases=$(python3 "$sdir/make_init.py" list)

: > Screen.log
for c in $cases; do
    echo "--- $c"
    if ! ./encflow p_$c.txt >> Screen.log 2>&1; then
        echo "FAIL: $c の実行が異常終了した(Screen.log)" >&2
        exit 1
    fi
done
echo ""
python3 "$sdir/Check_wetbank.py" table
