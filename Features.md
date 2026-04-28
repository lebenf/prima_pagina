# Prima Pagina — Funzionalità implementate

## Autenticazione e sessioni
- Login con username o email + password
- Sessioni persistenti via cookie `HttpOnly` (`pp_session`)
- CSRF protection con double-submit cookie (`X-CSRF-Token`)
- Logout con revoca sessione
- Rate limiting sul login (5 tentativi/minuto)
- Visualizzazione e revoca delle proprie sessioni attive dalla pagina Impostazioni

## Gestione feed (RSS/Atom)
- Catalogo globale di feed gestito dagli admin
- Auto-discovery del titolo e metadati da URL
- Configurazione per feed: intervallo di polling (5–1440 min), peso fonte (0.1–5.0), categoria, stato attivo/inattivo
- Refresh manuale on-demand
- Iscrizione/disiscrizione per singolo utente
- Protezione SSRF: blocco di IP privati, loopback, link-local, schemi non-HTTP

## Lettura articoli (Reader)
- Lista feed nella sidebar sinistra, raggruppata per categoria con nomi localizzati
- Lista articoli al centro con conteggio non letti per feed
- Lettore inline a destra con testo completo estratto on-demand (trafilatura)
- Marcatura automatica come letto dopo 3 secondi di lettura
- Navigazione da tastiera: `j`/`k` articolo precedente/successivo, `r` segna letto, `s` salva
- Filtri: non letti, salvati, archiviati, ricerca testuale
- Marca tutto come letto per feed
- Stato articolo: letto, salvato (starred), archiviato

## Prima Pagina (front page)
- Layout stile giornale: articolo hero, seconda riga, colonne per categoria
- Scoring degli articoli: decadimento temporale (emivita 12h), peso fonte, affinità categoria, peso topic, penalità articoli già letti
- Affinità categoria calcolata dalla cronologia di lettura dell'utente
- Peso topic basato sulle preferenze personali per tag (aggiornate dai voti)
- topic_prefs e category_affinity precaricati una volta per richiesta (no N+1)
- Finestra temporale 48 ore

## Voti articoli (pollice su/giù)
- Voto +1 / -1 per articolo; aggiornabile e rimovibile
- I voti aggiornano le preferenze per tag (user_topic_preferences) dell'utente
- Score tag normalizzato [-5, +5] → peso ranking [0.1, 2.0]; neutro = 1.0
- I voti non penalizzano il singolo articolo ma l'intero topic (tag) associato
- `user_vote` incluso in ogni risposta lista/dettaglio/frontpage
- Voti degli utenti indipendenti: non influenzano il ranking degli altri utenti

## Estrazione full-text intelligente (T16)
- Tre modalità per feed: `trafilatura` (default), `script` (CSS selectors via LLM), `auto` (trafilatura + generazione script automatica)
- LLM analizza HTML campione e produce CSS selectors per content/title/author/date
- Selectors validati su HTML reale prima del salvataggio; non salvati se `content` non trovato
- Layout change detection: hash struttura body (tag+classi, non testo) — penalità accelerata su cambio
- `consecutive_failures >= 5` → script disattivato, rigenerazione avviata in background
- `success_rate` con media mobile esponenziale (×0.95 per failure, ×0.95+0.05 per success)
- `fulltext_method` salvato su ogni articolo (`trafilatura` | `script`)
- Admin API: `GET /feeds/{id}/extraction-script`, `POST /feeds/{id}/extraction-script/regenerate`
- `PUT /feeds/{id}` esteso con `fulltext_enabled` e `fulltext_mode`
- `beautifulsoup4` + `lxml` aggiunti come dipendenze

## Ricerca full-text globale (T18)
- `GET /api/v1/search?q=...` — ricerca su titolo + excerpt degli articoli dei feed sottoscritti
- SQLite: LIKE case-insensitive con `func.lower().contains()`; PostgreSQL: `to_tsvector` + `plainto_tsquery` + `ts_rank`
- `title_highlighted` e `excerpt_snippet` con `<mark>` attorno ai match, snippet con contesto ±80 caratteri
- Filtri: `feed_id`, `category_id`, `date_from`, `date_to`; paginazione standard `page`/`size`/`total`/`pages`
- `Ctrl+K` / `⌘K` globale apre SearchModal; `Esc` chiude; frecce ↑↓ navigano risultati; `Enter` apre articolo nel Reader
- Debounce 300ms, focus automatico sull'input, reset selezione al cambio risultati
- Bottone ricerca in AppHeader (visibile su desktop) sostituisce input disabilitato
- CSS globale `mark { background: #fef08a }` per evidenziazione uniforme

## ArticleDrawer e deep linking (T19)
- Drawer slide-from-right nella Prima Pagina: click su articolo apre pannello laterale senza lasciare la pagina
- URL come fonte di verità: `?article={id}` nella query string; condivisibile e navigabile con back/forward del browser
- Caricamento articolo completo al primo accesso, fulltext polling se ancora in elaborazione
- Marcatura automatica come letto dopo 3 secondi di apertura
- Tasto Esc e click sull'overlay chiudono il drawer
- Navigazione a articoli correlati inline: click apre il correlato nello stesso drawer
- Blocco scroll del body durante apertura, ripristinato alla chiusura/smontaggio
- Pulsante "Apri nel Reader" per passare alla vista Reader con l'articolo già selezionato
- **VoteButtons** (pollice su/giù): componente compatto riutilizzabile in ArticleToolbar (Reader), HeroArticle, SecondRowArticle, CategoryColumn e ArticleDrawer
- Aggiornamento ottimistico del voto con rollback in caso di errore API
- `@click.stop` sui bottoni voto — non propaga click verso l'apertura articolo
- `vote-changed` emit aggiorna lo stato in-memory nei componenti della Prima Pagina senza ricaricare

