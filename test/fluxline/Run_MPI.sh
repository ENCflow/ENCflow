#!/bin/bash
# fluxline: MPI 実行 + 検定(流量測線の角度掃引。developer.md §24.3)
#   ./Run_MPI.sh [ランク数]
# 逐次(Run.sh)と同じ検定を同じ並列数で回し、逐次の Run.sh が残した result_*_serial/ と
# 測線の CSV・最終の水深と流速の分布をバイト比較する(測線はどれもランク境界をまたぐ)。
# 21 行なので 2 行/ランクの制約から np <= 10
sdir=$(dirname "$(readlink -f "$0")")
"$sdir/../Scripts/Check_mode.sh" mpi || exit 1
export MPIRUN_OPTS=${MPIRUN_OPTS:-"--bind-to none"}
python3 "$sdir/make_init.py"

np=2
for a in "$@"; do np=$a; done

rc=0
for tag in stair xy; do
    rm -rf result_$tag
    ENCFLOW_EXPECT_NP="$np" mpirun -np "$np" $MPIRUN_OPTS ./encflow_mpi param_$tag.txt > Screen_$tag.log 2>&1 \
        || { echo "ERROR: param_$tag.txt (np=$np) run failed" >&2; exit 1; }
    python3 Check_fluxline.py $tag || rc=1
    if [ -d result_${tag}_serial ]; then
        same=1
        for f in result_${tag}_serial/fluxes/flux*.csv result_${tag}_serial/H9998.bil result_${tag}_serial/V9998.bil; do
            g=result_$tag/${f#result_${tag}_serial/}
            cmp -s "$f" "$g" || { echo "MISMATCH: $g differs from the serial run" >&2; same=0; rc=1; }
        done
        [ $same -eq 1 ] && echo "=== result_$tag (flux CSVs, H9998, V9998) is bit-identical to the serial run ==="
    fi
done

if [ $rc -eq 0 ]; then
    echo "=== fluxline MPI verification PASS (np=$np) ==="
else
    echo "=== fluxline MPI verification FAIL (np=$np) ===" >&2
fi
exit $rc
