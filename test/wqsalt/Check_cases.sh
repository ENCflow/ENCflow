#!/bin/bash
# wqsalt: 全ケースの判定(Run.sh と Run_MPI.sh が呼ぶ)。結果ディレクトリは result_<ケース名>
#   ./Check_cases.sh
sdir=$(dirname "$(readlink -f "$0")")
C="python3 $sdir/Check_wqsalt.py"
rc=0
# --- 水平の混合(wq_diff)---
$C mix     result_mix 81 81 10 0.5 200 1 600 3 || rc=1         # 分散が 2·D·t で増える・等方・質量保存
$C uniform result_mixflow 40 20 100 1 2 3 || rc=1              # 一様な濃度は揺れる水の中でも一様
$C wall    result_mixwall 40 20 10 21 2 || rc=1                # 乾いた尾根は混合を通さない
$C gv      result_mixgv 24 12 10 2 || rc=1                     # 家屋の空隙率の違うセルの間で質量保存・濃度が一様
$C gv      result_mixwd 24 12 10 2 || rc=1                     # サブグリッド河道幅のセルをまたいで質量保存・濃度が一様
# --- 析出と溶解(wq_csat・wq_kdis)---
$C sat     result_sat 10000 0.5 100000 300000 2.7777777777777778e-5 10 0.001 || rc=1   # 蒸発 → 析出 → 干上がり
$C dis     result_dis 10 10 1 300000 0.2 100 30 || rc=1        # 瞬時の溶解(飽和まで・在庫まで)
$C disk    result_disk 300000 0.2 1.0e-4 100 30 200 || rc=1    # 溶解の速さつき(指数の式)
$C inf     result_inf 10 10 1 300000 0.036 100 0.5 2 0.018 360 3 5 8 5 || rc=1   # 浸透水が溶かして地下へ・地下の濃度の上限
# --- 海から入る水の濃度・初期濃度の分布 ---
$C sea     result_sea 24 8 35000 1 2 3 || rc=1
$C c0map   result_c0map 40 20 21 100 300 0 1 2 || rc=1
# --- 可能蒸発散の時系列(f_evmodel = 5)---
$C evts    result_evts 10000 1.0 0.048 || rc=1
exit $rc
