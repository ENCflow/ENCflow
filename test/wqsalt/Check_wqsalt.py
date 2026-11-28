#!/usr/bin/env python3
"""wqsalt の検定(Python 標準ライブラリのみ)。

  Check_wqsalt.py mix RESDIR NX NY DX D T1 N1 T2 N2
      静水の中の物質の広がり(水平の混合係数 wq_diff): 分布 C の番号 N1(時刻 T1)から N2(時刻 T2)の間に、
      x・y 方向の分散が 2·D·(T2 − T1) ずつ増え、共分散が増えず、質量が変わらないこと。
  Check_wqsalt.py uniform RESDIR NX NY C0 N [N ...]
      揺れる水の中で、一様な濃度 C0 が一様のままであること(分布 C の番号 N。水のあるセルの最大のずれ)。
  Check_wqsalt.py wall RESDIR NX NY DX IRIDGE N
      乾いた尾根(列 IRIDGE。1 始まり)の東側の濃度が厳密に 0 で、西側が一様に近づき、質量が台帳と合うこと。
  Check_wqsalt.py gv RESDIR NX NY DX N
      水の入る面積の割合(家屋の空隙率 × 河道の平面積率。計算が出力する分布 A0000)の違うセルの間の
      混合: 分布 N で濃度が一様で、その値が投入量 ÷ 水の体積(Σ 割合 × 水深 × セル面積)に合い、
      質量が台帳と合うこと。
  Check_wqsalt.py sat RESDIR AREA H0 C0 CSAT E DT DD
      蒸発による濃縮と析出(wq_csat): 記録時刻ごとに、水柱の物質 = min(初期量, 溶解度 × その
      ステップの蒸発の前の水深)、析出物 = 残り。AREA は有効セルの面積 (m2)、E は蒸発の速さ (m/s)。
  Check_wqsalt.py dis RESDIR NX NY N CSAT H0 BWEST BEAST
      析出物の瞬時の溶解: 分布 N で、西半分・東半分の濃度と残った析出物(初期の析出物 kg/m2)。
  Check_wqsalt.py disk RESDIR CSAT H0 KDIS BWEST BEAST DTREC
      溶解の速さ(wq_kdis [m/s])つきの溶解: プローブ 1(西)・2(東)の濃度の時系列が
      C = CSAT (1 − exp(−k t / H0)) に合い、東は析出物が尽きた濃度で止まること。DTREC は記録の間隔 (s)。
  Check_wqsalt.py inf RESDIR NX NY N CSAT RAIN BWEST BEAST R DPUMP NSTEP IW JW IE JE
      浸透水による析出物の溶解と、地下水と一緒に動く濃度の上限: 分布 N で、地下の質量プール Cg と
      残った析出物 B、井戸のセル(西 IW,JW・東 IE,JE。1 始まり)が運び出した量。RAIN は浸透した
      雨の総量の名目値 (m。実際の値は井戸のないセルの地下貯留から読み、名目値の 3 % 以内を確かめる)、
      DPUMP は井戸が 1 セルから汲んだ水の総量 (m)、NSTEP はそのステップ数。
  Check_wqsalt.py sea RESDIR NX NY CSEA N [N ...]
      海から入る水の濃度(wq_sea_conc): 分布 N で、水のある陸のセルと海セルの濃度が CSEA。台帳は
      海から入った量 − 海へ出た量 = 地表の質量(記録の全行)で、出入りの両方が起きていること。
  Check_wqsalt.py c0map RESDIR NX NY IRIDGE CW CE N [N ...]
      初期濃度の分布(fn_wq_c0): 分布 N で、尾根(列 IRIDGE)の西の濃度が CW、東が CE。
  Check_wqsalt.py evts RESDIR AREA H0 TOTAL
      可能蒸発散の時系列(f_evmodel = 5): 最後の累積蒸発量が TOTAL (m) × AREA、半分の時刻で半分
      (周期強制の折り返し)、Log.txt の貯留高が H0 − TOTAL。
"""
import csv
import struct
import sys

