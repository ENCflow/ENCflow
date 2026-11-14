#!/bin/bash
# 補足節(解像度の影響・4 近傍との比較・移流項の扱い)の図 figs/supp_*.png を再生成する。
#   使い方: ./Fig_supp.sh   (要 gnuplot。実行ファイルは make で用意)
# Fig_chichibu.sh とは別にしてある: 50 m 格子(1120×600、dt 0.75 s)のケースを
# 7 本含むため、4 コアのノート PC で 3〜4 時間かかる。
# param_supp_{200m,100m,50m}.txt(Step 3 と同じ既定の設定。空の &list_enc を持つ)を
# ENC(そのまま)と 4 近傍(&list_enc に p_diagratio = 0.0 を追記)で実行し、
# 結果を result_supp_<解像度>[_4nb] に退避してから
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
    sed -e '/^&list_enc/a\  p_diagratio = 0.0        ! 対角成分ゼロ = 4近傍相当' "param_supp_$r.txt" > "wrk_supp_param_${r}_4nb.txt"
    grep -q 'p_diagratio = 0.0' "wrk_supp_param_${r}_4nb.txt"
    rm -rf result
    ./encflow "wrk_supp_param_${r}_4nb.txt"
    mv result "result_supp_${r}_4nb"
  fi
done

# --- 河道幅を 50 m に揃えたサブグリッド河道(壁なし)。幅データは test/chichibu/ のもの
#     (落水線に載せ直した河道マスクのセルに一様 50 m)。
#     50 m 格子は河道セル自体が 50 m 幅なので、W = 50 m の指定が解像表現に退化する
#     ことの確認用(結果 1 の末尾) ---
for r in 200m 100m 50m; do
  if [ ! -d "result_supp_${r}_w50" ]; then
    case $r in
      200m) wdir="../../test/chichibu/data_chichibu_200m"; wfile="width200_50_flowline.txt" ;;
      100m) wdir="../../test/chichibu/data_chichibu";      wfile="width_chichibu50_flowline.txt" ;;
      50m)  wdir="../../test/chichibu/data_chichibu_50m";  wfile="width50_50_flowline.txt" ;;
    esac
    sed -e '/dir_data/i\  fn_channel = "-"           ! 河道条件設定ファイル' \
        -e "s#^  dir_data = \".*\"#  dir_data = \"$wdir\"#" "param_supp_$r.txt" > "wrk_supp_param_${r}_w50.txt"
    printf '\n&list_channel\n  fn_width = "%s"   ! 河道幅 (m): 河道セルに一様 50 m(壁なし=自然河岸)\n/\n' "$wfile" >> "wrk_supp_param_${r}_w50.txt"
    # 200 m は流れが幅 50 m の河道に集まり、dt 6 s では 1.5 時間目に Courant 数 1 を超える
    # (流速 29 m/s)ので dt = 4 s にする
    if [ "$r" = 200m ]; then sed -i 's/^  dt = 6.0 /  dt = 4.0 /' "wrk_supp_param_${r}_w50.txt"; grep -q 'dt = 4.0' "wrk_supp_param_${r}_w50.txt"; fi
    rm -rf result
    ./encflow "wrk_supp_param_${r}_w50.txt"
    mv result "result_supp_${r}_w50"
  fi
done

