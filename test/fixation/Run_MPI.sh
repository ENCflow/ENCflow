#!/bin/bash
# fixation: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" z > zinit.txt
python3 "$sdir/make_init.py" h > hinit.txt

export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_off.txt | tee Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_on.txt | tee -a Screen.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_weak.txt | tee -a Screen.log || exit 1
rm -rf save_rt
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_rt1.txt | tee -a Screen.log || exit 1
rm -rf save_rt1 && cp -r save_rt save_rt1       # 前半(t = 600 s)の保存値は成長則の検定が読む
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_rt2.txt | tee -a Screen.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_fixation.py" || rc=1
for f in state.dat geomorph_fixation.dat; do
    if cmp -s save_rt/$f save_on/$f; then
        echo "=== restart continuation: $f is bit-identical to the straight run ==="
    else
        echo "FAIL: restart continuation differs from the straight run: $f" >&2
        rc=1
    fi
done
for c in off on weak; do
    if [ -d save_${c}_serial ]; then
        for f in state.dat geomorph_fixation.dat; do
            [ -e save_$c/$f ] || continue
            if cmp -s save_$c/$f save_${c}_serial/$f; then
                echo "=== $c: $f is bit-identical to the serial result ==="
            else
                echo "MISMATCH: save_$c/$f != save_${c}_serial/$f" >&2
                rc=1
            fi
        done
    fi
done
exit $rc
