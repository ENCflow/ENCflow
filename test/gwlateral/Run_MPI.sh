#!/bin/bash
# gwlateral: MPI 実行 + 検定(地下水の側方流 f_gwlateral = 1。developer.md §16.1・§16.6)
#   ./Run_MPI.sh [ランク数]
# 逐次(Run.sh)と同じ検定を同じ並列数で回し、同じバイナリの np = 1 と分布出力(Hg*.bil)と
# Log.txt(Runge 列を除く)をバイト比較する。構成 2〜4 は 40 行なので 2 行/ランクの制約から np <= 20
sdir=$(dirname "$(readlink -f "$0")")
"$sdir/../Scripts/Check_mode.sh" mpi || exit 1
export MPIRUN_OPTS=${MPIRUN_OPTS:-"--bind-to none"}
python3 "$sdir/make_init.py"

np=2
for a in "$@"; do np=$a; done

run() {   # run <ランク数> <param> <ログ>
    ENCFLOW_EXPECT_NP="$1" mpirun -np "$1" $MPIRUN_OPTS ./encflow_mpi "$2" > "$3" 2>&1 \
        || { echo "ERROR: $2 (np=$1) run failed" >&2; exit 1; }
}
same_as_np1() {   # same_as_np1 <param> <dir_result>: np = 1 で回し直して出力をバイト比較する
    local tmp f
    tmp=$(mktemp)
    sed -e "s/dir_result = '[^']*'/dir_result = '$2_np1'/" "$1" > "$tmp"
    rm -rf "$2_np1"
    run 1 "$tmp" Screen_np1.log
    rm -f "$tmp"
    for f in "$2"/Hg*.bil; do
        cmp -s "$f" "$2_np1/${f##*/}" || { echo "ERROR: $f differs between np=$np and np=1" >&2; exit 1; }
    done
    cmp -s <(awk '{$6 = ""; print}' "$2/Log.txt") <(awk '{$6 = ""; print}' "$2_np1/Log.txt") \
        || { echo "ERROR: $2/Log.txt differs between np=$np and np=1" >&2; exit 1; }
    echo "  ok   $2/Hg*.bil and Log.txt identical between np=$np and np=1"
    rm -rf "$2_np1"
}

rm -rf result result_strip result_strip_open result_line_open
run "$np" param.txt Screen.log
for tag in strip strip_open line_open; do
    run "$np" param_$tag.txt Screen_$tag.log
done
python3 Check_gwlateral.py gauss result || exit 1
for tag in strip strip_open line_open; do
    python3 Check_gwlateral.py $tag result_$tag || exit 1
done
if [ "$np" != 1 ]; then
    same_as_np1 param.txt result
    for tag in strip strip_open line_open; do
        same_as_np1 param_$tag.txt result_$tag
    done
fi

echo "=== gwlateral MPI verification PASS (np=$np) ==="
