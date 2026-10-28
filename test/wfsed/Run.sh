#!/bin/bash
# wfsed: 逐次実行 + 回帰テスト + 検定(沿岸の波浪場による土砂の攪拌と輸送 = 段 W4・W5。developer.md §88)
#   ./Run.sh [-u]
# param.txt(海浜の沿岸漂砂。test/wfcurrent の基本 + 掃流砂・浮遊砂 + f_wfsed)は reference
# 比較(Log.txt・wavefield.csv・Z9998.txt・Hs9998.txt、ULP=0)と Check_wfsed.py beach・asym。
# param_stir(攪拌と平衡濃度)・param_bed(一様な流れの掃流砂)・param_closed(閉じた海盆の
# 土砂の保存)・param_storm と param_calm(高波浪の侵食と低波浪の回復)・param_turb(砕波の乱れに
# よる攪拌)は Check_wfsed.py の検定のみ(reference 非依存)。param_rt1 → param_rt2 の
# 再開の継続が通し計算(param.txt)と state.dat・swflow_enc.dat・wavefield.dat・最終分布で
# バイト一致すること、param_bad1〜5(不正な設定)が停止することを確かめる
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列)
export FILES=${FILES:-"Log.txt wavefield.csv Z9998.txt Hs9998.txt"}
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

for tag in stir bed closed storm calm turb; do
    rm -rf result_$tag save_$tag
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag run failed" >&2; exit 1; }
done
rm -rf result_rt1 result_rt2 save_rt
./encflow param_rt1.txt > Screen_rt1.log 2>&1 || { echo "ERROR: param_rt1 run failed" >&2; exit 1; }
./encflow param_rt2.txt > Screen_rt2.log 2>&1 || { echo "ERROR: param_rt2 run failed" >&2; exit 1; }

python3 Check_wfsed.py stir result_stir save_stir || exit 1
python3 Check_wfsed.py bed result_bed || exit 1
python3 Check_wfsed.py beach result || exit 1
python3 Check_wfsed.py closed save_closed || exit 1
python3 Check_wfsed.py asym result || exit 1
python3 Check_wfsed.py shore result_storm result_calm || exit 1
python3 Check_wfsed.py turb result_turb result || exit 1

# 再開の継続: 通し計算(save_all / result)と分割(save_rt / result_rt2)
for f in save_all/state.dat:save_rt/state.dat save_all/swflow_enc.dat:save_rt/swflow_enc.dat \
         save_all/wavefield.dat:save_rt/wavefield.dat \
         result/Z9998.bil:result_rt2/Z9998.bil result/Hs9998.bil:result_rt2/Hs9998.bil \
         result/Qby9998.bil:result_rt2/Qby9998.bil result/Qsy9998.bil:result_rt2/Qsy9998.bil; do
    a=${f%%:*}; b=${f##*:}
    cmp -s "$a" "$b" || { echo "ERROR: restart continuation differs from the straight run: $b" >&2; exit 1; }
    echo "  ok   restart continuation matches the straight run: $b"
done

# 不正な設定(停止すること)
stop_check() {   # stop_check <param> <期待するメッセージ>
    rm -rf result_bad
    if ./encflow "$1" > Screen_bad.log 2>&1; then
        echo "ERROR: $1 should stop" >&2; exit 1
    fi
    grep -q "$2" Screen_bad.log || { echo "ERROR: $1 stopped for another reason" >&2; exit 1; }
    echo "  ok   $1 stops ($2)"
}
stop_check param_bad1.txt "f_wfsed requires the coastal wave field"
stop_check param_bad2.txt "f_wfsed cannot be combined with the longshore transport of fn_wave"
stop_check param_bad3.txt "f_wfsed must be 0 or 1"
stop_check param_bad4.txt "f_wfsed of fn_geomorph requires f_wavefield=1"
stop_check param_bad5.txt "f_wfsed_turb requires f_wfsed=1"

echo "=== wfsed verification PASS ==="
