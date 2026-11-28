#!/bin/bash
# wqsalt: MPI 実行(N ランク)+ 検定(developer.md §139)
#   ./Run_MPI.sh [N](既定 2。N <= 4)
# 全ケースを N ランクで回して Check_cases.sh で判定し、帯の境をまたぐ輸送のある 7 ケース(mix・mixflow・
# mixwall・mixgv・mixwd・sea・c0map)は 1 ランク(同じ実行ファイル)でも回して、Log.txt・wq.csv・最後の濃度の分布を
# バイト比較する(水平の混合の流束は隣の行の濃度と水深を読む。海から入る水は海の列から東へ進む)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

cases="mix mixflow mixwall mixgv mixwd sat dis disk inf sea c0map evts"
mcases="mix mixflow mixwall mixgv mixwd sea c0map"

tmp=$(mktemp -p .)
trap 'rm -f "$tmp"' EXIT
: > Screen.log
rc=0
for c in $cases; do
    echo "--- $c (np=$NP)"
    rm -rf result_$c
    export ENCFLOW_EXPECT_NP="$NP"
    if ! mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt >> Screen.log 2>&1; then
        echo "FAIL: $c の実行が異常終了した(Screen.log)" >&2
        exit 1
    fi
done
for c in $mcases; do
    rm -rf result_${c}_np1
    sed "s/^  dir_result = 'result_$c'/  dir_result = 'result_${c}_np1'/" param_$c.txt > "$tmp"
    export ENCFLOW_EXPECT_NP=1
    mpirun -np 1 $MPIRUN_OPTS ./encflow_mpi "$tmp" >> Screen.log 2>&1 || exit 1
    for f in Log.txt wq.csv C9998.bil; do
        if cmp -s "result_$c/$f" "result_${c}_np1/$f"; then
            echo "  ok   result_$c/$f identical between np=$NP and np=1"
        else
            echo "FAIL: result_$c/$f differs between np=$NP and np=1" >&2
            rc=1
        fi
    done
done
echo ""

"$sdir/Check_cases.sh" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== wqsalt MPI verification PASS ==="
else
    echo "=== wqsalt MPI verification FAIL ===" >&2
fi
exit $rc
