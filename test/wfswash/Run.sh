#!/bin/bash
# wfswash: 逐次実行 + 検定(遡上域の輸送 f_wfswash = 汀線の面の岸沖・沿岸の正味の輸送。developer.md §90.21)
#   ./Run.sh
# reference は持たない(合否は Check_wfswash.py の検定、再開の往復のバイト比較、不正な設定の停止)。
# rate・diag(1 回の更新の量を式と倍精度で照合)・eq・mild・steep・obl・cliff は波→流れの外力なし
# (静水面のまま)で式を確かめ、flow は波→流れ・掃流砂・浮遊砂と一緒に閉じた海盆で回す。
# param_rt1 → param_rt2 の再開の継続が通し計算(param_flow.txt)と state.dat・swflow_enc.dat・
# wavefield.dat・最終分布でバイト一致すること(入射波の波高は時系列で、時刻の関数として毎ステップ
# 受け渡すので保存しない)、param_bad1〜4(不正な設定)が停止することを確かめる
sdir=$(dirname "$(readlink -f "$0")")
"$sdir/../Scripts/Check_mode.sh" serial || exit 1
python3 "$sdir/make_z.py"

rm -rf result_rate result_diag result_eq result_mild result_steep result_obl result_cliff result_flow result_rt1 result_rt2 \
       save_rate save_diag save_eq save_mild save_steep save_obl save_cliff save_flow save_rt
for tag in rate diag eq mild steep obl cliff flow rt1 rt2; do
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag run failed" >&2; exit 1; }
done

python3 Check_wfswash.py rate result_rate save_rate || exit 1
python3 Check_wfswash.py diag result_diag save_diag || exit 1
python3 Check_wfswash.py eq save_eq || exit 1
python3 Check_wfswash.py mild save_mild || exit 1
python3 Check_wfswash.py steep save_steep || exit 1
python3 Check_wfswash.py obl result_obl save_obl || exit 1
python3 Check_wfswash.py cliff result_cliff save_cliff || exit 1
python3 Check_wfswash.py flow result_flow save_flow || exit 1

# 再開の継続: 通し計算(save_flow / result_flow)と分割(save_rt / result_rt2)
for f in save_flow/state.dat:save_rt/state.dat save_flow/swflow_enc.dat:save_rt/swflow_enc.dat \
         save_flow/wavefield.dat:save_rt/wavefield.dat \
         result_flow/Z9998.bil:result_rt2/Z9998.bil result_flow/Hs9998.bil:result_rt2/Hs9998.bil; do
    a=${f%%:*}; b=${f##*:}
    cmp -s "$a" "$b" || { echo "ERROR: restart continuation differs from the straight run: $b" >&2; exit 1; }
    echo "  ok   restart continuation matches the straight run: $b"
done

# 不正な設定(停止すること)
stop_check() {   # stop_check <param> <期待するメッセージ>
    rm -rf result_bad save_bad
    if ./encflow "$1" > Screen_bad.log 2>&1; then
        echo "ERROR: $1 should stop" >&2; exit 1
    fi
    grep -q "$2" Screen_bad.log || { echo "ERROR: $1 stopped for another reason" >&2; exit 1; }
    echo "  ok   $1 stops ($2)"
}
stop_check param_bad1.txt "f_wfswash requires f_wfsed=1"
stop_check param_bad2.txt "f_wfswash requires wfswash_tanbe"
stop_check param_bad3.txt "wfswash_tanbe must be in"
stop_check param_bad4.txt "f_wfswash must be 0 or 1"
rm -rf result_bad save_bad

echo "=== wfswash verification PASS ==="
