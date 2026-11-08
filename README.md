# UPIX 1989

Tributo arcade a **Qix (1981)** e **Volfied (1989)**, sviluppato in Python con Pygame. Si conquistano porzioni del campo per rivelare un'immagine, evitando il boss e i suoi missili durante il tracciamento.

Il progetto contiene una campagna di **12 livelli con boss distinti**, cicli di
difficoltà progressiva, Scossa anti-attesa, scudi e bonus di conquista.
L'avvio passa sempre dal **menu principale**. Run Score, riepiloghi di livello,
finale di campagna e classifica locale sono implementati.
La schermata finale usa il logo Sons of Art e propone **Continua: New Game Plus**.
La build Windows è in **dist/UPIX1989.exe**; istruzioni in
[RELEASE_WINDOWS.md](RELEASE_WINDOWS.md). Per l'agente del sito:
[webapp.md](webapp.md), piano tecnico del port browser e delle classifiche online.
Per verifiche, problemi aperti e roadmap consultare
[REPORT_SVILUPPO.md](REPORT_SVILUPPO.md), aggiornato l'8 novembre 2026.

Finestra **1024×768**, campo logico **800×600**. La cornice originale
`public/icon/Cornice_gioco.png` circonda il campo, proiettato a **917×688** in
`(52,66)` senza deformazioni. I valori compaiono nei pannelli Livello, Cattura e Vite/Scudi;
score e tempo restano nel bordo inferiore.
Fisica a **60 tick/s** con accumulatore, rendering limitato a **60 FPS** e cattura
cooperativa distribuita su più frame.

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
| Su / Giù nel menu | Selezionano Inizia Campagna, Classifica, Come si gioca, Lingua, Esci |
| Invio | Conferma menu, riepilogo e inserimento nome |
| P | Pausa / ripresa |
| Esc | Pausa durante il gioco; torna al menu dalle schermate della classifica |
| Q | Esce |
| R | Riapre il livello se la fisica è sospesa per uno stato invalido |
| Spazio | Equipaggia uno scudo durante il gioco; conferma i riepiloghi |
| Stick / D-pad | Direzione nel gioco e navigazione del menu |
| A / pulsante 0 | Conferma |
| B / pulsante 1 | Indietro / pausa |
| X / pulsante 2 | Equipaggia uno scudo |
| Start / pulsante 7 | Pausa / ripresa |

- Il movimento continua anche rilasciando la freccia. Una nuova freccia cambia direzione; durante il disegno non è possibile invertire direttamente il senso.
- Il cursore parte sul bordo sicuro. Entrando nel campo non conquistato crea una scia vulnerabile.
- Si muove solo sul confine del territorio conquistato o nel campo libero: non attraversa l'interno sicuro. Il solver verifica tutte le celle e i contatti lungo il percorso. Il confine include gli angoli adiacenti al campo libero, così si può svoltare senza iniziare un taglio.
- La linea deve tornare a un'area sicura. Sono possibili percorsi ortogonali complessi, non soltanto rettangoli.
- La zona separata dal boss viene conquistata; quella raggiungibile dal boss rimane aperta.
- Boss e missili che toccano la scia fanno perdere una vita. Anche un'autointersezione fa perdere una vita.
- Il territorio conquistato assorbe i missili al primo contatto, anche con muri di una cella.
- La perdita del focus mette in pausa; premere P per riprendere. Boss, missili, input di movimento, timer e audio rimangono sospesi durante la pausa.
- L'HUD mostra il tempo simulato del livello. Timer, spari, AI e movimento usano gli stessi tick; la pausa non crea arretrati alla ripresa.
- Si parte con **5 vite**. Una vittoria con **≥74%** di conquista assegna una vita extra, annunciata nei premi e nel riepilogo. Alla morte parte un'esplosione di sette fotogrammi con audio dedicato: il campo resta congelato per **700 ms**, poi si riparte dall'ultimo punto sicuro oppure appare il Game Over.
- La vittoria richiede dal 70% nel tutorial all'86% nel livello 12, configurabile per livello. La percentuale include il bordo iniziale ed è corretta già all'avvio.
- Durante `CAPTURING`, calcolo e rivelazione procedono a blocchi; fisica e timer restano sospesi, mentre eventi e rendering continuano. P sospende/riprende anche la cattura.
- Il player è proporzionato nel box 30×30, centrato sulla cella logica. Il file attuale 1023×1183 produce **26×30**, dimensione condivisa dalla sua **AABB completa**. Sul bordo lo sprite può essere ritagliato dal campo.
- La Scossa conta la permanenza in qualsiasi zona sicura, anche camminando. Nel livello 1 avvisa dopo 8 s e si attiva dopo 12 s: da quel momento il boss spara il doppio più spesso. Nei livelli successivi le soglie si riducono gradualmente. Il taglio sospende il conteggio ma non spegne la pressione; conquista o morte la azzerano.
- Alla Scossa attiva compare una scossa nei livelli 1–4; dal **livello 5 sono due, in versi opposti fissi**. Nel ciclo 1 la velocità cresce da **150 a 260 px/s** e l'attivazione scende da **12 a 7,6 s**. Toccarle costa una vita se non protetti. Il confine segue le conquiste, senza BFS nel tick; le scosse restano sul bordo anche durante un taglio. Pausa e cattura le congelano; conquista, morte e nuovo livello le eliminano.
- Scossa e missili usano `public/icon/shock.png`, orientato nel verso di movimento. La scossa usa sprite nel box 18×18 e corpo 10×10; i missili mantengono sprite nel box 8×8 e corpo 5,2×5,2.
- Una **singola conquista ≥25% dell'intero campo** dà uno scudo: compare `scudo.png` con label al centro. Spazio/X lo equipaggia; un contatto ostile lo consuma, con 500 ms di grazia contro urti duplicati. Il taglio colpito viene annullato e si torna al punto sicuro; l'autointersezione resta fatale. Il pannello **VITE/SCUDI**, per esempio **5/2**, include anche lo scudo equipaggiato finché non viene consumato.
- Dopo il livello 12 si sceglie se **registrare e terminare** o **continuare dal livello 1 in un ciclo più difficile**. Il Run Score somma risultati conclusi e punteggio corrente. Solo il bonus corrente può scadere; quelli consolidati non vengono persi.

