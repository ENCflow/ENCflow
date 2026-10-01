# ダム破壊: 数値解と Stoker 解析解の比較(Check_stoker.py の後に実行)
#   gnuplot Plot_dambreak.plt
set datafile separator ","
set key top right
set xlabel "x (m)"
set ylabel "h (m)"
set title "dam break (wet bed): h"
plot 'result/stoker.csv' using 1:4 with lines lw 2 lc rgb "black" title "Stoker", \
     'result/stoker.csv' using 1:2 with lines lw 1 lc rgb "red" title "ENCflow"
pause -1
set ylabel "u (m/s)"
set title "dam break (wet bed): u"
plot 'result/stoker.csv' using 1:5 with lines lw 2 lc rgb "black" title "Stoker", \
     'result/stoker.csv' using 1:3 with lines lw 1 lc rgb "red" title "ENCflow"
pause -1