## Articoli correlati (T17)
- Calcolo automatico dopo il tagging: finestra 72h, articoli con tag sovrapposti da feed diversi
- Fino a 3 candidati: restituiti direttamente; oltre 3: LLM seleziona i top 5 più pertinenti per argomento
- Fallback silenzioso: nessun LLM configurato → primi MAX_RELATED per overlap di tag
- Risultato in `article_llm_data.related_article_ids` — condiviso tra utenti, calcolato una sola volta
- `GET /api/v1/articles/{id}/related` restituisce lista ordinata con stato utente (is_read, is_starred, user_vote)
- Sezione "Leggi anche" in fondo al Reader: click su correlato apre l'articolo
- Non mostra placeholder o skeleton se correlati non ancora disponibili

## Dati LLM condivisi (article_llm_data)
- Riepilogo LLM e articoli correlati memorizzati una volta per articolo (condivisi tra utenti)

## Digest (rassegna stampa)
- Generazione on-demand o schedulata (cron configurabile, default `0 7 * * *`)
- Provider LLM selezionabile: Ollama (self-hosted) o Claude (Anthropic API)
- Output HTML strutturato con sezioni tematiche
- Timeout configurabile per provider (default 300s)
- Storico digest con lista e dettaglio
- Gestione errori: digest falliti persistiti con `status = "failed"` e `generation_error` (messaggio LLM/timeout)
- UI: banner rosso con messaggio errore e bottone "Riprova" per digest falliti; modale mostra dettaglio errore e hint

## Feed virtuali
- Creazione di feed filtrati per categoria, tag o combinazione
- Anteprima articoli corrispondenti prima del salvataggio
- Esportazione Atom 1.0 tramite URL pubblico con token (`/api/v1/virtual-feeds/{id}/rss?token=...`)
- Rigenerazione token RSS
- Possibilità di includere il digest come primo articolo del feed

## Tagging LLM
- Tagging automatico degli articoli con categorie e tag liberi
- Prompt bilingue con lingua rilevata automaticamente
- Fallback silenzioso in caso di timeout o errore

## Inviti utenti
- Admin genera link monouso con token UUID (`/join?token=...`)
- Link opzionalmente legato a un'email specifica
- Scadenza configurabile (default 7 giorni); revocabile prima del termine
- Pagina registrazione pubblica: valida token, precompila email se vincolata, auto-login dopo registrazione
- Conferma password richiesta sia nella creazione admin che nella registrazione pubblica
- Lista inviti in admin con stato (attivo/scaduto/usato) e bottone revoca

## Pannello di amministrazione
- **Utenti**: lista, creazione (con conferma password), modifica (ruolo, lingua, password, stato), eliminazione (con protezione self-delete)
- **Inviti**: generazione link, lista con stato, revoca
- **Sessioni**: lista globale con filtro per utente, revoca singola, revoca tutte per utente
- **Feed**: lista con filtro categoria e ricerca, colonna Fulltext con badge script (verde/arancio/rosso per success rate), modale dettaglio script con CSS selectors e bottone rigenerazione, iscrizione/disiscrizione inline, refresh, CRUD completo
- **Categorie**: CRUD con nomi multilingua (it/en/fr/de/es/pt), raggruppamento per categoria nel reader
- **Config LLM**: CRUD provider (Ollama/Claude), health check con latenza, timeout configurabile (30–3600s), selezione uso (tagging/digest), priorità
- **Plugin**: CRUD configurazioni plugin, test connessione inline, form dinamico guidato dallo schema

## Plugin notifiche
- Architettura a plugin con registro dinamico
- Plugin Telegram: invio articoli e digest con tastiera inline, supporto canali e chat private
- Test connessione dalla UI admin

## Impostazioni utente
- Cambio lingua interfaccia con effetto immediato (6 lingue: it/en/fr/de/es/pt)
- Cambio password con verifica password corrente
- Visualizzazione e revoca sessioni proprie

## Internazionalizzazione (i18n)
- 6 lingue complete: italiano, inglese, francese, tedesco, spagnolo, portoghese
- Formati data/ora localizzati
- Lingua preferita salvata per utente, applicata automaticamente al login

## PWA (Progressive Web App)
- Service worker con caching stratificato:
  - Articoli: NetworkFirst, cache 24h
  - Feed: NetworkFirst, cache 30min
  - Auth: NetworkOnly (mai in cache)
  - Immagini esterne: CacheFirst, cache 7 giorni
- Banner offline con animazione slide-down
- Prompt aggiornamento con scelta utente (non autoUpdate)
- Manifest con icone 192×512

## Sicurezza backend
- Security headers su tutte le risposte: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`
- CSP in produzione
- HSTS quando `SECURE_COOKIES=true`
- API key LLM cifrate a riposo con Fernet (`ENCRYPTION_KEY`)
- Cookie sessione `HttpOnly`, `SameSite=Lax`, `Secure` configurabile

## Database e infrastruttura
- SQLite (default, async via aiosqlite) o PostgreSQL — cambio solo via `DATABASE_URL`
- Migrazioni Alembic versionate
- WAL mode per SQLite
- Scheduler APScheduler in-process con job per feed e digest
- Docker Compose con profili: default, `postgres`, `ollama`

## Code splitting frontend
- Chunk separati: `vue-vendor`, `i18n`, `axios`
