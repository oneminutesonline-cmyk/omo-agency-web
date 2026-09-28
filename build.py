import json, re, base64, html, os, shutil, urllib.parse, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extra import X, LANGS, DOMAIN, EMAIL, PHONE, PHONE_TEL, WA, SLUGS
from legal import PAGES, UPD

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)
def b64(path): return base64.b64encode(open(P(path), 'rb').read()).decode()

T = json.load(open(P('src', 'i18n.json')))
BLOG = json.load(open(P('data', 'blog.json')))
LIPOSTS = json.load(open(P('data', 'linkedin.json')))
TPL = open(P('src', 'template.html')).read()
LOGO = b64('assets/logo160.png')
PORT = b64('assets/portrait.webp')
OUT = P('_site')
BLOG_MAX = 6
LI_MAX = 2
LI_UI = {
 "h3": {"it": "Da LinkedIn", "es": "Desde LinkedIn", "en": "From LinkedIn"},
 "cta": {"it": "Leggi il post su LinkedIn", "es": "Leer el post en LinkedIn", "en": "Read the post on LinkedIn"},
 "note": {"it": {"es": "Traduzione del post originale, pubblicato in spagnolo.", "en": "Traduzione del post originale, pubblicato in inglese."},
          "es": {"it": "Traducción del post original, publicado en italiano.", "en": "Traducción del post original, publicado en inglés."},
          "en": {"it": "Translated from the original post, written in Italian.", "es": "Translated from the original post, written in Spanish."}},
}
LNAME = {"it": "Italiano", "es": "Español", "en": "English"}

def plain(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s)).replace('\xa0', ' ').strip()

def nodot(s):
    # the design avoids middle-dot separators in visible labels
    return s.replace(' &middot; ', ', ').replace(' · ', ', ')

def posts_html(lang):
    months = X["months"][lang].split()
    out = []
    for p in sorted(BLOG, key=lambda p: p['date'], reverse=True)[:BLOG_MAX]:
        y, m, d = p['date'].split('-')
        title, body, label = p[lang]['title'], p[lang]['body'], p[lang]['sourceLabel']
        paras = ''.join('<p>%s</p>' % html.escape(x) for x in body.split('\n\n'))
        out.append('<article class="post"%s><div class="date">%d %s<span>%s</span></div><div><h3>%s</h3>%s<p class="srcl"><a href="%s" target="_blank" rel="noopener">%s: %s</a></p></div></article>' % (
            '', int(d), months[int(m)-1], y, html.escape(title), paras,
            html.escape(p['sourceUrl']), X['src'][lang], html.escape(label)))
    return ''.join(out)

def li_html(lang):
    posts = sorted(LIPOSTS, key=lambda p: p['date'], reverse=True)[:LI_MAX]
    if not posts: return ''
    cards = []
    for p in posts:
        L = p[lang]
        imgs = ''.join('<img src="data:image/webp;base64,%s" alt="%s" loading="lazy">' % (b64(src), html.escape(L['alts'][i] if i < len(L['alts']) else ''))
                       for i, src in enumerate(p['images'][:3]))
        paras = ''.join('<p>%s</p>' % html.escape(x) for x in L['text'])
        note = LI_UI['note'][lang].get(p.get('orig', 'it'), '') if p.get('orig', 'it') != lang else ''
        note = '<p class="li-note">%s</p>' % note if note else ''
        photos = '<div class="li-photos n%d">%s</div>' % (min(len(p['images']), 3), imgs) if p['images'] else ''
        cards.append('<article class="li-card%s">%s<div class="li-text"><p class="li-meta">Eleonora Saccucci, %s</p>%s%s'
                     '<a class="btn btn-ghost" href="%s" target="_blank" rel="noopener">%s</a></div></article>' % (
                     '' if p['images'] else ' noimg', photos, html.escape(L['meta']), paras, note, html.escape(p['url']), LI_UI['cta'][lang]))
    return '<div class="li"><h3>%s</h3>%s</div>' % (LI_UI['h3'][lang], ''.join(cards))

