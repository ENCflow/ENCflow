#!/bin/bash
# gwdefault: MPI 実行(既定値の同値検定。developer.md §64)
#   ./Run_MPI.sh [N]   (既定 N=2)
# 構成 a〜d の最小入力(param_X.txt)と既定値の明示(param_Xx.txt)を
# N ランクで実行し、save の全ファイルと Log.txt がバイト一致することを
# 検定する(既定値の採用が全ランクで同一であること)。Run.sh が残した
# save_X_serial/ があれば逐次結果とも比較するが、-Ofast の fast-math
# ビルド間差(§28.3)があり得るため不一致は警告に留める

NP=${1:-2}
../Scripts/Check_mode.sh mpi || exit 1
export MPIRUN_OPTS="${MPIRUN_OPTS:---bind-to none}"
export ENCFLOW_EXPECT_NP="$NP"
rc=0
rm -f Screen_mpi.log
for tag in a b c d; do
    set -o pipefail
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_${tag}.txt  | tee -a Screen_mpi.log || exit 1
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_${tag}x.txt | tee -a Screen_mpi.log || exit 1
    set +o pipefail
    echo ""
    if diff -r save_${tag} save_${tag}x > /dev/null && cmp -s result_${tag}/Log.txt result_${tag}x/Log.txt; then
        echo "=== config $tag (np=$NP): save/ and Log.txt are bit-identical between the minimal input and the explicit defaults ==="
    else
        echo "FAIL: config $tag (np=$NP) differs between the minimal input (defaults) and the explicit defaults" >&2
        rc=1
    fi
    if [ -d save_${tag}_serial ]; then
        if diff -r save_${tag} save_${tag}_serial > /dev/null; then
            echo "=== config $tag: save/ is bit-identical to the serial run ==="
        else
            echo "警告: config $tag の save/ が逐次ビルドと不一致(-Ofast の fast-math ビルド間差の" >&2
            echo "      可能性。ビット検証は -O2 厳密数学で行うこと — §28.3)" >&2
        fi
    fi
done
ndef=$(grep -c "(default)" Screen_mpi.log)
echo "=== $ndef '(default)' lines were printed (expected 18) ==="
[ "$ndef" -eq 18 ] || { echo "FAIL: unexpected number of '(default)' lines" >&2; rc=1; }
if [ $rc -eq 0 ]; then
    echo "=== gwdefault MPI verification PASS ==="
else
    echo "=== gwdefault MPI verification FAIL ===" >&2
fi
exit $rc
