#!/bin/bash
# sfzone: 逐次実行 + 回帰テスト + 解析検定(貯留関数法の区画・タンク・出口。developer.md §106)
#   ./Run.sh [-u]
# param.txt は reference 比較(Log.txt、ULP=0)と Check_sfzone.py base。
# ほかは Check_sfzone.py の検定と停止の確認のみ(reference 非依存):
#   param_avg.txt         雨の分布 + 区画内面積平均(入力 = 面積 × 区画内平均雨量、収支)
#   param_strictfail.txt  同じ雨で厳密モード → 区画内の雨量の不一致で停止すること
#   param_save.txt / param_restart.txt  6 h で保存 → 再開(連続計算とビット一致)
#   param_bflow.txt       区画の基底流(解析積分、タンク側の不変、出口・Log の収支)。
#                         sed で保存 → 再開(累積の基底流の引き継ぎ)も確かめる
#   param_dflt.txt        既定値の表示と、同じ値を明示した param.txt とのビット一致。
#                         sed で K を消した構成が停止することも確かめる
#   param_sync.txt        同期間隔 dt_sfm = 60 s(参照解との一致・収支)。sed で同期区間の
#                         途中(21625 s)で保存 → 再開も確かめる
#   param_steady.txt      一定の雨 48 h で q → r、S = K·r^P
#   param_lag.txt         遅れ時間(遅らせた雨に対する厳密解・参照解、移動中の水 vlag、収支)。
#                         sed で保存 → 再開、同期間隔 60 s(同期区間の途中の保存 → 再開を含む)も確かめる
#   param_et.txt          蒸発散をタンクから引く(ステップごとの参照解・収支。sed で保存 → 再開)。
#   param_et_steady.txt   蒸発散ありの定常(q → r − E、線形低減の区画は r = q + E·S/S_lim の解)
#   param_mosaic.txt      VZ との併用(貯留関数の区画と受水セルが param.txt と一致、全体の収支)。
#                         sed で区画の重なり・出口が VZ のセルにある構成・P > 1 の停止も確かめる
# reference 比較は Log.txt(ULP=0)。sfm_zone.csv は 16 桁で書くため CPU(-march=native の
# ベクトル化)が違うと最終桁が変わりうる(test/vzcol と同じ理由)。CSV の内容は
# Check_sfzone.py の解析検定で確かめる。
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export SKIPCOLS=6      # 検査対象外とする列番号(Log の Runge 列)
export FILES=${FILES:-Log.txt}
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

python3 Check_sfzone.py base result || exit 1

run() {   # run <タグ> <設定ファイル>: 実行(失敗したら終了)
    rm -rf "result_$1"
    ./encflow "$2" > "Screen_$1.log" 2>&1 || { echo "ERROR: $2 run failed" >&2; exit 1; }
}
expect_stop() {   # expect_stop <タグ> <設定ファイル> <停止の文言>
    rm -rf "result_$1"
    if ./encflow "$2" > "Screen_$1.log" 2>&1; then
        echo "ERROR: $1 should stop ($3)" >&2; exit 1
    fi
    grep -q -- "$3" "Screen_$1.log" || { echo "ERROR: $1 stopped for another reason" >&2; exit 1; }
    echo "  ok   $1 stops: $3"
}
variant() {   # variant <元の設定> <dir_result> <追加の sed 式> > 出力
    sed -e "s/^  dir_result = '[a-z_]*'/  dir_result = '$2'/" -e "$3" "$1"
}
tmp=$(mktemp -p .)
trap 'rm -f "$tmp"' EXIT

run avg param_avg.txt
python3 Check_sfzone.py avg result_avg || exit 1
expect_stop strictfail param_strictfail.txt "rainfall differs within zone"

rm -rf result_save result_restart save
run save param_save.txt
run restart param_restart.txt
python3 Check_sfzone.py restart result result_restart || exit 1

# 区画の基底流と、その保存 → 再開
rm -rf save_bflow
run bflow param_bflow.txt
python3 Check_sfzone.py bflow result result_bflow || exit 1
variant param_bflow.txt result_bflow_save "s/^  tt = 43200 /  tt = 21600 /;s/f_state_save = 0 /f_state_save = 1 /" > "$tmp"
run bflow_save "$tmp"
variant param_bflow.txt result_bflow_restart "s/f_state_restore = 0 /f_state_restore = 1 /" > "$tmp"
run bflow_restart "$tmp"
python3 Check_sfzone.py restart result_bflow result_bflow_restart || exit 1

