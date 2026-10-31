#!/bin/bash
# nhbottom 構成 1 の線形理論検定: 静水圧(param_h.txt)・NH 加速度項なし(param_n.txt)・
# NH 加速度項あり(param.txt)の 3 ケースを uplift ドライバで実行し、Check_nhbottom.py で
# 先頭波(x = xc + 200 m)を各モデルの線形理論(Theory.py)と比べる
#   ./Run_theory.sh     (逐次で約 1.5 分。Check_nhbottom.py は numpy を使う)
# 回帰テスト(reference との比較)は ./Run.sh。図表は検定のあと python3 Fig.py
sdir=$(dirname "$(readlink -f "$0")")
cd "$sdir" || exit 1
../Scripts/Check_mode.sh serial || exit 1
make -s uplift || exit 1
for p in param param_h param_n; do
    ./uplift $p.txt uplift.txt > Screen_$p.log 2>&1 \
        || { echo "ERROR: $p.txt run failed (see Screen_$p.log)" >&2; exit 1; }
done
python3 ./Check_nhbottom.py || exit 1
