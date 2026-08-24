#!/bin/bash
# チュートリアル本文(README.md)の図 figs/*.png を一括再生成する。
#   使い方: ./Fig_chichibu.sh   (要 gnuplot。実行ファイルは make で用意)
# 本文の手順どおり Step 1〜6 と未処理 DEM の比較計算を順に実行し、
# 結果を result_step1〜6, result_raw に退避してから Fig_chichibu.plt で
# 描画する。計算済みの result_step* があれば計算を飛ばして描画だけ行う
# (全て計算し直す場合は rm -rf result_step* result_raw してから実行)。
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

# --- 未処理 DEM(raw)の比較計算(Step 2 の設定で fn_z だけ差し替え) ---
if [ ! -d result_raw ]; then
  sed -e 's/Chichibu_200m_filled.tif/Chichibu_200m_raw.tif/' \
      param_step2.txt > wrk_param_raw.txt
  rm -rf result
  ./encflow wrk_param_raw.txt
  mv result result_raw
fi

# --- 4近傍の比較計算(Step 2 の設定で対角成分をゼロに) ---
if [ ! -d result_4nb ]; then
  sed -e '/dir_data/i\  fn_enc     = "-"           ! ENC条件設定ファイル' \
      param_step2.txt > wrk_param_4nb.txt
  printf '\n&%s\n  p_diagratio = 0.0        ! 対角成分ゼロ = 4近傍相当\n/\n' \
      list_enc >> wrk_param_4nb.txt
  rm -rf result
  ./encflow wrk_param_4nb.txt
  mv result result_4nb
fi

# --- 地形図用: 流域マスク外を欠損(-9999)にした地盤高 ---
awk 'NR==FNR{for(i=1;i<=NF;i++)b[FNR,i]=$i;next}
     {for(i=1;i<=NF;i++)printf "%s ",(b[FNR,i]>0? $i : -9999); print ""}' \
  data_chichibu/Chichibu_200m_basin.txt result_step1/Z0000.txt > wrk_zmask.txt

# --- 描画(日本語版 figs/ と英語版 en/figs/ を同時に再生成) ---
gnuplot Fig_chichibu.plt
gnuplot en/Fig_chichibu.plt
echo "generated figures in figs/ and en/figs/"
