#!/bin/bash
# wfshoal: MPI 実行 + 回帰テスト + 解析検定(沿岸の波浪場 fn_wavefield。developer.md §88)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は Log.txt・wavefield.csv・Wh0001.txt を ULP=0(CLAUDE.md
# 検証規律。波浪場の更新は Jacobi 型、台帳は行部分和の決定的総和なので並列数に
# よらずビット一致する)。砕波(param_brk)・非定常(param_unst)の波高の分布は
# 同じバイナリの np = 1 とバイト比較し、再開の往復(rt1 → rt2)は同じ並列数の
# 通し計算とバイト比較する。行は 8 なので 2 行/ランクの制約から np <= 4
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
export FILES=${FILES:-"Log.txt wavefield.csv Wh0001.txt"}
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

python3 Check_wfshoal.py base result || exit 1

np=2
for a in "$@"; do case $a in -u) ;; *) np=$a ;; esac; done

run() {   # run <ランク数> <param> <ログ>
    mpirun -np "$1" $MPIRUN_OPTS ./encflow_mpi "$2" > "$3" 2>&1 \
        || { echo "ERROR: $2 (np=$1) run failed" >&2; exit 1; }
}
withdir() {   # withdir <param> <新しい dir_result> → 一時ファイル名
    local tmp
    tmp=$(mktemp)
    sed -e "s/dir_result = '[^']*'/dir_result = '$2'/" -e "s/dir_save = 'save_all'/dir_save = 'save_np1'/" "$1" > "$tmp"
    echo "$tmp"
}

for tag in brk unst; do
    rm -rf result_$tag
    run "$np" param_$tag.txt Screen_$tag.log
done
python3 Check_wfshoal.py brk result_brk || exit 1
python3 Check_wfshoal.py unst result_unst result_brk || exit 1
if [ "$np" != 1 ]; then
    for tag in brk unst; do
        tmp=$(withdir param_$tag.txt result_${tag}_np1)
        rm -rf result_${tag}_np1 save_np1
        run 1 "$tmp" Screen_${tag}_np1.log
        rm -f "$tmp"
        for f in Wh0001.bil Wh9998.bil wavefield.csv; do
            [ -e result_$tag/$f ] || continue
            cmp -s result_$tag/$f result_${tag}_np1/$f \
                || { echo "ERROR: result_$tag/$f differs between np=$np and np=1" >&2; exit 1; }
            echo "  ok   $tag/$f identical between np=$np and np=1"
        done
    done
fi

rm -rf result_rt1 result_rt2 save_rt
run "$np" param_rt1.txt Screen_rt1.log
run "$np" param_rt2.txt Screen_rt2.log
for f in save_all/wavefield.dat:save_rt/wavefield.dat save_all/state.dat:save_rt/state.dat \
         result_unst/Wh9998.bil:result_rt2/Wh9998.bil; do
    a=${f%%:*}; b=${f##*:}
    cmp -s "$a" "$b" || { echo "ERROR: restart continuation (np=$np) differs from the straight run: $b" >&2; exit 1; }
    echo "  ok   restart continuation (np=$np) matches the straight run: $b"
done

rm -rf result_nowf
run "$np" param_nowf.txt Screen_nowf.log
cmp -s result/Log.txt result_nowf/Log.txt \
    || { echo "ERROR: Log.txt differs from the run without the wave field (np=$np)" >&2; exit 1; }
echo "  ok   the flow (Log.txt) is identical to the run without the wave field (np=$np)"

echo "=== wfshoal verification PASS ==="
