"""CultureShyft Media logo system, from mark #2 "The Y" (the Y of Shyft as a broadcast antenna).

Generates vector SVGs (text as outlines, no font dependency) for every lockup and colourway:
  lockups:   horizontal, stacked, mark, wordmark
  colourways: color-onlight, color-ondark, mono-black, mono-white
Run tools/export.sh afterwards for PDF, PNG, icons and favicon.
"""
import os, io, sys, math
sys.path.insert(0, r"C:\Users\mstat\projects\ncc-media-shirts\src")
import textpaths
textpaths.FILES.update({"Manrope": "Manrope.ttf"})
from textpaths import text_path as text, text_width, glyph_spans

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "logo", "svg"); os.makedirs(OUT, exist_ok=True)

ACCENT = "#ff5a1f"; INK = "#14151a"; PAPER = "#ffffff"
COLORWAYS = {
    "color-onlight": dict(ink=INK, accent=ACCENT, bg=None),
    "color-ondark":  dict(ink="#ffffff", accent=ACCENT, bg=None),
    "mono-black":    dict(ink=INK, accent=INK, bg=None),
    "mono-white":    dict(ink="#ffffff", accent="#ffffff", bg=None),
}

def mark(x, y, s, ink, accent):
    """The Y antenna in a box of side s at (x, y). Geometry on a 100-unit grid."""
    k = s / 100
    g = f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.4f})">'
    g += f'<path d="M 50 56 L 24 26" stroke="{ink}" stroke-width="14" stroke-linecap="round" fill="none"/>'
    g += f'<path d="M 50 56 L 76 26" stroke="{ink}" stroke-width="14" stroke-linecap="round" fill="none"/>'
    g += f'<rect x="43" y="52" width="14" height="40" rx="7" fill="{ink}"/>'
    g += f'<path d="M 36 20 A 20 20 0 0 1 64 20" stroke="{accent}" stroke-width="7" stroke-linecap="round" fill="none"/>'
    g += f'<path d="M 28 10 A 31 31 0 0 1 72 10" stroke="{accent}" stroke-width="7" stroke-linecap="round" fill="none"/>'
    return g + '</g>'

def wordmark(x, y, size, ink, accent, anchor="start", media=True):
    """CULTURESH[Y]FT with the Y in accent, MEDIA spaced below. Returns (svg, width, height)."""
    sp = size * 0.01
    full = "CULTURESHYFT"
    w = text_width(full, size, "Manrope", 800, sp)
    x0 = x - w / 2 if anchor == "middle" else x
    spans = glyph_spans(full, size, "Manrope", 800, sp)
    g = ""
    for i, ch in enumerate(full):
        g += text(x0 + spans[i][0], y, ch, size, "Manrope", 800, 0, anchor="start", fill=(accent if ch == "Y" else ink))
    h = size * 0.72
    if media:
        g += text(x0 + 4, y + size * 0.46, "MEDIA", size * 0.30, "Manrope", 700, size * 0.13, anchor="start", fill=ink, extra='fill-opacity="0.78"')
        h += size * 0.56
    return g, w, h

def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w/300:.4f}in" height="{h/300:.4f}in" viewBox="0 0 {w} {h}">'
            f'<title>{title}</title>{body}</svg>\n')

def build(lockup, cw):
    c = COLORWAYS[cw]; ink, acc = c["ink"], c["accent"]
    if lockup == "mark":
        W = H = 1200
        body = mark(100, 100, 1000, ink, acc)
    elif lockup == "wordmark":
        size = 300; wm, w, h = wordmark(0, size * 0.72, size, ink, acc)
        W, H = int(w + 160), int(h + 160)
        body = f'<g transform="translate(80 80)">{wm}</g>'
    elif lockup == "horizontal":
        size = 300; ms = size * 1.55
        wm, w, h = wordmark(0, size * 0.72, size, ink, acc)
        W, H = int(ms + 120 + w + 200), int(ms + 200)
        body = mark(100, 100, ms, ink, acc) + f'<g transform="translate({100 + ms + 120:.0f} {100 + (ms - h) / 2 + size * 0.08:.0f})">{wm}</g>'
    elif lockup == "stacked":
        size = 260; ms = 760
        wm, w, h = wordmark(0, size * 0.72, size, ink, acc)
        W = int(max(w, ms) + 240); H = int(ms + 120 + h + 240)
        body = mark((W - ms) / 2, 120, ms, ink, acc) + f'<g transform="translate({(W - w) / 2:.0f} {120 + ms + 120:.0f})">{wm}</g>'
    return svg(W, H, body, f"CultureShyft Media {lockup} {cw}"), W, H

if __name__ == "__main__":
    import json
    index = {}
    for lockup in ("horizontal", "stacked", "mark", "wordmark"):
        for cw in COLORWAYS:
            s, W, H = build(lockup, cw)
            name = f"cultureshyft-{lockup}-{cw}"
            io.open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8", newline="\n").write(s)
            index[name] = {"w": W, "h": H, "lockup": lockup, "colorway": cw, "dark_bg": cw in ("color-ondark", "mono-white")}
    json.dump(index, open(os.path.join(OUT, "index.json"), "w"), indent=1)
    print("wrote", len(index), "svgs")
