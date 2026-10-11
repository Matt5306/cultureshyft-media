"""Extra brand assets: more social layouts, highlight covers, postcard, sticker, invoice/quote, Zoom background,
phone wallpaper, email header, Canva starter PNGs. Uses the same render helper as build_templates.py."""
import os, io, sys, subprocess, shutil
sys.path.insert(0, os.path.dirname(__file__))
from build_templates import render, LOGO, QR, ACC, INK, PAPER, SAND, SLATE, EMBER, NAME, TITLE, EMAIL, PHONE, SITE, HANDLE, R
TAG = "Media made to move people."
HEAD = f"file:///{R}/assets/mark-headshot-1600.jpg".replace("\\", "/")
for d in ("templates/social/highlights", "templates/canva", "templates/digital"): os.makedirs(os.path.join(R, d), exist_ok=True)

# ---- social post layouts (1080 x 1080) ----
render("social-post-announcement", f'''<div style="width:1080px;height:1080px;background:{INK};color:{PAPER};padding:80px;display:flex;flex-direction:column;justify-content:space-between">
  <div style="display:flex;justify-content:space-between;align-items:center"><img src="{LOGO('cultureshyft-mark-color-ondark')}" style="width:110px"><span style="font-size:22px;font-weight:700;letter-spacing:4px;color:{ACC}">ANNOUNCEMENT</span></div>
  <div><div style="font-size:30px;font-weight:700;letter-spacing:3px;color:{SLATE}">[DATE · PLACE]</div><div style="font-size:108px;font-weight:800;line-height:1;letter-spacing:-3px;margin-top:18px">[Big<br>headline<br>here]</div></div>
  <div style="display:flex;justify-content:space-between;align-items:center;border-top:2px solid #2a2c33;padding-top:28px"><span style="font-size:26px;font-weight:700">{SITE}</span><span style="background:{ACC};border-radius:14px;padding:14px 26px;font-size:24px;font-weight:800">[Call to action]</span></div>
</div>''', "", "png", px=(1080, 1080))
render("social-post-quote", f'''<div style="width:1080px;height:1080px;background:{SAND};color:{INK};padding:90px;display:flex;flex-direction:column;justify-content:space-between">
  <div style="font-size:160px;line-height:0.6;color:{ACC};font-weight:800">“</div>
  <div style="font-size:72px;font-weight:800;line-height:1.1;letter-spacing:-2px">[A short quote or a bold claim, two or three lines long.]</div>
  <div style="display:flex;justify-content:space-between;align-items:center"><span style="font-size:24px;font-weight:700;letter-spacing:3px;color:{SLATE}">{HANDLE.upper()}</span><img src="{LOGO('cultureshyft-horizontal-color-onlight')}" style="width:300px"></div>
</div>''', "", "png", px=(1080, 1080))
render("social-post-before-after", f'''<div style="width:1080px;height:1080px;background:{PAPER};color:{INK};display:grid;grid-template-rows:1fr auto">
  <div style="display:grid;grid-template-columns:1fr 1fr">
    <div style="background:#e9e7e1;display:grid;place-items:center;position:relative"><span style="position:absolute;top:28px;left:28px;font-size:22px;font-weight:700;letter-spacing:3px;color:{SLATE}">BEFORE</span><span style="color:#9a9ea8;font-size:28px;font-weight:700">[old flyer image]</span></div>
    <div style="background:{EMBER};display:grid;place-items:center;position:relative"><span style="position:absolute;top:28px;left:28px;font-size:22px;font-weight:700;letter-spacing:3px;color:{ACC}">AFTER</span><span style="color:{ACC};font-size:28px;font-weight:700">[new flyer image]</span></div>
  </div>
  <div style="padding:40px 60px;display:flex;justify-content:space-between;align-items:center;background:{INK};color:{PAPER}"><span style="font-size:40px;font-weight:800;letter-spacing:-1px">{TAG}</span><img src="{LOGO('cultureshyft-mark-color-ondark')}" style="width:90px"></div>
</div>''', "", "png", px=(1080, 1080))
render("social-story-offer", f'''<div style="width:1080px;height:1920px;background:{ACC};color:{PAPER};padding:120px 90px;display:flex;flex-direction:column;justify-content:space-between">
  <img src="{LOGO('cultureshyft-horizontal-mono-white')}" style="width:520px">
  <div><div style="font-size:34px;font-weight:700;letter-spacing:5px">[THIS WEEK ONLY]</div><div style="font-size:150px;font-weight:800;line-height:0.95;letter-spacing:-4px;margin-top:20px">Flyers<br>from<br>$20.</div></div>
  <div style="background:{INK};border-radius:24px;padding:36px 44px;font-size:34px;font-weight:800;text-align:center">DM {HANDLE} to start</div>
</div>''', "", "png", px=(1080, 1920))
render("social-story-headshot", f'''<div style="width:1080px;height:1920px;background:{INK};color:{PAPER};position:relative;overflow:hidden">
  <img src="{HEAD}" style="position:absolute;left:0;top:0;width:1080px;height:1080px;object-fit:cover;object-position:top">
  <div style="position:absolute;left:0;right:0;top:900px;height:200px;background:linear-gradient(to bottom, rgba(20,21,26,0), {INK})"></div>
  <div style="position:absolute;left:90px;right:90px;bottom:140px;display:flex;flex-direction:column;gap:26px">
    <div style="font-size:26px;font-weight:700;letter-spacing:5px;color:{ACC}">MEET MARK</div>
    <div style="font-size:92px;font-weight:800;line-height:1;letter-spacing:-3px">{TAG}</div>
    <img src="{LOGO('cultureshyft-horizontal-color-ondark')}" style="width:460px;margin-top:10px">
  </div>
</div>''', "", "png", px=(1080, 1920))
for name, w, h in (("social-facebook-post", 1200, 630), ("social-linkedin-post", 1200, 1200)):
    render(name, f'''<div style="width:{w}px;height:{h}px;background:{INK};color:{PAPER};padding:70px;display:flex;flex-direction:column;justify-content:space-between">
      <img src="{LOGO('cultureshyft-horizontal-color-ondark')}" style="width:{int(w*0.38)}px">
      <div style="font-size:{int(h*0.09)}px;font-weight:800;line-height:1;letter-spacing:-2px">[Headline for the post]</div>
      <div style="font-size:{int(h*0.03)}px;font-weight:700;color:{ACC};letter-spacing:4px">{SITE.upper()}</div></div>''', "", "png", px=(w, h))

