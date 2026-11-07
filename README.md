# UPIX 1989

Tributo arcade a **Qix (1981)** e **Volfied (1989)**, sviluppato in Python con Pygame. Si conquistano porzioni del campo per rivelare un'immagine, evitando il boss e i suoi missili durante il tracciamento.

Il progetto è un **prototipo giocabile** con 12 livelli. Per analisi del codice, problemi aperti, fonti storiche e piano di sviluppo consultare [REPORT_SVILUPPO.md](REPORT_SVILUPPO.md), aggiornato il 7 novembre 2026.

## Installazione e avvio

Ambiente verificato: Windows, Python **3.13.5**, Pygame **2.6.1**, renderer SVG **resvg_py 0.5.0**. Altri sistemi o versioni di Python richiedono una verifica dedicata.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe Upqix89.py
```

Se Python è disponibile tramite il launcher Windows, usare `py -3` al posto di `python` per creare l'ambiente. Installare le dipendenze aggiornate nell'interprete usato per avviare il gioco. L'ambiente `.venv` locale è già stato preparato durante lo sviluppo.

Gli asset vengono cercati rispetto a `Upqix89.py`, indipendentemente dalla cartella di avvio. `start.bat`, se presente localmente, preferisce `.venv`, salva l'output in `errorlog.txt` e mostra eventuali errori.

## Comandi e regole attuali

| Tasto | Azione |
| --- | --- |
| Frecce | Impostano la direzione del cursore |
| P | Pausa / ripresa |
| Q | Esce |
| R | Ricomincia dopo il Game Over; riapre il livello se la fisica è sospesa per uno stato invalido |
| Spazio | Passa al livello successivo dopo la vittoria |

- Il movimento continua anche rilasciando la freccia. Una nuova freccia cambia direzione; durante il disegno non è possibile invertire direttamente il senso.
- Il cursore parte sul bordo sicuro. Entrando nel campo non conquistato crea una scia vulnerabile.
- La linea deve tornare a un'area sicura. Sono possibili percorsi ortogonali complessi, non soltanto rettangoli.
- La zona separata dal boss viene conquistata; quella raggiungibile dal boss rimane aperta.
- Boss e missili che toccano la scia fanno perdere una vita. Anche un'autointersezione fa perdere una vita.
- Il territorio conquistato assorbe i missili al primo contatto, anche con muri di una cella.
- La perdita del focus mette in pausa; premere P per riprendere. Boss, missili, input di movimento, timer e audio rimangono sospesi durante la pausa.
- L'HUD mostra il tempo attivo del livello. La pausa non crea arretrati negli spari o nell'AI alla ripresa.
- Si parte con 3 vite. Dopo una morte si riparte dall'ultimo punto sicuro.
- La vittoria richiede almeno l'80%. Attualmente la percentuale include il bordo iniziale, ma si aggiorna solo dopo una cattura.
- Dopo il livello 12 si torna al livello 1 mantenendo le vite. Il punteggio interno si azzera a ogni livello e non è ancora mostrato nell'HUD.

## Audio della saldatrice

L'effetto è attivo **soltanto mentre il cursore traccia nel campo non conquistato**. È spento sul bordo e nelle aree sicure, alla chiusura della linea, alla morte, al cambio livello e all'uscita.

- `public/sounds/saldatrice.mp3`: registrazione originale, mantenuta come fallback.
- `public/sounds/saldatrice.wav`: stessa registrazione preparata per il gioco, con i primi 0,30 s rimossi, guadagno di 6 dB, limitatore e brevi dissolvenze per attenuare i clic.
- Un canale riservato riproduce il loop senza riavviarlo a ogni frame.
- Durante il tracciamento la musica passa da `0.26` a **`0.155`**; alla fine torna a `0.26`. L'effetto usa volume `0.80`. `DRAW_MUSIC_ATTENUATION = 0.105` regola la riduzione musicale; `DRAW_MUSIC_VOLUME` viene calcolato dal volume normale. L'ultima modifica dimezza l'abbassamento precedente, rendendo la musica più udibile durante il disegno.
- Le costanti si trovano all'inizio di `Upqix89.py`. Senza dispositivo audio il gioco continua in silenzio e stampa il motivo.

Per rigenerare il WAV serve **FFmpeg**, non necessario per giocare:

```powershell
ffmpeg -i public/sounds/saldatrice.mp3 -af "atrim=start=0.30:end=8.55,asetpts=PTS-STARTPTS,volume=2,alimiter=limit=0.95:level=false,afade=t=in:d=0.005,afade=t=out:st=8.24:d=0.01" -c:a pcm_s16le public/sounds/saldatrice.wav
```

Se il WAV esiste già, FFmpeg chiede se sovrascriverlo.

## Struttura

```text
Upix/
├── Upqix89.py                # Simulazione, rendering, audio e loop principale
├── collisions.py            # Geometria e solver AABB indipendente (Passi 1A–1B)
├── game_state.py            # Stati e orologio logico che esclude le pause
├── territory.py             # Pianificazione validata della conquista (Passo 1C)
├── assets.py                # Sfondi SVG e fallback raster al cambio livello
├── README.md
├── REPORT_SVILUPPO.md        # Revisione tecnica e roadmap
├── requirements.txt
├── .gitignore
├── tests/
│   ├── test_game.py          # Regressioni con driver SDL dummy
│   ├── test_collisions.py    # Geometria e solver, incluso muro 200–201 px
│   ├── test_territory.py     # Catture senza modifiche parziali
│   ├── test_game_state.py    # Timer deterministico senza attese reali
│   └── test_assets.py        # SVG, testo, cache e fallback
├── tools/
│   └── benchmark_resolution.py
└── public/
    ├── assets/              # SVG di copertura e PNG/JPG primarie da svelare
    ├── icon/                # cursor_lukso.png, boss2.png e altre icone
    ├── music/               # Quattro tracce MP3
    └── sounds/              # Effetto originale MP3 e WAV preparato
