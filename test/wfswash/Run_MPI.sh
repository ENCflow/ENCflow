#!/bin/bash
# wfswash: MPI 実行 + 検定(遡上域の輸送 f_wfswash。developer.md §90.21)
#   ./Run_MPI.sh [ランク数]
# 逐次(Run.sh)と同じ検定を同じ並列数で回し、同じバイナリの np = 1 と state.dat・最終分布をバイト比較する
# (汀線セルの遡上高・沿岸のベクトルは自帯で求めてハロ交換、面の流束は書き手一意で je+1 行を冗長に
# 計算するので、並列数によらずビット一致する)。再開の往復(rt1 → rt2)は同じ並列数の通し計算と
# バイト比較する。行が 8 のケースは 2 行/ランクの制約から np <= 4
sdir=$(dirname "$(readlink -f "$0")")
"$sdir/../Scripts/Check_mode.sh" mpi || exit 1
export MPIRUN_OPTS=${MPIRUN_OPTS:-"--bind-to none"}
python3 "$sdir/make_z.py"

np=2
for a in "$@"; do np=$a; done

run() {   # run <ランク数> <param> <ログ>
    ENCFLOW_EXPECT_NP="$1" mpirun -np "$1" $MPIRUN_OPTS ./encflow_mpi "$2" > "$3" 2>&1 \
        || { echo "ERROR: $2 (np=$1) run failed" >&2; exit 1; }
}
withdir() {   # withdir <param> <新しい dir_result> <新しい dir_save> → 一時ファイル名
    local tmp
    tmp=$(mktemp)
    sed -e "s/dir_result = '[^']*'/dir_result = '$2'/" -e "s/dir_save = '[^']*'/dir_save = '$3'/" "$1" > "$tmp"
    echo "$tmp"
}

tags="rate diag eq mild steep obl cliff flow"
for tag in $tags; do
    rm -rf result_$tag save_$tag
    run "$np" param_$tag.txt Screen_$tag.log
done
python3 Check_wfswash.py rate result_rate save_rate || exit 1
python3 Check_wfswash.py diag result_diag save_diag || exit 1
python3 Check_wfswash.py eq save_eq || exit 1
python3 Check_wfswash.py mild save_mild || exit 1
python3 Check_wfswash.py steep save_steep || exit 1
python3 Check_wfswash.py obl result_obl save_obl || exit 1
python3 Check_wfswash.py cliff result_cliff save_cliff || exit 1
python3 Check_wfswash.py flow result_flow save_flow || exit 1
if [ "$np" != 1 ]; then
    for tag in $tags; do
        tmp=$(withdir param_$tag.txt result_${tag}_np1 save_${tag}_np1)
        rm -rf result_${tag}_np1 save_${tag}_np1
        run 1 "$tmp" Screen_${tag}_np1.log
        rm -f "$tmp"
        for f in save_$tag/state.dat:save_${tag}_np1/state.dat result_$tag/Z9998.bil:result_${tag}_np1/Z9998.bil; do
            a=${f%%:*}; b=${f##*:}
            cmp -s "$a" "$b" || { echo "ERROR: $a differs between np=$np and np=1" >&2; exit 1; }
            echo "  ok   $a identical between np=$np and np=1"
        done
        rm -rf result_${tag}_np1 save_${tag}_np1
    done
fi

rm -rf result_rt1 result_rt2 save_rt
run "$np" param_rt1.txt Screen_rt1.log
run "$np" param_rt2.txt Screen_rt2.log
for f in save_flow/state.dat:save_rt/state.dat save_flow/swflow_enc.dat:save_rt/swflow_enc.dat \
         save_flow/wavefield.dat:save_rt/wavefield.dat \
         result_flow/Z9998.bil:result_rt2/Z9998.bil result_flow/Hs9998.bil:result_rt2/Hs9998.bil; do
    a=${f%%:*}; b=${f##*:}
    cmp -s "$a" "$b" || { echo "ERROR: restart continuation (np=$np) differs from the straight run: $b" >&2; exit 1; }
    echo "  ok   restart continuation (np=$np) matches the straight run: $b"
done

echo "=== wfswash MPI verification PASS (np=$np) ==="