TOL_VAR = 1.0e-5      # 分散の増分の相対誤差(分布は float32 で出力)
TOL_MASS = 1.0e-6     # 質量の相対誤差


def read_bil(path, nx, ny):
    """bil(float32・リトルエンディアン・ヘッダなし・先頭行が北端)を行のリストで返す"""
    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) != 4 * nx * ny:
        raise SystemExit(f"FAIL: {path} の大きさが {nx} x {ny} の float32 と合わない")
    v = struct.unpack("<%df" % (nx * ny), raw)
    return [v[j * nx:(j + 1) * nx] for j in range(ny)]


def read_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    head = [h.strip() for h in rows[0]]
    data = [[float(x) for x in r[:len(head)]] for r in rows[1:] if r]
    return head, data


def moments(c, dx):
    """分布 c(行のリスト)の質量(Σc)、重心、x・y の分散と共分散(セル中心の座標 [m])"""
    m = sx = sy = 0.0
    for j, row in enumerate(c):
        for i, v in enumerate(row):
            m += v
            sx += v * i
            sy += v * j
    xc, yc = sx / m, sy / m
    vxx = vyy = vxy = 0.0
    for j, row in enumerate(c):
        for i, v in enumerate(row):
            vxx += v * (i - xc) ** 2
            vyy += v * (j - yc) ** 2
            vxy += v * (i - xc) * (j - yc)
    return m, xc, yc, vxx / m * dx * dx, vyy / m * dx * dx, vxy / m * dx * dx


def check_mix(args):
    res, nx, ny, dx, d, t1, n1, t2, n2 = (args[0], int(args[1]), int(args[2]), float(args[3]), float(args[4]),
                                           float(args[5]), int(args[6]), float(args[7]), int(args[8]))
    a = moments(read_bil(f"{res}/C{n1:04d}.bil", nx, ny), dx)
    b = moments(read_bil(f"{res}/C{n2:04d}.bil", nx, ny), dx)
    want = 2.0 * d * (t2 - t1)
    ok = True
    for name, k in (("x", 3), ("y", 4)):
        got = b[k] - a[k]
        err = abs(got - want) / want
        flag = "ok  " if err <= TOL_VAR else "FAIL"
        ok = ok and err <= TOL_VAR
        print(f"  {flag} {name} 方向の分散の増分 {got:.6f} m2(理論 2·D·Δt = {want:.6f}。相対差 {err:.1e})")
    cov = abs(b[5] - a[5]) / want
    flag = "ok  " if cov <= TOL_VAR else "FAIL"
    ok = ok and cov <= TOL_VAR
    print(f"  {flag} 共分散の増分 / 理論の分散の増分 = {cov:.1e}(等方なら 0)")
    dm = abs(b[0] - a[0]) / a[0]
    flag = "ok  " if dm <= TOL_MASS else "FAIL"
    ok = ok and dm <= TOL_MASS
    print(f"  {flag} 分布の質量の変化(相対){dm:.1e}")
    head, data = read_csv(f"{res}/wq.csv")
    ms = [r[head.index("mass_surface_g")] for r in data]
    inp = data[-1][head.index("in_point_g")]
    dl = abs(ms[-1] - inp) / inp
    flag = "ok  " if dl <= 1.0e-12 else "FAIL"
    ok = ok and dl <= 1.0e-12
    print(f"  {flag} 台帳: 地表の質量 {ms[-1]:.7e} g = 投入 {inp:.7e} g(相対差 {dl:.1e})")
    return ok


def check_uniform(args):
    res, nx, ny, c0 = args[0], int(args[1]), int(args[2]), float(args[3])
    ok = True
    for n in [int(a) for a in args[4:]]:
        c = read_bil(f"{res}/C{n:04d}.bil", nx, ny)
        h = read_bil(f"{res}/H{n:04d}.bil", nx, ny)
        dev = max(abs(c[j][i] - c0) for j in range(ny) for i in range(nx) if h[j][i] > 0.01)
        hmin = min(min(r) for r in h)
        hmax = max(max(r) for r in h)
        good = dev <= 1.0e-5 * c0
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} 分布 {n}: 濃度のずれの最大 {dev:.2e} mg/L"
              f"(水深は {hmin:.3f}〜{hmax:.3f} m)")
    return ok


