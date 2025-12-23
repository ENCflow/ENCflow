set key left top
#set key at 20,1.2
set xrange[0:50]
set yrange[0.8:1.3]
set grid
set xlabel 'x (m)' offset 0, 0.5
set ylabel 'depth (m)' offset 1, 0
#plot 'res_compare.txt' us 1:3 w l lw 1.0              lc 'red'      title 'N8-collocated grid (t=8s)', \
#     'res_compare.txt' us 1:4 w l lw 1.2 dt (40,20)   lc 'web-blue' title 'staggered grid (t=8s)'
plot 'res_compare.txt' us 1:3 w l lw 1.0              lc 'red'      title 'N8-collocated grid', \
     'res_compare.txt' us 1:4 w l lw 1.2 dt (40,20)   lc 'web-blue' title 'staggered grid'
pause -1

#set term pngcairo fontscale 2.5 linewidth 2.5 size 1000,960
#set term pngcairo fontscale 2.5 linewidth 2.5 size 1500,480
set term pngcairo fontscale 2.5 linewidth 2.5 size 1800,576
#set term pngcairo fontscale 2.5 linewidth 2.5 size 2000,640
set grid linewidth 1.5 lc 'dark-gray'
set output 'graph1.png'
#set key at 20,1.2
set xrange[0:50]
replot
unset term
unset xlabel
unset ylabel
unset grid


set key left top
#set key at 20,1.2
set xrange[0:50]
set yrange[0.8:2.1]
set grid
set xlabel 'x (m)' offset 0, 0.5
set ylabel 'depth (m)' offset 1, 0
#plot 'res_compare.txt' us 1:2 w l lw 1.0              lc 'black'      title 'initial condition (t=0s)'
plot 'res_compare.txt' us 1:2 w l lw 1.0              lc 'black'      notitle
pause -1

#set term pngcairo fontscale 2.5 linewidth 2.5 size 1000,960
#set term pngcairo fontscale 2.5 linewidth 2.5 size 1500,480
set term pngcairo fontscale 2.5 linewidth 2.5 size 1800,576
#set term pngcairo fontscale 2.5 linewidth 2.5 size 2000,640
set grid linewidth 1.5 lc 'dark-gray'
set output 'graph2.png'
#set key at 20,1.2
set xrange[0:50]
replot
unset term
unset xlabel
unset ylabel
unset grid

