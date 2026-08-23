# -*- coding: utf-8 -*-
# sewer_hybrid: 幹線1本(線)+枝管網(面)を単一の管路連続体層
# インスタンスに同居させる模式実験のデータ生成。
#
# このスクリプトの前半は「管諸元(径・粗度・配置密度)→ 連続体層
# パラメータ(cap, cnd 密度, sy)」の幾何換算で、段階案の項目1
# (B×D→cnd の前処理換算)の実演を兼ねる。換算式:
#   満管通水能   C = (1/n)·A·R^(2/3)   [m3/s]  (q = C·sqrt(動水勾配))
#   通水能密度   dens = C × (セル幅あたり本数) [m2/s]
#   貯留容量     cap = A·(セル内管長)/セル面積 [m 柱状]
#   貯留係数     sy = cap / 管高(頂までの水頭上昇で満管になる勾配)
#
# 領域: 400 m x 210 m(nx=40, ny=21, dx=10 m)、勾配 0.005 の東向き斜面。
# 枝管網(全セル): D=0.4 m, n=0.013, セルあたり管長 10 m(街路 1 本)
# 幹線(j=11, i=2..38): D=1.0 m, n=0.013, 埋設深 5 m(枝管は 2 m)
# 枡: 全セル 0.01 個/m2(セルに 1 個)。吐口: 幹線末端 i=38 は 0.1 個/m2
import math
import os

nx, ny = 40, 21
dx = 10.0
jline = 11              # 幹線の行(1 始まり)
i1, i2 = 2, 38          # 幹線のセル範囲(i2 が吐口)
slope = 0.005

def pipe_params(D, n, length_per_cell):
    """管諸元 → (満管通水能 C m3/s, cap m, sy)"""
    A = math.pi * D * D / 4.0
    R = D / 4.0
    C = (1.0 / n) * A * R ** (2.0 / 3.0)
    cap = A * length_per_cell / (dx * dx)
    sy = cap / D
    return C, cap, sy

C_b, cap_b, sy_b = pipe_params(0.4, 0.013, 10.0)   # 枝管
C_t, cap_t, sy_t = pipe_params(1.0, 0.013, 10.0)   # 幹線
dens_b = C_b / dx                                   # セル幅 10 m に 1 本
dens_t = C_t / dx
cap_trunkcell = cap_t + cap_b                       # 幹線セルは幹線+枝管の合算
sy_trunkcell = cap_trunkcell / 1.0                  # 管高は幹線 1.0 m が支配

print("枝管 D=0.4: C=%.3f m3/s, cap=%.5f m, sy=%.4f, dens=%.4f m2/s"
      % (C_b, cap_b, sy_b, dens_b))
print("幹線 D=1.0: C=%.3f m3/s, cap=%.5f m, sy(単体)=%.4f, dens=%.4f m2/s"
      % (C_t, cap_t, cap_t / 1.0, dens_t))
print("幹線セル(合算): cap=%.5f m, sy=%.4f" % (cap_trunkcell, sy_trunkcell))
print("幹線の満管能力 Q(S=0.005) = %.2f m3/s" % (C_t * math.sqrt(slope)))
print("降雨 60 mm/h の領域流出 = %.2f m3/s" % (0.06 / 3600.0 * nx * ny * dx * dx))

def x_of(i):
    return (i - 0.5) * dx

def z_of(i):
    # 基準面 +8 m: fn_gwc_bot の読込検査が負値を拒否するため、
    # 管底(z-5)が全域で正になるよう基準を上げる(力学は不変)
    return 8.0 - slope * x_of(i)

def write_mat(fn, fval):
    with open(fn, "w") as f:
        for j in range(1, ny + 1):
            f.write(" ".join("%.5f" % fval(i, j) for i in range(1, nx + 1)))
            f.write("\n")

here = os.path.dirname(os.path.abspath(__file__))
d = os.path.join(here, "data_sewer")
os.makedirs(d, exist_ok=True)

on_trunk = lambda i, j: (j == jline and i1 <= i <= i2)

write_mat(os.path.join(d, "z.txt"), lambda i, j: z_of(i))

# --- 幹線ありの系(ラン A・B) ---
write_mat(os.path.join(d, "cap_T.txt"),
          lambda i, j: cap_trunkcell if on_trunk(i, j) else cap_b)
write_mat(os.path.join(d, "bot_T.txt"),
          lambda i, j: z_of(i) - (5.0 if on_trunk(i, j) else 2.0))
write_mat(os.path.join(d, "cnd_T.txt"),
          lambda i, j: dens_t if on_trunk(i, j) else dens_b)

# --- 幹線なしの系(ラン C。全セル枝管) ---
write_mat(os.path.join(d, "cap_C.txt"), lambda i, j: cap_b)
write_mat(os.path.join(d, "bot_C.txt"), lambda i, j: z_of(i) - 2.0)
write_mat(os.path.join(d, "cnd_C.txt"), lambda i, j: dens_b)

# --- 枡・吐口密度(共通) ---
write_mat(os.path.join(d, "inlet.txt"),
          lambda i, j: 0.1 if (i == i2 and j == jline) else 0.01)

# --- ラン D 用: セル別の貯留係数(§46.5 (5)) ---
#     幹線セル = 幹線に整合(sy 0.0911)、枝管セル = 枝管に整合(0.0314)。
#     slot は各セルの sy/5(物理寄りの硬い圧力応答。dt 上界を超える分は
#     サブサイクリング(§46.5 (4))が自動で吸収する)
sy_t, sy_b = cap_trunkcell / 1.0, cap_b / 0.4
write_mat(os.path.join(d, "sy_T.txt"),
          lambda i, j: sy_t if on_trunk(i, j) else sy_b)
write_mat(os.path.join(d, "slot_T.txt"),
          lambda i, j: (sy_t if on_trunk(i, j) else sy_b) / 5.0)

print("maps written to data_sewer/")
