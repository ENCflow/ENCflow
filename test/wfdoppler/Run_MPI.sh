#!/bin/bash
# wfdoppler: MPI 実行 + 回帰テスト + 検定(流れによる沿岸の波浪場の変化 = 段 W3。developer.md §90)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は Log.txt・wavefield.csv・Wh9998.txt・u9998.txt を ULP=0
# (CLAUDE.md 検証規律。ドップラーの分散関係・2 リンク分解・流れの勾配による屈折は
# セルごとの局所計算と u・v・E のハロ交換なので並列数によらずビット一致する)。河口の噴流
# (param_river。2 次元の流れの勾配がランク界面をまたぐ)は同じバイナリの np = 1 と
# バイト比較し、再開の往復(rt1 → rt2)は同じ並列数の通し計算とバイト比較する。水路は
# 8 行なので 2 行/ランクの制約から np <= 4
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
export FILES=${FILES:-"Log.txt wavefield.csv Wh9998.txt u9998.txt"}
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

np=2
for a in "$@"; do case $a in -u) ;; *) np=$a ;; esac; done

run() {   # run <ランク数> <param> <ログ>
    mpirun -np "$1" $MPIRUN_OPTS ./encflow_mpi "$2" > "$3" 2>&1 \
        || { echo "ERROR: $2 (np=$1) run failed" >&2; exit 1; }
}
withdir() {   # withdir <param> <新しい dir_result> → 一時ファイル名
    local tmp
    tmp=$(mktemp)
    sed -e "s/dir_result = '[^']*'/dir_result = '$2'/" "$1" > "$tmp"
    echo "$tmp"
}

python3 Check_wfdoppler.py blk result || exit 1

rm -rf result_river
run "$np" param_river.txt Screen_river.log
if [ "$np" != 1 ]; then
    tmp=$(withdir param_river.txt result_river_np1)
    rm -rf result_river_np1
    run 1 "$tmp" Screen_river_np1.log
    rm -f "$tmp"
    for f in E9998.bil u9998.bil v9998.bil Wh9998.bil wavefield.csv; do
        cmp -s result_river/$f result_river_np1/$f \
            || { echo "ERROR: result_river/$f differs between np=$np and np=1" >&2; exit 1; }
        echo "  ok   river/$f identical between np=$np and np=1"
    done
fi

rm -rf result_rt1 result_rt2 save_rt
run "$np" param_rt1.txt Screen_rt1.log
run "$np" param_rt2.txt Screen_rt2.log
for f in save_all/state.dat:save_rt/state.dat save_all/swflow_enc.dat:save_rt/swflow_enc.dat \
         save_all/wavefield.dat:save_rt/wavefield.dat \
         result/Wh9998.bil:result_rt2/Wh9998.bil result/u9998.bil:result_rt2/u9998.bil; do
    a=${f%%:*}; b=${f##*:}
    cmp -s "$a" "$b" || { echo "ERROR: restart continuation (np=$np) differs from the straight run: $b" >&2; exit 1; }
    echo "  ok   restart continuation (np=$np) matches the straight run: $b"
done

echo "=== wfdoppler verification PASS ==="
