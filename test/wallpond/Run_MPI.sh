#!/bin/bash
# wallpond: MPI 実行(N ランク)+ 検定(developer.md §134)
#   ./Run_MPI.sh [N](既定 2。N <= 4。計算する行が 2 行だけの ax2_mask は 2 ランクまでで回す)
# 全ケースを N ランクで回して Check_wallpond.py で判定し、湛水の 4 ケース(make_wallpond.py mpi)は 1 ランク
# (同じ実行ファイル)でも回して、Log.txt・水位 E0003・水深 H0003 をバイト比較する。帯の境は河道と堤防を横切る
# (仮想壁面の判定が読む隣のセルがハロの行に入る)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_wallpond.py" || exit 1
cases=$(python3 "$sdir/make_wallpond.py" list)
mcases=$(python3 "$sdir/make_wallpond.py" mpi)

tmp=$(mktemp -p .)
trap 'rm -f "$tmp"' EXIT
: > Screen.log
rc=0
for c in $cases; do
    # ax2_mask は計算する行が河道の 2 行だけ(窓は 4 行)なので、2 ランクまでで回す(1 ランクに 2 行以上が要る)
    n=$NP
    if [ "$c" = ax2_mask ] && [ "$n" -gt 2 ]; then n=2; fi
    echo "--- $c (np=$n)"
    export ENCFLOW_EXPECT_NP="$n"
    if ! mpirun -np "$n" $MPIRUN_OPTS ./encflow_mpi p_$c.txt >> Screen.log 2>&1; then
        echo "FAIL: $c の実行が異常終了した(Screen.log)" >&2
        exit 1
    fi
done
for c in $mcases; do
    sed "s/^  dir_result = 'result_$c'/  dir_result = 'result_${c}_np1'/" p_$c.txt > "$tmp"
    export ENCFLOW_EXPECT_NP=1
    mpirun -np 1 $MPIRUN_OPTS ./encflow_mpi "$tmp" >> Screen.log 2>&1 || exit 1
    for f in Log.txt E0003.txt H0003.txt; do
        if cmp -s "result_$c/$f" "result_${c}_np1/$f"; then
            echo "  ok   result_$c/$f identical between np=$NP and np=1"
        else
            echo "FAIL: result_$c/$f differs between np=$NP and np=1" >&2
            rc=1
        fi
    done
done
echo ""

python3 "$sdir/Check_wallpond.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== wallpond MPI verification PASS ==="
else
    echo "=== wallpond MPI verification FAIL ===" >&2
fi
exit $rc
