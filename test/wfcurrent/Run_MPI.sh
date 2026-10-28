#!/bin/bash
# wfcurrent: MPI 実行 + 回帰テスト + 検定(沿岸の波浪場の流れへの作用 = 段 W2。developer.md §90)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は Log.txt・E9998.txt・v9998.txt を ULP=1・RTOL=1e-6(reference を作ったマシンと CPU の違う
# マシンの最終桁の差の許容と wavefield.csv を外す理由は Run.sh と developer.md §90.18。同じマシンでは
# ULP=0 RTOL=0 FILES="Log.txt wavefield.csv E9998.txt v9998.txt" ./Run_MPI.sh N でビット比較できる)。並列数によらないビット一致は、
# 同じバイナリの np = 1 とのバイト比較(下)と、同じマシンでの ULP=0 の比較で確かめる
# (CLAUDE.md 検証規律。波→流れの外力は行ごとの局所計算とハロ交換、側方 Neumann の
# 境界面は同じ入力からの冗長計算なので並列数によらずビット一致する)。ローラーの検定
# (param_long の結果と比べる)も同じ並列数で回す。90° 回した格子(param_rot。W・E の
# 側方 Neumann がランク界面をまたぐ)は同じバイナリの np = 1 とバイト比較し、再開の往復
# (rt1 → rt2)は同じ並列数の通し計算とバイト比較する。双方向の連成(param_cur。段 W3)も
# 同じ並列数で回して検定し、np = 1 とバイト比較する。拡散項(param_diff。側方 Neumann の辺の
# 行のセルと境界面の拡散 = §90.12)とその 90° 回した格子(param_rotdiff。W・E の辺の拡散が
# ランク界面をまたぐ)・砕波による水平混合(param_mix)も同じ。基本の行は 8 なので 2 行/ランクの
# 制約から np <= 4
sdir=$(dirname "$(readlink -f "$0")")
export ULP=${ULP:-1}       # 印字の最終桁 1 つ分まで(CPU の違うマシンの最終桁の差。上の注・Run.sh)
export RTOL=${RTOL:-1e-6}
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
export FILES=${FILES:-"Log.txt E9998.txt v9998.txt"}
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

np=2
for a in "$@"; do case $a in -u) ;; *) np=$a ;; esac; done

run() {   # run <ランク数> <param> <ログ>
    mpirun -np "$1" $MPIRUN_OPTS ./encflow_mpi "$2" > "$3" 2>&1 \
        || { echo "ERROR: $2 (np=$1) run failed" >&2; exit 1; }
}
withdir() {   # withdir <param> <新しい dir_result> → 一時ファイル名
    local tmp
    tmp=$(mktemp)
    sed -e "s/dir_result = '[^']*'/dir_result = '$2'/" "$1" > "$tmp"
    echo "$tmp"
}

rm -rf result_long result_rot result_cur result_diff result_rotdiff result_mix
run "$np" param_long.txt Screen_long.log
run "$np" param_rot.txt Screen_rot.log
run "$np" param_cur.txt Screen_cur.log
run "$np" param_diff.txt Screen_diff.log
run "$np" param_rotdiff.txt Screen_rotdiff.log
run "$np" param_mix.txt Screen_mix.log
python3 Check_wfcurrent.py roller result result_long || exit 1
python3 Check_wfcurrent.py rot result result_rot || exit 1
python3 Check_wfcurrent.py cur result_cur result || exit 1
python3 Check_wfcurrent.py diff result_diff result || exit 1
python3 Check_wfcurrent.py rot result_diff result_rotdiff || exit 1
python3 Check_wfcurrent.py mix result_mix result || exit 1
if [ "$np" != 1 ]; then
    for tag in rot cur diff rotdiff mix; do
        tmp=$(withdir param_$tag.txt result_${tag}_np1)
        rm -rf result_${tag}_np1
        run 1 "$tmp" Screen_${tag}_np1.log
        rm -f "$tmp"
        for f in E9998.bil u9998.bil v9998.bil Wh9998.bil wavefield.csv; do
            cmp -s result_$tag/$f result_${tag}_np1/$f \
                || { echo "ERROR: result_$tag/$f differs between np=$np and np=1" >&2; exit 1; }
            echo "  ok   $tag/$f identical between np=$np and np=1"
        done
    done
fi

rm -rf result_rt1 result_rt2 save_rt
run "$np" param_rt1.txt Screen_rt1.log
run "$np" param_rt2.txt Screen_rt2.log
for f in save_all/state.dat:save_rt/state.dat save_all/swflow_enc.dat:save_rt/swflow_enc.dat \
         save_all/wavefield.dat:save_rt/wavefield.dat \
         result/E9998.bil:result_rt2/E9998.bil result/v9998.bil:result_rt2/v9998.bil \
         result/Wr9998.bil:result_rt2/Wr9998.bil; do
    a=${f%%:*}; b=${f##*:}
    cmp -s "$a" "$b" || { echo "ERROR: restart continuation (np=$np) differs from the straight run: $b" >&2; exit 1; }
    echo "  ok   restart continuation (np=$np) matches the straight run: $b"
done

echo "=== wfcurrent verification PASS ==="
