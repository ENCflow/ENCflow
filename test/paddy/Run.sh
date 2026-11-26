#!/bin/bash
# paddy: 逐次実行 + 回帰テスト + 解析検定(田んぼダムのサブグリッドの水田タンク fn_paddy。developer.md §127)
#   ./Run.sh [-u]
# param.txt は reference 比較(Log.txt、ULP=0)と Check_paddy.py weir。
# ほかは Check_paddy.py の検定と停止の確認のみ(reference 非依存):
#   param_open.txt    三角の切欠き(厳密解)と円の穴(参照解)の落水
#   param_sep.txt     長方形の穴と機能分離型(min の切り替えと流出量調整板の越流)
#   param_steady.txt  一定の雨の平衡と満水の越流。sed で 6 h で保存 → 再開(連続計算とビット一致)
#   param_spill.txt   強い雨で畦畔まで満ちる越流
#   param_mix.txt     面積率・取組率・空隙率の分布と閉じた領域の水の保存(sed で作る水田なしの計算と比べる)
#   param_dflt.txt    既定値の採用と表示、同じ値を明示した構成(sed で作る)とのビット一致
#   param_wash.txt    雨滴侵食(f_wash の雨滴の項)に 1 − 面積率が掛かること(§127.5)
#   param_splash.txt  乾いた斜面の侵食(f_splash)に 1 − 面積率が掛かること(§127.5)
#   param_tw_*.txt    双方向(二室化。f_pd_exchange = 1。§127.6): 落水口からの逆流(参照解)、畦畔を越える浸水での
#                     瞬時の満水と二重計上がないこと、外水の流入での水の保存、浸水が引いた後の落水。tw_drain は sed で
#                     6 h で保存 → 再開(連続計算とビット一致)
#   param_b_*.txt     区画の解像(表現 B。fn_pd_plot。§127.8。入力は make_plots.py が作る): 1 区画の落水(堰の厳密解・
#                     穴の参照解)、畦畔・市松の角の水密、畦畔の越流と閉じた領域の水の保存、落水口からの逆流、畦畔を
#                     越える外からの流入、畦畔と河川堤防が重なるエッジ、区画から区画への落水口(田越し)。b_back は sed で
#                     6 h で保存 → 再開(連続計算とビット一致)
#   param_wq_*.txt    水質(fn_wq。§127.10): タンクの濃度の一次減衰(厳密解)、雨の物質、双方向の逆流で入る水の
#                     濃度、区画の解像の減水深の持ち出し(wq.csv の質量の収支)。wq_a は sed で 6 h で保存 → 再開
#   param_sed_tw.txt  土砂(§127.11): 双方向のタンクへ入る水の浮遊砂を田面に積む(固相の保存)。地形変化の刻み 7 s
#                     で 1 h で保存 → 再開
#   param_b_sed.txt   土砂: 区画の解像で掃流砂が畦畔を越えない(区画ごとの河床の変化の合計 0)
#   param_catch.txt   集水面積率(fn_pd_catch。§127.13): 閉じた箱の雨だけの厳密解(片方向と、sed で双方向)。
#                     集水面積率 0 の分布を与えた計算と与えない計算のビット一致(steady・tw_drain の変形)、
#                     集水面積の雨の物質がタンクへ入ること(wq_rain の変形)
#   param_catch_sp.txt 集水面積の雨を 3 × 3 の近傍の水田へ配る(§127.15): 面積率・取組率・集水面積率が場所で違う
#                     閉じた箱のセルごとのタンクの水深と種類ごとの濃度の厳密解(片方向と、sed で双方向)
#   停止の確認: 河道セル・面積率 > 空隙率・取組率の範囲・型 0 の流出量調整板・
#   面積率の二重指定・事前の湛水深 > 畦畔高・保存ファイルが残ったまま無効で再開、双方向の水田でない面積の割合
#   < 0.01・ため池のセル・土石流・非静水圧との併用・保存時とやり取りの方式が違う再開・保存時と水質の有無が違う
#   再開・保存時と浮遊砂の有無が違う双方向の再開、集水面積率の範囲・水田のないセルの集水面積・面積率 + 集水面積率
#   > 空隙率・雨滴侵食との併用、B の入力の誤り(外周の
#   区画のセル・同じ区画や区画でないセルの落水口・区画の中で違う種類・整数でない区画番号・天端より高い先・
#   向かい合う落水口)と A だけの入力(集水面積率を含む)との併用、B と非静水圧、保存時と表現が違う再開、
#   B と掃流砂の写しの手続き(混合粒径 f_bedmix・有効掃流力 f_taupart = 2)、双方向・浮遊砂と混合粒径
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
variant param_dflt.txt result_dflt_explicit "s/^  pd_frac = 1.0$/  pd_frac = 1.0\n  f_pd_exchange = 0\n  pd_adopt = 0.0\n  pd_aplot = 3000.0\n  pd_hlev = 0.30\n  pd_h0 = 0.03\n  pd_perc_mmd = 5.0\n  pd_dev_type(1) = 0\n  pd_board_h(1) = 0.03\n  pd_board_w(1) = 0.30\n  pd_cw(1) = 0.6/" > "$tmp"
run dflt_explicit "$tmp"
for f in paddy.csv Log.txt; do
    cmp -s "result_dflt/$f" "result_dflt_explicit/$f" || { echo "ERROR: result_dflt_explicit/$f differs from the defaults" >&2; exit 1; }