def check_wall(args):
    res, nx, ny, dx, ir, n = args[0], int(args[1]), int(args[2]), float(args[3]), int(args[4]), int(args[5])
    c = read_bil(f"{res}/C{n:04d}.bil", nx, ny)
    h = read_bil(f"{res}/H{n:04d}.bil", nx, ny)
    east = max(abs(c[j][i]) for j in range(ny) for i in range(ir, nx))
    west = [c[j][i] for j in range(ny) for i in range(ir - 1)]
    mass = sum(c[j][i] * h[j][i] for j in range(ny) for i in range(nx)) * dx * dx
    head, data = read_csv(f"{res}/wq.csv")
    inp = data[-1][head.index("in_point_g")]
    ok = True
    good = east == 0.0
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 尾根の東側の濃度の最大 {east:.3e} mg/L(厳密に 0)")
    spread = (max(west) - min(west)) / (sum(west) / len(west))
    good = spread <= 0.05
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 西側の濃度の幅 / 平均 = {spread:.3f}(一様に近づく。0.05 以下)")
    err = abs(mass - inp) / inp
    good = err <= TOL_MASS
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 分布の質量 {mass:.6e} g = 投入 {inp:.6e} g(相対差 {err:.1e})")
    return ok


def check_gv(args):
    res, nx, ny, dx, n = args[0], int(args[1]), int(args[2]), float(args[3]), int(args[4])
    c = read_bil(f"{res}/C{n:04d}.bil", nx, ny)
    h = read_bil(f"{res}/H{n:04d}.bil", nx, ny)
    gv = read_bil(f"{res}/A0000.bil", nx, ny)
    amin = min(min(r) for r in gv)
    vol = sum(gv[j][i] * h[j][i] for j in range(ny) for i in range(nx)) * dx * dx
    mass = sum(c[j][i] * gv[j][i] * h[j][i] for j in range(ny) for i in range(nx)) * dx * dx
    head, data = read_csv(f"{res}/wq.csv")
    inp = data[-1][head.index("in_point_g")]
    msur = data[-1][head.index("mass_surface_g")]
    flat = [v for row in c for v in row]
    mean = sum(flat) / len(flat)
    ok = True
    spread = (max(flat) - min(flat)) / mean
    good = spread <= 1.0e-5
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 濃度の幅 / 平均 = {spread:.1e}(水の入る面積の割合 {amin:.2f}〜1 によらず一様。1e-5 以下)")
    want = inp / vol
    err = abs(mean - want) / want
    good = err <= 1.0e-5
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 濃度 {mean:.6f} mg/L = 投入 {inp:.1f} g ÷ 水の体積 {vol:.1f} m3 = {want:.6f}"
          f"(相対差 {err:.1e})")
    err = abs(msur - inp) / inp
    good = err <= 1.0e-12
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 台帳: 地表の質量 {msur:.7e} g = 投入 {inp:.7e} g(相対差 {err:.1e})")
    err = abs(mass - inp) / inp
    good = err <= TOL_MASS
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 分布の質量 {mass:.6e} g = 投入(相対差 {err:.1e})")
    return ok


def read_probe(path):
    """プローブ CSV(# の行は見出し)。列名 → 値のリストの辞書を返す"""
    names, cols = None, None
    with open(path) as f:
        for line in f:
            if line.startswith("#"):
                if "t(hour)" in line:
                    names = [n.strip() for n in line.lstrip("#").split(",")]
                    cols = {n: [] for n in names}
                continue
            v = [float(x) for x in line.split(",")]
            for n, x in zip(names, v):
                cols[n].append(x)
    return cols