def jsonld(lang, url):
    svcs = [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": plain(T['svc%02d_title' % i][lang]),
             "description": plain(T['svc%02d_desc' % i][lang])}} for i in range(1, 7)]
    g = {"@context": "https://schema.org", "@graph": [
        {"@type": "ProfessionalService", "@id": DOMAIN + "/#org", "name": "OMO Agency", "legalName": "CM Digital S.R.L.S.",
         "url": DOMAIN + "/", "logo": DOMAIN + "/assets/omo-logo.png", "image": DOMAIN + "/assets/omo-logo.png",
         "email": EMAIL, "telephone": PHONE, "foundingDate": "2025-11", "vatID": "IT03187650605",
         "description": X['desc'][lang],
         "founder": {"@type": "Person", "name": "Eleonora Saccucci"},
         "address": {"@type": "PostalAddress", "streetAddress": "Via Campo La Guzza 7/A", "postalCode": "03030",
                     "addressLocality": "Broccostella", "addressRegion": "FR", "addressCountry": "IT"},
         "areaServed": [{"@type": "Country", "name": "Spain"}, {"@type": "Country", "name": "Italy"}],
         "knowsLanguage": ["it", "es", "en"],
         "hasOfferCatalog": {"@type": "OfferCatalog", "name": plain(T['nav_servizi'][lang]), "itemListElement": svcs}},
        {"@type": "WebSite", "@id": DOMAIN + "/#site", "url": DOMAIN + "/", "name": "OMO Agency", "publisher": {"@id": DOMAIN + "/#org"}},
        {"@type": "WebPage", "@id": url, "url": url, "name": X['title'][lang], "description": X['desc'][lang],
         "inLanguage": lang, "isPartOf": {"@id": DOMAIN + "/#site"}, "about": {"@id": DOMAIN + "/#org"}}]}
    return json.dumps(g, ensure_ascii=False).replace('</', '<\\/')

def render(tpl, lang, v):
    def rep(m):
        kind, key = m.group(1), m.group(2)
        if kind == 't': return T[key][lang]
        if kind == 'x': return X[key][lang]
        return v[key]
    return re.sub(r'\{\{([txv]):([a-zA-Z0-9_]+)\}\}', rep, tpl)

def hub_meta(lang, s, w):
    site = {"it": ("cantiere", "cantieri"), "es": ("obra", "obras"), "en": ("site", "sites")}[lang]
    op = {"it": "operai", "es": "operarios", "en": "workers"}[lang]
    return "%d %s, %d %s" % (s, site[0] if s == 1 else site[1], w, op)

