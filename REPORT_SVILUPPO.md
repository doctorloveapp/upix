# UPIX 1989 — Stato tecnico e piano di sviluppo

Aggiornamento: **8 novembre 2026**. Ruolo operativo: Senior Game Engine Developer
e Technical Lead. Obiettivo: consolidamento verso Release Candidate.

## Regole vincolanti e stato attuale

- **Tutte le operazioni Git, anche di sola lettura, sono riservate all'utente.**
  Nessun comando Git eseguito in questo task. Regola conservata in `AGENTS.md`.
- Il piano generale è approvato. **Collisioni Fase 1 estese ai missili**;
  Fase 2 con stati, pausa, **tempo fisso 60 Hz e cattura cooperativa implementati**.
  Completata la **vertical slice dei primi tre livelli**, con parametri e sprite distinti.
  **Fase 4 implementata**: player 2×, Scossa separata e punteggio area/tempo.
  **Fase 5 implementata**: Run Score, riepilogo e finale della campagna.
  **Fase 6 desktop implementata**: menu iniziale e classifica personale persistente.
  Implementati controller/deadzone, i18n IT/EN, dodici boss distinti, hitbox player
  completa, movimento sulla frontiera, scudi, vite extra e cicli di difficoltà.
  Port browser e classifica pubblica sul backend sono progettati, non deployati.
  Il collaudo esteso da Release Candidate e gli altri interventi della roadmap
  restano aperti.
- Campo logico **800 × 600 px**, celle di 2 px, griglia **400 × 300**.
  Finestra **1024 × 768 px**, cornice `public/icon/Cornice_gioco.png` e campo
  **917 × 688 px** in `(52, 66)`, scala uniforme con arrotondamento raster.
  Rendering limitato a 60 FPS. Valori HUD nei pannelli originali della cornice.
- Ogni livello usa il proprio `boss1.png`–`boss12.png`: box base **96×70**,
  **scala 1,4**, alpha e proporzioni preservate. `boss_size` governa insieme
  sprite e AABB identica. Dimensioni correnti nella tabella della nuova consegna.
- **Copertura SVG visibile all'avvio**, **immagine primaria PNG/JPG svelata
  dalla conquista**: ruoli separati per tutte le dodici coppie di asset.
  Entrambe usano scala uniforme e ritaglio centrato, senza deformare le immagini.
- **Spari diretti al player in tutti i livelli**, più lenti e meno frequenti
  all'inizio: da **2 px/tick ogni 2400 ms** a **5,3 px/tick ogni 750 ms**.
  Boss da 1,6 a 6 px/tick; conquista dal 70% all'86%. La curva sostituisce
  i precedenti 1900/1800/1700 ms e la velocità missile uniforme di 5 px/tick.
- **Player proporzionato nel box 30×30**, centrato sulla cella logica; AABB
  **uguale allo sprite**. File attuale 1023×1183, reso e collidente a **26×30**.
  L'ancora naviga soltanto sul confine sicuro o nelle celle libere; non può
  attraversare l'interno conquistato. **5 vite**, vita extra con vittoria ≥74%,
  **scudo per singola conquista ≥25% del campo**; Spazio/X per equipaggiarlo.
  **Proiettili al 130%**: AABB **5,2×5,2**, raggio nominale 3,9 arrotondato a 4 px.
  **Scossa** configurabile: preavviso e dimezzamento dell'intervallo spari dopo
  permanenza prolungata in zona sicura, più **una scossa nei livelli 1–4 e due
  in versi opposti nei livelli 5–12**; velocità da 150 a 260 px/s nel ciclo 1.
  Attivazione da 12 a 7,6 s. Conquista/morte le disinnescano; scudo assorbe un contatto.
  Scossa e missili usano `public/icon/shock.png`, orientato nel verso del moto.
  **SCORE/BONUS/TEMPO** nell'HUD: base permanente e bonus di area che scade.
- Musica normale **0,26**, musica durante il disegno **0,155**, effetto saldatrice
  **0,80**. L'ultima richiesta dimezza la riduzione precedente, da 0,21 a 0,105:
  la musica è quindi più udibile durante il disegno. Costante dedicata
  `DRAW_MUSIC_ATTENUATION = 0.105`; il volume attenuato è calcolato da quello normale.
- Menu con cambio lingua IT/EN immediato, overlay debug nascosto con avvio
  personalizzato solo in memoria; premi vita/scudo mostrati insieme a fine livello.
- Morte con stato temporaneo **DYING**, sette fotogrammi di esplosione e audio
  dedicato; fisica e tempo congelati per **700 ms**, poi respawn o Game Over.
  Il rilascio della direzione resta richiesto dopo il respawn.
- Musica scoperta da `public/music` all'avvio, shuffle senza ripetizioni nel
  giro e alla giunzione fra giri, con RNG separato dalla simulazione.
- **248 test superati**, compresi animazione di morte, contabilità vite/respawn, debug, shuffle, lingua a caldo, premi combinati,
  input/controller, i18n, frontiera, scudi,
  vite extra, salvataggio oltre 12 livelli, scossa, contorni frammentati, sprite orientati,
  menu, campagna completa, classifica JSON/browser,
  manifest, nuove dimensioni, Scossa, punteggio, progressione dei dodici livelli,
  AABB player completa, configurazioni, cattura a budget diversi,
  cancellazione/pausa, HUD esterno, loop, determinismo a FPS diversi e collisioni.
  Verifica visiva IT/EN di menu, tutorial, gioco, premio scudo, riepilogo e finale.
  La diagnostica storica di 3.000 movimenti riguardava il vecchio corpo:
  non viene presentata come collaudo esteso del nuovo boss.
- Ambiente verificato: Windows, Python **3.13.5**, Pygame **2.6.1**,
  `resvg_py` **0.5.0**. Dipendenze dichiarate in `requirements.txt`.

## Consegna corrente — Scossa/Shock e DeathSequence (8 novembre 2026)

### Nomenclatura unificata

La meccanica anti-attesa si chiama **Scossa** in italiano e **Shock** in inglese.
Aggiornati preavviso, avviso attivo sul campo/HUD, tutorial, suggerimenti, sorgenti,
test, README, report e documentazione web. Il modulo è ora `shock_system.py`,
con `ShockSystem` e `ShockConfig`; `Game.shock`, `LevelConfig.shock`, i record
`levels[].shock`, `minimum_shock_ms` e le chiavi i18n `shock_warning`/`shock_active`
usano la stessa nomenclatura. Tutti i consumatori interni sono stati aggiornati
insieme, senza alias duplicati. Nessun parametro di difficoltà è stato variato.

Rinominato anche lo sprite energia condiviso in **public/icon/shock.png**,
con aggiornamento del manifest e delle regressioni: contenuto grafico invariato.
Il manifest distribuito è la versione da usare con il codice aggiornato; anche
eventuali profili esterni devono rispettare le nuove chiavi. Il fingerprint del
manifest viene ricalcolato automaticamente, come per ogni variazione della configurazione.

### Macchina a stati della morte: codice implementato

Flusso: **PLAYING → DYING → PLAYING oppure GAME_OVER**. `handle_death()`
memorizza il centro logico dell'impatto, avvia `DeathSequence`, entra in `DYING`,
sospende musica/saldatrice, riproduce l'esplosione e soltanto dopo decrementa
una vita. La guardia sullo stato rifiuta contatti ripetuti durante la sequenza:
un'unica esplosione, un unico avvio audio, un unico decremento. Con l'ultima
vita il contatore arriva a zero in DYING; la schermata Game Over e l'inserimento
del nome attendono la conclusione dell'animazione.

`death_sequence.py` contiene una macchina temporale indipendente da SDL,
fisica e RNG. Il normale accumulatore viene azzerato alla transizione e durante
DYING avanza esclusivamente i tick di presentazione dell'esplosione. Il clock
del livello non avanza: boss, proiettili, scossa, scudi, scia, bonus e tempo
restano fermi. Scia ed entità sono mantenute visibili, senza pulizia anticipata.
Alla fine del settimo fotogramma `_finish_death()` esegue un solo commit:
annulla il taglio, rimuove missili/scosse, ripristina lo stato degli scudi,
quindi torna all'ultimo punto sicuro oppure entra in Game Over.

L'uscita da DYING azzera nuovamente il credito: nessun recupero del tempo speso
nell'esplosione. Dopo il respawn rimane la protezione introdotta nell'audit vite:
rilasciare la direzione e premere di nuovo per muoversi. Da quel momento il mondo
avanza normalmente, anche mentre il player attende il rilascio.

P o perdita del focus sospendono anche l'animazione e il suo audio; riprendere
torna allo stesso fotogramma, senza riavviare il campione. Menu, chiusura e
inizializzazione di un nuovo quadro annullano eventuali sequenze pendenti.

### Asset, scala e audio

I sette file **cursor_lukso_death1.png … cursor_lukso_death7.png** vengono
precaricati all'avvio del Game. Nessuna lettura di file o trasformazione grafica
avviene al momento dell'impatto. `load_animation_frames()` calcola un fattore
uniforme dal primo fotogramma e dalle dimensioni effettive del player (**26×30**),
applicandolo all'intera sequenza: alpha e proporzioni restano corretti e
l'espansione originale non viene annullata ridimensionando ogni frame nello
stesso box. Il primo fotogramma misura **25×30**, il più ampio **33×36**.
Il centro è sempre quello logico dell'impatto; nelle collisioni durante un passo
del player viene passata la cella del contatto. Il cursore normale è nascosto e
l'esplosione è composta sopra le altre entità congelate. Le AABB attive restano
quelle degli sprite di gioco: l'animazione non introduce un nuovo corpo fisico.

Configurazione centralizzata nel manifest:

- `assets.death_frames`: elenco ordinato dei sette PNG.
- `assets.death_sound`: **icon/death_sequence/esplosione.mp3**.
- `death_sequence.frame_duration_ms`: **100 ms**, cioè 6 tick per fotogramma
  a 60 Hz; totale **42 tick / 700 ms**. Per durate non allineate al tick si
  arrotonda per eccesso, senza abbreviare l'ultimo frame.
- `death_sequence.sprite_scale`: **1,0**, moltiplicatore della scala del player.
- `death_sequence.sound_volume`: **0,85**.

Canale 0 riservato alla saldatrice, canale 1 all'esplosione. Il suono parte
all'ingresso in DYING, una sola volta, senza dipendere dal rendering. La musica
è sospesa per tutta l'animazione e riprende all'uscita. Il campione MP3 dura
circa **2,116 s** e può terminare naturalmente dopo il respawn: la pausa di gioco
segue la durata configurata dei sette frame, senza dipendere dal dispositivo audio.
Una nuova morte sostituisce il suono sullo stesso canale; menu e nuovo quadro
lo fermano. Asset mancanti o corrotti producono diagnostica e fallback visivo
per lo stesso numero di frame; audio assente mantiene invariata la sequenza.

### Verifiche e limiti

**248 test superati in 76,855 s** con
`.venv\Scripts\python.exe -m unittest discover -s tests -q`.
Aggiunti **15 test**, di cui dodici nel nuovo `tests/test_death_sequence.py`.
Verificati tutti i sette indici e durata completa dell'ultimo frame, inizio
sequenza/audio prima del decremento, contatto ripetuto senza perdite aggiuntive,
zero vite senza Game Over anticipato, congelamento di entità/clock/bonus/RNG,
pausa/ripresa, reset dell'accumulatore, cancellazione al menu/nuovo livello,
scala condivisa e centro, fallback asset, validazione manifest e nomenclatura IT/EN.
La morte a **30/60/144 FPS** mostra tutti i frame e lo stesso stato finale.
Controllati visivamente i sette frame (ingranditi per ispezionare alpha e
proporzioni) e la composizione dell'esplosione nel viewport **1024×768**.
Le regressioni precedenti sulle vite sono adeguate alla transizione temporanea:
prima verificano DYING, poi attendono la conclusione prima di controllare il respawn.

La durata è deterministica in tick; sotto stalli oltre il budget il motore
scarta il debito eccedente come per la fisica, quindi la presentazione può
durare più a lungo nel tempo reale. Nessun test dummy certifica ascolto,
latenza hardware o fluidità sul monitor. Le fasi completate restano confermate;
questa consegna implementa il feedback di morte e la nomenclatura per la release.
Nessuna operazione Git eseguita.

## Consegna precedente — Audit vite e correzione respawn (8 novembre 2026)

Sezione storica: descrive il respawn immediato allora implementato. La consegna
Scossa/Shock e DeathSequence aggiunge ora l'intervallo congelato DYING prima del
respawn; contabilità vite e requisito di rilascio restano validi.

### Problema riprodotto e causa

Segnalazione: campagna debug con 15 vite, Game Over percepito dopo circa dieci
morti. L'audit ha seguito `StartSettings` → `CampaignApp` → `Game.lives`, tutte
le sorgenti di danno, ricompense, cambio livello/ciclo, HUD e ingresso nella
schermata di registrazione del punteggio.

**Non è emerso un limite a dieci morti né una conversione da 15 a 5 vite.**
Il difetto riprodotto è il consumo di più vite durante un unico input mantenuto:
il boss tangente al bordo sicuro colpisce appena si tenta un nuovo taglio;
`handle_death()` azzera il movimento ma `_update_player()` lo riattiva dal tasto
ancora premuto. La morte non interrompeva neppure il recupero dell'accumulatore,
perciò più respawn e collisioni potevano avvenire prima di un solo rendering.

Riproduzione deterministica: 15 vite, boss fermo e geometricamente valido appena
sopra il punto di rientro, SU mantenuto, frame da 100 ms. Risultati misurati:

| Tempo reale | Tick nel frame prima | Vite prima | Tick nel frame dopo | Vite dopo |
| --- | --- | --- | --- | --- |
| 100 ms | 6 | 9 | 1 | 14 |
| 200 ms | 6 | 3 | 6 | 14 |
| 300 ms | 3, poi Game Over | 0 | 6 | 14 |

Questa è una causa verificata di morti apparentemente mancanti; non è disponibile
una registrazione della specifica partita segnalata, quindi non se ne attribuisce
con certezza assoluta ogni evento a questo scenario.

### Correzione effettivamente implementata

- Ogni morte azzera `frame_clock`: il cambio di posizione interrompe i tick
  arretrati del frame, come già accade per pausa e cambio stato. Non viene
  azzerato il tempo del livello; viene scartato il credito reale precedente
  al respawn, senza recuperarlo nel frame successivo.
- `_respawn_waiting_for_release` richiede un input direzionale neutro dopo la
  morte, quindi una nuova direzione per ripartire. Mantenere o cambiare direzione
  senza rilascio non riapre un taglio. Il controllo usa `InputFrame`, oppure
  l'adattatore tastiera esistente; sul controller il neutro segue la deadzone
  dell'InputManager. Nessuna lettura hardware nel tick fisico.
- Il requisito di rilascio riguarda soltanto il movimento del player: boss,
  proiettili, tempo e Scossa continuano ad avanzare. La scossa può ancora
  colpire un giocatore fermo sul bordo; il respawn non introduce invulnerabilità.
