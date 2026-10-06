# チュートリアル本文(README.md)の図を figs/*.png に描画する。
# 事前に Fig_chichibu.sh が各 Step の計算を実行し、結果を
# result_step1 〜 result_step6, result_cmp_* に、前処理済みデータを
# wrk_* に用意していることを前提とする(単体では実行しない)。

set datafile separator whitespace
set terminal pngcairo size 760,440 font ",11"

# 分布図の共通設定(格子番号→km 換算、行順=北→南なので y 反転)
kx(i) = i * 0.2

# ---- 地形(流域外は欠損) ----
set palette defined ( 0 '#000090',1 '#000fff',2 '#0090ff',3 '#0fffee',4 '#90ff70',5 '#ffee00',6 '#ff7000',7 '#ee0000',8 '#7f0000')
set output "figs/step1_z.png"
set view map
set size ratio -1
set xlabel "x (km)"
set ylabel "y (km)"
set yrange [30:0]
set xrange [0:56]
set cblabel "標高 (m)"
set cbrange [0:2600]
set title "地形(流域マスク内)"
splot 'wrk_zmask.txt' matrix using (kx($1)):(kx($2)):($3 < -9000 ? NaN : $3) with pm3d notitle

# ---- Step 2: 流域マスクと河道マスク(入力データそのもの。計算結果は不要) ----
# マスク値 1 のセルだけを塗り、0 は白抜き(NaN)にする。2 層を重ねる
# 図では、流域を薄い灰色、河道を青で描く
DIR = "data_chichibu"
BASIN = DIR."/Chichibu_200m_basin.txt"
RIVER = DIR."/Chichibu_200m_river.txt"
set view map
set size ratio -1
set xlabel "x (km)"
set ylabel "y (km)"
set yrange [30:0]
set xrange [0:56]
unset colorbox
set palette defined (1 '#c8d3dd', 2 '#1f5fbf')
set cbrange [1:2]

set output "figs/step2_mask_basin.png"
set title "流域マスク Chichibu_200m_basin(1: 流域内 = 計算対象セル)" noenhanced
plot BASIN matrix using (kx($1)):(kx($2)):($3 > 0 ? 1 : NaN) with image notitle

set output "figs/step2_mask_river.png"
set title "河道マスク Chichibu_200m_river(1: 河道セル。幅 1 セルの線)" noenhanced
plot RIVER matrix using (kx($1)):(kx($2)):($3 > 0 ? 2 : NaN) with image notitle

# ---- Step 3: 河道マスクに測線とプローブを重ねる ----
# param_step3.txt の flxy / pbxy をそのまま書き写す(セル番号、1 スタート)。
# 列: 測線番号, 右岸 ix, 右岸 iy, 左岸 ix, 左岸 iy, プローブ ix, プローブ iy
$TR << EOD
1   82 107   82 103    82 105
2  107 103  107 100   107 102
3  147 105  147 102   147 104
4  216  43  216  37   216  39
EOD
# セル番号 → km(セル中心。matrix の添字は 0 始まりなので番号 −1)
cx(i) = (i - 1) * 0.2
cy(j) = (j - 1) * 0.2

set terminal pngcairo size 900,640 font ",11"
set output "figs/step3_map.png"
set multiplot

# 上段: 全体図
set origin 0, 0.42
set size 1, 0.58
set xlabel "x (km)"
set ylabel "y (km)"
set yrange [30:0]
set xrange [0:56]
set xtics 10
set ytics 5
set title "Step 3: 河道マスクに重ねた測線(赤、右岸 → 左岸)とプローブ(○)" noenhanced
plot BASIN matrix using (kx($1)):(kx($2)):($3 > 0 ? 1 : NaN) with image notitle, \
     RIVER matrix using (kx($1)):(kx($2)):($3 > 0 ? 2 : NaN) with image notitle, \
     $TR using (cx($2)):(cy($3)):(cx($4)-cx($2)):(cy($5)-cy($3)) with vectors nohead lw 3 lc rgb '#d02020' notitle, \
     $TR using (cx($2)+1.0):(cy($3)+1.4):(sprintf("%d", $1)) with labels font ",12" tc rgb '#d02020' notitle

# 下段: 各測線の拡大(軸はセル番号。param_step3.txt の数値と直接対応する)
set size 0.25, 0.42
set xlabel "ix(セル番号)"
set ylabel "iy(セル番号)"
set xtics 4
set ytics 4
# 拡大の中心(各測線の ix と、両端 iy の中点)
array XC[4] = [ 82, 107, 147, 216 ]
array YC[4] = [ 104.5, 101.5, 103.5, 40 ]
do for [i=1:4] {
  set origin (i-1) * 0.25, 0
  set xrange [XC[i]-7.5:XC[i]+7.5]
  set yrange [YC[i]+7.5:YC[i]-7.5]
  set title sprintf("測線 %d・プローブ %d", i, i) noenhanced
  plot BASIN matrix using ($1+1):($2+1):($3 > 0 ? 1 : NaN) with image notitle, \
       RIVER matrix using ($1+1):($2+1):($3 > 0 ? 2 : NaN) with image notitle, \
       $TR every ::i-1::i-1 using 2:3:($4-$2):($5-$3) with vectors head filled size 0.6,25 lw 3 lc rgb '#d02020' notitle, \
       $TR every ::i-1::i-1 using 6:7 with points pt 6 ps 2 lw 2 lc rgb '#000000' notitle
}
unset multiplot

# ---- マスク・測線図の設定を戻す(以降は 1 枚 760x440、カラーバーあり) ----
set terminal pngcairo size 760,440 font ",11"
set origin 0, 0
set size ratio -1 1, 1
set colorbox
set xtics autofreq
set ytics autofreq
set xlabel "x (km)"
set ylabel "y (km)"
set xrange [0:56]
set yrange [30:0]

