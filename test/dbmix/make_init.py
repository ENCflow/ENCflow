#!/usr/bin/env python3
# test/dbmix の入力と設定の生成(Check_dbmix.py と定数を対で保守)
#   地形: 転置した遷緩点つき斜面 20 × 60 セル(Δx = 1 m)。流れは j 方向(南向き)で、MPI の帯の界面を
#   横切る。y < YB で tanθ = ST、それより下流は平坦(z = 0)。雛形 b(境界から入る土石流)だけは、下流を
#   勾配 SB の緩い斜面にして南辺の自由流出まで流す(z_out.txt。遷緩点で一部が積もり、残りは流れ出る)。
#   python3 make_init.py        入力(z_slope.txt・z_out.txt・sd_rel.txt・sd_zero.txt・sd_film.txt・dbinit.txt・
#                               dbinit_half.txt・dbinit_film.txt・csfrac.txt)と、
#                               雛形 param_e.txt・param_r.txt・param_s.txt・param_b.txt から作る構成の設定
#                               p_<構成>.txt を書く(雛形の行を差し替える。差し替えた行には注釈を付ける)
#   python3 make_init.py list   構成の一覧を表示する(Run.sh・Run_MPI.sh が使う)
import re
import sys

NX, NY, DX = 20, 60, 1.0
ST, YB = 0.4, 40.0
SB = 0.1                         # 雛形 b の下流の勾配(z_out.txt)
# 崩壊域(瞬時流動化の区画): i ∈ [RI1, RI2]、j ∈ [RJ1, RJ2]。土層はここだけ(ほかは基盤)
RI1, RI2, RJ1, RJ2 = 5, 16, 5, 16
SD_REL = 1.0                     # 崩壊域の土層厚 (m)
D_HALF = 0.5                     # 構成 rp3 の崩壊深 (m。土層の上半分)
# 構成 film3 の、倍精度の下限に近い厚さの膜(正規化数の下限は 2.225e-308)。膜の半分を流動化すると、もとの厚さ・
# 残る厚さ(2.3e-308 m。正規化数)と割合(0.6 以下)の積が、どれも正規化数より小さくなる
SD_FILM, D_FILM = 4.6e-308, 2.3e-308
# 流入土砂の粒径階の割合の時系列(構成 bt3。時刻 min, f_1, f_2, f_3)。区間で線形補間
CSFRAC = [(0.0, 1.0, 0.0, 0.0),
          (1.0 / 3.0, 0.0, 0.0, 1.0),
          (10.0, 0.0, 0.0, 1.0)]


def z_of(j):
    y = (j - 0.5) * DX
    return ST * (YB - y) if y < YB else 0.0


def zout_of(j):
    y = (j - 0.5) * DX
    return ST * (YB - y) + SB * (NY * DX - YB) if y < YB else SB * (NY * DX - y)


def in_patch(i, j):
    return RI1 <= i <= RI2 and RJ1 <= j <= RJ2


def write_inputs():
    with open("z_slope.txt", "w") as f:
        for j in range(1, NY + 1):
            f.write(" ".join("%.6f" % z_of(j) for i in range(NX)) + "\n")
    with open("z_out.txt", "w") as f:
        for j in range(1, NY + 1):
            f.write(" ".join("%.6f" % zout_of(j) for i in range(NX)) + "\n")
    for name, val in (("sd_rel.txt", SD_REL), ("dbinit.txt", SD_REL), ("dbinit_half.txt", D_HALF)):
        with open(name, "w") as f:
            for j in range(1, NY + 1):
                f.write(" ".join("%.3f" % (val if in_patch(i, j) else 0.0) for i in range(1, NX + 1)) + "\n")
    for name, val in (("sd_film.txt", SD_FILM), ("dbinit_film.txt", D_FILM)):   # 構成 film3: 崩壊域だけに膜
        with open(name, "w") as f:
            for j in range(1, NY + 1):
                f.write(" ".join("%.3e" % (val if in_patch(i, j) else 0.0) for i in range(1, NX + 1)) + "\n")
    with open("sd_zero.txt", "w") as f:                 # 雛形 b: 土層なし(基盤)
        for j in range(1, NY + 1):
            f.write(" ".join("0.0" for i in range(NX)) + "\n")
    with open("csfrac.txt", "w") as f:
        for row in CSFRAC:
            f.write(" ".join("%.10g" % v for v in row) + "\n")


