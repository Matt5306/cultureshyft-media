"""Brand guidelines PDF (US letter, multi-page) + one-page cheat sheet. Rendered with Chrome headless from HTML.
Pricing/services pages are pulled from brand/pricing.md if it exists (Codex copy), otherwise a placeholder page."""
import os, io, re, subprocess, html
R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUT = os.path.join(R, "brand"); SRC = os.path.join(R, "templates", "src")
ACC, INK, PAPER, SAND, SLATE, EMBER = "#FF5A1F", "#14151A", "#FFFFFF", "#F4F3EF", "#6A6E78", "#FFE8DC"
L = lambda n: f"file:///{R}/logo/web/{n}.png".replace("\\", "/")
T = lambda n: f"file:///{R}/templates/{n}".replace("\\", "/")
HEAD = f"file:///{R}/assets/mark-headshot-1600.jpg".replace("\\", "/")
FONT = f'@font-face{{font-family:Manrope;src:url("file:///{R}/fonts/Manrope-Variable.ttf");font-weight:200 800}}'.replace("\\", "/")

CSS = f'''{FONT}
@page{{size:8.5in 11in;margin:0}} *{{box-sizing:border-box}} body{{margin:0;font-family:Manrope,sans-serif;color:{INK};-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.pg{{width:8.5in;height:11in;padding:0.75in;page-break-after:always;position:relative;display:flex;flex-direction:column;gap:0.25in;overflow:hidden}}
.pg:last-child{{page-break-after:auto}}
.dark{{background:{INK};color:{PAPER}}} .sand{{background:{SAND}}}
.eyebrow{{font-size:9pt;font-weight:700;letter-spacing:2.5pt;color:{ACC};text-transform:uppercase}}
h1{{font-size:40pt;font-weight:800;line-height:1;letter-spacing:-1pt;margin:0}} h2{{font-size:24pt;font-weight:800;letter-spacing:-0.5pt;margin:0}} h3{{font-size:12pt;font-weight:700;margin:0}}
p{{margin:0;font-size:10.5pt;line-height:1.5}} .muted{{color:{SLATE}}} .dark .muted{{color:#b8bcc6}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:0.2in}} .grid3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.2in}}
.tile{{border:1px solid #dad8d0;border-radius:10pt;padding:0.18in;display:grid;place-items:center;min-height:1.5in}} .tile.d{{background:{INK};border-color:transparent}}
.tile img{{max-width:100%;max-height:1.3in}} .cap{{font-size:8pt;font-weight:700;letter-spacing:1.5pt;color:{SLATE};text-transform:uppercase}}
.sw{{display:grid;grid-template-columns:repeat(3,1fr);gap:0.15in}} .sw div{{border-radius:10pt;padding:0.15in;min-height:1.1in;display:flex;flex-direction:column;justify-content:flex-end;font-size:9pt;border:1px solid #dad8d0}} .sw b{{font-size:11pt}}
ul{{margin:0;padding-left:0.2in;font-size:10.5pt;line-height:1.5}} .foot{{position:absolute;bottom:0.45in;left:0.75in;right:0.75in;display:flex;justify-content:space-between;font-size:8pt;font-weight:700;letter-spacing:1.5pt;color:{SLATE};text-transform:uppercase}}
.dark .foot{{color:#8a8e98}} table{{width:100%;border-collapse:collapse;font-size:9.5pt}} th{{text-align:left;font-size:8pt;letter-spacing:1.5pt;color:{SLATE};padding:6pt 4pt;border-bottom:2pt solid {ACC}}} td{{padding:7pt 4pt;border-bottom:1px solid #dad8d0;vertical-align:top}}
'''
def foot(n): return f'<div class="foot"><span>CultureShyft Media · Brand guidelines</span><span>{n}</span></div>'

def md_table_to_html(md):
    """Render a small subset of Markdown (headings, paragraphs, bullets, bold, tables) for the pricing page."""
    out, lines = [], md.splitlines(); i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:-]+\|", lines[i + 1]):
            hdr = [c.strip() for c in ln.strip("|").split("|")]; i += 2; rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")]); i += 1
            out.append("<table><tr>" + "".join(f"<th>{inl(h)}</th>" for h in hdr) + "</tr>" + "".join("<tr>" + "".join(f"<td>{inl(c)}</td>" for c in r) + "</tr>" for r in rows) + "</table>"); continue
        if ln.startswith("# "): out.append(f"<h2>{inl(ln[2:])}</h2>")
        elif ln.startswith("## "): out.append(f"<h3 style='margin-top:8pt'>{inl(ln[3:])}</h3>")
        elif ln.startswith("### "): out.append(f"<h3>{inl(ln[4:])}</h3>")
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "): items.append(f"<li>{inl(lines[i][2:])}</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>"); continue
        elif ln.strip(): out.append(f"<p>{inl(ln)}</p>")
        i += 1
    return "\n".join(out)
