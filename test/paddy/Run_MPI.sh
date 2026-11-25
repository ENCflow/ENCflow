#!/bin/bash
# paddy: MPI 実行 + 回帰テスト + 解析検定(田んぼダムのサブグリッドの水田タンク fn_paddy。developer.md §119)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は Log.txt を ULP=0。paddy.csv は同じバイナリの np=1 とバイト比較(セル単位の
# 計算と行部分和の決定的総和なので、ランク数によらない)。閉じた領域の水の保存(param_mix.txt)、
# 雨滴侵食から水田の部分を外す検定(param_wash.txt・param_splash.txt。地盤高も np=1 とバイト比較)、
# 双方向(二室化)の検定(param_tw_back・tw_flood・tw_drain。np=1 とバイト比較)、
# 区画の解像(表現 B。§119.8。param_b_*.txt。区画・落水口・市松の角が帯の境にかかる。np=1 とバイト比較)、
# 水質と併用するタンクのプールと区画の解像の減水深の持ち出し(param_wq_a・wq_tw・wq_b。np=1 とバイト比較)と
# その保存 → 再開、土砂(param_sed_tw・b_sed。np=1 とバイト比較)、集水面積率(param_catch の片方向・双方向と
# 水質。np=1 とバイト比較)、
# 保存 → 再開(np=1 とバイト比較)、rank0 が見つける停止と帯で見つける停止(全ランク同時の par_stop)も
# MPI で確かめる。行は 8 なので np <= 4
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
export FILES=${FILES:-Log.txt}
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

python3 Check_paddy.py weir result || exit 1

np=2
for a in "$@"; do case $a in -u) ;; *) np=$a ;; esac; done

variant() {   # variant <元の設定> <dir_result> <追加の sed 式> > 出力
    sed -e "s/^  dir_result = '[a-z_0-9]*'/  dir_result = '$2'/" -e "$3" "$1"
}
run() {   # run <ランク数> <タグ> <設定ファイル>: 実行(失敗したら終了)
    rm -rf "result_$2"
    mpirun -np "$1" $MPIRUN_OPTS ./encflow_mpi "$3" > "Screen_$2.log" 2>&1 \
        || { echo "ERROR: $3 run failed (np=$1)" >&2; exit 1; }
}
expect_stop() {   # expect_stop <タグ> <設定ファイル> <停止の文言>
    rm -rf "result_$1"
    if timeout 300 mpirun -np "$np" $MPIRUN_OPTS ./encflow_mpi "$2" > "Screen_$1.log" 2>&1; then
        echo "ERROR: $1 should stop ($3)" >&2; exit 1
    fi
    grep -q -- "$3" "Screen_$1.log" || { echo "ERROR: $1 stopped for another reason (or hung)" >&2; exit 1; }
    echo "  ok   $1 stops on all ranks: $3"
}
same_as_np1() {   # same_as_np1 <np の結果> <np=1 の結果> <ファイル...>
    local a=$1 b=$2; shift 2
    for f in "$@"; do
        cmp -s "$a/$f" "$b/$f" || { echo "ERROR: $a/$f differs between np=$np and np=1" >&2; exit 1; }
        echo "  ok   $f identical between np=$np and np=1 ($a)"
    done
}
tmp=$(mktemp -p .)
trap 'rm -f "$tmp"' EXIT

# paddy.csv の並列数不変性(同じバイナリの np=1 とバイト比較)
if [ "$np" != 1 ]; then
    variant param.txt result_np1 "" > "$tmp"
    run 1 np1 "$tmp"
    same_as_np1 result result_np1 paddy.csv
fi

# 2 種類のタンク・分布・空隙率と閉じた領域の水の保存
run "$np" mix param_mix.txt
variant param_mix.txt result_mix_nopd "/^  fn_paddy = /d" > "$tmp"
run "$np" mix_nopd "$tmp"
python3 Check_paddy.py mix result_mix result_mix_nopd || exit 1
if [ "$np" != 1 ]; then
    variant param_mix.txt result_mix_np1 "" > "$tmp"
    run 1 mix_np1 "$tmp"
    same_as_np1 result_mix result_mix_np1 paddy.csv Log.txt Hpn9998.txt Hpd9998.txt