# ---- Instagram highlight covers (1080 x 1080, mark centred on a tile) ----
labels = ["WORK", "FLYERS", "SOCIAL", "LOGOS", "PRICES"]
for i, lab in enumerate(labels):
    bg = ACC if i % 2 == 0 else INK
    render(f"social-highlight-{lab.lower()}", f'''<div style="width:1080px;height:1080px;background:{bg};color:{PAPER};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:40px">
      <img src="{LOGO('cultureshyft-mark-' + ('mono-white' if bg == ACC else 'color-ondark'))}" style="width:360px"><span style="font-size:72px;font-weight:800;letter-spacing:8px">{lab}</span></div>''', "", "png", px=(1080, 1080))

# ---- print extras ----
render("postcard-6x4-front", f'''<div style="width:6.25in;height:4.25in;background:{INK};color:{PAPER};position:relative;overflow:hidden">
  <div style="position:absolute;inset:0.125in;padding:0.35in;display:flex;flex-direction:column;justify-content:space-between">
    <img src="{LOGO('cultureshyft-horizontal-color-ondark')}" style="width:2.6in">
    <div style="font-size:34pt;font-weight:800;line-height:1;letter-spacing:-1pt">{TAG}</div>
    <div style="font-size:11pt;font-weight:700;color:{ACC};letter-spacing:2pt">FLYERS FROM $20 · {SITE.upper()}</div></div></div>''', "", "print", 6.25, 4.25)
render("postcard-6x4-back", f'''<div style="width:6.25in;height:4.25in;background:{PAPER};position:relative">
  <div style="position:absolute;inset:0.125in;padding:0.3in;display:grid;grid-template-columns:1fr 1fr;gap:0.3in">
    <div style="display:flex;flex-direction:column;gap:6pt;font-size:9.5pt;line-height:1.4;color:#3a3d44"><img src="{LOGO('cultureshyft-mark-color-onlight')}" style="width:0.7in"><b style="font-size:11pt;color:{INK}">{NAME}</b><span>{TITLE}</span><span>{PHONE} · {EMAIL}</span><span><b>{SITE}</b> · {HANDLE}</span><img src="{QR}" style="width:0.7in;margin-top:4pt"></div>
    <div style="border-left:1pt solid #dad8d0;padding-left:0.3in;display:flex;flex-direction:column;justify-content:flex-end;gap:14pt"><div style="height:1pt;background:#dad8d0"></div><div style="height:1pt;background:#dad8d0"></div><div style="height:1pt;background:#dad8d0"></div><div style="height:1pt;background:#dad8d0"></div></div></div></div>''', "", "print", 6.25, 4.25)