# --- 旧移流スキーム(f_advection_scheme = 1)と、移流項なしの拡散波(局所慣性
#     方程式。f_govequation = 1)。解像度依存の比較(補足の「結果 3」)。
#     200 m → 100 m → 50 m の順(50 m は 1 本 10〜60 分)。移流項なしの 50 m は、
#     dt 0.75 s でも完走するが、慣性の制限がなく、1 時間目に段差で流速が 59 m/s、
#     Courant 数が 0.98 に達して余裕がないので dt = 0.4 s にする ---
for r in 200m 100m 50m; do
  if [ ! -d "result_supp_${r}_s1" ]; then
    sed -e '/^&list_enc/a\  f_advection_scheme = 1   ! 旧移流スキーム(非保存形・風上重み)' "param_supp_$r.txt" > "wrk_supp_param_${r}_s1.txt"
    grep -q 'f_advection_scheme = 1' "wrk_supp_param_${r}_s1.txt"
    rm -rf result
    # 50 m は、3 時間目(流出口の湛水が 25〜27 m の頃)に流速が 64 m/s、Courant 数が 1.00 に達して、
    # 安定の限界にある(dt を 0.5 s に縮めると、同じ頃に流速が 93 m/s まで発散して止まる = 時間刻みでは
    # なくスキームの不安定)。環境によっては途中で止まるので、止まっても続ける(図の曲線が途中で切れる)
    ./encflow "wrk_supp_param_${r}_s1.txt" || echo "(s1 $r: 途中停止)"
    mv result "result_supp_${r}_s1"
  fi
  if [ ! -d "result_supp_${r}_s1u" ]; then      # スキーム 1 + 風上化指数 0.1(test/chichibu と同じ値)
    sed -e '/^&list_enc/a\  f_advection_scheme = 1   ! 旧移流スキーム' \
        -e '/^&list_enc/a\  p_adv_upwind_index = 0.1 ! 風上化指数(既定 0.5 より弱い風上化)' "param_supp_$r.txt" > "wrk_supp_param_${r}_s1u.txt"
    grep -q 'p_adv_upwind_index = 0.1' "wrk_supp_param_${r}_s1u.txt"
    # 風上化 0.1 は数値粘性が小さく、100 m は減水期(dt 1.5 s で 4.1 h、1.0 s で 3.9 h。流出口の湛水が
    # 33 m の頃)に、50 m は立ち上がり期(63 分)に、流速が発散して Courant 数 1 を超えて停止する
    # (時間刻みを縮めても止まる)。100 m は dt 1.0 s、50 m は 0.5 s で回す
    case $r in
      100m) sed -i 's/^  dt = 1.5 /  dt = 1.0 /' "wrk_supp_param_${r}_s1u.txt"; grep -q 'dt = 1.0' "wrk_supp_param_${r}_s1u.txt" ;;
      50m)  sed -i 's/^  dt = 0.75 /  dt = 0.5  /' "wrk_supp_param_${r}_s1u.txt"; grep -q 'dt = 0.5' "wrk_supp_param_${r}_s1u.txt" ;;
    esac
    rm -rf result
    # 途中で止まっても、そこまでの結果をそのまま使う(100 m のピーク 135 分は停止の前。50 m は
    # ピークに届かない。図では曲線が途中で切れる)
    ./encflow "wrk_supp_param_${r}_s1u.txt" || echo "(s1u $r: 途中停止)"
    mv result "result_supp_${r}_s1u"
  fi
  if [ ! -d "result_supp_${r}_s1f" ]; then      # スキーム 1 + 風上化指数 1.0(完全風上。上限値)
    sed -e '/^&list_enc/a\  f_advection_scheme = 1   ! 旧移流スキーム' \
        -e '/^&list_enc/a\  p_adv_upwind_index = 1.0 ! 風上化指数(完全風上。既定 0.5 より強い風上化)' "param_supp_$r.txt" > "wrk_supp_param_${r}_s1f.txt"
    grep -q 'p_adv_upwind_index = 1.0' "wrk_supp_param_${r}_s1f.txt"
    rm -rf result
    ./encflow "wrk_supp_param_${r}_s1f.txt"
    mv result "result_supp_${r}_s1f"
  fi
  if [ ! -d "result_supp_${r}_noadv" ]; then
    sed -e 's/f_govequation = 0/f_govequation = 1/' "param_supp_$r.txt" > "wrk_supp_param_${r}_noadv.txt"
    if [ "$r" = 50m ]; then sed -i 's/^  dt = 0.75 /  dt = 0.4  /' "wrk_supp_param_${r}_noadv.txt"; grep -q 'dt = 0.4' "wrk_supp_param_${r}_noadv.txt"; fi
    grep -q 'f_govequation = 1' "wrk_supp_param_${r}_noadv.txt"
    rm -rf result
    ./encflow "wrk_supp_param_${r}_noadv.txt"
    mv result "result_supp_${r}_noadv"
  fi
done

gnuplot Fig_supp.plt
gnuplot en/Fig_supp.plt
echo "generated figures figs/supp_*.png and en/figs/supp_*.png"
