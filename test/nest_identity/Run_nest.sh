#!/bin/bash
# nest_identity の実行本体(Run.sh / Run_MPI.sh から呼ぶ)
#   Run_nest.sh serial | mpi [N]
mode=$1; shift
NP=${1:-2}
sdir=$(dirname "$(readlink -f "$0")")
"$sdir/../Scripts/Check_mode.sh" "$mode" || exit 1
if [ "$mode" = mpi ]; then
    make -s MODE=mpi nestcheck_mpi links || exit 1
    run="mpirun -np $NP $MPIRUN_OPTS"; exe=./nestcheck_mpi; sfx=_mpi
    export ENCFLOW_EXPECT_NP="$NP"
else
    make -s nestcheck links || exit 1
    run=; exe=./nestcheck; sfx=
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
# --- 双方向(nest_fb=2)の比 1:1 恒等(Phase 2): 子の内部 == 親(nestcheck)に加え、
#     ルートの最終状態(save の state.dat / swflow_enc.dat)が単独ランとバイト一致すること
#     (置換が恒等になる = 子→親の経路が親を乱さない)。wave_s1 と chichibu(乾湿あり)---
rm -rf save_wave_tw_* save_chichibu_tw_*
cp hinit_wave_s1_child.txt hinit_wave_tw_child.txt
tw_ok=1
for v in wave chichibu; do
    if [ $v = wave ]; then args="133 133 2"; else args="20 10 3"; fi
    $run ./encflow$sfx param_${v}_tw_single.txt > Screen_${v}_tw_single.log 2>&1 || { echo "ERROR: $v two-way single run failed"; tw_ok=0; continue; }
    if $run $exe run param_${v}_tw_root.txt $args > Screen_${v}_tw.log 2>&1; then
        grep "nestcheck: steps" Screen_${v}_tw.log
    else
        echo "nest_identity two-way $v: FAIL (child interior != parent)"; grep "nestcheck\|ERROR" Screen_${v}_tw.log | tail -5; tw_ok=0; continue
    fi
    for f in state.dat swflow_enc.dat; do
        if cmp -s save_${v}_tw_single/$f save_${v}_tw_root/$f; then
            echo "nest_identity two-way $v: root $f IDENTICAL to the single run"
        else
            echo "nest_identity two-way $v: root $f DIFFER from the single run"; tw_ok=0
        fi
    done
    grep "nest:   grid 2 -> parent" Screen_${v}_tw.log
done
if [ $tw_ok -eq 1 ]; then echo "nest_identity two-way: PASS"; else echo "nest_identity two-way: FAIL"; fail=1; fi
# --- Phase 4 の選択肢の恒等: 保存修正(nest_fb = 3。比 1 では修正が厳密に 0)と
#     場の表(chichibu + 地下水バケツ。hg を帯で与え置換で平均)。いずれもルートの
#     最終状態が単独ランとバイト一致すること ---
rm -rf save_wave_fb3_* save_chichibu_fb3_* save_chichibu_gw_*
cp hinit_wave_s1_child.txt hinit_wave_fb3_child.txt
p4_ok=1
for v in wave_fb3 chichibu_fb3 chichibu_gw; do
    case $v in wave*) args="133 133 2";; *) args="20 10 3";; esac
    $run ./encflow$sfx param_${v}_single.txt > Screen_${v}_single.log 2>&1 || { echo "ERROR: $v single run failed"; p4_ok=0; continue; }
    if $run $exe run param_${v}_root.txt $args > Screen_${v}.log 2>&1; then
        grep "nestcheck: steps" Screen_${v}.log
    else
        echo "nest_identity $v: FAIL (child interior != parent)"; grep "nestcheck\|ERROR" Screen_${v}.log | tail -5; p4_ok=0; continue
    fi
    for f in state.dat swflow_enc.dat; do
        if cmp -s save_${v}_single/$f save_${v}_root/$f; then
            echo "nest_identity $v: root $f IDENTICAL to the single run"
        else
            echo "nest_identity $v: root $f DIFFER from the single run"; p4_ok=0
        fi
    done
    grep "nest:   grid 2" Screen_${v}.log | grep -v "<- parent 1, " | cut -c1-160
done
if [ $p4_ok -eq 1 ]; then echo "nest_identity phase4 (fb3, fields): PASS"; else echo "nest_identity phase4 (fb3, fields): FAIL"; fail=1; fi
# --- Flather 放射(nest_bc = 3)の退化恒等(nesting_plan §15.5-2): 親 = 静水(385x385)、
#     子 = 201x201(親セル 93..293)に自前の水の山、4 辺が放射(f_bc_* = 2)で一方向。
#     親の値は η_e = 1・u_n,e = 0 なので、子の Log が単独ラン(現行の放射境界のみ)と
#     ビット一致すること(拡張式が u_n,e = 0 で現行式に退化する)---
rm -rf result_wave_fl_*
fl_ok=1
$run ./encflow$sfx param_wave_fl_single.txt > Screen_wave_fl_single.log 2>&1 || { echo "ERROR: flather single run failed"; fl_ok=0; }
$run ./encflow$sfx param_wave_fl_root.txt > Screen_wave_fl.log 2>&1 || { echo "ERROR: flather nested run failed"; tail -3 Screen_wave_fl.log; fl_ok=0; }
if [ $fl_ok -eq 1 ]; then
    if cmp -s result_wave_fl_single/Log.txt result_wave_fl_child/Log.txt; then
        echo "nest_identity flather: child Log IDENTICAL to the single run (radiation boundary)"
    else
        echo "nest_identity flather: child Log DIFFER from the single run"; fl_ok=0
    fi
    grep "Flather cells" Screen_wave_fl.log | cut -c1-140
fi
if [ $fl_ok -eq 1 ]; then echo "nest_identity flather: PASS"; else echo "nest_identity flather: FAIL"; fail=1; fi
if [ $fail -eq 0 ]; then echo "nest_identity ($mode): verification PASS"; else echo "nest_identity ($mode): verification FAIL"; exit 1; fi
