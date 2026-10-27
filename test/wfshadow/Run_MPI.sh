#!/bin/bash
# wfshadow: MPI 実行 + 回帰テスト + 検定(沿岸の波浪場 fn_wavefield の 2 次元。developer.md §88)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は Log.txt・wavefield.csv・Wh0001.txt を ULP=0(CLAUDE.md
# 検証規律。防波堤の陰・菱形の壁・側方 Neumann の辺がランク境界をまたぐ)
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
export FILES=${FILES:-"Log.txt wavefield.csv Wh0001.txt"}
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

python3 Check_wfshadow.py base result || exit 1

np=2
for a in "$@"; do case $a in -u) ;; *) np=$a ;; esac; done
rm -rf result_aligned
mpirun -np "$np" $MPIRUN_OPTS ./encflow_mpi param_aligned.txt > Screen_aligned.log 2>&1 \
    || { echo "ERROR: param_aligned run failed" >&2; exit 1; }
python3 Check_wfshadow.py aligned result_aligned || exit 1

echo "=== wfshadow verification PASS ==="
