#!/bin/bash
# GeoTIFF リーダーの回帰テスト
#   資産(data_gtif/)と期待値(expected/)はコミット済み。
#   他のケースと違い計算は回さないので Run_case.sh は使わない。
#   ビルド設定(コンパイラ・PREC)は ../../make.inc に従う。
cd "$(dirname "$0")" || exit 2
make -s "$@" || exit 2
./test_gtif_reader
