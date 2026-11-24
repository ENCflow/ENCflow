#!/bin/bash
# bedmix: MPI 実行(N ランク)+ 検定 + 逐次 save とのビット一致確認
#   ./Run_MPI.sh [N](既定 2)

NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

for g in std deep free bank; do
    python3 "$sdir/make_init.py" z $g > zinit_$g.txt
    python3 "$sdir/make_init.py" h $g > hinit_$g.txt
    python3 "$sdir/make_init.py" sd $g > sdinit_$g.txt
done
python3 "$sdir/make_init.py" qbmix > qbmix.txt
python3 "$sdir/make_init.py" rw > rw_suw.txt
python3 "$sdir/make_init.py" width > width_suw.txt

export ENCFLOW_EXPECT_NP="$NP"
CASES="single equal single_te equal_te single_tp equal_tp tpmix1 tpfix1 tpmix tpfix single_su equal_su susp suw armor bcfeed bank qbmix"
set -o pipefail
for c in $CASES hide1 hide2; do
    mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_$c.txt 2>&1 | tee screen_$c.log || exit 1
done
rm -rf save_rt save_surt
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_rt1.txt 2>&1 | tee screen_rt1.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_rt2.txt 2>&1 | tee screen_rt2.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_surt1.txt 2>&1 | tee screen_surt1.log || exit 1
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi param_surt2.txt 2>&1 | tee screen_surt2.log || exit 1
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_bedmix.py" || rc=1
for f in state.dat geomorph_bedmix.dat; do
    cmp -s save_rt/$f save_bank/$f || { echo "FAIL: restart continuation differs: $f" >&2; rc=1; }
    cmp -s save_surt/$f save_susp/$f || { echo "FAIL: restart continuation (surt) differs: $f" >&2; rc=1; }
done
for c in $CASES hide rt surt; do
    if [ -d save_${c}_serial ]; then
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
exit $rc
