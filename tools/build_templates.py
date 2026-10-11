"""Templates for CultureShyft Media: business card, letterhead, flyer, slide, social kit, email signature.
Renders print PDFs (exact page size, bleed on the card) and PNGs with Chrome headless. Edit the HTML blocks to change copy.
"""
import os, io, subprocess, re
R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SRC = os.path.join(R, "templates", "src"); os.makedirs(SRC, exist_ok=True)
for d in ("print", "social", "web"): os.makedirs(os.path.join(R, "templates", d), exist_ok=True)

ACC, INK, PAPER, SAND, SLATE, EMBER = "#FF5A1F", "#14151A", "#FFFFFF", "#F4F3EF", "#6A6E78", "#FFE8DC"
NAME, TITLE, EMAIL, PHONE, SITE, HANDLE = "Mark Andrew", "Cultural Media Artifact Engineer", "mark@cultureshyftmedia.com", "248-505-0050", "cultureshyftmedia.com", "@cultureshyftmedia"
LOGO = lambda n: f"file:///{R}/logo/web/{n}.png".replace("\\", "/")
FONT = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&display=swap">'
BASE = f"body{{margin:0;font-family:Manrope,'Segoe UI',system-ui,sans-serif;color:{INK};-webkit-print-color-adjust:exact;print-color-adjust:exact}} *{{box-sizing:border-box}}"

def render(name, body, css, kind, w_in=None, h_in=None, px=None):
    """kind: 'print' (PDF at w_in x h_in) or 'png' (screenshot at px=(w,h))."""
    if kind == "print":
        html = f'<!doctype html><html><head><meta charset="utf-8">{FONT}<style>@page{{size:{w_in}in {h_in}in;margin:0}} html,body{{width:{w_in}in;height:{h_in}in;overflow:hidden}} {BASE} {css}</style></head><body>{body}</body></html>'
        p = os.path.join(SRC, name + ".html"); io.open(p, "w", encoding="utf-8").write(html)
        out = os.path.join(R, "templates", "print", name + ".pdf")
        subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out}", "file:///" + p.replace("\\", "/")], capture_output=True)
    else:
        w, h = px
        html = f'<!doctype html><html><head><meta charset="utf-8">{FONT}<style>html,body{{width:{w}px;height:{h}px;overflow:hidden}} {BASE} {css}</style></head><body>{body}</body></html>'
        p = os.path.join(SRC, name + ".html"); io.open(p, "w", encoding="utf-8").write(html)
        sub = "social" if "social" in name or "cover" in name or "post" in name or "story" in name else "web"
        out = os.path.join(R, "templates", sub, name + ".png")
        subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}", "--force-device-scale-factor=1", f"--screenshot={out}", "file:///" + p.replace("\\", "/")], capture_output=True)
    print("rendered", name)

# ---------- business card, 3.5 x 2 in with 0.125 in bleed (3.75 x 2.25); keep text 0.25 in from the trim ----------
card_css = f".card{{width:3.75in;height:2.25in;position:relative;overflow:hidden}} .trim{{position:absolute;inset:0.125in;}}"
render("business-card-front", f'''<div class="card" style="background:{INK}"><div class="trim" style="display:flex;align-items:center;justify-content:center;padding:0.2in">
  <img src="{LOGO('cultureshyft-horizontal-color-ondark')}" style="width:2.6in"></div></div>''', card_css, "print", 3.75, 2.25)
render("business-card-back", f'''<div class="card" style="background:{PAPER}"><div class="trim" style="padding:0.22in 0.28in;display:flex;gap:0.22in;align-items:center">
  <img src="{LOGO('cultureshyft-mark-color-onlight')}" style="width:0.75in;height:0.75in">
  <div style="display:flex;flex-direction:column;gap:2pt">
    <div style="font-size:14pt;font-weight:800;letter-spacing:-0.2pt">{NAME}</div>
    <div style="font-size:7.5pt;font-weight:700;letter-spacing:1pt;color:{ACC};text-transform:uppercase">{TITLE}</div>
    <div style="height:2pt;width:0.4in;background:{ACC};margin:4pt 0"></div>
    <div style="font-size:8pt;font-weight:500;color:#3a3d44">{PHONE}</div>
    <div style="font-size:8pt;font-weight:500;color:#3a3d44">{EMAIL}</div>
    <div style="font-size:8pt;font-weight:700">{SITE} · {HANDLE}</div>
  </div></div></div>''', card_css, "print", 3.75, 2.25)

