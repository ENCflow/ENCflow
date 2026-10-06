##############################################################
#
# 測線流量の 1 分値に移動平均を重ねて表示する(チュートリアル Step 6 用)
#
# 使い方
#
#  gnuplot -p -c Plot_ma.plt result
#    ディレクトリ "result" 内の測線 4(fluxes/flux0004.csv)を表示。
#    -p で終了後もグラフが画面に残る(オプションは -p -c の順)
#
#  gnuplot -p -c Plot_ma.plt result_step6 2
#    第 2 引数で測線番号を指定(省略時 4)
#
#  gnuplot -p -c Plot_ma.plt result 4 21
#    第 3 引数で窓幅(点数)を指定(省略時 11。出力が 1 分刻みなら
#    そのまま「分」になる)
#
# 中身の読み方は README.md の Step 6 を参照。gnuplot 5.2 以降(配列機能)が必要
#
##############################################################

if (ARGC < 1) { dir = "result" } else { dir = ARG1 }
if (ARGC < 2) { tr = 4 } else { tr = int(ARG2) }
if (ARGC < 3) { N = 11 } else { N = int(ARG3) }
file = sprintf("%s/fluxes/flux%04d.csv", dir, tr)
print "File: ", file, ",  window: ", N, " points"

set datafile separator comma     # 結果の CSV はカンマ区切り
array A[N]                       # 直近 N 点を入れるリングバッファ
# 行番号 $0 を N で割った余りの位置に値を入れ、N 点そろったら平均を返す
ma(x) = (A[(int($0) % N) + 1] = x, $0 < N-1 ? NaN : (sum [i=1:N] A[i]) / N)

set grid
set xlabel "時間 (min)"
set ylabel "流量 (m^3/s)"
set title sprintf("測線 %d: 1 分値と %d 分移動平均(中央寄せ)", tr, N) noenhanced
plot file using 2:3 with lines title "1 分値", \
     ""   using ($2 - (N-1)/2.0):(ma($3)) with lines lw 2 title sprintf("%d 分移動平均", N)

pause -1 "Press Enter to quit"
