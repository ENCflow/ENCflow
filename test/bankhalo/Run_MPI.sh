#!/bin/bash
# bankhalo: MPI 実行(N ランク)+ 検定(developer.md §128)
#   ./Run_MPI.sh [N](既定 2。行は 16 なので N <= 8)
# N ランクと 1 ランク(同じ実行ファイル)の Log.txt・水位 E・水深 H をバイト比較する。帯の境が河道を
# 横切るので、斜めの堤防エッジの隣のセルがハロの行に入り、越流の追い越し上限がハロの af を読む
# (ハロの af が古いままだと N ランクが 1 ランクと一致しない)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

for k in z rw w e; do
    python3 "$sdir/make_bankhalo.py" $k > bh_$k.txt
done

tmp=$(mktemp -p .)
trap 'rm -f "$tmp"' EXIT
set -o pipefail
: > Screen.log
rc=0
for c in param param_sect; do
    res=$(sed -n "s/^  dir_result = '\([a-z_0-9]*\)'.*/\1/p" $c.txt)
    export ENCFLOW_EXPECT_NP="$NP"
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi $c.txt | tee -a Screen.log || exit 1
    sed "s/^  dir_result = '$res'/  dir_result = '${res}_np1'/" $c.txt > "$tmp"
    export ENCFLOW_EXPECT_NP=1
    mpirun -np 1 $MPIRUN_OPTS ./encflow_mpi "$tmp" >> Screen.log || exit 1
    for f in Log.txt E0001.txt H0001.txt; do
        if cmp -s "$res/$f" "${res}_np1/$f"; then
            echo "  ok   $res/$f identical between np=$NP and np=1"
        else
            echo "FAIL: $res/$f differs between np=$NP and np=1" >&2
            rc=1
        fi
    done
done
set +o pipefail
echo ""

python3 "$sdir/Check_bankhalo.py" result result_sect || rc=1
if [ $rc -eq 0 ]; then
    echo "=== bankhalo MPI verification PASS ==="
else
    echo "=== bankhalo MPI verification FAIL ===" >&2
fi
exit $rc
