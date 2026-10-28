#!/bin/bash
# wfcurrent: 逐次実行 + 回帰テスト + 検定(沿岸の波浪場の流れへの作用 = 段 W2。developer.md §90)
#   ./Run.sh [-u]
# param.txt(海浜の沿岸流。不規則波・斜め入射・ローラーあり)は reference 比較(Log.txt・
# E9998.txt・v9998.txt、ULP=1・RTOL=1e-6)と Check_wfcurrent.py roller。
# param_setup(セットアップ)・param_flat(一様水深の沿岸流と岸沖の釣り合い)・param_long
# (ローラーなし)・param_rot(90° 回した格子)・param_cur(流れの波への作用 = 段 W3 を加えた
# 双方向の連成)・param_diff(拡散項。側方 Neumann の辺の拡散 = §90.12)・param_rotdiff(その 90° 回した
# 格子)・param_mix(砕波による水平混合 wf_break_visc)は Check_wfcurrent.py の検定のみ
# (reference 非依存)。param_rt1 → param_rt2
# の再開の継続が通し計算(param.txt)と state.dat・swflow_enc.dat・wavefield.dat・最終分布で
# バイト一致すること、param_bad(wf_flow = 3)が停止することを確かめる
# reference を作ったマシン(AVX-512 の Xeon)と CPU の違うマシン(CI のランナー)では、-march=native の
# ベクトル化の差で最終桁がずれ、波と流れの双方向の連成で Log.txt の S が相対 1e-7 程度、出力が
# 印字の最終桁 1 つ変わる(developer.md §90.18)。比較は ULP=1・RTOL=1e-6 にし、その差で変わる
# wavefield.csv(収支の残差・反復回数の列)は外す。同じマシンでは環境変数で上書きしてビット比較できる:
#   ULP=0 RTOL=0 FILES="Log.txt wavefield.csv E9998.txt v9998.txt" ./Run.sh
sdir=$(dirname "$(readlink -f "$0")")
export ULP=${ULP:-1}       # 印字の最終桁 1 つ分まで(CPU の違うマシンの最終桁の差。上の注)
export RTOL=${RTOL:-1e-6}
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列)
export FILES=${FILES:-"Log.txt E9998.txt v9998.txt"}
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

for tag in setup flat long rot cur diff rotdiff mix; do
    rm -rf result_$tag
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag run failed" >&2; exit 1; }
done
rm -rf result_rt1 result_rt2 save_rt
./encflow param_rt1.txt > Screen_rt1.log 2>&1 || { echo "ERROR: param_rt1 run failed" >&2; exit 1; }
./encflow param_rt2.txt > Screen_rt2.log 2>&1 || { echo "ERROR: param_rt2 run failed" >&2; exit 1; }

python3 Check_wfcurrent.py setup result_setup || exit 1
python3 Check_wfcurrent.py flat result_flat || exit 1
python3 Check_wfcurrent.py long result_long || exit 1
python3 Check_wfcurrent.py roller result result_long || exit 1
python3 Check_wfcurrent.py rot result result_rot || exit 1
python3 Check_wfcurrent.py cur result_cur result || exit 1
python3 Check_wfcurrent.py diff result_diff result || exit 1
python3 Check_wfcurrent.py rot result_diff result_rotdiff || exit 1
python3 Check_wfcurrent.py mix result_mix result || exit 1

# 再開の継続: 通し計算(save_all / result)と分割(save_rt / result_rt2)
for f in save_all/state.dat:save_rt/state.dat save_all/swflow_enc.dat:save_rt/swflow_enc.dat \
         save_all/wavefield.dat:save_rt/wavefield.dat \
         result/E9998.bil:result_rt2/E9998.bil result/v9998.bil:result_rt2/v9998.bil \
         result/Wr9998.bil:result_rt2/Wr9998.bil; do
    a=${f%%:*}; b=${f##*:}
    cmp -s "$a" "$b" || { echo "ERROR: restart continuation differs from the straight run: $b" >&2; exit 1; }
    echo "  ok   restart continuation matches the straight run: $b"
done

rm -rf result_bad
if ./encflow param_bad.txt > Screen_bad.log 2>&1; then
    echo "ERROR: param_bad should stop (wf_flow = 3)" >&2; exit 1
fi
grep -q "wf_flow must be 0" Screen_bad.log \
    || { echo "ERROR: param_bad stopped for another reason" >&2; exit 1; }
echo "  ok   wf_flow = 3 stops"

echo "=== wfcurrent verification PASS ==="
