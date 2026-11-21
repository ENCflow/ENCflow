#!/bin/bash
# examples/chichibu_flood の計算をまとめて回す。計算済みの result_* があれば飛ばす
# (全部やり直すときは rm -rf result_* してから実行)。図は python3 plot_results.py で描く。
#   使い方: ./run_cases.sh [200m] [100m] [50m]   (省略時は 3 つとも。200 m → 100 m → 50 m の順)
# 解像度ごとの基本の設定(200 m は param.txt、100 m・50 m は param_100m.txt・param_50m.txt)から、変種の
# 設定を wrk_<解像度>_<変種>.txt に作って実行し、結果を result_<解像度>[_<変種>] に置く。
#   (なし)        基本(ENC。8 方向交換。河床を整えた標高・河道の粗度 0.04・流域出口を開ける)
#   4nb           4 近傍(&list_enc に p_diagratio = 0.0 を追記)
#   w50           河道幅を 50 m に揃えたサブグリッド河道
#   filled        地盤高を、河床を整える前の窪地除去済みの標高に戻したもの(200 m・100 m だけ)
#   filled_noadv  その標高で、移流項なし(200 m・100 m だけ)
#   s1・s1u・s1f  旧移流スキーム(風上化指数 0.5・0.1・1.0)
#   noadv         移流項なし(拡散波 = 局所慣性方程式)
#   n02・n02_noadv 河道の粗度を 0.02 にしたものと、その移流項なし(200 m・100 m だけ)
#   raw・loss・closed  200 m だけ: 窪地除去をしていない元の DEM、降雨遮断と地下浸透、流域出口を閉じる
# 所要時間の目安(4 スレッド): 200 m は 1 本 1 分弱、100 m は 1 本 5〜10 分、50 m は 1 本 1 時間前後。
# 100 m・50 m の地形データは test/chichibu/ のもの、200 m は tutorials/chichibu/ のものを参照する。
set -eu
RES=${*:-200m 100m 50m}
rm -f wrk_*.txt

