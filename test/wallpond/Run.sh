#!/bin/bash
# wallpond: 河道の堤防の仮想壁面の向こうの湛水が、河道の流れを変えないことの検定(逐次実行。developer.md §134)
#   ./Run.sh
# make_wallpond.py が 14 ケース(軸に沿う直線の河道を解像 2 セル・サブグリッド 1 セルで、45° の直線の河道を
# 4 連結の 1 セルの階段で表し、堤内地を乾いた・湛水した、などに変えたもの。階段は移流項の構成 4 つ)の入力と
# 設定を生成し、全ケースを実行して Check_wallpond.py が判定する。reference は持たない。画面出力は Screen.log
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_wallpond.py" || exit 1
cases=$(python3 "$sdir/make_wallpond.py" list)

: > Screen.log
for c in $cases; do
    echo "--- $c"
    if ! ./encflow p_$c.txt >> Screen.log 2>&1; then
        echo "FAIL: $c の実行が異常終了した(Screen.log)" >&2
        exit 1
    fi
done
echo ""

rc=0
python3 "$sdir/Check_wallpond.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== wallpond verification PASS ==="
else
    echo "=== wallpond verification FAIL ===" >&2
fi
exit $rc