- Avviso visibile IT/EN sul campo: rilasciare la direzione e premere di nuovo.
  La pausa conserva il requisito; `start_level()` lo elimina per il nuovo quadro.
- `_handle_hostile_contact()` ora rifiuta chiamate fuori da `PLAYING`, evitando
  anche di consumare scudi in stati sospesi o terminali.
- La diagnostica delle vite stampa anche l'ultimo decremento a zero.

### Esito dell'audit del sistema vite

1. **Avvio:** le vite debug sono applicate prima di caricare il livello, senza
   limite nascosto al valore normale di cinque. Validazione iniziale 1–99;
   questo limite appartiene al menu debug, non alle ricompense durante il run.
2. **Danni:** unico decremento in `handle_death()`, una vita per chiamata valida.
   Boss, missili, scossa, autointersezione e contatto rilevato alla cattura
   confluiscono in quel percorso. I chiamanti interrompono subito il tick al
   danno; missili e scosse vengono rimossi al respawn, scia e audio puliti.
3. **Scudi:** inventario distinto dalle vite. Uno scudo equipaggiato assorbe il
   contatto ostile e consuma una carica; la morte mantiene le cariche non usate.
   L'autointersezione resta un errore strutturale non assorbibile.
4. **Premi e continuità:** vittoria con conquista ≥74% assegna una vita una sola
   volta per coppia ciclo/livello. Le vite residue proseguono nei livelli e cicli
   successivi; nessun ripristino automatico a cinque a ogni livello.
5. **HUD e finale:** `HudData.lives` legge il contatore autorevole, senza copie
   del valore iniziale. Il pannello mostra **vite/scudi**: `5/0` significa cinque
   vite, zero scudi. L'app apre l'inserimento nome quando il motore entra in
   `GAME_OVER`, che il percorso di morte imposta soltanto a zero. Ulteriori
   contatti dopo il finale non portano il contatore sotto zero.

### Verifiche e stato della consegna

Aggiunti **12 test**: undici in `tests/test_lives.py` e uno nel percorso completo
del menu/campagna. I test di regressione sono stati eseguiti prima della modifica:
tre fallivano per recupero multiplo, input mantenuto e adattatore tastiera;
dopo la correzione superano il controllo.

Verificati 15 → 5 dopo esattamente dieci collisioni reali distinte, Game Over
soltanto alla quindicesima, contatore zero stabile dopo il finale, avvio dal
vero overlay debug con 15 vite e ingresso nella registrazione soltanto alla
quindicesima morte; inoltre decrementi da 99, premio al 74% senza duplicati,
continuità al cambio livello, scudi separati, pausa, stati sospesi, riarmo
tastiera/controller, pericolosità della scossa durante l'attesa e input
mantenuto a 30/60/144 FPS. I test preesistenti coprono le singole sorgenti di
danno, cattura, cicli, collisioni e determinismo della simulazione.

Suite completa: **233 test superati in 115,355 s** con
`.venv\Scripts\python.exe -m unittest discover -s tests -q`.
Controllata visivamente la composizione
1024×768 con avviso e HUD IT/EN usando i driver SDL dummy. Il collaudo fisico
del controller e una sessione prolungata sul dispositivo reale restano da
eseguire. Nessun comando Git eseguito. Le fasi già completate rimangono tali;
questa consegna corregge una regressione del respawn, senza cambiare bilanciamento,
hitbox o soglie.

## Consegna precedente — Bilanciamento, debug, premi e shuffle (8 novembre 2026)

### Vita extra al 74% e premi combinati

`progression.extra_life_percent` passa da **76 a 74**. La verifica resta
inclusiva e una sola volta per coppia ciclo/livello: 73,999% non basta, 74% sì.
Tutorial e riepilogo formattano la soglia dal manifest, senza copie nel codice.
Non sono state cambiate le soglie di vittoria dei dodici profili.

Nuovo riferimento `assets.life_sprite = icon/vita.png`, caricato e proporzionato
nel box dei premi, con alpha preservato. Dopo LEVEL_CLEAR viene congelata anche
la presentazione dei premi: **vita.png sopra**, **scudo.png sotto**, entrambi
centrati con label IT/EN se vita extra e scudo sono stati ottenuti nello stesso
livello. È mostrato anche il caso di un solo premio. Per gli scudi si usa il
totale guadagnato nel livello, anche se l'avviso durante il gioco è già scaduto
o la carica è stata consumata: la label parla di scudi ottenuti, non disponibili.

`level_rewards_pending` separa la conferma del pannello finale dal timer
dell'avviso scudo durante il gioco. Invio/Spazio/A apre il riepilogo, una seconda
conferma avanza. Rendering e conferma non assegnano premi: punti, vita e scudi
rimangono quelli del commit e di `LevelResult`, senza accrediti duplicati.

### Sequenza nascosta e overlay debug

Dal **solo Menu Principale** premere:
**SU, GIÙ, SINISTRA, DESTRA, SU, SU, SPAZIO**.
La sequenza viene elaborata prima della normale navigazione. Tastiera e azioni
controller sono normalizzate dall'InputManager; X, associato allo scudo, può
sostituire lo Spazio finale. Un evento marcato come ripetizione non avanza il
codice. Entrare in altre schermate, avviare una campagna o perdere il focus
impedisce di completare una sequenza rimasta parziale fuori dal menu.

Nuovo **debug_menu.py**:

- `CheatSequence`: riconoscitore con tabella dei prefissi; un errore conserva
  soltanto il suffisso che può essere l'inizio di una nuova sequenza. Non sono
  accettate sequenze incomplete o con il tasto finale sbagliato.
- `StartSettings`: dataclass immutabile e validata, usata per l'avvio del Game.
  Livello 1–12, vite 1–99, scudi 0–99; massimi e sequenza nel manifest.
- `DEBUG_MENU`: overlay con pannello opaco, menu sottostante oscurato e tre
  campi. Su/Giù seleziona il campo; Sinistra/Destra cambia il valore con limiti;
  Invio/A avvia immediatamente; Esc/B annulla e torna al menu.

I parametri vengono applicati **prima del primo start_level()**, evitando di
caricare il livello 1 per poi sostituirlo. Il run parte con ciclo 1 e score zero.
I valori appartengono all'istanza di `CampaignApp`, non sono scritti sul manifest,
nelle traduzioni o in un salvataggio di configurazione. L'avvio normale dal menu
usa sempre livello 1, cinque vite e zero scudi, anche nella stessa sessione.
`close()` elimina i valori debug; un nuovo processo riparte dalle impostazioni
normali. Il normale salvataggio della classifica locale non è stato modificato.

### Musica dinamica e shuffle senza ripetizioni

Nuovo **music.py**, con responsabilità distinte:

1. `MusicShuffle` enumera con **Path.iterdir()** la cartella configurata
   `public/music` all'avvio dell'applicazione. Accetta file MP3 anche con estensione
   maiuscola; ignora cartelle e altri formati. Nessun elenco di nomi o legame
   livello/brano nel sorgente o nei profili del manifest.
2. Il catalogo ordinato viene mescolato con un **Random indipendente** e consumato
   tramite deque. Ogni brano compare una volta per giro. Solo a sacchetto vuoto
   viene ricaricato l'intero catalogo; se il primo elemento coincide con l'ultimo
   precedente, viene scambiato con un altro. La ripetizione immediata è quindi
   evitata anche tra giri, salvo il caso inevitabile di un solo MP3.
3. `MusicPlayer` gestisce l'unico stream SDL. Usa `play()` senza loop infinito;
   alla fine naturale sceglie il prossimo brano. Il polling avviene nel **frame
   loop**, mai nel tick fisico. Il cambio livello e il nuovo ciclo conservano
   il brano corrente: non vengono troncati i brani per consumare la playlist.
4. Il player è condiviso per tutta la sessione. Tornare al menu ferma lo stream,
   conservando il sacchetto; la campagna successiva prende il brano seguente.
   Chiudere il processo elimina anche la playlist in memoria. I file aggiunti
   durante una partita vengono rilevati al successivo avvio dell'applicazione.
5. In pausa non viene interpretato `get_busy() == False` come fine brano.
   Ripresa e attenuazione durante il disegno restano quelle precedenti; quando
   cambia traccia il volume viene risincronizzato nello stesso frame. Cartella
   vuota/audio assente lasciano il gioco silenzioso; file illeggibili vengono
   saltati, con tentativi limitati al catalogo, senza ciclo infinito se sono tutti
   corrotti. Diagnostica nel log, nessuna eccezione audio blocca la simulazione.

