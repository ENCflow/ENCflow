##############################################################
#
# 最終時刻と期間最大の分布 6 枚を 1 画面に並べて表示する
# (チュートリアル Step 3 用。param_step3.txt の f_out_* 設定が前提)
#
#   上段: 最終時刻の 水深 H9998・流速 V9998・流量 Q9998
#   下段: 期間最大の 水深 H9999・流速 V9999、最終時刻のクーラン数 Cn9998
#
# 使い方
#
#  gnuplot Plot_step3.plt
#    通常。ディレクトリ "result" 内のデータがプロットされる。
#    表示後、ターミナルで Enter を押すと終了する
#
#  gnuplot -c Plot_step3.plt result_step3
#    ディレクトリを指定
#
#  gnuplot -p -c Plot_step3.plt result
#    終了後もグラフが画面に残る(オプションは -p -c の順)
#
##############################################################

# コマンドライン引数からデータのディレクトリを設定
if (ARGC < 1) { dir = "result" } else { dir = ARG1 }
print "Directory: ", dir

# 表示するファイルと表題・カラーバー上限(0 なら自動)。
# 水深はデフォルト 10 m — 出口の湛水(30 m 超)でなく河川網が読める値
array num[6]
array lbl[6]
array cmax[6]
num[1] = "H9998";  lbl[1] = "h last (m)";        cmax[1] = 10
num[2] = "V9998";  lbl[2] = "V last (m/s)";      cmax[2] = 0
num[3] = "Q9998";  lbl[3] = "Q last (m^2/s)";    cmax[3] = 0
num[4] = "H9999";  lbl[4] = "h max (m)";         cmax[4] = 10
num[5] = "V9999";  lbl[5] = "V max (m/s)";       cmax[5] = 0
num[6] = "Cn9998"; lbl[6] = "Cn last (-)";       cmax[6] = 0

# 乾いたセル・マスク外(値 0)は白抜きにする
blank = 0.001

set palette defined ( -1 '#ffffff', 0 '#000090',1 '#000fff',2 '#0090ff',3 '#0fffee',4 '#90ff70',5 '#ffee00',6 '#ff7000',7 '#ee0000',8 '#7f0000')
set size ratio -1
set yrange [*:*] reverse
set autoscale fix

# with image はラスタをセル単位で描く(pm3d は隣接セルが NaN の
# 四角形を落とすため、1 セル幅の河道が欠けることがある)
set multiplot layout 2,3 title dir noenhanced
do for [i=1:6] {
  c = cmax[i]
  if (c == 0) {
    stats dir."/".num[i].".txt" matrix nooutput
    c = STATS_max
  }
  set cbrange [0:c]
  set title lbl[i]
  plot dir."/".num[i].".txt" matrix using 1:2:($3 <= blank ? NaN : $3) with image notitle
}
unset multiplot

pause -1 "Press Enter to quit"
