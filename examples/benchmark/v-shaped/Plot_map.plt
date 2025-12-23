#
set palette defined ( -1 '#ffffff', 0 '#000090',1 '#000fff',2 '#0090ff',3 '#0fffee',4 '#90ff70',5 '#ffee00',6 '#ff7000',7 '#ee0000',8 '#7f0000')
#set palette rgbformula 22,13,-31
set view map
set size ratio -1
set yrange [*:*] reverse


#set title 'V (n=9999)'
#set cbrange[0:]
##set cbrange[0:1]
#splot 'result/V9999.txt' matrix with pm3d
#pause -1

set title 'Q (n=9999)'
set cbrange[0:]
set cbrange[0:0.003]
splot 'result/Q9999.txt' matrix with pm3d
pause -1
