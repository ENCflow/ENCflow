#!/bin/bash
# conduit: 模式実験 B(局所流入・sqrt 側方拡散・漏水)の逐次実行
#   reference 機構は使わない(np 一致検証は Run_lat_MPI.sh の出力と
#   result_lat/Log.txt を直接 diff する)
export PARAM=param_lat.txt
export RESDIR=result_lat
time ./encflow param_lat.txt | tee Screen_lat.log