done
echo "  ok   the defaults are bit-identical to the same values given explicitly"

# 雨滴侵食から水田の部分を外す(地形変化との併用。§127.5)
run wash param_wash.txt
python3 Check_paddy.py wash result_wash || exit 1
run splash param_splash.txt
python3 Check_paddy.py splash result_splash || exit 1

# 双方向(二室化。§127.6)
for t in tw_back tw_fill tw_flood tw_drain; do
    run $t param_$t.txt
    python3 Check_paddy.py $t result_$t || exit 1
done
# 双方向の保存 → 再開(6 h で保存し 12 h まで)と連続計算(tw_drain の 12 h)のビット一致
rm -rf save_tw
variant param_tw_drain.txt result_tw_save "s/^  tt = 43200$/  tt = 21600/;s|^  dir_result = 'result_tw_save'|&\n  dir_save = 'save_tw'\n  f_state_save = 1|" > "$tmp"
run tw_save "$tmp"
variant param_tw_drain.txt result_tw_restart "s|^  dir_result = 'result_tw_restart'|&\n  dir_save = 'save_tw'\n  f_state_restore = 1|" > "$tmp"
run tw_restart "$tmp"
python3 Check_paddy.py restart result_tw_drain result_tw_restart || exit 1
variant param_tw_drain.txt result_tw_mode "s|^  dir_result = 'result_tw_mode'|&\n  dir_save = 'save_tw'\n  f_state_restore = 1|;s|^  f_pd_exchange = 1 .*|  f_pd_exchange = 0|" > "$tmp"
expect_stop tw_mode "$tmp" "f_pd_exchange differs from the saved state"

# 区画の解像(表現 B。§127.8)
python3 make_plots.py data_paddy || exit 1
for t in b_drain b_tight b_over b_back b_ext b_bank b_chain; do
    run $t param_$t.txt
    python3 Check_paddy.py $t result_$t || exit 1
done
# B の保存 → 再開(6 h で保存し 12 h まで)と連続計算(b_back の 12 h)のビット一致。表現が違う再開は停止
rm -rf save_b
variant param_b_back.txt result_b_save "s/^  tt = 43200$/  tt = 21600/;s|^  dir_result = 'result_b_save'|&\n  dir_save = 'save_b'\n  f_state_save = 1|" > "$tmp"
run b_save "$tmp"
variant param_b_back.txt result_b_restart "s|^  dir_result = 'result_b_restart'|&\n  dir_save = 'save_b'\n  f_state_restore = 1|" > "$tmp"
run b_restart "$tmp"
python3 Check_paddy.py restart_b result_b_back result_b_restart || exit 1
variant param_b_back.txt result_b_mode "s|^  dir_result = 'result_b_mode'|&\n  dir_save = 'save_b'\n  f_state_restore = 1|;s|^  fn_pd_plot = .*|  pd_frac = 0.5|;/^  fn_pd_outlet = /d" > "$tmp"
expect_stop b_mode "$tmp" "the representation of the paddy fields differs from the saved state"

