#!/bin/bash
# nest_identity: 比 1:1 自己ネスト恒等テスト(MPI)。 ./Run_MPI.sh [N](既定 2)
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
exec ./Run_nest.sh mpi "$@"
