#!/bin/bash
# 補足節(解像度の影響と 4 近傍との比較)の図 figs/supp_*.png を再生成する。
#   使い方: ./Fig_supp.sh   (要 gnuplot。実行ファイルは make で用意)
# Fig_chichibu.sh とは別にしてある: 50 m 格子(1120×600、dt 1.5 s)のケースを
# 2 本含むため(dt 0.75 s)、4 コアのノート PC で 1 時間前後かかる。
# param_supp_{200m,100m,50m}.txt を ENC(そのまま)と 4 近傍(fn_enc を足して
# p_diagratio = 0.0)で実行し、結果を result_supp_<解像度>[_4nb] に退避してから
# Fig_supp.plt で描画する。河道幅を 50 m に揃えた 200 m・100 m のケース
# (result_supp_*_w50)も実行する。計算済みの result_supp_* があれば計算を飛ばす
# (全て計算し直す場合は rm -rf result_supp_* してから実行)。
# 100 m・50 m の地形データは test/chichibu/ のものを参照する。
set -eu

mkdir -p figs en/figs
rm -f wrk_supp_*

for r in 200m 100m 50m; do
  # --- ENC(8 方向交換) ---
  if [ ! -d "result_supp_$r" ]; then
    rm -rf result
    ./encflow "param_supp_$r.txt"
    mv result "result_supp_$r"
  fi
  # --- 4 近傍(対角成分ゼロ) ---
  if [ ! -d "result_supp_${r}_4nb" ]; then
    sed -e '/dir_data/i\  fn_enc     = "-"           ! ENC条件設定ファイル' "param_supp_$r.txt" > "wrk_supp_param_${r}_4nb.txt"
    printf '\n&list_enc\n  p_diagratio = 0.0        ! 対角成分ゼロ = 4近傍相当\n/\n' >> "wrk_supp_param_${r}_4nb.txt"
    rm -rf result
    ./encflow "wrk_supp_param_${r}_4nb.txt"
    mv result "result_supp_${r}_4nb"
  fi
done

# --- 河道幅を 50 m に揃えたサブグリッド河道(壁なし)。200 m・100 m のみ
#     (50 m 格子は河道セル自体が 50 m 幅)。幅データは test/chichibu/ のもの ---
for r in 200m 100m; do
  if [ ! -d "result_supp_${r}_w50" ]; then
    case $r in
      200m) wdir="../../test/chichibu/data_chichibu_200m"; wfile="width200_50.txt" ;;
      100m) wdir="../../test/chichibu/data_chichibu";      wfile="width_chichibu50.txt" ;;
    esac
    sed -e '/dir_data/i\  fn_channel = "-"           ! 河道条件設定ファイル' \
        -e "s#^  dir_data = \".*\"#  dir_data = \"$wdir\"#" "param_supp_$r.txt" > "wrk_supp_param_${r}_w50.txt"
    printf '\n&list_channel\n  fn_width = "%s"   ! 河道幅 (m): 河道セルに一様 50 m(壁なし=自然河岸)\n/\n' "$wfile" >> "wrk_supp_param_${r}_w50.txt"
    rm -rf result
    ./encflow "wrk_supp_param_${r}_w50.txt"
    mv result "result_supp_${r}_w50"
  fi
done

gnuplot Fig_supp.plt
gnuplot en/Fig_supp.plt
echo "generated figures figs/supp_*.png and en/figs/supp_*.png"
