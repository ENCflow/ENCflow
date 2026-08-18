#!/bin/bash
# conduit: 模式実験 B の MPI 実行(np 指定。既定 2)
#   逐次との比較:  ./Run_lat.sh && mv result_lat/Log.txt Log_serial.txt
#                  ./Run_lat_MPI.sh 2 && diff Log_serial.txt result_lat/Log.txt
NP=${1:-2}
export ENCFLOW_EXPECT_NP="$NP"
time mpirun -np "$NP" --bind-to none ./encflow_mpi param_lat.txt | tee Screen_lat.log
