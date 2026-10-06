#!/usr/bin/env python3
"""Build the static Content My Trip showcase site into dist/.

Reads data/*.json (snapshots exported from the local platform databases by
snapshot.sh), templates/legal/*.html (the same Jinja templates auth-service
serves at /auth/terms etc.) and assets/img/*, and writes the HTML pages in
dist/, then checks every internal link. GitHub Actions deploys dist/ to
Pages on each push to main. Run locally:  python3 build.py
"""
import json, pathlib, re, html
from datetime import datetime
from jinja2 import Environment, DictLoader

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"
CTX = dict(business_legal_name="Content My Trip LLP",
           business_address="56/2, Doddathogur, Electronics City, Bangalore South, Bengaluru 560100, Karnataka, India",
           support_email="contentmytrip@gmail.com", support_phone="")
MAIL = "mailto:contentmytrip@gmail.com"

def load(name):
    return json.loads((ROOT / "data" / f"{name}.json").read_text() or "[]") or []

destinations = [d for d in load("destinations") if d["slug"] != "other"]
videos = load("videos")
creators = load("creators")
uploaders = {u["id"]: u for u in load("uploaders")}
edits = {e["creator_id"]: e["edits"] for e in load("edits")}
dest_by_id = {d["id"]: d for d in destinations}

def usable_thumb(path):
    """Auto-generated thumbnails are sometimes a near-black frame; treat those
    as missing so the card falls back to the destination image."""
    try:
        from PIL import Image, ImageStat
        p = pathlib.Path(path); f = ROOT / "assets" / "img" / "video_thumbnails" / (p.stem + ".jpg")
        st = ImageStat.Stat(Image.open(f).convert("L")) if f.exists() else None
        return bool(st) and (st.median[0] >= 40 or st.mean[0] >= 60)
    except Exception:
        return True

def img(path, kind=None):
    """Map a platform upload path to the optimised copy under assets/img."""
    if not path: return ""
    p = pathlib.Path(path); kind = kind or p.parent.name
    out = ROOT / "assets" / "img" / kind / (p.stem + ".jpg")
    return f"/assets/img/{kind}/{p.stem}.jpg" if out.exists() else ""

def dest_image(d):
    return img(d.get("main_image")) or img(d.get("banner_image"))

def esc(s): return html.escape(s or "")

def _items(value):
    """Destination fields are free text in some rows and JSON lists (of strings
    or {name/title, description} objects) in others; normalise to strings."""
    if not value: return []
    if isinstance(value, dict): value = [value]
    if isinstance(value, list):
        out = []
        for it in value:
            if isinstance(it, dict):
                name = it.get("name") or it.get("title") or ""
                desc = it.get("description") or it.get("detail") or ""
                out.append(f"{name}: {desc}" if name and desc else name or desc)
            elif it: out.append(str(it))
        return [o for o in out if o]
    return [t.strip(" -•\t") for t in re.split(r"[\n;]|(?<=\.)\s+(?=[A-Z])", str(value)) if t.strip(" -•\t")]

def paras(text):
    if isinstance(text, (list, dict)): return bullets(text)
    return "".join(f"<p>{esc(t.strip())}</p>" for t in re.split(r"\n\s*\n|\r\n\r\n", text or "") if t.strip())

def bullets(value):
    items = _items(value)
    return "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items[:10]) + "</ul>" if items else ""

def rich(value):
    if isinstance(value, (list, dict)): return bullets(value)
    v = str(value or "")
    return bullets(v) if (";" in v or "\n" in v) else paras(v)

NAV_LINKS = '<a href="/destinations/">Destinations</a><a href="/videos/">Videos</a><a href="/kreators/">Kreators</a><a href="/guides/">Guides</a><a href="/#pricing">Pricing</a><a class="pill" href="/signin/">Early access</a>'
NAV = ('<a class="skip-link" href="#main">Skip to content</a><header class="site-head"><div class="wrap"><a class="brand" href="/"><img src="/assets/wordmark.png" alt="Content My Trip"></a>'
       '<nav class="desktop-nav" aria-label="Main navigation">' + NAV_LINKS + '</nav><details class="mobile-nav"><summary>Menu</summary><nav aria-label="Mobile navigation">' + NAV_LINKS + '</nav></details></div></header>')
