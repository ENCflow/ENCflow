#!/bin/bash
# sewer_wq: MPI 実行 + 回帰テスト(下水噴出の衛生リスク)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)
export FILES="Log.txt wq.csv"
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
exec ../Scripts/Run_case.sh mpi "$@"
