#!/bin/bash
# vzzone: 逐次実行 + 回帰テスト + 解析検定(VZ 区画・共有柱・出口。developer.md §87)
#   ./Run.sh [-u]
# param.txt は reference 比較(Log.txt、ULP=0)と
# Check_vzzone.py base。ほかは Check_vzzone.py の検定のみ(reference 非依存):
#   param_dup.txt         柱を共有 vs 複製(区画の応答がビット一致)
#   param_avg.txt         雨の分布 + 柱内面積平均(入力 = 面積 × 柱内平均雨量、収支)
#   param_strictfail.txt  同じ雨で厳密モード → 柱内の雨量の不一致で停止すること
#   param_save.txt / param_restart.txt  6 h で保存 → 再開(連続計算とビット一致)
#   param_bflow.txt       区画の基底流(解析積分、VZ 側の不変、出口・Log の収支)。
#                         tt・dir_result・f_state_save・f_state_restore を sed で書き換えて
#                         保存 → 再開と、時刻が減る時系列での停止も確かめる
# reference 比較は Log.txt(ULP=0)。vz_zone.csv・vz_column.csv は 16 桁で書くため
# CPU(-march=native のベクトル化)が違うと最終桁が変わり(Zen3 向けビルドで確認)、
# 他ホストの CI では ULP=0 が成立しない。CSV の内容は Check_*.py の解析検定で
# 確かめる。同じホストで作った reference と CSV もビット比較したいときは
#   FILES="Log.txt vz_zone.csv vz_column.csv" ./Run.sh
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export SKIPCOLS=6      # 検査対象外とする列番号(Log の Runge 列)
export FILES=${FILES:-Log.txt}
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

python3 Check_vzzone.py base result || exit 1

for tag in dup avg; do
    rm -rf result_$tag
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 || { echo "ERROR: param_$tag run failed" >&2; exit 1; }
done
python3 Check_vzzone.py dup result result_dup || exit 1
python3 Check_vzzone.py avg result_avg || exit 1

rm -rf result_strictfail
if ./encflow param_strictfail.txt > Screen_strictfail.log 2>&1; then
    echo "ERROR: param_strictfail should stop (rainfall differs within a column)" >&2; exit 1
fi
grep -q "rainfall differs within column" Screen_strictfail.log \
    || { echo "ERROR: param_strictfail stopped for another reason" >&2; exit 1; }
echo "  ok   strict mode stops when rainfall differs within a column"

rm -rf result_save result_restart save
./encflow param_save.txt > Screen_save.log 2>&1 || { echo "ERROR: param_save run failed" >&2; exit 1; }
./encflow param_restart.txt > Screen_restart.log 2>&1 || { echo "ERROR: param_restart run failed" >&2; exit 1; }
python3 Check_vzzone.py restart result result_restart || exit 1

# 区画の基底流
bvariant() {   # bvariant <dir_result の接尾辞> <追加の sed 式> > 出力
    sed -e "s/dir_result = 'result_bflow'/dir_result = 'result_bflow$1'/" -e "$2" param_bflow.txt
}
tmp=$(mktemp)
rm -rf result_bflow result_bflow_save result_bflow_restart result_bflowbad save_bflow
./encflow param_bflow.txt > Screen_bflow.log 2>&1 || { echo "ERROR: param_bflow run failed" >&2; exit 1; }
python3 Check_vzzone.py bflow result result_bflow || exit 1
python3 Check_vzzone.py base result_bflow || exit 1
bvariant _save "s/^  tt = 43200 /  tt = 21600 /;s/f_state_save = 0 /f_state_save = 1 /" > "$tmp"
./encflow "$tmp" > Screen_bflow_save.log 2>&1 || { echo "ERROR: param_bflow (save) run failed" >&2; exit 1; }
bvariant _restart "s/f_state_restore = 0 /f_state_restore = 1 /" > "$tmp"
./encflow "$tmp" > Screen_bflow_restart.log 2>&1 || { echo "ERROR: param_bflow (restart) run failed" >&2; exit 1; }
python3 Check_vzzone.py restart result_bflow result_bflow_restart || exit 1
bvariant bad "s/vz_base(:,4,1) = 300.25, 1.0/vz_base(:,4,1) = 20.0, 1.0/" > "$tmp"
if ./encflow "$tmp" > Screen_bflowbad.log 2>&1; then
    rm -f "$tmp"; echo "ERROR: decreasing baseflow times should stop" >&2; exit 1
fi
rm -f "$tmp"
grep -q "baseflow times of zone 1 must not decrease" Screen_bflowbad.log \
    || { echo "ERROR: the decreasing baseflow times stopped for another reason" >&2; exit 1; }
echo "  ok   decreasing baseflow times stop"

echo "=== vzzone verification PASS ==="
