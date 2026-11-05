#!/bin/bash
# conduit: 模式実験 B の MPI 実行(np 指定。既定 2)+ 自己検定(Check_conduit.py B)
#   逐次との比較:  ./Run_lat.sh && mv result_lat/Log.txt Log_serial.txt
#                  ./Run_lat_MPI.sh 2 && diff Log_serial.txt result_lat/Log.txt
NP=${1:-2}
export ENCFLOW_EXPECT_NP="$NP"
set -o pipefail
time mpirun -np "$NP" --bind-to none ./encflow_mpi param_lat.txt | tee Screen_lat.log || exit 1
echo ""
python3 ./Check_conduit.py B result_lat || exit 1

# 模式実験 C(B + 土層の側方流 gw_diagratio = 1/3。管路層の通過幅は gwc_diagratio のまま。§98)
time mpirun -np "$NP" --bind-to none ./encflow_mpi param_latgw.txt | tee Screen_latgw.log || exit 1
echo ""
python3 ./Check_conduit.py B result_latgw || exit 1
a=$(grep "gwflow_conduit: dt limit" Screen_lat.log)
b=$(grep "gwflow_conduit: dt limit" Screen_latgw.log)
if [ -n "$a" ] && [ "$a" = "$b" ]; then
    echo "=== conduit C: stability line identical to B PASS ==="
else
    echo "FAIL: conduit C: the conduit stability line differs from B" >&2
    exit 1
fi