render("sticker-3in-circle", f'''<div style="width:3.25in;height:3.25in;display:grid;place-items:center"><div style="width:3.25in;height:3.25in;border-radius:50%;background:{ACC};display:grid;place-items:center"><img src="{LOGO('cultureshyft-mark-mono-white')}" style="width:1.9in"></div></div>''', "", "print", 3.25, 3.25)
render("invoice-template", f'''<div style="width:8.5in;height:11in;padding:0.7in 0.75in;display:flex;flex-direction:column;gap:0.3in;font-size:10pt">
  <div style="display:flex;justify-content:space-between;align-items:flex-start"><img src="{LOGO('cultureshyft-horizontal-color-onlight')}" style="width:2.3in"><div style="text-align:right"><div style="font-size:22pt;font-weight:800;letter-spacing:-0.5pt">INVOICE</div><div style="color:{SLATE}">No. [0001] · [DATE]</div><div style="color:{SLATE}">Due: [DATE + 14 days]</div></div></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3in"><div><div style="font-size:8pt;font-weight:700;letter-spacing:1.5pt;color:{SLATE}">FROM</div><div style="font-weight:800">{NAME} · CultureShyft Media</div><div style="color:#3a3d44">{EMAIL} · {PHONE}<br>{SITE}</div></div><div><div style="font-size:8pt;font-weight:700;letter-spacing:1.5pt;color:{SLATE}">BILL TO</div><div style="font-weight:800">[Client name]</div><div style="color:#3a3d44">[Client email]<br>[Client address or organisation]</div></div></div>
  <table style="width:100%;border-collapse:collapse;margin-top:0.1in"><tr style="background:{INK};color:{PAPER};font-size:8.5pt;letter-spacing:1pt"><th style="text-align:left;padding:8pt">ITEM</th><th style="text-align:left;padding:8pt">DETAILS</th><th style="text-align:right;padding:8pt">QTY</th><th style="text-align:right;padding:8pt">PRICE</th><th style="text-align:right;padding:8pt">TOTAL</th></tr>
  <tr style="border-bottom:1pt solid #dad8d0"><td style="padding:9pt 8pt;font-weight:700">[Digital flyer]</td><td style="padding:9pt 8pt;color:#3a3d44">[Letter + Instagram square, 1 round of edits]</td><td style="padding:9pt 8pt;text-align:right">1</td><td style="padding:9pt 8pt;text-align:right">$20</td><td style="padding:9pt 8pt;text-align:right">$20</td></tr>
  <tr style="border-bottom:1pt solid #dad8d0"><td style="padding:9pt 8pt;font-weight:700">[Item]</td><td style="padding:9pt 8pt;color:#3a3d44">[Details]</td><td style="padding:9pt 8pt;text-align:right">1</td><td style="padding:9pt 8pt;text-align:right">$0</td><td style="padding:9pt 8pt;text-align:right">$0</td></tr></table>
  <div style="display:flex;justify-content:flex-end"><div style="width:2.6in;display:grid;gap:5pt"><div style="display:flex;justify-content:space-between;color:#3a3d44"><span>Subtotal</span><span>$20</span></div><div style="display:flex;justify-content:space-between;color:#3a3d44"><span>Deposit paid (50%)</span><span>−$10</span></div><div style="display:flex;justify-content:space-between;font-size:14pt;font-weight:800;border-top:2pt solid {ACC};padding-top:6pt"><span>Balance due</span><span>$10</span></div></div></div>
  <div style="flex:1"></div>
  <div style="border-top:1pt solid #dad8d0;padding-top:0.15in;font-size:8.5pt;color:{SLATE};line-height:1.5"><b style="color:{INK}">How to pay:</b> [Zelle / Cash App / PayPal handle]. Files are delivered as PDF, PNG and SVG once the balance clears. 2 rounds of edits are included; further edits are billed at [$X]. Thank you for shyfting with us.</div></div>''', "", "print", 8.5, 11)

# ---- digital extras ----
render("digital-zoom-background", f'''<div style="width:1920px;height:1080px;background:{INK};position:relative;overflow:hidden"><div style="position:absolute;right:-200px;top:-200px;width:900px;height:900px;border-radius:50%;background:{ACC};opacity:0.12"></div><img src="{LOGO('cultureshyft-horizontal-color-ondark')}" style="position:absolute;left:80px;bottom:70px;width:520px"></div>''', "", "png", px=(1920, 1080))
render("digital-phone-wallpaper", f'''<div style="width:1170px;height:2532px;background:{INK};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:60px"><img src="{LOGO('cultureshyft-mark-color-ondark')}" style="width:420px"><div style="font-size:44px;font-weight:800;color:{PAPER};letter-spacing:-1px">{TAG}</div></div>''', "", "png", px=(1170, 2532))
render("digital-email-header", f'''<div style="width:1200px;height:300px;background:{INK};display:flex;align-items:center;justify-content:space-between;padding:0 70px"><img src="{LOGO('cultureshyft-horizontal-color-ondark')}" style="width:460px"><span style="font-size:28px;font-weight:700;color:{ACC};letter-spacing:4px">{SITE.upper()}</span></div>''', "", "png", px=(1200, 300))

# move digital renders into templates/digital
for n in ("digital-zoom-background", "digital-phone-wallpaper", "digital-email-header"):
    src = os.path.join(R, "templates", "web", n + ".png")
    if os.path.exists(src): shutil.move(src, os.path.join(R, "templates", "digital", n + ".png"))
for lab in labels:
    src = os.path.join(R, "templates", "social", f"social-highlight-{lab.lower()}.png")
    if os.path.exists(src): shutil.move(src, os.path.join(R, "templates", "social", "highlights", f"highlight-{lab.lower()}.png"))
# Canva starter: transparent PNGs of every lockup at 2000 px wide
from PIL import Image
for f in os.listdir(os.path.join(R, "logo", "png")):
    im = Image.open(os.path.join(R, "logo", "png", f)).convert("RGBA"); s = 2000 / im.width
    im.resize((2000, int(im.height * s)), Image.LANCZOS).save(os.path.join(R, "templates", "canva", f.replace(".png", "-2000px.png")), optimize=True)
print("extras done")