# ---------- letterhead / invoice header, US letter ----------
render("letterhead", f'''<div style="width:8.5in;height:11in;padding:0.6in 0.75in;display:flex;flex-direction:column">
  <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2pt solid {ACC};padding-bottom:0.25in">
    <img src="{LOGO('cultureshyft-horizontal-color-onlight')}" style="width:2.4in">
    <div style="text-align:right;font-size:9pt;font-weight:500;color:{SLATE};line-height:1.5">{NAME}<br>{TITLE}<br>{SITE} · {EMAIL}</div>
  </div>
  <div style="flex:1;padding-top:0.4in;font-size:11pt;line-height:1.5;color:{SLATE}">[Letter or invoice body starts here. Headings in Manrope ExtraBold, body Medium 11 pt.]</div>
  <div style="border-top:1pt solid #dad8d0;padding-top:0.15in;font-size:8pt;font-weight:700;letter-spacing:1pt;color:{SLATE};display:flex;justify-content:space-between"><span>CULTURESHYFT MEDIA</span><span>{SITE}</span><span>{HANDLE}</span></div>
</div>''', "", "print", 8.5, 11)

# ---------- flyer template, US letter ----------
render("flyer-template", f'''<div style="width:8.5in;height:11in;display:flex;flex-direction:column;background:{PAPER}">
  <div style="background:{INK};padding:0.6in 0.6in 0.5in;color:{PAPER};display:flex;flex-direction:column;gap:0.15in">
    <div style="font-size:11pt;font-weight:700;letter-spacing:2pt;color:{ACC}">[CLIENT] · [DATE]</div>
    <div style="font-size:46pt;font-weight:800;line-height:1;letter-spacing:-1pt">[Event or offer headline]</div>
    <div style="font-size:14pt;font-weight:500;color:#cfcfd4;max-width:5.5in;line-height:1.4">[Two lines: where, when, what people get.]</div>
  </div>
  <div style="flex:1;padding:0.5in 0.6in;display:grid;grid-template-columns:1fr 1fr;gap:0.25in;align-content:start">
    <div style="border:2pt solid #dad8d0;border-radius:10pt;padding:0.2in"><div style="font-size:9pt;font-weight:700;letter-spacing:1.5pt;color:{SLATE}">WHEN</div><div style="font-size:16pt;font-weight:800">[Day, time]</div></div>
    <div style="border:2pt solid #dad8d0;border-radius:10pt;padding:0.2in"><div style="font-size:9pt;font-weight:700;letter-spacing:1.5pt;color:{SLATE}">WHERE</div><div style="font-size:16pt;font-weight:800">[Address]</div></div>
    <div style="grid-column:span 2;background:{ACC};border-radius:10pt;padding:0.22in 0.25in;display:flex;justify-content:space-between;align-items:center;color:{PAPER}"><span style="font-size:19pt;font-weight:800">[Call to action]</span><span style="font-size:13pt;font-weight:700">[link or QR]</span></div>
  </div>
  <div style="border-top:1pt solid #dad8d0;padding:0.2in 0.6in;display:flex;justify-content:space-between;align-items:center"><span style="font-size:8pt;font-weight:700;letter-spacing:1.5pt;color:{SLATE}">DESIGNED BY</span><img src="{LOGO('cultureshyft-horizontal-color-onlight')}" style="width:1.9in"></div>
</div>''', "", "print", 8.5, 11)