def inl(s):
    s = html.escape(s); s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s); s = re.sub(r"`(.+?)`", r"<code>\1</code>", s); return s

pricing_path = os.path.join(R, "brand", "pricing.md")
def compact_pricing():
    """Service / price / turnaround table from pricing.md headings (### N. Name — $X) and bold youth/website lines."""
    if not os.path.exists(pricing_path): return "<p class='muted'>See brand/pricing.md.</p>"
    md = io.open(pricing_path, encoding="utf-8").read()
    rows = []
    for m in re.finditer(r"^(?:### \d+\. |\*\*)([^—\n*]+?)\s*—\s*(\$[\d,]+(?:[–-]\$?[\d,]+)?(?:\s*/\s*\w+)?)", md, re.M):
        name, price = m.group(1).strip(), m.group(2).strip()
        tail = md[m.end(): m.end() + 900]
        turn = re.search(r"\*\*Turnaround:\*\*\s*([^\n]+)", tail); inc = re.search(r"\n- ([^\n]+)", tail)
        rows.append((name, price, (turn.group(1).strip() if turn else "").rstrip(".")[:60], (inc.group(1).strip() if inc else "")[:70]))
    html_rows = "".join(f"<tr><td><b>{inl(n)}</b></td><td>{inl(pr)}</td><td>{inl(tu)}</td><td class='muted'>{inl(ic)}</td></tr>" for n, pr, tu, ic in rows)
    return f"<table><tr><th>Service</th><th>Price</th><th>Turnaround</th><th>Starts with</th></tr>{html_rows}</table>"
pricing_html = ("<h2>Media made to move people.</h2><p class='muted'>Introductory prices, reviewed every 6 months. 50% deposit to book, balance on delivery; 2 rounds of edits included; files delivered as PDF, PNG and SVG. Full sheet with what's included and extras: <b>CultureShyft-Media-Pricing.pdf</b>.</p>" + compact_pricing())

