#!/bin/bash
# Export the logo system: PNG (300 DPI, transparent) + web PNG + vector PDF per SVG, app icons and favicon from the mark,
# and a review sheet. Chrome headless does the rendering (no window).
R="C:/Users/mstat/projects/cultureshyft-media"; CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
cd "$R" && python tools/build_logo.py && mkdir -p logo/png logo/pdf logo/web logo/icons tools/html && python - <<'PY'
import io, os, re, json, subprocess
R = os.getcwd(); CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
index = json.load(open("logo/svg/index.json"))
for name, m in index.items():
    svg = io.open(f"logo/svg/{name}.svg", encoding="utf-8").read(); w, h = m["w"], m["h"]
    bg = "#14151a" if m["dark_bg"] else "transparent"
    io.open(f"tools/html/{name}.html", "w", encoding="utf-8").write(f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;padding:0;background:transparent;overflow:hidden}} svg{{display:block;width:{w}px;height:{h}px}}</style></head><body>{svg}</body></html>')
    io.open(f"tools/html/{name}-pdf.html", "w", encoding="utf-8").write(f'<!doctype html><html><head><meta charset="utf-8"><style>@page{{size:{w/300}in {h/300}in;margin:0}} html,body{{margin:0;padding:0;width:{w/300}in;height:{h/300}in;overflow:hidden;background:{bg}}} svg{{display:block;width:{w/300}in;height:{h/300}in}}</style></head><body>{svg}</body></html>')
    subprocess.run([CHROME,"--headless=new","--no-sandbox","--disable-gpu","--hide-scrollbars",f"--window-size={w},{h}","--force-device-scale-factor=1","--default-background-color=00000000",f"--screenshot={R}/logo/png/{name}.png",f"file:///{R}/tools/html/{name}.html"],capture_output=True)
    subprocess.run([CHROME,"--headless=new","--no-sandbox","--disable-gpu","--no-pdf-header-footer",f"--print-to-pdf={R}/logo/pdf/{name}.pdf",f"file:///{R}/tools/html/{name}-pdf.html"],capture_output=True)
    print("exported", name)
from PIL import Image
for name, m in index.items():
    im = Image.open(f"logo/png/{name}.png").convert("RGBA"); assert im.size == (m["w"], m["h"]), (name, im.size)
    scale = 1200 / im.width
    im.resize((1200, max(1, int(im.height * scale))), Image.LANCZOS).save(f"logo/web/{name}.png", optimize=True)
# icons and favicon from the colour mark on a paper-white tile and on the ink tile
mk = Image.open("logo/png/cultureshyft-mark-color-onlight.png").convert("RGBA")
for bgname, bg in (("light", (255, 255, 255, 255)), ("dark", (20, 21, 26, 255))):
    src = Image.open(f"logo/png/cultureshyft-mark-color-{'onlight' if bgname == 'light' else 'ondark'}.png").convert("RGBA")
    for size in (16, 32, 48, 64, 128, 180, 192, 256, 512, 1024):
        tile = Image.new("RGBA", src.size, bg); tile.alpha_composite(src)
        tile.resize((size, size), Image.LANCZOS).save(f"logo/icons/icon-{bgname}-{size}.png", optimize=True)
    tile = Image.new("RGBA", src.size, bg); tile.alpha_composite(src)
    tile.resize((1080, 1080), Image.LANCZOS).save(f"logo/icons/avatar-{bgname}-1080.png", optimize=True)
tile = Image.new("RGBA", mk.size, (255, 255, 255, 255)); tile.alpha_composite(mk)
tile.save("logo/icons/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
# review sheet
names = [n for n in index]
rows = []
for lockup in ("horizontal", "stacked", "wordmark", "mark"):
    row = Image.new("RGB", (2400, 420), (128, 128, 128)); x = 0
    for cw in ("color-onlight", "mono-black", "color-ondark", "mono-white"):
        n = f"cultureshyft-{lockup}-{cw}"; m = index[n]
        bg = (20, 21, 26) if m["dark_bg"] else (255, 255, 255)
        im = Image.open(f"logo/web/{n}.png").convert("RGBA"); im.thumbnail((560, 380))
        cell = Image.new("RGBA", (600, 420), bg + (255,)); cell.alpha_composite(im, ((600 - im.width) // 2, (420 - im.height) // 2))
        row.paste(cell.convert("RGB"), (x, 0)); x += 600
    rows.append(row)
sheet = Image.new("RGB", (2400, 4 * 430), (128, 128, 128))
for i, r in enumerate(rows): sheet.paste(r, (0, i * 430))
sheet.save("logo/review-sheet.jpg", quality=86)
print("icons + favicon + review sheet ok")
PY
