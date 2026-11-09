#!/bin/bash
# wetbank: 雨で濡れた河岸が斜めのラスタ河道の水深を変えないことの検定(逐次実行)
#   ./Run.sh
# make_init.py が 36 ケース(形 9 = Δx 50 m・1 セル幅の θ 0・10・22.5・30・45°、θ 22.5° の 1 セル幅の
# Δx 100・25 m、幅 100 m の 2・4 セル × 乾いた河岸・雨 20 mm/h × f_advection_donor 0・3)の入力と設定を
# 生成し、全ケースを実行して Check_wetbank.py が判定する。reference は持たない。画面出力は Screen.log
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
