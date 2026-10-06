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
    set xrange [0:(t == 1 ? 150 : 360)]   # 上流は波形が短いので時間軸を縮める
    set yrange [0:(t == 1 ? 1600 : 6500)]
    plot for [r=1:3] sprintf("result_supp_%s%s/fluxes/flux000%d.csv", RES[r], SFX[s], TRN[t]) \
         using 2:3 with lines lw 1.5 title RLB[r]
  }
}
unset multiplot

# ---- 図 2b: 河道幅を 50 m に揃えた ENC(測線 1・4)。幅なしを破線で重ねる ----
reset
set datafile separator comma
set terminal pngcairo size 1000,360 font ",11"
set output "figs/supp_hydro_w50.png"
set multiplot layout 1,2 title "河道幅を 50 m に揃えた比較(実線: W = 50 m のサブグリッド河道、破線: 幅なし、50 m 格子は解像河道)" noenhanced
set grid
set xlabel "時間 (min)"
set ylabel "流量 (m^3/s)"
set xrange [0:360]
set key top right
array TRNW[2] = [ 1, 4 ]
array TLBW[2] = [ "上流(測線 1)", "下流(測線 4)" ]
do for [t=1:2] {
  set title TLBW[t] noenhanced
  set xrange [0:(t == 1 ? 150 : 360)]
  set yrange [0:(t == 1 ? 1600 : 6500)]
  plot sprintf("result_supp_200m/fluxes/flux000%d.csv", TRNW[t])     using 2:3 with lines lw 1.2 dt 2 lc rgb '#9467bd' title "200 m 幅なし", \
       sprintf("result_supp_200m_w50/fluxes/flux000%d.csv", TRNW[t]) using 2:3 with lines lw 1.8      lc rgb '#9467bd' title "200 m W = 50", \
       sprintf("result_supp_100m/fluxes/flux000%d.csv", TRNW[t])     using 2:3 with lines lw 1.2 dt 2 lc rgb '#2ca02c' title "100 m 幅なし", \
       sprintf("result_supp_100m_w50/fluxes/flux000%d.csv", TRNW[t]) using 2:3 with lines lw 1.8      lc rgb '#2ca02c' title "100 m W = 50", \
       sprintf("result_supp_50m/fluxes/flux000%d.csv", TRNW[t])      using 2:3 with lines lw 1.8      lc rgb '#1f9fd0' title "50 m(解像河道)"
}
unset multiplot

# ---- 図 3: 6 時間後の水深分布。左 ENC、右 4 近傍(行: 200 / 100 / 50 m) ----
# 水深 0 を白とするパレット(Fig_chichibu.plt と同じ)。4 近傍では河道網の
# 至る所に点状の湛水が残り、斜めに走る区間ごとに水が寸断されることを見せる
reset
set datafile separator whitespace
set terminal pngcairo size 1000,900 font ",11"
set output "figs/supp_hend.png"
set multiplot layout 3,2 title "6 時間後の水深分布: 左 ENC、右 4 近傍" noenhanced
set view map
set size ratio -1
set yrange [30:0]
set xrange [0:56]
set xlabel "x (km)"
set ylabel "y (km)"
set cblabel "水深 (m)"
set palette defined ( -1 '#ffffff', 0 '#000090',1 '#000fff',2 '#0090ff',3 '#0fffee',4 '#90ff70',5 '#ffee00',6 '#ff7000',7 '#ee0000',8 '#7f0000')
set cbrange [0:5]
array RES3[3] = [ "200m", "100m", "50m" ]
array DXK[3]  = [ 0.2, 0.1, 0.05 ]      # セル番号 → km
array SFX3[2] = [ "", "_4nb" ]
array SLB3[2] = [ "ENC", "4 近傍" ]
do for [r=1:3] {
  do for [s=1:2] {
    set title sprintf("%s m %s", RES3[r][1:strlen(RES3[r])-1], SLB3[s]) noenhanced
    plot sprintf("result_supp_%s%s/H9998.txt", RES3[r], SFX3[s]) matrix \
         using ($1*DXK[r]):($2*DXK[r]):($3 <= 0.05 ? NaN : $3) with image notitle
  }
}
unset multiplot