## Campagna, menu e salvataggi

Alla vittoria appare un riepilogo con conquista, vite, base, bonus, totale del
livello, tempo e Run Score. Il risultato viene consolidato una sola volta.
Invio/Spazio continua; se si è ottenuta una vita extra o uno scudo nel livello,
la prima conferma chiude il pannello premi e apre il riepilogo. Quando presenti
entrambi, `vita.png` appare sopra e `scudo.png` sotto, con label tradotte.
Il nome per la classifica viene
richiesto al Game Over o scegliendo Registra e termina dopo la campagna.

Continuare un ciclo conserva Run Score, vite e cariche scudo. Campo, timer,
punti/bonus del livello, boss, scia, missili e Scossa vengono reinizializzati;
lo scudo viene riposto. Ogni ciclo aggiunge 15% alle velocità (massimo 200%),
riduce gli intervalli di 10 punti percentuali (minimo 40%) e aggiunge 2 punti
alla soglia di vittoria (massimo 90%). Spari mai sotto 300 ms, Scossa mai sotto
3000 ms. Il calcolo riparte sempre dal profilo base. Una nuova campagna dal
menu riparte invece con cinque vite, zero scudi, zero punti e ciclo 1.

La classifica personale viene creata al primo salvataggio in
`user_data/highscores.json`, esclusa dal versionamento. Conserva dieci risultati,
nomi fino a 16 caratteri, versione del formato e ID campagna. La scrittura usa
un file temporaneo e sostituzione atomica: errori o JSON corrotto non cancellano
automaticamente dati esistenti. Il nome resta nella schermata se il salvataggio
fallisce e Invio consente di riprovare. Non è un salvataggio della partita in corso.

Per il sito **Sons of Art**: [piano di integrazione Web](docs/WEB_RELEASE.md),
[contratto API proposto](web/leaderboard.openapi.json) e [schema PostgreSQL](web/schema.sql).
`BrowserScoreStore` offre lo stesso contratto su storage browser iniettato.
La classifica pubblica richiede il backend: quella locale non è verificata e
non viene inviata automaticamente online. Build Web e API non sono deployate.

## Lingua e controller

`localization.py` usa i cataloghi **locales/it.json** e **locales/en.json** per
menu, HUD, tutorial, suggerimenti e notifiche. Rileva lingua di sistema/UI
Windows, con fallback inglese. Per forzarla impostare `i18n.language` nel
manifest a `it`/`en`, oppure la variabile `UPIX_LANGUAGE`; `auto` usa il rilevamento.
La selezione iniziale avviene all'avvio. L'opzione **Lingua / Language** nel
menu passa immediatamente da IT a EN e viceversa, comprese le label e la cache
dell'HUD, senza ricaricare file. La scelta resta solo in memoria.
Le label stampate nella cornice vengono
sostituite a runtime: l'asset originale non viene modificato.