Rimosse le associazioni `LevelConfig.music`, i nomi per livello e `MUSIC_TRACKS`.
Restano configurabili cartella, estensione MP3, volume e attenuazione. La scansione
non viene ripetuta nel frame loop; la decodifica/caricamento avviene soltanto
al cambio effettivo del brano. Non è una riproduzione gapless/crossfade.
Riferimento primario: [pygame.mixer.music](https://www.pygame.org/docs/ref/music.html),
in particolare il comportamento di get_busy() durante la pausa.

### Cambio lingua immediato

Il Menu Principale ha ora **Lingua: IT → EN / Language: EN → IT**.
`Localizer.set_language()` e `toggle()` cambiano il catalogo attivo in memoria,
senza rileggere i JSON o ricreare il Game. Le schermate, i suggerimenti e i
premi usano lo stesso oggetto I18N condiviso e cambiano immediatamente.

L'HUD rileva il cambio anche se HudData è identico: ricompone label della
cornice e footer dalla copia neutra già in memoria, invalidando la cache del
testo. Nessuna rilettura del PNG, modifica all'apertura del campo o perdita
dello stato di gioco. Non viene salvata una preferenza linguistica: al prossimo
processo valgono nuovamente lingua di sistema, variabile ambiente o manifest.

### Verifiche della consegna

**221 test superati** con `.venv\Scripts\python.exe -m unittest discover -s tests -q`
in **56,256 s**. Baseline 207 più **14 nuove regressioni**: sequenza/impostazioni
(3), musica (6), integrazione menu/debug/premi/lingua (4), cache HUD a caldo (1).
Dopo la rifinitura grafica del pannello debug sono stati ripetuti con successo
i **13 test di campagna/menu**.

Copertura nuova: riconoscimento esatto, errore e prefissi sovrapposti, sequenza
solo nel menu e reset con focus perso; avvio livello 12 con 7 vite/3 scudi;
successivo avvio normale e chiusura senza modificare i byte del manifest;
scoperta di un MP3 aggiunto, estensioni miste, catalogo vuoto/singolo/doppio;
20 giri per ciascuno di dieci semi senza duplicati o ripetizioni alla giunzione;
nessun consumo del RNG globale; pausa e fine naturale tramite mixer simulato;
uscita limitata con catalogo interamente corrotto; entrambi gli sprite dei premi
visibili nell'ordine corretto, senza mutazioni del punteggio; cambio lingua con
HudData invariato e caricamento immagini vietato durante il cambio.

Verificati visivamente menu IT/EN, overlay debug e premi combinati con gli asset
reali tramite SDL dummy. Restano superate regressioni fisiche, AABB, pause,
scudi, catture, JSON e determinismo 30/60/144 FPS. L'ascolto reale e il comportamento
del caricamento MP3 su dispositivi lenti richiedono collaudo sul dispositivo;
non è stato pubblicato nulla sul sito. Nessuna operazione Git.

## Storico — Gameplay avanzato, controller e i18n (8 novembre 2026)

Questa sezione conserva la consegna precedente. La soglia 76%, l'assenza del
cambio lingua a caldo e le associazioni musicali di livello sono superate
dalla consegna corrente.

### InputManager e controller

Nuovo **input_manager.py** con `InputManager` e `InputFrame` immutabile.
`CampaignApp` normalizza tastiera, assi analogici, D-pad e pulsanti in azioni
logiche; acquisisce una direzione per frame e la passa invariata ai tick di
recupero. La simulazione non legge dispositivi fisici: input assente significa
frame neutro. Rimane un adattatore per i dizionari di tasti usati dai test storici.

Deadzone di ingresso **0,25**, rilascio **0,18**: l'isteresi mantiene solo la
direzione già attiva, un cambio di asse/verso deve superare nuovamente 0,25.
L'asse dominante produce movimento ortogonale; nessuna diagonale. Lo stick
neutro non avvia né cambia direzione. Come la tastiera, rilasciare il comando
conserva il movimento arcade continuo già esistente.

`pygame.joystick` gestisce connessioni/rimozioni tramite **instance ID**, non
tramite l'indice instabile del dispositivo. La disconnessione azzera la direzione
del player; il focus perso sospende il gioco e filtra gli input. Nel menu stick
e D-pad generano una selezione per cambio di direzione, senza ripetizioni da drift.
Tastiera ha priorità su joystick; più dispositivi sono ordinati per instance ID.

`controller` nel manifest configura assi e pulsanti. Default: assi 0/1,
**A/0 conferma**, **B/1 indietro**, **X/2 scudo**, **Start/7 pausa**. Le sigle
sono quelle di un layout comune: altri pad possono richiedere la rimappatura.
L'inserimento del nome continua a usare la tastiera; non è stata introdotta
una tastiera virtuale per gamepad. Riferimenti API verificati:
[pygame.joystick](https://www.pygame.org/docs/ref/joystick.html),
[pygame.event](https://www.pygame.org/docs/ref/event.html).

### Hitbox effettive dei dodici boss e del player

Il manifest associa ora **tutti i dodici asset** ai rispettivi livelli, senza
riusare boss5 nei livelli avanzati. Stessa pipeline `load_sprite()` e stesso
parametro dimensionale per immagine e AABB; nessuna dimensione fisica separata
da sincronizzare manualmente. La hitbox comprende anche i pixel trasparenti
del rettangolo dello sprite, come richiesto per una AABB, non una maschera alpha.

| Entità | PNG attuale | Sprite e AABB logici |
| --- | --- | --- |
| Player | 1023×1183 | 26×30 |
| Boss 1 | 1470×1070 | 134×98 |
| Boss 2 | 1511×1041 | 134×92 |
| Boss 3 | 1470×1070 | 134×98 |
| Boss 4 | 1484×1060 | 134×97 |
| Boss 5 | 1345×1169 | 113×98 |
| Boss 6 | 1498×1050 | 134×94 |
| Boss 7 | 1484×1060 | 134×97 |
| Boss 8 | 1448×1086 | 130×98 |
| Boss 9 | 1469×1071 | 134×98 |
| Boss 10 | 1484×1060 | 134×97 |
| Boss 11 | 1484×1060 | 134×97 |
| Boss 12 | 1484×1060 | 134×97 |

`Game._player_body()` è l'unica AABB del player: sostituisce cella 2×2 e vecchio
margine nei contatti con boss, missili e scosse. Restano le regole di protezione
del territorio sicuro da boss/missili; durante il taglio è vulnerabile l'intero
sprite. La proiezione grafica 800×600→viewport non modifica la geometria logica.
Gli asset originali non sono stati alterati.

### Movimento vincolato al confine

Il solver **collisions.move_player()** condivide il budget di substep del core,
enumera tutte le celle attraversate e blocca il primo ingresso nell'interno
conquistato. `player_cell_allowed()` consente celle libere oppure celle sicure
adiacenti al campo libero negli **otto vicini**. Il vicinato diagonale permette
di girare attorno agli angoli senza entrare nel campo; il movimento resta
strettamente ortogonale. Una cornice profonda non diventa una strada alternativa
lontana dal campo: serve sempre l'adiacenza al territorio libero.

La topologia riguarda l'**ancora** del player; l'AABB grafica completa determina
i contatti con le entità. Obbligare l'intero sprite 26×30 a stare in un bordo
di poche celle renderebbe impossibile navigarlo. Il renderer può ritagliare
lo sprite ai margini del canvas, come prima; dimensioni fisiche e grafiche
logiche rimangono uguali.

`swept_contact()` verifica l'intero tragitto AABB del player verso boss, missili
e scosse, evitando il solo controllo sulla destinazione. La costruzione della
scia segue le celle nell'ordine del solver; una chiusura interrompe il movimento
prima di attraversare ulteriori celle. Se la cattura ingloba il punto di rientro,
la transazione cerca all'indietro sulla linea appena terminata il primo punto
del nuovo confine e vi fissa player/respawn nello stesso commit. Nessuna ricerca
BFS aggiuntiva o correzione applicata durante un tick fisico.

### Vite extra, scudi e HUD

**5 vite iniziali**. Alla vittoria, se la percentuale totale del livello è
**≥76%**, viene assegnata **una vita extra**. `LevelResult` registra il premio,
il ciclo e gli scudi guadagnati; il riepilogo annuncia +1 e le vite già aggiornate.
L'accredito usa la chiave `(ciclo, livello)`: ripetere la transizione non duplica
né punti né vite. Nei primi livelli, la cui soglia di vittoria è inferiore a 76%,
serve oltrepassare 76% con il taglio conclusivo per guadagnare la vita.

Nuovo **shields.py**: inventario a cariche intere. Una singola transazione deve
conquistare **almeno il 25% delle 120.000 celle del campo**, includendo la nuova
linea, per dare uno scudo. Tagli piccoli successivi non si sommano per il premio.
La carica arriva solo dopo il commit riuscito, mai durante una cattura cancellata.

**Spazio / X** equipaggia una carica disponibile; il cerchio rosa circoscrive
lo sprite. La carica resta conteggiata nell'inventario fino al primo contatto
ostile, poi si consuma. Boss, missili e scosse passano da un gestore comune del
contatto. **500 ms di grazia** impediscono che lo stesso urto o due scosse
sovrapposte causino immediatamente anche la perdita di una vita. Durante la
grazia resta visibile l'anello di protezione residua.

Un contatto protetto annulla l'eventuale taglio e riporta il player all'ultimo
punto sicuro senza conquistare territorio. È necessario per non lasciare una
scia intersecante il boss in attesa di un commit impossibile. L'autointersezione,
che invalida la linea, resta una morte non assorbibile. Vite perse non cancellano
le cariche ancora disponibili; al nuovo livello lo scudo viene riposto e la
grazia azzerata, conservando l'inventario.

`public/icon/scudo.png` e label tradotta compaiono al centro per **1,8 s simulati**
durante il gioco. Se il premio coincide con la vittoria, compare prima del
riepilogo: Invio/A lo chiude, una seconda conferma prosegue al livello successivo.
Il pannello superiore mostra **VITE/SCUDI**, per esempio **5/2**, e il footer
riporta anche scudi, punti, bonus, tempo e ciclo. Immagine cornice preservata.

### Due scosse e progressione

| Livello del ciclo 1 | Scosse | Velocità | Attivazione |
| --- | ---: | ---: | ---: |
| 1 | 1 | 150 px/s | 12 s |
| 4 | 1 | 180 px/s | 10,8 s |
| 5 | 2 | 190 px/s | 10,4 s |
| 12 | 2 | 260 px/s | 7,6 s |

Le due entità partono dal punto opposto al player sul medesimo contorno e si
separano in versi **fissi +1/-1**, mantenendoli durante tutto il giro. Una scossa
singola continua a inseguire per il percorso più breve. `perimeter_threats` è
la sorgente unica delle entità; `perimeter_threat` rimane una vista compatibile
del primo elemento per strumenti/test esistenti. Restano contorni compressi,
urti continui ai corner, pausa/cattura congelate e reset dopo conquista/morte.

Profili `LevelConfig`: `perimeter_threat_count` e `perimeter_speed_px_per_second`.
Il vecchio parametro globale di velocità è sostituito da
`perimeter_threat.speed_multiplier=1.0`, moltiplicatore esplicito dei profili.
Le soglie della Scossa sono già distinte nei dodici record del manifest.

### Internazionalizzazione e tutorial

Nuovi **localization.py**, **locales/it.json**, **locales/en.json**. Testi di
menu, HUD, riepiloghi, notifiche, tutorial, dodici suggerimenti e messaggi UI
sono nei cataloghi; il manifest conserva chiavi e configurazione. All'avvio
sono verificati uguaglianza delle chiavi e segnaposto di formattazione.
Errori tecnici interni e identificatori degli algoritmi restano nel log/codice;
la schermata PHYSICS_ERROR mostra un messaggio tradotto, non l'eccezione grezza.

Selezione: `UPIX_LANGUAGE`, poi locale esplicito dell'ambiente, poi lingua UI
Windows o locale di sistema. Italiano/Inglese supportati, **inglese come fallback**.
`i18n.language` può forzare `it`/`en` oppure usare `auto`; richiede riavvio.
Le label italiane stampate nella cornice PNG vengono coperte e ridisegnate
nei rettangoli `frame.labels`, senza cambiare l'asset.

Il menu aggiunge **Come si gioca / How to Play**, navigabile anche con controller.
Spiega confini, movimento continuo, cattura, cinque vite, premio al 76%, scudo al
25%, comandi e cicli. Le soglie nel tutorial vengono formattate dal manifest,
così non divergono modificando il bilanciamento.

### Cosa accade dopo il livello 12?

1. Il riepilogo consolida una sola volta risultato, bonus residuo, eventuale
   vita extra e dati del dodicesimo livello. Segue la schermata di campagna
   completata con **Continua: ciclo N+1** (default) o **Registra e termina**.
2. Continuando si torna al livello 1 con nuovo numero di ciclo. **Run Score,
   tempo totale consolidato, vite e cariche scudo restano acquisiti**. I risultati
   sono indicizzati per coppia `(ciclo, livello)`, senza sovrascrivere il ciclo
   precedente. Totali e conteggio sono mantenuti incrementalmente in O(1).
3. Si ricreano campo, immagini, boss e velocità iniziale del profilo. **Timer del
   livello, scia, missili, scosse, conteggio Scossa, bonus/punti correnti, timer AI,
   equipaggiamento e grazia ripartono da zero**. Si riprende la musica del livello 1.
   Il generatore RNG mantiene la sequenza del run, senza un nuovo seme dal tempo reale.
4. Si applica il modificatore del ciclo ai profili base, senza alterare griglia o
   hitbox: **+15% velocità per ciclo, massimo 200%** per boss, missili e scosse;
   intervalli spari e attivazione Scossa **−10 punti percentuali per ciclo,
   minimo 40%** del profilo; pavimenti di **300 ms** per gli spari e **3000 ms**
   per l'attivazione. Conquista richiesta **+2 punti per ciclo, massimo 90%**.
   Il livello 1 del ciclo 2 ha quindi boss **1,84 px/tick**, scossa **172,5 px/s**,
   attivazione **10,8 s** e soglia vittoria **72%**. Il ciclo ricalcola dal profilo
   base: non moltiplica ripetutamente i valori già scalati.
5. La curva interna 1–12 ricomincia: il primo livello del nuovo ciclo può essere
   più lento del dodicesimo appena concluso, ma è più difficile dello stesso
   livello nel ciclo precedente. I limiti evitano crescita illimitata della
   velocità/costo del solver. Restano una scossa nei livelli 1–4 e due dal 5.
6. **Registra e termina** apre l'inserimento nome e salva il Run Score totale nel
   JSON locale. Anche un Game Over nei cicli successivi salva tutti i livelli
   completati, per esempio 13 dopo il primo livello del ciclo 2; `completed`
   indica che almeno una campagna è stata conclusa. La persistenza della partita
   in corso resta in memoria: non è stato aggiunto un ripristino dopo chiusura.
7. **Inizia Campagna** dal menu crea un nuovo Game: ciclo 1, cinque vite, zero
   punti e zero scudi. I risultati già salvati nella classifica rimangono sul file.

I moltiplicatori e i limiti sono in `progression.loop`. La classifica conserva
compatibilità con i record precedenti, ma regole diverse non costituiscono una
graduatoria competitiva confrontabile: la futura API dovrà versionare il ruleset.
Il contratto Web proposto include anche input scudo e scelta del ciclo; nessun
backend, replay recorder o build browser è stato implementato in questo task.

### Verifiche, prestazioni e limiti della consegna

**207 test superati** in **55,480 s** con
`.venv\Scripts\python.exe -m unittest discover -s tests -q`.
Baseline 178 e **29 nuove regressioni**: input (5), i18n (3),
movimento player (6), inventario scudi (3), integrazione avanzata (9),
campagna/salvataggio nei cicli (2), HUD scudi (1). Le regressioni esistenti sono
aggiornate alle cinque vite e alla AABB completa, mantenendo muro 200–201 px,
solver boss/missili, pausa/audio, cattura e determinismo.

Verifiche nuove significative: soglie inclusive 76% e 25%, nessun premio doppio,
un grande taglio reale con premio solo al commit, ancoraggio sul nuovo confine,
urto assorbito senza modificare la griglia, due versi opposti, tracciamento di
tutte le celle anche ad alta velocità, svolta sicura attorno agli angoli,
assenza di letture hardware dal tick, deadzone/hotplug tramite dispositivi
simulati, conteggio e salvataggio reale JSON di 13 risultati. Una simulazione
di nove secondi con due scosse e consumo dello scudo coincide a **30/60/144 FPS**.

Verifica visiva SDL dummy IT/EN: menu, tutorial, pannelli cornice, partita con
due scosse e anello, icona/premio scudo, riepilogo con vita extra e scelta del ciclo.
I test/screenshot usano file temporanei e non creano risultati fittizi nel
salvataggio personale. Controller fisico, audio reale e playtest prolungato
restano da collaudare sul dispositivo dell'utente.

Benchmark cattura isolato, con rendering, viewport e HUD, senza overlay del
controller schermate: taglio x=400 px **17 frame**, massimo CPU **6,638 ms**;
taglio x=160 px **16 frame**, massimo **6,568 ms**. Lavoro di cattura massimo
**4,115 ms**, coerente con budget 4 ms controllato tra quanti. Caso stretto del
tool aggiornato da 120 a 160 px per contenere interamente il boss attuale.

Profilo CPU livello 12, seme 1989, 20 tick di riscaldamento e 240 campioni,
tick + Game.draw + viewport + HUD, due scosse attive. Player fermo con grazia
artificiale nella sola diagnostica, per impedire che una morte interrompa il
profilo. Ciclo 1: mediana **5,550 ms**, P95 **7,289 ms**, massimo **10,378 ms**.
Ciclo 8, già al tetto 200% velocità: **8,725 / 10,290 / 13,649 ms**.
Sono scenari controllati SDL dummy, non una garanzia universale di 60 FPS su
monitor/hardware reale o con contorni/scie estremi. Nessuna operazione Git.

## Storico — Scossa sul perimetro e sprite energia (7 novembre 2026)

La sezione seguente descrive la prima scossa fisica; hitbox player, quantità,
progressione, localizzazione e flusso dopo il livello 12 sono stati aggiornati
dalla consegna dell'8 novembre.

### Comportamento implementato

La Scossa mantiene soglie, conteggio dei tick sicuri e incremento degli spari
precedenti. Il preavviso resta ambrato con conto alla rovescia. All'attivazione
viene creata **una PerimeterThreat**, separata dalla lista dei missili, e il
messaggio diventa «SCOSSA SUL BORDO! Conquista per disinnescare».

La scossa nasce a metà della lunghezza del contorno rispetto alla proiezione
del giocatore. Insegue la sua proiezione sul medesimo contorno lungo il verso
più breve; a distanze uguali conserva il verso precedente. Velocità predefinita
**150 px/s = 2,5 px/tick a 60 Hz**. Non usa RNG o tempo reale e non cambia
velocità in funzione degli FPS. Il movimento resta sul confine del territorio
sicuro, non attraversa le aree conquistate per raggiungere un player interno.

Il contatto con la **cella fisica del player in zona sicura** causa una sola
perdita di vita tramite `handle_death()`, con respawn o Game Over già esistenti.
Durante il taglio la scossa continua sul confine; non insegue né colpisce la
scia nel campo libero. Il corpo della scossa è **10×10 px**, lo sprite è
proporzionato nel box **18×18 px**: parametri distinti, come consentito dalla
meccanica semi-fisica richiesta. La regola AABB identica allo sprite resta
invariata per il boss.

Ogni spostamento viene spezzato agli angoli e verifica l'inviluppo AABB del
singolo segmento assiale: urti continui anche ad alta velocità, senza il falso
contatto che deriverebbe da un unico rettangolo contenente una curva. Viene
controllato anche il player che si muove nella scossa durante lo stesso tick.
La semplice tangenza non è un urto, coerentemente con `collisions.AABB`.

PAUSED, CAPTURING e stati terminali congelano la scossa. Una conquista riuscita,
una morte e l'avvio del livello la eliminano; la conquista azzera anche la
Scossa. Nessuna fisica aggiuntiva viene eseguita dal renderer.

### Contorni senza BFS e commit cooperativo

Nuovo modulo puro **perimeter_threat.py**: `PerimeterRoute`,
`build_perimeters()` e `PerimeterThreat`. Il confine è l'interfaccia tra celle
FILLED e campo libero, inizialmente il rettangolo interno del bordo sicuro;
dopo le catture può essere concavo. Vengono raccolti lati orientati e seguiti
con una regola di svolta deterministica. Regioni che si toccano in un solo
vertice mantengono contorni distinti. I lati collineari diventano segmenti
lunghi: il campo iniziale richiede solo **quattro segmenti**.

La costruzione costa O(celle + lati), con memoria temporanea O(lati), senza
BFS né ricerca di cammini. I semi dei contorni sono scanditi una sola volta
anche in campi molto frammentati. Al cambio livello il calcolo è fuori dal
tick fisico; dopo la conquista viene distribuito nello stesso lavoro
CAPTURING, con yield per colonna e ogni 128 operazioni sui lati. Il valore
128 è il chunk predefinito del generatore, separato dal passo della simulazione.
Il commit sostituisce insieme griglia, canvas e contorni: niente confini
parziali visibili alla fisica. Una cattura cancellata conserva il percorso
precedente.

Ogni tick cerca la proiezione sul contorno selezionato in O(segmenti), poi
percorre soltanto i segmenti necessari. In presenza di più contorni lo spawn
sceglie quello più vicino al player; non salta fra contorni durante la caccia.

### Sprite condiviso e configurazione

**shock.png** attuale: **1261×1247**, alpha presente. Il file originale non è
stato alterato. Nuovo **sprite_renderer.py**, con `DirectionalSprite`: carica
lo sprite una volta per taglia, mantiene proporzioni/trasparenza e lo centra
sulla posizione logica. I missili usano il medesimo asset nel box **8×8**,
conservando il precedente aumento del 30% e il corpo fisico **5,2×5,2**.
Mira, velocità, cadenza e solver dei missili restano quelli già verificati.

La direzione usa `atan2(vy, vx)` con il segno corretto per le coordinate schermo.
L'orientamento grafico è quantizzato a **5°**, con cache di al massimo **72**
rotazioni per taglia; non vengono accumulate trasformazioni sul bitmap già
ruotato. La rotazione non modifica il corpo fisico. Un asset assente/corrotto
produce un fallback magenta, senza interrompere la simulazione.

Nuove chiavi di **game_manifest.json**, validate prima dell'avvio:

- `assets.energy_sprite`: percorso comune a scossa e missili.
- `perimeter_threat.enabled`, `speed_px_per_second`, `body_size`, `sprite_max_size`.
- `energy_visual.rotate_with_velocity`, `source_angle_degrees` (asse originale
  verso destra a 0°), `rotation_step_degrees`, `fallback_color`.

Il manifest mantiene l'ID della campagna locale per non rendere illeggibili
salvataggi esistenti. Il fingerprint cambia automaticamente. Per una classifica
pubblica competitiva, non ancora implementata, questa variazione delle regole
richiederà una nuova versione del regolamento.

È cambiato anche il PNG boss5 dell'utente: ora **1345×1169**, reso a **113×98**
con AABB uguale allo sprite. La regressione dei cinque boss verifica proporzioni,
scala massima e corpo condiviso partendo dai file correnti, senza imporre le
dimensioni dei vecchi PNG. Nessuna modifica ai file sorgente degli asset.

### Verifiche e limiti

**178 test superati** con
`.venv\Scripts\python.exe -m unittest discover -s tests -q` (43,330 s).
Baseline 157, **21 nuovi test**: 12 sui contorni/scossa, 5 sull'integrazione
nel gioco, 3 sul rendering direzionale e 1 sulla validazione del manifest.
Una regressione esistente estende il confronto a 30/60/144 FPS includendo
posizione e verso della scossa dopo l'attivazione.

Verificati: collisione sul bordo e perdita di una sola vita, movimento del
player verso la scossa, urti attraverso angoli e origine del percorso,
assenza di falsi urti nelle diagonali non percorse, reset e commit dopo
cattura, sospensione/ripresa, nessun impatto sul player distante dal bordo,
regione concava, isole e contatti diagonali. Su **25 griglie frammentate**
ogni lato di confine è confrontato con l'elenco di riferimento e deve apparire
esattamente una volta. Test grafici con fixture asimmetrica verificano verso,
centratura e cache limitata. Restano superate collisioni boss/missili, timer,
campagna, classifica e audio.

Verifica visiva SDL dummy del campo con scossa attiva e missili in tre direzioni.
Come il player, una parte dello sprite può essere ritagliata ai margini esterni
del canvas. Le misure prestazionali delle consegne precedenti sono storiche:
non certificano il frame time con i nuovi asset e questa meccanica. Restano
necessari playtest reale per leggibilità e bilanciamento, e profilazione dei
contorni estremi; non viene dichiarata una garanzia universale di 60 FPS.
Nessuna operazione Git eseguita.

## Storico — Fasi 5/6, sito e nuovi sprite (7 novembre 2026)

La sezione seguente descrive la consegna precedente; le misure del boss5 e
l'assenza di una scossa fisica sono superate dalla consegna corrente.

### Campagna e Run Score

`campaign.py` introduce `RunScore` e `LevelResult` immutabile. Alla transizione
LEVEL_CLEAR il gioco congela punti base, bonus residuo, tempo, percentuale e vite
del livello e li consolida una sola volta, indicizzando il risultato per livello.
Una ripetizione della transizione non accredita nuovamente il punteggio.

`Game.score` resta il punteggio del livello corrente, per mantenere separata la
logica esistente di area/tempo. `Game.run_score` è invece il totale dei risultati
conclusi più il punteggio corrente, escludendolo quando è già consolidato.
L'HUD mostra quest'ultimo. Il bonus già acquisito alla vittoria non decade nel
livello successivo; il bonus del livello in corso mantiene la scadenza precedente.
`start_level()` azzera soltanto contatori del nuovo livello, Scossa e clock,
conservando registro di campagna e vite. Una nuova campagna crea un nuovo Game.

La schermata **Riepilogo Livello** compare sulla primaria completata, con sfondo
attenuato: conquista, vite, punti base, bonus, totale del livello, Run Score e
tempo. Invio/Spazio continua. Il dodicesimo riepilogo porta a
**CAMPAIGN_COMPLETE**, senza il precedente ritorno automatico al livello 1.

### Menu e gestione delle schermate

`application.py` separa il controller `CampaignApp` dalla simulazione. Parte
sempre in **MENU**: nessun Game, livello o stream musicale viene creato prima
di scegliere **Inizia Campagna**. Su/Giù navigano fra Inizia Campagna, Classifica
ed Esci; Invio conferma. Menu e gioco condividono cornice/viewport.

Stati UI aggiunti: MENU, HIGHSCORES, NAME_ENTRY, CAMPAIGN_COMPLETE; il controller
deriva lo stato attivo del gioco quando la campagna è avviata, evitando di
duplicare flag PAUSED/CAPTURING/LEVEL_CLEAR. Il percorso di Game Over apre
l'inserimento nome. Il finale mantiene prima una schermata dedicata e poi
permette l'inserimento. Text input Unicode, Backspace, Invio per salvare ed Esc
per tornare al menu senza salvare. Q chiude dal menu/gioco e resta un carattere
normale mentre si scrive un nome. R conserva soltanto il riavvio da errore fisico.

Gli errori di salvataggio mantengono nome e risultato, consentendo il retry;
gli errori di lettura della classifica permettono un nuovo tentativo con Invio.
Le operazioni di persistenza sono eseguite nelle schermate UI, mai nel tick
fisico. Non è stato introdotto un salvataggio della partita a metà campagna.

### Persistenza locale e adattatore browser

`highscores.py` contiene il modello validato `ScoreEntry` e il contratto comune
`ScoreStore`. `JsonScoreStore` crea **user_data/highscores.json** al primo
salvataggio; il percorso è configurato nel manifest ed escluso dal versionamento.

Schema: `schema_version`, `campaign_id`, `entries`. Ogni entry include run UUID,
nome normalizzato, punteggio, livelli completati, millisecondi attivi, esito
campagna e timestamp UTC. Il nome usa lettere/numeri Unicode, spazi, `_` e `-`,
massimo 16 caratteri. Il totale è intero e non negativo. Dieci risultati ordinati
per punti decrescenti, livelli completati, tempo e chiavi stabili per i pareggi.
Lo stesso run già presente non viene aggiunto nuovamente.

Scrittura: file temporaneo nella stessa directory, UTF-8, flush/fsync, poi
`os.replace`. Un errore di sostituzione lascia il precedente JSON intatto e
rimuove il temporaneo. Un file corrotto, una campagna diversa o una versione
sconosciuta producono errore senza sovrascrittura automatica. È un archivio
personale per il processo desktop, non un database condiviso multiutente.

`BrowserScoreStore` usa un oggetto storage iniettato con `getItem/setItem` e
lo stesso codec. Gestisce eccezioni di quota/blocco del browser. È testato con
un fake del bridge: non viene presentato come port WebAssembly già funzionante.
I risultati locali sono modificabili dall'utente e non sono una classifica
pubblica verificata.

### Manifest e rimozione dei profili codificati nel sorgente

Nuovo **game_manifest.json**, letto da `manifest.py` con validazione e struttura
ricorsivamente immutabile. I dodici profili sono documenti espliciti: non vengono
più derivati da CAMPAIGN_BALANCE o dal numero del livello. Ogni record contiene
anche primaria, copertura, sprite, box base e scala, musica, Scossa e score.

Il manifest centralizza dimensioni logiche/finestra/celle, vite iniziali, timing,
budget di cattura, proiettili, player, asset e percorsi, volumi, controlli, testi
di menu/riepilogo, stile della UI, coordinate della cornice e politica della
classifica. `controls.py` risolve i tasti senza inizializzare SDL durante l'import.
`level_config.py` rimane la vista dataclass validata usata dal motore.

Gli invarianti degli algoritmi e i dettagli strutturali del disegno rimangono nel
codice; le impostazioni di campagna e i riferimenti agli asset sono caricati dal
manifest. Cambiare il documento richiede riavvio. Un fingerprint identifica la
configurazione; un hash pubblicamente modificabile non è una firma anti-cheat.
L'ID campagna va versionato quando cambia il bilanciamento destinato alla classifica.

### Nuovi sprite e ultime richieste dimensionali

`assets.load_sprite()` preserva proporzioni e alpha e restituisce insieme bitmap
e dimensione effettiva. Per i boss viene prima determinata la misura nel box
96×70, poi applicato `boss_render_scale=1.4` con arrotondamento al pixel. Fallback
e AABB usano la stessa dimensione; il corpo non viene ristretto per passare nei
corridoi. La scala riparte sempre dall'asset originale, senza accumularsi ai restart.

| Asset | File attuale | Sprite e AABB logici |
| --- | --- | --- |
| boss1 | 1470×1070 | 134×98 |
| boss2 | 1511×1041 | 134×92 |
| boss3 | 1470×1070 | 134×98 |
| boss4 | 1484×1060 | 134×97 |
| boss5 | 817×592 | 134×98 |

Il player è stato aggiornato dall'utente anche durante questo task: l'ultima
lettura è 1028×1191, resa a 26×30 senza schiacciamento. È stata conservata la
regola della Fase 4: cella 2×2 per missile/player e margine preesistente di 2 px
nel contatto boss/player. La nuova richiesta di hitbox uguale allo sprite si
applica al boss; la fisica del player non è stata ampliata implicitamente.

`missile_size_scale=1.3` applica +30% al corpo 4×4, ora 5,2×5,2 float. Il raggio
grafico nominale passa da 3 a 3,9: sul canvas intero viene arrotondato a 4 px.
Mira, velocità e cadenza restano quelle dei dodici profili della Fase 4.

### Analisi del sito e percorso di release Web

Controllato il sito pubblico **https://sonsofart.vercel.app/**: HTTP 200,
server Vercel, HTML Sons of Art e bundle con React/createRoot e marcatori Vite.
La pagina include giochi e universo LUKSO. Il backend è personalizzato, come
confermato dall'utente; il sorgente pubblico non ne rivela database o API private.
Non è stato modificato/deployato il sito.

Consegne concrete di preparazione:
[docs/WEB_RELEASE.md](docs/WEB_RELEASE.md), contratto proposto
[web/leaderboard.openapi.json](web/leaderboard.openapi.json) e schema PostgreSQL
[web/schema.sql](web/schema.sql). Non sono endpoint o migrazioni già eseguiti.

Strategia: pagina React dedicata al gioco, build browser con loop cooperativo,
asset SVG prerasterizzati per evitare di assumere compatibilità WebAssembly di
resvg_py, storage browser solo personale e API sullo stesso dominio per la
classifica condivisa. Server genera run ID/seme, valida sequenza e input, poi
un worker ricalcola il risultato prima di ammetterlo nella classifica pubblica.
Il semplice invio di un punteggio dal client non viene considerato affidabile.

Fonti primarie: [Pygbag](https://github.com/pygame-web/pygbag/blob/main/README.md),
[MDN localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage),
[Vercel storage](https://vercel.com/docs/marketplace-storage),
[OWASP REST](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html).
Il port Web, l'API, la verifica replay e il collegamento al backend rimangono
da implementare nel progetto del sito: nessuna credenziale o servizio è stato creato.

### Verifiche e limiti

**157 test superati** con `.venv\Scripts\python.exe -m unittest discover -s tests -q`.
Baseline 140, più 17 nuove regressioni: Run Score idempotente, menu iniziale,
riepilogo, intera campagna fino al finale, inserimento e persistenza del nome,
retry, formato JSON/Unicode, classifica ordinata e limitata, dati corrotti,
scrittura atomica fallita, storage browser, manifest e proiettili scalati.
Le regressioni del muro 200–201 px hanno partenze aggiornate per il corpo più
grande; controllano ancora rimbalzo, residuo e non attraversamento. Restano
superati determinismo a FPS diversi, Scossa, score/bonus, catture e audio.

Verificati visivamente menu, gioco, riepilogo, nome e classifica con driver SDL
dummy. La prova della persistenza ha scritto solo in directory temporanee,
senza produrre classifiche fittizie nel percorso reale dell'utente.

Profilazione CPU isolata, 20 frame di riscaldamento e 120 misure, boss ingranditi,
Scossa attiva, player fermo al sicuro; include tick, rendering, cornice e HUD:

| Profilo | Mediana | P95 | Massimo |
| --- | ---: | ---: | ---: |
| Livello 1 | 4,507 ms | 6,551 ms | 8,939 ms |
| Livello 12 | 10,061 ms | 13,671 ms | 17,400 ms |

Il picco del livello 12 supera 16,67 ms: non viene certificato un 60 FPS costante
in ogni situazione. Il corpo più grande aumenta il lavoro locale del solver;
scie estreme e hardware reale richiedono ulteriore profilazione. I caricamenti
di livello restano sincroni fuori dall'avanzamento fisico e vanno valutati nel
port browser. Le verifiche automatiche non sostituiscono il playtest della
campagna né l'ascolto reale. Nessuna operazione Git.

## Storico — Fase 4 e preparazione Fase 5 (7 novembre 2026)

I parametri dimensionali e le limitazioni di questa sezione descrivono la
consegna precedente; per lo stato attuale fanno fede manifest e sezione sopra.

### Codice effettivamente implementato

- `Upqix89.py`: `PLAYER_SPRITE_SIZE=(30,30)`, il doppio della scala precedente.
  Rendering e fallback centrati nel centro della cella `(x*2+1, y*2+1)`.
  Nessuna dimensione grafica entra nelle collisioni: missile/player resta a una
  cella 2×2, boss/player conserva il margine preesistente di 2 px. Il boss
  continua a usare un unico `boss_size` per sprite e AABB identici.
- `shock_system.py`: modulo logico senza Pygame/RNG/tempo reale, con `ShockConfig`
  immutabile e validata. `advance(safe=...)` viene chiamato una volta per tick
  PLAYING. Conta qualsiasi cella FILLED, anche muovendosi: camminare lungo il
  perimetro non elude la Scossa. Si ferma durante i tagli, senza perdere il
  conteggio o spegnere la pressione; reset dopo commit di cattura, morte e nuovo
  livello. Pausa, CAPTURING e stati terminali non consumano tempo.
- Preavviso visivo ambrato con conto alla rovescia, poi avviso rosso di Scossa
  attiva. Nel livello 1: **8 s / 12 s**; nel livello 12: **5,25 s / 7,6 s**.
  La cadenza attiva usa `base_ms * shot_interval_percent // 100` (minimo 1 ms),
  con valore predefinito 50: doppia frequenza, senza cambiare velocità o mira.
  La scadenza si riferisce all'ultimo sparo, con massimo un lancio per tick,
  senza recuperi a raffica. Soglie non allineate si attivano al primo tick utile.
  `enabled=False` disattiva la Scossa; `missile_interval_ms=None` continua a
  disabilitare gli spari anche sotto pressione.
- `scoring.py`: `ScoreConfig`/`LevelScore`, senza dipendenze grafiche; tutti i
  calcoli sono interi. Per un taglio di area A su N=120.000 celle:
  `base=A*10`, `bonus_potenziale=base*A*area_bonus_percent//(N*100)`.
  Le celle della scia e il bordo iniziale non generano punti. Il commit assegna
  una sola volta base e bonus potenziale. Un taglio da 100 celle su un campo
  di 1000 dà 1000+100 punti; due tagli da 50 danno 1000+50 al tempo zero.
- Il bonus mostrato è la somma dei bonus potenziali moltiplicata per
  `max(0, limite_ms-tempo_attivo_ms)//limite_ms`, eseguendo la moltiplicazione
  prima della divisione. Decade quindi anche dopo una cattura; una cattura oltre
  il limite non lo riavvia. SCORE = punti base + bonus corrente, senza valori
  negativi. Il limite va da **180 s a 290 s**, +10 s per livello; la base resta
  acquisita. `area_bonus_percent=0` elimina il bonus. Lo score resta per livello,
  si congela alla vittoria e si azzera al cambio livello, come nel gioco precedente.
- `hud.py`: SCORE, BONUS e TEMPO nello spazio inferiore della cornice, con
  adattamento a larghezza/altezza del pannello. Il totale può diminuire mentre
  il bonus scade: la componente BONUS rende visibile la causa.

### Campagna: manifest esplicito di dodici profili

`CAMPAIGN_BALANCE` in `level_config.py` sostituisce i profili generici 4–12.
Nessuna condizione sul livello nel loop: ogni `LevelConfig` include anche
`ShockConfig` e `ScoreConfig`. Crescono boss, missili, inseguimento e soglia;
calano gli intervalli di sparo/direzione senza discontinuità dopo il tutorial.

| Livello | Boss px/tick | Missile px/tick | Sparo base ms | Conquista % |
| --- | ---: | ---: | ---: | ---: |
| 1 | 1,6 | 2,0 | 2400 | 70 |
| 2 | 2,0 | 2,3 | 2250 | 72 |
| 3 | 2,4 | 2,6 | 2100 | 74 |
| 4 | 2,8 | 2,9 | 1950 | 76 |
| 5 | 3,2 | 3,2 | 1800 | 78 |
| 6 | 3,6 | 3,5 | 1650 | 80 |
| 7 | 4,0 | 3,8 | 1500 | 81 |
| 8 | 4,4 | 4,1 | 1350 | 82 |
| 9 | 4,8 | 4,4 | 1200 | 83 |
| 10 | 5,2 | 4,7 | 1050 | 84 |
| 11 | 5,6 | 5,0 | 900 | 85 |
| 12 | 6,0 | 5,3 | 750 | 86 |

Le velocità sono pixel logici per tick a 60 Hz (2 px/tick = 120 px/s).
Sprite e musiche del tutorial sono conservati; 4–12 riusano `boss3.png` e le
quattro tracce. Il manifest configura varietà parametrica, senza introdurre
asset o archetipi nuovi. L'80% precedente è sostituito dalla curva 70–86% per
alleggerire l'apprendimento e aumentare gradualmente la sfida finale.

### Verifiche e decisioni di bilanciamento

Baseline precedente: **120 test superati**. Suite aggiornata: **140 test superati**:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Nuove regressioni: soglia Scossa esatta e non allineata al tick, disattivazione,
persistenza nel taglio, reset, cadenza effettiva aumentata e movimento sul bordo;
formule note di punteggio, premio del taglio unico, scadenza e catture tardive,
zero area e input invalidi; congelamento in pausa/cattura/stati terminali;
progressione monotona e spari runtime in tutti i dodici livelli; stessa cattura
di circa 75% vincente al livello 1 e insufficiente al 12; rendering player 30×30
centrato e impatto missile solo nella hitbox originale. Con seme 1989, Scossa
attiva e bonus, stato identico a 30/60/144 FPS. Le regressioni precedenti su
collisioni, territorio, audio e loop restano superate; AABB/sprite boss uguali
verificati durante il caricamento di tutti i livelli.

Controllati visivamente due frame 1024×768 renderizzati con SDL dummy: preavviso
ambrato, allerta rossa, cursore ingrandito e pannello SCORE/BONUS/TEMPO leggibili,
cornice e primaria rivelata coerenti. Nessuna operazione Git eseguita.

**Limiti:** i missili restano assorbiti dal territorio sicuro; la Scossa rende
più rischioso il taglio successivo, mentre il bonus decrescente dà un costo
all'attesa. Non è un cacciatore che uccide sul bordo. Il cursore centrato può
essere ritagliato ai margini del campo, come prima. Test deterministici e frame
dummy non certificano la difficoltà in una partita completa o l'audio reale.

**Stato fasi:** Fase 4 implementata per questa richiesta; bilanciamento numerico
da validare con playtest. Preparazione Fase 5 implementata (manifest completo,
progressione e bonus). Restano pianificati: score cumulativo di campagna, finale,
nuovi archetipi/asset, eventuali potenziamenti, salvataggi e classifica; nessuno
di questi è presentato come codice già consegnato.

## Storico — Spari ripristinati, cornice e immagini proporzionate

Le sezioni delle consegne precedenti conservano i parametri di quel momento;
per il comportamento corrente fanno fede la consegna dell'8 novembre in apertura,
il manifest e il codice.

### Ripristino delle pallottole

La segnalazione è stata ricondotta al profilo tutorial: la precedente consegna
aveva impostato `missile_interval_ms=None` nel livello 1, rimosso gli spari e
rallentato le pallottole del livello 2. Il puntamento al player non era stato
eliminato dal codice, ma la configurazione del primo livello lo rendeva inattivo.
L'ultima richiesta sostituisce quella precedente del tutorial senza missili.

Ripristinati intervalli **1900, 1800 e 1700 ms** nei primi tre livelli e velocità
**5 px/tick** (300 px/s a 60 Hz), come nel motore prima della vertical slice.
I livelli 4–12 conservano l'intervallo `max(500, 2000 - livello × 100)` e la
stessa velocità. Velocità boss, sprite, musica e inseguimento restano definiti
dai rispettivi profili. I parametri sono modificati in `level_config.py`, senza
condizioni speciali nel loop.

Il lancio è raccolto in `_shoot_at_player()`: usa la posizione logica corrente
del player, normalizza il vettore rispetto al centro del boss e lo moltiplica
per la velocità configurata. La traiettoria resta rettilinea dopo il lancio;
un bersaglio coincidente non produce divisioni per zero. Il solver continuo
dei missili resta responsabile di muro, scia e player vulnerabile. Spari e
intervalli rimangono fermi in PAUSED/CAPTURING e negli stati terminali.

### Cornice e pannelli HUD

Integrato il PNG originale **1448×1086** con alpha, senza alterare il file.
La cornice è scalata uniformemente a **1024×768** una sola volta, poi composta
sopra il campo. Il centro è trasparente: il gioco resta visibile. `hud.py`
conserva metadati espliciti nel sistema di coordinate dell'asset:

- apertura interna `(40, 94, 1364, 972)`;
- aree libere dei valori per **LIVELLO**, **CATTURA** e **VITE**;
- piccolo spazio nel bordo inferiore per **SCORE** e **TEMPO**.

Le label già disegnate nel PNG non vengono duplicate. I valori sono centrati
nei rispettivi pannelli; la percentuale usa una cifra decimale. Il vecchio
suggerimento tutoriale non viene sovrapposto all'immagine di gioco. I testi
dinamici e la cornice sono memorizzati in una superficie RGBA e ricomposti solo
quando cambiano i dati. Un asset mancante/corrotto produce un fallback funzionale
con la stessa geometria e diagnostica, senza bloccare l'avvio.

Il rettangolo interno dell'asset è leggermente più largo del 4:3. Per mantenere
interamente visibile il campo e non deformare la fisica, il viewport inscrive
il frame logico 800×600 nell'apertura: **917×688** in `(52,66)`, fattore
**688/600 ≈ 1,146667** prima dell'arrotondamento dei pixel. Rimangono sottili
margini laterali neri nell'apertura. La cornice resta intera e proporzionata;
le celle non vengono tagliate. `Hud.game_area` determina l'area disponibile:
main e benchmark non duplicano più l'altezza fissa del vecchio header.

### Sfondi: riempimento con ritaglio centrato

Le dodici immagini primarie distribuite sono **2048×2048**. Prima venivano
ridimensionate direttamente a 800×600, alterando il rapporto 1:1. Ora il loader
comune applica `scala = max(larghezza_dest/larghezza_src, altezza_dest/altezza_src)`
e centra il risultato nel quadro: nessuna scala diversa fra asse X e asse Y.
Il contenuto che eccede il quadro viene ritagliato. Per una primaria quadrata,
si ottiene **800×800** e si tagliano **100 px sopra e 100 sotto** nello spazio
scalato; resta visibile la zona centrale dell'originale.

La stessa politica si applica alla copertura SVG. Il renderer SVG usa ora le
dimensioni intrinseche del documento, evitando bande introdotte da un viewport
intermedio con rapporto diverso; poi il loader esegue il ritaglio. La cache PNG
SVG resta limitata a quattro elementi e invalidata dal timestamp, senza lavoro
SVG nel frame loop. Ritaglio/ridimensionamento avvengono al caricamento del livello.

I ruoli non cambiano: SVG visibile nel territorio libero, primaria PNG/JPG
rivelata nelle celle conquistate e interamente sul quadro di vittoria. La stessa
primaria già ritagliata alimenta tutte le copie per cella/intervallo: nessuno
spostamento dell'immagine durante le catture. Il ritaglio di parte del contenuto
è intenzionale, come richiesto; gli originali rimangono invariati.

### Verifiche della consegna

**120 test superati**. Quattro nuovi test e adattamento delle regressioni ai
contratti correnti: puntamento nelle diverse direzioni, velocità e cadenza dei
primi tre livelli, bersaglio coincidente, ritaglio di primarie larghe/alte con
marcatore quadrato non deformato, SVG con identica prova e assenza di bande,
geometria della cornice/pannelli, fallback e composizione trasparente. Le prove
di collisione, pausa/cattura e determinismo a 30/60/144 FPS restano superate.

Verificati visivamente avvio e conquista al **51,16%**, con valori nei pannelli,
score sul bordo inferiore, SVG e primaria distinti. Benchmark aggiornato al nuovo
layout, eseguito separatamente dai test con SDL dummy:

| Misura CPU | Taglio centrale | Cattura grande / vittoria |
| --- | ---: | ---: |
| Frame di cattura | 16 | 14 |
| Frame completo, mediana | 5,840 ms | 5,854 ms |
| Frame completo, massimo | 8,092 ms | 7,778 ms |
| Lavoro di cattura, massimo/frame | 4,218 ms | 4,568 ms |

Il costo della composizione con alpha resta entro il budget di 16,67 ms nei
casi misurati. Il limite cooperativo di 4 ms può essere superato di un quanto o
per scheduling del sistema operativo; le misure non certificano ogni hardware
né sostituiscono una partita con refresh e audio reali. Nessuna operazione Git.

## Consegna precedente — Cattura fluida e vertical slice

Le scelte di tutorial senza missili e di HUD in fascia da 48 px descrivono la
consegna precedente; sono sostituite dalle direttive e dall'implementazione sopra.

### Cattura cooperativa e commit — Fase 2

`fill_area()` ora avvia un lavoro e passa a **CAPTURING**; non esegue più
l'intera conquista dentro il tick fisico. È una gestione cooperativa sul thread
principale, senza thread concorrenti che possano leggere/scrivere la griglia
durante una collisione. Ogni frame esegue lavoro entro **4 ms**, con quanti di
**128 celle/operazioni locali** e un tetto di **256 quanti**. Il controllo del
tempo avviene fra quanti, quindi il budget è un obiettivo con piccolo margine
di superamento, non una garanzia di scheduling real-time del sistema operativo.

`CapturePlanner` in `territory.py` è puro e indipendente da Pygame/timer. La BFS
con set di tuple è sostituita da un **flood fill scanline**: espande intervalli
verticali e accoda gli inizi degli intervalli adiacenti. Una `bytearray` di
120.000 flag distingue libero, solido/frontiera e raggiungibile. Il risultato
contiene intervalli `(colonna, primo_y, y_escluso)`, non decine di migliaia di
tuple di celle. La proprietà iterabile `CapturePlan.cells` conserva le query
usate da test e strumenti; `plan_capture()` rimane un wrapper sincrono dedicato
a questi ultimi e non viene chiamato dal runtime.

L'intero processo è distribuito, comprese validazione del corpo/scia, preparazione
dei flag, visita, raccolta degli intervalli, copie delle colonne e rivelazione.
Prima di modificare dati visibili alla fisica vengono verificati continuità,
estremi sicuri, assenza di duplicati, boss libero e conservazione dell'intera AABB.
Un contatto scia/boss fa perdere una vita; una geometria invalida sospende la
fisica. In entrambi i casi il piano non viene applicato.

Dopo la validazione si prepara una **copia di griglia e canvas**. La primaria
viene copiata con un blit per intervallo, eliminando il blit per cella. Il
renderer può mostrare il canvas in preparazione; griglia attiva, punteggio e
percentuale restano quelli precedenti. Al termine si scambiano i riferimenti,
si aggiorna una sola volta lo score e si usa il conteggio incrementale delle
celle conquistate. Nessuna scansione completa aggiuntiva per la percentuale.
La percentuale comprende ancora il bordo iniziale, ora correttamente mostrato
fin dall'avvio (**2,32%**). Il punteggio conserva la regola precedente: 10 punti
per cella di area, senza conteggiare la nuova scia.

In CAPTURING fisica, player, boss, missili, AI e tempo simulato sono fermi;
eventi, musica e rendering continuano. La saldatrice si interrompe subito.
Una pulsazione della scia e il suggerimento di chiusura danno feedback durante
la breve transizione. La pulsazione usa soltanto tempo grafico, senza consumare
tick o RNG. Il reset dello scheduler interrompe i tick arretrati alla chiusura e
alla ripresa. P/perdita focus sospendono anche CAPTURING; P riprende lo stesso
lavoro, mentre il riavvio del livello lo scarta senza applicazioni parziali.

### Configurazioni e primi tre livelli — Fase 3

Nuovo `level_config.py`: `LevelConfig` immutabile, valori numerici validati,
registro di 12 livelli e `get_level_config()`, che rifiuta livelli inesistenti.
Ogni profilo contiene sprite, velocità boss, intervallo/velocità dei missili,
intervallo e intensità delle variazioni di direzione, peso dell'inseguimento,
soglia di vittoria, musica e suggerimento. Il loop usa il profilo corrente:
nessuna catena di condizioni sul numero del livello. Tutti i valori nel registro
sono assegnati per nome, per rendere leggibile e sicura la taratura. Dopo questa
rifinitura sono stati ricontrollati anche i 3 test specifici delle configurazioni.

| Profilo | Boss px/tick | Missili | Direzione | Inseguimento | Musica |
| --- | ---: | --- | --- | --- | --- |
| 01 — Cattura | 1,6 | Assenti | 1800 ms, variazione 0,35 | Assente | 01pink.mp3 |
| 02 — Missili | 2,5 | 2400 ms, 4 px/tick | 1200 ms, variazione 0,8 | Assente | 02gold.mp3 |
| 03 — Pressione | 3,6 | 1200 ms, 5 px/tick | 600 ms, variazione 1,2 | Peso 0,35 sui tagli aperti | 03silver.mp3 |

Tutti partono con soglia **80%**, regolabile per profilo. Gli spari sono diretti
alla posizione del player al momento del lancio. Il livello 3 orienta anche il
boss verso il giocatore durante un taglio aperto; il solver continua a governare
muri e rimbalzi. Le velocità sono magnitudini per tick a 60 Hz, coerenti sia
allo spawn diagonale sia dopo i cambi AI: risolta l'incongruenza precedente.
I livelli 4–12 conservano una progressione parametrica, riusano `boss3.png` e
ciclano le quattro musiche; non sono dichiarati livelli già differenziati.

Gli asset attuali misurano **817×592**, **1240×711**, **1240×759**. Sono scalati
uniformemente nel box `BOSS_SIZE=(96,70)` e centrati sulla posizione logica.
`boss_size`, calcolato dal loader, è l'unica dimensione effettiva usata da sprite,
AABB e fallback grafico. Se il file manca/è corrotto si usa una primitiva 96×70
con AABB corrispondente. Gli originali non sono stati alterati.

### HUD e proiezione

Il precedente frame 800×600 scalato 1,28 occupava tutti i 1024×768: non esisteva
uno spazio esterno disponibile per l'HUD. Ora una fascia superiore di **48 px**
è riservata alla UI. L'area restante 1024×720 contiene il campo **960×720**,
centrato con margini laterali di 32 px. Trasformazione:
`x_finestra = 32 + x_logico × 1,2`, `y_finestra = 48 + y_logico × 1,2`.
Il rapporto del campo resta 4:3; nessun cambiamento alle 120.000 celle o alla
fisica. La trasformazione inversa esclude fascia HUD e margini.

`hud.py` disegna in coordinate di finestra **vite, percentuale/soglia, score
attuale**, livello, tempo e suggerimento. Il testo è memorizzato e rigenerato
solo quando i dati cambiano. Il punteggio resta per livello, senza introdurre
implicitamente uno score cumulativo. L'HUD viene composto dopo il campo e prima
di `flip()`, anche nelle schermate terminali. `RENDER_FPS_LIMIT` è ora **60**;
il passo fisico rimane separato e indipendente.

### Risultati misurati e verifiche

**116 test superati**: regressioni precedenti aggiornate ai nuovi contratti e
13 nuovi test. Coprono caricamento/immutabilità dei profili, tre asset e relative
AABB, assenza di spari nel tutorial, missile diretto nel livello 2 e inseguimento
nel livello 3; inoltre budget di cattura diversi con piano identico, confronto
con BFS indipendente su 25 campi frammentati, nessuna mutazione prima del commit,
score applicato una sola volta, pausa/cancellazione e HUD esterno. Restano verdi
le collisioni del muro x=200–201 px e il determinismo a 30/60/144 FPS.

Nuovo `tools/benchmark_capture.py`, eseguito separatamente dai test, con rendering,
HUD e SDL dummy; nessuna attesa del refresh:

| Misura | Taglio centrale | Cattura grande / vittoria |
| --- | ---: | ---: |
| Frame di cattura | 15 | 13 |
| Durata prevista a 60 FPS | 250,0 ms | 216,7 ms |
| Richiesta iniziale | 0,043 ms | 0,035 ms |
| Lavoro di cattura, massimo/frame | 4,074 ms | 4,196 ms |
| Frame completo CPU, mediana | 4,973 ms | 4,906 ms |
| Frame completo CPU, massimo | 7,721 ms | 7,132 ms |
| Percentuale finale | 51,160% | 85,693% |

Nei due casi misurati il frame completo resta sotto i **16,67 ms** disponibili
a 60 FPS, distribuendo il costo invece di concentrarlo in un frame da oltre
100 ms. Questi dati non certificano il monitor reale, il caso peggiore o ogni
PC: OS, lunghezza della scia e geometrie frammentate possono cambiare i tempi.
La cattura è una breve transizione con fisica sospesa, non una simulazione che
prosegue in parallelo. Il costo totale non sparisce, viene distribuito.

`tools/benchmark_resolution.py` aggiornato per attendere il completamento della
cattura e riportare frame e massimo del lavoro per frame. Smoke test a 800×600,
una ripetizione: lavoro completo 57,509 ms distribuito su 17 frame, massimo
4,137 ms/frame. Non confrontare una singola misura con mediane storiche come
prova definitiva di accelerazione. Verificati visivamente HUD e tutti e tre i
boss, più la separazione SVG/primaria dopo una cattura al 51,16%.

Prossimo lavoro: playtest dei tre livelli su monitor/audio reali, profilazione
di scie molto lunghe e geometrie avverse, poi score cumulativo e progressione
della campagna come scelte esplicite di design. La vertical slice implementa
la differenziazione richiesta, ma il suo bilanciamento non è ancora certificato.

## Consegna precedente — Viewport 1024×768 e tempo fisso

La sezione conserva la prima implementazione. Scala, HUD, sprite e cattura
sono stati successivamente aggiornati come descritto nella consegna corrente.

### Proiezione trasparente — `viewport.py`

Il loop crea la finestra a **1024×768** e una superficie logica a **800×600**.
`Game` riceve esclusivamente quest'ultima: griglia, coordinate, caricamento
degli asset, rivelazione, scia, boss, missili e HUD continuano a lavorare nello
spazio logico originale. `Game.draw()` disegna il frame completo;
`Viewport.present()` lo scala una volta e chiama `pygame.display.flip()`.

La trasformazione è `x_finestra = x_logico × 1,28` e
`y_finestra = y_logico × 1,28`, senza offset nel profilo corrente. Il centro
logico `(400, 300)` corrisponde a `(512, 384)`. Entrambi i rapporti sono 4:3:
nessun ritaglio o deformazione. Le funzioni `logical_to_window()` e
`window_to_logical()` centralizzano anche l'eventuale conversione di input
puntatore; le frecce attuali non richiedono conversioni. Con rapporti diversi
si usano bande centrate e l'input sulle bande viene escluso.

Il buffer scalato è riutilizzato; nearest-neighbor conserva la pixel art.
Il fattore frazionario comporta il normale arrotondamento dei pixel visualizzati,
senza arrotondare coordinate fisiche o cambiare celle. Boss e AABB restano
entrambi **96×70 logici**; l'ingombro proiettato è **122,88×89,6 px**, circa
123×90 sullo schermo, per entrambi. Tutti gli elementi, compresi cursore,
sfondi, scia, missili e overlay di pausa, ricevono la stessa trasformazione.

La BFS continua a lavorare su **120.000 celle**. Il +63,84% di celle dell'analisi
di una griglia logica 1024×768 non si applica a questo viewport. Aumentano
soltanto le superfici di presentazione e il costo della copia/scalatura finale.

### Tempo fisso — `game_state.py` e loop principale

La migrazione è **implementata**, non soltanto pianificata:

1. `FixedTimestep` legge una sorgente monotona in millisecondi, iniettabile nei
   test. Accumula credito intero `delta_ms × 60`: ogni tick consuma 1000 unità.
   La frazione residua resta al frame successivo; non si sommano approssimazioni
   float di 16,666… ms.
2. `Game.advance_frame()` campiona le direzioni e chiama `Game.update(keys)`
   zero, una o più volte. Ogni `update` è esattamente **1/60 s**; AI, spari,
   missili, boss e player vengono aggiornati nel loro ordine precedente.
   Le velocità esistenti sono ora esplicitamente per tick a 60 Hz: ad esempio
   il player percorre 60 celle/s e un missile 300 px logici/s.
3. `SimulationClock` conta soltanto i tick eseguiti. HUD, intervalli di sparo
   e variazioni AI usano questo unico tempo simulato. Il rendering non legge
   il tempo reale per alterare lo stato. Le scadenze usano `>=`: il cambio AI
   avviene al tick 60 e il primo sparo del livello 1 al tick 114 (1900 ms).
4. `Game.draw()` e `Viewport.present()` vengono eseguiti una volta per frame.
   `RENDER_FPS_LIMIT = 144` limita soltanto il rendering; `SIMULATION_HZ = 60`
   governa la simulazione. Viene mostrato l'ultimo stato fisico completato;
   non vengono prodotte pose interpolate che possano falsare il contatto visivo.

Le due responsabilità temporali sono distinte: `FixedTimestep` converte il tempo
reale in lavoro da eseguire; `SimulationClock` misura il lavoro effettivamente
simulato. Non esiste un timer AI reale parallelo al timer della fisica.
Il generatore casuale è ora locale a `Game` e iniettabile (`rng`): con lo stesso
seme e lo stesso input per tick, rendering più o meno frequente non consuma
estrazioni diverse. Questo garantisce le regressioni nello stesso ambiente;
un sistema di replay con input registrati e portabilità fra runtime resta un
eventuale sviluppo separato. L'input umano viene campionato al frame corrente,
senza ricostruire retroattivamente eventi durante uno stallo.

### Pausa, transizioni e sovraccarico

Pausa/ripresa e stati terminali azzerano l'accumulatore e riallineano la sorgente
reale. Il cambio livello lo azzera dopo caricamento e rasterizzazione. Un reset
interrompe anche un recupero già in corso: un Game Over al primo tick di un
frame con sei tick disponibili non simula i cinque successivi. Timer e audio
mantengono i contratti della pausa precedente; non avvengono salti alla ripresa.
Il piccolo credito inferiore a un tick viene scartato sulle transizioni.

`MAX_STEPS_PER_FRAME = 8` limita il recupero a circa 133,33 ms simulati per
frame. In uno stallo più lungo si scarta soltanto il debito eccedente di tick
interi, mantenendo il resto frazionario; `dropped_ticks` conta i tick scartati
dalla creazione dello scheduler. Non vengono allargati il passo fisico o i
substep, né saltate celle. In sovraccarico il tempo simulato rallenta rispetto
al tempo reale: è una limitazione esplicita, preferita a recuperi incontrollati.
I profili di test 30–240 FPS non scartano tick.

### Verifiche, risultati e prosecuzione

**103 test superati** con l'interprete `.venv` e driver SDL dummy:

- Stesso stato completo a **30/60/144 FPS** dopo 3 secondi: 180 tick, posizione
  e velocità del boss, missili, player, vite, punteggio, stato e RNG identici.
- Accumulatore a **30/60/75/120/144/240 FPS**: 600 tick in 10 secondi;
  nessuna deriva in 18.000 tick / 300 secondi simulati.
- Regressione runtime della parete **x=200–201 px** con boss e missile veloce:
  rimbalzo/assorbimento e risultato identici ai tre frame rate. Tutte le
  regressioni pure di geometria, solver e conquista della Fase 1 passano.
- Pause simulate di 60/120 secondi, audio senza riavvio del campione, intervalli
  residui di AI/spari, stati terminali e nuovo livello senza credito ereditato.
- Proiezione, trasformazione inversa, frame completo e bande su rapporto diverso;
  loop reale con eventi sintetici P, ripresa, perdita focus e Q.

Il primo run ha evidenziato due errori nella preparazione dei nuovi test:
la sorgente fittizia veniva riportata indietro fra profili dello stesso gioco
e i test del viewport non inizializzavano il display. Corretti i setup, senza
indebolire la validazione monotona o le regressioni fisiche.

Verificato visivamente un frame reale 1024×768 con copertura SVG, immagine
primaria sul bordo, HUD, sprite centrato, missile e scia. Microbenchmark locale
di `draw + present`, 20 warm-up e 200 campioni, stessa scena statica con SDL dummy:
mediana **1,048 ms**, P95 **1,565 ms**. È costo CPU del rendering in questo run,
esclude fisica/BFS e non misura sincronizzazione o fluidità del monitor reale.

Il consolidamento richiesto del tempo fisso è completato. Prossimi interventi:
ottimizzare la cattura sincrona, rendere coerenti percentuale iniziale e score,
quindi eseguire sessioni RC prolungate su monitor e audio reali. Il tempo fisso
non elimina il blocco del thread durante la BFS già misurato; lo contiene
senza introdurre movimenti fisici grandi dopo il blocco. L'eventuale cattura
distribuita su più frame richiede uno stato dedicato e mantiene i vincoli del
piano validato prima delle scritture.

## Consegna precedente — Missili continui, stati e pausa

### Dimensioni condivise del boss e label SVG

`BOSS_SIZE = (96, 70)` è usato sia dal ridimensionamento dello sprite sia da
`_boss_body()`. Il rettangolo fisico comprende l'intero ingombro dello sprite,
anche i pixel trasparenti. Non esiste più un raggio separato da 15 px. Il fallback
grafico usa lo stesso ingombro; fonte mancante o corrotta non cambia la fisica.

La variazione della hitbox è intenzionale: cambia distanze di contatto e
larghezza minima dei passaggi. Il corpo deve rimanere libero in **tutte** le sue
celle. Non viene ristretto automaticamente per entrare in corridoi piccoli.
I test di cattura e del muro 200–201 px sono stati aggiornati con partenze valide
per il nuovo corpo; sprite e AABB vengono confrontati direttamente.

Eliminate materialmente le dodici label centrali dagli SVG `01.svg`–`12.svg`.
Un test XML verifica che non ci siano elementi `<text>` in nessuno dei file,
oltre al controllo della rasterizzazione senza testo centrale. Gradiente e
bordo sono conservati. Il livello rimane indicato nell'HUD.

### Missili — `move_projectile()`

Il solver puro `collisions.py` ora gestisce anche proiettili AABB di **4 × 4 px**,
conservando la hitbox precedente dei missili e il disegno circolare di raggio 3.
Boss e missili condividono AABB, griglia, validazione dei dati e calcolo/budget
dei substep tramite `_substep_count()`.

Ogni substep è al massimo metà cella per componente. Per i missili viene
verificato il **segmento rettilineo**: l'intersezione temporale degli intervalli
sui due assi determina il primo contatto con muro, scia o player. L'inviluppo
seleziona soltanto i candidati; non trasforma una traiettoria diagonale in un
rettangolo solido o in uno zig-zag.

- Primo muro/confine: missile assorbito, senza rimbalzo.
- Prima scia/player vulnerabile: una sola perdita di vita e arresto del tick.
- Pari tempo di contatto: il muro ha priorità e protegge ciò che è oltre.
- Missile già dentro un'area appena conquistata: assorbito prima del movimento.
- Percorso privo di urti: spostamento intero, comprese le componenti frazionarie.
- Budget o dati numerici invalidi: tick rifiutato, nessun salto di celle.

`Game._update_missiles()` prepara i sopravvissuti prima di sostituire la lista.
È stato aggiunto anche il controllo del tratto appena creato dal player contro
i missili: non si attende il tick successivo per rilevare una sovrapposizione.

### Stati e tempo logico — `game_state.py`

Un solo stato autorevole: `PLAYING`, `PAUSED`, `LEVEL_CLEAR`, `GAME_OVER`,
`PHYSICS_ERROR`. `win` e `game_over` sono proprietà derivate; non si conservano
flag di stato indipendenti che possano contraddirsi.

**P** mette in pausa/riprende. La perdita del focus chiama la pausa; il ritorno
del focus non riprende automaticamente, per consentire al giocatore di essere
pronto. In `PAUSED`:

- `update()` non esegue boss, missili, AI, spari o movimento del player.
- L'input di direzione non modifica il tracciato o la direzione corrente.
- Il timer attivo del livello, mostrato nell'HUD, resta fermo.
- `pygame.mixer.pause()` e `music.pause()` sospendono effetti e stream musicale.
  La ripresa usa `unpause()`: la saldatrice non viene fermata e riavviata.

La prima versione di `SimulationClock` contava i millisecondi reali attivi,
escludendo le pause. È stata ora sostituita dal contatore di tick della consegna
corrente: spari, AI e HUD condividono il tempo fisso. Nuovo livello, vittoria,
Game Over ed errore fisico conservano i rispettivi reset/arresti. La pausa è
idempotente e non si attiva sopra uno stato terminale.

### Verifiche della consegna

**91 test**: 73 della baseline adattati alle nuove direttive, 8 sui proiettili,
4 sull'orologio e 6 di integrazione su missili/pausa. Nessun test temporale usa
sleep. Verificati pause di 60/120 secondi simulate, ritardo residuo degli spari,
nessun cambio AI anticipato, audio sospeso/ripreso e campione non riavviato.

Controllato il loop reale con eventi sintetici: P → `PAUSED`, P → `PLAYING`,
perdita focus → `PAUSED`, Q → chiusura pulita. Verificati visivamente l'HUD col
timer, lo sprite ingrandito e le schermate di gioco/pausa senza label SVG.

## Correzione preservata — Copertura SVG e immagine primaria

Regressione segnalata dall'utente: il livello partiva ancora nero e le catture
svelavano l'SVG invece della fotografia/immagine primaria. Il precedente
caricamento unificato aveva assegnato l'SVG a `hidden_image`: era una separazione
errata dei ruoli grafici, codificata anche nei precedenti test.

Correzione applicata:

- `load_level_cover()` accetta esclusivamente l'SVG e inizializza direttamente
  la canvas visibile. L'SVG sostituisce il nero nelle celle ancora libere.
- `load_level_image()` accetta PNG/JPG e inizializza `hidden_image`. Ripristina
  l'adattamento all'intero campo del prototipo, senza bande nere aggiuntive.
- `_reveal_pixel()` continua a copiare dalla primaria. La vittoria mostra la
  stessa primaria completa; il bordo iniziale, già sicuro, ne rivela i pixel.
- `Game.cover_source` e `Game.primary_image_source` espongono separatamente le
  sorgenti. La vecchia proprietà ambigua `background_source` è stata rimossa.
- Nessuna ulteriore superficie permanente: la canvas contiene inizialmente la
  copertura e viene aggiornata con i ritagli della primaria. La cache SVG
  conserva bytes PNG, non una canvas mutabile condivisa tra partite.
- Fallback indipendenti: SVG assente/corrotto → copertura neutra; primaria
  assente → immagine procedurale. Nessuno scambio fra i due ruoli.

Verifiche del task precedente: suite completa di **73 test**; sorgenti corrette per tutti i 12
livelli; caso con copertura rossa e primaria blu che controlla stato iniziale,
cattura, zona non conquistata e vittoria; PNG corrotto con fallback JPG;
SVG assente/corrotto e primaria mancante. Controllo visivo con gli asset reali.
La separazione copertura/primaria rimane verificata nella suite corrente.

## Fase 1B e 1C implementata

### Solver indipendente — `collisions.py`

Il modulo usa esclusivamente la libreria standard. Non legge Pygame, tastiera,
orologi o casualità e non modifica griglia, vite o entità del chiamante.

`AABB` è immutabile e conserva limiti float. Gli intervalli sono semiaperti,
la tangenza non è penetrazione. `CollisionGrid` è una vista su `cells[x][y]`:
forma stabile, aggiornamenti consentiti fra query, nessuna mutazione durante una
query. Fuori dal campo è solido.

`move_body()` implementa il contratto approvato:

1. Valida finitezza, rappresentabilità e corpo iniziale libero.
2. Calcola `N = max(1, ceil(max(abs(dx), abs(dy)) / (CELL_SIZE / 2)))`.
   Con celle di 2 px, ogni componente del substep è al massimo 1 px.
3. Risolve **X, poi Y**, in ordine fisso. Ogni segmento enumera le celle del
   corpo lungo il percorso, incluse le facce di contatto, e determina il primo
   ostacolo con sovrapposizione stretta sull'asse trasversale.
4. Porta il corpo alla tangenza esatta con la parete, riflette soltanto l'asse
   colpito e verifica/consuma il residuo nel nuovo verso. I substep successivi
   usano il verso aggiornato. Più rimbalzi nello stesso tick sono consentiti.
5. Risolve i pareggi con priorità muro, scia, giocatore; l'ordine delle celle è
   stabile per riga/colonna. Una minaccia oltre una parete non attraversata non
   colpisce il boss.
6. Restituisce nuova AABB, parità delle riflessioni, assi vincolati ed eventuale
   evento di contatto. Il chiamante applica la risposta una sola volta.

L'inviluppo `swept_bounds` è soltanto una selezione conservativa dei candidati:
non viene trattato come prova di urto diagonale. Un test di passaggio vicino a
un angolo protegge questa distinzione.

Un corridoio esattamente largo quanto il corpo non permette movimento su
quell'asse: il risultato lo marca come **vincolato**, il chiamante pone a zero
la relativa velocità e consente il movimento sull'altro asse. Questa regola
evita riflessioni infinite a distanza zero.

I budget diagnostici sono espliciti: massimo 4.096 substep/tick e 4.096 contatti
per segmento d'asse. Se vengono superati il movimento è rifiutato, senza
allargare il passo o saltare celle. Sono molto superiori ai 7 substep necessari
per 6,6 px/tick. Input invalidi non vengono riparati con teletrasporti.

### Integrazione runtime — `Upqix89.py`

`_move_boss()` chiama il solver, aggiorna il centro float e applica riflessioni
o vincoli alle velocità. La stessa AABB 96 × 70 serve per muri, scia e player;
il rendering conserva il suo arrotondamento separato. La scia viene interrogata
localmente tramite un insieme di celle, escludendo quelle già sicure.

AI, spari e timer vengono eseguiti una volta per tick di simulazione, non per
substep. Il movimento è espresso in pixel/tick a 60 Hz, indipendente dal
rendering grazie alla consegna corrente. Il solver rimane puro e non legge
tempo o RNG; il determinismo del gioco viene verificato con input e seme fissi
nello stesso ambiente.

Contatto con scia/player vulnerabile: perdita di una vita e arresto del tick.
Un tratto appena creato dal player viene controllato subito, dato che il player
si muove dopo il boss. Il vecchio controllo del solo centro e gli spostamenti
correttivi successivi al rimbalzo sono stati rimossi.

Stato fisico numericamente invalido: simulazione sospesa, saldatrice spenta,
diagnostica visibile e tasto **R** per riaprire il livello. Non vengono sottratte
vite o corrette arbitrariamente le coordinate per nascondere il problema.

### Conquista prima delle scritture — `territory.py`

`plan_capture()` costruisce un piano immutabile senza modificare dati di gioco:

- Verifica corpo del boss libero, scia senza duplicati, continuità ortogonale,
  celle entro il campo ed estremi in territorio sicuro.
- Controlla il contatto della nuova frontiera con **tutto il corpo** del boss.
  Un contatto genera `CaptureContactError`: il gioco perde una vita senza
  modificare griglia o canvas.
- Valida il seme BFS; usa la scia come barriera temporanea e visita la regione
  raggiungibile dal boss. Pianifica le celle libere non raggiunte.
- Verifica che nessuna cella selezionata invada il corpo del boss. Il controllo
  usa un piccolo insieme locale, evitando di duplicare in un set tutta l'area
  conquistata.
- Solo dopo la validazione `fill_area()` applica il piano a griglia e canvas.

Percentuale, soglia all'80% e punteggio del prototipo sono conservati: il bordo
iniziale è ancora incluso nella percentuale e le celle della scia non vengono
conteggiate nello stesso modo nel punteggio. La loro revisione resta separata.

## Integrazione degli sfondi SVG

### Problema riscontrato e scelta tecnica

Il caricamento SVG nativo di Pygame/SDL_image, nell'ambiente verificato, restituiva
per gli asset presenti una superficie trasparente senza errori. I file contengono
rettangoli con dimensioni percentuali e gradienti; il testo centrale presente
allora è stato ora rimosso. Non sarebbe sufficiente
cambiare l'estensione da PNG a SVG e considerare riuscito il caricamento.

Pygame documenta il supporto SVG, mentre SDL_image dichiara un supporto a SVG
semplici: la fedeltà va verificata sugli asset effettivi.
[Pygame image](https://www.pygame.org/docs/ref/image.html),
[SDL_image](https://wiki.libsdl.org/SDL2_image/FrontPage).

È stato quindi integrato **resvg_py 0.5.0**, renderer con wheel Windows, che
restituisce PNG in memoria. I parametri di rasterizzazione e font sono descritti
nella sua [API ufficiale](https://resvg-py.readthedocs.io/en/latest/api.html).
La dipendenza è installata nella `.venv` locale, senza installazioni globali.

### Pipeline operativa — `assets.py`

1. Cerca `public/assets/{level:02d}.svg` per la **copertura** al cambio livello.
2. Rasterizza alla dimensione richiesta. Usa il font incluso in Pygame come
   sostituzione esplicita per il testo, senza scansione dei font di sistema.
3. Conserva proporzioni, alpha compositato su nero e centratura. Se il viewport
   ha un diverso rapporto di aspetto, applica bande nere.
4. Memorizza il PNG in una cache limitata a quattro elementi, con chiave che
   include percorso, timestamp e risoluzione. Modificare un SVG invalida la cache.
5. Un errore SVG produce una copertura neutra, senza esporre la primaria.
   Separatamente carica la **primaria** PNG, poi JPG, poi immagine procedurale.
   Le sorgenti sono esposte da `Game.cover_source` e `Game.primary_image_source`
   e stampate nel log. La primaria viene adattata all'intero campo.

La rasterizzazione non avviene durante il movimento o durante la BFS. Il frame
loop riutilizza la canvas: la copertura SVG è visibile nelle celle libere,
mentre bordo e celle conquistate mostrano l'immagine primaria. Alla vittoria
appare la primaria completa. Sono stati verificati tutti i livelli **01–12**,
i gradienti della copertura e i pixel rivelati dalla primaria.

`start.bat`, locale ed escluso secondo la preferenza dell'utente, ora preferisce
l'interprete `.venv`. Avviando direttamente il gioco con un altro interprete,
installarvi prima le dipendenze di `requirements.txt`; in assenza del renderer
la copertura è neutra e l'immagine primaria resta disponibile.

### Workflow degli asset dopo questo task

L'integrazione dei dodici SVG è **completata**. Musica, boss e regole sono ora
nel registro `level_config`; l'immagine segue ancora la convenzione numerica.
Prossimi interventi: manifest completo delle immagini; eventuali SVG quadrati se si sceglierà
un campo 1:1; esportazione e controllo del pacchetto su PC pulito. I dodici SVG
sono stati modificati soltanto per eliminare le label centrali; le immagini
primarie non sono state modificate. Restano le copie JPG rinominate
PNG create dallo script storico, da razionalizzare in una fase dedicata.

## Analisi conservata — Griglia logica 1024 × 768 px

**Sì, 1024 × 768 è fattibile** e conserva il rapporto 4:3 di campo e SVG.
Questa tabella riguarda un aumento della **griglia logica**, valutato nella
consegna su missili e pausa. La consegna corrente ha attivato soltanto il viewport
1024×768: il campo simulato rimane 800×600. Le celle della colonna maggiore
non vengono quindi allocate dal gioco operativo.

| Voce | 800 × 600 | 1024 × 768 |
| --- | ---: | ---: |
| Rapporto | 4:3 | 4:3 |
| Griglia a celle di 2 px | 400 × 300 | 512 × 384 |
| Celle | 120.000 | 196.608 |
| Pixel | 480.000 | 786.432 |
| Tre superfici principali | 5,493 MiB | 9,000 MiB |

Le due dimensioni crescono del 28%; celle e pixel del **63,84%**. Gli SVG 4:3
possono riempire il quadro senza bande. Le immagini primarie continuano a essere
adattate all'intero campo.

Benchmark della consegna precedente, con boss e hitbox **96 × 70**, eseguito
isolatamente dalla suite: cinque tagli verticali centrali e 100 chiamate al solver
del boss. Non ripetuto per il solo cambiamento di presentazione e schedulazione.

| Misura | 800 × 600 | 1024 × 768 |
| --- | ---: | ---: |
| Pianificazione + BFS, mediana | 95,677 ms | 172,289 ms |
| Cattura completa, mediana | 132,045 ms | 221,307 ms |
| Cattura completa, min–max | 117,535–133,748 ms | 185,739–253,972 ms |
| Chiamata solver boss, mediana | 2,828 ms | 2,644 ms |

La piccola differenza fra i tempi del solver non indica che un campo più grande
sia più rapido: la query è locale, mentre i tempi variano col carico. La cattura
resta invece chiaramente oltre il budget di 16,7 ms a 60 FPS. Queste misure non
sono confrontabili direttamente con quelle storiche a hitbox 30 × 30.

Per ripetere:

```powershell
.\.venv\Scripts\python.exe tools/benchmark_resolution.py --repeats 5 --resolutions 800x600 1024x768
```

Lo strumento consente anche `1024x1024`; senza selezione esplicita misura tutti
e tre i profili. Nessuna soglia di performance viene trattata come test unitario.

**Raccomandazione attuata:** separazione fra finestra 1024×768 e campo logico
800×600, senza aggiungere celle. Dopo le presentazioni a scala 1,28 e 1,2, ora
il campo è inscritto nella cornice a 917×688 in `(52,66)`.
La stessa trasformazione proietta grafica e hitbox. Implementazione e verifiche
correnti sono descritte nella sezione iniziale di questo report.

Se si vuole realmente più terreno simulato, adottare 512 × 384 celle dopo
l'ottimizzazione della cattura e un nuovo collaudo del bilanciamento. A velocità
invariate aumenterebbe il tempo di attraversamento, e il boss fisso 96 × 70
occuperebbe una quota relativa minore del campo. Ogni eventuale ridimensionamento
del boss deve continuare ad aggiornare insieme sprite e AABB.

## Analisi storica: campo 1024 × 1024 px

La sezione seguente conserva la valutazione precedente. Le misure sono anteriori
all'aumento della hitbox del boss; per lo stato corrente fare riferimento al
confronto 800 × 600 / 1024 × 768 sopra.

### Perché oggi 800 × 600

Nei sorgenti e nel README originari **non è documentata la motivazione storica**:
800 × 600 è una costante del prototipo. Gli SVG presenti dichiarano anch'essi
800 × 600 e quindi condividono il rapporto **4:3**.

La scelta è coerente con un viewport desktop comune per un prototipo, con gli
asset esistenti e con un carico di griglia contenuto. Queste sono motivazioni
tecniche plausibili, **non una ricostruzione certa della decisione originaria**.
Non è emerso un limite di Pygame che imponga 800 × 600. La risoluzione maggiore
è fattibile; il vincolo pratico attuale è il costo della conquista sincrona.

### Dimensioni e complessità

| Voce | 800 × 600 | 1024 × 1024 |
| --- | ---: | ---: |
| Rapporto | 4:3 | 1:1 |
| Griglia a celle di 2 px | 400 × 300 | 512 × 512 |
| Celle | 120.000 | 262.144 |
| Pixel | 480.000 | 1.048.576 |
| Screen + hidden image + canvas, nel benchmark | 5,493 MiB | 12,000 MiB |

Celle e pixel crescono di **2,1845 volte**, cioè circa **+118,45%**. La BFS e
la scansione della griglia sono O(celle); la scrittura delle porzioni rivelate
dipende dalle celle conquistate. Anche gli insiemi Python di visita e il piano
di cattura occupano memoria proporzionale all'area. I MiB in tabella riguardano
solo le tre superfici, non memoria totale del processo o strutture della BFS.

### Misure riproducibili sul codice corrente

Strumento aggiunto: `tools/benchmark_resolution.py`. Esegue le funzioni di
produzione sotto una configurazione temporanea di test, **senza cambiare i
sorgenti o la risoluzione operativa**. Caso: taglio verticale centrale, boss
nella metà sinistra, circa metà campo conquistato. Cinque ripetizioni per
risoluzione; 100 chiamate per la misura del solver, senza scia attiva.

Sessione registrata nel task 1B–1C, eseguita separatamente dalla suite su questo
PC con SDL dummy, prima della correzione dei ruoli copertura/primaria. Il
benchmark non è stato ripetuto per la sola correzione grafica:

| Misura | 800 × 600 | 1024 × 1024 |
| --- | ---: | ---: |
| Pianificazione validata + BFS, mediana | 115,654 ms | 562,373 ms |
| Cattura completa, mediana | 169,743 ms | 948,602 ms |
| Cattura completa, min–max | 155,023–227,789 ms | 709,040–1154,585 ms |
| Chiamata solver, mediana | 0,849 ms | 1,671 ms |

I tempi dipendono da carico del computer, allocazioni e raccolta memoria; altri
run hanno mostrato valori inferiori. Non assumere il rapporto fra queste due
mediane come legge di scala o attribuirlo tutto al numero di celle. Il caso
misurato non copre ogni distribuzione delle aree né certifica il caso peggiore.
La conclusione stabile è che **la cattura supera ampiamente 16,7 ms**, budget di
un frame a 60 FPS, già a 800 × 600. A 1024 × 1024 gli scatti possono diventare
molto più evidenti.

Per ripetere, separatamente da test e altri carichi controllabili:

```powershell
.\.venv\Scripts\python.exe tools/benchmark_resolution.py --repeats 5
```

### Impatto sul solver e sulle proporzioni

Il solver esamina una regione **locale** attorno alla AABB e al segmento di
movimento, non tutta la griglia. A corpo, cella e velocità invariati,
il numero nominale di celle candidate/substep rimane simile anche su un campo
più grande. Non ci si aspetta un fattore 2,1845 obbligatorio nel suo costo.
Le misure locali sono sensibili al carico e alle allocazioni; vanno ripetute su
hardware target. In `Game` si aggiunge la costruzione dell'insieme della scia,
che dipende dalla lunghezza del tracciato. Ingrandire anche corpo o velocità
aumenterebbe rispettivamente candidati o numero di substep.

Il boss 96 × 70 occupa oggi il 12% della larghezza e circa l'11,67% dell'altezza.
Su 1024 × 1024 scenderebbe a circa 9,38% e 6,84%: apparirebbe relativamente
più piccolo. Un fattore uniforme 1,28 darebbe circa **123 × 90 px**, mantenendo
la quota di larghezza ma non quella di altezza. Il passaggio da 4:3 a 1:1 non
consente di mantenere entrambe senza cambiare composizione; deformare lo sprite
non è la soluzione. Per direttiva dell'utente, qualunque nuova dimensione del
boss deve essere applicata insieme a sprite e AABB tramite `BOSS_SIZE`.

Gli SVG attuali sono 4:3: il loader li inserisce in un viewport quadrato con
bande nere, comportamento già verificato a 1024 × 1024. Un campo quadrato pieno
richiederebbe risorse con viewport/viewBox 1:1 o una scelta esplicita di ritaglio.
Vanno inoltre rivisti velocità, tempo di attraversamento e densità dei pericoli:
più spazio a velocità invariata cambia il bilanciamento della partita.

### Raccomandazione e piano

**Non migrare ora il campo logico a 1024 × 1024.** Mantenerlo a 800 × 600 durante
la Fase 1. Il passaggio è fattibile, ma il flood fill attuale introduce un rischio
concreto di latenza eccessiva.

Prima della migrazione:

1. Completare il collaudo esteso da Release Candidate; i missili hanno ora collisioni continue.
2. Ottimizzare visita con memoria compatta/indici lineari, conteggi incrementali
   e rivelazione per intervalli invece di un blit per cella; confrontare regioni
   catturate con i test attuali.
3. Se necessario, distribuire la pianificazione su uno stato `CAPTURING` con
   simulazione sospesa e budget per frame, senza perdere i vincoli di cattura.
4. Risoluzione logica e viewport ora sono separati. Un eventuale profilo quadrato
   richiede ancora asset, scala grafica e bilanciamento espliciti; la presentazione
   può essere valutata separatamente dal numero di celle simulate.
5. Ripetere benchmark su casi piccoli/grandi, forme concave, scie lunghe e PC
   target; attivare il nuovo profilo soltanto con risultati accettabili.

## Verifiche e limiti residui

Suite corrente: **248 test superati** con:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Copertura: muro 200–201 px nei due versi e nel runtime, alta velocità, muri
orizzontali, angoli, tangenze, residuo, rimbalzi multipli, asse vincolato,
scia/player lungo il percorso, protezione dei muri, input invalidi, ripetibilità,
densità dei substep nei casi di riferimento, missili rettilinei/diagonali senza
tunnelling, catture concave e senza scritture parziali, audio e timer in pausa,
respawn, vittoria/livelli, tutte le coppie SVG/primaria, gradienti senza label,
cache, fallback separati, viewport quadrato e rendering del boss.
La Fase 4 aggiunge Scossa, score/bonus, scaling del player senza variazioni
fisiche, curva e soglie dei dodici livelli, determinismo sotto pressione.

Diagnostica storica sul precedente corpo del boss: **3.000 movimenti**, seme 1989 e componenti casuali
comprese fra −25 e +25 px/tick, mantenendo sempre il corpo libero. Una sequenza
più breve è conservata come regressione automatica. Controllo visivo di sfondo
intero, cattura parziale e inserimento 4:3 nel viewport quadrato.

I driver dummy non verificano ascolto reale, latenza degli altoparlanti,
presentazione sul monitor o difficoltà dei dodici livelli. Non sono stati
certificati tutti i casi patologici di geometria: 1D resta aperto.

Problemi ancora da affrontare:

- **Bilanciamento:** velocità normalizzate, Scossa e dodici profili progressivi implementati;
  difficoltà e ritmo devono essere verificati giocando sul dispositivo reale.
- **Cattura:** cooperativa e misurata nei casi descritti; da profilare su scie
  estreme e geometrie avverse. Score ancora per livello, scia esclusa dal conteggio.
- **Collaudo RC:** sessioni prolungate sul dispositivo reale e bilanciamento del
  boss più grande, oltre ai test automatici già superati.
- **Asset:** cursore corrotto non ancora gestito; duplicati grafici e provenienza/
  licenze da inventariare prima della distribuzione pubblica.

## Contesto conservato e roadmap generale

Progressione delle consegne:

| Consegna | Risultato |
| --- | --- |
| Prima revisione | Audio saldatrice, percorsi stabili, spawn e respawn, 19 test |
| Boss2 | Alpha/proporzioni/centratura e hitbox indipendente, 22 test |
| Passo 1A | Geometria pura, boss raddoppiato, prima attenuazione, 39 test |
| Passi 1B–1C e SVG | Solver integrato, conquista validata, 12 SVG, analisi risoluzione e nuova richiesta audio, 70 test |
| Correzione copertura/primaria | SVG visibile da subito e PNG/JPG svelata, ruoli e fallback separati, 73 test |
| Chiusura collisioni / avvio Fase 2 | Missili continui, boss e AABB 96×70, stati/pausa/timer e SVG senza label, 91 test |
| Viewport / tempo fisso | Proiezione 800×600 → 1024×768, accumulatore 60 Hz, tempo simulato unico e regressioni a FPS diversi, 103 test |
| Cattura / vertical slice | CAPTURING cooperativo, scanline e commit isolato, 3 boss/configurazioni, HUD esterno e score, 116 test |
| Ripristino / cornice | Spari originali verso il player, Cornice_gioco con pannelli HUD e ritaglio proporzionato degli sfondi, 120 test |
| Fase 4 / preparazione Fase 5 | Player 2×, Scossa modulare, score/bonus area-tempo, curva di 12 livelli e missili progressivi, 140 test |
| Fasi 5/6 desktop | Run Score, riepilogo/finale, menu, classifica atomica, manifest JSON e nuove dimensioni, 157 test; Web progettato separatamente |
| Scossa / sprite energia | PerimeterThreat sui contorni aggiornati, collisione continua, sprite scossa condiviso e orientato, 178 test |
| Gameplay / i18n / controller | Dodici boss, AABB player completa, frontiera, 5 vite/premi/scudi, doppie scosse, cicli, cataloghi IT/EN e joystick; 207 test |
| Debug / audio / premi | Vita extra al 74%, avvio debug solo in memoria, premi combinati, MP3 dinamici/shuffle e lingua a caldo; 221 test |
| Audit vite / respawn | Riprodotte morti multiple da input mantenuto; interruzione del recupero alla morte e rilascio richiesto per ripartire, 15/99 vite e percorso menu/finale verificati; 233 test |
| Localizzazione / morte | Scossa/Shock uniforme, stato DYING, sette fotogrammi/audio e mondo congelato, respawn/finale differiti e regressioni a FPS diversi; 248 test |

Il gioco comprende una prima vertical slice di 3 livelli su una campagna
giocabile di 12, con 5 vite iniziali, vita extra al 74%, scudi per tagli ≥25%,
obiettivo dal 70% all'86% nel ciclo 1, movimento ortogonale continuo sul confine e
morte per autointersezione. Gli spari sono presenti fin dal primo livello,
sempre più veloci e frequenti con la progressione. Il Run Score persiste tra
livelli, con riepiloghi e bonus consolidati alla vittoria. Dopo il dodicesimo
livello appare la scelta tra nuovo ciclo più difficile e registrazione del risultato.
Menu navigabile da tastiera/controller, tutorial IT/EN e
classifica personale JSON sono implementati. Restano aperti il port browser,
la classifica pubblica verificata sul backend, packaging, impostazioni e
collaudo esteso del bilanciamento e dei comportamenti dei boss.

| Fase | Stato / consegna successiva |
| --- | --- |
| 1A | Completata: AABB/griglia e regressione del muro |
| 1B | Completata: substep, primo contatto e residuo |
| 1C | Completata: boss runtime e validazione della conquista |
| Collisioni missili | Completate: primo impatto continuo e assorbimento |
| 1D / collaudo RC | Regressioni automatiche estese; sessioni reali prolungate e bilanciamento ancora da completare |
| Fase 2 — stati/pausa | Implementati: P, focus, timer attivo e sospensione/ripresa audio |
| Fase 2 — tempo fisso | Implementato: tick 60 Hz, rendering separato, transizioni senza arretrati e budget di recupero |
| Viewport / HUD | Implementati: Cornice_gioco nella finestra 1024×768, pannelli HUD e campo 917×688; logica 800×600 invariata |
| Fase 2 — cattura | Implementata: lavoro a blocchi, piano scanline e commit isolato, 4 ms/frame di budget |
| Consolidamento restante | Playtest e profilazione di scie/geometrie avverse |
| Fluidità e controllo | HUD score/bonus/tempo implementato; restano impostazioni dei volumi e collaudo sul dispositivo reale |
| Vertical slice | Tre profili/boss implementati; spari diretti in tutti i livelli e inseguimento nel terzo; bilanciamento da collaudare |
| Fase 4 — Varietà e bilanciamento | Implementati AABB player completa, scudi, vita extra, doppie scosse e dodici asset; resta il playtest |
| Fase 5 — Campagna | Manifest, Run Score per ciclo/livello, riepiloghi e scelta dei cicli con limiti espliciti implementati |
| Fase 6 — Desktop | Menu/tutorial IT/EN, input controller e classifica personale implementati; pacchetto e collaudo hardware ancora aperti |
| Release Web | Piano React/Vite/Vercel e contratto API/SQL pronti; build browser, backend e replay autorevole non deployati |

## Riferimenti arcade e direzione di design

**Qix (1981)**: nemico nel campo, Sparx lungo le linee sicure, avanzamento rapido
o lento con premio di punteggio; nella versione descritta da Taito la soglia è
75%. **Volfied (1989)**: conquista all'80% e vulnerabilità di nave/linee incomplete
quando la barriera è disattivata.
[Taito — Qix](https://www.taito.co.jp/egret2mini/title),
[Taito Milestones](https://www.taito.co.jp/taitomilestones/titles),
[HAMSTER — Volfied](https://www.arcadearchives.com/en/title/aca-301/).

La documentazione storica riportata da
[Arcade Database](https://adb.arcadeitalia.net/dettaglio_mame.php?game_name=qix)
descrive anche scossa contro le esitazioni, ricompensa della modalità lenta e
separazione dei due Qix. Sono meccaniche da valutare singolarmente dopo il core.

Direzione approvata: identità vicina a Volfied, con immagine rivelata, boss LUKSO,
soglie progressive (70–86% dopo la Fase 4) e decisioni geometriche. Insegnare prima rischio della scia e rientro,
anticipare visivamente gli spari, premiare il confinamento. Aggiungere una sola
pressione contro l'attesa, poi pochi potenziamenti leggibili e l'eventuale doppia
velocità. Due boss richiederanno BFS da entrambi oppure una condizione esplicita
di vittoria per separazione: non riutilizzare la BFS da un solo seme.

La strategia attuale resta preparare chiusure corte e sicure, poi confinare il
boss nella regione piccola per conquistare quella maggiore. Ogni tratto della
scia è vulnerabile. Il bordo rimane silenzioso: la saldatrice segnala soltanto
il tracciamento nel campo libero.