FOOT = ('<footer class="site-foot"><div class="wrap"><div class="footer-grid"><div><p class="kicker">Content-led travel brand</p><h2>Content My Trip</h2><p>Real travel moments. Stories worth sharing. Discover destinations and the kreators who bring them to life.</p></div>'
        '<div><h3>Explore</h3><a href="/destinations/">Destinations</a><a href="/videos/">Videos</a><a href="/kreators/">Kreators</a><a href="/guides/">AI Tour Guide</a></div>'
        '<div><h3>Get in touch</h3><a href="/signin/">Early access</a><a href="/contact/">Contact us</a><a href="' + MAIL + '">contentmytrip@gmail.com</a><a href="/terms/">Terms and Conditions</a><a href="/privacy/">Privacy Policy</a><a href="/refunds/">Refunds &amp; Cancellation</a></div></div>'
        '<div class="footer-bottom"><p><strong>Content My Trip LLP</strong> · LLPIN ADC-1855 · 56/2, Doddathogur, Electronics City, Bengaluru 560100, Karnataka, India</p><p>© 2026 Content My Trip LLP. All rights reserved.</p></div></div></footer>')
CSS = (ROOT / "templates" / "site.css").read_text()
BASE = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>{% block title %}Content My Trip{% endblock %}</title><meta name="description" content="{% block desc %}Content My Trip turns your travel footage into finished destination videos.{% endblock %}">'
        '<link rel="icon" href="/assets/favicon.png"><style>' + CSS + '</style></head><body>' + NAV + '<main id="main">{% block content %}{% endblock %}</main>' + FOOT + '</body></html>')
tpls = {"base.html": BASE}
for f in (ROOT / "templates" / "legal").glob("*.html"):
    tpls[f"auth/{f.name}"] = f.read_text()
env = Environment(loader=DictLoader(tpls), autoescape=False)
LINKS = {"/auth/terms": "/terms/", "/auth/privacy": "/privacy/", "/auth/refunds": "/refunds/", "/auth/contact": "/contact/",
         "/support": MAIL, "/videos/privacy": "/contact/", "/auth/login": "/signin/", "/live/community-standards": "/terms/"}
def fix(h):
    for a, b in LINKS.items(): h = h.replace(f'href="{a}"', f'href="{b}"')
    return h
def write(rel, h):
    out = DIST / rel; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(h)
def page(title, desc, body):
    return env.from_string('{% extends "base.html" %}{% block title %}' + title + '{% endblock %}{% block desc %}' + desc + '{% endblock %}{% block content %}' + body + '{% endblock %}').render(**CTX)

# ---------- legal ----------
for name in ("terms", "privacy", "refunds", "contact"):
    write(f"{name}/index.html", fix(env.get_template(f"auth/{name}.html").render(**CTX)))

