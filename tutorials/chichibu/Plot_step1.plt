##############################################################
#
# 4 時刻の分布を 1 画面に並べて表示する(チュートリアル Step 1 用)
#
# 使い方
#
#  gnuplot Plot_step1.plt
#    通常。ディレクトリ "result" 内の水深(H)がプロットされる。
#    表示後、ターミナルで Enter を押すと終了する
#
#  gnuplot -c Plot_step1.plt V
#    変数を切り替える。引数はファイル名の接頭辞
#    (H: 水深, V: 流速絶対値, Q: 流量絶対値, Cn: クーラン数 など。
#     H 以外は f_out_* で出力を有効にした場合のみ — Step 3 参照)
#
#  gnuplot -c Plot_step1.plt H result_step1
#    第 2 引数で結果ディレクトリを指定
#
#  gnuplot -p -c Plot_step1.plt H
#    終了後もグラフが画面に残る(オプションは -p -c の順)
#
##############################################################

# コマンドライン引数: 第1引数 = 変数(接頭辞)、第2引数 = ディレクトリ
if (ARGC < 1) { var = "H" } else { var = ARG1 }
if (ARGC < 2) { dir = "result" } else { dir = ARG2 }
print "Directory: ", dir, ",  variable: ", var

# 表示する 4 時刻(ファイル番号と表題)。dt_file = 30 min の設定が前提。
# 別の時刻を見たいときはここを書き換える(9998 は最終時刻)
array num[4]
array lbl[4]
num[1] = "0001"; lbl[1] = "t = 0:30"
num[2] = "0002"; lbl[2] = "t = 1:00"
num[3] = "0006"; lbl[3] = "t = 3:00"
num[4] = "9998"; lbl[4] = "t = 6:00 (last)"

# カラーバー上限(0 なら 4 枚の最大値から自動決定)。
# 水深はデフォルト 10 m — 出口の湛水(30 m 超)でなく河川網が読める値
cbmax = (var eq "H") ? 10 : 0
if (cbmax == 0) {
  do for [i=1:4] {
    stats dir."/".var.num[i].".txt" matrix nooutput
    cbmax = (STATS_max > cbmax) ? STATS_max : cbmax
  }
}

# 乾いたセル・マスク外(値 0)は白抜きにする
blank = 0.001

set palette defined ( -1 '#ffffff', 0 '#000090',1 '#000fff',2 '#0090ff',3 '#0fffee',4 '#90ff70',5 '#ffee00',6 '#ff7000',7 '#ee0000',8 '#7f0000')
set size ratio -1
set yrange [*:*] reverse
set autoscale fix
set cbrange [0:cbmax]

# with image はラスタをセル単位で描く(pm3d は隣接セルが NaN の
# 四角形を落とすため、1 セル幅の河道が欠けることがある)
set multiplot layout 2,2 title sprintf("%s  (%s)", var, dir) noenhanced
do for [i=1:4] {
  set title sprintf("%s  %s", var, lbl[i]) noenhanced
  plot dir."/".var.num[i].".txt" matrix using 1:2:($3 <= blank ? NaN : $3) with image notitle
}
unset multiplot

pause -1 "Press Enter to quit"
