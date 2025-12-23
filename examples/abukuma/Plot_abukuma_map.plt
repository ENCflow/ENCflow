set palette defined ( -1 '#ffffff', 0 '#000090',1 '#000fff',2 '#0090ff',3 '#0fffee',4 '#90ff70',5 '#ffee00',6 '#ff7000',7 '#ee0000',8 '#7f0000')
#set palette rgbformula 22,13,-31
set view map
set size ratio -1


set title 'depth (it = 1)'
set cbrange[0:]
splot 'result/H0001.txt' matrix with pm3d notitle
pause -1

set title 'velocity (it = 1)'
set cbrange[0:]
splot 'result/V0001.txt' matrix with pm3d notitle
pause -1

unset cbrange
set title 'depth (it = last)'
set cbrange[0:]
splot 'result/H9998.txt' matrix with pm3d notitle
pause -1

set title 'velocity (it = last)'
set cbrange[0:]
splot 'result/V9998.txt' matrix with pm3d notitle
pause -1

unset cbrange
set title 'depth (max)'
set cbrange[0:]
splot 'result/H9999.txt' matrix with pm3d notitle
pause -1

set title 'velocity (max)'
set cbrange[0:]
splot 'result/V9999.txt' matrix with pm3d notitle
pause -1
