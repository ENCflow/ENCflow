set grid
set xlabel '時間 (分)'
set ylabel '流量 (m^3/s)'
plot 'result_5xStg/flux01.txt' us 1:2 w l lw 1.0                   lc 'red'      title 'dx = 5m', \
     'result_10xStg/flux01.txt' us 1:2 w l lw 1.2 dt (40,20)       lc 'dark-green'    title 'dx = 10m', \
     'result_20xStg/flux01.txt' us 1:2 w l lw 1.2 dt (40,15,15,15) lc 'web-blue' title 'dx = 20m'
pause -1

#set term pngcairo fontscale 2.5 linewidth 2.5 size 1280,960
set term pngcairo fontscale 2.5 linewidth 2.5 size 2000,640
set grid linewidth 1.5 lc 'dark-gray'
set output 'graph1.png'
replot
unset term
unset xlabel
unset ylabel
unset grid


set grid
set xlabel '時間 (分)'
set ylabel '流量 (m^3/s)'
plot 'result_5xEdc/flux01.txt' us 1:2 w l lw 1.0                   lc 'red'      title 'dx = 5m', \
     'result_10xEdc/flux01.txt' us 1:2 w l lw 1.2 dt (40,20)       lc 'dark-green'    title 'dx = 10m', \
     'result_20xEdc/flux01.txt' us 1:2 w l lw 1.2 dt (40,15,15,15) lc 'web-blue' title 'dx = 20m'
pause -1

#set term pngcairo fontscale 2.5 linewidth 2.5 size 1280,960
set term pngcairo fontscale 2.5 linewidth 2.5 size 2000,640
set grid linewidth 1.5 lc 'dark-gray'
set output 'graph2.png'
replot
unset term
unset xlabel
unset ylabel
unset grid

