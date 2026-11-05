#!/usr/bin/env python3
# test/stencil9 の入力生成(developer.md §93。値は Check_stencil9.py と対で保守する)
#   z_hill2.txt : 81 × 81 セル(Δ = 1 m)、中心セル (41, 41) のガウス丘 z = 10 + A exp(−r²/2σ²)
#                 (A = 1 m、σ = 2 m = 2Δ。格子で解像しきれない丘 = 格子の向きの検出器)
#   z_strip1.txt: 1 × 40 セル、z = A cos(π (j − 0.5)/40)(南北の帯。四周は壁)
#   z_strip3.txt: 3 × 40 セル、同じ
#   書式は 17 桁(Check_stencil9.py が同じ文字列を読み、ENCflow と同じ倍精度の値を得る)
import math

A, SIG, N, C = 1.0, 2.0, 81, 41
with open('z_hill2.txt', 'w') as f:
    for j in range(1, N + 1):
        f.write(' '.join('%.17g' % (10.0 + A * math.exp(-((i - C) ** 2 + (j - C) ** 2) / (2 * SIG ** 2)))
                         for i in range(1, N + 1)) + '\n')
for nx, fn in ((1, 'z_strip1.txt'), (3, 'z_strip3.txt')):
    with open(fn, 'w') as f:
        for j in range(1, 41):
            f.write(' '.join(['%.17g' % (A * math.cos(math.pi * (j - 0.5) / 40.0))] * nx) + '\n')
print('written: z_hill2.txt, z_strip1.txt, z_strip3.txt')
