# 補足節(解像度の影響と 4 近傍との比較)の図を figs/supp_*.png に描画する。
# 事前に Fig_supp.sh が 6 ケースの計算を result_supp_{200m,100m,50m}[_4nb] に
# 用意していることを前提とする(単体では実行しない)。

set datafile separator whitespace
set terminal pngcairo size 1100,780 font ",11"

# ---- 各解像度の入力データと測線・プローブ(param_supp_*.txt の数値を書き写す) ----
# 列: 測線番号, 右岸 ix, 右岸 iy, 左岸 ix, 左岸 iy, プローブ ix, プローブ iy
$T200 << EOD
1   82 107   82 103    82 105
2  107 103  107 100   107 102
3  147 105  147 102   147 104
4  216  43  216  37   216  39
EOD
$T100 << EOD
1  164 214  164 205   164 210
2  214 206  214 199   214 203
3  294 210  294 203   294 207
4  432  86  432  73   432  78
EOD
$T50 << EOD
1  327 428  327 409   327 421
2  427 412  427 397   427 405
3  587 420  587 405   587 414
4  863 172  863 145   863 155
EOD
array LBL[3]   = [ "200 m", "100 m", "50 m" ]
array HALF[3]  = [ 7.5, 15, 30 ]       # 拡大窓の半幅(セル)= ±1.5 km
array RIVER[3] = [ "data_chichibu/Chichibu_200m_river.txt", \
                   "../../test/chichibu/data_chichibu/Chichibu_100m_river.txt", \
                   "../../test/chichibu/data_chichibu_50m/Chichibu_50m_river.txt" ]
array BASIN[3] = [ "data_chichibu/Chichibu_200m_basin.txt", \
                   "../../test/chichibu/data_chichibu/Chichibu_100m_basin.txt", \
                   "../../test/chichibu/data_chichibu_50m/Chichibu_50m_basin.txt" ]
array TR[3]    = [ "$T200", "$T100", "$T50" ]
# 拡大窓の中心(測線の ix と、両端 iy の中点)
array XC200[4] = [ 82, 107, 147, 216 ];  array YC200[4] = [ 105, 101.5, 103.5, 40 ]
array XC100[4] = [ 164, 214, 294, 432 ]; array YC100[4] = [ 209.5, 202.5, 206.5, 79.5 ]
array XC50[4]  = [ 327, 427, 587, 863 ]; array YC50[4]  = [ 418.5, 404.5, 412.5, 158.5 ]
xc(r, i) = (r == 1) ? XC200[i] : (r == 2) ? XC100[i] : XC50[i]
yc(r, i) = (r == 1) ? YC200[i] : (r == 2) ? YC100[i] : YC50[i]

# ---- 図 1: 各解像度の河道マスクと測線(測線が河道を跨いでいることの確認) ----
set output "figs/supp_transects.png"
set multiplot layout 3,4 title "各解像度の河道マスク(青)と測線(赤、右岸 → 左岸)・プローブ(○)。窓は ±1.5 km" noenhanced
set size ratio -1
unset colorbox
set palette defined (1 '#c8d3dd', 2 '#1f5fbf')
set cbrange [1:2]
set xlabel "ix(セル番号)"
set ylabel "iy(セル番号)"
do for [r=1:3] {
  do for [i=1:4] {
    set xrange [xc(r,i)-HALF[r]:xc(r,i)+HALF[r]]
    set yrange [yc(r,i)+HALF[r]:yc(r,i)-HALF[r]]
    set xtics HALF[r] * 0.8
    set ytics HALF[r] * 0.4
    set title sprintf("%s: 測線 %d", LBL[r], i) noenhanced
    plot BASIN[r] matrix using ($1+1):($2+1):($3 > 0 ? 1 : NaN) with image notitle, \
         RIVER[r] matrix using ($1+1):($2+1):($3 > 0 ? 2 : NaN) with image notitle, \
         TR[r] every ::i-1::i-1 using 2:3:($4-$2):($5-$3) with vectors head filled size 0.6,25 lw 2 lc rgb '#d02020' notitle, \
         TR[r] every ::i-1::i-1 using 6:7 with points pt 6 ps 1.5 lw 2 lc rgb '#000000' notitle
  }
}
unset multiplot

# ==== ここから計算結果を使う図 ====

# ---- 図 2: 上流(測線 1)と下流(測線 4)のハイドログラフ。ENC(上段)と 4 近傍(下段) ----
reset
set datafile separator comma
set terminal pngcairo size 1000,640 font ",11"
set output "figs/supp_hydro.png"
set multiplot layout 2,2 title "解像度の影響: 上段 ENC(8 方向交換)、下段 4 近傍(p_diagratio = 0)" noenhanced
set grid
set xlabel "時間 (min)"
set ylabel "流量 (m^3/s)"
set xrange [0:360]
set key top right
array RES[3] = [ "200m", "100m", "50m" ]
array RLB[3] = [ "200 m", "100 m", "50 m" ]
array SFX[2] = [ "", "_4nb" ]
array SLB[2] = [ "ENC", "4 近傍" ]
array TRN[2] = [ 1, 4 ]
array TLB[2] = [ "上流(測線 1)", "下流(測線 4)" ]
do for [s=1:2] {
  do for [t=1:2] {
    set title sprintf("%s: %s", SLB[s], TLB[t]) noenhanced
    set yrange [0:(t == 1 ? 1600 : 6500)]
    plot for [r=1:3] sprintf("result_supp_%s%s/fluxes/flux000%d.csv", RES[r], SFX[s], TRN[t]) \
         using 2:3 with lines lw 1.5 title RLB[r]
  }
}
unset multiplot