for r in $RES; do
  case $r in 200m) base=param.txt ;; *) base=param_$r.txt ;; esac
  case $r in
    200m) wdir="../../test/chichibu/data_chichibu_200m"; wfile="width200_50_flowline.txt"
          zcond="Chichibu_200m_cond.txt";  zfilled="Chichibu_200m_filled.txt" ;;
    100m) wdir="../../test/chichibu/data_chichibu";      wfile="width_chichibu50_flowline.txt"
          zcond="Chichibu_100m_cond.txt";  zfilled="Chichibu_100m_filled2.txt" ;;
    50m)  wdir="../../test/chichibu/data_chichibu_50m";  wfile="width50_50_flowline.txt"
          zcond="Chichibu_50m_cond.txt";   zfilled="" ;;
  esac

  # --- ENC(8 方向交換) ---
  if [ ! -d "result_$r" ]; then
    rm -rf result
    ./encflow "$base"
    mv result "result_$r"
  fi

  # --- 4 近傍(対角成分ゼロ) ---
  if [ ! -d "result_${r}_4nb" ]; then
    sed -e '/^&list_enc/a\  p_diagratio = 0.0        ! 対角成分ゼロ = 4近傍相当' "$base" > "wrk_${r}_4nb.txt"
    grep -q 'p_diagratio = 0.0' "wrk_${r}_4nb.txt"
    rm -rf result
    ./encflow "wrk_${r}_4nb.txt"
    mv result "result_${r}_4nb"
  fi

  # --- 河道幅を 50 m に揃えたサブグリッド河道(壁なし)。幅データは test/chichibu/ のもの
  #     (落水線に載せ直した河道マスクのセルに一様 50 m)。
  #     50 m 格子は河道セル自体が 50 m 幅なので、W = 50 m の指定が解像表現に退化する
  #     ことの確認用(README の「河道幅をそろえると」の最後) ---
  if [ ! -d "result_${r}_w50" ]; then
    sed -e '/dir_data/i\  fn_channel = "-"           ! 河道条件設定ファイル' \
        -e "s#^  dir_data = \".*\"#  dir_data = \"$wdir\"#" "$base" > "wrk_${r}_w50.txt"
    printf '\n&list_channel\n  fn_width = "%s"   ! 河道幅 (m): 河道セルに一様 50 m(壁なし=自然河岸)\n/\n' "$wfile" >> "wrk_${r}_w50.txt"
    grep -q "dir_data = \"$wdir\"" "wrk_${r}_w50.txt"
    # 200 m は流れが幅 50 m の河道に集まって速くなるので、dt = 4 s にする
    if [ "$r" = 200m ]; then sed -i 's/^  dt = 6.0 /  dt = 4.0 /' "wrk_${r}_w50.txt"; grep -q 'dt = 4.0' "wrk_${r}_w50.txt"; fi
    rm -rf result
    ./encflow "wrk_${r}_w50.txt"
    mv result "result_${r}_w50"
  fi

  # --- 河床を整える前の標高(窪地除去済み)。河床を整えた効果を見る比較用
  #     (200 m・100 m だけ。ほかの設定は同じ) ---
  if [ -n "$zfilled" ] && [ ! -d "result_${r}_filled" ]; then
    sed -e "s#fn_z = \"$zcond\"#fn_z = \"$zfilled\"#" "$base" > "wrk_${r}_filled.txt"
    grep -q "fn_z = \"$zfilled\"" "wrk_${r}_filled.txt"
    rm -rf result
    ./encflow "wrk_${r}_filled.txt"
    mv result "result_${r}_filled"
  fi

  # --- 旧移流スキーム(f_advection_scheme = 1)と、移流項なしの拡散波(局所慣性
  #     方程式。f_govequation = 1)。README の「移流項の扱い」。
  #     スキーム 1 は、急な段差や深い静水で流速が発散して止まることがあるので、
  #     止まっても続ける(止まるまでの結果を使う。図では曲線が途中で切れる) ---
  if [ ! -d "result_${r}_s1" ]; then       # スキーム 1(風上化指数は既定の 0.5)
    sed -e '/^&list_enc/a\  f_advection_scheme = 1   ! 旧移流スキーム(非保存形・風上重み)' "$base" > "wrk_${r}_s1.txt"
    grep -q 'f_advection_scheme = 1' "wrk_${r}_s1.txt"
    rm -rf result
    ./encflow "wrk_${r}_s1.txt" || echo "(s1 $r: 途中停止)"
    mv result "result_${r}_s1"
  fi
  if [ ! -d "result_${r}_s1u" ]; then      # スキーム 1 + 風上化指数 0.1(test/chichibu と同じ値)
    sed -e '/^&list_enc/a\  f_advection_scheme = 1   ! 旧移流スキーム' \
        -e '/^&list_enc/a\  p_adv_upwind_index = 0.1 ! 風上化指数(既定 0.5 より弱い風上化)' "$base" > "wrk_${r}_s1u.txt"
    grep -q 'p_adv_upwind_index = 0.1' "wrk_${r}_s1u.txt"
    # 風上化 0.1 の 50 m は、流速が大きくなって、dt 0.75 s では Courant 数が 1 を超えて止まるので、dt = 0.5 s にする
    if [ "$r" = 50m ]; then sed -i 's/^  dt = 0.75 /  dt = 0.5  /' "wrk_${r}_s1u.txt"; grep -q 'dt = 0.5' "wrk_${r}_s1u.txt"; fi
    rm -rf result
    ./encflow "wrk_${r}_s1u.txt" || echo "(s1u $r: 途中停止)"
    mv result "result_${r}_s1u"
  fi
  if [ ! -d "result_${r}_s1f" ]; then      # スキーム 1 + 風上化指数 1.0(完全風上。上限値)
    sed -e '/^&list_enc/a\  f_advection_scheme = 1   ! 旧移流スキーム' \
        -e '/^&list_enc/a\  p_adv_upwind_index = 1.0 ! 風上化指数(完全風上。既定 0.5 より強い風上化)' "$base" > "wrk_${r}_s1f.txt"
    grep -q 'p_adv_upwind_index = 1.0' "wrk_${r}_s1f.txt"
    rm -rf result
    ./encflow "wrk_${r}_s1f.txt"
    mv result "result_${r}_s1f"
  fi
  if [ -n "$zfilled" ] && [ ! -d "result_${r}_filled_noadv" ]; then   # 河床を整える前の標高で、移流項なし
    sed -e "s#fn_z = \"$zcond\"#fn_z = \"$zfilled\"#" -e 's/f_govequation = 0/f_govequation = 1/' "$base" > "wrk_${r}_filled_noadv.txt"
    grep -q "fn_z = \"$zfilled\"" "wrk_${r}_filled_noadv.txt"
    grep -q 'f_govequation = 1' "wrk_${r}_filled_noadv.txt"
    rm -rf result
    ./encflow "wrk_${r}_filled_noadv.txt"
    mv result "result_${r}_filled_noadv"
  fi
  if [ ! -d "result_${r}_noadv" ]; then    # 移流項なし(拡散波)
    sed -e 's/f_govequation = 0/f_govequation = 1/' "$base" > "wrk_${r}_noadv.txt"
    grep -q 'f_govequation = 1' "wrk_${r}_noadv.txt"
    # 移流項なしの 50 m は、慣性の制限がなく、流速が大きくなるので、余裕を見て dt = 0.5 s にする
    if [ "$r" = 50m ]; then sed -i 's/^  dt = 0.75 /  dt = 0.5  /' "wrk_${r}_noadv.txt"; grep -q 'dt = 0.5' "wrk_${r}_noadv.txt"; fi
    rm -rf result
    ./encflow "wrk_${r}_noadv.txt"
    mv result "result_${r}_noadv"
  fi

  # --- 河道の粗度を 0.02 にした計算(スキーム 3 と、移流項なし)。移流項の働きが、河道の粗度で
  #     どう変わるかを見る(README の「移流項の扱い」。200 m・100 m だけ)。流れが速くなるので、
  #     dt を、200 m は 4 s、100 m は 1.0 s にする ---
  if [ "$r" != 50m ]; then
    case $r in
      200m) dtn='s/^  dt = 6.0 /  dt = 4.0 /'; dtg='dt = 4.0' ;;
      100m) dtn='s/^  dt = 1.5 /  dt = 1.0 /'; dtg='dt = 1.0' ;;
    esac
    if [ ! -d "result_${r}_n02" ]; then
      sed -e 's/rn0_rw = 0.04 /rn0_rw = 0.02 /' -e "$dtn" "$base" > "wrk_${r}_n02.txt"
      grep -q 'rn0_rw = 0.02' "wrk_${r}_n02.txt"
      grep -q "$dtg" "wrk_${r}_n02.txt"
      rm -rf result
      ./encflow "wrk_${r}_n02.txt"
      mv result "result_${r}_n02"
    fi
    if [ ! -d "result_${r}_n02_noadv" ]; then
      sed -e 's/rn0_rw = 0.04 /rn0_rw = 0.02 /' -e 's/f_govequation = 0/f_govequation = 1/' -e "$dtn" "$base" > "wrk_${r}_n02_noadv.txt"
      grep -q 'rn0_rw = 0.02' "wrk_${r}_n02_noadv.txt"
      grep -q 'f_govequation = 1' "wrk_${r}_n02_noadv.txt"
      grep -q "$dtg" "wrk_${r}_n02_noadv.txt"
      rm -rf result
      ./encflow "wrk_${r}_n02_noadv.txt"
      mv result "result_${r}_n02_noadv"
    fi
  fi