# ---------- cards ----------
def video_card(v):
    d = dest_by_id.get((v.get("destination_ids") or [None])[0])
    thumb = (img(v.get("thumbnail_path")) if v.get("thumbnail_path") and usable_thumb(v["thumbnail_path"]) else "") or (dest_image(d) if d else "")
    who = uploaders.get(v["uploader_id"], {}).get("name") or "Content My Trip"
    date = (v.get("published_at") or "")[:10]
    links = [(v.get("youtube_url"), "YouTube"), (v.get("instagram_url"), "Instagram"), (v.get("facebook_url"), "Facebook"), (v.get("tiktok_url"), "TikTok")]
    btns = "".join(f'<a class="btn" href="{esc(u)}" target="_blank" rel="noopener">{n}</a>' for u, n in links if u)
    primary = next((u for u, _ in links if u), None)
    media = f'<img src="{thumb}" alt="{esc(v["title"])}" loading="lazy">' if thumb else '<div class="ph"></div>'
    if primary: media = f'<a aria-label="Watch {esc(v["title"])}" href="{esc(primary)}" target="_blank" rel="noopener">{media}</a>'
    where = f'<a href="/destinations/{d["slug"]}/">{esc(d["name"])}</a>' if d else "Content My Trip"
    return (f'<article class="vcard"><div class="thumb{" land" if not v.get("is_portrait") else ""}">{media}</div>'
            f'<div class="vbody"><h3>{esc(v["title"])}</h3><p class="muted">{where} · {esc(who)}{" · " + date if date else ""}</p>'
            f'<div class="btns">{btns or "<span class=muted>Published on Content My Trip</span>"}</div></div></article>')

def dest_card(d):
    im = dest_image(d); n = sum(1 for v in videos if d["id"] in (v.get("destination_ids") or []))
    return (f'<a class="dcard" href="/destinations/{d["slug"]}/">{f"<img src={chr(34)}{im}{chr(34)} alt={chr(34)}{esc(d[chr(110)+chr(97)+chr(109)+chr(101)])}{chr(34)} loading=lazy>" if im else "<div class=ph></div>"}'
            f'<div class="dbody"><h3>{esc(d["name"])}</h3><p class="muted">{esc(d.get("region") or "")}{", " if d.get("region") and d.get("country") else ""}{esc(d.get("country") or "")}</p>'
            f'<p>{esc(d.get("tagline") or "")}</p>{f"<p class=muted>{n} video{chr(115) if n != 1 else chr(0)}</p>".replace(chr(0), "") if n else ""}</div></a>')

def kreator_card(c):
    photo = img(c.get("profile_photo")); home = dest_by_id.get(c.get("home_destination_id"))
    initials = "".join(w[0] for w in (c.get("name") or c["username"]).split()[:2]).upper()
    avatar = f'<img src="{photo}" alt="{esc(c["name"])}" loading="lazy">' if photo else f'<div class="avatar-ph">{esc(initials)}</div>'
    n = edits.get(c["id"], 0)
    meta = " · ".join(x for x in [f'Based in <a href="/destinations/{home["slug"]}/">{esc(home["name"])}</a>' if home and home["slug"] != "other" else "", f"{n} edit{'s' if n != 1 else ''} delivered" if n else ""] if x)
    badge = '<span class="badge">Featured</span>' if c.get("is_featured") else ""
    return (f'<article class="kcard"><div class="avatar">{avatar}</div><div><h3>{esc(c["name"] or c["username"])} {badge}</h3>'
            f'<p class="muted">@{esc(c["username"])}{" · " + meta if meta else ""}</p><p>{esc(c.get("bio") or "")}</p></div></article>')

# ---------- pages ----------
write("destinations/index.html", page("Destinations — Content My Trip", "The destinations Content My Trip covers, with videos from travellers and Kreators.",
    '<section class="hero small"><div class="wrap"><h1>Destinations</h1><p>Every place we cover has its own page: when to go, what it is known for, and the videos our travellers and Kreators have made there.</p></div></section>'
    '<section><div class="wrap"><div class="grid dgrid">' + "".join(dest_card(d) for d in destinations) + '</div></div></section>'))