# ---- 構成(雛形, 差し替える行)。キーは「変数名」(雛形にあれば差し替え、なければ &list_geomorph の末尾に足す)。
#      「群:変数名」と書くと、その namelist の群の末尾に足す。値 None はその行を消す
EQ = {"f_bedmix": "1", "bmix_d": "0.002, 0.002, 0.002"}                  # 全粒径階を同じ粒径に(等粒径の極限)
WIDE = {"f_bedmix": "1", "bmix_d": "0.0005, 0.002, 0.008", "bmix_frac0": "0.2, 0.5, 0.3",
        "bmix_sub0": "0.5, 0.3, 0.2", "bmix_la": "0.004"}                # 粒度の幅のある河床(交換層と下層で違う組成)
LABEL = dict(EQ, bmix_frac0="1.0, 0.0, 0.0", bmix_sub0="0.0, 1.0, 0.0", bmix_la="0.002")   # 交換層と下層に別の札
CASES = {
    # --- 侵食起動型(雨で斜面の土層が侵食される。閉領域) ---
    "e1": ("e", {}),                                                     # 単一粒径(基準)
    "e3": ("e", dict(EQ, bmix_frac0="0.3, 0.4, 0.3")),                   # 等粒径・一様な組成(e1 と丸めの範囲で一致)
    "u1": ("e", {"list_enc:f_scalar_scheme": "1"}),                      # 単一粒径・1 次風上
    "u3": ("e", dict(LABEL, **{"list_enc:f_scalar_scheme": "1"})),       # 等粒径・札つき・1 次風上(u1 と一致)
    "m3": ("e", dict(LABEL)),                                            # 等粒径・札つき・MUSCL(e1 との差は制限関数の水準)
    "w3": ("e", dict(WIDE)),                                             # 粒度の幅(粒径階ごとの保存)
    "tk3": ("e", dict(WIDE, f_dbed="3", f_dbres="3", db_d50="0.01", db_delte="0.005", db_deltd="0.5")),  # 高橋・中川則
    "rt1": ("e", dict(WIDE, tt="24", dt_disp="24")),                     # w3 の 24 s まで(保存。流れに土砂がある)
    "rt2": ("e", dict(WIDE, f_state_restore="1")),                       # rt1 の保存から再開(w3 と最終の保存がビット一致)
    # 交互計算: rt1 の保存(流れに土砂が残る)を、土石流のない混合粒径の構成に復元する
    "alt2": ("e", dict(WIDE, f_debris=None, db_phi=None, db_delte=None, db_deltd=None, f_dbres=None, f_dbstop=None,
                       db_vstop=None, db_wstop=None, tt="1", dt_disp="1", f_state_restore="2")),
    "alt3": ("e", dict(WIDE, f_debris=None, db_phi=None, db_delte=None, db_deltd=None, f_dbres=None, f_dbstop=None,
                       db_vstop=None, db_wstop=None, tt="1", dt_disp="1", f_state_restore="2", f_suspend="1")),
    # --- 瞬時流動化(崩壊域の土層を流動化。ほかは基盤) ---
    "r1": ("r", {}),                                                     # 単一粒径(基準)
    "r3": ("r", dict(EQ, bmix_frac0="0.6, 0.3, 0.1", bmix_sub0="0.1, 0.3, 0.6", bmix_la="0.05")),  # 全層の流動化
    "rp3": ("r", dict(EQ, bmix_frac0="0.6, 0.3, 0.1", bmix_sub0="0.1, 0.3, 0.6", bmix_la="0.05",
                      fn_dbinit="'dbinit_half.txt'", tt="0.02", dt_disp="0.02")),                  # 上半分・1 ステップ
    # 倍精度の下限に近い厚さの膜の上半分を流動化(1 ステップ)。交換層の組成が有効なまま残ること(§139.7)
    "film3": ("r", dict(EQ, bmix_frac0="0.4, 0.3, 0.3", bmix_sub0="0.3, 0.3, 0.4", bmix_la="0.05",
                        fn_sd="'sd_film.txt'", fn_dbinit="'dbinit_film.txt'", tt="0.02", dt_disp="0.02")),
    # --- 斜面安定判定(雨 → 飽和 → 流動化。slide_dmax で上から一部) ---
    "s3": ("s", dict(WIDE)),
    # --- 境界から入る土石流(基盤の斜面。南辺は自由流出) ---
    "b3": ("b", dict(EQ, bmix_frac0="0.3, 0.4, 0.3", **{"list_bound_inflow:inflow_csfrac(:,1)": "0.2, 0.3, 0.5"})),
    "bt3": ("b", dict(WIDE, **{"list_bound_inflow:fn_inflow_csfrac(1)": "'csfrac.txt'"})),
    # --- 初期化で止まる構成 ---
    "bstop1": ("b", dict(EQ, bmix_frac0="0.3, 0.4, 0.3")),               # 流入土砂の組成がない
    "bstop2": ("b", dict(EQ, bmix_frac0="0.3, 0.4, 0.3", f_debris="0",
                         **{"list_bound_inflow:inflow_csfrac(:,1)": "0.2, 0.3, 0.5"})),   # 土石流なしに組成だけ
}
RUN = ["e1", "e3", "u1", "u3", "m3", "w3", "tk3", "r1", "r3", "rp3", "film3", "s3", "b3", "bt3"]   # 通しで回す構成
STOP = ["bstop1", "bstop2"]