`controller` configura assi e pulsanti. La deadzone è **0,25**, con rilascio
a **0,18** nella stessa direzione; il cambio di asse richiede nuovamente 0,25.
Sono gestiti collegamento, rimozione e D-pad. Il movimento resta continuo anche
rilasciando lo stick; scollegare un pad ferma la direzione corrente. Le sigle
A/B/X/Start dipendono dal layout: la mappatura numerica è modificabile.
L'inserimento del nome richiede ancora la tastiera. Le verifiche automatiche
simulano il controller; il collaudo sul pad fisico rimane necessario.

## Avvio debug nascosto

Dal Menu Principale: **Segreto**.
Si apre un overlay per scegliere livello **1–12**, vite **1–99** e scudi **0–99**.
Su/Giù seleziona il campo, Sinistra/Destra cambia il valore, Invio/A avvia,
Esc/B annulla. X può sostituire lo Spazio finale sul controller.

I valori valgono soltanto per l'avvio dall'overlay. Inizia Campagna continua a
partire da livello 1, cinque vite e zero scudi. Nessuna configurazione viene
scritta su disco; alla chiusura i valori debug sono eliminati. Sequenza e
limiti sono parametrizzati in `debug_menu` nel manifest.

## Campagna e configurazione

`game_manifest.json` è la fonte di configurazione. `manifest.py` carica e valida
il documento prima di avviare il gioco. `level_config.py` espone profili immutabili per velocità del boss,
sprite, intervallo/velocità dei missili, variazioni di direzione, inseguimento,
soglia di vittoria, chiave del suggerimento, Scossa/punteggio e numero/velocità
delle scosse. Le velocità boss/missili sono pixel logici per
tick a 60 Hz; lo spawn e i cambi direzione usano la stessa magnitudine.

| Livello | Boss px/tick | Missili px/tick | Intervallo base | Conquista |
| --- | ---: | ---: | ---: | ---: |
| 01 | 1,6 | 2,0 | 2400 ms | 70% |
| 02 | 2,0 | 2,3 | 2250 ms | 72% |
| 03 | 2,4 | 2,6 | 2100 ms | 74% |
| 04 | 2,8 | 2,9 | 1950 ms | 76% |
| 05 | 3,2 | 3,2 | 1800 ms | 78% |
| 06 | 3,6 | 3,5 | 1650 ms | 80% |
| 07 | 4,0 | 3,8 | 1500 ms | 81% |
| 08 | 4,4 | 4,1 | 1350 ms | 82% |
| 09 | 4,8 | 4,4 | 1200 ms | 83% |
| 10 | 5,2 | 4,7 | 1050 ms | 84% |
| 11 | 5,6 | 5,0 | 900 ms | 85% |
| 12 | 6,0 | 5,3 | 750 ms | 86% |

Il manifest esplicita i dodici profili senza salto dopo il tutorial. Configura
anche percorsi di primarie/coperture, sprite, cartella musicale, Scossa, score, controlli,
dimensioni, audio, cornice, controlli, menu, localizzazione, scudi, premi e classifica.
I testi sono nei cataloghi, referenziati per chiave. Le modifiche si applicano
al riavvio. Ogni livello usa `boss1.png`–`boss12.png` secondo il manifest.
L'inseguimento dei tagli cresce dal
livello 3; le variazioni di direzione diventano più frequenti. La mira usa la
posizione logica al lancio, poi il missile prosegue rettilineo.

`LevelConfig.shock` usa `ShockConfig`: `enabled=False` disattiva la meccanica,
`warning_ms` e `activation_ms` regolano le soglie, `shot_interval_percent`
regola la cadenza sotto pressione (50 = metà intervallo). Le soglie scendono
da 8/12 s a 5,25/7,6 s. La logica è separata in `shock_system.py`, senza Pygame o tempo
reale. Pausa, cattura e stati terminali congelano conteggio e bonus.

