set xrange[0:48]
set xtics 6
#set key left top

set grid
set xlabel "時間 (時)"
set ylabel "流量 (m^3/s)"
plot 'result/fluxes/flux0001.csv' us ($2/60):3 w l lw 1.5 title "上流部", \
     'result/fluxes/flux0002.csv' us ($2/60):3 w l lw 1.5 dt (50,15) title "中流部", \
     'result/fluxes/flux0003.csv' us ($2/60):3 w l lw 1.5 dt (50,15,15,15) title "下流部"
pause -1


#set term pngcairo fontscale 2.5 linewidth 2.5 size 1280,960
set term pngcairo fontscale 2.5 linewidth 2.5 size 2000,640
#set term pngcairo fontscale 2.5 linewidth 2.5 size 2000,1000
set grid linewidth 1.5 lc 'dark-gray'
set output 'graph.png'
set yrange[0:]


replot
unset term
unset xlabel
unset ylabel
unset grid