# ---- ここから水深図の共通設定 ----
# 水深 0 を白とするパレット(水が無い場所を濃色にしない)。浅い水は
# ほぼ白に沈み、湛水だけが色になる — 「水が出払った流域は真っ白、
# 溜まった場所だけ色」という読みを意図した配色。描画はセル単位の
# with image(pm3d は隣接セルが NaN の四角形を落とすため 1 セル幅の
# 河道が欠けることがある)
set palette defined ( -1 '#ffffff', 0 '#000090',1 '#000fff',2 '#0090ff',3 '#0fffee',4 '#90ff70',5 '#ffee00',6 '#ff7000',7 '#ee0000',8 '#7f0000')
set cblabel "水深 (m)"
set cbrange [0:10]

# ---- Step 1: 最終時刻の水深(閉流域の湛水) ----
set output "figs/step1_hend.png"
set title "Step 1: 6 時間後の水深(出口に湛水)"
plot 'result_step1/H9998.txt' matrix using (kx($1)):(kx($2)):($3 <= 0.01 ? NaN : $3) with image notitle

# ---- Step 1: 窪地除去の有無(12 時間後の水深の比較。計算時間を延長した比較計算) ----
set output "figs/step1_hend_filled.png"
set title "12 時間後の水深: 窪地除去済み DEM(filled)"
plot 'result_cmp_filled/H9998.txt' matrix using (kx($1)):(kx($2)):($3 <= 0.01 ? NaN : $3) with image notitle

set output "figs/step1_hend_raw.png"
set title "12 時間後の水深: 未処理 DEM(raw)"
plot 'result_cmp_raw/H9998.txt' matrix using (kx($1)):(kx($2)):($3 <= 0.01 ? NaN : $3) with image notitle

# ---- Step 1: 4近傍計算との比較(D8 窪地除去と 8 方向交換の相性) ----
set output "figs/step1_hend_4nb.png"
set title "12 時間後の水深: filled DEM を 4 近傍で計算(p_diagratio = 0)" noenhanced
plot 'result_cmp_4nb/H9998.txt' matrix using (kx($1)):(kx($2)):($3 <= 0.01 ? NaN : $3) with image notitle

# ---- Step 6: 湛水の解消(最終時刻の水深) ----
set output "figs/step6_hend_step5.png"
set title "Step 5: 6 時間後の水深(出口なし)"
plot 'result_step5/H9998.txt' matrix using (kx($1)):(kx($2)):($3 <= 0.01 ? NaN : $3) with image notitle

set output "figs/step6_hend.png"
set title "Step 6: 6 時間後の水深(完全排水口あり)"
plot 'result_step6/H9998.txt' matrix using (kx($1)):(kx($2)):($3 <= 0.01 ? NaN : $3) with image notitle

# ---- ここからハイドログラフ(CSV はカンマ区切り) ----
reset
set datafile separator comma
set terminal pngcairo size 760,440 font ",11"
set grid
set xlabel "時間 (min)"
set ylabel "流量 (m^3/s)"

# ---- Step 3: 4 本の測線(上流→下流の流量の成長) ----
set output "figs/step3_transects.png"
set title "Step 3: 各測線のハイドログラフ(上流 1 → 下流 4)"
plot for [i=1:4] sprintf('result_step3/fluxes/flux000%d.csv', i) using 2:3 with lines lw 1.5 title sprintf("測線 %d", i)

# ---- Step 4: 風上化と限界水深の調整の効果 ----
set output "figs/step4_hydro.png"
set title "Step 4: パラメータ調整の効果(測線 4)"
plot 'result_step3/fluxes/flux0004.csv' using 2:3 with lines lw 1.5 title "Step 3(調整前)", \
     'result_step4/fluxes/flux0004.csv' using 2:3 with lines lw 1.5 title "Step 4(調整後)"

# ---- Step 5: 遮断・浸透による流出の減少 ----
set output "figs/step5_hydro.png"
set title "Step 5: 降雨遮断と地下浸透の効果(測線 4)"
plot 'result_step4/fluxes/flux0004.csv' using 2:3 with lines lw 1.5 title "Step 4(損失なし)", \
     'result_step5/fluxes/flux0004.csv' using 2:3 with lines lw 1.5 title "Step 5(遮断+浸透)"

# ---- Step 6: 流量振動と移動平均 ----
# 移動平均(窓 N 点 = N 分)。gnuplot 5.2 以降の配列機能を使用
N = 11
array A[N]
ma(x) = (A[(int($0) % N) + 1] = x, $0 < N-1 ? NaN : (sum [i=1:N] A[i]) / N)

set output "figs/step6_osc.png"
set title "Step 6: 1 分値の流量振動と移動平均(測線 4)"
set xrange [60:360]
plot 'result_step6/fluxes/flux0004.csv' using 2:3 with lines lc rgb "#4477aa" title "1 分値(生)", \
     ''                                 using ($2 - (N-1)/2.0):(ma($3)) with lines lw 2 lc rgb "#c04040" title sprintf("%d 分移動平均(中央寄せ)", N)

set output "figs/step6_osc_zoom.png"
set title "同 拡大(120〜240 min)"
set xrange [120:240]
set yrange [2000:4400]
do for [i=1:N] { A[i] = 0.0 }
plot 'result_step6/fluxes/flux0004.csv' using 2:3 with lines lc rgb "#4477aa" title "1 分値(生)", \
     ''                                 using ($2 - (N-1)/2.0):(ma($3)) with lines lw 2 lc rgb "#c04040" title sprintf("%d 分移動平均(中央寄せ)", N)
