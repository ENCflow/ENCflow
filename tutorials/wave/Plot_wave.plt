set palette rgbformula 22,13,-31
set title 'e'
set zrange[:1.3]
splot 'result/E9998.txt' matrix with pm3d
pause -1

set view map
set size square
set title 'e'
set format x ""
set format y ""
set format z ""
set xtics 50
set ytics 50
set ztics 0.1
splot 'result/E9998.txt' matrix with pm3d
pause -1