def render(name):
    base, rep = CASES[name]
    lines = open("param_%s.txt" % base, encoding="utf-8").read().splitlines()
    rep = dict(rep)
    rep.setdefault("dir_result", "'result_%s'" % name)
    rep.setdefault("dir_save", "'save_%s'" % ("rt" if name in ("rt1", "rt2") else name))
    out, group = [], None
    pending = {}                                  # 群ごとに末尾へ足す行
    for key in list(rep):
        if ":" in key:
            g, k = key.split(":", 1)
            pending.setdefault(g, []).append((k, rep.pop(key)))
    used = set()
    for ln in lines:
        m = re.match(r"^\s*&(\w+)", ln)
        if m:
            group = m.group(1)
        m = re.match(r"^(\s*)([A-Za-z_][\w():,]*)\s*=", ln)
        if m and group is not None and m.group(2) in rep:
            key = m.group(2)
            used.add(key)
            if rep[key] is None:
                continue                          # 行を消す
            out.append("%s%s = %s   ! 構成 %s の値" % (m.group(1), key, rep[key], name))
            continue
        if ln.strip() == "/" and group is not None:
            extra = list(pending.get(group, []))
            if group == "list_geomorph":
                extra += [(k, v) for k, v in rep.items() if k not in used and v is not None]
                used.update(k for k, _ in extra)
            for k, v in extra:
                out.append("  %s = %s   ! 構成 %s で足した行" % (k, v, name))
            group = None
        out.append(ln)
    missing = [k for k, v in rep.items() if k not in used and v is not None]
    assert not missing, "keys not placed in %s: %s" % (name, missing)
    with open("p_%s.txt" % name, "w", encoding="utf-8") as f:
        f.write("! test/dbmix の構成 %s(make_init.py が雛形 param_%s.txt から作る。手で直さない)\n" % (name, base))
        f.write("\n".join(out) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print(" ".join(RUN))
    elif len(sys.argv) > 1 and sys.argv[1] == "stop":
        print(" ".join(STOP))
    else:
        write_inputs()
        for c in CASES:
            render(c)
