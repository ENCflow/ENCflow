#!/bin/bash
# dbmix: MPI 実行(N ランク)+ 検定 + 逐次の保存とのビット一致の確認(developer.md §139)
#   ./Run_MPI.sh [N](既定 2)
# 先に ./Run.sh(逐次)を回して save_*_serial を作っておくと、保存をバイト比較する

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

python3 "$sdir/make_init.py" || exit 1
CASES=$(python3 "$sdir/make_init.py" list)
export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
for c in $CASES; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi p_$c.txt 2>&1 | tee screen_$c.log || exit 1
done
rm -rf save_rt save_alt2 save_alt3
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi p_rt1.txt 2>&1 | tee screen_rt1.log || exit 1
cp -r save_rt save_alt2
cp -r save_rt save_alt3
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi p_rt2.txt 2>&1 | tee screen_rt2.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi p_alt2.txt 2>&1 | tee screen_alt2.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi p_alt3.txt 2>&1 | tee screen_alt3.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_dbmix.py" || rc=1
for f in state.dat geomorph_bedmix.dat swflow_enc.dat; do
    cmp -s save_rt/$f save_w3/$f || { echo "FAIL: restart continuation (rt) differs: $f" >&2; rc=1; }
done
nser=0
for c in $CASES rt alt2 alt3; do
    if [ -d save_${c}_serial ]; then
        nser=$((nser + 1))
        for f in state.dat geomorph_bedmix.dat; do
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
[ $nser -eq 0 ] && echo "(no save_*_serial: run ./Run.sh first to compare with the serial results)"

if [ $rc -eq 0 ]; then
    echo "=== dbmix verification PASS (np=$NP) ==="
else
    echo "=== dbmix verification FAIL (np=$NP) ===" >&2
fi
exit $rc