def check_sat(args):
    res = args[0]
    area, h0, c0, csat, e, dt, dd = [float(a) for a in args[1:8]]
    head, data = read_csv(f"{res}/wq.csv")
    it, im, ip = head.index("time_s"), head.index("mass_surface_g"), head.index("mass_pool_g")
    ipr, idi = head.index("precip_g"), head.index("dissol_g")
    m0 = c0 * h0 * area
    worst = wclose = wled = 0.0
    nsat = ndry = 0
    for r in data:
        t = r[it]
        hb = h0 - e * max(t - dt, 0.0)           # そのステップの蒸発の前の水深
        want = min(m0, csat * hb * area) if hb > dd else 0.0
        if t == 0.0:
            want = m0
        worst = max(worst, abs(r[im] - want) / m0)
        wclose = max(wclose, abs(r[im] + r[ip] - m0) / m0)
        wled = max(wled, abs(r[ipr] - r[idi] - r[ip]) / m0)
        nsat += 0.0 < want < m0
        ndry += want == 0.0
    ok = True
    for name, v, tol in (("水柱の物質が min(初期量, 溶解度 × 蒸発の前の水深) に合う", worst, 3.0e-7),
                         ("水柱 + 析出物 = 初期量", wclose, 3.0e-7),
                         ("析出 − 溶解 = 析出物の現在量", wled, 3.0e-7)):
        good = v <= tol
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} {name}(初期量に対する差の最大 {v:.1e})")
    good = nsat >= 5 and ndry >= 3
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 記録 {len(data)} 行のうち、析出の途中 {nsat} 行、干上がった後 {ndry} 行")
    return ok


def check_dis(args):
    res, nx, ny, n = args[0], int(args[1]), int(args[2]), int(args[3])
    csat, h0, bw, be = [float(a) for a in args[4:8]]
    c = read_bil(f"{res}/C{n:04d}.bil", nx, ny)
    b = read_bil(f"{res}/B{n:04d}.bil", nx, ny)          # kg/ha
    ok = True
    for name, cols, b0 in (("西", range(0, nx // 2), bw), ("東", range(nx // 2, nx), be)):
        cw = min(csat, b0 * 1000.0 / h0)                 # 濃度 (mg/L = g/m3)
        bwant = (b0 - cw * h0 / 1000.0) * 1.0e4          # 残った析出物 (kg/ha)
        ec = max(abs(c[j][i] - cw) for j in range(ny) for i in cols) / csat
        eb = max(abs(b[j][i] - bwant) for j in range(ny) for i in cols) / (bw * 1.0e4)
        good = ec <= 1.0e-6 and eb <= 1.0e-6
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} {name}半分: 濃度 {cw/1000:.1f} g/L(差 {ec:.1e})、"
              f"残った析出物 {bwant/1e4:.1f} kg/m2(差 {eb:.1e})")
    head, data = read_csv(f"{res}/wq.csv")
    r = data[-1]
    tot = r[head.index("mass_surface_g")] + r[head.index("mass_pool_g")]
    m0 = (bw + be) / 2.0 * 1000.0 * nx * ny * 100.0
    good = abs(tot - m0) / m0 <= 3.0e-7
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 台帳: 水柱 + 析出物 = 初期の析出物(相対差 {abs(tot - m0) / m0:.1e})")
    return ok


def check_disk(args):
    import math
    res = args[0]
    csat, h0, k, bw, be, dtr = [float(a) for a in args[1:7]]
    ok = True
    for num, name, b0 in ((1, "西", bw), (2, "東", be)):
        p = read_probe(f"{res}/probes/probe{num:04d}.csv")
        cend = min(csat, b0 * 1000.0 / h0)
        worst = 0.0
        nrise = nflat = 0
        for tm, c in zip(p["t(min)"], p["C(mg/L)"]):
            t = round(tm * 60.0 / dtr) * dtr          # 記録の時刻(印字は 5 桁なので間隔の整数倍に戻す)
            want = min(csat * (1.0 - math.exp(-k * t / h0)), cend)
            worst = max(worst, abs(c - want) / csat)
            nrise += want < cend * (1.0 - 1.0e-9)
            nflat += want >= cend * (1.0 - 1.0e-9)
        good = worst <= 1.0e-9 and nrise >= 3 and (nflat >= 3 or cend >= csat)
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} {name}のプローブ: C = Csat (1 − exp(−k t / h)) を {cend/1000:.0f} g/L で頭打ち"
              f"(Csat に対する差の最大 {worst:.1e}。上昇中 {nrise} 点、頭打ち {nflat} 点)")
    return ok