La base del punteggio vale **10 punti per cella di area conquistata**, esclusi
scia e bordo iniziale. Ogni taglio aggiunge al bonus potenziale
`base_taglio × area_taglio / celle_campo`: a parità di area totale, un taglio
ampio premia più tagli piccoli. Il bonus complessivo diminuisce linearmente
con il tempo attivo del livello, fino a zero dopo **180 s nel livello 1** e
**290 s nel livello 12**. I punti base rimangono acquisiti. L'HUD SCORE somma
i risultati dei livelli conclusi e il punteggio corrente, incluso il BONUS
mostrato accanto. Solo il bonus corrente può diminuire; quelli consolidati
alla vittoria restano acquisiti.
`LevelConfig.scoring`/`ScoreConfig` regolano punti, percentuale del bonus e limite;
`area_bonus_percent=0` disattiva il bonus. Il calcolo usa soltanto interi.

La Scossa aumenta il rischio del taglio successivo; i territori sicuri continuano
ad assorbire i missili. L'attesa prolungata riduce anche il bonus disponibile.
La taratura completa richiede playtest sul dispositivo reale.

## Musica dinamica

Musica e tema menu vengono uniformati rispetto al volume percepito di
**02gold.mp3**, usando copie OGG con controllo dei picchi. Gli originali restano
intatti. `audio.normalization` nel manifest regola preparazione, riferimento,
limite di guadagno e cache. Nel sorgente i brani nuovi/cambiati vengono preparati
prima dell'apertura del menu (FFmpeg nel PATH); la prima volta può richiedere
alcuni minuti. Per anticipare il lavoro:

```powershell
.\.venv\Scripts\python.exe audio_normalization.py
```

La release EXE contiene già la cache e non richiede FFmpeg. Il player usa copie
valide senza elaborazioni nel loop e ripiega sugli originali se necessario.
La cache `public/audio_normalized/` è generata e non fa parte dei sorgenti:
la pipeline desktop/web deve prepararla prima del packaging. Gli effetti di
saldatrice ed esplosione conservano il proprio bilanciamento.

Il **livello 1** riproduce sempre **public/music/02gold.mp3** in loop, anche nei
cicli successivi. Il percorso è configurabile in `assets.first_level_music`.
Dal livello 2 torna lo shuffle; il tema già ascoltato viene conteggiato nel giro,
evitando che si ripeta subito. Gli avvii debug da livelli successivi usano lo shuffle.

Nei menu suona **public/sounds/UPix.mp3** in loop, con fade-in di **800 ms**.
Passare fra menu, tutorial, classifica e debug mantiene il brano in corso.
All'avvio normale o debug della campagna, un fade-out di **500 ms** precede
il caricamento del livello: eventi e rendering restano attivi durante la
transizione. Esc può annullarla. Il tema ritorna anche nell'inserimento nome.
Percorso, volume (**0,26**) e durate sono configurabili in `assets.menu_music`
e `audio.menu_music_volume` / `menu_fade_in_ms` / `menu_fade_out_ms`.

All'avvio `MusicShuffle` legge tutti gli MP3 in **public/music**, anche con
estensione maiuscola. Ogni giro riproduce tutti i brani una sola volta; poi
ricarica e rimescola il catalogo, evitando anche la ripetizione immediata fra
due giri se ci sono almeno due file. Con un solo MP3 la ripetizione è inevitabile.
Per aggiungere musica basta copiare il file e riavviare l'applicazione.

Dal livello 2 ogni brano termina naturalmente, senza essere interrotto dal cambio livello.
Playlist e RNG musicale sono separati dalla simulazione. La pausa conserva il
brano; tornare al menu ferma la playlist e ripristina il tema senza svuotare il
sacchetto. I brani casuali della campagna non richiedono nomi nel manifest o nel codice.
Cartella vuota/file corrotti non
bloccano il gioco; la riproduzione non è gapless.

## Audio della saldatrice

L'effetto è attivo **soltanto mentre il cursore traccia nel campo non conquistato**. È spento sul bordo e nelle aree sicure, alla chiusura della linea, alla morte, al cambio livello e all'uscita.

- `public/sounds/saldatrice.mp3`: registrazione originale, mantenuta come fallback.
- `public/sounds/saldatrice.wav`: stessa registrazione preparata per il gioco, con i primi 0,30 s rimossi, guadagno di 6 dB, limitatore e brevi dissolvenze per attenuare i clic.
- Un canale riservato riproduce il loop senza riavviarlo a ogni frame.
- Durante il tracciamento la musica passa da `0.26` a **`0.155`**; alla fine torna a `0.26`. L'effetto usa volume `0.80`. `DRAW_MUSIC_ATTENUATION = 0.105` regola la riduzione musicale; `DRAW_MUSIC_VOLUME` viene calcolato dal volume normale. L'ultima modifica dimezza l'abbassamento precedente, rendendo la musica più udibile durante il disegno.
- I parametri si trovano nella sezione `audio` di `game_manifest.json`. Senza dispositivo audio il gioco continua in silenzio e stampa il motivo.

