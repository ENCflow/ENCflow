#!/bin/bash
# splash: MPI 実行 + 回帰テスト(乾式斜面侵食 f_splash)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は ULP=0(CLAUDE.md 検証規律)
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
exec ../Scripts/Run_case.sh mpi "$@"
