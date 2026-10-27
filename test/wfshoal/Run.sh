#!/bin/bash
# wfshoal: 逐次実行 + 回帰テスト + 解析検定(沿岸の波浪場 fn_wavefield。developer.md §88)
#   ./Run.sh [-u]
# param.txt(沖の波の時系列・斜め入射の不規則波)は reference 比較(Log.txt・
# wavefield.csv・Wh0001.txt、ULP=0)と Check_wfshoal.py base。
# param_shoal(浅水変形と飽和砕波)・param_refr / param_refr80(屈折と方向ビンの収束)・
# param_brk / param_brkjb(砕波・摩擦)・param_unst(非定常)は Check_wfshoal.py の
# 検定のみ(reference 非依存)。param_rt1 → param_rt2 の再開の継続が通し計算
# (param_unst)と wavefield.dat・state.dat・Wh9998 でバイト一致すること、
# param_nowf(波浪場なし)の Log.txt が基本とバイト一致すること(段 W1 は流れに
# 作用しない)、param_bad(wf_ntheta が 8 の倍数でない)が停止することを確かめる
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列)
export FILES=${FILES:-"Log.txt wavefield.csv Wh0001.txt"}
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

python3 Check_wfshoal.py base result || exit 1

for tag in shoal refr refr80 brk brkjb unst nowf; do
    rm -rf result_$tag
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag run failed" >&2; exit 1; }
done
rm -rf result_rt1 result_rt2 save_rt
./encflow param_rt1.txt > Screen_rt1.log 2>&1 || { echo "ERROR: param_rt1 run failed" >&2; exit 1; }
./encflow param_rt2.txt > Screen_rt2.log 2>&1 || { echo "ERROR: param_rt2 run failed" >&2; exit 1; }

python3 Check_wfshoal.py shoal result_shoal || exit 1
python3 Check_wfshoal.py refr result_refr result_refr80 || exit 1
python3 Check_wfshoal.py brk result_brk || exit 1
python3 Check_wfshoal.py brkjb result_brkjb || exit 1
python3 Check_wfshoal.py unst result_unst result_brk || exit 1
python3 Check_wfshoal.py rt result_unst result_rt2 || exit 1

# 再開の継続: 通し計算(save_all / result_unst)と分割(save_rt / result_rt2)
for f in save_all/wavefield.dat:save_rt/wavefield.dat save_all/state.dat:save_rt/state.dat \
         result_unst/Wh9998.bil:result_rt2/Wh9998.bil; do
    a=${f%%:*}; b=${f##*:}
    cmp -s "$a" "$b" || { echo "ERROR: restart continuation differs from the straight run: $b" >&2; exit 1; }
    echo "  ok   restart continuation matches the straight run: $b"
done

# 段 W1 の波浪場は流れに作用しない: 波浪場なしと Log.txt がバイト一致
cmp -s result/Log.txt result_nowf/Log.txt \
    || { echo "ERROR: Log.txt differs from the run without the wave field" >&2; exit 1; }
echo "  ok   the flow (Log.txt) is identical to the run without the wave field"

rm -rf result_bad
if ./encflow param_bad.txt > Screen_bad.log 2>&1; then
    echo "ERROR: param_bad should stop (wf_ntheta is not a multiple of 8)" >&2; exit 1
fi
grep -q "wf_ntheta must be a multiple of 8" Screen_bad.log \
    || { echo "ERROR: param_bad stopped for another reason" >&2; exit 1; }
echo "  ok   wf_ntheta that is not a multiple of 8 stops"

echo "=== wfshoal verification PASS ==="
