#!/usr/bin/env python3
"""ENCflow を BMI で駆動しながら、水深分布と水深時系列を順次表示する。

計算の進行は Python 側が update_until で完全に制御するので、表示間隔は
モデルのファイル出力(dt_file)と合わせても、別の間隔にしてもよい。
--interval 省略時は param.txt の dt_file を読んで同じタイミングで表示する
(ファイル出力と画面表示が同期する)。

使い方(ケースディレクトリで):
    python3 ../../bmi/python/live_view.py param.txt                 # 画面に順次表示
    python3 ../../bmi/python/live_view.py param.txt --interval 60
    python3 ../../bmi/python/live_view.py param.txt --probe 50 2    # セル(i,j)の時系列
    python3 ../../bmi/python/live_view.py param.txt --save frames   # PNG 連番保存(ヘッドレス)

表示: 左 = 地形(グレー)+水深(青系の単色シーケンシャル)、
      右 = 水深の時系列(--probe セル、省略時は領域最大水深)。
BMI 層は行順を標準形(行0=南)に正規化して返すため origin='lower' で
表示する。--probe は ENCflow 内部のセル番地 (i, j)(j=1 が北。record の
プローブ指定と同じ流儀)で受け、内部で行反転後の添字に変換する。
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from encflow import ENCflow, VAR_DEPTH, VAR_ELEVATION  # noqa: E402

HMIN = 0.001  # これ未満の水深は「水なし」として描かない (m)


def read_dt_file(param_path):
    """param.txt の namelist から dt_file (s) を読む(見つからなければ None)。

    数値形式 `dt_file = 3600` と文字列形式 `dt_file_c = "10 min"`
    (d/h/m/s の組み合わせ。m は分)の両方に対応する。
    """
    num = re.compile(r"^\s*dt_file\s*=\s*([0-9.+\-]+(?:[eEdD][+\-]?[0-9]+)?)")
    cstr = re.compile(r"^\s*dt_file_c\s*=\s*['\"]([^'\"]+)['\"]")
    unit_s = {"d": 86400.0, "h": 3600.0, "m": 60.0, "min": 60.0, "s": 1.0}
    with open(param_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = num.match(line)
            if m:
                return float(m.group(1).replace("d", "e").replace("D", "e"))
            m = cstr.match(line)
            if m:
                total = 0.0
                for val, unit in re.findall(r"([0-9.]+)\s*(min|[dhms])",
                                            m.group(1)):
                    total += float(val) * unit_s[unit]
                if total > 0:
                    return total
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("param", help="ENCflow パラメータファイル")
    ap.add_argument("--interval", type=float, default=None,
                    help="表示間隔 (s)。省略時は param の dt_file")
    ap.add_argument("--probe", type=int, nargs=2, metavar=("I", "J"),
                    default=None, help="時系列を取るセル(1始まり)。省略時は領域最大")
    ap.add_argument("--save", metavar="DIR", default=None,
                    help="表示せず PNG 連番を DIR に保存(ヘッドレス環境向け)")
    ap.add_argument("--vmax", type=float, default=None,
                    help="水深カラースケールの上限 (m)。省略時は自動拡大")
    args = ap.parse_args()

    if args.save:
        import matplotlib
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    model = ENCflow(args.param)
    t0, tend, dt = model.start_time, model.end_time, model.time_step
    interval = args.interval or read_dt_file(args.param) or 20 * dt
    # dt の整数倍に丸める(update_until の受理条件)
    interval = max(round(interval / dt), 1) * dt
    ny, nx = model.grid_shape
    dy, dx = model.grid_spacing

    print(f"live_view: {model.name}  grid {nx} x {ny}  dt={dt:g}s  "
          f"tend={tend:g}s  interval={interval:g}s")

    z = model.get2d(VAR_ELEVATION)
    extent = (0.0, nx * dx, 0.0, ny * dy)   # BMI 標準形(行0=南)→ origin='lower'

    fig, (ax_map, ax_ts) = plt.subplots(
        1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1.3, 1.0]})
    fig.suptitle(f"ENCflow via BMI — {Path(args.param).name}")

    # 左: 地形(グレー)+ 水深(単色シーケンシャル。マゼンタ等は使わない)
    ax_map.imshow(z, cmap="Greys", origin="lower", extent=extent,
                  interpolation="nearest")
    im = ax_map.imshow(np.full((ny, nx), np.nan), cmap="Blues",
                       origin="lower", extent=extent,
                       interpolation="nearest",
                       vmin=0.0, vmax=args.vmax or HMIN)
    cbar = fig.colorbar(im, ax=ax_map, shrink=0.85, label="water depth h (m)")
    ax_map.set_xlabel("x (m)")
    ax_map.set_ylabel("y (m)")

    # 右: 水深の時系列(1系列なので凡例は置かずタイトルで名乗る)
    if args.probe:
        ip, jp = args.probe
        ts_title = f"h at cell (i={ip}, j={jp})"
    else:
        ip = jp = None
        ts_title = "max h in domain"
    (line,) = ax_ts.plot([], [], lw=2)
    ax_ts.set_xlim(t0, tend)
    ax_ts.set_xlabel("t (s)")
    ax_ts.set_ylabel("h (m)")
    ax_ts.set_title(ts_title)
    ax_ts.grid(True, alpha=0.3)

    if args.save:
        outdir = Path(args.save)
        outdir.mkdir(parents=True, exist_ok=True)
    else:
        plt.ion()
        plt.show()

    times, series = [], []
    frame = 0

    def draw(t):
        nonlocal frame
        h = model.get2d(VAR_DEPTH)
        wet = np.where(h >= HMIN, h, np.nan)
        im.set_data(wet)
        hmax = float(np.nanmax(h))
        if args.vmax is None and hmax > im.get_clim()[1]:
            im.set_clim(0.0, hmax)          # 自動拡大(縮めない = ちらつき防止)
        ax_map.set_title(f"t = {t:,.0f} s   max h = {hmax:.3f} m")
        times.append(t)
        # 内部セル (i, j)(j=1=北)→ 標準形配列(行0=南)の添字
        series.append(h[ny - jp, ip - 1] if ip else hmax)
        line.set_data(times, series)
        ax_ts.relim()
        ax_ts.autoscale_view(scalex=False)
        if args.save:
            fig.savefig(outdir / f"frame_{frame:04d}.png", dpi=110)
        else:
            fig.canvas.draw_idle()
            plt.pause(0.01)
        frame += 1

    draw(model.time)                        # 初期状態
    while model.time < tend:
        model.update_until(min(model.time + interval, tend))
        draw(model.time)

    model.finalize()
    print(f"live_view: finished at t = {times[-1]:g} s ({frame} frames)")
    if args.save:
        print(f"live_view: frames saved in {outdir}/")
    else:
        plt.ioff()
        plt.show()                          # 最終フレームを表示したまま終わる


if __name__ == "__main__":
    main()
