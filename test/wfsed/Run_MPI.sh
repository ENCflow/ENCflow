#!/bin/bash
# wfsed: MPI 実行 + 回帰テスト + 検定(沿岸の波浪場による土砂の攪拌と輸送 = 段 W4・W5。developer.md §90)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は Log.txt・Z9998.txt・Hs9998.txt を ULP=1・RTOL=1e-6(reference を作ったマシンと CPU の違う
# マシンの最終桁の差の許容と wavefield.csv を外す理由は Run.sh と developer.md §90.18。同じマシンでは
# ULP=0 RTOL=0 FILES="Log.txt wavefield.csv Z9998.txt Hs9998.txt" ./Run_MPI.sh N でビット比較できる)。並列数によらないビット一致は、
# 同じバイナリの np = 1 とのバイト比較(下)と、同じマシンでの ULP=0 の比較で確かめる
# (CLAUDE.md 検証規律。攪拌はセル・エッジの局所計算、波の書き出しと流れはハロ交換、側方
# Neumann の掃流砂の境界面は同じランクが計算した内側のエッジを写すので並列数によらず
# ビット一致する)。攪拌・掃流砂・閉じた海盆・高波浪・低波浪・砕波の乱れの検定も同じ並列数で回し、
# 攪拌・掃流砂・閉じた海盆・砕波の乱れは同じバイナリの np = 1 とバイト比較する。再開の往復(rt1 → rt2)は同じ並列数の
# 通し計算とバイト比較する。行は 8 なので 2 行/ランクの制約から np <= 4
sdir=$(dirname "$(readlink -f "$0")")
export ULP=${ULP:-1}       # 印字の最終桁 1 つ分まで(CPU の違うマシンの最終桁の差。上の注・Run.sh)
export RTOL=${RTOL:-1e-6}
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=4
export FILES=${FILES:-"Log.txt Z9998.txt Hs9998.txt"}
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

np=2
for a in "$@"; do case $a in -u) ;; *) np=$a ;; esac; done

run() {   # run <ランク数> <param> <ログ>
    mpirun -np "$1" $MPIRUN_OPTS ./encflow_mpi "$2" > "$3" 2>&1 \
        || { echo "ERROR: $2 (np=$1) run failed" >&2; exit 1; }
}
withdir() {   # withdir <param> <新しい dir_result> <新しい dir_save> → 一時ファイル名
    local tmp
    tmp=$(mktemp)
    sed -e "s/dir_result = '[^']*'/dir_result = '$2'/" -e "s/dir_save = '[^']*'/dir_save = '$3'/" "$1" > "$tmp"
    echo "$tmp"
}

for tag in stir bed closed storm calm turb; do
    rm -rf result_$tag save_$tag
    run "$np" param_$tag.txt Screen_$tag.log
done
python3 Check_wfsed.py stir result_stir save_stir || exit 1
python3 Check_wfsed.py bed result_bed || exit 1
python3 Check_wfsed.py beach result || exit 1
python3 Check_wfsed.py closed save_closed || exit 1
python3 Check_wfsed.py asym result || exit 1
python3 Check_wfsed.py shore result_storm result_calm || exit 1
python3 Check_wfsed.py turb result_turb result || exit 1
if [ "$np" != 1 ]; then
    for tag in stir bed closed turb; do
        tmp=$(withdir param_$tag.txt result_${tag}_np1 save_${tag}_np1)
        rm -rf result_${tag}_np1 save_${tag}_np1
        run 1 "$tmp" Screen_${tag}_np1.log
        rm -f "$tmp"
        for f in Z9998.bil H9998.bil u9998.bil Hs9998.bil; do
            [ -e result_$tag/$f ] || continue
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
         result/Z9998.bil:result_rt2/Z9998.bil result/Hs9998.bil:result_rt2/Hs9998.bil \
         result/Qby9998.bil:result_rt2/Qby9998.bil result/Qsy9998.bil:result_rt2/Qsy9998.bil; do
    a=${f%%:*}; b=${f##*:}
    cmp -s "$a" "$b" || { echo "ERROR: restart continuation (np=$np) differs from the straight run: $b" >&2; exit 1; }
    echo "  ok   restart continuation (np=$np) matches the straight run: $b"
done

echo "=== wfsed verification PASS ==="
