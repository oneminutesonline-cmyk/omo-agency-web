"""Turns the owner's "[LinkedIn]" issues into posts shown under the blog.
Each issue (opened from the "Nuovo post LinkedIn" form) holds: link, text, photos, date.
The original text is kept as written; the other two languages are written by Claude."""
import base64, datetime, io, json, os, re, sys
import requests
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from claude_api import call, final_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "linkedin.json")
REPO = os.environ["GITHUB_REPOSITORY"]
OWNER = REPO.split("/")[0].lower()
GH = {"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"], "Accept": "application/vnd.github+json"}
LANGS = ("it", "es", "en")
MONTHS = {"it": "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre",
          "es": "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre",
          "en": "January February March April May June July August September October November December"}


def sections(body):
    out, cur = {}, None
    for line in (body or "").splitlines():
        m = re.match(r"^###\s+(.*)$", line)
        if m:
            cur = m.group(1).strip().lower()
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def pick(sec, *names):
    for k, v in sec.items():
        if any(n in k for n in names):
            return "" if v == "_No response_" else v
    return ""


def fmt_date(d, lang):
    m = MONTHS[lang].split()[d.month - 1]
    return {"it": "%d %s %d", "es": "%d de %s de %d", "en": "%d %s %d"}[lang] % (d.day, m, d.year)


def paragraphs(text):
    text = re.sub(r"(?m)^\s*(#\w+\s*)+$", "", text)          # hashtag-only lines
    return [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def process(issue, posts):
    sec = sections(issue["body"])
    link = re.search(r"https?://\S+", pick(sec, "link"))
    text = pick(sec, "testo", "text")
    if not link or not text:
        return "Manca il link o il testo del post. Apri un nuovo modulo con tutti i campi."
    link = link.group(0).rstrip(").,")
    if any(p["url"] == link for p in posts):
        return "Questo post è già sul sito."
    try:
        date = datetime.date.fromisoformat(pick(sec, "data", "date")[:10])
    except ValueError:
        date = datetime.date.fromisoformat(issue["created_at"][:10])

    urls = re.findall(r"!\[[^\]]*\]\((https?://[^)\s]+)\)", issue["body"]) + re.findall(r'<img[^>]+src="(https?://[^"]+)"', issue["body"])
    pid = "li-%d" % issue["number"]
    images, raw = [], []
    for i, u in enumerate(urls[:3]):
        r = requests.get(u, headers={"Authorization": GH["Authorization"]}, timeout=60)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        im.thumbnail((900, 900))
        rel = "assets/li/%s-%d.webp" % (pid, i + 1)
        im.save(os.path.join(ROOT, rel), "WEBP", quality=76)
        images.append(rel)
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=80)
        raw.append(base64.b64encode(buf.getvalue()).decode())

    paras = paragraphs(text)
    system = ("Prepari un post LinkedIn di Eleonora Saccucci (fondatrice di OMO Agency) per il sito, in italiano, spagnolo di Spagna e inglese. "
              "Non aggiungere né togliere informazioni: traduci in modo naturale e fedele. Non inventare nulla. "
              "Rispondi SOLO con JSON: {\"orig\": \"it|es|en\", "
              "\"it\": {\"text\": [paragrafi], \"topic\": \"...\", \"alts\": [...]}, \"es\": {...}, \"en\": {...}}. "
              "orig = lingua del testo originale. text = i paragrafi nella lingua indicata (per la lingua originale, copia identici i paragrafi ricevuti). "
              "topic = massimo 8 parole: evento o tema del post e luogo se citato nel testo, senza data. "
              "alts = una descrizione breve e concreta per ogni foto, nello stesso ordine, senza inventare nomi di persone oltre a Eleonora se chiaramente è lei (selfie).")
    content = [{"type": "text", "text": "Paragrafi del post:\n" + json.dumps(paras, ensure_ascii=False)}]
    content += [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": d}} for d in raw]
    data = final_json(call(system, content, max_tokens=5000))

    orig = data.get("orig") if data.get("orig") in LANGS else "it"
    entry = {"id": pid, "date": date.isoformat(), "url": link, "orig": orig, "images": images}
    for lang in LANGS:
        v = data.get(lang) or {}
        body = paras if lang == orig else [p for p in v.get("text", []) if isinstance(p, str) and p.strip()]
        if not body:
            raise ValueError("missing %s text" % lang)
        alts = [a for a in v.get("alts", []) if isinstance(a, str)][:len(images)]
        alts += ["Foto dal post LinkedIn di Eleonora Saccucci"] * (len(images) - len(alts))
        topic = (v.get("topic") or "LinkedIn").strip()
        entry[lang] = {"meta": "%s, %s" % (topic, fmt_date(date, lang)), "text": body, "alts": alts}
    posts.append(entry)
    return None


def main():
    posts = json.load(open(PATH))
    r = requests.get("https://api.github.com/repos/%s/issues?state=open&per_page=50" % REPO, headers=GH, timeout=60)
    r.raise_for_status()
    for issue in r.json():
        if "pull_request" in issue or not issue["title"].lower().startswith("[linkedin]"):
            continue
        if issue["user"]["login"].lower() != OWNER:        # only the site owner can publish
            continue
        try:
            err = process(issue, posts)
        except Exception as e:                             # keep the issue open, try again next run
            print("Issue #%d not processed: %s" % (issue["number"], e))
            continue
        base = "https://api.github.com/repos/%s/issues/%d" % (REPO, issue["number"])
        msg = err or "Pubblicato sul sito. Il sito si aggiorna tra un paio di minuti."
        requests.post(base + "/comments", headers=GH, json={"body": msg}, timeout=60)
        requests.patch(base, headers=GH, json={"state": "closed"}, timeout=60)
    json.dump(posts, open(PATH, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
