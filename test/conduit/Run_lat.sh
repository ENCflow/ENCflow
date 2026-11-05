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

# 模式実験 C(param_latgw.txt): B に土層の側方流(gw_diagratio = 1/3)を足す。管路層の
#   通過幅は gwc_diagratio(既定)のまま = 管路層の安定条件の表示が B と一致する(§95)
time ./encflow param_latgw.txt | tee Screen_latgw.log || exit 1
echo ""
python3 ./Check_conduit.py B result_latgw || exit 1
a=$(grep "gwflow_conduit: dt limit" Screen_lat.log)
b=$(grep "gwflow_conduit: dt limit" Screen_latgw.log)
if [ -n "$a" ] && [ "$a" = "$b" ]; then
    echo "=== conduit C: the conduit edge conductances do not depend on gw_diagratio (stability line identical to B) PASS ==="
else
    echo "FAIL: conduit C: the conduit stability line differs from B (B: '$a' / C: '$b')" >&2
    exit 1
fi
