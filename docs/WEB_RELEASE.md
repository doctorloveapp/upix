# UPIX 1989 sul sito Sons of Art

Aggiornamento dell'8 novembre 2026: la consegna operativa aggiornata per l'agente
del sito è **[webapp.md](../webapp.md)**. Comprende anche pipeline audio
normalizzato, finale New Game Plus, differenze della build Windows e limiti del
contratto replay attuale. Le API descritte qui restano proposte, non pubblicate.

Verifica del 7 novembre 2026 su <https://sonsofart.vercel.app/>: risposta HTTP 200,
header `Server: Vercel`, bundle `/assets/index-dS5fXNpK.js` con React/createRoot
e marcatori Vite. La pagina presenta il collettivo e la sezione giochi/LUKSO.
Il contenuto pubblico non permette di verificare database, autenticazione o
backend privato. Il repository del sito non è presente in questo workspace e
non è stato modificato né pubblicato nulla sul sito.

## Implementato in questa consegna

- Campagna desktop con menu iniziale, riepiloghi, Run Score, finale dopo il
  dodicesimo livello, scelta di nuovi cicli e nome per la classifica alla fine
  della partita. Aggiornamento 8 novembre: controller, cataloghi IT/EN, AABB
  complete, scudi, vita extra e due scosse dal livello 5 implementati sul desktop.
  Sono ora disponibili anche lingua a caldo, premi combinati, avvio debug in
  memoria e playlist musicale scoperta automaticamente dal filesystem.
- `JsonScoreStore`: `user_data/highscores.json`, UTF-8, versione e campagna,
  ordinamento stabile, massimo dieci risultati e scrittura atomica.
- `BrowserScoreStore`: stesso contratto, storage Web iniettato con `getItem` e
  `setItem`. Testato con un fake del bridge; non è una build WebAssembly collaudata.
- `game_manifest.json`: contenuti, campagna, asset, dimensioni, audio, input,
  riferimenti ai cataloghi IT/EN, cornice, chiavi storage e namespace API. Il fingerprint
  identifica la configurazione distribuita; non è una prova di autenticità.

Il bonus di un livello viene congelato al completamento. Il totale consolidato
persiste in memoria fra i livelli; il bonus del livello in corso può ancora
decrescere. La classifica salva il totale al Game Over o a fine campagna.
Non è stato aggiunto un salvataggio/ripristino della partita a metà livello.
I risultati sono indicizzati per ciclo/livello; `levels_completed` può superare
12. Il Run Score resta in memoria tra i cicli e viene registrato solo al termine.
Il futuro replay deve includere anche l'attivazione dello scudo e la scelta
continua/termina, usando tick globali del run anziché azzerarli a ogni livello.
L'enum del contratto proposto è stato aggiornato; recorder e verifica server
restano da implementare. Regole nuove richiedono un ruleset competitivo distinto.

## Pubblicazione proposta

1. Aggiungere nel sito React una pagina `/games/upix-1989`, con contenitore 4:3
   responsivo e focus tastiera esplicito. I comandi del gioco devono impedire lo
   scroll della pagina solo mentre il canvas ha il focus; uscita con Esc deve
   restare accessibile. Desktop resta il riferimento; touch va progettato.
2. Preparare una build pygame WebAssembly dedicata. Pygbag richiede un ciclo
   `async` che ceda il controllo al browser; il loop desktop corrente non va
   pubblicato semplicemente come Python su una pagina.
   [Documentazione primaria Pygbag](https://github.com/pygame-web/pygbag/blob/main/README.md).
   Includere entrambi i cataloghi e passare la lingua del browser al Localizer;
   verificare la mappatura dei gamepad nel runtime Web invece di assumere che
   il collaudo joystick SDL desktop certifichi anche quella piattaforma.
   La scansione musicale desktop dovrà vedere il filesystem virtuale degli
   asset inclusi nella build: aggiungere MP3 sul server senza una nuova build
   richiederebbe un catalogo HTTP dedicato, non implementato in questa consegna.
3. Esportare prima della build le coperture SVG in PNG alla dimensione logica:
   `resvg_py` è una dipendenza nativa del desktop e non è stata verificata su
   WebAssembly. Bundlare un font e verificare decoder audio, avvio tramite gesto
   utente, pausa su perdita focus, caricamenti, memoria e dimensione del pacchetto.
4. Iniettare `BrowserScoreStore(window.localStorage)` nel controller Web per
   risultati personali offline. Lo storage è per origine e può essere negato o
   cancellato: gestire l'errore come nel desktop. Passare dal dominio Vercel al
   dominio definitivo non trasferisce automaticamente questi dati.
   [MDN: localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage).
5. Integrare nel backend personalizzato il contratto
   [leaderboard.openapi.json](../web/leaderboard.openapi.json), con database
   persistente; [schema.sql](../web/schema.sql) è una base PostgreSQL da adattare.
   Le funzioni Vercel possono accedere a storage/database esterni; il JSON locale
   del gioco non è un database condiviso per gli utenti del sito.
   [Vercel: database e storage](https://vercel.com/docs/marketplace-storage).

## Classifica pubblica: verifica sul server

Le API descritte sono **proposte, non endpoint già attivati**. Nessuna chiamata
di rete è stata inserita nel tick fisico e nessuna credenziale è nel manifest.

- `POST /runs`: il server sceglie run ID e seme, associa campagna/configurazione
  ammessa e rilascia una capability di breve durata. Il client non decide quali
  versioni di bilanciamento siano ammesse.
- Il gioco registra input efficaci per tick logico, comprimendo gli intervalli
  ripetuti. Tempo di pausa e frame di CAPTURING non aggiungono tick. Registrazione
  e replay pubblico non sono ancora implementati in questa consegna.
- `POST /runs/{run_id}/finish`: invia nome, tick finale e input, non un punteggio
  da accettare sulla fiducia. Il server convalida token, sequenza, dimensione e
  durata; un worker riesegue la simulazione ammessa e ricalcola il risultato.
- La risposta è `202 pending`: una verifica lunga non deve occupare il render
  loop né richiedere una funzione HTTP aperta per tutta la campagna.
- Solo una run verificata entra nella classifica pubblica. Run ID univoco e
  transazione impediscono di accreditare due volte lo stesso invio. Record locali
  modificabili e sola firma/hash del manifest non costituiscono anti-cheat.
- Il client interroga lo stato con backoff e timeout. Offline conserva il
  risultato personale; non lo presenta come risultato pubblico verificato.

Usare HTTPS, validazione server, limiti sulle richieste e transizioni di stato
verificate; per account/cookie adattare CSRF e autenticazione al backend già
esistente. [OWASP: REST Security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html).
Nessun provider, database o servizio a pagamento è stato creato.

## Criteri prima della release Web

Il port Web, il replay autorevole, le API e la migrazione SQL richiedono il
repository/backend del sito. Prima di pubblicare: test desktop/browser sullo
stesso seed e input, reload con storage personale, indisponibilità/quota storage,
retry HTTP idempotenti, invii manipolati rifiutati e sessioni complete dei dodici
livelli sul dispositivo reale. Il codice desktop consegnato non viene dichiarato
una release online già collaudata.
