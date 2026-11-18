#!/bin/bash
# 補足節(解像度の影響・4 近傍との比較・河床を整えた効果・移流項の扱い・河道の粗度)の図
# figs/supp_*.png を再生成する。
#   使い方: ./Fig_supp.sh   (要 gnuplot。実行ファイルは make で用意)
# Fig_chichibu.sh とは別にしてある: 50 m 格子(1120×600、dt 0.75 s)のケースを
# 7 本含むため、4 コアのノート PC で 5〜6 時間かかる(200 m・100 m の 22 本は、始めの 1 時間あまり)。
# param_supp_{200m,100m,50m}.txt(Step 3 の設定に Step 5 の流域出口を足したもの。
# 空の &list_enc を持つ)を、解像度ごとに次の変種で実行し、結果を
# result_supp_<解像度>[_<変種>] に退避してから Fig_supp.plt で描画する。
#   (なし)  既定の設定(ENC。8 方向交換)
#   4nb      4 近傍(&list_enc に p_diagratio = 0.0 を追記)
#   w50      河道幅を 50 m に揃えたサブグリッド河道
#   filled   地盤高を、河床を整える前の窪地除去済みの標高に戻したもの(200 m・100 m だけ)
#   filled_noadv  その標高で、移流項なし(200 m・100 m だけ。段々の河床での移流項の働きを見る)
#   s1u・s1・s1f  旧移流スキーム(風上化指数 0.1・0.5・1.0)
#   noadv    移流項なし(拡散波)
#   n02・n02_noadv  河道の粗度を 0.02 にしたものと、その移流項なし(200 m・100 m だけ)
# 200 m → 100 m → 50 m の順に回す。計算済みの result_supp_* があれば計算を飛ばす
# (全て計算し直す場合は rm -rf result_supp_* してから実行)。
# 100 m・50 m の地形データは test/chichibu/ のものを参照する。
set -eu

mkdir -p figs en/figs
rm -f wrk_supp_*