done


# --- 200 m だけの比較: 元の DEM(窪地除去なし)、降雨遮断と地下浸透、流域出口を閉じる ---
case " $RES " in *" 200m "*)
  if [ ! -d "result_200m_raw" ]; then
    # 元の DEM は GeoTIFF しかないので、入力をすべて GeoTIFF に替える
    sed -e 's/f_input_mode = 1 /f_input_mode = 4 /' \
        -e 's/"Chichibu_200m_cond.txt"/"Chichibu_200m_raw.tif"/' \
        -e 's/"Chichibu_200m_basin.txt"/"Chichibu_200m_basin.tif"/' \
        -e 's/"Chichibu_200m_river_flowline.txt"/"Chichibu_200m_river_flowline.tif"/' param.txt > wrk_200m_raw.txt
    grep -q '"Chichibu_200m_raw.tif"' wrk_200m_raw.txt
    grep -q 'f_input_mode = 4' wrk_200m_raw.txt
    rm -rf result
    ./encflow wrk_200m_raw.txt
    mv result result_200m_raw
  fi
  if [ ! -d "result_200m_loss" ]; then
    # 遮断率 0.2 の固定遮断率モデルと、浸透能 5 mm/h・地下貯留容量 0.2 m のバケツモデル
    sed -e '/^  fn_boundary/a\  fn_intercept = "-"         ! 降雨遮断条件設定ファイル\n  fn_gwflow = "-"            ! 地下水条件設定ファイル' param.txt > wrk_200m_loss.txt
    grep -q 'fn_gwflow = "-"' wrk_200m_loss.txt
    cat >> wrk_200m_loss.txt <<'EOS'

&list_intercept
  f_icmodel = 1              ! 1:固定遮断率モデル
/
&list_intercept_fixed
  ic_alpha = 0.2             ! 遮断率(有効雨量 = (1-α)P)
/
&list_gwflow
  f_gwvertical = 1           ! 1:バケツモデル
/
&list_gwflow_bucket
  gw_infil_mmh = 5.0         ! 浸透能 (mm/h)
  gw_capacity = 0.2          ! 地下貯留容量(柱状換算水深) (m)
/
EOS
    rm -rf result
    ./encflow wrk_200m_loss.txt
    mv result result_200m_loss
  fi
  if [ ! -d "result_200m_closed" ]; then
    # fn_boundary を消すと、&list_bound_stage(流域出口)を読まない = 出口を閉じた器になる
    sed -e '/^  fn_boundary/d' param.txt > wrk_200m_closed.txt
    ! grep -q 'fn_boundary' wrk_200m_closed.txt
    rm -rf result
    ./encflow wrk_200m_closed.txt
    mv result result_200m_closed
  fi
  ;;
esac
echo "done: result_* (draw the figures with: python3 plot_results.py [en])"
