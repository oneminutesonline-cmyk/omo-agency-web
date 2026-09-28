# Sito OMO Agency – 1minutesonline.agency

Sito statico in tre lingue (/it/, /es/, /en/), pubblicato con GitHub Pages tramite GitHub Actions.

## Cosa succede da solo
- **Ogni lunedì alle 06:00 UTC** l'automazione "Sito OMO" scrive un nuovo articolo del blog in italiano, spagnolo e inglese. Parte da una notizia vera sull'AI nell'edilizia, sempre con la fonte citata. Se la notizia non supera i controlli (fonte verificata, non già usata, testi completi), quella settimana non pubblica nulla.
- **Post LinkedIn:** quando apri il modulo "Nuovo post LinkedIn" (tab Issues), il sito si aggiorna in un paio di minuti. Il testo originale resta com'è, le altre due lingue vengono tradotte. Il sito mostra i due post più recenti.
- **Ogni modifica** caricata su `main` ripubblica il sito.

## Pubblicare un post LinkedIn (anche da telefono, app GitHub)
Issues → New issue → **Nuovo post LinkedIn** → link, testo, fino a 3 foto, data (facoltativa) → Submit.
Solo il proprietario del repository può pubblicare così: gli issue aperti da altre persone vengono ignorati.

## Configurazione (una volta sola)
1. Settings → Pages → Source: **GitHub Actions**. Custom domain: `1minutesonline.agency`.
2. Settings → Secrets and variables → Actions → New repository secret: `ANTHROPIC_API_KEY` (chiave da console.anthropic.com).
3. Actions → Sito OMO → Run workflow (spunta "Scrivi subito il post del blog" se vuoi l'articolo subito).

## Dove stanno le cose
- `data/blog.json` – articoli del blog (IT/ES/EN)
- `data/linkedin.json` e `assets/li/` – post LinkedIn e foto
- `src/` – design, testi del sito, pagine legali, generatore
- `scripts/` – automazioni settimanali