def build_home(lang):
    url = "%s/%s/" % (DOMAIN, lang)
    sl = SLUGS[lang]
    langlinks = ''.join('<a href="../%s/" hreflang="%s" lang="%s"%s>%s</a>' % (l, l, l, ' aria-current="page"' if l == lang else '', l.upper()) for l in LANGS)
    footlangs = ''.join('<a href="../%s/" hreflang="%s" lang="%s">%s</a>' % (l, l, l, LNAME[l]) for l in LANGS if l != lang)
    og_alt = '\n'.join('<meta property="og:locale:alternate" content="%s">' % X['og_locale'][l] for l in LANGS if l != lang)
    wa = "https://wa.me/%s?text=%s" % (WA, urllib.parse.quote(plain(T['contact_wa_msg'][lang])))
    mail = "mailto:%s?subject=%s&body=%s" % (EMAIL, urllib.parse.quote(plain(T['contact_mail_subject'][lang])), urllib.parse.quote(plain(T['contact_mail_body'][lang])))
    docs = {"it": "documenti", "es": "documentos", "en": "documents"}[lang]
    worker = {"it": "1 lavoratore", "es": "1 trabajador", "en": "1 worker"}[lang]
    jsdata = {
        "svc": {"%02d" % i: [T['svc%02d_title' % i][lang], T['svc%02d_desc' % i][lang]] for i in range(1, 7)},
        "copied": T['contact_copied'][lang], "email": EMAIL,
        "mailSubject": plain(T['contact_mail_subject'][lang]), "mailBody": plain(T['contact_mail_body'][lang]),
        "formErr": X['f_err'][lang], "consentErr": X['consent_err'][lang], "consentLine": X['consent_line'][lang],
        "f": {"name": X['f_name'][lang], "company": X['f_company'][lang], "email": X['f_email'][lang], "size": X['f_size'][lang]},
        "menuOpen": T['nav_menuLabel'][lang], "menuClose": X['menu_close'][lang]}
    v = {
        "url": url, "domain": DOMAIN, "og_alt": og_alt, "logo_b64": LOGO, "portrait_b64": PORT,
        "jsonld": jsonld(lang, url), "langlinks": langlinks, "footlangs": footlangs,
        "eyebrow": nodot(T["hero_eyebrow"][lang]), "h1rest": T['hero_h1_suffix'][lang].strip(),
        "cred2": nodot(T['bio_cred2'][lang]), "cred3": nodot(T['bio_cred3'][lang]),
        "hub1": hub_meta(lang, 3, 14), "hub2": hub_meta(lang, 1, 5), "hub3": hub_meta(lang, 2, 8), "hub4": hub_meta(lang, 1, 3),
        "cae1": "2 " + docs, "cae2": worker, "cae4": "3 " + docs,
        "langnote": '',
        "posts": posts_html(lang), "linkedin": li_html(lang), "wa_href": html.escape(wa), "mail_href": html.escape(mail),
        "email": EMAIL, "phone": PHONE, "phone_tel": PHONE_TEL,
        "tagline": nodot(T['footer_tagline'][lang]),
        "p_privacy": sl['privacy'], "p_cookie": sl['cookie'], "p_legal": sl['legal'],
        "consent": X['consent_html'][lang].format(p=sl['privacy']),
        "jsdata": json.dumps(jsdata, ensure_ascii=False).replace('</', '<\\/'),
    }
    out = render(TPL, lang, v)
    left = re.findall(r'\{\{[^}]+\}\}', out)
    assert not left, left
    os.makedirs(f"{OUT}/{lang}", exist_ok=True)
    open(f"{OUT}/{lang}/index.html", 'w').write(out)
    return out

LEGAL_CSS = """:root{--calce:#E4E6E1;--lastra:#F3F4F1;--acciaio:#1C2226;--ink2:#4A5358;--giallo:#F2B705;--linea:#C4C9C4;color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--calce:#14181B;--lastra:#1D2327;--acciaio:#E6E8E4;--ink2:#A3ACB1;--linea:#2F373C;color-scheme:dark}}
:root[data-theme="dark"]{--calce:#14181B;--lastra:#1D2327;--acciaio:#E6E8E4;--ink2:#A3ACB1;--linea:#2F373C;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--calce);color:var(--acciaio);font:17px/1.65 'Figtree',system-ui,sans-serif}
.w{max-width:760px;margin:0 auto;padding:32px 22px 64px}
header{display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1.5px solid var(--linea);padding-bottom:16px}
header a.b{display:flex;align-items:center;gap:10px;font:800 22px 'Big Shoulders Display',sans-serif;text-decoration:none;color:inherit}
header img{width:36px;height:36px;border-radius:8px}
h1{font:900 clamp(44px,9vw,72px)/.95 'Big Shoulders Display','Arial Narrow',sans-serif;margin:40px 0 8px}
h2{font:800 30px/1 'Big Shoulders Display','Arial Narrow',sans-serif;margin:36px 0 8px}
p{margin:10px 0}.u{color:var(--ink2);font-size:15px}a{color:inherit;text-decoration-color:var(--giallo);text-decoration-thickness:2px;text-underline-offset:4px}
.back{font-weight:600}.langs a{margin-left:10px;font-size:14px;font-weight:700}
footer{margin-top:56px;padding-top:16px;border-top:6px solid var(--giallo);font-size:11.5px;color:var(--ink2)}
:focus-visible{outline:3px solid var(--acciaio);outline-offset:3px}"""