# ---------- 16:9 title slide ----------
render("slide-title", f'''<div style="width:1920px;height:1080px;background:{INK};color:{PAPER};padding:120px;display:flex;flex-direction:column;justify-content:space-between">
  <img src="{LOGO('cultureshyft-horizontal-color-ondark')}" style="width:520px">
  <div><div style="font-size:96px;font-weight:800;line-height:1;letter-spacing:-2px;max-width:1300px">[Presentation title]</div><div style="font-size:32px;font-weight:500;color:#cfcfd4;margin-top:28px">[Subtitle or client · date]</div></div>
  <div style="font-size:20px;font-weight:700;letter-spacing:4px;color:{ACC}">CULTURESHYFT MEDIA · {SITE}</div>
</div>''', "", "png", px=(1920, 1080))

# ---------- social kit ----------
render("social-instagram-post", f'''<div style="width:1080px;height:1080px;background:{ACC};padding:80px;display:flex;flex-direction:column;justify-content:space-between;color:{PAPER}">
  <div style="font-size:24px;font-weight:700;letter-spacing:4px">{HANDLE.upper()}</div>
  <div style="font-size:104px;font-weight:800;line-height:1;letter-spacing:-2px">Shyft<br>the room.</div>
  <div style="background:{INK};border-radius:20px;padding:28px 36px;display:flex;align-items:center;justify-content:space-between"><img src="{LOGO('cultureshyft-horizontal-color-ondark')}" style="width:420px"><span style="font-size:22px;font-weight:700">{SITE}</span></div>
</div>''', "", "png", px=(1080, 1080))
render("social-instagram-story", f'''<div style="width:1080px;height:1920px;background:{INK};padding:120px 90px;display:flex;flex-direction:column;justify-content:space-between;color:{PAPER}">
  <img src="{LOGO('cultureshyft-stacked-color-ondark')}" style="width:420px;align-self:center">
  <div style="font-size:120px;font-weight:800;line-height:1;letter-spacing:-3px">Made to<br>move<br><span style="color:{ACC}">people.</span></div>
  <div style="font-size:30px;font-weight:700;letter-spacing:5px;color:{ACC}">{HANDLE.upper()}</div>
</div>''', "", "png", px=(1080, 1920))
for name, w, h, safe in (("social-facebook-cover", 1640, 624, 0), ("social-linkedin-banner", 1584, 396, 0), ("social-x-header", 1500, 500, 0), ("social-youtube-banner", 2560, 1440, 1)):
    inner = f'''<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center"><div style="display:flex;align-items:center;gap:{int(h*0.1)}px">
      <img src="{LOGO('cultureshyft-horizontal-color-ondark')}" style="width:{int(min(w*0.34, h*1.6))}px">
      <div style="border-left:3px solid {ACC};padding-left:{int(h*0.06)}px;color:#cfcfd4;font-size:{int(h*0.07)}px;font-weight:500;line-height:1.4">Flyers · Social · Campaigns<br><span style="color:{PAPER};font-weight:700">{SITE}</span></div></div></div>'''
    render(name, f'<div style="width:{w}px;height:{h}px;background:{INK};position:relative">{inner}</div>', "", "png", px=(w, h))

# ---------- email signature (HTML to paste) ----------
sig = f'''<table cellpadding="0" cellspacing="0" style="font-family:Manrope,'Segoe UI',Arial,sans-serif;color:{INK};font-size:14px;line-height:1.4">
<tr><td style="padding-right:16px;vertical-align:top"><img src="https://{SITE}/logo/icons/icon-light-128.png" width="64" height="64" alt="CultureShyft Media" style="display:block;border-radius:12px"></td>
<td style="vertical-align:top;border-left:3px solid {ACC};padding-left:16px">
<div style="font-weight:800;font-size:16px">{NAME}</div>
<div style="font-weight:700;font-size:11px;letter-spacing:1px;color:{ACC};text-transform:uppercase">{TITLE}</div>
<div style="color:{SLATE};margin-top:6px">CultureShyft Media · {PHONE}</div>
<div><a href="https://{SITE}" style="color:{INK};font-weight:700;text-decoration:none">{SITE}</a> · <a href="https://instagram.com/cultureshyftmedia" style="color:{SLATE};text-decoration:none">{HANDLE}</a></div>
</td></tr></table>'''
io.open(os.path.join(R, "templates", "email-signature.html"), "w", encoding="utf-8").write(sig)
print("email signature written")
