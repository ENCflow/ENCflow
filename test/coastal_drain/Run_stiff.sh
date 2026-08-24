#!/bin/bash
# coastal_drain: 硬い変種(gwc_slot_sy=0.002 → サブサイクル N=2)の逐次実行
#   reference 機構は使わない(検算は解析平衡: 全管路セル
#   hgc = cap + (0.5 − (−0.8))·slot_sy = 0.1026 と、np 一致は
#   Run_MPI.sh 同様の手動実行で確認する)
time ./encflow param_stiff.txt | tee Screen_stiff.log
