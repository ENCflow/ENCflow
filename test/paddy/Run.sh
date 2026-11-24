#!/bin/bash
# paddy: 逐次実行 + 回帰テスト + 解析検定(田んぼダムのサブグリッドの水田タンク fn_paddy。developer.md §119)
#   ./Run.sh [-u]
# param.txt は reference 比較(Log.txt、ULP=0)と Check_paddy.py weir。
# ほかは Check_paddy.py の検定と停止の確認のみ(reference 非依存):
#   param_open.txt    三角の切欠き(厳密解)と円の穴(参照解)の落水
#   param_sep.txt     長方形の穴と機能分離型(min の切り替えと流出量調整板の越流)
#   param_steady.txt  一定の雨の平衡と満水の越流。sed で 6 h で保存 → 再開(連続計算とビット一致)
#   param_spill.txt   強い雨で畦畔まで満ちる越流
#   param_mix.txt     面積率・取組率・空隙率の分布と閉じた領域の水の保存(sed で作る水田なしの計算と比べる)
#   param_dflt.txt    既定値の採用と表示、同じ値を明示した構成(sed で作る)とのビット一致
#   param_wash.txt    雨滴侵食(f_wash の雨滴の項)に 1 − 面積率が掛かること(§119.5)
#   param_splash.txt  乾いた斜面の侵食(f_splash)に 1 − 面積率が掛かること(§119.5)
#   停止の確認: 河道セル・面積率 > 空隙率・取組率の範囲・水質との併用・型 0 の流出量調整板・
#   面積率の二重指定・事前の湛水深 > 畦畔高・保存ファイルが残ったまま無効で再開
# reference 比較は Log.txt(ULP=0)。paddy.csv は 16 桁で書くため CPU(-march=native のベクトル化)が
# 違うと最終桁が変わりうる(test/vzcol・sfzone と同じ理由)。CSV の内容は Check_paddy.py で確かめる。
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export SKIPCOLS=4      # 検査対象外とする列番号(Log の Runge 列。S(m) の 1 列形式)
export FILES=${FILES:-Log.txt}
"$sdir/../Scripts/Run_case.sh" serial "$@" || exit 1

python3 Check_paddy.py weir result || exit 1

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
    sed -e "s/^  dir_result = '[a-z_0-9]*'/  dir_result = '$2'/" -e "$3" "$1"
}
tmp=$(mktemp -p .)
trap 'rm -f "$tmp"' EXIT

run open param_open.txt
python3 Check_paddy.py open result_open || exit 1
run sep param_sep.txt
python3 Check_paddy.py sep result_sep || exit 1
run steady param_steady.txt
python3 Check_paddy.py steady result_steady || exit 1
run spill param_spill.txt
python3 Check_paddy.py spill result_spill || exit 1

# 閉じた領域の水の保存: 水田なしの同じ計算(fn_paddy を消す)と比べる
run mix param_mix.txt
variant param_mix.txt result_mix_nopd "/^  fn_paddy = /d" > "$tmp"
run mix_nopd "$tmp"
python3 Check_paddy.py mix result_mix result_mix_nopd || exit 1

# 既定値と、同じ値を明示した構成とのビット一致
run dflt param_dflt.txt
python3 Check_paddy.py dflt result_dflt Screen_dflt.log || exit 1
variant param_dflt.txt result_dflt_explicit "s/^  pd_frac = 1.0$/  pd_frac = 1.0\n  pd_adopt = 0.0\n  pd_aplot = 3000.0\n  pd_hlev = 0.30\n  pd_h0 = 0.03\n  pd_perc_mmd = 5.0\n  pd_dev_type(1) = 0\n  pd_board_h(1) = 0.03\n  pd_board_w(1) = 0.30\n  pd_cw(1) = 0.6/" > "$tmp"
run dflt_explicit "$tmp"
for f in paddy.csv Log.txt; do
    cmp -s "result_dflt/$f" "result_dflt_explicit/$f" || { echo "ERROR: result_dflt_explicit/$f differs from the defaults" >&2; exit 1; }
done
echo "  ok   the defaults are bit-identical to the same values given explicitly"

# 雨滴侵食から水田の部分を外す(地形変化との併用。§119.5)
run wash param_wash.txt
python3 Check_paddy.py wash result_wash || exit 1
run splash param_splash.txt
python3 Check_paddy.py splash result_splash || exit 1

# 保存 → 再開(6 h で保存し 12 h まで)と、連続計算(12 h)のビット一致
rm -rf save_rs
variant param_steady.txt result_rs_cont "s/^  tt = 172800$/  tt = 43200/" > "$tmp"
run rs_cont "$tmp"
variant param_steady.txt result_rs_save "s/^  tt = 172800$/  tt = 21600/;s|^  dir_result = 'result_rs_save'|&\n  dir_save = 'save_rs'\n  f_state_save = 1|" > "$tmp"
run rs_save "$tmp"
variant param_steady.txt result_rs_restart "s/^  tt = 172800$/  tt = 43200/;s|^  dir_result = 'result_rs_restart'|&\n  dir_save = 'save_rs'\n  f_state_restore = 1|" > "$tmp"
run rs_restart "$tmp"
python3 Check_paddy.py restart result_rs_cont result_rs_restart || exit 1
variant param_steady.txt result_orphan "s/^  tt = 172800$/  tt = 43200/;/^  fn_paddy = /d;s|^  dir_result = 'result_orphan'|&\n  dir_save = 'save_rs'\n  f_state_restore = 1|" > "$tmp"
expect_stop orphan "$tmp" "paddy.dat exists in"

# 停止の確認
variant param.txt result_rw "s|^  f_masktype = 0|&\n  fn_rw = 'rw_one.txt'|" > "$tmp"
expect_stop rw "$tmp" "a paddy cell is on a channel cell (rw)"
variant param_mix.txt result_overgv "s/'frac_mix.txt'/'frac_over_gv.txt'/" > "$tmp"
expect_stop overgv "$tmp" "exceeds the void ratio gv"
variant param_mix.txt result_adoptbad "s/'adopt_mix.txt'/'adopt_bad.txt'/" > "$tmp"
expect_stop adoptbad "$tmp" "the adoption ratio must satisfy 0 <= r <= 1"
variant param.txt result_wq "s|^  fn_paddy = '-'|&\n  fn_wq = '-'|" > "$tmp"
printf "\n&list_wq\n/\n" >> "$tmp"          # 水質の初期化を通る最小の入力(空のグループ)
expect_stop wq "$tmp" "fn_paddy cannot be combined with fn_wq"
variant param.txt result_plate0 "s|^  pd_cw(1) = 0.6|&\n  pd_plate_h(1) = 0.2|" > "$tmp"
expect_stop plate0 "$tmp" "are for the separated type"
variant param_mix.txt result_twofrac "s|^  fn_pd_frac = 'frac_mix.txt'|&\n  pd_frac = 0.5|" > "$tmp"
expect_stop twofrac "$tmp" "specify only one of fn_pd_frac and pd_frac"
variant param.txt result_h0big "s/^  pd_h0 = 0.25 /  pd_h0 = 0.35 /" > "$tmp"
expect_stop h0big "$tmp" "pd_h0 must satisfy 0 <= pd_h0 <= pd_hlev"

echo "=== paddy verification PASS ==="
