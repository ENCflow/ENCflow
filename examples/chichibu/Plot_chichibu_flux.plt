#set xrange[0:360]
#set key left top

set grid
#set xlabel "時間 (分)"
#set xtics 60

set xlabel "時間 (時)"
set xtics 1

set ylabel "流量 (m^3/s)"
plot 'result/fluxes/flux0001.csv' us 1:3 w l lw 1.5 title "地点A", \
     'result/fluxes/flux0002.csv' us 1:3 w l lw 1.5 dt (50,15) title "地点B", \
     'result/fluxes/flux0003.csv' us 1:3 w l lw 1.5 dt (50,15,15,15) title "地点C", \
     'result/fluxes/flux0004.csv' us 1:3 w l lw 1.5 dt (30,10) title "地点D"
pause -1

#set ylabel "川幅 (m)"
#plot 'result/fluxes/flux0001.csv' us 4:3 w l lw 1.5 title "地点A", \
#     'result/fluxes/flux0002.csv' us 4:3 w l lw 1.5 dt (50,15) title "地点B", \
#     'result/fluxes/flux0003.csv' us 4:3 w l lw 1.5 dt (50,15,15,15) title "地点C", \
#     'result/fluxes/flux0004.csv' us 4:3 w l lw 1.5 dt (30,10) title "地点D"
#pause -1


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
