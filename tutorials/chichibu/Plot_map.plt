#
set palette defined ( -1 '#ffffff', 0 '#000090',1 '#000fff',2 '#0090ff',3 '#0fffee',4 '#90ff70',5 '#ffee00',6 '#ff7000',7 '#ee0000',8 '#7f0000')
#set palette rgbformula 22,13,-31
set view map
set size ratio -1
set yrange [*:*] reverse


set title 'h (n=1)'
set cbrange[0:]
splot 'result/H0001.txt' matrix with pm3d
pause -1

set title 'V (n=1)'
unset cbrange
set cbrange[0:]
splot 'result/V0001.txt' matrix with pm3d
pause -1

set title 'Q (n=1)'
unset cbrange
set cbrange[0:]
splot 'result/Q0001.txt' matrix with pm3d
pause -1


set title 'h (n=6)'
set cbrange[0:]
splot 'result/H0006.txt' matrix with pm3d
pause -1

set title 'V (n=6)'
unset cbrange
set cbrange[0:]
splot 'result/V0006.txt' matrix with pm3d
pause -1

set title 'Q (n=6)'
unset cbrange
set cbrange[0:]
splot 'result/Q0006.txt' matrix with pm3d
pause -1


set title 'h (n=12)'
set cbrange[0:]
splot 'result/H0012.txt' matrix with pm3d
pause -1

set title 'V (n=12)'
unset cbrange
set cbrange[0:]
splot 'result/V0012.txt' matrix with pm3d
pause -1

set title 'Q (n=12)'
unset cbrange
set cbrange[0:]
splot 'result/Q0012.txt' matrix with pm3d
pause -1




set title 'h (last)'
set cbrange[0:]
splot 'result/H9998.txt' matrix with pm3d
pause -1

set title 'V (last)'
unset cbrange
set cbrange[0:6]
splot 'result/V9998.txt' matrix with pm3d
pause -1

set title 'Q (last)'
unset cbrange
set cbrange[0:]
splot 'result/Q9998.txt' matrix with pm3d
pause -1


set title 'h (max)'
unset cbrange
set cbrange[0:]
splot 'result/H9999.txt' matrix with pm3d
pause -1

set title 'V (max)'
unset cbrange
set cbrange[0:]
splot 'result/V9999.txt' matrix with pm3d
pause -1