Per rigenerare il WAV serve **FFmpeg**, non necessario per giocare:

```powershell
ffmpeg -i public/sounds/saldatrice.mp3 -af "atrim=start=0.30:end=8.55,asetpts=PTS-STARTPTS,volume=2,alimiter=limit=0.95:level=false,afade=t=in:d=0.005,afade=t=out:st=8.24:d=0.01" -c:a pcm_s16le public/sounds/saldatrice.wav
```

Se il WAV esiste già, FFmpeg chiede se sovrascriverlo.

## Struttura

```text
Upix/
├── Upqix89.py                # Simulazione, rendering, audio e loop principale
├── application.py            # Menu, riepilogo, finale e inserimento nome
├── campaign.py               # Risultati immutabili e punteggio cumulativo
├── highscores.py             # Classifica JSON atomica e adattatore browser
├── game_manifest.json        # Parametri, asset, controlli e testi
├── manifest.py               # Validazione e configurazione immutabile
├── controls.py               # Controlli simbolici del manifest
├── input_manager.py          # InputFrame, controller/deadzone e hotplug
├── localization.py           # Lingua di sistema, cataloghi e formattazione
├── debug_menu.py             # Sequenza nascosta e avvio configurabile in memoria
├── music.py                  # Catalogo dinamico, shuffle e stream musicale
├── locales/                  # it.json, en.json
├── shields.py                # Cariche, equipaggiamento e grazia a tick fissi
├── collisions.py            # Geometria e solver AABB indipendente (Passi 1A–1B)
├── game_state.py            # Stati, accumulatore 60 Hz e tempo simulato
├── death_sequence.py        # Animazione di morte e durata a tick fissi
├── viewport.py              # Proiezione uniforme del frame logico sulla finestra
├── hud.py                   # HUD esterno al campo, con cache del testo
├── level_config.py          # Configurazioni immutabili dei 12 livelli
├── shock_system.py          # Scossa e cadenza sotto pressione, a tick fissi
├── perimeter_threat.py      # Contorni per segmenti e scossa con collisioni continue
├── sprite_renderer.py       # Sprite orientati con cache delle rotazioni
├── scoring.py               # Punti base e bonus area/tempo deterministico
├── territory.py             # Flood fill scanline cooperativo e piano validato
├── assets.py                # Sfondi SVG e fallback raster al cambio livello
├── README.md
├── REPORT_SVILUPPO.md        # Revisione tecnica e roadmap
├── requirements.txt
├── .gitignore
├── tests/
│   ├── test_game.py          # Regressioni con driver SDL dummy
│   ├── test_collisions.py    # Geometria e solver, incluso muro 200–201 px
│   ├── test_territory.py     # Catture senza modifiche parziali
│   ├── test_game_state.py    # Tick, accumulatore e sovraccarico senza attese reali
│   ├── test_viewport.py      # Proiezione, frame completo e bande
│   ├── test_level_config.py  # Tutorial, missili, aggressività e configurazioni
│   ├── test_shock_system.py  # Soglie esatte, disattivazione e persistenza
│   ├── test_death_sequence.py # Esplosione, audio, freeze e respawn/finale
│   ├── test_lives.py         # Contabilità 15/99 vite e riarmo dopo il respawn
│   ├── test_perimeter_threat.py # Contorni, inseguimento e collisioni sul bordo
│   ├── test_sprite_renderer.py # Rotazione, centratura e cache limitata
│   ├── test_scoring.py       # Bonus per area, tempo e arrotondamenti
│   ├── test_campaign.py      # Menu, intera campagna e riepiloghi
│   ├── test_highscores.py    # Persistenza, errori e storage browser
│   ├── test_manifest.py      # Validazione e configurazioni
│   ├── test_input_manager.py # Joystick simulati, deadzone, azioni e hotplug
│   ├── test_localization.py  # Cataloghi IT/EN, lingua e fallback
│   ├── test_debug_menu.py    # Sequenza, prefissi e limiti di avvio
│   ├── test_music.py         # Scoperta MP3, giri senza ripetizioni e pausa
│   ├── test_player_motion.py # Confine, angoli e movimento senza tunnel
│   ├── test_shields.py       # Soglie, inventario e protezione singola
│   ├── test_advanced_gameplay.py # Premi, doppie scosse, loop e determinismo
│   └── test_assets.py        # SVG, testo, cache e fallback
├── docs/WEB_RELEASE.md       # Strategia di pubblicazione sul sito
├── web/                     # Contratto API e schema SQL proposti
├── tools/
│   ├── benchmark_resolution.py
│   └── benchmark_capture.py  # Budget di cattura e costo CPU del frame completo
└── public/
    ├── assets/              # SVG di copertura e PNG/JPG primarie da svelare
    ├── icon/                # Player, boss1 … boss12, scossa, scudo e cornice
    ├── music/               # MP3 scoperti automaticamente all'avvio
    └── sounds/              # Effetto originale MP3 e WAV preparato
```

