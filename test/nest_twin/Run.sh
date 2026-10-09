#!/bin/bash
# nest_twin: 複数インスタンス交互実行 == 単独実行 のビット一致検査(逐次)
#   ./Run.sh
#   1) encflow で param_wave.txt / param_chichibu.txt を単独実行(single_*)
#   2) twin で 2 ケースを同一プロセスで交互実行(result_*)
#   3) 結果ディレクトリ同士を比較(全ファイル一致で PASS)
#   reference は持たない(基準は同一ビルドの単独実行)。スレッド数は
#   既定 1(OpenMP のリダクション順序に依存するケースの再現性のため)
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
exec ./Run_twin.sh serial "$@"