# 水質(fn_wq。§127.10): タンクのプール(A の片方向・双方向)と区画の解像(B)の減水深の持ち出し
for t in wq_a wq_rain wq_tw wq_b; do
    run $t param_$t.txt
    python3 Check_paddy.py $t result_$t || exit 1
done
# 水質のプールの保存 → 再開(6 h で保存し 12 h まで)と連続計算(wq_a の 12 h)の一致。水質を外した再開は停止
rm -rf save_wq
variant param_wq_a.txt result_wq_save "s/^  tt = 43200$/  tt = 21600/;s|^  dir_result = 'result_wq_save'|&\n  dir_save = 'save_wq'\n  f_state_save = 1|" > "$tmp"
run wq_save "$tmp"
variant param_wq_a.txt result_wq_restart "s|^  dir_result = 'result_wq_restart'|&\n  dir_save = 'save_wq'\n  f_state_restore = 1|" > "$tmp"
run wq_restart "$tmp"
python3 Check_paddy.py restart_wq result_wq_a result_wq_restart || exit 1
variant param.txt result_wq_mode "s|^  dir_result = 'result_wq_mode'|&\n  dir_save = 'save_wq'\n  f_state_restore = 1|;s/^  pd_perc_mmd = 0.0 .*/  pd_perc_mmd = 5.0/" > "$tmp"
expect_stop wq_mode "$tmp" "water quality (fn_wq) differs from the saved state"

# 土砂(§127.11): 双方向のタンクへ入る水の浮遊砂を田面に積む、区画の解像の掃流砂は畦畔を越えない
for t in sed_tw b_sed; do
    run $t param_$t.txt
    python3 Check_paddy.py $t result_$t || exit 1
done
# 堆積の記録の保存 → 再開: 地形変化の刻みを 7 s にして(保存の時刻 1 h は刻みの途中)、連続計算とビット一致。
# 浮遊砂を外した再開は停止
rm -rf save_sed
variant param_sed_tw.txt result_sed_cont "s/^  dt_geomorph = 0.0/  dt_geomorph = 7.0/" > "$tmp"
run sed_cont "$tmp"
variant param_sed_tw.txt result_sed_save "s/^  dt_geomorph = 0.0/  dt_geomorph = 7.0/;s/^  tt = 7200$/  tt = 3600/;s|^  dir_result = 'result_sed_save'|&\n  dir_save = 'save_sed'\n  f_state_save = 1|" > "$tmp"
run sed_save "$tmp"
variant param_sed_tw.txt result_sed_restart "s/^  dt_geomorph = 0.0/  dt_geomorph = 7.0/;s|^  dir_result = 'result_sed_restart'|&\n  dir_save = 'save_sed'\n  f_state_restore = 1|" > "$tmp"
run sed_restart "$tmp"
python3 Check_paddy.py restart_sed result_sed_cont result_sed_restart || exit 1
variant param_tw_flood.txt result_sed_mode "s|^  dir_result = 'result_sed_mode'|&\n  dir_save = 'save_sed'\n  f_state_restore = 1|" > "$tmp"
expect_stop sed_mode "$tmp" "suspended sediment (f_suspend) with f_pd_exchange=1 differs from the saved state"

