#!/bin/bash
# coastal_drain: MPI 実行 + 回帰テスト(海抜下ポルダーの排水)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
exec ../Scripts/Run_case.sh mpi "$@"
