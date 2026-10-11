"""Add the services/pricing section, Mark's section, and PDF download links to docs/index.html (idempotent)."""
import io, os
R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
p = os.path.join(R, "docs", "index.html")
t = io.open(p, encoding="utf-8").read()
tile = 'class="tile" style="min-height: 0; place-items: start; gap: 4px"'
def card(name, price, note):
    return f'<div {tile}><b>{name}</b><span style="font-size: 28px; font-weight: 800">{price}</span><span class="muted" style="font-size: 14px">{note}</span></div>'
cards = "".join([
    card("Flyer", "$20", "Letter + Instagram square, 48 hours"),
    card("Continuous flyers", "$76 / mo", "4 per month; 8 for $144"),
    card("Logo", "$180", "2 concepts, all file types"),
    card("Brand story", "$120", "Story, mission, values, taglines"),
    card("Social media rebrand", "$180", "5 platforms, 6 templates, bios"),
    card("Full rebrand", "$450", "Logo + story + social + card + guide"),
    card("Youth program rebrand", "$400", "For churches, schools, youth programs"),
    card("Youth refresh", "$120", "A younger feel, same logo"),
    card("Website", "from $350", "1 page; 3–5 pages $650–950"),
])
services = f'''  <section id="services">
    <h2>Services and pricing</h2>
    <p class="muted">Introductory prices. 50% deposit to book, balance on delivery, 2 rounds of edits included, files as PDF, PNG and SVG.</p>
    <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr))">{cards}</div>
    <div class="row"><a class="btn" href="downloads/CultureShyft-Media-Pricing.pdf">Full price sheet (PDF)</a><a class="btn q" href="mailto:mark@cultureshyftmedia.com">Email Mark</a></div>
  </section>

  <section id="mark">
    <h2>Mark Andrew</h2>
    <div style="display: grid; grid-template-columns: 140px 1fr; gap: 20px; align-items: center">
      <img src="assets/mark.jpg" alt="Mark Andrew" style="width: 140px; height: 140px; object-fit: cover; object-position: top; border-radius: 16px">
      <div><p><b>Cultural Media Artifact Engineer.</b> Flyers, social posts, campaign sets, logos and websites for people with something to announce.</p><p class="muted" style="margin-top: 8px">mark@cultureshyftmedia.com · 248-505-0050 · @cultureshyftmedia</p></div>
    </div>
  </section>

'''
anchor = '  <section>\n    <h2>Templates and downloads</h2>'
if 'id="services"' not in t and anchor in t:
    t = t.replace(anchor, services + anchor)
dl = '<li><a href="downloads/CultureShyft-Media-Brand-Guidelines.pdf">Brand guidelines (PDF, 10 pages)</a> · <a href="downloads/CultureShyft-Media-Cheat-Sheet.pdf">one-page cheat sheet</a> · <a href="downloads/CultureShyft-Media-Services.pdf">services sheet</a></li>\n      '
first_li = '<li><a href="https://github.com/Matt5306/cultureshyft-media/tree/main/templates/print">'
if "Brand guidelines (PDF" not in t and first_li in t:
    t = t.replace(first_li, dl + first_li)
t = t.replace("Cultural Media Artifact Engineer. This page is also", "Cultural Media Artifact Engineer. Flyers from $20. This page is also")
t = t.replace("Cultural Media Artifact Engineer. This page is the brand guide", "Cultural Media Artifact Engineer. Flyers from $20. This page is also the brand guide")
io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("site patched:", 'id="services"' in t, "Brand guidelines (PDF" in t)
