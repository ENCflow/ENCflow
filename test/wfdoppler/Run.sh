#!/bin/bash
# wfdoppler: 逐次実行 + 回帰テスト + 検定(流れによる沿岸の波浪場の変化 = 段 W3。developer.md §88)
#   ./Run.sh [-u]
# param.txt(逆流で阻止される不規則波)は reference 比較(Log.txt・wavefield.csv・Wh9998.txt・
# u9998.txt、ULP=0)と Check_wfdoppler.py blk。param_opp・param_fol・param_fol72(作用量の
# 流束の保存)、param_opp_u(非定常)、param_nocur・param_zero/param_zero_off(流れの作用の
# 有無)、param_river/param_river_nocur(河口の噴流)は Check_wfdoppler.py の検定のみ
# (reference 非依存)。
# param_rt1 → param_rt2 の再開の継続が通し計算(param.txt)と state.dat・swflow_enc.dat・
# wavefield.dat・最終分布でバイト一致すること、param_bad(f_wf_current = 2)が停止することを
# 確かめる
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列)
export FILES=${FILES:-"Log.txt wavefield.csv Wh9998.txt u9998.txt"}
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

for tag in opp fol fol72 opp_u nocur zero zero_off river river_nocur; do
    rm -rf result_$tag
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag run failed" >&2; exit 1; }
done
rm -rf result_rt1 result_rt2 save_rt
./encflow param_rt1.txt > Screen_rt1.log 2>&1 || { echo "ERROR: param_rt1 run failed" >&2; exit 1; }
./encflow param_rt2.txt > Screen_rt2.log 2>&1 || { echo "ERROR: param_rt2 run failed" >&2; exit 1; }

python3 Check_wfdoppler.py blk result || exit 1
python3 Check_wfdoppler.py opp result_opp || exit 1
python3 Check_wfdoppler.py fol result_fol || exit 1
python3 Check_wfdoppler.py fol72 result_fol result_fol72 || exit 1
python3 Check_wfdoppler.py unst result_opp_u result_opp || exit 1
python3 Check_wfdoppler.py nocur result_nocur result || exit 1
python3 Check_wfdoppler.py zero result_zero result_zero_off || exit 1
python3 Check_wfdoppler.py river result_river result_river_nocur || exit 1

# 再開の継続: 通し計算(save_all / result)と分割(save_rt / result_rt2)
for f in save_all/state.dat:save_rt/state.dat save_all/swflow_enc.dat:save_rt/swflow_enc.dat \
         save_all/wavefield.dat:save_rt/wavefield.dat \
         result/Wh9998.bil:result_rt2/Wh9998.bil result/u9998.bil:result_rt2/u9998.bil; do
    a=${f%%:*}; b=${f##*:}
    cmp -s "$a" "$b" || { echo "ERROR: restart continuation differs from the straight run: $b" >&2; exit 1; }
    echo "  ok   restart continuation matches the straight run: $b"
done

rm -rf result_bad
if ./encflow param_bad.txt > Screen_bad.log 2>&1; then
    echo "ERROR: param_bad should stop (f_wf_current = 2)" >&2; exit 1
fi
grep -q "f_wf_current must be 0 or 1" Screen_bad.log \
    || { echo "ERROR: param_bad stopped for another reason" >&2; exit 1; }
echo "  ok   f_wf_current = 2 stops"

echo "=== wfdoppler verification PASS ==="
