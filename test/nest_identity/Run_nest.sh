#!/bin/bash
# nest_identity の実行本体(Run.sh / Run_MPI.sh から呼ぶ)
#   Run_nest.sh serial | mpi [N]
mode=$1; shift
NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
"$sdir/../Scripts/Check_mode.sh" "$mode" || exit 1
if [ "$mode" = mpi ]; then
    make -s MODE=mpi nestcheck_mpi links || exit 1
    run="mpirun -np $NP $MPIRUN_OPTS"; exe=./nestcheck_mpi
    export ENCFLOW_EXPECT_NP="$NP"
else
    make -s nestcheck links || exit 1
    run=; exe=./nestcheck
fi
rm -rf result_*
fail=0
# --- wave: 子 = 中央 121x121(親セル 133..253。境界は中心から 15.7 m。波は t≈5 s に
#     帯へ達し、以後 3 s 間は帯を横切る)。初期水深は単独格子から切り出す。
#     wave_s1 = f_advection_scheme=1(帯幅 2)、wave = 既定のスキーム 3(帯幅 3)---
for v in wave_s1 wave; do
    if [ $v = wave_s1 ]; then nb=2; else nb=3; fi
    $run $exe cut param_${v}_single.txt 133 133 121 121 hinit_${v}_child.txt > Screen_cut_$v.log 2>&1 \
        || { echo "ERROR: $v cut failed"; tail -5 Screen_cut_$v.log; exit 1; }
    if $run $exe run param_${v}_root.txt 133 133 $nb > Screen_$v.log 2>&1; then
        grep "nestcheck: steps" Screen_$v.log; echo "nest_identity $v: PASS"
    else
        echo "nest_identity $v: FAIL"; grep "nestcheck\|ERROR" Screen_$v.log | tail -5; fail=1
    fi
done
# --- restart: wave_s1 を t=4 s で保存して再開(各格子の dir_save は別)。再開後も
#     子の内部 == 親(nestcheck)で、Log.txt は中断なしランと一致すること ---
rm -rf save_wave_rs_*
cp hinit_wave_s1_child.txt hinit_wave_rs_child.txt
rs_ok=1
for leg in A B; do
    cp param_wave_rs${leg}_root.txt param_wave_rs_root.txt
    cp param_wave_rs${leg}_child.txt param_wave_rs_child.txt
    if ! $run $exe run param_wave_rs_root.txt 133 133 2 > Screen_wave_rs$leg.log 2>&1; then
        echo "nest_identity restart leg $leg: FAIL"; grep "nestcheck\|ERROR" Screen_wave_rs$leg.log | tail -5; rs_ok=0
    fi
done
rm -f param_wave_rs_root.txt param_wave_rs_child.txt
if [ $rs_ok -eq 1 ]; then
    # 再開ラン(leg B)の Log の各行(t > 4 s)が中断なしランの Log に字句同一で現れること
    # (再開時刻 t = 4 s の行は区間統計(Runge・最大値)が未蓄積なので比較しない = 単一格子の restart と同じ性質)
    for who in root child; do
        if python3 - result_wave_s1_$who/Log.txt result_wave_rs_$who/Log.txt <<'PY'
import sys
full = set(l.rstrip() for l in open(sys.argv[1]).readlines()[1:])
legb = [l.rstrip() for l in open(sys.argv[2]).readlines()[2:]]   # 再開時刻の行(区間統計が未蓄積)は除く
missing = [l for l in legb if l not in full]
sys.exit(0 if (len(legb) >= 2 and not missing) else 1)
PY
        then echo "nest_identity restart $who Log: rows after restart IDENTICAL to the uninterrupted run"
        else echo "nest_identity restart $who Log: DIFFER"; rs_ok=0; fi
    done
fi
if [ $rs_ok -eq 1 ]; then echo "nest_identity restart: PASS"; else echo "nest_identity restart: FAIL"; fail=1; fi
# --- chichibu 500 m・1 時間: 子 = 60x40(親セル 20..79 x 10..49)。地形類を切り出す。
#     f_advection_scheme=3 なので帯幅は自動で 3(比較も帯 3 を除く)---
python3 cut_chichibu.py ../chichibu/data_chichibu_500m data_chichibu_child 20 10 60 40 || exit 1
if $run $exe run param_chichibu_root.txt 20 10 3 > Screen_chichibu.log 2>&1; then
    grep "nestcheck: steps" Screen_chichibu.log; echo "nest_identity chichibu: PASS"
else
    echo "nest_identity chichibu: FAIL"; grep "nestcheck" Screen_chichibu.log | tail -5; fail=1
fi
if [ $fail -eq 0 ]; then echo "nest_identity ($mode): verification PASS"; else echo "nest_identity ($mode): verification FAIL"; exit 1; fi
