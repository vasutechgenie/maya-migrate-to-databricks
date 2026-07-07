#!/usr/bin/env python3
"""Create transparent-background variants of the dark logos (light artwork on
near-black) by keying background to alpha via luminance. Used on dark pages."""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")


def key(src, dst, lo=32, hi=82):
    im = Image.open(src).convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if lum <= lo:
                na = 0
            elif lum >= hi:
                na = 255
            else:
                na = int(round(255 * (lum - lo) / (hi - lo)))
            px[x, y] = (r, g, b, min(a, na))
    im.save(dst)
    print("wrote", dst)


key(os.path.join(ASSETS, "maya-logo-dark.png"),
    os.path.join(ASSETS, "maya-logo-trans.png"))
key(os.path.join(ASSETS, "nmb-logo-dark.png"),
    os.path.join(ASSETS, "nmb-logo-trans.png"))
