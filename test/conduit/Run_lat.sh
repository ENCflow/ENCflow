#!/bin/bash
# conduit: 模式実験 B(局所流入・sqrt 側方拡散・漏水)の逐次実行 + 自己検定
#   reference 機構は使わない(np 一致検証は Run_lat_MPI.sh の出力と
#   result_lat/Log.txt を直接 diff する)。実行のあと Check_conduit.py B で
#   質量保存・分布の対称性・中心の被圧を確かめる
export PARAM=param_lat.txt
export RESDIR=result_lat
set -o pipefail
time ./encflow param_lat.txt | tee Screen_lat.log || exit 1
echo ""
python3 ./Check_conduit.py B result_lat || exit 1