`copy_images.ps1` è uno script storico che **copia** i JPG con estensione `.png`: non converte il formato. Pygame li decodifica comunque, ma la pipeline va corretta prima della distribuzione. Nessun asset è stato eliminato.

I due livelli grafici hanno ruoli distinti:

- **Copertura:** `01.svg` … `12.svg`, visibile subito nel campo non conquistato,
  al posto del nero. Rasterizzata solo al cambio livello, con cache limitata,
  gradienti e proporzioni preservate con ritaglio centrato. Le label centrali “Level 1” … “Level 12”
  sono state eliminate dai file SVG; il livello è indicato nell'HUD.
- **Immagine primaria:** `01.png` … `12.png` (fallback `.jpg`), nascosta sotto
  la copertura e scalata uniformemente per riempire il campo, con ritaglio centrato.
  Le catture ne
  svelano le porzioni corrispondenti; alla vittoria viene mostrata interamente.

Se manca l'SVG si usa una copertura neutra. Se manca l'immagine primaria si usa
un'immagine procedurale. I fallback mantengono separati i ruoli: l'SVG non
diventa mai l'immagine da svelare e la primaria non viene esposta in anticipo.
Le primarie 2048×2048 diventano 800×800 e perdono 100 px sopra/sotto per riempire
il quadro logico 800×600: il loro rapporto originale resta coerente. Anche gli SVG
usano la politica di riempimento con ritaglio. I file originali non vengono modificati.

Ogni livello carica lo sprite configurato, preservando alpha e proporzioni nel
box base 96×70, poi applica `boss_render_scale=1.4`: **+40%** rispetto alla
dimensione precedente, con arrotondamento ai pixel interi. Tutti i dodici boss
hanno dimensioni effettive ricavate dal file corrente: tabella nel report.
Il parametro `boss_size` governa sia il rendering sia la **hitbox AABB identica
allo sprite**. Il centro rimane la posizione logica. Se manca l'asset si usa
una primitiva 134×98 con la stessa hitbox.

I proiettili usano `missile_size_scale=1.3`: corpo fisico **5,2×5,2** e raggio
grafico nominale 3,9, arrotondato a **4 px**. Velocità e cadenza restano quelle
del livello; il solver continua a verificare le celle attraversate.
Lo sprite energia riempie un box di diametro 8 px preservando le proporzioni.

`perimeter_threat` nel manifest regola abilitazione, moltiplicatore globale di
velocità, corpo fisico e box grafico; i profili livello definiscono px/s e quantità.
`assets.energy_sprite` sceglie l'asset comune;
`energy_visual` regola rotazione, asse originale, passo angolare e fallback.
Il passo predefinito di 5° limita la cache a 72 rotazioni per taglia.

## Architettura e cattura delle aree

La sezione **level_cover**, nelle prime righe di `game_manifest.json`, regola
la copertura SVG retinata:

```json
"level_cover": {
  "transparency": 0.03,
  "halftone_strength": 0.55,
  "halftone_spacing_px": 4
}
```

`transparency`: **0** nasconde la primaria, **1** la mostra completamente.
Aumentare il valore lascia intravedere di più il quadro.
Subito sotto, **`halftone_strength`** regola quanto è evidente la retinatura:
**0** la disattiva, **0.25** la rende leggera, **0.55** intermedia, **1** più marcata.
`halftone_spacing_px` regola invece la distanza fra i punti.
Riavviare il gioco dopo le modifiche. L'effetto è preparato al caricamento e
riguarda la grafica: griglia, percentuale e collisioni restano indipendenti.
Le aree conquistate mostrano sempre la primaria pulita.

Il campo 800 × 600 px usa celle da 2 px: **400 × 300 = 120.000 celle**. `grid[x][y]` contiene `EMPTY` o `FILLED`; la scia in corso è conservata separatamente.

