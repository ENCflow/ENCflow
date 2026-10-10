#!/usr/bin/env python3
"""ユーザーガイド各章の説明図を docs/figs/ に描く(日英)。

  使い方: python3 make_guide_figs.py [章名 ...]   (docs/figs/ で実行。引数なしで全章)
  各章の図は guide/fig_<章名>.py の draw(lang) が描く(データ不要の模式図。matplotlib)。
  ネスティングの図は make_nest_figs.py。計算本体の外(方針 10)。
"""
import glob, importlib, os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "guide"))
names = sys.argv[1:] or sorted(os.path.basename(f)[4:-3] for f in glob.glob(os.path.join(here, "guide", "fig_*.py")))
for n in names:
    mod = importlib.import_module("fig_" + n)
    for lang in ("ja", "en"):
        print("wrote", os.path.relpath(mod.draw(lang), here))
