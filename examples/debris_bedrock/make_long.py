#!/usr/bin/env python3
# examples/debris_bedrock 後半(長期: 土石流を挟む渓流の定常勾配)の構成の生成と、連鎖の記録の読み取り
#   python3 make_long.py                 long/<構成>/ に設定ファイルを書き、long/configs.txt に一覧を書く
#   python3 make_long.py track SAVE 段 サイクル LOG   台帳の表示と save のセルごとの z・Ri・sd を 1 行で
#                                                    出す(Run_chain.sh が各段の後に呼ぶ)
# 一様勾配の水路(幅 10 m を横断 1 セル(Δx = 10 m)、Δy = 2 m、長さ 200 m)で、出水(T_r 年分)と
# 土石流 1 回を f_state_restore = 2 で交互につなぐ(docs/mountain_stream_plan.md §13。developer.md
# §89.22)。前半の 5 セルの水路では、出水が壁の列を削らずに流れが中央へ集まり、低下速度が
# サイクルごとに上がるので(plan §13.8)、横断の形が変わらない 1 セルにした。水路の下には勾配 0.6・
# 長さ 20 m の落ち口を足す(自由流出の境界のセルは流れが深く遅く、堰になって土砂がたまるため)。
# 定数は plot_long.py と対で保守する。土石流と岩盤侵食の係数は前半(make_init.py)と同じ。
import os, sys, struct
from make_init import CMIX, KD, TAUCD, MD, HSTAR, hydro

NX, W = 1, 10.0                            # 横断のセル数と水路の幅 = Δx (m)
NYR, NC, DY = 100, 10, 2.0                 # 水路の行数(200 m)、その下の落ち口の行数(20 m)、Δy (m)
NY = NYR + NC
SC = 0.6                                   # 落ち口の勾配(出口のセルが土砂を捕まえても水路に届かない)
SLOPES = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
TRS = [100, 30, 10]                        # 土石流の間隔 T_r (年)
D50S = [0.1, 0.4]                          # 掃流砂(土石流の堆積物)の粒径 (m)
F = 300.0                                  # 1 年の形成流量の継続 (s)
YEAR = 3.15576e7                           # 1 年 (s)
IF = F / YEAR                              # 間欠係数 i_f
MORFAC = 10.0                              # 出水の計算の morfac
QF = 5.0                                   # 形成流量 (m3/s)
KP, TAUC, MP = 4.6e-6, 300.0, 1.0          # 流水の剥離(出水だけの定常勾配が約 0.355 になる k_p)
U = 1.0                                    # 隆起速度 (mm/年。暦の値)
NCYC, NSKIP = 10, 2                        # 固定勾配の連鎖のサイクル数と、捨てる最初のサイクル数
TR_INF, NCYC_INF = 100, 5                  # 出水だけ(T_r = ∞): 100 年分の出水を 5 回
TDEB = 200.0                               # 土石流の計算時間 (s)
DT_F = 0.1                                 # 出水の時間刻み (s)
# 確認(隆起あり): 足し合わせで予測した定常勾配 0.25(T_r = 30 年・粒径 0.1 m)の ± 0.03
UPLIFT_RUNS = [("U_d10_S028_T030", 0.28), ("U_d10_S022_T030", 0.22)]
NCYC_U, TR_U, D50_U = 150, 30, 0.1
MID = (40.0, 160.0)                        # 中央区間 (m。谷頭から)


def name_fixed(d50, s, tr):
    return "L_d%02d_S%03d_T%s" % (round(d50 * 100), round(s * 100), "inf" if tr is None else "%03d" % tr)


def zrow(s, j):
    """セル行 j(1 始まり、谷頭が 1)の標高。水路(j ≤ NYR)は勾配 s、その下の落ち口は勾配 SC で、
    最下流の行の中心が 10 m"""
    zr = 10.0 + SC * NC * DY
    return zr + s * (NYR - j) * DY if j <= NYR else zr - SC * (j - NYR) * DY


def write_matrix(fn, f, fmt="%.6f"):
    with open(fn, "w") as o:
        for j in range(1, NY + 1):
            o.write(" ".join(fmt % f(i, j) for i in range(1, NX + 1)) + "\n")