fi

# 雨滴侵食から水田の部分を外す(地形変化との併用。§119.5): 解析検定と np=1 とのバイト一致
run "$np" wash param_wash.txt
python3 Check_paddy.py wash result_wash || exit 1
run "$np" splash param_splash.txt
python3 Check_paddy.py splash result_splash || exit 1
if [ "$np" != 1 ]; then
    for t in wash splash; do
        variant "param_$t.txt" "result_${t}_np1" "" > "$tmp"
        run 1 "${t}_np1" "$tmp"
        same_as_np1 "result_$t" "result_${t}_np1" Z0001.bil paddy.csv Log.txt
    done
fi

# 双方向(二室化。§119.6): 解析検定と np=1 とのバイト一致(帯の境の水田のセルも階段形の断面)
for t in tw_back tw_flood tw_drain; do
    run "$np" $t param_$t.txt
    python3 Check_paddy.py $t result_$t || exit 1
    if [ "$np" != 1 ]; then
        variant "param_$t.txt" "result_${t}_np1" "" > "$tmp"
        run 1 "${t}_np1" "$tmp"
        fl="paddy.csv Log.txt H9998.txt Hpn9998.txt"
        [ -f "result_$t/Hpd9998.txt" ] && fl="$fl Hpd9998.txt"
        same_as_np1 "result_$t" "result_${t}_np1" $fl
    fi
done

# 区画の解像(表現 B。§119.8): 解析検定と np=1 とのバイト一致
python3 make_plots.py data_paddy || exit 1
for t in b_drain b_tight b_over b_back b_ext b_bank b_chain; do
    run "$np" $t param_$t.txt
    python3 Check_paddy.py $t result_$t || exit 1
    if [ "$np" != 1 ]; then
        variant "param_$t.txt" "result_${t}_np1" "" > "$tmp"
        run 1 "${t}_np1" "$tmp"
        same_as_np1 "result_$t" "result_${t}_np1" paddy.csv Log.txt H9998.txt
    fi
done

# 水質(§119.10): 解析検定と np=1 とのバイト一致(タンクのプールと減水深の持ち出しの記録)
for t in wq_a wq_tw wq_b; do
    run "$np" $t param_$t.txt
    python3 Check_paddy.py $t result_$t || exit 1
    if [ "$np" != 1 ]; then
        variant "param_$t.txt" "result_${t}_np1" "" > "$tmp"
        run 1 "${t}_np1" "$tmp"
        same_as_np1 "result_$t" "result_${t}_np1" paddy.csv Log.txt wq.csv
    fi
done

# 水質のプールの保存 → 再開(np で保存・再開。帯ごとのプールを m_restart で集めて配る)と、連続計算(上の wq_a)の
# ビット一致
rm -rf save_wq
variant param_wq_a.txt result_wq_save "s/^  tt = 43200$/  tt = 21600/;s|^  dir_result = 'result_wq_save'|&\n  dir_save = 'save_wq'\n  f_state_save = 1|" > "$tmp"
run "$np" wq_save "$tmp"
variant param_wq_a.txt result_wq_restart "s|^  dir_result = 'result_wq_restart'|&\n  dir_save = 'save_wq'\n  f_state_restore = 1|" > "$tmp"
run "$np" wq_restart "$tmp"
python3 Check_paddy.py restart_wq result_wq_a result_wq_restart || exit 1

# 土砂(§119.11): 解析検定と np=1 とのバイト一致(タンクへ入る浮遊砂の堆積、区画の解像の掃流砂の除外。区画の
# 畦畔が帯の境にかかる)
for t in sed_tw b_sed; do
    run "$np" $t param_$t.txt
    python3 Check_paddy.py $t result_$t || exit 1
    if [ "$np" != 1 ]; then
        variant "param_$t.txt" "result_${t}_np1" "" > "$tmp"
        run 1 "${t}_np1" "$tmp"
        same_as_np1 "result_$t" "result_${t}_np1" paddy.csv Log.txt Z0001.bil
    fi
done