def check_inf(args):
    res, nx, ny, n = args[0], int(args[1]), int(args[2]), int(args[3])
    csat, rain, bw, be, rr, dpump = [float(a) for a in args[4:10]]
    nstep, iw, jw, ie, je = [int(a) for a in args[10:15]]
    cg = read_bil(f"{res}/Cg{n:04d}.bil", nx, ny)        # g/m2
    hg = read_bil(f"{res}/Hg{n:04d}.bil", nx, ny)        # m
    b = read_bil(f"{res}/B{n:04d}.bil", nx, ny)          # kg/ha
    ok = True
    nominal = rain
    rain = hg[0][0]                                      # 浸透した雨の総量 = 井戸のないセルの地下貯留
    good = abs(rain - nominal) / nominal <= 0.03
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 浸透した雨の総量 {rain*1000:.3f} mm(名目 {nominal*1000:.1f} mm の 3 % 以内)")
    cap = csat * rain                                    # 浸透水が溶かせる上限 (g/m2)
    removed = 0.0
    for name, cols, b0, (ip, jp) in (("西", range(0, nx // 2), bw, (iw, jw)),
                                     ("東", range(nx // 2, nx), be, (ie, je))):
        m_in = min(b0 * 1000.0, cap)                     # 地下へ入った量 (g/m2)
        # 井戸のセル: 汲む水は min(cg/hg, Csat)/R の濃度を運ぶ(ステップごとに同じ式で進める)
        m, w = m_in, rain
        fx = dpump / nstep
        for _ in range(nstep):
            m -= min(m / w, csat) / rr * fx
            w -= fx
        removed += (m_in - m) * 100.0
        e1 = e2 = e3 = 0.0
        for j in range(ny):
            for i in cols:
                pumped = (i + 1, j + 1) == (ip, jp)
                e1 = max(e1, abs(cg[j][i] - (m if pumped else m_in)) / cap)
                e2 = max(e2, abs(hg[j][i] - (rain - dpump if pumped else rain)) / rain)
                e3 = max(e3, abs(b[j][i] / 10.0 - (b0 * 1000.0 - m_in)) / (bw * 1000.0))
        good = max(e1, e2, e3) <= 2.0e-6
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} {name}半分: 地下へ入った物質 {m_in/1000:.2f} kg/m2、井戸のセルに残る物質 "
              f"{m/1000:.4f} kg/m2、残った析出物 {(b0 * 1000.0 - m_in)/1000:.1f} kg/m2"
              f"(差の最大: Cg {e1:.1e}・Hg {e2:.1e}・B {e3:.1e})")
    head, data = read_csv(f"{res}/wq.csv")
    r = data[-1]
    out = r[head.index("out_intake_g")]
    good = abs(out - removed) / removed <= 3.0e-7
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 台帳: 井戸が運び出した量 {out:.7e} g = 式 {removed:.7e} g"
          f"(相対差 {abs(out - removed) / removed:.1e})")
    m0 = (bw + be) / 2.0 * 1000.0 * nx * ny * 100.0
    tot = r[head.index("mass_surface_g")] + r[head.index("mass_pool_g")] + r[head.index("mass_gw_g")] + out
    good = abs(tot - m0) / m0 <= 3.0e-7
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 台帳: 水柱 + 析出物 + 地下 + 井戸 = 初期の析出物(相対差 {abs(tot - m0) / m0:.1e})")
    dis, tog = r[head.index("dissol_g")], r[head.index("to_gw_g")]
    good = abs(dis - tog) / tog <= 3.0e-7
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 台帳: 溶解 = 浸透(浸透水が溶かした分は両方に数える。相対差 {abs(dis - tog) / tog:.1e})")
    return ok


def check_sea(args):
    res, nx, ny, csea = args[0], int(args[1]), int(args[2]), float(args[3])
    ok = True
    for n in [int(a) for a in args[4:]]:
        c = read_bil(f"{res}/C{n:04d}.bil", nx, ny)
        h = read_bil(f"{res}/H{n:04d}.bil", nx, ny)
        land = [abs(c[j][i] - csea) for j in range(ny) for i in range(1, nx) if h[j][i] > 0.01]
        sea = max(abs(c[j][0] - csea) for j in range(ny))
        good = len(land) > 0 and max(land) <= 1.0e-5 * csea and sea <= 1.0e-5 * csea
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} 分布 {n}: 水のある陸のセル {len(land)} 個の濃度のずれの最大 "
              f"{max(land) if land else float('nan'):.2e} mg/L、海セルのずれ {sea:.2e} mg/L")
    head, data = read_csv(f"{res}/wq.csv")
    ii, io, im = head.index("in_sea_g"), head.index("out_sea_g"), head.index("mass_surface_g")
    scale = max(r[ii] for r in data)
    worst = max(abs(r[ii] - r[io] - r[im]) for r in data) / scale
    good = worst <= 3.0e-7
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 台帳: 海から入った量 − 海へ出た量 = 地表の質量(差の最大 / 入った量 = {worst:.1e})")
    r = data[-1]
    good = r[ii] > 0.0 and r[io] > 0.05 * r[ii]
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} 海から入った量 {r[ii]:.4e} g、海へ出た量 {r[io]:.4e} g(満ち潮と引き潮の両方)")
    return ok


