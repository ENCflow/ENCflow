# チュートリアル本文(README.md)の図を figs/*.png に描画する。
# 事前に Fig_chichibu.sh が各 Step の計算を実行し、結果を
# result_step1 〜 result_step6, result_raw に、前処理済みデータを
# wrk_* に用意していることを前提とする(単体では実行しない)。

set datafile separator whitespace
set terminal pngcairo size 760,440 font ",11"

# 分布図の共通設定(格子番号→km 換算、行順=北→南なので y 反転)
kx(i) = i * 0.2
set palette defined ( 0 '#000090',1 '#000fff',2 '#0090ff',3 '#0fffee',4 '#90ff70',5 '#ffee00',6 '#ff7000',7 '#ee0000',8 '#7f0000')

# ---- 地形(流域外は欠損) ----
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

# ---- Step 1: 最終時刻の水深(閉流域の湛水) ----
set output "figs/step1_hend.png"
set cblabel "水深 (m)"
set cbrange [0:10]
set title "Step 1: 6 時間後の水深(出口に湛水)"
splot 'result_step1/H9998.txt' matrix using (kx($1)):(kx($2)):($3 <= 0.01 ? NaN : $3) with pm3d notitle

# ---- Step 1: 窪地除去の有無(最大水深の比較) ----
set output "figs/step1_hmax_filled.png"
set cbrange [0:10]
set title "最大水深: 窪地除去済み DEM(filled)"
splot 'result_step2/H9999.txt' matrix using (kx($1)):(kx($2)):($3 <= 0.01 ? NaN : $3) with pm3d notitle

set output "figs/step1_hmax_raw.png"
set title "最大水深: 未処理 DEM(raw)"
splot 'result_raw/H9999.txt' matrix using (kx($1)):(kx($2)):($3 <= 0.01 ? NaN : $3) with pm3d notitle

# ---- Step 6: 湛水の解消(最終時刻の水深) ----
set output "figs/step6_hend_step5.png"
set cbrange [0:10]
set title "Step 5: 6 時間後の水深(出口なし)"
splot 'result_step5/H9998.txt' matrix using (kx($1)):(kx($2)):($3 <= 0.01 ? NaN : $3) with pm3d notitle

set output "figs/step6_hend.png"
set title "Step 6: 6 時間後の水深(完全排水口あり)"
splot 'result_step6/H9998.txt' matrix using (kx($1)):(kx($2)):($3 <= 0.01 ? NaN : $3) with pm3d notitle

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
plot 'result_step6/fluxes/flux0004.csv' using 2:3 with lines lc rgb "#a0c8e8" title "1 分値(生)", \
     ''                                 using ($2 - (N-1)/2.0):(ma($3)) with lines lw 2 lc rgb "#c04040" title sprintf("%d 分移動平均(中央寄せ)", N)

set output "figs/step6_osc_zoom.png"
set title "同 拡大(120〜240 min)"
set xrange [120:240]
set yrange [1500:3200]
do for [i=1:N] { A[i] = 0.0 }
plot 'result_step6/fluxes/flux0004.csv' using 2:3 with lines lc rgb "#a0c8e8" title "1 分値(生)", \
     ''                                 using ($2 - (N-1)/2.0):(ma($3)) with lines lw 2 lc rgb "#c04040" title sprintf("%d 分移動平均(中央寄せ)", N)