# 集水面積率(fn_pd_catch。§127.13・§127.15): 閉じた箱の雨だけの厳密解(片方向・双方向)、集水面積率 0 の分布を与えた
# 計算と与えない計算のビット一致(片方向 steady・双方向 tw_drain)、集水面積の雨の物質もタンクへ入ること(雨の濃度へ
# 近づく)、近傍の水田へ配る雨のセルごとの厳密解(場所で違う面積率・取組率・集水面積率。片方向・双方向)
run catch param_catch.txt
python3 Check_paddy.py catch result_catch || exit 1
variant param_catch.txt result_catch_tw "s|^  pd_perc_mmd = 0.0|&\n  f_pd_exchange = 1|" > "$tmp"
run catch_tw "$tmp"
python3 Check_paddy.py catch_tw result_catch_tw || exit 1
variant param_steady.txt result_catch_zero "s|^  pd_adopt = 0.5|&\n  fn_pd_catch = 'catch_zero.txt'|" > "$tmp"
run catch_zero "$tmp"
python3 Check_paddy.py catch_zero result_steady result_catch_zero || exit 1
variant param_tw_drain.txt result_catch_zero_tw "s|^  f_pd_exchange = 1|  fn_pd_catch = 'catch_zero.txt'\n&|" > "$tmp"
run catch_zero_tw "$tmp"
python3 Check_paddy.py catch_zero result_tw_drain result_catch_zero_tw || exit 1
variant param_wq_rain.txt result_catch_wq "s/^  pd_frac = 1.0$/  pd_frac = 0.5\n  fn_pd_catch = 'catch_03.txt'/" > "$tmp"
run catch_wq "$tmp"
python3 Check_paddy.py wq_rain result_catch_wq || exit 1
run catch_sp param_catch_sp.txt
python3 Check_paddy.py catch_sp result_catch_sp || exit 1
variant param_catch_sp.txt result_catch_sp_tw "s|^  pd_perc_mmd = 0.0|&\n  f_pd_exchange = 1|" > "$tmp"
run catch_sp_tw "$tmp"
python3 Check_paddy.py catch_sp_tw result_catch_sp_tw || exit 1

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
variant param.txt result_plate0 "s|^  pd_cw(1) = 0.6|&\n  pd_plate_h(1) = 0.2|" > "$tmp"
expect_stop plate0 "$tmp" "are for the separated type"
variant param_mix.txt result_twofrac "s|^  fn_pd_frac = 'frac_mix.txt'|&\n  pd_frac = 0.5|" > "$tmp"
expect_stop twofrac "$tmp" "specify only one of fn_pd_frac and pd_frac"
variant param.txt result_h0big "s/^  pd_h0 = 0.25 /  pd_h0 = 0.35 /" > "$tmp"
expect_stop h0big "$tmp" "pd_h0 must satisfy 0 <= pd_h0 <= pd_hlev"
variant param_tw_flood.txt result_tw_smin "s/'frac_tw.txt'/'frac_mix.txt'/" > "$tmp"
expect_stop tw_smin "$tmp" "the non-paddy fraction 1 - a/gv of a paddy cell is below"
variant param_tw_back.txt result_tw_pond "s|^  f_masktype = 0|&\n  fn_rscap = 'rscap_one.txt'|" > "$tmp"
expect_stop tw_pond "$tmp" "a paddy cell is a pond cell"
variant param_tw_back.txt result_tw_db "s|^  fn_paddy = '-'|&\n  fn_geomorph = '-'|;s|^  rn0 = 0.03|&\n  sd0 = 1.0|" > "$tmp"
printf "\n&list_geomorph\n  f_debris = 1\n/\n" >> "$tmp"
expect_stop tw_db "$tmp" "f_pd_exchange=1 cannot be combined with debris flows"
variant param_b_back.txt result_b_db "s|^  fn_paddy = '-'|&\n  fn_geomorph = '-'|;s|^  rn0 = 0.03|&\n  sd0 = 1.0|" > "$tmp"
printf "\n&list_geomorph\n  f_debris = 1\n/\n" >> "$tmp"
expect_stop b_db "$tmp" "fn_pd_plot cannot be combined with debris flows"
variant param_tw_back.txt result_tw_nh "s|^  fn_paddy = '-'|&\n  fn_enc = '-'|" > "$tmp"
printf "\n&list_enc\n  f_nonhydrostatic = 1\n/\n" >> "$tmp"
expect_stop tw_nh "$tmp" "cannot be combined with the non-hydrostatic correction"
# 集水面積率(§127.13)の入力の誤りと併用の停止
variant param_catch.txt result_catch_range "s/'catch_03.txt'/'catch_bad.txt'/" > "$tmp"
expect_stop catch_range "$tmp" "the catchment fraction (fn_pd_catch) must satisfy 0 <= c <= 1"
variant param_mix.txt result_catch_nopd "s|^  fn_pd_frac = 'frac_mix.txt'|&\n  fn_pd_catch = 'catch_03.txt'|" > "$tmp"
expect_stop catch_nopd "$tmp" "is > 0 on a cell without paddy fields"
variant param_steady.txt result_catch_gv "s|^  pd_adopt = 0.5|&\n  fn_pd_catch = 'catch_03.txt'|" > "$tmp"
expect_stop catch_gv "$tmp" "plus the catchment fraction (fn_pd_catch) exceeds the void ratio"
variant param_wash.txt result_catch_ero "s|^  fn_pd_frac = 'frac_mix.txt'|&\n  fn_pd_catch = 'catch_mix.txt'|" > "$tmp"
expect_stop catch_ero "$tmp" "fn_pd_catch cannot be combined with the raindrop erosion"
# 区画の解像(B)の入力の誤りと併用の停止
bstop() {   # bstop <タグ> <sed 式> <停止の文言>(param_b_back.txt の変形)
    variant param_b_back.txt "result_$1" "$2" > "$tmp"
    expect_stop "$1" "$tmp" "$3"
}
bstop b_ring "s/'b_back_plot.txt'/'b_bad_ring_plot.txt'/" "a plot cell is on the outermost row or column"
bstop b_self "s/'b_back_out.txt'/'b_bad_self_out.txt'/" "an outlet points to a cell of the same plot"
bstop b_noplot "s/'b_back_out.txt'/'b_bad_noplot_out.txt'/" "is given on a cell that is not a plot cell"
bstop b_class "s|^  fn_pd_outlet = .*|&\n  fn_pd_class = 'b_bad_class.txt'|" "the cells of a plot have different outlet classes"
bstop b_id "s/'b_back_plot.txt'/'b_bad_id_plot.txt'/" "the plot number (fn_pd_plot) must be an integer"
bstop b_up "s/'b_back_z.txt'/'b_bad_up_z.txt'/" "an outlet points to a cell whose ground is not below the levee crest"
bstop b_face "s/'b_back_plot.txt'/'b_bad_face_plot.txt'/;s/'b_back_out.txt'/'b_bad_face_out.txt'/" "two outlets face each other"
bstop b_frac "s|^  pd_hlev = 0.30|&\n  pd_frac = 1.0|" "fn_pd_frac and pd_frac are for the subgrid paddy tanks"
bstop b_exch "s|^  pd_hlev = 0.30|&\n  f_pd_exchange = 1|" "f_pd_exchange (the resolved plots exchange water"
bstop b_catch "s|^  pd_hlev = 0.30|&\n  fn_pd_catch = 'catch_zero.txt'|" "fn_pd_catch (the farm roads and levees draining"
# 掃流砂の写しの手続き(混合粒径・芦田・道上の有効掃流力)と B、混合粒径と双方向・浮遊砂の併用の停止(§127.17)
variant param_b_sed.txt result_b_bmix "s|^  fluv_dzmax = 0.05|&\n  f_bedmix = 1\n  bmix_d = 0.001, 0.020\n  bmix_frac0 = 0.5, 0.5|" > "$tmp"
expect_stop b_bmix "$tmp" "fn_pd_plot cannot be combined with the bed load of mixed grain sizes"
variant param_b_sed.txt result_b_taueff "s|^  fluv_dzmax = 0.05|&\n  f_taupart = 2|" > "$tmp"
expect_stop b_taueff "$tmp" "fn_pd_plot cannot be combined with the bed load of mixed grain sizes"
variant param_sed_tw.txt result_tw_bmix "s|^  f_suspend = 1|&\n  f_fluvial = 1\n  f_qbform = 1\n  fluv_d50 = 0.001\n  fluv_tausc = 0.05\n  fluv_sgrav = 1.65\n  f_bedmix = 1\n  bmix_d = 0.0002, 0.020\n  bmix_frac0 = 0.5, 0.5|" > "$tmp"
expect_stop tw_bmix "$tmp" "f_pd_exchange=1 with suspended sediment (f_suspend) cannot be combined with mixed grain sizes"
variant param_b_back.txt result_b_nh "s|^  fn_paddy = '-'|&\n  fn_enc = '-'|" > "$tmp"
printf "\n&list_enc\n  f_nonhydrostatic = 1\n/\n" >> "$tmp"
expect_stop b_nh "$tmp" "fn_pd_plot cannot be combined with the non-hydrostatic correction"
variant param.txt result_b_aonly "s|^  pd_frac = 1.0 |  fn_pd_outlet = 'b_back_out.txt'\n&|" > "$tmp"
expect_stop b_aonly "$tmp" "fn_pd_outlet and fn_pd_class require fn_pd_plot"

echo "=== paddy verification PASS ==="