Alla chiusura della linea, `fill_area()`:

1. Entra in `CAPTURING`, interrompendo subito i tick di recupero e la saldatrice.
2. `CapturePlanner` valida boss e scia e visita la regione raggiungibile dal boss con un flood fill scanline, usando flag compatti e intervalli verticali.
3. Verifica che il piano lasci libero l'intero boss. Un contatto fa perdere una vita; un errore geometrico sospende la fisica. La griglia attiva rimane intatta.
4. Prepara una copia di griglia/canvas, rivelando la primaria per strisce; completa con uno scambio di riferimenti e aggiorna percentuale/punteggio una sola volta.

Il flood fill inverso è adatto alle forme concave, purché il boss sia in una cella libera valida e le collisioni mantengano questo vincolo. **Non garantisce da solo che il boss non attraversi muri**. Con più boss occorrerà definire le regole e, se devono restare tutti in gioco, conservare l'unione delle regioni raggiungibili da tutti i boss attivi.

Il budget cooperativo è **4 ms/frame**, con quanti di 128 celle e un limite di
256 quanti per frame. Anche copia delle colonne e rivelazione sono distribuite;
si usa un blit per intervallo, evitando un blit per cella. Il rendering mostra la
preparazione progressiva e una scia pulsante durante la chiusura. Il commit usa
conteggi incrementali, senza una nuova scansione completa della percentuale.
`plan_capture()` resta un wrapper sincrono per test e strumenti, non per il loop.

I Passi 1B e 1C collegano il solver al movimento del boss: corpo AABB float
dimensionato come lo sprite, substep di massimo 1 px per asse, scansione dell'intero segmento,
rimbalzi sull'asse d'impatto e consumo del residuo. Il test sul muro
x=200–201 px passa anche nel runtime. Il solver non legge timer o casualità.
I missili usano lo stesso contratto di substep e la stessa geometria di griglia,
con primo contatto sul segmento rettilineo e assorbimento senza rimbalzi.

`Game.advance_frame()` usa `FixedTimestep` per eseguire zero o più aggiornamenti
a **60 Hz**, poi il loop disegna e presenta una sola volta. Il credito residuo
è conservato in unità intere, senza deriva float. `SimulationClock` conta i tick
eseguiti e governa anche AI, spari e HUD. Il generatore casuale è locale al gioco
e iniettabile per ripetere una simulazione con seme e input identici.

`Hud.game_area` descrive l'apertura della cornice, misurata sull'asset originale
1448×1086. `Viewport` vi inscrive il frame logico a `(52, 66, 917, 688)` nella
finestra 1024×768, usando un buffer riutilizzato. La cornice RGBA e i valori HUD
sono composti dopo il campo. Restano piccoli margini laterali neri nell'apertura
per mantenere il 4:3 senza tagliare celle. `RENDER_FPS_LIMIT = 60`
limita la presentazione; la fisica mantiene il suo accumulatore indipendente.

Pausa, morte, stati terminali e cambio livello azzerano l'accumulatore. Il budget di
recupero è di 8 tick/frame: dopo stalli più lunghi si scarta il debito intero
eccedente, diagnosticato da `dropped_ticks`, senza ingrandire il passo fisico.
In sovraccarico la simulazione rallenta rispetto al tempo reale. `CAPTURING`
ferma il tempo simulato e azzera gli arretrati all'uscita; nessun recupero del
tempo speso a pianificare la conquista.

Dopo il respawn occorre rilasciare la direzione (tastiera, D-pad o stick al
neutro) prima di premere di nuovo per ripartire. Un avviso IT/EN lo segnala:
il tasto mantenuto non può consumare altre vite riaprendo subito lo stesso
taglio. Boss, timer e Scossa restano attivi durante l'attesa. Il pannello
`VITE/SCUDI` mostra nell'ordine le vite residue e gli scudi disponibili.

Gli stati `PLAYING`, `DYING`, `CAPTURING`, `PAUSED`, `LEVEL_CLEAR`, `GAME_OVER` e `PHYSICS_ERROR`
sono espliciti. `game_over` e `win` sono proprietà derivate dallo stato.
La pausa sospende canali e musica senza riavviare i campioni alla ripresa.
`CampaignApp` coordina inoltre `MENU`, `TUTORIAL`, `HIGHSCORES`, `NAME_ENTRY` e
`CAMPAIGN_COMPLETE`, creando la simulazione solo all'avvio della campagna.