pages = []
pages.append(f'''<div class="pg dark" style="justify-content:space-between"><img src="{L('cultureshyft-horizontal-color-ondark')}" style="width:3.6in">
<div><div class="eyebrow">Brand guidelines · 2026</div><h1 style="font-size:54pt;margin-top:0.15in">Media made<br>to move people.</h1></div>
<p class="muted">How to use the CultureShyft Media identity: logo, color, type, voice, templates. For printers, partners, and any AI you hand this to.</p></div>''')
pages.append(f'''<div class="pg"><div class="eyebrow">The idea</div><h2>Culture is the crowd. Shyft is the pattern changing. Media is the signal that carries it.</h2>
<p>CultureShyft Media makes digital marketing materials: flyers, social posts, campaign sets, logos, websites. The name is spelled with a Y on purpose, and the Y is the brand's mark: a bold letter whose arms hold two orange broadcast arcs, an antenna. Once people see it, they stop typing "shift".</p>
<div class="grid2" style="margin-top:0.2in"><div class="tile"><img src="{L('cultureshyft-mark-color-onlight')}" style="max-height:2.2in"></div><div style="display:flex;flex-direction:column;gap:0.12in;justify-content:center"><h3>Three things to remember</h3><ul><li>One word: <b>CultureShyft</b>. Capital C, capital S, a Y.</li><li>One accent color, used once per layout.</li><li>Short headlines, left-aligned, plenty of air.</li></ul></div></div>
<div class="grid2" style="margin-top:0.1in"><div><h3>Who it is for</h3><p class="muted">Small businesses, churches and youth programs, event hosts, creators: anyone with something to announce and no designer on staff.</p></div><div><h3>What a client gets</h3><p class="muted">Print-ready and phone-ready files, fast, that look like they belong to a brand people already trust.</p></div></div>{foot(2)}</div>''')
pages.append(f'''<div class="pg"><div class="eyebrow">Logo</div><h2>Four lockups, four colorways.</h2>
<div class="grid2"><div class="tile"><img src="{L('cultureshyft-horizontal-color-onlight')}"><span class="cap">Horizontal · color on light</span></div><div class="tile d"><img src="{L('cultureshyft-horizontal-color-ondark')}"><span class="cap">Horizontal · color on dark</span></div>
<div class="tile"><img src="{L('cultureshyft-stacked-color-onlight')}" style="max-height:1.5in"><span class="cap">Stacked</span></div><div class="tile"><img src="{L('cultureshyft-wordmark-color-onlight')}"><span class="cap">Wordmark</span></div>
<div class="tile"><img src="{L('cultureshyft-horizontal-mono-black')}"><span class="cap">Mono black</span></div><div class="tile d"><img src="{L('cultureshyft-horizontal-mono-white')}"><span class="cap">Mono white</span></div></div>
<p class="muted">Use the horizontal lockup by default. Stacked for square spaces. The mark alone under about 1 inch. Mono versions for one-color print, embroidery, engraving.</p>{foot(3)}</div>''')
pages.append(f'''<div class="pg"><div class="eyebrow">Logo rules</div><h2>Clear space, minimum size, and the don'ts.</h2>
<div class="grid2"><div class="tile" style="min-height:2.4in;position:relative"><div style="position:absolute;inset:0.35in;border:1px dashed {ACC};border-radius:6pt"></div><img src="{L('cultureshyft-horizontal-color-onlight')}" style="max-width:70%"><span class="cap" style="position:absolute;bottom:6pt">Clear space = height of the Y's stem, all sides</span></div>
<div style="display:flex;flex-direction:column;gap:0.1in"><h3>Minimum size</h3><ul><li>Horizontal: 1.2 in / 30 mm wide in print, 140 px on screen</li><li>Stacked: 0.8 in / 20 mm, 96 px</li><li>Mark alone: 0.25 in / 6 mm, 16 px</li></ul><h3>Backgrounds</h3><p class="muted">Light or dark, plain or quiet. On a busy photo, put the logo on an Ink or Paper block. Never on orange with the color lockup: use mono white there.</p></div></div>
<h3 style="margin-top:0.1in">Don't</h3><div class="grid3"><div class="tile" style="min-height:1.1in"><img src="{L('cultureshyft-horizontal-color-onlight')}" style="transform:scaleX(1.5);max-width:60%"><span class="cap">stretch it</span></div><div class="tile" style="min-height:1.1in;background:{ACC};border-color:transparent"><img src="{L('cultureshyft-horizontal-color-ondark')}" style="max-width:70%"><span class="cap" style="color:#fff">color lockup on orange</span></div><div class="tile" style="min-height:1.1in"><img src="{L('cultureshyft-horizontal-color-onlight')}" style="max-width:70%;filter:drop-shadow(3px 3px 3px rgba(0,0,0,.5))"><span class="cap">shadows or glows</span></div></div>
<ul style="margin-top:0.1in"><li>Don't retype the wordmark in Manrope; use the files.</li><li>Don't recolor the arcs or the Y.</li><li>Don't write "Culture Shift".</li></ul>{foot(4)}</div>''')
pages.append(f'''<div class="pg"><div class="eyebrow">Color</div><h2>Two colors do the work.</h2>
<div class="sw"><div style="background:{ACC};color:#fff;border-color:transparent"><b>Shyft Orange</b>#FF5A1F · 255 90 31<br>C0 M65 Y88 K0 · Pantone 1655 C</div><div style="background:{INK};color:#fff;border-color:transparent"><b>Ink</b>#14151A · 20 21 26<br>rich black C75 M68 Y60 K80</div><div style="background:{PAPER}"><b>Paper</b>#FFFFFF</div><div style="background:{SAND}"><b>Sand</b>#F4F3EF</div><div style="background:{SLATE};color:#fff;border-color:transparent"><b>Slate</b>#6A6E78</div><div style="background:{EMBER}"><b>Ember tint</b>#FFE8DC</div></div>
<div class="grid2" style="margin-top:0.15in"><div><h3>How much of each</h3><p class="muted">About 60% background (Paper or Ink), 30% text, 10% Shyft Orange. Orange is the thing you notice, so it appears once per layout and never behind small text.</p></div><div><h3>Readable pairs</h3><ul><li>Ink on Paper or Sand; Paper on Ink: always.</li><li>White on orange: 24 pt+ or bold 19 pt+ only.</li><li>Orange text on white: headlines only, never body.</li></ul></div></div>{foot(5)}</div>''')
pages.append(f'''<div class="pg"><div class="eyebrow">Type</div><h2>Manrope. One family, free, built into Canva.</h2>
<div style="font-size:48pt;font-weight:800;line-height:1;letter-spacing:-1.5pt">Shyft the room.</div><div style="font-size:24pt;font-weight:800;margin-top:0.1in">Headlines are short and left-aligned.</div>
<p style="max-width:5in;margin-top:0.1in">Body text stays around 65 characters a line, Medium weight, line-height 1.5. Numbers as numbers: 48 hours, 3 sizes. One size jump between levels is enough; if something needs to be louder, make it orange, not bigger.</p>
<div style="font-size:9pt;font-weight:700;letter-spacing:2pt;color:{SLATE};margin-top:0.1in">LABELS IN CAPS WITH LETTER-SPACING</div>
<table style="margin-top:0.2in"><tr><th>Role</th><th>Size</th><th>Weight</th><th>Notes</th></tr><tr><td>Display</td><td>64–96 px</td><td>ExtraBold 800</td><td>letter-spacing −2%, line-height 1.0</td></tr><tr><td>Headline</td><td>40–48 px</td><td>ExtraBold 800</td><td>letter-spacing −1%</td></tr><tr><td>Subhead</td><td>22–32 px</td><td>Bold 700</td><td></td></tr><tr><td>Body</td><td>17–18 px</td><td>Medium 500</td><td>line-height 1.5</td></tr><tr><td>Label</td><td>13–14 px</td><td>Bold 700</td><td>caps, +8% spacing</td></tr></table>
<p class="muted" style="margin-top:0.15in">Download: fonts.google.com/specimen/Manrope (SIL Open Font License). Never Light or Thin weights.</p>{foot(6)}</div>''')
pages.append(f'''<div class="pg sand"><div class="eyebrow">Voice</div><h2>Bold, warm, quick, clear.</h2>
<div class="grid2"><div><h3>Tagline</h3><p style="font-size:20pt;font-weight:800;letter-spacing:-0.5pt">Media made to move people.</p><h3 style="margin-top:0.2in">How we write</h3><ul><li>Short sentences. One idea each.</li><li>Lead with what the reader gets.</li><li>Numbers as numbers.</li><li>No exclamation marks in body text; the orange does the shouting.</li><li>We say "flyer", not "collateral". "You", not "clients".</li></ul></div>
<div><h3>Mark Andrew</h3><p class="muted">Cultural Media Artifact Engineer</p><img src="{HEAD}" style="width:2.2in;border-radius:10pt;margin:0.12in 0;display:block"><p class="muted">mark@cultureshyftmedia.com · 248-505-0050<br>cultureshyftmedia.com · @cultureshyftmedia</p></div></div>{foot(7)}</div>''')
pages.append(f'''<div class="pg"><div class="eyebrow">Templates</div><h2>Ready to use, in the kit.</h2>
<div class="grid3"><div class="tile d" style="padding:0"><img src="{T('social/social-post-announcement.png')}" style="max-height:2.1in;border-radius:10pt"></div><div class="tile" style="padding:0"><img src="{T('social/social-post-quote.png')}" style="max-height:2.1in;border-radius:10pt"></div><div class="tile" style="padding:0"><img src="{T('social/social-instagram-post.png')}" style="max-height:2.1in;border-radius:10pt"></div>
<div class="tile" style="padding:0"><img src="{T('web/business-card-back-preview.png')}" style="max-height:2.1in;border-radius:10pt"></div><div class="tile d" style="padding:0"><img src="{T('social/social-story-headshot.png')}" style="max-height:2.1in;border-radius:10pt"></div><div class="tile d" style="padding:0"><img src="{T('digital/digital-zoom-background.png')}" style="max-height:2.1in;border-radius:10pt"></div></div>
<p class="muted">Also in the kit: letterhead, invoice, flyer template, postcard, sticker, 5 highlight covers, covers for Facebook/LinkedIn/X/YouTube, phone wallpaper, email header and signature, Canva-ready PNGs. Everything regenerates from the scripts in <code>tools/</code>.</p>{foot(8)}</div>''')
pages.append(f'''<div class="pg"><div class="eyebrow">Services and pricing · draft</div>{pricing_html}{foot(9)}</div>''')
pages.append(f'''<div class="pg dark" style="justify-content:space-between"><div><div class="eyebrow">Where everything lives</div><h2>cultureshyftmedia.com</h2><p class="muted" style="margin-top:0.1in">The brand guide site. The full kit: github.com/Matt5306/cultureshyft-media. The AI handoff prompt: brand/brand-prompt.md.</p></div>
<img src="{L('cultureshyft-stacked-color-ondark')}" style="width:2.6in;align-self:center"><p class="muted" style="text-align:center">© CultureShyft Media · Mark Andrew · Fonts: Manrope, SIL Open Font License</p></div>''')

