#!/bin/bash
# gwtani: MPI 実行 + 検定(谷(Tani)型のシナリオ。developer.md §16.7)
#   ./Run_MPI.sh [ランク数]
# 逐次(Run.sh)と同じ検定を同じ並列数で回し、同じバイナリの np = 1 と分布出力(*.bil)と
# Log.txt(Runge 列を除く)をバイト比較する。斜面は 41 行なので 2 行/ランクの制約から np <= 20
sdir=$(dirname "$(readlink -f "$0")")
"$sdir/../Scripts/Check_mode.sh" mpi || exit 1
export MPIRUN_OPTS=${MPIRUN_OPTS:-"--bind-to none"}
python3 "$sdir/make_data.py"

np=2
for a in "$@"; do np=$a; done

run() {   # run <ランク数> <param> <ログ>
    ENCFLOW_EXPECT_NP="$1" mpirun -np "$1" $MPIRUN_OPTS ./encflow_mpi "$2" > "$3" 2>&1 \
        || { echo "ERROR: $2 (np=$1) run failed" >&2; exit 1; }
}
same_as_np1() {   # same_as_np1 <param> <dir_result>: np = 1 で回し直して出力をバイト比較する
    local tmp f
    tmp=$(mktemp)
    sed -e "s/dir_result = '[^']*'/dir_result = '$2_np1'/" -e "s/dir_save = '[^']*'/dir_save = 'save_np1'/" "$1" > "$tmp"
    rm -rf "$2_np1" save_np1
    run 1 "$tmp" Screen_np1.log
    rm -f "$tmp"
    for f in "$2"/*.bil; do
        cmp -s "$f" "$2_np1/${f##*/}" || { echo "ERROR: $f differs between np=$np and np=1" >&2; exit 1; }
    done
    cmp -s <(awk '{$6 = ""; print}' "$2/Log.txt") <(awk '{$6 = ""; print}' "$2_np1/Log.txt") \
        || { echo "ERROR: $2/Log.txt differs between np=$np and np=1" >&2; exit 1; }
    echo "  ok   $2/*.bil and Log.txt identical between np=$np and np=1"
    rm -rf "$2_np1" save_np1
}

rm -rf save_rt0 save_rt
for c in uni_thin uni_thick thin_toe thin_toe_k2 l2only rt0 rt1 rt2; do
    rm -rf result_$c
    run "$np" param_$c.txt Screen_$c.log
done
rc=0
for c in uni_thin uni_thick thin_toe thin_toe_k2 l2only kcompare restart; do
    python3 "$sdir/Check_gwtani.py" $c || rc=1
done
[ $rc -eq 0 ] || { echo "=== gwtani MPI verification FAIL (np=$np) ===" >&2; exit 1; }
if [ "$np" != 1 ]; then
    for c in uni_thin uni_thick thin_toe thin_toe_k2 l2only rt0; do
        same_as_np1 param_$c.txt result_$c
    done
fi

echo "=== gwtani MPI verification PASS (np=$np) ==="