`DeathSequence` governa esclusivamente la presentazione durante `DYING`:
sette fotogrammi da 100 ms, con fisica, tempo e bonus congelati. La vita viene
scalata una sola volta dopo l'avvio della sequenza/audio; anche l'ultima morte
attende il settimo frame prima del Game Over. P e perdita del focus sospendono
anche l'esplosione. `assets.death_frames` e `assets.death_sound` scelgono gli
asset; `death_sequence.frame_duration_ms`, `sprite_scale` e `sound_volume`
regolano durata, scala relativa al player e volume. Il MP3 può terminare
naturalmente dopo la fine dell'animazione; la musica riprende al respawn/finale.

## Verifiche

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

I **279 test** coprono normalizzazione/cache, finale New Game Plus, persistenza
della release, geometria/solver, missili continui, stati/pausa, timer,
cattura, audio, respawn, vittoria,
progressione, le 12 coppie copertura/immagine primaria senza label, cache, rendering
del boss e fallback. Una regressione con SVG e PNG di colori distinti verifica
copertura iniziale, rivelazione e schermata di vittoria.
I test geometrici e della conquista non richiedono Pygame.
Le nuove regressioni confrontano lo stato completo a 30/60/144 FPS con seme e
input fissi, inclusi gli urti sul muro x=200–201 px. Sono verificati accumulatore,
assenza di deriva, sovraccarico, proiezione e loop reale con eventi sintetici.
Le nuove verifiche includono parametri dei tre livelli, traiettoria del missile,
inseguimento del boss, cattura a budget diversi, confronto con una BFS di
riferimento su 25 campi frammentati, commit unico, pausa/cancellazione e HUD esterno.
Sono inoltre verificati soglie e cadenza della Scossa, reset/disattivazione,
premio dei tagli ampi, scadenza del bonus, sprite player centrato con AABB completa,
soglie di vittoria e spari di tutti i 12 livelli, e determinismo con
Scossa attiva e bonus a 30/60/144 FPS.
Sono verificati anche il menu iniziale, il Run Score senza accrediti duplicati,
la campagna completa, i riepiloghi, la classifica JSON con scrittura atomica,
errori e retry, l'adattatore browser e la validazione del manifest.
La scossa è verificata su contorni concavi, contatti diagonali e 25 griglie
frammentate, con collisioni continue ai corner, perdita di una sola vita,
reset dopo conquista, sospensione e determinismo a FPS diversi. Fixture
asimmetriche verificano orientamento e centratura degli sprite.
Le nuove regressioni coprono anche input/controller, i18n, frontiere con angoli,
vita extra al 74%, scudo al 25%, due scosse in versi opposti, contatto protetto,
persistenza di 13 risultati nel JSON e confronto a FPS diversi con due scosse
e consumo dello scudo. Nessuna lettura dei dispositivi fisici nel tick.
Sono verificati anche sequenza debug, reset degli avvii personalizzati,
shuffle completo senza ripetizioni, premi combinati e cambio lingua a caldo
con cache HUD invalidata senza rileggere immagini.

Usano driver SDL `dummy`: controllano mixer e segnale del WAV, **non l'ascolto dagli altoparlanti**. Non certificano l'assenza dei problemi aperti né sostituiscono una partita completa con audio reale.

Per confrontare le risoluzioni senza cambiare la configurazione del gioco:

```powershell
.\.venv\Scripts\python.exe tools/benchmark_resolution.py --repeats 5 --resolutions 800x600 1024x768
```

Per misurare i singoli frame della cattura con rendering e HUD:

```powershell
.\.venv\Scripts\python.exe tools/benchmark_capture.py
```

Eseguirlo separatamente dalla suite di test. È disponibile anche il profilo
`1024x1024`. Il benchmark varia la **griglia logica**. Il gioco ora usa la finestra
**1024×768** con griglia **800×600**: non aggiunge celle alla BFS. Una futura griglia
logica 1024×768 richiederebbe il 63,84% di celle in più, un nuovo controllo del
budget di cattura e un collaudo del bilanciamento.

## Repository

Il `.gitignore` esclude cache Python, ambienti virtuali, build, log, file degli editor, configurazioni private e salvataggi. Gli asset runtime e i test devono essere versionati. Le esclusioni locali di `Documenti` e `start.bat` aggiunte durante la revisione sono state rispettate.

**Tutti i comandi e le operazioni Git sono riservati all'utente**, inclusi i
controlli di sola lettura. Questa regola è conservata anche in `AGENTS.md`.
L'assistente modifica codice e documentazione ed esegue le verifiche applicative.
