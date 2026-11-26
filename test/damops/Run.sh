#!/bin/bash
# damops: 逐次実行 + 回帰テスト(ダムの運転則。developer.md §132)
#   ./Run.sh [-u]
# 回帰(Log.txt と 7 基のダム CSV)に加えて reference 非依存の検定を行う:
#   Check_damops.py rules : 運転則の式・時系列との一致、流入 = 1 歩前のソースの流量、
#                           閉じた系の体積保存(Log の S)
#   リスタート            : 165 分で保存して再開した継続が、通し計算とダム CSV・S で一致する
#   不正な設定            : モードと合わないパラメータなど 9 通りが起動時に止まる
# 派生の設定(wrk_param_*.txt)と保存(wrk_save_rt)は param.txt の文字列置換で毎回作る。
# reference 比較は ULP=1(印字の最終桁 1 つ分まで)。reference を作ったマシン(AVX-512 の
# Xeon)と CPU の違うマシンでは、-march=native の生成コードの差で Log.txt の S の最終桁が
# 変わり得る(test/damwq と同じ扱い。developer.md §10)。同じマシンでは環境変数で上書きして
# ビット比較できる:
#   ULP=0 ./Run.sh
sdir=$(dirname "$(readlink -f "$0")")
export FILES="Log.txt dams/dam0001.csv dams/dam0002.csv dams/dam0003.csv dams/dam0004.csv dams/dam0005.csv dams/dam0006.csv dams/dam0007.csv"
export ULP=${ULP:-1}   # 印字の最終桁 1 つ分まで(上の注)
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列)
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

echo "Check_damops rules: result"
python3 Check_damops.py rules result || exit 1

# param.txt の文字列置換で派生の設定を作る: variant <出力> <置換元> <置換先> [...]
variant() {
    python3 - "$@" << 'EOF'
import sys
out, pairs = sys.argv[1], sys.argv[2:]
p = open("param.txt").read()
for a, b in zip(pairs[::2], pairs[1::2]):
    assert p.count(a) == 1, "not found exactly once in param.txt: " + a
    p = p.replace(a, b)
open(out, "w").write(p)
EOF
}

# リスタート: 165 分で保存 → 再開して 330 分まで
echo "restart continuation (save at 165 min, restore, continue to 330 min)"
rm -rf result_rt1 result_rt2 wrk_save_rt
variant wrk_param_rt1.txt "  tt = 19800" "  tt = 9900" \
    "dir_result = 'result'" "dir_result = 'result_rt1'" \
    "  f_check_cfl = 1" "  f_check_cfl = 1
  f_state_save = 1
  dir_save = 'wrk_save_rt'" || exit 1
variant wrk_param_rt2.txt "dir_result = 'result'" "dir_result = 'result_rt2'" \
    "  f_check_cfl = 1" "  f_check_cfl = 1
  f_state_restore = 1
  dir_save = 'wrk_save_rt'" || exit 1
./encflow wrk_param_rt1.txt > Screen_rt1.log 2>&1 || { echo "ERROR: wrk_param_rt1 run failed" >&2; exit 1; }
./encflow wrk_param_rt2.txt > Screen_rt2.log 2>&1 || { echo "ERROR: wrk_param_rt2 run failed" >&2; exit 1; }
python3 Check_damops.py restart result result_rt2 165 || exit 1

# 不正な設定(起動時に止まること)
stop_check() {   # stop_check <置き換える行> <期待するメッセージ>
    rm -rf result_bad
    variant wrk_param_bad.txt "dir_result = 'result'" "dir_result = 'result_bad'" \
        "  ! @BAD@" "$1" || exit 1
    if ./encflow wrk_param_bad.txt > Screen_bad.log 2>&1; then
        echo "ERROR: [$1] should stop" >&2; exit 1
    fi
    grep -q "$2" Screen_bad.log || { echo "ERROR: [$1] stopped for another reason" >&2; exit 1; }
    echo "  ok   stops: $2"
}
echo "invalid settings stop at start-up"
stop_check "  dam_qon(1) = 0.5" "dam_qon of dam 1 applies to f_dam_mode=2"
stop_check "  dam_hlim(3) = 101.0" "dam_hlim of dam 3 applies to f_dam_mode=1 or 2"
stop_check "  dam_qout_val(:,1,1) = 0, 0.5" "dam_qout_val / fn_dam_qout_val of dam 1 requires f_dam_mode=4"
stop_check "  dam_qmax(2) = 0.5" "dam_qmax of dam 2 (the maximum release) must be >= dam_qon"
stop_check "  dam_qout_val(:,4,3) = 20, 0.6" "times of dam_qout_val of dam 3 must not decrease"
stop_check "  dam_tadashigaki(3) = 110.0" "dam_tadashigaki of dam 3 does not apply to f_dam_mode=4 or 5"
stop_check "  dam_hlim(1) = 111.0" "must be below the emergency-release start level"
stop_check "  fn_dam_h_val(4) = ''
  dam_h_val(:,1,4) = 0, 99.0" "water-level time series of dam 4 must lie between the minimum and surcharge levels"
stop_check "  dam_lake(8) = 4
  dam_out_cell(:,1,8) = 18, 8
  f_dam_mode(8) = 4
  dam_qout_val(:,1,8) = 0, 0.1" "cannot reference lake 4 operated by a water-level time series"
rm -rf result_bad

echo "=== damops verification PASS ==="
