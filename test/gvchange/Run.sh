#!/bin/bash
# 空隙率変更手続き m_state_set_gv の単体検定(developer.md §63.1 A2)
#   計算は回さず libencflow.a の手続きを直接呼ぶ(test/gtif と同じ様式)。
#   ビルド設定(コンパイラ・PREC・MODE)は ../../make.inc に従う
#   (MODE=mpi のときは m_parallel_mpi がリンクされるが、本検定は
#   collective を呼ばないので mpirun なしのシングルトンで動く)。
cd "$(dirname "$0")" || exit 2
make -s "$@" || exit 2
./test_setgv