doc = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{"".join(pages)}</body></html>'
p = os.path.join(SRC, "brand-guidelines.html"); io.open(p, "w", encoding="utf-8").write(doc)
out = os.path.join(OUT, "CultureShyft-Media-Brand-Guidelines.pdf")
subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out}", "file:///" + p.replace("\\", "/")], capture_output=True)

# one-page cheat sheet
cheat = f'''<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="pg" style="gap:0.18in"><div style="display:flex;justify-content:space-between;align-items:center"><img src="{L('cultureshyft-horizontal-color-onlight')}" style="width:2.6in"><span class="eyebrow">Brand cheat sheet</span></div>
<div class="grid2"><div><h3>Name</h3><p><b>CultureShyft Media</b>, one word, capital C and S, with a Y. Handle @cultureshyftmedia. Site cultureshyftmedia.com.</p></div><div><h3>Tagline</h3><p style="font-size:16pt;font-weight:800">Media made to move people.</p></div></div>
<div class="sw"><div style="background:{ACC};color:#fff;border-color:transparent"><b>Shyft Orange</b>#FF5A1F</div><div style="background:{INK};color:#fff;border-color:transparent"><b>Ink</b>#14151A</div><div style="background:{SAND}"><b>Sand</b>#F4F3EF</div></div>
<div class="grid2"><div><h3>Type</h3><p>Manrope. 800 headlines, 700 labels, 500 body. Labels in caps with spacing. Never Light.</p></div><div><h3>Logo</h3><p>Horizontal by default, stacked for squares, mark alone under 1 in. Mono white on orange. Clear space = the Y's stem. Never stretch, recolor, shadow.</p></div></div>
<div class="grid2"><div><h3>Voice</h3><p>Bold, warm, quick, clear. Short sentences. Lead with what the reader gets. No exclamation marks in body copy.</p></div><div><h3>Contact block</h3><p>Mark Andrew · Cultural Media Artifact Engineer<br>mark@cultureshyftmedia.com · 248-505-0050</p></div></div>
<div class="tile d" style="min-height:1.6in"><img src="{L('cultureshyft-stacked-color-ondark')}" style="max-height:1.4in"></div><div class="foot"><span>CultureShyft Media · cheat sheet</span><span>github.com/Matt5306/cultureshyft-media</span></div></div></body></html>'''
p2 = os.path.join(SRC, "brand-cheat-sheet.html"); io.open(p2, "w", encoding="utf-8").write(cheat)
subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={os.path.join(OUT, 'CultureShyft-Media-Cheat-Sheet.pdf')}", "file:///" + p2.replace("\\", "/")], capture_output=True)
print("guidelines + cheat sheet rendered")

# standalone pricing + services PDFs from the markdown
for src_md, out_name, title in (("pricing.md", "CultureShyft-Media-Pricing.pdf", "Services and pricing"), ("services-onepager.md", "CultureShyft-Media-Services.pdf", "Services")):
    mp = os.path.join(R, "brand", src_md)
    if os.path.exists(mp):
        body = md_table_to_html(io.open(mp, encoding="utf-8").read())
        doc = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS} .pg{{height:auto;min-height:11in;page-break-after:auto}} h2{{font-size:18pt}} h3{{font-size:12pt}} p,li{{font-size:10pt}}</style></head><body><div class="pg" style="gap:0.12in"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.1in"><img src="{L("cultureshyft-horizontal-color-onlight")}" style="width:2.2in"><span class="eyebrow">{title} · draft</span></div>{body}</div></body></html>'
        hp = os.path.join(SRC, out_name.replace(".pdf", ".html")); io.open(hp, "w", encoding="utf-8").write(doc)
        subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={os.path.join(OUT, out_name)}", "file:///" + hp.replace("\\", "/")], capture_output=True)
        print("rendered", out_name)
