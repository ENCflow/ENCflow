# 補足節の図の描画(Fig_supp.sh から呼ばれる)。入力は wrk_*_prof.txt
# (0° 方向の動径プロファイル。列 1: 中心からの距離 r (m)、列 2: 水位 e (m))

set terminal pngcairo size 560,520 font ",13"
set xlabel 'distance from center r (m)'
set ylabel 'e (m)'
set xrange [30:42]
set yrange [0.95:1.3]
set key top left
set grid

# --- 静水圧のまま格子と時間刻みを細かくする ---
set output 'figs/supp_grid.png'
set title 'wave front profile,  t = 8 s,  hydrostatic'
plot 'wrk_h350_prof.txt'  with lines lc rgb 'blue'    lw 2 title 'nx = 350,  dt = 0.01', \
     'wrk_h700_prof.txt'  with lines lc rgb 'red'     lw 2 title 'nx = 700,  dt = 0.005', \
     'wrk_h1400_prof.txt' with lines lc rgb 'black'   lw 2 title 'nx = 1400,  dt = 0.0025', \
     'wrk_s2_prof.txt'    with lines lc rgb 'green' dt 2 lw 2 title 'nx = 350,  dt = 0.05,  thresh = 1.1'

# --- 非静水圧補正(物理分散)との比較 ---
set output 'figs/supp_nh.png'
set title 'wave front profile,  t = 8 s,  non-hydrostatic'
plot 'wrk_h1400_prof.txt' with lines lc rgb 'gray60' lw 4 title 'hydrostatic,  nx = 1400', \
     'wrk_n350_prof.txt'  with lines lc rgb 'blue'   lw 2 title 'non-hydrostatic,  nx = 350', \
     'wrk_n700_prof.txt'  with lines lc rgb 'red'    lw 2 title 'non-hydrostatic,  nx = 700', \
     'wrk_n1400_prof.txt' with lines lc rgb 'black'  lw 2 title 'non-hydrostatic,  nx = 1400'