# 既定値と K の必須
run dflt param_dflt.txt
python3 Check_sfzone.py dflt result result_dflt Screen_dflt.log || exit 1
variant param.txt result_nok "s/^  sfm_k(2) = 2.0, /  /" > "$tmp"
expect_stop nok "$tmp" "sfm_k(2) must be given"

# 同期間隔と、同期区間の途中での保存 → 再開
run sync param_sync.txt
python3 Check_sfzone.py sync result result_sync || exit 1
rm -rf save_psync
variant param_sync.txt result_psync_save \
    "s/^  tt = 43200 .*/  tt = 21625/;s|^  dir_result = 'result_psync_save'|&\n  dir_save = 'save_psync'\n  f_state_save = 1|" > "$tmp"
run psync_save "$tmp"
grep -q "sfm: syncing the partial interval of 5 steps before saving" Screen_psync_save.log \
    || { echo "ERROR: the partial interval was not synchronised before saving" >&2; exit 1; }
variant param_sync.txt result_psync_restart \
    "s|^  dir_result = 'result_psync_restart'|&\n  dir_save = 'save_psync'\n  f_state_restore = 1|" > "$tmp"
run psync_restart "$tmp"
python3 Check_sfzone.py partial result_sync result_psync_restart || exit 1

# 遅れ時間(param_lag.txt)と、その保存 → 再開、同期間隔 60 s(同期区間の途中の保存 → 再開を含む)
rm -rf save_lag save_lagsync
run lag param_lag.txt
python3 Check_sfzone.py lag result result_lag || exit 1
variant param_lag.txt result_lag_save "s/^  tt = 43200 /  tt = 21600 /;s/f_state_save = 0 /f_state_save = 1 /" > "$tmp"
run lag_save "$tmp"
variant param_lag.txt result_lag_restart "s/f_state_restore = 0 /f_state_restore = 1 /" > "$tmp"
run lag_restart "$tmp"
python3 Check_sfzone.py restart result_lag result_lag_restart || exit 1
lagsync="s|^  fn_sfm_zone = 'zone.txt'|&\n  dt_sfm = 60.0|;s/'save_lag'/'save_lagsync'/"
variant param_lag.txt result_lag_sync "$lagsync" > "$tmp"
run lag_sync "$tmp"
python3 Check_sfzone.py lag result result_lag_sync 1e-4 || exit 1
variant param_lag.txt result_lag_psave "$lagsync;s/^  tt = 43200 .*/  tt = 21625/;s/f_state_save = 0 /f_state_save = 1 /" > "$tmp"
run lag_psave "$tmp"
variant param_lag.txt result_lag_prestart "$lagsync;s/f_state_restore = 0 /f_state_restore = 1 /" > "$tmp"
run lag_prestart "$tmp"
python3 Check_sfzone.py partial result_lag_sync result_lag_prestart || exit 1

# 蒸発散をタンクから引く(param_et.txt)と、その保存 → 再開、蒸発散ありの定常
rm -rf save_et
run et param_et.txt
python3 Check_sfzone.py et result_et || exit 1
variant param_et.txt result_et_save "s/^  tt = 43200 /  tt = 21600 /;s/f_state_save = 0 /f_state_save = 1 /" > "$tmp"
run et_save "$tmp"
variant param_et.txt result_et_restart "s/f_state_restore = 0 /f_state_restore = 1 /" > "$tmp"
run et_restart "$tmp"
python3 Check_sfzone.py restart result_et result_et_restart || exit 1
run et_steady param_et_steady.txt
python3 Check_sfzone.py et_steady result_et_steady || exit 1

run steady param_steady.txt
python3 Check_sfzone.py steady result_steady || exit 1

# VZ との併用と、併用できない構成の停止
run mosaic param_mosaic.txt
python3 Check_sfzone.py mosaic result result_mosaic || exit 1
variant param_mosaic.txt result_overlap "s/'vzzone_mosaic.txt'/'vzzone_overlap.txt'/" > "$tmp"
expect_stop overlap "$tmp" "a cell belongs to both a VZ zone and a SFM zone"
variant param_mosaic.txt result_outvz "s/^  sfm_out_cell(:,1,2) = 7, 1 /  sfm_out_cell(:,1,2) = 3, 7 /" > "$tmp"
expect_stop outvz "$tmp" "list_sfm_zone: an outlet cell is a VZ cell"
variant param.txt result_pbig "s/sfm_p(3) = 0.4/sfm_p(3) = 1.5/" > "$tmp"
expect_stop pbig "$tmp" "sfm_p(3) must satisfy 0 < P <= 1"

echo "=== sfzone verification PASS ==="
