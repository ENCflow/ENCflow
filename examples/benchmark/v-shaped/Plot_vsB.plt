set yrange[-0.5:]
set grid
set xlabel '時間 (分)'
set ylabel '流量 (m^3/s)'
plot 'result_5Stg/flux01.txt' us 1:2 w l lw 1.0                   lc 'red'      title 'dx = 5m', \
     'result_10Stg/flux01.txt' us 1:2 w l lw 1.2 dt (40,20)       lc 'dark-green'    title 'dx = 10m', \
     'result_20Stg/flux01.txt' us 1:2 w l lw 1.2 dt (40,15,15,15) lc 'web-blue' title 'dx = 20m', \
     'analytical.txt' us 1:3 pt 6 ps 2 lw 1.0 lc 'black' title '理論値'
pause -1

#set term pngcairo fontscale 2.5 linewidth 2.5 size 1280,960
#set term pngcairo fontscale 2.5 linewidth 2.5 size 2000,640
set term pngcairo fontscale 2.5 linewidth 2.5 size 2000,1280
set grid linewidth 1.5 lc 'dark-gray'
set output 'graph1B.png'
replot
unset term
unset xlabel
unset ylabel
unset grid


set grid
set xlabel '時間 (分)'
set ylabel '流量 (m^3/s)'
plot 'result_5Edc/flux01.txt' us 1:2 w l lw 1.0                   lc 'red'      title 'dx = 5m', \
     'result_10Edc/flux01.txt' us 1:2 w l lw 1.2 dt (40,20)       lc 'dark-green'    title 'dx = 10m', \
     'result_20Edc/flux01.txt' us 1:2 w l lw 1.2 dt (40,15,15,15) lc 'web-blue' title 'dx = 20m', \
     'analytical.txt' us 1:3 pt 6 ps 2 lw 1.0 lc 'black' title '理論値'
pause -1

#set term pngcairo fontscale 2.5 linewidth 2.5 size 1280,960
#set term pngcairo fontscale 2.5 linewidth 2.5 size 2000,640
set term pngcairo fontscale 2.5 linewidth 2.5 size 2000,1280
set grid linewidth 1.5 lc 'dark-gray'
set output 'graph2B.png'
replot
unset term
unset xlabel
unset ylabel
unset grid

