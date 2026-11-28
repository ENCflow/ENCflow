#!/bin/bash
# saltledger: 全ケースの判定(Run.sh と Run_MPI.sh が呼ぶ)。結果ディレクトリは result_<ケース名>
#   ./Check_cases.sh
sdir=$(dirname "$(readlink -f "$0")")
C="python3 $sdir/Check_saltledger.py"
rc=0
# --- 台帳の閉合(全ケース)---
for c in sea evap pump0 pump1 pump2 xfer exin exout gwsea; do
    $C close result_$c || rc=1
done
# --- 経路ごとの値 ---
$C pos   result_sea in_sea_m3 out_sea_m3 || rc=1                 # 海からの流入と、海への流出
$C evap  result_evap 10000 0.5 2.7777777777777778e-5 10 7200 || rc=1   # 蒸発で縮んだ分が lost_surf
$C pump  result_pump0 3200 640 0 320 || rc=1                     # 運ばない: 取水側に残り、水深を下回った分が消える
$C pump  result_pump1 3200 0 960 0 || rc=1                       # 底層から先に: 塩水 0.3 m がすべて出る
$C pump  result_pump2 3200 192 768 0 || rc=1                     # 混合比: 汲んだ 0.8 m の 3 割
$C xfer  result_xfer 9 8 10 1 960 4 6 0.3 || rc=1                # 域内の転送: 西 → 東、合計は不変
$C exin  result_exin 6400 1920 640 || rc=1                       # 浸透の配分: 塩水 0.3 m が地下へ
$C pos   result_exout seep_m3 infil_m3 || rc=1                   # 湧出の配分と、窪地からの再浸透
$C pos   result_gwsea in_sea_gw_m3 || rc=1                       # 地下の海側境界
$C well  result_gwsea 0.2 || rc=1                                # 井戸が汲んだ水(塩水だけの帯水層)は揚水に数える
exit $rc
