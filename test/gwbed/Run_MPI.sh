#!/bin/bash
# gwbed: MPI 実行 + 回帰テスト + 解析検定(河床交換能 f_gwbed)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)。行は 11(領域外行
# 2 を含む)なので 2 行/ランクの制約から np <= 5
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=6
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

python3 Check_gwbed.py gain result || exit 1

echo "=== gwbed verification PASS ==="