def inflow(q, cs=None):
    s = "&list_bound_inflow\n"
    for i in range(1, NX + 1):
        s += "  inflow_cell(1:2,%d,1) = %d, 1\n" % (i, i)
    if q is None:
        qw, cv = hydro(CMIX)
        for k, (t, v) in enumerate(qw, 1):
            s += "  inflow_val(1:2,%d,1) = %.6f, %.6f\n" % (k, t, v)
        s += "  inflow_dist(1) = 0\n"
        for k, (t, v) in enumerate(cv, 1):
            s += "  inflow_cs(1:2,%d,1) = %.6f, %.6f\n" % (k, t, v)
    else:
        s += "  inflow_val(1:2,1,1) = 0, %.3f\n  inflow_val(1:2,2,1) = 99999, %.3f\n  inflow_dist(1) = 0\n" % (q, q)
    return s + "/\n"


def common(z, dt, tt, restore):
    return ("&list_sysparam\n  dt = %.2f\n  t0 = 0\n  tt = %.1f\n  dt_disp = %.1f\n  dt_file = %.1f\n"
            "  dt_recrd = %.1f\n  fn_geoinfo = '-'\n  fn_initial = '-'\n  fn_enc = '-'\n"
            "  fn_geomorph = '-'\n  fn_boundary = '-'\n  dir_result = 'result'\n  dir_save = 'save_chain'\n"
            "  f_state_save = 1\n%s  f_check_cfl = 1\n  f_output_mode = 2\n/\n"
            "&list_enc\n  f_gravity_correction = 1\n  f_opening_dynamic = 3\n/\n&list_initial\n  f_htype = 0\n  h0 = 0.0\n/\n"
            "&list_geoinfo\n  lx = %.1f\n  ly = %.1f\n  nx = %d\n  ny = %d\n  f_ztype = 1\n  fn_z = '../%s'\n"
            "  f_rntype = 0\n  rn0 = 0.05\n  f_sdtype = 1\n  fn_sd = '../sd0.txt'\n  sy0 = 0.2\n/\n"
            % (dt, tt, tt, tt, tt, "  f_state_restore = 2       ! 前の段の save を初期条件にする\n" if restore else "",
               W, NY * DY, NX, NY, z))


def flood(z, d50, tr, restore, rockmap, upmap=None):
    """出水の計算 1 回 = T_r 年(地形の時間 T_r × F、流れの時間 T_r × F / morfac)"""
    s = common(z, DT_F, tr * F / MORFAC, restore)
    s += ("&list_geomorph\n  dt_geomorph = 0.0\n  morfac = %.1f\n  f_fluvial = 1\n  fluv_d50 = %.2f\n"
          "  fluv_porosity = 0.4\n  f_rockinc = 1\n  rock_kp = %.3e\n  rock_tauc = %.1f\n  rock_m = %.1f\n"
          "  rock_hstar = %.2f\n  fn_rock = '../%s'\n" % (MORFAC, d50, KP, TAUC, MP, HSTAR, rockmap))
    if upmap:
        s += "  f_uplift = 1\n  uplift0 = %.4f       ! 隆起 (mm/yr) = %.1f mm/yr / i_f\n  fn_uplift = '../%s'\n" % (U / IF, U, upmap)
    s += "/\n&list_bound_edge\n  f_bc_s = 1\n/\n" + inflow(QF)
    return s


def debris(z, rockmap):
    """土石流の計算 1 回(前半の T_b と同じ抵抗則・侵食堆積式・岩盤侵食。暦には数えない)"""
    s = common(z, 0.02, TDEB, True)
    s += ("&list_geomorph\n  dt_geomorph = 0.0\n  morfac = 1.0\n  f_debris = 1\n  db_phi = 35.0\n"
          "  f_dbed = 3\n  f_dbres = 3\n  db_d50 = 0.1\n  db_delte = 0.0001\n  db_deltd = 0.5\n"
          "  f_dbstop = 1\n  db_vstop = 0.05\n  db_wstop = 0.05\n  fluv_porosity = 0.4\n  f_rockinc = 1\n"
          "  rock_hstar = %.2f\n  fn_rock = '../%s'\n  rock_kdb = %.3e\n  rock_taucdb = %.1f\n  rock_mdb = %.1f\n/\n"
          % (HSTAR, rockmap, KD, TAUCD, MD))
    s += "&list_bound_edge\n  f_bc_s = 1\n/\n" + inflow(None)
    return s


def make_config(name, z, d50, tr, with_debris, rockmap, upmap=None):
    d = os.path.join("long", name)
    os.makedirs(d, exist_ok=True)
    head = "!" + "=" * 70 + "\n! examples/debris_bedrock 後半: 構成 %s(make_long.py が生成)\n!" % name + "=" * 70 + "\n"
    open(os.path.join(d, "param_flood0.txt"), "w").write(head + flood(z, d50, tr, False, rockmap, upmap))
    open(os.path.join(d, "param_flood.txt"), "w").write(head + flood(z, d50, tr, True, rockmap, upmap))
    if with_debris:
        open(os.path.join(d, "param_debris.txt"), "w").write(head + debris(z, rockmap))