for d in destinations:
    im = dest_image(d); vids = [v for v in videos if d["id"] in (v.get("destination_ids") or [])]
    facts = [("Best time to visit", d.get("best_time_to_visit")), ("Ideal duration", d.get("ideal_duration")), ("Nearest airport", d.get("nearest_airport")), ("Budget", d.get("budget_range")), ("Type", d.get("destination_type"))]
    facts_html = "".join(f'<div class="fact"><span>{k}</span><strong>{esc(v)}</strong></div>' for k, v in facts if v)
    sections = ""
    for k, v in (("Known for", d.get("known_for")), ("Highlights", d.get("highlights")), ("Experiences", d.get("experiences")), ("Attractions", d.get("attractions")), ("Local food", d.get("local_food"))):
        if v: sections += f"<h2>{k}</h2>" + rich(v)
    body = (f'<section class="hero small" style="{f"background-image:linear-gradient(rgba(0,0,0,.45),rgba(0,0,0,.55)),url({im});background-size:cover;background-position:center;color:#fff" if im else ""}"><div class="wrap"><p class="kicker">{esc(d.get("region") or "")}{", " if d.get("region") and d.get("country") else ""}{esc(d.get("country") or "")}</p><h1>{esc(d["name"])}</h1><p>{esc(d.get("tagline") or "")}</p></div></section>'
            f'<section><div class="wrap"><div class="facts">{facts_html}</div>{paras(d.get("description"))}{sections}</div></section>'
            + (f'<section style="background:#fafafa"><div class="wrap"><h2>Videos from {esc(d["name"])}</h2><div class="grid vgrid">' + "".join(video_card(v) for v in vids) + '</div></div></section>' if vids else '')
            + '<section><div class="wrap"><p><a class="cta" href="/destinations/">All destinations</a></p></div></section>')
    write(f"destinations/{d['slug']}/index.html", page(f"{d['name']} — Content My Trip", (d.get("tagline") or d["name"])[:160], body))

write("videos/index.html", page("Videos — Content My Trip", "Published destination videos made on Content My Trip.",
    '<section class="hero small"><div class="wrap"><h1>Videos</h1><p>Finished videos made from travellers\' footage on Content My Trip, published on our channels. Tap a card to watch it where it was published.</p></div></section>'
    '<section><div class="wrap"><div class="grid vgrid">' + "".join(video_card(v) for v in videos) + '</div></div></section>'))

write("kreators/index.html", page("Kreators — Content My Trip", "The approved Kreators who edit travel footage on Content My Trip.",
    '<section class="hero small"><div class="wrap"><h1>Kreators</h1><p>Our approved editors. Pick a Professional Creator plan and one of them turns your footage into a finished video; a Kreator based at your destination is offered first.</p></div></section>'
    '<section><div class="wrap"><div class="grid kgrid">' + "".join(kreator_card(c) for c in creators) + '</div></div></section>'
    '<section style="background:#fafafa"><div class="wrap"><h2>Want to edit on Content My Trip?</h2><p>Kreators are onboarded by invitation. Write to <a href="' + MAIL + '">contentmytrip@gmail.com</a> with a link to your work.</p></div></section>'))

write("guides/index.html", page("AI Tour Guide — Content My Trip", "A free AI guide for the destinations Content My Trip covers.",
    '<section class="hero small"><div class="wrap"><h1>AI Tour Guide</h1><p>A free, chat-style guide for every destination we cover: what to see, when to go, how to get around, what to eat. It runs inside the Content My Trip platform and apps.</p></div></section>'
    '<section><div class="wrap"><h2>Destinations the guide covers</h2><div class="grid dgrid">' + "".join(dest_card(d) for d in destinations) + '</div>'
    '<p class="note" style="margin-top:22px">The guide is live on the platform and will ship in the Content My Trip app. This site is the public company page; the interactive guide needs an account.</p></div></section>'))

write("signin/index.html", page("Sign in — Content My Trip", "How to use Content My Trip.",
    '<section class="hero small"><div class="wrap"><h1>Sign in</h1><p>This page is the public company site. Accounts, uploads, editing and payments live on the Content My Trip platform and apps.</p></div></section>'
    '<section><div class="wrap"><div class="grid"><div class="card"><h3>Mobile apps</h3><p>The Content My Trip customer app and the Kreator app for editors are in testing with a closed group and will be listed on the App Store and Google Play.</p></div>'
    '<div class="card"><h3>Web platform</h3><p>The full web platform, with sign-in, uploads, Auto-Edit, Kreator plans and CMT Live, launches with our cloud deployment.</p></div>'
    '<div class="card"><h3>Early access</h3><p>Write to <a href="' + MAIL + '">contentmytrip@gmail.com</a> and we will add you to the testing group.</p></div></div></div></section>'))

