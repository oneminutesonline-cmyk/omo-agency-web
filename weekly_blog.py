"""Every Monday: write one new blog post (IT/ES/EN) about a real, recent piece
of news on AI in construction, with its source. Publishes nothing if any check fails."""
import datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from claude_api import call, final_json, searched_urls, norm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "blog.json")
posts = json.load(open(PATH))
today = datetime.date.today()

if any((today - datetime.date.fromisoformat(p["date"])).days < 5 for p in posts):
    print("A post from the last 5 days already exists: nothing to do.")
    sys.exit(0)

recent = sorted(posts, key=lambda p: p["date"], reverse=True)
already = "\n".join("- %s | %s" % (p["it"]["title"], p["sourceUrl"]) for p in recent[:20])
examples = "\n\n---\n\n".join(p["it"]["body"] for p in recent[:2])

SYSTEM = """Scrivi il post settimanale del blog di OMO Agency, in prima persona come Eleonora Saccucci, fondatrice.
OMO Agency aiuta le imprese di costruzione con almeno 10 dipendenti, in Spagna e in Italia, a gestire documenti dei lavoratori, piattaforme CAE e cantieri con sistemi su misura, e ad adottare l'intelligenza artificiale.

Regole, tutte obbligatorie:
1. Usa lo strumento di ricerca web. Scegli UNA notizia vera, pubblicata negli ultimi 14 giorni, sull'intelligenza artificiale o la digitalizzazione nel settore delle costruzioni. Preferisci fonti autorevoli (testate di settore, studi, comunicati ufficiali).
2. Non ripetere notizie o fonti già pubblicate (elenco sotto).
3. Ogni numero, nome e fatto deve venire dalla fonte. Non inventare dati, clienti, progetti o citazioni. Nel commento finale Eleonora può collegare la notizia al suo lavoro in modo generale, senza citare clienti né numeri propri.
4. Struttura: 3 paragrafi brevi (cosa è successo, i dati chiave, il commento di Eleonora). Tono diretto, niente gergo, niente elenchi, niente emoji, niente hashtag.
5. Scrivi tre versioni native, non traduzioni letterali: italiano, spagnolo di Spagna, inglese.
6. sourceLabel: nome della testata e data di pubblicazione della notizia, scritta nella lingua della versione (es. "Construction Dive, 16 settembre 2026" / "Construction Dive, 16 de septiembre de 2026" / "Construction Dive, 16 September 2026").

Rispondi SOLO con un oggetto JSON, senza testo prima o dopo:
{"sourceUrl": "...", "it": {"title": "...", "body": "paragrafo\\n\\nparagrafo\\n\\nparagrafo", "sourceLabel": "..."}, "es": {...}, "en": {...}}
Se non trovi una notizia che rispetti tutte le regole, rispondi {"skip": true}."""

USER = "Oggi è il %s.\n\nNotizie già pubblicate (non ripeterle):\n%s\n\nEsempi dello stile di Eleonora:\n\n%s" % (
    today.isoformat(), already or "- nessuna", examples)

blocks = call(SYSTEM, USER, tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}])
data = final_json(blocks)
if data.get("skip"):
    print("The model found no suitable news this week: nothing published.")
    sys.exit(0)

# --- checks before publishing ---
url = data.get("sourceUrl", "")
found = {norm(u) for u in searched_urls(blocks)}
problems = []
if not url.startswith("http"):
    problems.append("missing source URL")
if norm(url) not in found:
    problems.append("source URL was not among the search results")
if norm(url) in {norm(p["sourceUrl"]) for p in posts}:
    problems.append("source already used")
for lang in ("it", "es", "en"):
    v = data.get(lang) or {}
    if not all(isinstance(v.get(k), str) and v.get(k).strip() for k in ("title", "body", "sourceLabel")):
        problems.append("incomplete %s version" % lang)
    elif not (60 <= len(v["body"].split()) <= 450):
        problems.append("%s body length out of range" % lang)
if problems:
    print("Post NOT published: " + "; ".join(problems))
    sys.exit(0)

entry = {"date": today.isoformat(), "sourceUrl": url}
for lang in ("it", "es", "en"):
    entry[lang] = {k: data[lang][k].strip() for k in ("title", "body", "sourceLabel")}
posts.append(entry)
json.dump(posts, open(PATH, "w"), ensure_ascii=False, indent=1)
print("Published: " + entry["it"]["title"])
