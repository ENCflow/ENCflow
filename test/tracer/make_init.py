#!/usr/bin/env python3
# test/tracer の入力生成: 一様流の直線水路(勾配 S = 9e-4、n = 0.03 → 水深 1 m で u = 1 m/s)
#   z_a10.txt : 構成 A(縦断の数値拡散)。3 列 × 600 行(南北の水路。北から南へ流下。
#               帯分割の MPI 検証ができる向き)、dx = 10 m
#   z_a20.txt : 同 A、3 列 × 300 行、dx = 20 m
#   z_b.txt   : 構成 B(横断の数値拡散)。600 列 × 61 行、dx = 10 m
#   inflow_b.txt : 構成 B の西辺流入セル(1, 1..61)
import numpy as np
S = 9.0e-4
def channel(nx, ny, dx, fn, along='x'):
    if along == 'x':                       # 西から東へ流下
        x = (np.arange(nx) + 0.5) * dx
        z = np.tile(-S * x, (ny, 1))
    else:                                  # 北から南へ流下(行 1 が北)
        y = (np.arange(ny) + 0.5) * dx
        z = np.tile(-S * y, (nx, 1)).T
    np.savetxt(fn, z, fmt='%.4f')
    print('written: %s (%d x %d, dx = %g m)' % (fn, nx, ny, dx))
channel(3, 600, 10.0, 'z_a10.txt', along='y')
channel(3, 300, 20.0, 'z_a20.txt', along='y')
channel(600, 61, 10.0, 'z_b.txt')
with open('inflow_b.txt', 'w') as f:
    for j in range(1, 62):
        f.write('1 %d\n' % j)
print('written: inflow_b.txt')
