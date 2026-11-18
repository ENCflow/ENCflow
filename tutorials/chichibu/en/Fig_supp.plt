# English mirror of tutorials/chichibu/Fig_supp.plt. The Japanese file is the
# master copy; edit it first.
# 英語版 README(en/README.md)用の補足節の図を en/figs/supp_*.png に描画する。
# Fig_supp.sh が日本語版と一緒に呼び出す(単体では実行しない)。

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
1  164 214  164 205   164 211
2  214 206  214 199   214 202
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
array RIVER[3] = [ "data_chichibu/Chichibu_200m_river_flowline.txt", \
                   "../../test/chichibu/data_chichibu/Chichibu_100m_river_flowline.txt", \
                   "../../test/chichibu/data_chichibu_50m/Chichibu_50m_river_flowline.txt" ]
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
set output "en/figs/supp_transects.png"
set multiplot layout 3,4 title "Channel mask (blue), transects (red, right bank -> left bank) and probes (o) at each resolution; window ±1.5 km" noenhanced
set size ratio -1
unset colorbox
set palette defined (1 '#c8d3dd', 2 '#1f5fbf')
set cbrange [1:2]
set xlabel "ix (cell number)"
set ylabel "iy (cell number)"
do for [r=1:3] {
  do for [i=1:4] {
    set xrange [xc(r,i)-HALF[r]:xc(r,i)+HALF[r]]
    set yrange [yc(r,i)+HALF[r]:yc(r,i)-HALF[r]]
    set xtics HALF[r] * 0.8
    set ytics HALF[r] * 0.4
    set title sprintf("%s: transect %d", LBL[r], i) noenhanced
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
set output "en/figs/supp_hydro.png"
set multiplot layout 2,2 title "Effect of resolution: top ENC (8-direction exchange), bottom 4-neighbor (p_diagratio = 0)" noenhanced
set grid
set xlabel "time (min)"
set ylabel "discharge (m^3/s)"
set xrange [0:360]
set key top right
array RES[3] = [ "200m", "100m", "50m" ]
array RLB[3] = [ "200 m", "100 m", "50 m" ]
array SFX[2] = [ "", "_4nb" ]
array SLB[2] = [ "ENC", "4-neighbor" ]
array TRN[2] = [ 1, 4 ]
array TLB[2] = [ "upstream (transect 1)", "downstream (transect 4)" ]
do for [s=1:2] {
  do for [t=1:2] {
    set title sprintf("%s: %s", SLB[s], TLB[t]) noenhanced
    set xrange [0:(t == 1 ? 150 : 360)]   # 上流は波形が短いので時間軸を縮める
    set yrange [0:(s == 1 ? (t == 1 ? 1600 : 10000) : 100)]   # the 4-neighbor panels are 1/16 (upstream) and 1/100 (downstream) of ENC; noted in the text
    plot for [r=1:3] sprintf("result_supp_%s%s/fluxes/flux000%d.csv", RES[r], SFX[s], TRN[t]) \
         using 2:3 with lines lw 1.5 title RLB[r]
  }
}
unset multiplot

# ---- 図 2c: 移流項の扱い(なし / スキーム 1 / スキーム 3)× 解像度。測線 1・4 ----
reset
set datafile separator comma
set terminal pngcairo size 1000,1500 font ",11"
set output "en/figs/supp_hydro_adv.png"
set multiplot layout 5,2 title "Advection treatment and resolution dependence (from top: no advection, scheme 1 with upwind 0.1 / 0.5 / 1.0, scheme 3)" noenhanced
set grid
set xlabel "time (min)"
set ylabel "discharge (m^3/s)"
set key top right
array RESA[3] = [ "200m", "100m", "50m" ]
array RLBA[3] = [ "200 m", "100 m", "50 m" ]
array SFXA[5] = [ "_noadv", "_s1u", "_s1", "_s1f", "" ]   # scheme 1 from the weakest upwinding (0.1 -> 0.5 = default -> 1.0)
array SLBA[5] = [ "no advection", "scheme 1 (upwind 0.1)", "scheme 1 (upwind 0.5 = default)", "scheme 1 (upwind 1.0)", "scheme 3 (default)" ]
array TRNA[2] = [ 1, 4 ]
array TLBA[2] = [ "upstream (transect 1)", "downstream (transect 4)" ]
do for [s=1:5] {
  do for [t=1:2] {
    set title sprintf("%s: %s", SLBA[s], TLBA[t]) noenhanced
    set xrange [0:(t == 1 ? 150 : 360)]
    set yrange [0:(t == 1 ? 1800 : 15000)]   # the right column (transect 4) uses one range for all rows, wider than in the other figures (noted in the text)
    plot for [r=1:3] sprintf("result_supp_%s%s/fluxes/flux000%d.csv", RESA[r], SFXA[s], TRNA[t]) \
         using 2:3 with lines lw 1.5 title RLBA[r]
  }
}
unset multiplot

# ---- 図 2b: 河道幅を 50 m に揃えた ENC(測線 3・4)。幅なしを破線で重ねる ----
reset
set datafile separator comma
set terminal pngcairo size 1000,360 font ",11"
set output "en/figs/supp_hydro_w50.png"
set multiplot layout 1,2 title "Channel width equalized to 50 m (solid: W = 50 m subgrid channel, dashed: no width; the 50 m grid has a resolved channel)" noenhanced
set grid
set xlabel "time (min)"
set ylabel "discharge (m^3/s)"
set xrange [0:360]
set key top right
array TRNW[2] = [ 3, 4 ]
array TLBW[2] = [ "transect 3", "transect 4" ]
do for [t=1:2] {
  set title TLBW[t] noenhanced
  set xrange [0:(t == 1 ? 240 : 360)]
  set yrange [0:10000]
  set key top right Left reverse samplen 2 font ",9"
  plot sprintf("result_supp_200m/fluxes/flux000%d.csv", TRNW[t])     using 2:3 with lines lw 1.2 dt 2 lc rgb '#9467bd' title "200 m, no width", \
       sprintf("result_supp_200m_w50/fluxes/flux000%d.csv", TRNW[t]) using 2:3 with lines lw 1.8      lc rgb '#9467bd' title "200 m W = 50", \
       sprintf("result_supp_100m/fluxes/flux000%d.csv", TRNW[t])     using 2:3 with lines lw 1.2 dt 2 lc rgb '#2ca02c' title "100 m, no width", \
       sprintf("result_supp_100m_w50/fluxes/flux000%d.csv", TRNW[t]) using 2:3 with lines lw 1.8      lc rgb '#2ca02c' title "100 m W = 50", \
       sprintf("result_supp_50m/fluxes/flux000%d.csv", TRNW[t])      using 2:3 with lines lw 1.8      lc rgb '#1f9fd0' title "50 m (resolved)", \
       sprintf("result_supp_50m_w50/fluxes/flux000%d.csv", TRNW[t])  using 2:3 with lines lw 1.2 dt 2 lc rgb '#1f9fd0' title "50 m W = 50"
}
unset multiplot

# ---- Figure 2d: fluctuations in the 1-minute values (examples for item 3 of the supplement
#      "Fine oscillations in the hydrograph") ----
# Left: transect 4 of the 100 m grid. At a bend 0.4 to 0.8 km upstream of the transect the channel depth becomes
#     about equal to the height difference between the channel cell and the cells on both sides (water starts to
#     spill onto, or retreats from, the bank cells), and the flow state switches back and forth.
#     It does not appear with the 50 m wide subgrid channel or on the 200 m grid (dashed).
# Right: transect 3 of the 50 m grid. At the upstream end of the deep reach formed by a bend 0.5 to 1 km downstream
#     of the transect, the boundary where the shallow, fast flow enters the deep flow (a hydraulic jump) moves
#     back and forth. It does not appear on the 100 m and 200 m grids (dashed).
# Both are water stored and released in a reach and do not change the total runoff. Lower panels: change per minute
reset
set datafile separator comma
set terminal pngcairo size 1100,640 font ",11"
set output "en/figs/supp_osc.png"
set multiplot layout 2,2 title "Examples of fluctuations in the 1-minute values (left: transect 4 of the 100 m grid; right: transect 3 of the 50 m grid)" noenhanced
set grid
set xlabel "time (min)"
array TRO[2]  = [ 4, 3 ]
array XO0[2]  = [ 90, 40 ]
array XO1[2]  = [ 250, 130 ]
# 上段: 流量
set ylabel "discharge (m^3/s)"
set key top right
set yrange [0:10000]
set xrange [XO0[1]:XO1[1]]
set title "transect 4 of the 100 m grid"
plot "result_supp_100m/fluxes/flux0004.csv"     using 2:3 with lines lw 1.6      lc rgb '#2ca02c' title "100 m", \
     "result_supp_100m_w50/fluxes/flux0004.csv" using 2:3 with lines lw 1.2 dt 2 lc rgb '#2ca02c' title "100 m W = 50", \
     "result_supp_200m/fluxes/flux0004.csv"     using 2:3 with lines lw 1.2 dt 2 lc rgb '#9467bd' title "200 m"
set xrange [XO0[2]:XO1[2]]
set title "transect 3 of the 50 m grid"
plot "result_supp_50m/fluxes/flux0003.csv"  using 2:3 with lines lw 1.6      lc rgb '#1f9fd0' title "50 m", \
     "result_supp_100m/fluxes/flux0003.csv" using 2:3 with lines lw 1.2 dt 2 lc rgb '#2ca02c' title "100 m", \
     "result_supp_200m/fluxes/flux0003.csv" using 2:3 with lines lw 1.2 dt 2 lc rgb '#9467bd' title "200 m"
# 下段: 1 分ごとの変化 = 当該行の流量 − 前の行の流量(各曲線の先頭で前値を NaN に戻す)
set ylabel "change per minute (m^3/s)"
unset title
set yrange [-3000:3000]
set xrange [XO0[1]:XO1[1]]
plot p = NaN, "result_supp_100m/fluxes/flux0004.csv"     using 2:(d = $3 - p, p = $3, d) with lines lw 1.6      lc rgb '#2ca02c' title "100 m", \
     p = NaN, "result_supp_100m_w50/fluxes/flux0004.csv" using 2:(d = $3 - p, p = $3, d) with lines lw 1.2 dt 2 lc rgb '#2ca02c' title "100 m W = 50", \
     p = NaN, "result_supp_200m/fluxes/flux0004.csv"     using 2:(d = $3 - p, p = $3, d) with lines lw 1.2 dt 2 lc rgb '#9467bd' title "200 m"
set xrange [XO0[2]:XO1[2]]
plot p = NaN, "result_supp_50m/fluxes/flux0003.csv"  using 2:(d = $3 - p, p = $3, d) with lines lw 1.6      lc rgb '#1f9fd0' title "50 m", \
     p = NaN, "result_supp_100m/fluxes/flux0003.csv" using 2:(d = $3 - p, p = $3, d) with lines lw 1.2 dt 2 lc rgb '#2ca02c' title "100 m", \
     p = NaN, "result_supp_200m/fluxes/flux0003.csv" using 2:(d = $3 - p, p = $3, d) with lines lw 1.2 dt 2 lc rgb '#9467bd' title "200 m"
unset multiplot

# ---- 図 2e: 河床を整えた効果(200 m・100 m 格子。実線 = 河床を整えた標高、破線 = 窪地除去済みの標高) ----
reset
set datafile separator comma
set terminal pngcairo size 1000,360 font ",11"
set output "en/figs/supp_bed.png"
set multiplot layout 1,2 title "Effect of the conditioned bed (solid: conditioned channel bed, dashed: depression-filled elevation)" noenhanced
set grid
set xlabel "time (min)"
set ylabel "discharge (m^3/s)"
set key top right Left reverse samplen 2 font ",9"   # a smaller legend at the top right, clear of the peaks
array TRNB[2] = [ 3, 4 ]
array TLBB[2] = [ "transect 3", "transect 4" ]
do for [t=1:2] {
  set title TLBB[t] noenhanced
  set xrange [0:(t == 1 ? 240 : 360)]
  set yrange [0:10000]
  plot sprintf("result_supp_200m/fluxes/flux000%d.csv", TRNB[t])        using 2:3 with lines lw 1.8      lc rgb '#9467bd' title "200 m", \
       sprintf("result_supp_200m_filled/fluxes/flux000%d.csv", TRNB[t]) using 2:3 with lines lw 1.2 dt 2 lc rgb '#9467bd' title "200 m (depression-filled)", \
       sprintf("result_supp_100m/fluxes/flux000%d.csv", TRNB[t])        using 2:3 with lines lw 1.8      lc rgb '#2ca02c' title "100 m", \
       sprintf("result_supp_100m_filled/fluxes/flux000%d.csv", TRNB[t]) using 2:3 with lines lw 1.2 dt 2 lc rgb '#2ca02c' title "100 m (depression-filled)"
}
unset multiplot

# ---- 図 2f: 河道の粗度と移流項(測線 4。200 m・100 m 格子)。粗度 0.02 の移流項なしは、洪水波が段波になる ----
reset
set datafile separator comma
set terminal pngcairo size 1000,360 font ",11"
set output "en/figs/supp_rough.png"
set multiplot layout 1,2 title "Channel roughness and the advection term (transect 4; solid: scheme 3, dashed: no advection)" noenhanced
set grid
set xlabel "time (min)"
set ylabel "discharge (m^3/s)"
set key top right
set xrange [0:300]
set yrange [0:30000]   # 段波のピークを収めるため、この図だけ縦軸の範囲が広い(本文に注記)
array RESR[2] = [ "200m", "100m" ]
array RLBR[2] = [ "200 m grid", "100 m grid" ]
do for [r=1:2] {
  set title RLBR[r] noenhanced
  plot sprintf("result_supp_%s/fluxes/flux0004.csv", RESR[r])           using 2:3 with lines lw 1.8      lc rgb '#444444' title "n = 0.04, scheme 3", \
       sprintf("result_supp_%s_noadv/fluxes/flux0004.csv", RESR[r])     using 2:3 with lines lw 1.2 dt 2 lc rgb '#444444' title "n = 0.04, no advection", \
       sprintf("result_supp_%s_n02/fluxes/flux0004.csv", RESR[r])       using 2:3 with lines lw 1.8      lc rgb '#e08a00' title "n = 0.02, scheme 3", \
       sprintf("result_supp_%s_n02_noadv/fluxes/flux0004.csv", RESR[r]) using 2:3 with lines lw 1.2 dt 2 lc rgb '#e08a00' title "n = 0.02, no advection"
}
unset multiplot

# ---- 図 3: 6 時間後の水深分布。左 ENC、右 4 近傍(行: 200 / 100 / 50 m) ----
# 水深 0 を白とするパレット(Fig_chichibu.plt と同じ)。4 近傍では河道網の
# 至る所に点状の湛水が残り、斜めに走る区間ごとに水が寸断されることを見せる
reset
set datafile separator whitespace
set terminal pngcairo size 1000,900 font ",11"
set output "en/figs/supp_hend.png"
set multiplot layout 3,2 title "Depth after 6 hours: left ENC, right 4-neighbor" noenhanced
set view map
set size ratio -1
set yrange [30:0]
set xrange [0:56]
set xlabel "x (km)"
set ylabel "y (km)"
set cblabel "depth (m)"
set palette defined ( -1 '#ffffff', 0 '#000090',1 '#000fff',2 '#0090ff',3 '#0fffee',4 '#90ff70',5 '#ffee00',6 '#ff7000',7 '#ee0000',8 '#7f0000')
set cbrange [0:5]
array RES3[3] = [ "200m", "100m", "50m" ]
array DXK[3]  = [ 0.2, 0.1, 0.05 ]      # セル番号 → km
array SFX3[2] = [ "", "_4nb" ]
array SLB3[2] = [ "ENC", "4-neighbor" ]
do for [r=1:3] {
  do for [s=1:2] {
    set title sprintf("%s m %s", RES3[r][1:strlen(RES3[r])-1], SLB3[s]) noenhanced
    plot sprintf("result_supp_%s%s/H9998.txt", RES3[r], SFX3[s]) matrix \
         using ($1*DXK[r]):($2*DXK[r]):($3 <= 0.05 ? NaN : $3) with image notitle
  }
}
unset multiplot
