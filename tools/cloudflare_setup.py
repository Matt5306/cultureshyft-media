"""One-time Cloudflare setup for cultureshyftmedia.com. Reads credentials from ../.cloudflare.env (git-ignored).

Does three things, each idempotent (safe to rerun):
  1. DNS for the GitHub Pages site: 4 A records on the apex + CNAME www -> matt5306.github.io (DNS only, not proxied,
     so GitHub can issue the HTTPS certificate).
  2. Email Routing: enable it (Cloudflare adds the MX/TXT records), add the destination address, and forward
     mark@ and hello@ (and a catch-all) to the destination.
  3. Prints what it did and what still needs a human (destination-address verification email, GitHub custom domain).
Run:  python tools/cloudflare_setup.py            (dry run: shows the plan)
      python tools/cloudflare_setup.py --apply    (makes the changes)
"""
import os, sys, json, io, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ZONE_NAME = "cultureshyftmedia.com"
PAGES_HOST = "matt5306.github.io"
PAGES_IPS = ["185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"]
DESTINATION = "cutureshyftmedia@gmail.com"      # Mark's Gmail (spelling as given)
FORWARD_NAMES = ["mark", "hello"]
APPLY = "--apply" in sys.argv

def load_env():
    env = {}
    p = os.path.join(ROOT, ".cloudflare.env")
    if not os.path.exists(p):
        sys.exit("missing .cloudflare.env")
    for line in io.open(p, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); env[k.strip()] = v.strip()
    return env

ENV = load_env()
def headers():
    tok = ENV.get("CF_API_TOKEN", "")
    if tok and not tok.startswith("paste-"):
        return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    if ENV.get("CF_GLOBAL_KEY") and ENV.get("CF_EMAIL"):
        return {"X-Auth-Key": ENV["CF_GLOBAL_KEY"], "X-Auth-Email": ENV["CF_EMAIL"], "Content-Type": "application/json"}
    sys.exit("no usable credential in .cloudflare.env (paste the token after CF_API_TOKEN=)")

def api(method, path, body=None):
    req = urllib.request.Request("https://api.cloudflare.com/client/v4" + path, data=json.dumps(body).encode() if body is not None else None, headers=headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode())
        except Exception: return {"success": False, "errors": [{"message": f"HTTP {e.code}"}]}

def ok(resp, what):
    if not resp.get("success"):
        print(f"  FAILED {what}: {resp.get('errors')}")
        return False
    return True

def main():
    print("mode:", "APPLY" if APPLY else "DRY RUN (add --apply to make changes)")
    z = api("GET", f"/zones?name={ZONE_NAME}")
    if not ok(z, "zone lookup") or not z["result"]:
        sys.exit("zone not found or token lacks Zone:Read")
    zone = z["result"][0]; zid = zone["id"]; acct = zone["account"]["id"]
    print(f"zone {ZONE_NAME} id={zid} status={zone.get('status')}")

    # 1. DNS for GitHub Pages
    recs = api("GET", f"/zones/{zid}/dns_records?per_page=100")
    existing = recs.get("result", []) if recs.get("success") else []
    want = [("A", ZONE_NAME, ip) for ip in PAGES_IPS] + [("CNAME", f"www.{ZONE_NAME}", PAGES_HOST)]
    for rtype, name, content in want:
        have = [r for r in existing if r["type"] == rtype and r["name"] == name and r["content"] == content]
        if have:
            print(f"  DNS ok: {rtype} {name} -> {content}"); continue
        print(f"  DNS add: {rtype} {name} -> {content} (DNS only)")
        if APPLY:
            ok(api("POST", f"/zones/{zid}/dns_records", {"type": rtype, "name": name, "content": content, "ttl": 1, "proxied": False}), f"add {rtype} {name}")
    stray = [r for r in existing if r["type"] in ("A", "AAAA", "CNAME") and r["name"] in (ZONE_NAME, f"www.{ZONE_NAME}") and r["content"] not in PAGES_IPS + [PAGES_HOST]]
    for r in stray:
        print(f"  DNS NOTE: existing {r['type']} {r['name']} -> {r['content']} would conflict with Pages; left alone, remove by hand if it is not wanted")

    # 2. Email routing
    st = api("GET", f"/zones/{zid}/email/routing")
    enabled = st.get("result", {}).get("enabled") if st.get("success") else None
    print(f"  Email Routing enabled: {enabled}")
    if not enabled:
        print("  enable Email Routing (adds MX + SPF records)")
        if APPLY:
            ok(api("POST", f"/zones/{zid}/email/routing/dns"), "enable email routing")
    dests = api("GET", f"/accounts/{acct}/email/routing/addresses?per_page=50")
    dlist = dests.get("result", []) if dests.get("success") else []
    d = next((x for x in dlist if x["email"].lower() == DESTINATION.lower()), None)
    if d:
        print(f"  destination {DESTINATION}: {'verified' if d.get('verified') else 'NOT verified yet (check that inbox for the Cloudflare email)'}")
    else:
        print(f"  add destination {DESTINATION} (Cloudflare will send a verification email there)")
        if APPLY:
            ok(api("POST", f"/accounts/{acct}/email/routing/addresses", {"email": DESTINATION}), "add destination")
    rules = api("GET", f"/zones/{zid}/email/routing/rules?per_page=50")
    rlist = rules.get("result", []) if rules.get("success") else []
    for name in FORWARD_NAMES:
        addr = f"{name}@{ZONE_NAME}"
        if any(any(m.get("value") == addr for m in r.get("matchers", [])) for r in rlist):
            print(f"  rule ok: {addr} -> {DESTINATION}"); continue
        print(f"  rule add: {addr} -> {DESTINATION}")
        if APPLY:
            ok(api("POST", f"/zones/{zid}/email/routing/rules", {"name": f"forward {name}", "enabled": True,
                "matchers": [{"type": "literal", "field": "to", "value": addr}], "actions": [{"type": "forward", "value": [DESTINATION]}]}), f"rule {addr}")
    ca = api("GET", f"/zones/{zid}/email/routing/rules/catch_all")
    if ca.get("success") and ca["result"].get("enabled"):
        print("  catch-all ok")
    else:
        print(f"  catch-all: forward everything else -> {DESTINATION}")
        if APPLY:
            ok(api("PUT", f"/zones/{zid}/email/routing/rules/catch_all", {"name": "catch-all", "enabled": True, "matchers": [{"type": "all"}], "actions": [{"type": "forward", "value": [DESTINATION]}]}), "catch-all")

    print("\nStill needs a human:")
    print(f"  - Mark opens {DESTINATION} and clicks the Cloudflare verification email (forwarding stays off until then).")
    print("  - GitHub: repo Settings > Pages > Custom domain = cultureshyftmedia.com, then tick Enforce HTTPS once the check passes.")
    print(f"  - To SEND as mark@{ZONE_NAME} from Gmail: Gmail Settings > Accounts > 'Send mail as' > add mark@{ZONE_NAME}; use Gmail's SMTP (smtp.gmail.com, the Gmail address + an App Password). Cloudflare forwards inbound only.")

if __name__ == "__main__":
    main()
