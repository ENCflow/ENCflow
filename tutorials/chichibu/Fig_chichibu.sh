#!/bin/bash
# チュートリアル本文(README.md)の図 figs/*.png を一括再生成する。
#   使い方: ./Fig_chichibu.sh   (要 gnuplot。実行ファイルは make で用意)
# 本文の手順どおり Step 1〜6 を順に実行して結果を result_step1〜6 に
# 退避し、窪地除去・4 近傍の比較計算(Step 2 の設定で計算時間を 12 時間に
# 延ばしたもの)を result_cmp_{filled,raw,4nb} に置いてから Fig_chichibu.plt
# で描画する。計算済みの result_* があれば計算を飛ばして描画だけ行う
# (全て計算し直す場合は rm -rf result_step* result_cmp_* してから実行)。
set -eu

mkdir -p figs en/figs
rm -f wrk_*

# --- Step 1〜6 の実行(結果を result_stepN に退避) ---
for s in 1 2 3 4 5 6; do
  if [ ! -d "result_step$s" ]; then
    rm -rf result
    ./encflow "param_step$s.txt"
    mv result "result_step$s"
  fi
done

# --- 窪地除去・4近傍の比較計算(Step 2 の設定で計算時間を 12 時間に延長。
#     河道の水が出口の池にほぼ集まり切った状態で比べるため) ---
#   filled: そのまま / raw: fn_z を未処理 DEM に差し替え /
#   4nb: 対角成分をゼロにして 4 近傍相当に
for c in filled raw 4nb; do
  if [ ! -d "result_cmp_$c" ]; then
    sed -e 's/tt_c = "6 hour"/tt_c = "12 hour"/' param_step2.txt > "wrk_param_$c.txt"
    case $c in
      raw) sed -i -e 's/Chichibu_200m_filled.tif/Chichibu_200m_raw.tif/' "wrk_param_$c.txt" ;;
      4nb) sed -i -e '/dir_data/i\  fn_enc     = "-"           ! ENC条件設定ファイル' "wrk_param_$c.txt"
           printf '\n&%s\n  p_diagratio = 0.0        ! 対角成分ゼロ = 4近傍相当\n/\n' \
               list_enc >> "wrk_param_$c.txt" ;;
    esac
    rm -rf result
    ./encflow "wrk_param_$c.txt"
    mv result "result_cmp_$c"
  fi
done

# --- 地形図用: 流域マスク外を欠損(-9999)にした地盤高 ---
awk 'NR==FNR{for(i=1;i<=NF;i++)b[FNR,i]=$i;next}
     {for(i=1;i<=NF;i++)printf "%s ",(b[FNR,i]>0? $i : -9999); print ""}' \
  data_chichibu/Chichibu_200m_basin.txt result_step1/Z0000.txt > wrk_zmask.txt

# --- 描画(日本語版 figs/ と英語版 en/figs/ を同時に再生成) ---
gnuplot Fig_chichibu.plt
gnuplot en/Fig_chichibu.plt
echo "generated figures in figs/ and en/figs/"
