#!/bin/bash
# チュートリアル本文(README.md)の図 figs/*.png を一括再生成する。
#   使い方: ./Fig_chichibu.sh   (要 gnuplot。実行ファイルは make で用意)
# 本文の手順どおり Step 1〜5 を順に実行して結果を result_step1〜5 に
# 退避し、河床を整える前の標高での比較計算(Step 3 の設定で地盤高だけを戻したもの)を
# result_step3_filled に、窪地除去・4 近傍の比較計算(Step 2 の設定で地盤高を替え、
# 計算時間を 12 時間に延ばしたもの)を result_cmp_{filled,raw,4nb} に置いてから
# Fig_chichibu.plt で描画する。計算済みの result_* があれば計算を飛ばして描画だけ行う
# (全て計算し直す場合は rm -rf result_step* result_cmp_* してから実行)。
set -eu

mkdir -p figs en/figs
rm -f wrk_*

# --- Step 1〜5 の実行(結果を result_stepN に退避) ---
for s in 1 2 3 4 5; do
  if [ ! -d "result_step$s" ]; then
    rm -rf result
    ./encflow "param_step$s.txt"
    mv result "result_step$s"
  fi
done

# --- 河床を整えた効果の比較(Step 3 の設定で、地盤高を、河床を整える前の
#     窪地除去済みの標高に戻したもの。Step 3 の図) ---
if [ ! -d result_step3_filled ]; then
  sed -e 's/Chichibu_200m_cond.tif"  /Chichibu_200m_filled.tif"/' param_step3.txt > wrk_param_step3_filled.txt
  grep -q 'Chichibu_200m_filled.tif' wrk_param_step3_filled.txt
  rm -rf result
  ./encflow wrk_param_step3_filled.txt
  mv result result_step3_filled
fi

# --- 窪地除去・4近傍の比較計算(Step 2 の設定で、地盤高を窪地除去済みの標高に替え、
#     計算時間を 12 時間に延長。河道の水が出口の池にほぼ集まり切った状態で比べるため) ---
#   filled: fn_z を窪地除去済みの DEM に / raw: fn_z を未処理 DEM に /
#   4nb: 窪地除去済みの DEM で、対角成分をゼロにして 4 近傍相当に
for c in filled raw 4nb; do
  if [ ! -d "result_cmp_$c" ]; then
    sed -e 's/tt_c = "6 hour"/tt_c = "12 hour"/' \
        -e 's/Chichibu_200m_cond.tif"  /Chichibu_200m_filled.tif"/' param_step2.txt > "wrk_param_$c.txt"
    grep -q 'Chichibu_200m_filled.tif' "wrk_param_$c.txt"
    case $c in
      raw) sed -i -e 's/Chichibu_200m_filled.tif/Chichibu_200m_raw.tif/' "wrk_param_$c.txt" ;;
      4nb) sed -i -e '/dir_data/i\  fn_enc     = "-"           ! ENC条件設定ファイル' "wrk_param_$c.txt"
           printf '\n&%s\n  p_diagratio = 0.0        ! 対角成分ゼロ = 4近傍相当\n/\n' \
               list_enc >> "wrk_param_$c.txt" ;;
    esac
    rm -rf result
    ./encflow "wrk_param_$c.txt"
    mv result "result_cmp_$c"
  fi
done

# --- 地形図用: 流域マスク外を欠損(-9999)にした地盤高 ---
awk 'NR==FNR{for(i=1;i<=NF;i++)b[FNR,i]=$i;next}
     {for(i=1;i<=NF;i++)printf "%s ",(b[FNR,i]>0? $i : -9999); print ""}' \
  data_chichibu/Chichibu_200m_basin.txt result_step1/Z0000.txt > wrk_zmask.txt

# --- 河床の縦断(Step 2 の図): 本川の源頭のセル (54,113) から流域出口のセル (240,19) まで、
#     河道セルの 8 近傍のうち、整えた河床の勾配が最も急なセルへ順に下り、
#     「出口からの距離 (km)・窪地除去済みの標高・河床を整えた標高・セル番号 ix・iy」を書く ---
awk -v i0=54 -v j0=113 -v io=240 -v jo=19 -v dx=0.2 '
  FILENAME==ARGV[1]{for(i=1;i<=NF;i++)rw[FNR,i]=$i; ny=FNR; nx=NF; next}
  FILENAME==ARGV[2]{for(i=1;i<=NF;i++)zf[FNR,i]=$i; next}
  {for(i=1;i<=NF;i++)zc[FNR,i]=$i}
  END{
    if(!(rw[j0,i0]>0 && rw[jo,io]>0)){print "bed profile: start or outlet is not a channel cell" > "/dev/stderr"; exit 1}
    # 出口までの道のり(河道セルを 8 近傍でつないだ最短。同じ高さが続く水面で、下流の向きを決めるのに使う)
    for(j=1;j<=ny;j++)for(i=1;i<=nx;i++)if(rw[j,i]>0)d[j,i]=1e30
    d[jo,io]=0; qn=1; qj[1]=jo; qi[1]=io
    for(q=1;q<=qn;q++){j=qj[q]; i=qi[q]
      for(b=-1;b<=1;b++)for(a=-1;a<=1;a++)if((a||b) && rw[j+b,i+a]>0){
        w=(a&&b)?sqrt(2):1
        if(d[j,i]+w<d[j+b,i+a]-1e-9){d[j+b,i+a]=d[j,i]+w; qn++; qj[qn]=j+b; qi[qn]=i+a}}}
    # 源頭から下る
    j=j0; i=i0; n=0; L=0
    while(1){n++; pj[n]=j; pi[n]=i; pl[n]=L
      if(j==jo && i==io)break
      best=-1; bj=0
      for(b=-1;b<=1;b++)for(a=-1;a<=1;a++)if((a||b) && rw[j+b,i+a]>0){
        w=(a&&b)?sqrt(2):1; s=(zc[j,i]-zc[j+b,i+a])/w
        if(s<0 || (s==0 && d[j+b,i+a]>=d[j,i]))continue
        if(s>best || (s==best && d[j+b,i+a]<bd)){best=s; bj=j+b; bi=i+a; bw=w; bd=d[j+b,i+a]}}
      if(!bj || n>5000){print "bed profile: no way down at cell", i, j > "/dev/stderr"; exit 1}
      L+=bw; j=bj; i=bi}
    for(k=1;k<=n;k++)printf "%.3f %.3f %.3f %d %d\n", (L-pl[k])*dx, zf[pj[k],pi[k]], zc[pj[k],pi[k]], pi[k], pj[k]
  }' data_chichibu/Chichibu_200m_river_flowline.txt data_chichibu/Chichibu_200m_filled.txt \
     data_chichibu/Chichibu_200m_cond.txt > wrk_bed.txt

# --- 描画(日本語版 figs/ と英語版 en/figs/ を同時に再生成) ---
gnuplot Fig_chichibu.plt
gnuplot en/Fig_chichibu.plt
echo "generated figures in figs/ and en/figs/"
