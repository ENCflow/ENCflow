# チュートリアル本文(README.md)の図の描画(Fig_wave.sh から呼ばれる)
# 入力は Fig_wave.sh が退避した wrk_*.txt。軸はセル添字を座標 (m) に換算
# (dx = lx/nx = 1/3 m)。カラースケールは全図共通(壁セルの 1.5 は飽和)。

set terminal pngcairo size 560,520 font ",13"
set palette rgbformula 22,13,-31
unset key
dx = 100.0 / 300.0

# --- 初期水位(3D 表示) ---
set output 'figs/step1_init.png'
set title 'water surface e (m),  t = 0 s'
set xlabel 'x (m)' offset 0,-1
set ylabel 'y (m)' offset -1,0
set zrange [0.8:2.1]
set cbrange [0.8:2.1]
set xtics 50 offset 0,-0.5
set ytics 50
set ztics 0.5
splot 'wrk_step1_E0000.txt' matrix using ($1*dx):($2*dx):3 with pm3d

# --- 以降は平面図(共通設定) ---
set view map
set size square
unset xlabel
unset ylabel
set format x ""
set format y ""
set xtics 50
set ytics 50
set cbrange [0.85:1.25]
set cbtics 0.1
unset zrange

set output 'figs/step1_dt001.png'
set title 'e (m),  t = 8 s,  dt = 0.01 s'
splot 'wrk_step1_dt001_E9998.txt' matrix using ($1*dx):($2*dx):3 with pm3d

set output 'figs/step1_dt005.png'
set title 'e (m),  t = 8 s,  dt = 0.05 s'
splot 'wrk_step1_dt005_E9998.txt' matrix using ($1*dx):($2*dx):3 with pm3d

set output 'figs/step2_adprunge.png'
set title 'e (m),  t = 8 s,  dt = 0.05 s,  thresh = 1.1'
splot 'wrk_step2_E9998.txt' matrix using ($1*dx):($2*dx):3 with pm3d

# --- 動径プロファイル(0°方向 vs 45°方向。同心円なら両者は一致する) ---
unset view
unset size
set size ratio 0.62
set format x "%g"
set format y "%g"
set xlabel 'distance from center r (m)'
set ylabel 'e (m)'
set xtics 5
set ytics 0.1
set xrange [28:44]
set yrange [0.95:1.3]
set key top left samplen 3

set output 'figs/step1_profile.png'
set title 'wave front profile,  t = 8 s,  dt = 0.05 s'
plot 'wrk_step1_dt001_prof.txt' index 0 with lines lc rgb 'gray60' lw 4 title 'dt = 0.01 (reference)', \
     'wrk_step1_dt005_prof.txt' index 0 with lines lc rgb 'blue'   lw 2 title 'dt = 0.05,  0 deg', \
     'wrk_step1_dt005_prof.txt' index 1 with lines lc rgb 'red'    lw 2 title 'dt = 0.05,  45 deg'

set output 'figs/step2_profile.png'
set title 'wave front profile,  t = 8 s,  dt = 0.05 s,  thresh = 1.1'
plot 'wrk_step1_dt001_prof.txt' index 0 with lines lc rgb 'gray60' lw 4 title 'dt = 0.01 (reference)', \
     'wrk_step2_prof.txt'       index 0 with lines lc rgb 'blue'   lw 2 title 'thresh = 1.1,  0 deg', \
     'wrk_step2_prof.txt'       index 1 with lines lc rgb 'red'    lw 2 title 'thresh = 1.1,  45 deg'

# --- 平面図の設定へ戻す ---
set view map
set size square
unset xlabel
unset ylabel
set format x ""
set format y ""
set xtics 50
set ytics 50
set xrange [*:*]
set yrange [*:*]
unset key

set output 'figs/step2_tt14.png'
set title 'e (m),  t = 14 s,  closed walls'
splot 'wrk_step2_tt14_E9998.txt' matrix using ($1*dx):($2*dx):3 with pm3d

set output 'figs/step3_radiation.png'
set title 'e (m),  t = 14 s,  radiation boundaries'
splot 'wrk_step3_E9998.txt' matrix using ($1*dx):($2*dx):3 with pm3d

set output 'figs/step4_solid.png'
set title 'e (m),  t = 14 s,  solid wall (2 cells)'
splot 'wrk_step4_solid_E9998.txt' matrix using ($1*dx):($2*dx):3 with pm3d

set output 'figs/step4_leaky.png'
set title 'e (m),  t = 14 s,  leaky wall (1 cell)'
splot 'wrk_step4_leaky_E9998.txt' matrix using ($1*dx):($2*dx):3 with pm3d
