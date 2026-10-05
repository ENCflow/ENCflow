#!/bin/bash
# nhbottom: MPI 実行 + 回帰テスト(uplift_mpi ドライバ)
#   ./Run_MPI.sh [ランク数] [-u]
export ULP=1
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
export EXE=uplift
make -s MODE=mpi uplift_mpi || exit 1
exec ../Scripts/Run_case.sh mpi "$@"