for r in 200m 100m 50m; do
  case $r in
    200m) wdir="../../test/chichibu/data_chichibu_200m"; wfile="width200_50_flowline.txt"
          zcond="Chichibu_200m_cond.txt";  zfilled="Chichibu_200m_filled.txt" ;;
    100m) wdir="../../test/chichibu/data_chichibu";      wfile="width_chichibu50_flowline.txt"
          zcond="Chichibu_100m_cond.txt";  zfilled="Chichibu_100m_filled2.txt" ;;
    50m)  wdir="../../test/chichibu/data_chichibu_50m";  wfile="width50_50_flowline.txt"
          zcond="Chichibu_50m_cond.txt";   zfilled="" ;;
  esac

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

  # --- 河道幅を 50 m に揃えたサブグリッド河道(壁なし)。幅データは test/chichibu/ のもの
  #     (落水線に載せ直した河道マスクのセルに一様 50 m)。
  #     50 m 格子は河道セル自体が 50 m 幅なので、W = 50 m の指定が解像表現に退化する
  #     ことの確認用(結果 1 の末尾) ---
  if [ ! -d "result_supp_${r}_w50" ]; then
    sed -e '/dir_data/i\  fn_channel = "-"           ! 河道条件設定ファイル' \
        -e "s#^  dir_data = \".*\"#  dir_data = \"$wdir\"#" "param_supp_$r.txt" > "wrk_supp_param_${r}_w50.txt"
    printf '\n&list_channel\n  fn_width = "%s"   ! 河道幅 (m): 河道セルに一様 50 m(壁なし=自然河岸)\n/\n' "$wfile" >> "wrk_supp_param_${r}_w50.txt"
    grep -q "dir_data = \"$wdir\"" "wrk_supp_param_${r}_w50.txt"
    # 200 m は流れが幅 50 m の河道に集まって速くなるので、dt = 4 s にする
    if [ "$r" = 200m ]; then sed -i 's/^  dt = 6.0 /  dt = 4.0 /' "wrk_supp_param_${r}_w50.txt"; grep -q 'dt = 4.0' "wrk_supp_param_${r}_w50.txt"; fi
    rm -rf result
    ./encflow "wrk_supp_param_${r}_w50.txt"
    mv result "result_supp_${r}_w50"
  fi

  # --- 河床を整える前の標高(窪地除去済み。Step 1 の標高)。河床を整えた効果を見る比較用
  #     (200 m・100 m だけ。ほかの設定は同じ) ---
  if [ -n "$zfilled" ] && [ ! -d "result_supp_${r}_filled" ]; then
    sed -e "s#fn_z = \"$zcond\"#fn_z = \"$zfilled\"#" "param_supp_$r.txt" > "wrk_supp_param_${r}_filled.txt"
    grep -q "fn_z = \"$zfilled\"" "wrk_supp_param_${r}_filled.txt"
    rm -rf result
    ./encflow "wrk_supp_param_${r}_filled.txt"
    mv result "result_supp_${r}_filled"
  fi

  # --- 旧移流スキーム(f_advection_scheme = 1)と、移流項なしの拡散波(局所慣性
  #     方程式。f_govequation = 1)。解像度依存の比較(補足の「結果 3」)。
  #     スキーム 1 は、急な段差や深い静水で流速が発散して止まることがあるので、
  #     止まっても続ける(止まるまでの結果を使う。図では曲線が途中で切れる) ---
  if [ ! -d "result_supp_${r}_s1" ]; then       # スキーム 1(風上化指数は既定の 0.5)
    sed -e '/^&list_enc/a\  f_advection_scheme = 1   ! 旧移流スキーム(非保存形・風上重み)' "param_supp_$r.txt" > "wrk_supp_param_${r}_s1.txt"
    grep -q 'f_advection_scheme = 1' "wrk_supp_param_${r}_s1.txt"
    rm -rf result
    ./encflow "wrk_supp_param_${r}_s1.txt" || echo "(s1 $r: 途中停止)"
    mv result "result_supp_${r}_s1"
  fi
  if [ ! -d "result_supp_${r}_s1u" ]; then      # スキーム 1 + 風上化指数 0.1(test/chichibu と同じ値)
    sed -e '/^&list_enc/a\  f_advection_scheme = 1   ! 旧移流スキーム' \
        -e '/^&list_enc/a\  p_adv_upwind_index = 0.1 ! 風上化指数(既定 0.5 より弱い風上化)' "param_supp_$r.txt" > "wrk_supp_param_${r}_s1u.txt"
    grep -q 'p_adv_upwind_index = 0.1' "wrk_supp_param_${r}_s1u.txt"
    # 風上化 0.1 の 50 m は、流速が大きくなって、dt 0.75 s では Courant 数が 1 を超えて止まるので、dt = 0.5 s にする
    if [ "$r" = 50m ]; then sed -i 's/^  dt = 0.75 /  dt = 0.5  /' "wrk_supp_param_${r}_s1u.txt"; grep -q 'dt = 0.5' "wrk_supp_param_${r}_s1u.txt"; fi
    rm -rf result
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
  if [ -n "$zfilled" ] && [ ! -d "result_supp_${r}_filled_noadv" ]; then   # 河床を整える前の標高で、移流項なし
    sed -e "s#fn_z = \"$zcond\"#fn_z = \"$zfilled\"#" -e 's/f_govequation = 0/f_govequation = 1/' "param_supp_$r.txt" > "wrk_supp_param_${r}_filled_noadv.txt"
    grep -q "fn_z = \"$zfilled\"" "wrk_supp_param_${r}_filled_noadv.txt"
    grep -q 'f_govequation = 1' "wrk_supp_param_${r}_filled_noadv.txt"
    rm -rf result
    ./encflow "wrk_supp_param_${r}_filled_noadv.txt"
    mv result "result_supp_${r}_filled_noadv"
  fi
  if [ ! -d "result_supp_${r}_noadv" ]; then    # 移流項なし(拡散波)
    sed -e 's/f_govequation = 0/f_govequation = 1/' "param_supp_$r.txt" > "wrk_supp_param_${r}_noadv.txt"
    grep -q 'f_govequation = 1' "wrk_supp_param_${r}_noadv.txt"
    # 移流項なしの 50 m は、慣性の制限がなく、流速が大きくなるので、余裕を見て dt = 0.5 s にする
    if [ "$r" = 50m ]; then sed -i 's/^  dt = 0.75 /  dt = 0.5  /' "wrk_supp_param_${r}_noadv.txt"; grep -q 'dt = 0.5' "wrk_supp_param_${r}_noadv.txt"; fi
    rm -rf result
    ./encflow "wrk_supp_param_${r}_noadv.txt"
    mv result "result_supp_${r}_noadv"
  fi

  # --- 河道の粗度を 0.02 にした計算(スキーム 3 と、移流項なし)。移流項の働きが、河道の粗度で
  #     どう変わるかを見る(補足の「結果 3」。200 m・100 m だけ)。流れが速くなるので、
  #     dt を、200 m は 4 s、100 m は 1.0 s にする ---
  if [ "$r" != 50m ]; then
    case $r in
      200m) dtn='s/^  dt = 6.0 /  dt = 4.0 /'; dtg='dt = 4.0' ;;
      100m) dtn='s/^  dt = 1.5 /  dt = 1.0 /'; dtg='dt = 1.0' ;;
    esac
    if [ ! -d "result_supp_${r}_n02" ]; then
      sed -e 's/rn0_rw = 0.04 /rn0_rw = 0.02 /' -e "$dtn" "param_supp_$r.txt" > "wrk_supp_param_${r}_n02.txt"
      grep -q 'rn0_rw = 0.02' "wrk_supp_param_${r}_n02.txt"
      grep -q "$dtg" "wrk_supp_param_${r}_n02.txt"
      rm -rf result
      ./encflow "wrk_supp_param_${r}_n02.txt"
      mv result "result_supp_${r}_n02"
    fi
    if [ ! -d "result_supp_${r}_n02_noadv" ]; then
      sed -e 's/rn0_rw = 0.04 /rn0_rw = 0.02 /' -e 's/f_govequation = 0/f_govequation = 1/' -e "$dtn" "param_supp_$r.txt" > "wrk_supp_param_${r}_n02_noadv.txt"
      grep -q 'rn0_rw = 0.02' "wrk_supp_param_${r}_n02_noadv.txt"
      grep -q 'f_govequation = 1' "wrk_supp_param_${r}_n02_noadv.txt"
      grep -q "$dtg" "wrk_supp_param_${r}_n02_noadv.txt"
      rm -rf result
      ./encflow "wrk_supp_param_${r}_n02_noadv.txt"
      mv result "result_supp_${r}_n02_noadv"
    fi
  fi
done

gnuplot Fig_supp.plt
gnuplot en/Fig_supp.plt
echo "generated figures figs/supp_*.png and en/figs/supp_*.png"