```

`copy_images.ps1` è uno script storico che **copia** i JPG con estensione `.png`: non converte il formato. Pygame li decodifica comunque, ma la pipeline va corretta prima della distribuzione. Nessun asset è stato eliminato.

I due livelli grafici hanno ruoli distinti:

- **Copertura:** `01.svg` … `12.svg`, visibile subito nel campo non conquistato,
  al posto del nero. Rasterizzata solo al cambio livello, con cache limitata,
  gradienti e proporzioni preservate. Le label centrali “Level 1” … “Level 12”
  sono state eliminate dai file SVG; il livello è indicato nell'HUD.
- **Immagine primaria:** `01.png` … `12.png` (fallback `.jpg`), nascosta sotto
  la copertura e adattata all'intero campo come nel prototipo. Le catture ne
  svelano le porzioni corrispondenti; alla vittoria viene mostrata interamente.

Se manca l'SVG si usa una copertura neutra. Se manca l'immagine primaria si usa
un'immagine procedurale. I fallback mantengono separati i ruoli: l'SVG non
diventa mai l'immagine da svelare e la primaria non viene esposta in anticipo.

Il boss usa esclusivamente `boss2.png`: alpha preservato, proporzioni mantenute
a dimensioni arrotondate **96 × 70 px**, centro agganciato alla posizione logica.
L'ultima direttiva dell'utente richiede una **hitbox AABB uguale allo sprite**:
entrambi usano l'unico parametro `BOSS_SIZE`. Se manca l'asset, il fallback
grafico mantiene queste dimensioni; il vecchio `boss.png` non viene caricato.

## Architettura e cattura delle aree

Il campo 800 × 600 px usa celle da 2 px: **400 × 300 = 120.000 celle**. `grid[x][y]` contiene `EMPTY` o `FILLED`; la scia in corso è conservata separatamente.

Alla chiusura della linea, `fill_area()`:

1. Valida corpo del boss, scia continua e collegamento delle zone sicure.
2. Pianifica con `territory.plan_capture()` la BFS inversa, trattando la scia come barriera senza modificare la griglia.
3. Verifica che la conquista lasci libero l'intero corpo del boss. Un contatto con la nuova scia fa perdere una vita prima di qualsiasi scrittura.
4. Applica il piano a griglia/canvas e aggiorna percentuale e punteggio.

Il flood fill inverso è adatto alle forme concave, purché il boss sia in una cella libera valida e le collisioni mantengano questo vincolo. **Non garantisce da solo che il boss non attraversi muri**. Con più boss occorrerà definire le regole e, se devono restare tutti in gioco, conservare l'unione delle regioni raggiungibili da tutti i boss attivi.

Il rendering riutilizza la `canvas`, evitando di ricostruire la maschera ogni frame. La cattura resta sincrona e può superare il budget di un frame: vedere le misure nel report.

I Passi 1B e 1C collegano il solver al movimento del boss: corpo AABB float
96 × 70 px, substep di massimo 1 px per asse, scansione dell'intero segmento,
rimbalzi sull'asse d'impatto e consumo del residuo. Il test sul muro
x=200–201 px passa anche nel runtime. Il solver non legge timer o casualità.
I missili usano lo stesso contratto di substep e la stessa geometria di griglia,
con primo contatto sul segmento rettilineo e assorbimento senza rimbalzi.
La migrazione del movimento a tempo fisso resta un intervento successivo.

Gli stati `PLAYING`, `PAUSED`, `LEVEL_CLEAR`, `GAME_OVER` e `PHYSICS_ERROR`
sono espliciti. `game_over` e `win` sono proprietà derivate dallo stato.
La pausa sospende canali e musica senza riavviare i campioni alla ripresa.

## Verifiche

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

I **91 test** coprono geometria/solver, missili continui, stati/pausa, timer,
cattura, audio, respawn, vittoria,
progressione, le 12 coppie copertura/immagine primaria senza label, cache, rendering
del boss e fallback. Una regressione con SVG e PNG di colori distinti verifica
copertura iniziale, rivelazione e schermata di vittoria.
I test geometrici e della conquista non richiedono Pygame.

Usano driver SDL `dummy`: controllano mixer e segnale del WAV, **non l'ascolto dagli altoparlanti**. Non certificano l'assenza dei problemi aperti né sostituiscono una partita completa con audio reale.

Per confrontare le risoluzioni senza cambiare la configurazione del gioco:

```powershell
.\.venv\Scripts\python.exe tools/benchmark_resolution.py --repeats 5 --resolutions 800x600 1024x768
```

Eseguirlo separatamente dalla suite di test. È disponibile anche il profilo
`1024x1024`. Il campo resta **800×600**. **1024×768 è fattibile** e conserva
il 4:3, ma richiede il 63,84% di celle in più: prima di aumentare la griglia
si raccomanda di ottimizzare il flood fill o ingrandire soltanto il viewport.

## Repository

Il `.gitignore` esclude cache Python, ambienti virtuali, build, log, file degli editor, configurazioni private e salvataggi. Gli asset runtime e i test devono essere versionati. Le esclusioni locali di `Documenti` e `start.bat` aggiunte durante la revisione sono state rispettate.

**Tutti i comandi e le operazioni Git sono riservati all'utente**, inclusi i
controlli di sola lettura. Questa regola è conservata anche in `AGENTS.md`.
L'assistente modifica codice e documentazione ed esegue le verifiche applicative.
