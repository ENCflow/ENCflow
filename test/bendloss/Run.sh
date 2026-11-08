#!/bin/bash
# bendloss: 1 セル幅水路の定常流で屈曲(90°)による損失水頭を測る実験ケース
#   ./Run.sh [接尾辞 ...]
#     接尾辞なし: 既定(param_straight.txt / param_zigzag.txt)
#     _s3  : f_advection_scheme=3、_h2: f_hcap_upwind=2、_s3h2: 両方
#   地形・マスク(z_*.txt, mask_*.txt, path_*.csv)は毎回生成する。
#   reference との比較は行わない(解析解=Manning 等流水深との比較と、
#   直線 vs 折れ線の差を Check_bendloss.py が表示する。developer.md §68.8)
#   最後に横流入つき水路(lat1r・lat2r、スキーム 3)を回し、空間変化流の解析解に対する
#   水深比が 1 ± 0.02 に入るかを Check_lateral.py が判定する(外れると終了コード 1。§68.17)
set -e
python3 Make_channel.py straight > /dev/null
python3 Make_channel.py zigzag > /dev/null
[ -e encflow ] || make -s
sufs=("$@"); [ ${#sufs[@]} -eq 0 ] && sufs=("")   # 引数なし = 既定(空接尾辞)
for suf in "${sufs[@]}"; do
  for kind in straight zigzag; do
    p=param_$kind.txt
    case $suf in
      _s3)   sed -e "s|f_advection_scheme = 1|f_advection_scheme = 3|" -e "s|result_$kind|result_${kind}_s3|" $p > param_${kind}_s3.txt; p=param_${kind}_s3.txt ;;
      _h2)   sed -e "s|f_hcap_upwind = 1|f_hcap_upwind = 2|" -e "s|result_$kind|result_${kind}_h2|" $p > param_${kind}_h2.txt; p=param_${kind}_h2.txt ;;
      _s3h2) sed -e "s|f_advection_scheme = 1|f_advection_scheme = 3|" -e "s|f_hcap_upwind = 1|f_hcap_upwind = 2|" -e "s|result_$kind|result_${kind}_s3h2|" $p > param_${kind}_s3h2.txt; p=param_${kind}_s3h2.txt ;;
    esac
    echo "=== $p"; ./encflow $p | tail -2 | head -1
  done
done
python3 Check_bendloss.py "${sufs[@]}"

# 横流入つき水路(合否つき): 片側(lat1r。行 1・2 は無効セル)と両側(lat2r)の横流入
python3 Make_lateral.py > /dev/null
for k in lat1r lat2r; do
  sed -e "s|f_advection_scheme = 1|f_advection_scheme = 3|" -e "s|result_${k}_s1|result_${k}_s3|" param_${k}_s1.txt > param_${k}_s3.txt
  echo "=== param_${k}_s3.txt"; ./encflow param_${k}_s3.txt | tail -2 | head -1
  python3 Check_lateral.py $k _s3 --tol 0.02
done
