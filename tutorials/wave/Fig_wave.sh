#!/bin/bash
# チュートリアル本文(README.md)の図 figs/*.png を一括再生成する。
#   使い方: ./Fig_wave.sh   (要 gnuplot。実行ファイルは make で用意)
# 本文の手順どおりの計算を順に実行し、必要な出力を wrk_*.txt に退避して
# から Fig_wave.plt で描画する。パラメータの書き換えは param_step*.txt を
# 直接編集せず、一時ファイル wrk_param_*.txt を sed で生成して行う。
set -eu

mkdir -p figs
rm -f wrk_*

# 実行して最終水位 E9998 を wrk_<tag>_E9998.txt に退避する
run() {  # run <param> <tag>
  ./encflow "$1"
  cp result/E9998.txt "wrk_$2_E9998.txt"
}

# 中心からの動径プロファイルを抽出する(index 0: 0°方向、index 1: 45°方向)
# 領域中心はセル境界 (150.5, 150.5) にあるため、0°方向は中心を挟む2行の
# 平均、45°方向は対角セル (i,i) の値をそのまま使う
prof() {  # prof <E9998ファイル> <出力ファイル>
  awk '{for(i=1;i<=NF;i++)a[NR,i]=$i; n=NF}END{
    dx=100./n; c=(n+1)/2.; j=int(c)
    for(i=j+1;i<=n;i++) printf "%.4f %.5f\n", (i-c)*dx, (a[j,i]+a[j+1,i])/2
    print ""; print ""
    for(i=j+1;i<=n;i++) printf "%.4f %.5f\n", (i-c)*sqrt(2)*dx, a[i,i]
  }' "$1" > "$2"
}

# --- Step 1: dt = 0.01(初期水位 E0000 も図に使う) ---
./encflow param_step1.txt
cp result/E0000.txt wrk_step1_E0000.txt
cp result/E9998.txt wrk_step1_dt001_E9998.txt

# --- Step 1: dt = 0.05(本文の指示どおり dt の行を入れ替え) ---
sed -e 's/^  dt = 0.01/  !dt = 0.01/' -e 's/^  !dt = 0.05/  dt = 0.05/' \
    param_step1.txt > wrk_param_step1_dt005.txt
run wrk_param_step1_dt005.txt step1_dt005

# --- Step 2: 適応的ルンゲクッタの閾値 1.1 ---
run param_step2.txt step2

# --- 動径プロファイル(同心円対称性の確認用) ---
prof wrk_step1_dt001_E9998.txt wrk_step1_dt001_prof.txt
prof wrk_step1_dt005_E9998.txt wrk_step1_dt005_prof.txt
prof wrk_step2_E9998.txt       wrk_step2_prof.txt

# --- Step 2: 計算時間を tt = 14 に延長(閉じた壁での反射) ---
sed -e 's/^  tt = 8.0/  tt = 14.0/' param_step2.txt > wrk_param_step2_tt14.txt
run wrk_param_step2_tt14.txt step2_tt14

# --- Step 3: 長波放射境界 ---
run param_step3.txt step3

# --- Step 4: 斜めの不透過壁(2セル厚)/ 半透過壁(1セル厚) ---
run param_step4.txt step4_solid
sed -e 's/^  f_user_routine = "wave_solid_wall"/  !f_user_routine = "wave_solid_wall"/' \
    -e 's/^  !f_user_routine = "wave_leaky_wall"/  f_user_routine = "wave_leaky_wall"/' \
    param_step4.txt > wrk_param_step4_leaky.txt
run wrk_param_step4_leaky.txt step4_leaky

gnuplot Fig_wave.plt
rm -f wrk_*
echo "figs/ generated:"
ls figs/
