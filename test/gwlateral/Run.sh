#!/bin/bash
# gwlateral: 逐次実行 + 検定(地下水の側方流 f_gwlateral = 1 の線形化 Boussinesq。developer.md §16.1・§16.6)
#   ./Run.sh
# reference は持たない(合否は Check_gwlateral.py の検定)。構成 1(param.txt → result)は
# ガウス形の小山の 2 次モーメントの伸び d<r²>/dt = 4D を、構成 2(param_strip.txt → result_strip)は
# 南北に長い帯のコサイン形の起伏の減衰率を、壁沿いの通水能の欠けを含む離散の予測と比べる。
# 構成 3・4(param_strip_open.txt・param_line_open.txt)は塞がれた斜めの配分の振り替え
# (f_gw_opening = 1)で 3 列・1 列の帯の減衰率が D k² に戻ることを確かめる
sdir=$(dirname "$(readlink -f "$0")")
"$sdir/../Scripts/Check_mode.sh" serial || exit 1
python3 "$sdir/make_init.py"

rm -rf result result_strip result_strip_open result_line_open
./encflow param.txt > Screen.log 2>&1 || { echo "ERROR: param.txt run failed" >&2; exit 1; }
for tag in strip strip_open line_open; do
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag.txt run failed" >&2; exit 1; }
done

python3 Check_gwlateral.py gauss result || exit 1
for tag in strip strip_open line_open; do
    python3 Check_gwlateral.py $tag result_$tag || exit 1
done

echo "=== gwlateral verification PASS ==="
