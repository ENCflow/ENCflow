#!/bin/bash
# sfzone: MPI 実行 + 回帰テスト + 解析検定(貯留関数法の区画・タンク・出口。developer.md §106)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は Log.txt を ULP=0、sfm_zone.csv は np=1 とバイト比較(タンクは全ランクで
# 冗長に解く。出口は所有ランクだけが加える)。面積平均モード(行部分和の決定的総和)、厳密モードの停止
# (全ランク同時の par_stop)、保存 → 再開、同期区間の途中での保存 → 再開(np=1 とバイト比較)、
# VZ との併用と区画の重なりの停止(全ランク同時)、遅れ時間(param_lag.txt)、蒸発散(param_et.txt)、
# 降雨遮断の 2 段の遮断率(param_ic.txt)も MPI で確かめる。
# 行は 8 なので np <= 4
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=6
export FILES=${FILES:-Log.txt}
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

python3 Check_sfzone.py base result || exit 1

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

# sfm_zone.csv の並列数不変性: 同じバイナリの np=1 とバイト比較する(同一ホスト・同一バイナリ
# なので CPU 差の影響を受けない厳密な検査。reference との比較は Log.txt だけ = Run.sh の注記)
if [ "$np" != 1 ]; then
    variant param.txt result_np1 "" > "$tmp"
    run 1 np1 "$tmp"
    same_as_np1 result result_np1 sfm_zone.csv
fi

run "$np" avg param_avg.txt
python3 Check_sfzone.py avg result_avg || exit 1
expect_stop strictfail param_strictfail.txt "rainfall differs within zone"

rm -rf save
run "$np" save param_save.txt
run "$np" restart param_restart.txt
python3 Check_sfzone.py restart result result_restart || exit 1

# 同期区間の途中(21625 s)での保存 → 再開: np=1 と保存ファイル・出力がバイト一致
rm -rf save_psync save_psync1
for sfx in "" 1; do
    n=$np; [ "$sfx" = 1 ] && n=1
    variant param_sync.txt "result_psync_save$sfx" \
        "s/^  tt = 43200 .*/  tt = 21625/;s|^  dir_result = 'result_psync_save$sfx'|&\n  dir_save = 'save_psync$sfx'\n  f_state_save = 1|" > "$tmp"
    run "$n" "psync_save$sfx" "$tmp"
    variant param_sync.txt "result_psync_restart$sfx" \
        "s|^  dir_result = 'result_psync_restart$sfx'|&\n  dir_save = 'save_psync$sfx'\n  f_state_restore = 1|" > "$tmp"
    run "$n" "psync_restart$sfx" "$tmp"
done
cmp -s save_psync/sfm.dat save_psync1/sfm.dat \
    || { echo "ERROR: sfm.dat saved in the middle of an interval differs between np=$np and np=1" >&2; exit 1; }
echo "  ok   sfm.dat saved in the middle of an interval identical between np=$np and np=1"
same_as_np1 result_psync_restart result_psync_restart1 sfm_zone.csv Log.txt

# 遅れ時間: np=1 と出力がバイト一致。同期間隔 60 s の同期区間の途中(21625 s)の保存(遅れ列を含む
# sfm.dat)が np=1 とバイト一致
run "$np" lag param_lag.txt
python3 Check_sfzone.py lag result result_lag || exit 1
if [ "$np" != 1 ]; then
    variant param_lag.txt result_lag_np1 "" > "$tmp"
    run 1 lag_np1 "$tmp"
    same_as_np1 result_lag result_lag_np1 sfm_zone.csv Log.txt
fi
rm -rf save_lagp save_lagp1
for sfx in "" 1; do
    n=$np; [ "$sfx" = 1 ] && n=1
    variant param_lag.txt "result_lag_psave$sfx" \
        "s|^  fn_sfm_zone = 'zone.txt'|&\n  dt_sfm = 60.0|;s/'save_lag'/'save_lagp$sfx'/;s/^  tt = 43200 .*/  tt = 21625/;s/f_state_save = 0 /f_state_save = 1 /" > "$tmp"
    run "$n" "lag_psave$sfx" "$tmp"
done
cmp -s save_lagp/sfm.dat save_lagp1/sfm.dat \
    || { echo "ERROR: sfm.dat with lag saved in the middle of an interval differs between np=$np and np=1" >&2; exit 1; }
echo "  ok   sfm.dat with lag saved in the middle of an interval identical between np=$np and np=1"

# 蒸発散をタンクから引く(区画ごとの要求の決定的総和): np=1 と出力がバイト一致
run "$np" et param_et.txt
python3 Check_sfzone.py et result_et || exit 1
if [ "$np" != 1 ]; then
    variant param_et.txt result_et_np1 "" > "$tmp"
    run 1 et_np1 "$tmp"
    same_as_np1 result_et result_et_np1 sfm_zone.csv Log.txt evap.csv
fi

# 降雨遮断の 2 段の遮断率(一様と分布ファイル): np=1 と出力がバイト一致、分布ファイルは一様指定と一致
run "$np" ic param_ic.txt
python3 Check_sfzone.py ic result_ic 0.5 20 0 || exit 1
variant param_ic.txt result_icmap "s/^  ic_alpha_fill = 0.5 .*/  fn_icalpha_fill = 'icfill.txt'/;s/^  ic_alpha_full = 0.0 .*/  fn_icalpha_full = 'icfull.txt'/" > "$tmp"
run "$np" icmap "$tmp"
same_as_np1 result_icmap result_ic sfm_zone.csv Log.txt
if [ "$np" != 1 ]; then
    variant param_ic.txt result_ic_np1 "" > "$tmp"
    run 1 ic_np1 "$tmp"
    same_as_np1 result_ic result_ic_np1 sfm_zone.csv Log.txt
fi

# VZ との併用と、区画の重なりの停止
run "$np" mosaic param_mosaic.txt
python3 Check_sfzone.py mosaic result result_mosaic || exit 1
variant param_mosaic.txt result_overlap "s/'vzzone_mosaic.txt'/'vzzone_overlap.txt'/" > "$tmp"
expect_stop overlap "$tmp" "a cell belongs to both a VZ zone and a SFM zone"
variant param_mosaic.txt result_outvz "s/^  sfm_out_cell(:,1,2) = 7, 1 /  sfm_out_cell(:,1,2) = 3, 7 /" > "$tmp"
expect_stop outvz "$tmp" "list_sfm_zone: an outlet cell is a VZ cell"

echo "=== sfzone MPI verification PASS ==="
