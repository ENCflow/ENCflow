#!/bin/bash
# 補足節(格子の細分と非静水圧補正)の図 figs/supp_*.png を再生成する。
#   使い方: ./Fig_supp.sh   (要 gnuplot。実行ファイルは make で用意)
# Fig_wave.sh とは別にしてある: 静水圧 nx = 1400 のケースを含むため、4 コアの
# ノート PC で 30 分前後かかる。param_step1.txt / param_step2.txt から
# 一時ファイル wrk_param_*.txt を sed で生成して実行する。
set -eu

mkdir -p figs
rm -f wrk_*

# 格子数 nx・時間刻み dt・非静水圧の有無を変えたパラメータファイルを作る
mkparam() {  # mkparam <出力> <nx> <dt> <f_nonhydrostatic 0/1>
  sed -e "s/^  dt = 0.01 .*/  dt = $3                 ! 時間刻み (s)/" \
      -e "s/^  nx = 350, ny = 350/  nx = $2, ny = $2/" param_step1.txt > "$1"
  if [ "$4" = 1 ]; then
    sed -i 's/^  fn_initial = "-".*/&\n  fn_enc = "-"              ! ENCパラメータ設定ファイル/' "$1"
    printf '\n&list_enc\n  f_nonhydrostatic = 1           ! 1 層非静水圧補正\n/\n' >> "$1"
  fi
}

# 実行して最終水位 E9998 を wrk_<tag>_E9998.txt に退避する
run() {  # run <param> <tag>
  ./encflow "$1"
  cp result/E9998.txt "wrk_$2_E9998.txt"
}

# 中心からの 0° 方向(x 軸沿い)の動径プロファイル(Fig_wave.sh と同じ)
prof() {  # prof <E9998ファイル> <出力ファイル>
  awk '{for(i=1;i<=NF;i++)a[NR,i]=$i; n=NF}END{
    dx=100./n; c=(n+1)/2.; j=int(c)
    for(i=j+1;i<=n;i++) printf "%.4f %.5f\n", (i-c)*dx, (a[j,i]+a[j+1,i])/2
  }' "$1" > "$2"
}

# --- 静水圧: nx = 350 / 700 / 1400(dt は格子に比例して 0.01 / 0.005 / 0.0025) ---
run param_step1.txt h350
mkparam wrk_param_h700.txt  700  0.005  0; run wrk_param_h700.txt  h700
mkparam wrk_param_h1400.txt 1400 0.0025 0; run wrk_param_h1400.txt h1400

# --- 静水圧: dt = 0.05 + 適応ルンゲクッタ閾値 1.1(Step 2 と同じ) ---
run param_step2.txt s2

# --- 非静水圧: nx = 350 / 700(700 で既に収束しているので 1400 は走らせない) ---
mkparam wrk_param_n350.txt  350  0.01   1; run wrk_param_n350.txt  n350
mkparam wrk_param_n700.txt  700  0.005  1; run wrk_param_n700.txt  n700

for t in h350 h700 h1400 s2 n350 n700; do prof wrk_${t}_E9998.txt wrk_${t}_prof.txt; done

gnuplot Fig_supp.plt
rm -f wrk_*
echo "figs/ generated:"
ls figs/supp_*