# 集水面積率(§119.13): 解析検定と np=1 とのバイト一致(片方向・双方向、集水面積の雨の物質)
variant param_catch.txt result_catch_tw "s|^  pd_perc_mmd = 0.0|&\n  f_pd_exchange = 1|" > param_catch_tw.tmp
variant param_wq_rain.txt result_catch_wq "s/^  pd_frac = 1.0$/  pd_frac = 0.5\n  fn_pd_catch = 'catch_03.txt'/" > param_catch_wq.tmp
for t in catch catch_tw catch_wq; do
    pf=param_$t.txt; [ "$t" != catch ] && pf=param_$t.tmp
    run "$np" $t "$pf"
    ck=$t; [ "$t" = catch_wq ] && ck=wq_rain
    python3 Check_paddy.py $ck result_$t || exit 1
    if [ "$np" != 1 ]; then
        variant "$pf" "result_${t}_np1" "" > "$tmp"
        run 1 "${t}_np1" "$tmp"
        same_as_np1 "result_$t" "result_${t}_np1" paddy.csv Log.txt H9998.txt
    fi
done
rm -f param_catch_tw.tmp param_catch_wq.tmp

# 保存 → 再開(np で保存・再開)と、連続計算・np=1 とのビット一致
rm -rf save_rs save_rs1
for sfx in "" 1; do
    n=$np; [ "$sfx" = 1 ] && n=1
    variant param_steady.txt "result_rs_save$sfx" "s/^  tt = 172800$/  tt = 21600/;s|^  dir_result = 'result_rs_save$sfx'|&\n  dir_save = 'save_rs$sfx'\n  f_state_save = 1|" > "$tmp"
    run "$n" "rs_save$sfx" "$tmp"
    variant param_steady.txt "result_rs_restart$sfx" "s/^  tt = 172800$/  tt = 43200/;s|^  dir_result = 'result_rs_restart$sfx'|&\n  dir_save = 'save_rs$sfx'\n  f_state_restore = 1|" > "$tmp"
    run "$n" "rs_restart$sfx" "$tmp"
done
variant param_steady.txt result_rs_cont "s/^  tt = 172800$/  tt = 43200/" > "$tmp"
run "$np" rs_cont "$tmp"
python3 Check_paddy.py restart result_rs_cont result_rs_restart || exit 1
cmp -s save_rs/paddy.dat save_rs1/paddy.dat \
    || { echo "ERROR: paddy.dat differs between np=$np and np=1" >&2; exit 1; }
echo "  ok   paddy.dat identical between np=$np and np=1"
same_as_np1 result_rs_restart result_rs_restart1 paddy.csv Log.txt

# 停止(rank0 が全域で見つける誤りと、帯で見つける誤り)
variant param.txt result_rw "s|^  f_masktype = 0|&\n  fn_rw = 'rw_one.txt'|" > "$tmp"
expect_stop rw "$tmp" "a paddy cell is on a channel cell (rw)"
variant param_mix.txt result_overgv "s/'frac_mix.txt'/'frac_over_gv.txt'/" > "$tmp"
expect_stop overgv "$tmp" "exceeds the void ratio gv"
variant param_mix.txt result_catch_nopd "s|^  fn_pd_frac = 'frac_mix.txt'|&\n  fn_pd_catch = 'catch_03.txt'|" > "$tmp"
expect_stop catch_nopd "$tmp" "is > 0 on a cell without paddy fields"
variant param_steady.txt result_catch_gv "s|^  pd_adopt = 0.5|&\n  fn_pd_catch = 'catch_03.txt'|" > "$tmp"
expect_stop catch_gv "$tmp" "plus the catchment fraction (fn_pd_catch) exceeds the void ratio"
variant param_b_back.txt result_b_ring "s/'b_back_plot.txt'/'b_bad_ring_plot.txt'/" > "$tmp"
expect_stop b_ring "$tmp" "a plot cell is on the outermost row or column"
variant param_b_back.txt result_b_up "s/'b_back_z.txt'/'b_bad_up_z.txt'/" > "$tmp"
expect_stop b_up "$tmp" "an outlet points to a cell whose ground is not below the levee crest"

echo "=== paddy MPI verification PASS ==="
