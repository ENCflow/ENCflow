set grid
set xlabel '時間 (分)'
set ylabel '流量 (m^3/s)'
plot 'result/flux01.txt' us 1:2 w l lw 1.0                  lc 'red'      title '流域出口' #, \
#     'result/flux02.txt' us 1:2 w l lw 1.0 dt (40,20)       lc 'red'      title '流域中央', \
#     'result/flux03.txt' us 1:2 w l lw 1.2 dt (40,15,15,15) lc 'web-blue' title '斜面下端'
pause -1

set xlabel '時間 (分)'
set ylabel '水深 (m)'
plot 'result/probe01.txt' us 1:3 w l lw 1.0                  lc 'red'      title '流域出口' #, \
pause -1
pause -1

set xlabel '時間 (分)'
set ylabel '流速 (m/s)'
plot 'result/probe01.txt' us 1:6 w l lw 1.0                  lc 'red'      title '流域出口' #, \
pause -1
pause -1


set term pngcairo fontscale 2.5 linewidth 2.5 size 1280,960
set grid linewidth 1.5 lc 'dark-gray'
set output 'graph.png'
replot
unset term
unset xlabel
unset ylabel
unset grid


set palette rgbformula 22,13,-31
set title 'water surface elevation (m)'
splot 'result/e9998.txt' matrix with pm3d 
pause -1

set view map
set size square
set title 'depth (m)'
splot 'result/h9998.txt' matrix with pm3d
pause -1

set title 'velocity (m/s)'
splot 'result/vv9998.txt' matrix with pm3d
pause -1


