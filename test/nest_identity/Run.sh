#!/bin/bash
# nest_identity: 比 1:1・r_t=1 の自己ネスト恒等テスト(逐次。nesting_plan §9 の 4)
#   ./Run.sh
#   wave(湿潤水域)と chichibu 500 m(降雨・乾湿・サブグリッド河道)で、
#   一方向ネストの子の内部が親の同領域と全ステップでビット一致することを
#   nestcheck ドライバが検査する。reference は持たない
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
exec ./Run_nest.sh serial "$@"
