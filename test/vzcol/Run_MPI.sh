#!/bin/bash
# vzcol: MPI 実行 + 回帰テスト + 解析検定(VZ 共有参照柱。developer.md §87)
#   ./Run_MPI.sh [ランク数] [-u]
# 逐次 reference との比較は Log.txt を ULP=0(CLAUDE.md 検証規律。柱は全ランクで
# 冗長に解くので並列数によらずビット一致する)。CSV は np=1 とバイト比較する。面積平均モード(param_avg.txt)は
# 行部分和の決定的総和(par_sum_rows)を通るので、MPI でも厳密モードと一致する
# ことを確かめる。行は 8 なので 2 行/ランクの制約から np <= 4
sdir=$(dirname "$(readlink -f "$0")")
export ULP=0
export MPIRUN_OPTS="--bind-to none"
export SKIPCOLS=6
export FILES=${FILES:-Log.txt}
"$sdir/../Scripts/Run_case.sh" mpi "$@" || exit 1

python3 Check_vzcol.py base result || exit 1

np=2
for a in "$@"; do case $a in -u) ;; *) np=$a ;; esac; done

# vz_zone.csv・vz_column.csv の並列数不変性: 同じバイナリの np=1 とバイト比較する
# (同一ホスト・同一バイナリなので CPU 差の影響を受けない厳密な検査。
# reference との比較は Log.txt だけ = Run.sh の注記)
if [ "$np" != 1 ]; then
    tmp=$(mktemp)
    sed "s/dir_result = 'result'/dir_result = 'result_np1'/" param.txt > "$tmp"
    rm -rf result_np1
    mpirun -np 1 $MPIRUN_OPTS ./encflow_mpi "$tmp" > Screen_np1.log 2>&1
    rc=$?
    rm -f "$tmp"
    [ $rc -eq 0 ] || { echo "ERROR: np=1 run failed" >&2; exit 1; }
    for f in vz_zone.csv vz_column.csv; do
        cmp -s "result/$f" "result_np1/$f" \
            || { echo "ERROR: result/$f differs between np=$np and np=1" >&2; exit 1; }
        echo "  ok   $f identical between np=$np and np=1"
    done
fi
rm -rf result_avg
mpirun -np "$np" $MPIRUN_OPTS ./encflow_mpi param_avg.txt > Screen_avg.log 2>&1 \
    || { echo "ERROR: param_avg run failed" >&2; exit 1; }
python3 Check_vzcol.py avg result result_avg || exit 1

echo "=== vzcol verification PASS ==="
