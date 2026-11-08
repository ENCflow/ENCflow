#!/bin/bash
# stg: MPI 版の確認
#   ./Run_MPI.sh [N](既定 2)
# STG は MPI の 1 ランクでだけ動く(帯の境界でハロを交換しない。developer.md §7)。N = 1 では
# Run.sh と同じ判定(Check_stg.py の連続式の保存と、領域マスクで止まること)をし、逐次の Log.txt
# (Run.sh が result_serial/ に残す)があればバイト一致も確かめる。N >= 2 では、初期化で明示的に
# 止まることを確かめる
NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh mpi || exit 1

export ENCFLOW_EXPECT_NP="$NP"
python3 "$sdir/make_init.py" || exit 1
rm -rf result_stg result_stgmask
if [ "$NP" -gt 1 ]; then
    if mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi p_stg.txt > Screen_stg.log 2>&1; then
        echo "  FAIL p_stg ran to the end with np=$NP; STG must stop with more than one process" >&2
        exit 1
    fi
    grep -q "runs with one MPI process only" Screen_stg.log \
        || { echo "  FAIL p_stg stopped without the expected message (see Screen_stg.log)" >&2; exit 1; }
    echo "  ok   STG stops at initialization with np=$NP (one MPI process only)"
    echo "=== stg verification PASS (np=$NP) ==="
    exit 0
fi
mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi p_stg.txt > Screen_stg.log 2>&1 \
    || { echo "ERROR: p_stg run failed (see Screen_stg.log)" >&2; exit 1; }
python3 "$sdir/Check_stg.py" result_stg || exit 1

if mpirun -np "$NP" $MPIRUN_OPTS ./encflow_mpi p_stgmask.txt > Screen_stgmask.log 2>&1; then
    echo "  FAIL p_stgmask ran to the end; STG must stop on a domain mask" >&2
    exit 1
fi
grep -q "not supported with STG" Screen_stgmask.log \
    || { echo "  FAIL p_stgmask stopped without the expected message (see Screen_stgmask.log)" >&2; exit 1; }
echo "  ok   p_stgmask stops at initialization (np=$NP)"

if [ -d result_serial ]; then
    cmp -s result_stg/Log.txt result_serial/Log_stg.txt \
        || { echo "ERROR: result_stg/Log.txt differs from the serial run" >&2; exit 1; }
    echo "  ok   Log.txt identical to the serial run (np=$NP)"
fi
echo "=== stg verification PASS (np=$NP) ==="