def build_legal(lang, kind):
    title, secs = PAGES[kind][lang]
    sl = SLUGS[lang]
    url = "%s/%s/%s" % (DOMAIN, lang, sl[kind])
    alts = ''.join('<link rel="alternate" hreflang="%s" href="%s/%s/%s">' % (l, DOMAIN, l, SLUGS[l][kind]) for l in LANGS)
    langs = ''.join('<a href="../../%s/%s" hreflang="%s" lang="%s">%s</a>' % (l, SLUGS[l][kind], l, l, l.upper()) for l in LANGS if l != lang)
    body = ''.join('<h2>%s</h2>%s' % (h, ''.join('<p>%s</p>' % p for p in ps)) for h, ps in secs)
    page = f"""<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title} | OMO Agency</title><meta name="description" content="{title}, OMO Agency, CM Digital S.R.L.S.">
<meta name="robots" content="noindex, follow"><link rel="canonical" href="{url}">{alts}
<link rel="icon" href="data:image/png;base64,{LOGO}">
<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@800;900&family=Figtree:wght@400;600&display=swap" rel="stylesheet">
<style>{LEGAL_CSS}</style></head><body><div class="w">
<header><a class="b" href="../"><img src="data:image/png;base64,{LOGO}" alt="{X['logo_alt'][lang]}" width="36" height="36">OMO</a><span class="langs"><a class="back" href="../">{X['back'][lang]}</a>{langs}</span></header>
<main><h1>{title}</h1><p class="u">{UPD[lang]}</p>{body}</main>
<footer>&copy; 2026 OMO Agency, by CM Digital S.R.L.S. {X['legal_office'][lang]}: Via Campo La Guzza 7/A, 03030 Broccostella (FR), {X['country'][lang]}. {X['vat'][lang]} 03187650605.</footer>
</div></body></html>"""
    os.makedirs(f"{OUT}/{lang}/{sl[kind]}", exist_ok=True)
    open(f"{OUT}/{lang}/{sl[kind]}index.html", 'w').write(page)

def build_root():
    alts = ''.join('<link rel="alternate" hreflang="%s" href="%s/%s/">' % (l, DOMAIN, l) for l in LANGS) + '<link rel="alternate" hreflang="x-default" href="%s/">' % DOMAIN
    links = ''.join('<a href="%s/" hreflang="%s" lang="%s">%s</a>' % (l, l, l, LNAME[l]) for l in LANGS)
    page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>OMO Agency | Spain and Italy</title><meta name="description" content="{X['desc']['en']}">
<link rel="canonical" href="{DOMAIN}/">{alts}<link rel="icon" href="data:image/png;base64,{LOGO}">
<script>(function(){{try{{var l=(navigator.languages&&navigator.languages[0]||navigator.language||'').slice(0,2).toLowerCase();location.replace((l==='it'||l==='es'?l:'en')+'/');}}catch(e){{}}}})();</script>
<style>body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#E4E6E1;color:#1C2226;font:600 18px system-ui,sans-serif}}nav{{display:flex;gap:20px}}a{{color:inherit}}</style>
</head><body><nav aria-label="Language">{links}</nav></body></html>"""
    open(f"{OUT}/index.html", 'w').write(page)

if __name__ == '__main__':
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(f"{OUT}/assets")
    shutil.copy(P('assets', 'omo-logo.png'), f"{OUT}/assets/omo-logo.png")
    for l in LANGS:
        build_home(l)
        for k in ('privacy', 'cookie', 'legal'):
            build_legal(l, k)
    build_root()
    open(f"{OUT}/.nojekyll", 'w').write('')
    open(f"{OUT}/CNAME", 'w').write('1minutesonline.agency')
    for r, d, f in os.walk(OUT):
        for x in f: print(os.path.join(r, x), os.path.getsize(os.path.join(r, x)))
