##############################################################
# 
# 使い方
#
#  gnuplot Plot.plt
#    通常。ディレクトリ"result"内のデータがプロットされる
#
#  gnuplot -p Plot.plt
#    終了後も最後に表示されたグラフが画面に残る
#    途中のグラフを残す場合はターミナルで CTRL+C で終了する
#
#  gnuplot -c Plot.plt resultdir
#    ディレクトリを指定。"resultdir"内のデータがプロットされる
#
#  gnuplot -p -c Plot.plt resultdir
#    ディレクトリを指定、グラフを残す
#    オプションは -p -c の順でなければならない
#
##############################################################

# コマンドライン引数からデータのディレクトリを設定
if (ARGC < 1) {
  dir = "result"
} else {
  dir = ARG1
}
print "Directory: ", dir


# 配列を確保して空の文字列で初期化
nn = 100
array number[nn]
array file[nn]
do for [i=1:nn] {number[i] = ""}


# プロットする観測点番号を指定(任意の点数)
number[1]  = "0001"
number[2]  = "0002"
number[3]  = "0003"
number[4]  = "0004"
#number[5]  = "0005"
#number[6]  = "0006"
#number[7]  = "0007"
#number[8]  = "0008"
#number[9]  = "0009"
#number[10] = "0010"
#number[11] = "0000"
#number[12] = "0000"

#number[1]  = "0001"
#number[2]  = "0004"
#number[3]  = "0100"
#number[4]  = "0161"
#number[5]  = "0200"
#number[6]  = "0235"
#number[7]  = "0249"
#number[8]  = "0263"
#number[9]  = "0360"
#number[10] = "0400"
#number[11] = "0419"


# 指定された観測点の数を数えながらファイル名を作成
n = 0
do for [i=1:nn] {
  if (strlen(number[i]) > 0) {
    n = n + 1
    file[n] = dir."/fluxes/flux".number[n].".csv"
  }
}

set title dir noenhanced

set grid
set xlabel "時間 (hour)"
set ylabel "流量 (m^3/s)"
plot for [i=1:n] file[i] us 1:3 w l lw 1.5 title number[i]
pause -1

set grid
set xlabel "時間 (hour)"
set ylabel "水深 (m)"
plot for [i=1:n] file[i] us 1:4 w l lw 1.5 title number[i]
pause -1

set grid
set xlabel "時間 (hour)"
set ylabel "流速 (m)"
plot for [i=1:n] file[i] us 1:5 w l lw 1.5 title number[i]
pause -1


set grid
set xlabel "時間 (hour)"
set ylabel "実質流路幅 (m)"
plot for [i=1:n] file[i] us 1:6 w l lw 1.5 title number[i]
pause -1

