#!/bin/bash

#want=serial
want=mpi
srcdir=../../src
bin=../../bin/a.out
stamp=$srcdir/.mode_$want

# a.out(シンボリックリンク)の存在確認。リンク切れも -e で検出される
if [ ! -e ./a.out ]; then
    echo "ERROR: ./a.out がありません。先に make を実行してください。" >&2
    exit 1
fi

# ビルドモードの確認
if [ ! -e "$stamp" ]; then
    actual=$(cd "$srcdir" && ls .mode_* 2>/dev/null | sed 's/^\.mode_//')
    echo "ERROR: ビルドモードが一致しません(要求: $want / src: ${actual:-未ビルド})" >&2
    echo "  対処: cd $srcdir && make MODE=$want install" >&2
    exit 1
fi

# install 忘れの検出: bin/a.out がモード切替時刻より古ければ警告
if [ "$bin" -ot "$stamp" ]; then
    echo "ERROR: $bin が .mode_$want より古く、install 忘れの可能性があります。" >&2
    echo "  cd $srcdir && make install の実行をお勧めします。" >&2
    exit 1
fi

NP=${1:-2}    # ランク数(引数で変更可: ./Run_MPI.sh 4)
#time mpirun -np $NP /usr/bin/time -v ./a.out param.txt | tee Log.txt
time mpirun -np $NP ./a.out param.txt | tee Log.txt