def check_c0map(args):
    res, nx, ny, ir, cw, ce = args[0], int(args[1]), int(args[2]), int(args[3]), float(args[4]), float(args[5])
    ok = True
    for n in [int(a) for a in args[6:]]:
        c = read_bil(f"{res}/C{n:04d}.bil", nx, ny)
        dw = max(abs(c[j][i] - cw) for j in range(ny) for i in range(ir - 1))
        de = max(abs(c[j][i] - ce) for j in range(ny) for i in range(ir, nx))
        good = dw <= 1.0e-5 * cw and de <= 1.0e-5 * ce
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} 分布 {n}: 尾根の西 {cw:g} mg/L(ずれ {dw:.1e})、東 {ce:g} mg/L(ずれ {de:.1e})")
    return ok


def check_evts(args):
    res, area, h0, total = args[0], float(args[1]), float(args[2]), float(args[3])
    head, data = read_csv(f"{res}/evap.csv")
    it, iv = head.index("time_s"), head.index("ev_total_m3")
    tend = data[-1][it]
    ok = True
    for frac in (0.5, 1.0):
        r = min(data, key=lambda x: abs(x[it] - frac * tend))
        want = frac * total * area
        err = abs(r[iv] - want) / (total * area)
        good = err <= 3.0e-7
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} t = {r[it]:.0f} s の累積蒸発量 {r[iv]:.7e} m3(式 {want:.7e}。差 {err:.1e})")
    s_last = None
    with open(f"{res}/Log.txt") as f:
        for line in f:
            p = line.split()
            if len(p) >= 3 and p[0].count(":") == 2 and p[1].endswith("%"):
                s_last = float(p[2])
    err = abs(s_last - (h0 - total))
    good = err <= 1.0e-12
    ok = ok and good
    print(f"  {'ok  ' if good else 'FAIL'} Log.txt の最後の貯留高 {s_last:.14f} m(初期 {h0} m − {total} m。差 {err:.1e})")
    return ok


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    mode, args = sys.argv[1], sys.argv[2:]
    table = {"mix": check_mix, "uniform": check_uniform, "wall": check_wall, "gv": check_gv,
             "sat": check_sat, "dis": check_dis, "disk": check_disk, "inf": check_inf,
             "sea": check_sea, "c0map": check_c0map, "evts": check_evts}
    if mode not in table:
        raise SystemExit(__doc__)
    ok = table[mode](args)
    print(("PASS" if ok else "FAIL") + f": wqsalt {mode}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
