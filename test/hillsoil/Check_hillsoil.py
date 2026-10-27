#!/usr/bin/env python3
# test/hillsoil の検定(make_init.py・param*.txt と定数を対で保守)
#   python3 Check_hillsoil.py wthr    W1 風化の分布(save_wthr_none・save_wthr_map の z・sd)
# W1: 生成速度 W = W0 m(i, j)、dsd/dt = W exp(−sd/sd*) の解析解
#   sd(T) = sd* ln(e^{sd0/sd*} + W T/sd*)
# は、更新式 sd += sd* ln(1 + (W dts/sd*) e^{−sd/sd*})(指数の厳密積分)と刻みによらず
# 一致する(u = e^{sd/sd*} が毎回 W dts/sd* ずつ増える)。全セルで丸めの水準の一致、倍率 0 の
# セルの不変(ln 1 = 0)、z の不変(風化は岩盤面 z − sd を下げるだけ)を確かめる。
import sys, os, math, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, Z0, wmult

KYR_S = 1000.0 * 365.25 * 86400.0    # m_geomorph の kyr_s
# 構成 wthr(param_wthr_*.txt)
WT_P0, WT_SDS = 50.0, 0.5            # wthr_p0 (mm/kyr)、wthr_sdstar (m)
WT_DT, WT_TT, WT_MORF = 1.0, 100.0, 1.0e10
TOL_WTHR = 1.0e-12                   # 相対(倍精度の丸めの累積は 1e-15 程度)


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    n2 = struct.unpack("<i", f.read(4))[0]
    assert n == n2, "record marker mismatch"
    return payload


def read_rle_array(f, ntot):
    n, nrun = struct.unpack("<2q", read_rec(f))
    assert n == ntot, "unexpected array size %d != %d" % (n, ntot)
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    packed_raw = read_rec(f)
    packed = struct.unpack("<%dd" % (len(packed_raw) // 8), packed_raw)
    out = [0.0] * n
    i = k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def grid(a, nx):
    return [a[j * nx:(j + 1) * nx] for j in range(len(a) // nx)]


def load_state(savedir, nx, ny):
    """state.dat の h, z, sd(倍精度。並びは h, z, hrs, hg, sd, hs)"""
    with open(savedir + "/state.dat", "rb") as f:
        h = read_rle_array(f, nx * ny)
        z = read_rle_array(f, nx * ny)
        read_rle_array(f, nx * ny)
        read_rle_array(f, nx * ny)
        sd = read_rle_array(f, nx * ny)
    return grid(h, nx), grid(z, nx), grid(sd, nx)


def load_text(fn):
    return [[float(v) for v in line.split()] for line in open(fn) if line.strip()]


def report(label, ok, detail):
    print("%s: %s : %s" % (label, detail, "PASS" if ok else "FAIL"))
    return ok


def check_wthr():
    w0 = WT_P0 * 1.0e-3 / KYR_S                     # m/s
    tgeo = round(WT_TT / WT_DT) * WT_DT * WT_MORF   # 地形の時間(毎ステップ更新)
    sd0 = load_text("sdinit.txt")
    ok = True
    for c, mult in (("wthr_none", lambda i, j: 1.0), ("wthr_map", wmult)):
        _, z, sd = load_state("save_" + c, NX, NY)
        emax, nzero, zbad, zerobad = 0.0, 0, 0, 0
        for j in range(NY):
            for i in range(NX):
                m = mult(i + 1, j + 1)
                if z[j][i] != Z0:
                    zbad += 1
                if m == 0.0:
                    nzero += 1
                    if sd[j][i] != sd0[j][i]:
                        zerobad += 1
                    continue
                sa = WT_SDS * math.log(math.exp(sd0[j][i] / WT_SDS) + m * w0 * tgeo / WT_SDS)
                emax = max(emax, abs(sd[j][i] - sa) / sa)
        ok &= report("(W1) %s" % c, emax < TOL_WTHR,
                     "解析解との max 相対誤差 %.2e (許容 %.0e)" % (emax, TOL_WTHR))
        ok &= report("(W1) %s" % c, zbad == 0, "z の変わったセル %d" % zbad)
        if nzero > 0:
            ok &= report("(W1) %s" % c, zerobad == 0,
                         "倍率 0 のセル %d のうち土層厚の変わったセル %d" % (nzero, zerobad))
    return ok


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "wthr"
    if kind == "wthr":
        ok = check_wthr()
    else:
        sys.exit("unknown check: " + kind)
    sys.exit(0 if ok else 1)
