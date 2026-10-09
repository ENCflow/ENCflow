#!/bin/bash
# nest_twin: 複数インスタンス交互実行 == 単独実行 のビット一致検査(MPI)
#   ./Run_MPI.sh [N]     (既定 N=2)
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
exec ./Run_twin.sh mpi "$@"
