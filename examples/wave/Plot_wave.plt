set palette rgbformula 22,13,-31
splot 'result/E9998.txt' matrix with pm3d
pause -1



set view map
set size square
set title 'h'

set format x ""
set format y ""
set format z ""
set xtics 50
set ytics 50
set ztics 0.1

splot 'result/H9999.txt' matrix with pm3d
pause -1

#set title 'u'
#splot 'result/u9998.txt' matrix with pm3d
#pause -1
#set title 'v'
#splot 'result/v9998.txt' matrix with pm3d
#pause -1

#set title 'm'
#splot 'result/m9998.txt' matrix with pm3d
#pause -1
#set title 'n'
#splot 'result/n9998.txt' matrix with pm3d
#pause -1

set title 'V'
splot 'result/V9998.txt' matrix with pm3d
pause -1