# ---------- home ----------
featured_v = [v for v in videos if any(v.get(k) for k in ("youtube_url", "instagram_url", "facebook_url", "tiktok_url"))][:6]
platforms = [("YouTube", "youtube_url"), ("Instagram", "instagram_url"), ("Facebook", "facebook_url"), ("TikTok", "tiktok_url")]
reach = "".join(f'<div class="reach-row"><span>{name}</span><strong>{sum(bool(v.get(key)) for v in videos)}</strong></div>' for name, key in platforms)
write("index.html", page("Content My Trip — travel videos, edited and published", "Content My Trip turns your travel footage into finished destination videos: free Auto-Edit or a professional Kreator, then publishing.",
    '<section class="hero"><div class="wrap hero-layout"><div><span class="eyebrow">Travel content platform</span><h1>Upload. Edit.<br><span class="accent">Go Viral.</span></h1>'
    '<p>Your travels deserve more than a camera roll. Explore films made from real traveller footage, shaped by kreators, and shared with the world.</p>'
    '<a class="cta" href="/videos/">Browse gallery →</a> <a class="cta ghost" href="/signin/">Get early access</a>'
    f'<div class="hero-stats"><div><strong>{len(videos)}</strong><span>Videos live</span></div><div><strong>{len(destinations)}</strong><span>Destinations</span></div><div><strong>4</strong><span>Platforms</span></div></div></div>'
    '<aside class="reach" aria-label="Published video counts"><p class="reach-label">Platform reach · published videos</p>' + reach + f'<div class="reach-total"><span class="reach-label">Total stories live</span><strong>{len(videos)}</strong></div></aside></div></section>'
    '<section style="background:#fafafa"><div class="wrap"><p class="kicker">Fresh from the road</p><h2>Travel stories that feel like being there.</h2><p class="muted">Made from real traveller footage, shaped by talented kreators, and ready to inspire your next escape.</p><div class="grid vgrid">' + "".join(video_card(v) for v in featured_v) + '</div><p style="margin-top:18px"><a class="cta ghost" href="/videos/">All videos</a></p></div></section>'
    '<section id="how"><div class="wrap"><p class="kicker">Simple by design</p><h2>Your footage. Our craft. One unforgettable story.</h2><p class="muted">The full platform brings your travel moments together in three steps.</p><div class="grid">'
    '<div class="card"><h3>1. Upload</h3><p>Send us the raw clips from your trip through the full platform or the Content My Trip app, and tell us the destination and the story you want.</p></div>'
    '<div class="card"><h3>2. Edit</h3><p>Run a free Auto-Edit yourself, with music, filters, transitions and your own voice-over, or pick a Professional Creator plan and a human Kreator edits it for you.</p></div>'
    '<div class="card"><h3>3. Publish</h3><p>Download the finished video, or let us publish it on the Content My Trip channels and your connected social accounts.</p></div></div></div></section>'
    '<section id="pricing"><div class="wrap"><h2>Pricing</h2><p class="muted">Platform plans in Indian rupees, tax inclusive. Uploads, editing and payments become available with the full platform launch.</p><div class="grid">'
    '<div class="card"><h3>Auto-Edit</h3><div class="price">Free</div><p>Three attempts per video. Extra attempts: a pack of three credits for ₹69 per video.</p></div>'
    '<div class="card"><h3>Professional Creator · Basic</h3><div class="price">₹49</div><p>Per video. A Kreator edits your footage. Pay at upload or pay later, before work starts.</p></div>'
    '<div class="card"><h3>Professional Creator · Advanced</h3><div class="price">₹99</div><p>Per video. Larger uploads and the full Kreator Studio treatment.</p></div>'
    '<div class="card"><h3>CMT Membership</h3><div class="price">₹499 / month</div><p>or ₹4,999 / year. 10% off every paid plan. Cancel any time with a pro-rata refund for unused days.</p></div>'
    '</div><p class="note" style="margin-top:22px">Refunds are reviewed by our team and returned to the original payment method. See the <a href="/refunds/">Refunds and Cancellation Policy</a>.</p></div></section>'
    '<section style="background:#fafafa"><div class="wrap"><p class="kicker">Find your next feeling</p><h2>Go somewhere worth remembering.</h2><p class="muted">Explore places through local insight and real travel stories.</p><div class="grid dgrid">' + "".join(dest_card(d) for d in destinations[:6]) + '</div><p style="margin-top:18px"><a class="cta ghost" href="/destinations/">All destinations</a></p></div></section>'
    '<section><div class="wrap"><p class="kicker">People behind the stories</p><h2>Meet the kreators shaping every adventure.</h2><div class="grid kgrid">' + ''.join(kreator_card(c) for c in creators[:3]) + '</div><a class="cta ghost" href="/kreators/">Meet the community →</a></div></section>'
    '<section><div class="wrap"><h2>Also on Content My Trip</h2><div class="grid">'
    '<div class="card"><h3>Kreators</h3><p>Approved editors, offered destination-first. <a href="/kreators/">Meet them</a>.</p></div>'
    '<div class="card"><h3>CMT Live</h3><p>Free live destination discussions hosted by approved Kreators, with audience chat and hand-raise. Live sessions are never recorded.</p></div>'
    '<div class="card"><h3>AI Tour Guide</h3><p>A free chat guide for the destinations we cover. <a href="/guides/">About the guide</a>.</p></div></div></div></section>'
    '<section class="hero"><div class="wrap"><p class="kicker">Start your story</p><h2>Don’t let your best travel moments stay in your camera roll.</h2><p>Get in touch for early access to the Content My Trip platform and apps.</p><a class="cta" href="/signin/">Explore early access →</a> <a class="cta ghost" href="/contact/">Contact us</a></div></section>'
    '<section style="background:#fafafa"><div class="wrap"><h2>About the company</h2><p><strong>Content My Trip LLP</strong> is a limited liability partnership registered in India (LLPIN ADC-1855, incorporated 14 September 2026), with its registered office at 56/2, Doddathogur, Electronics City, Bangalore South, Bengaluru 560100, Karnataka. Reach us at <a href="' + MAIL + '">contentmytrip@gmail.com</a> or via the <a href="/contact/">contact page</a>.</p></div></section>'))

write("404.html", page("Page not found — Content My Trip", "", '<section><div class="wrap"><h2>Page not found</h2><p>Try the <a href="/">home page</a>.</p></div></section>'))
import shutil
if (DIST / "assets").exists(): shutil.rmtree(DIST / "assets")
shutil.copytree(ROOT / "assets", DIST / "assets", ignore=shutil.ignore_patterns(".DS_Store"))
(DIST / "CNAME").write_text("www.contentmytrip.com\n"); (DIST / ".nojekyll").write_text("")

# ---------- link check: every internal href/src must exist in dist ----------
broken = []
for f in DIST.rglob("*.html"):
    for m in re.finditer(r'(?:href|src)="(/[^"#?]*)', f.read_text()):
        target = DIST / m.group(1).lstrip("/")
        if not (target.exists() or (target / "index.html").exists()):
            broken.append((str(f.relative_to(DIST)), m.group(1)))
if broken:
    for page, link in broken: print(f"BROKEN {page} -> {link}")
    raise SystemExit(f"{len(broken)} broken internal link(s)")
print(f"built {datetime.now():%Y-%m-%d %H:%M}: {len(destinations)} destinations, {len(videos)} videos, {len(creators)} kreators")