def generate():
    os.makedirs("long", exist_ok=True)
    write_matrix("long/sd0.txt", lambda i, j: 0.0, "%.1f")
    # 固定勾配の構成は落ち口も削る(全体が下がる)。隆起の構成は水路の最後の行と落ち口を基準面に
    # (削れず隆起もしない)
    write_matrix("long/rock_all.txt", lambda i, j: 1.0, "%.1f")
    write_matrix("long/rock_base.txt", lambda i, j: 0.0 if j >= NYR else 1.0, "%.1f")
    write_matrix("long/up_base.txt", lambda i, j: 0.0 if j >= NYR else 1.0, "%.1f")
    for s in SLOPES + [s0 for _, s0 in UPLIFT_RUNS]:
        write_matrix("long/z_%03d.txt" % round(s * 100), lambda i, j, s=s: zrow(s, j))
    lines = []
    for name, s0 in UPLIFT_RUNS:          # 長いものから並べる(並列実行の詰め方)
        make_config(name, "z_%03d.txt" % round(s0 * 100), D50_U, TR_U, True, "rock_base.txt", "up_base.txt")
        lines.append("%s %d" % (name, NCYC_U))
    for tr in TRS:
        for d50 in D50S:
            for s in SLOPES:
                n = name_fixed(d50, s, tr)
                make_config(n, "z_%03d.txt" % round(s * 100), d50, tr, True, "rock_all.txt")
                lines.append("%s %d" % (n, NCYC))
    for d50 in D50S:
        for s in SLOPES:
            n = name_fixed(d50, s, None)
            make_config(n, "z_%03d.txt" % round(s * 100), d50, TR_INF, False, "rock_all.txt")
            lines.append("%s %d" % (n, NCYC_INF))
    open("long/configs.txt", "w").write("\n".join(lines) + "\n")
    print("wrote %d configurations under long/ (list: long/configs.txt)" % len(lines))


# ---------------------------------------------------------------------
# save の読み取り(state.dat・geomorph_rockinc.dat。倍精度の連長圧縮の形式。test/dbrock と同じ)
# ---------------------------------------------------------------------
def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    assert struct.unpack("<i", f.read(4))[0] == n, "record marker mismatch"
    return payload


def read_rle_array(f, ntot):
    n, nrun = struct.unpack("<2q", read_rec(f))
    assert n == ntot, "unexpected array size %d != %d" % (n, ntot)
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    raw = read_rec(f)
    packed = struct.unpack("<%dd" % (len(raw) // 8), raw)
    out = [0.0] * n
    i = k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def ledger(logfile):
    """終了時・初期化の表示: 流水の剥離・土石流の侵食(かさ体積)、復元した h_s の堆積(固体)"""
    import re
    v = {"plucked": 0.0, "eroded": 0.0, "deposited": 0.0}
    pats = {"plucked": r"rock incision: plucked\s+(\S+) m3", "eroded": r"rock erosion by debris flows: eroded\s+(\S+) m3",
            "deposited": r"deposited\s+(\S+) m3 \(solid\)"}
    for line in open(logfile, encoding="utf-8", errors="replace"):
        for k, p in pats.items():
            m = re.search(p, line)
            if m:
                v[k] = float(m.group(1))
    return v


def track(savedir, stage, cycle, logfile):
    """1 行: サイクル,段,全域の ΣRi·A,表示 3 つ,セルごとの z・Ri・sd(行 j = 谷頭から、列 i の順)"""
    n = NX * NY
    with open(os.path.join(savedir, "state.dat"), "rb") as f:
        read_rle_array(f, n)
        z = read_rle_array(f, n)
        read_rle_array(f, n)
        read_rle_array(f, n)
        sd = read_rle_array(f, n)
    with open(os.path.join(savedir, "geomorph_rockinc.dat"), "rb") as f:
        ri = read_rle_array(f, n)
    lg = ledger(logfile)
    out = [cycle, stage, "%.9e" % (sum(ri) * W * DY), "%.9e" % lg["plucked"], "%.9e" % lg["eroded"],
           "%.9e" % lg["deposited"]]
    out += ["%.7e" % v for v in z + ri + sd]
    print(",".join(str(v) for v in out))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "track":
        track(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        generate()
