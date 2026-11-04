#!/bin/bash
# dbonset: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)
# 先に ./Run.sh を実行しておくと、各ケースの save_<case>/state.dat を逐次の結果と比べる
NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" || exit 1
cases=$(python3 "$sdir/make_init.py" list)

export ENCFLOW_EXPECT_NP="$NP"
: > Screen.log
for c in $cases; do
    echo "--- $c (np=$NP)"
    if ! mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi p_$c.txt >> Screen.log 2>&1; then
        echo "FAIL: $c の実行が異常終了した(Screen.log)" >&2
        exit 1
    fi
done
echo ""
rc=0
python3 "$sdir/Check_dbonset.py" || rc=1
nsame=0
ndiff=0
for c in $cases; do
    if [ -d save_${c}_serial ]; then
        if cmp -s save_$c/state.dat save_${c}_serial/state.dat; then
            nsame=$((nsame + 1))
        else
            echo "警告: save_$c/state.dat が逐次の結果と不一致" >&2
            ndiff=$((ndiff + 1))
        fi
    fi
done
if [ $((nsame + ndiff)) -gt 0 ]; then
    echo "=== state.dat: 逐次の結果とビット一致 $nsame ケース、不一致 $ndiff ケース ==="
    if [ $ndiff -gt 0 ]; then
        echo "      (-Ofast の fast-math のビルド間差の可能性。ビット検証は -O2 厳密数学で — §28.3)" >&2
    fi
fi
exit $rc
