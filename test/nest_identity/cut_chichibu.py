#!/usr/bin/env python3
"""親(chichibu 500 m)の地形・河道・流域マスクの部分窓を子格子のデータとして切り出す。
テキストの字句をそのまま写すので値はビット同一。
  python3 cut_chichibu.py SRC_DIR DST_DIR i0 j0 nxc nyc
"""
import sys, os
src, dst, i0, j0, nxc, nyc = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
os.makedirs(dst, exist_ok=True)
for fn in ("Chichibu_500m_filled.txt", "Chichibu_500m_river.txt", "Chichibu_500m_basin.txt"):
    rows = [l.split() for l in open(os.path.join(src, fn)) if l.strip()]
    out = [" ".join(r[i0-1:i0-1+nxc]) for r in rows[j0-1:j0-1+nyc]]
    assert len(out) == nyc and all(len(l.split()) == nxc for l in out), fn
    open(os.path.join(dst, fn), "w").write("\n".join(out) + "\n")
print(f"cut {nxc}x{nyc} at ({i0},{j0}) -> {dst}")
