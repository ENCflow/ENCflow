#!/usr/bin/env python3
"""ネスティングの説明図(docs/users_guide/nest.md、docs/en/users_guide/nest.md 用)を figs/ に描く。

  使い方: python3 docs/figs/make_nest_figs.py [layout|time|bc ...]
  引数なしは従来どおり全3図。各指定は対象だけを日英PNG・SVGで生成。
  nest_layout.png   親子格子の配置(i0, j0・比 r・帯 nb)と親→子・子→親の交換
  nest_time.png     時間進行(親先行・子の r_t サブステップ・帯の時間補間・置換の時機)
  nest_bc.png       親→子の境界方式(帯・Flather・スポンジ)と非静水圧の追加設定
  各図は日本語(<name>.png)と英語(<name>_en.png)、同名のSVGを書く。
  draw(lang) が 3 図をまとめて描く。対象だけの生成には上記の引数を指定する。
計算本体の外(方針 10)。numpy + matplotlib。
"""
import os
import matplotlib
matplotlib.use("Agg")


# ------------------------------------------------------------------ 配置
def fig_layout(lang):
    """Draw only the integer-aligned layout, as PNG and SVG."""
    from guide.fig_nest_layout import draw as draw_layout
    return draw_layout(lang)

# ------------------------------------------------------------------ 時間進行
def fig_time(lang):
    """Draw only the nested time-stepping schematic, as PNG and SVG."""
    from guide.fig_nest_time import draw as draw_time
    return draw_time(lang)

# ------------------------------------------------------------------ 親→子の方式
def fig_bc(lang):
    """Draw boundary methods and the NH supplement, as PNG and SVG."""
    from guide.fig_nest_bc import draw as draw_bc
    return draw_bc(lang)


def draw(lang):
    """lang = "ja" | "en"。3 図を描いて出力パスの列を返す。"""
    return [fig_layout(lang), fig_time(lang), fig_bc(lang)]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("figures", nargs="*", metavar="FIGURE",
                        help="layout, time or bc (default: all three)")
    args = parser.parse_args()
    drawers = {"layout": fig_layout, "time": fig_time, "bc": fig_bc}
    names = args.figures or list(drawers)
    for name in names:
        if name not in drawers:
            parser.error("unknown figure: " + name + " (choose layout, time or bc)")
    outs = []
    for lang in ("ja", "en"):
        outs.extend(drawers[name](lang) for name in names)
    print("wrote " + " ".join(os.path.basename(o) for o in outs))
