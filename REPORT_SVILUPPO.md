# UPIX 1989 — Revisione tecnica e piano di sviluppo

Data: **7 novembre 2026**. Revisione di README, sorgente principale, vecchio prototipo locale, launcher, script immagini e asset. Ambiente: Windows, Python 3.13.5, Pygame 2.6.1 / SDL 2.28.4.

## Stato operativo aggiornato — Task asset boss e avvio Fase 1

- Piano generale approvato dall'utente; obiettivo: consolidamento verso Release Candidate.
- **Regola vincolante:** qualsiasi comando/operazione Git, anche di sola lettura,
  appartiene esclusivamente all'utente. Regola salvata anche in `AGENTS.md`.
  Nessun comando Git eseguito in questo task.
- **Completato:** integrazione definitiva di `public/icon/boss2.png`, preservazione
  alpha e proporzioni, centratura e separazione dei parametri grafici/fisici.
- **Verifica:** 22 test superati (19 precedenti + 3 regressioni sul boss),
  controllo visivo di un frame reale renderizzato con SDL dummy e ingrandimento
  dello sprite su sfondo scuro.
- **Fase 1 collisioni:** specifica tecnica definita nella sezione dedicata sotto;
  il sub-stepping non è ancora implementato. L'attraversamento dei muri rimane
  un problema aperto: non confondere l'aggiornamento grafico con la sua soluzione.
- Prossima consegna: solver del movimento del boss con substep e relative
  regressioni, prima dell'estensione ai missili e della migrazione al tempo fisso.

### Dettaglio dell'aggiornamento grafico

`boss2.png` è un PNG RGBA di **817 × 592 px**. Il verde presente nei canali RGB
dello sfondo è trasparente tramite alpha: non va rimosso con una colorkey.
Il vecchio codice usava `convert()` e il colore dell'angolo come trasparenza;
ora `_load_boss_sprite()` usa `convert_alpha()` e ridimensionamento proporzionale
nearest-neighbor, adatto allo stile pixel art.

Parametri espliciti in `Upqix89.py`:

| Parametro | Valore e responsabilità |
| --- | --- |
| `BOSS_SPRITE_FILENAME` | `boss2.png`, unica risorsa grafica del boss |
| `BOSS_SPRITE_MAX_SIZE` | 40 × 40 px; dimensione risultante attuale 40 × 29 |
| `BOSS_COLLISION_RADIUS` | 15 px; conserva la hitbox ordinaria esistente, senza dipendere dallo sprite |
| Posizione grafica | `Rect.center = (round(enemy_x), round(enemy_y))`, offset aggiuntivo zero |

La simulazione mantiene le coordinate float; l'arrotondamento riguarda soltanto
il rendering. Nessuna deformazione quadrata e nessuna correzione della posizione
fisica per adattarla all'immagine. La hitbox attuale contro scia/player rimane
un quadrato di lato 30 px; la collisione con i muri resta ancora basata sul centro.

Asset mancante o corrotto: messaggio diagnostico e cerchio di raggio 15, senza
ricaricare `boss.png`. Nel vecchio fallback il raggio diventava 4: ora l'assenza
della grafica non modifica la fisica. Il file storico non è stato eliminato.

Nuove regressioni: proporzioni e alpha dell'asset reale; compositing e centratura
su posizione frazionaria senza mutare la simulazione; fallback mancante/corrotto
con hitbox invariata e nessun recupero implicito del vecchio sprite.

## Stato dello sviluppo

UPIX ha un ciclo giocabile completo: partenza, tracciamento, chiusura, rivelazione dell'immagine, morte/respawn, vittoria, livelli e riavvio. Griglia e flood fill inverso sono una base appropriata. La classe `Game` concentra però quasi tutte le responsabilità; prima di aggiungere altri sistemi conviene consolidare collisioni, tempi e prestazioni della cattura.

La definizione corretta è **prototipo giocabile da consolidare**. I problemi sotto non annullano il funzionamento nelle partite ordinarie, ma riguardano casi riproducibili e vincoli ancora non garantiti.

| Sistema | Stato verificato |
| --- | --- |
| Campo | 800 × 600 px, griglia 400 × 300, celle di 2 px |
| Giocatore | Sprite LUKSO, movimento ortogonale continuo, aree conquistate sicure |
| Tracciamento | Percorsi ortogonali, blocco dell'inversione, morte per autointersezione |
| Conquista | BFS dal centro del boss; riempimento delle zone non raggiungibili |
| Nemici | Un boss con deviazioni casuali e missili diretti al giocatore |
| Progressione | 12 immagini, soglia 80%, 3 vite, velocità/frequenza spari crescenti |
| Audio | 4 musiche; saldatrice ora gestita sullo stato di tracciamento |
| Fine partita | Game Over e riavvio; dopo il dodicesimo livello si ricomincia |
| Punteggio | Interno, azzerato per livello, non mostrato |
| Mancante | Menu, pausa, impostazioni, classifica, boss differenziati, potenziamenti |

## Modifiche applicate

### Audio: diagnosi e correzione

`Sound.play(-1)` era già presente: non mancava il comando di riproduzione. Il file si decodifica correttamente. L'analisi PCM ha rilevato:

- Durata decodificata circa **8,70 s**.
- Silenzio/quasi silenzio iniziale di circa **0,19 s**, misurato con FFmpeg a −42 dB; RMS dei primi 100 ms circa 1,9 su scala s16.
- RMS dell'effetto circa **1.070**, contro circa **7.880** della prima musica, prima dei volumi del gioco.
- Con i vecchi volumi, effetto 0,50 e musica 0,26, livello medio stimato dell'effetto circa **12 dB inferiore** alla musica. È una misura indicativa del mascheramento, non una misura percettiva LUFS.

Questi dati spiegano una possibile scarsa udibilità, soprattutto nelle tracce brevi. Non dimostrano quale uscita audio fosse attiva nella sessione dell'utente.

Interventi:

1. Preparato `saldatrice.wav` dallo stesso MP3: taglio iniziale di 0,30 s, guadagno ×2, limitatore e brevi fade. Originale conservato e non modificato.
2. Riservato il canale 0: il loop non dipende dalla selezione automatica dei canali e non riparte a ogni frame.
3. Centralizzata la sincronizzazione: effetto attivo quando si disegna in una cella libera, senza vittoria o Game Over.
4. Musica temporaneamente a 0,10 durante il disegno, ripristinata a 0,26 alla fine; effetto a 0,80.
5. Arresto su conquista, morte, Game Over, nuovo livello, riavvio e uscita. Gli errori audio lasciano il gioco utilizzabile.

Il canale riservato è previsto dalla [documentazione Pygame](https://www.pygame.org/docs/ref/mixer.html); la musica usa lo [stream separato di mixer.music](https://www.pygame.org/docs/ref/music.html).

**Resta da verificare all'ascolto il bilanciamento sugli altoparlanti dell'utente.** Il fallback MP3 conserva l'attacco e il livello della registrazione originale: distribuire il WAV preparato.

### Correzioni e preparazione del repository

| Modifica | Motivo |
| --- | --- |
| Spawn sulla riga 298 anziché 297 | Il bordo inferiore occupa 298–299: prima il cursore partiva nel campo libero |
| `last_safe_x/y` aggiornati dopo la conquista | Respawn corretto anche iniziando subito una nuova traccia |
| Pulizia di scia, direzione e missili anche all'ultima morte | Stato terminale coerente |
| Percorsi da `__file__` | Asset disponibili da qualsiasi directory di avvio |
| Inizializzazione Pygame in `main()` | Import senza finestra e senza attivare l'audio |
| Display passato a `Game` | Meno globali e rendering verificabile nei test |
| Errori mirati su musica e sfondi | Diagnostica senza nascondere qualsiasi errore con `except` generico |
| Playlist riallineata nel ciclo 12 → 1 | Ripartenza dalla prima traccia |
| `requirements.txt` | Versione Pygame riproducibile nell'ambiente verificato |
| `.gitignore` | Cache, ambienti, log e configurazioni personali esclusi |
| Launcher locale | Directory corretta e visualizzazione degli errori di avvio |
| README | Regole reali, audio, installazione e test; corretta la descrizione di algoritmo “infallibile” |

Movimento automatico, soglia dell'80%, bilanciamento dei nemici e impostazione della conquista sono rimasti quelli del prototipo.

## Verifiche e limiti

**Baseline della prima revisione: 19 test automatici superati**, con
`python -m unittest discover -s tests -v`. La suite attuale contiene **22 test**,
inclusi quelli descritti nel registro operativo iniziale.

Copertura della baseline:

- Partenza e movimento sicuro silenziosi; loop singolo nel campo e musica attenuata.
- Chiusura, riattivazione alla traccia successiva e aggiornamento del respawn.
- Morte normale/finale, autointersezione e collisioni ordinarie boss/missile contro la scia.
- Assorbimento ordinario dei missili in zona sicura.
- Conquista opposta al boss e vittoria oltre l'80%.
- Cambio livello, ciclo campagna e riavvio senza loop residuo.
- Decodifica e rendering di tutti i 12 sfondi.
- Caricamento da un'altra directory; fallback senza asset e senza dispositivo audio.
- Fallback MP3 e segnale non silenzioso nei primi 100 ms del WAV.
- Import senza inizializzare Pygame.

I driver SDL dummy non certificano ascolto reale, latenza, resa visiva o bilanciamento dei livelli. I test non coprono ogni collisione: le diagnostiche seguenti dimostrano lavoro ancora necessario.

## Interventi proposti, in ordine di priorità

### P1 — Collisioni continue e vincoli del boss

**Difetto riprodotto:** muro verticale largo una cella, x = 200–201 px. Il boss da x = 196 con velocità 6,6 arriva a x = 202,6 senza rilevarlo. Un missile da x = 198 con velocità 5 arriva a x = 203 e resta attivo. Sono valori compatibili con il gioco.

Si controlla soltanto la cella finale. Il boss usa il centro per urtare i muri e un rettangolo più grande per colpire la scia: la forma fisica non è coerente. Il rimbalzo inverte entrambi gli assi e aggiunge uno spostamento che può produrre altri attraversamenti.

**Proposta:** esaminare tutte le celle attraversate dal movimento, con substep limitati o scansione della griglia. Risolvere gli assi separatamente e mantenere il boss in una cella libera. Definire una hitbox coerente e il comportamento nei corridoi più stretti del suo diametro. Per i missili stabilire l'ordine effettivo fra urto con scudo e scia lungo il segmento.

**Accettazione:** muri di una cella impermeabili a tutte le velocità; test su urti obliqui, angoli, corridoi e frontiere appena conquistate. `fill_area()` deve validare il seme prima di modificare la griglia: partire da una cella `FILLED` invalida le assunzioni della BFS.

### P1 — Tempi e velocità coerenti

Il giocatore avanza di una cella per frame, boss/missili usano pixel per frame e gli spari usano millisecondi. A FPS bassi cambiano le distanze percorse fra gli spari. La velocità diagonale iniziale del boss è maggiore di quella normalizzata dopo il primo cambio casuale.

**Proposta:** simulazione a passo fisso, ad esempio 60 aggiornamenti/s, separata dal rendering con accumulatore e recuperi limitati. Per il giocatore accumulare il tempo necessario a percorrere una cella. Azzerare l'accumulatore dopo la pausa.

**Accettazione:** stessa distanza e sequenza temporale degli spari con rendering a 30/60/144 FPS, usando una simulazione deterministica; norma della velocità coerente dalla partenza.

### P1 — Cattura senza scatti e contabilità dell'area

Cinque catture con taglio verticale completo hanno richiesto **106,5–145,4 ms**, mediana **126,0 ms**, su questo PC in modalità headless. Non è un benchmark universale. Il budget a 60 FPS è 16,7 ms: `fill_area()` può bloccare più frame.

**Proposta progressiva:** misurare BFS/scansione/blit separatamente; usare una struttura compatta di visita; contatore incrementale delle celle; blit per intervalli di riga anziché per cella. Conservare la scia come lista ordinata con un set parallelo per l'appartenenza, oggi lineare. Se necessario, introdurre uno stato `CAPTURING` che congela la simulazione e distribuisce l'aggiornamento visivo su più frame.

Decidere anche se la percentuale misura solo terreno conquistabile. Oggi comprende il bordo ma parte da zero sul display. Il punteggio non tratta le celle della scia allo stesso modo delle altre celle catturate. Separare `initial_safe_cells`, `captured_cells`, `level_score` e `run_score`.

**Accettazione:** nessuno scatto percepibile sul dispositivo target; percentuale coerente prima/dopo il primo taglio; stesse regioni conquistate su percorsi concavi e corridoi di una cella.

### P2 — Stati, pausa e moduli

Estrarre gradualmente `settings`, `grid`, `player`, `enemies`, `audio`, `rendering` e coordinamento `game`, mantenendo `Upqix89.py` come entry point. La logica della griglia dovrebbe poter funzionare senza display.

Stati suggeriti: `MENU`, `PLAYING`, `CAPTURING`, `PAUSED`, `DYING`, `LEVEL_CLEAR`, `GAME_OVER`, `CAMPAIGN_CLEAR`. Priorità a pausa e perdita del focus: oggi simulazione e pericoli continuano quando la finestra non è attiva. La pausa dovrà sospendere saldatrice e timer.

Non serve ancora un framework di entità generico: moduli piccoli e dipendenze esplicite bastano.

### P2 — Asset e distribuzione

`public/` occupa circa **88,54 MiB**, incluso il nuovo WAV. Esistono **12 coppie identiche**, per **27,18 MiB** ridondanti. Le immagini numerate `.png` hanno firma JPEG: lo script le copia, non le converte.

**Proposta:** manifest dei livelli che punti ai nomi originali, oppure vera esportazione al formato scelto. Eliminare duplicati dopo aver aggiornato i riferimenti e verificato il pacchetto. Separare sorgenti grafici e asset distribuiti. Il manifest conterrà immagine, musica, boss, velocità, spari, soglia e regole.

Le icone mancanti hanno fallback. Il boss ora gestisce anche file corrotto;
il cursore presente ma corrotto può ancora interrompere l'avvio. Estendere gli
errori mirati e controllare il manifest prima della partita. La warning
`pkg_resources` proviene da Pygame: monitorare un aggiornamento compatibile senza
pin casuali ad altre dipendenze. Le misure dello spazio occupato sopra appartengono
alla prima revisione, precedente all'aggiunta di `boss2.png`.

Prima della pubblicazione completare l'inventario di provenienza e licenze di immagini/musiche: nei file esaminati non è documentato. Nessun asset è stato sostituito o eliminato e non sono state attribuite licenze non presenti.

## Riferimenti arcade e direzione di gioco

**Qix è del 1981**, mentre **Volfied è del 1989**. Taito descrive Qix con due modalità di avanzamento e più punti per la cattura lenta; la soglia della versione presentata su EGRET II mini è 75%. Volfied usa l'80% e rende vulnerabili nave e linee incomplete quando la barriera è disattivata. Fonti: [Taito — Qix](https://www.taito.co.jp/egret2mini/title), [HAMSTER — Volfied](https://www.arcadearchives.com/en/title/aca-301/).

Qix combina il nemico nel campo con gli Sparx che seguono le linee sicure: ruoli confermati da [Taito Milestones](https://www.taito.co.jp/taitomilestones/titles). La documentazione storica riportata da [Arcade Database](https://adb.arcadeitalia.net/dettaglio_mame.php?game_name=qix) descrive anche miccia legata alle esitazioni, premio per la modalità lenta e separazione di due Qix. Sono meccaniche da valutare singolarmente.

La lezione di design è la scelta fra spazio conquistato, tempo di esposizione e rientro sicuro. UPIX possiede già questo nucleo; il bordo sempre sicuro e i missili schermati consentono però attesa indefinita. Questa è una valutazione derivata dal confronto, non una nuova regola già implementata.

### Direzione consigliata

Mantenere **conquista all'80%, cursore LUKSO, immagine rivelata e boss caratterizzati**, con base vicina a Volfied. Recuperare da Qix le decisioni geometriche e introdurre le varianti separatamente:

1. **Insegnare il rischio della scia:** primo livello leggibile, boss lento, primi secondi senza spari e vulnerabilità chiaramente segnalata.
2. **Premiare la pianificazione:** tagli lunghi più redditizi ma esposti; penisole corte come preparazione a chiusure successive; bonus chiaro quando si supera ampiamente la soglia.
3. **Anticipare gli attacchi:** segnale visivo/sonoro prima dello sparo. Aumentare la velocità dopo aver reso affidabili le collisioni.
4. **Una pressione contro l'attesa:** provare un nemico perimetrale oppure uno scudo a consumo, separatamente. La saldatrice resterà comunque silenziosa in zona sicura.
5. **Due velocità come variante successiva:** rapido per sicurezza, lento per più punti, con colori e comando espliciti. Prima occorre mostrare il punteggio e stabilire i tempi.
6. **Potenziamenti leggibili:** rallentamento del boss o velocità di tracciamento, con durata visibile. Valutare uno o due effetti prima di aggiungere armi e combinazioni.

La sicurezza deve restare prevedibile: un nemico che in futuro attraversa il territorio conquistato deve farlo per una regola insegnata e segnalata.

### Strategia con il gioco attuale

- Partire lontano dal boss e dalla traiettoria degli ultimi missili.
- Preferire inizialmente chiusure corte, poi usarle per preparare tagli importanti: tutta la scia resta vulnerabile.
- Lasciare il boss nella regione più piccola: si conquista ciò che non raggiunge, non necessariamente la regione geometricamente più piccola.
- Pianificare il rientro prima di uscire: autointersezione e inversione non sono vie di fuga.
- Sfruttare il ritmo degli spari. Finché non si correggono le collisioni, un muro di una cella non è una difesa completamente affidabile.

Questi consigli sono dedotti dal codice UPIX e andranno rivalutati con il bilanciamento futuro.

## Roadmap

Fasi ordinate per dipendenza, senza stime temporali arbitrarie.

| Fase | Consegna | Criterio per proseguire |
| --- | --- | --- |
| 1 — Consolidamento | Collisioni continue, seme valido, tempo fisso, percentuali coerenti | Muri sottili impermeabili, boss sempre in celle libere, simulazione indipendente dagli FPS |
| 2 — Fluidità e controllo | Cattura ottimizzata, pausa/focus, HUD score, volumi | Nessuno scatto nelle catture target; pausa senza avanzare timer o perdere vite |
| 3 — Vertical slice | Tre livelli con tutorial e boss diversi | Regole comprensibili senza spiegazione esterna e difficoltà crescente verificata giocando |
| 4 — Varietà | Una pressione anti-attesa e uno/due potenziamenti | Ogni aggiunta introduce una decisione riconoscibile; il disegno rimane centrale |
| 5 — Campagna | Manifest dei 12 livelli, score cumulativo, bonus e finale | Campagna completabile, progressione e riavvio coerenti |
| 6 — Release | Menu, impostazioni, classifica, pacchetto Windows, crediti | Avvio su PC pulito senza Python, asset inclusi e sessioni prolungate senza blocchi |

Per i tre livelli iniziali: il primo insegna cattura/rientro; il secondo introduce spari anticipati; il terzo cambia il comportamento del boss e premia il confinamento. Costruire gli altri nove dopo questa validazione, anziché differenziarli soltanto per immagine e velocità.

Due boss richiedono una scelta: conservare entrambe le regioni nemiche oppure vincere separandoli. La BFS attuale da un solo boss catturerebbe erroneamente il territorio dell'altro.

## Fase 1 — Specifica tecnica del sub-stepping del boss

**Stato: progettazione completata, implementazione da eseguire.** Il task attuale
richiede l'avvio della pianificazione collisioni; il movimento runtime non è
stato sostituito. La grafica del boss è già operativa.

### 1. Contratto fisico e geometria

- Posizione logica: centro float `(enemy_x, enemy_y)` in pixel.
- Forma scelta: **AABB 30 × 30 px**, semiestensioni `(15, 15)`, coerente con la
  hitbox attuale contro scia/player. La sprite, inclusi catene e alpha, non è
  una maschera fisica. Eventuale diversa hitbox richiederà una decisione di design.
- Celle: rettangoli di lato `CELL_SIZE`; `FILLED` è solido. Fuori dalla griglia
  è solido. Il boss può essere tangente a un muro, non compenetrarlo.
- Usare intervalli geometrici semiaperti e confronti float espliciti, senza
  convertire il corpo in `pygame.Rect` interi durante la simulazione.
- Una candidata AABB interroga tutte le celle nell'intervallo
  `floor(left / CELL_SIZE)` … `ceil(right / CELL_SIZE) - 1` e analogo per Y.
  Filtrare con sovrapposizione stretta: la tangenza non è penetrazione.
- Precondizione e postcondizione: corpo dentro il campo libero e centro in una
  cella `EMPTY`. Una posizione iniziale invalida è un errore di stato da segnalare
  prima di muovere; niente teletrasporti o spostamenti correttivi arbitrari.

Questo renderà il boss più coerente anche visivamente: oggi il corpo può
oltrepassare un muro finché il suo centro non lo tocca. Sarà una correzione fisica
esplicita da verificare nelle aree strette, non un effetto della nuova immagine.

### 2. Suddivisione deterministica del movimento

Per il vettore di spostamento richiesto `(dx, dy)`:

```text
max_axis_step = CELL_SIZE / 2                 # 1 px con la griglia attuale
N = max(1, ceil(max(abs(dx), abs(dy)) / max_axis_step))
substep = frazione 1/N del movimento di un tick
```

Con 6,6 px su un asse risultano 7 substep. Non usare un numero fisso di campioni,
né limitare N aumentando lo spostamento del singolo substep: reintrodurrebbe il
tunnelling. Validare finitezza di coordinate e spostamenti prima della divisione.

Ogni substep risolve X, poi Y, in ordine fisso. Dopo un urto, i substep successivi
usano il verso riflesso aggiornato; non continuano con il vettore iniziale.
L'ordine per assi è una scelta deterministica esplicita, da mantenere nei test.
Non si assume che i soli campioni finali descrivano ogni contatto geometrico.

### 3. Scansione del percorso e risposta al contatto

Per ciascun movimento su un asse:

1. Calcolare l'inviluppo fra AABB iniziale e candidata: enumerare **tutte** le
   celle di griglia intersecate dal corpo lungo quel segmento, in ordine stabile.
2. Trovare il primo contatto lungo il verso di movimento con celle solide,
   confine, scia attiva e giocatore vulnerabile. Usare la distanza di contatto
   sull'asse, non la sola appartenenza della posizione finale a una cella.
3. In assenza di urti, accettare lo spostamento. Contro un muro, portare il corpo
   alla tangenza esatta con la faccia della cella e riflettere **solo quell'asse**.
4. Consumare il tratto residuo del substep nel nuovo verso, verificandolo a sua
   volta. Non scartare sistematicamente il residuo, che ridurrebbe la velocità
   vicino ai muri. Gli impatti simultanei sui due assi riflettono entrambi.
5. A parità esatta di tempo di contatto, un muro protegge prima di una minaccia
   oltre la parete; gli altri pareggi seguono un ordine documentato e stabile.
6. Contatto con scia/player vulnerabile: evento di morte e arresto del tick;
   nessun secondo decremento vite nello stesso aggiornamento.

Il limite di 1 px aiuta a mantenere semplici gli urti; è la scansione dell'intero
segmento, insieme alla risoluzione per asse, a rendere esplicita la copertura di
tutte le celle. Un eventuale limite diagnostico al numero di contatti deve
segnalare lo stato anomalo, mai saltare controlli o accettare una posizione solida.

### 4. Separazione del solver e integrazione in Game

Introdurre un piccolo modulo di collisioni indipendente da Pygame, audio e AI.
Input: griglia, AABB, spostamento del tick e geometria delle minacce. Output:
posizione risolta, parità delle riflessioni su ciascun asse ed eventuale evento
di contatto. Il solver non legge tastiera, orologio o generatore casuale e non
modifica griglia, vite o canvas.

`Game` applica la variazione casuale del boss **una volta per tick**, chiama il
solver e aggiorna velocità/posizione. Spari, musica e timer non vanno moltiplicati
per N. Gli attuali controlli boss/scia/player solo a fine frame vanno sostituiti
con gli eventi del solver, mantenendo un solo punto che applica la morte.

In questa prima consegna lo spostamento resta espresso nell'unità attuale
pixel/tick: non si introduce un `dt` ricavato dal rendering. Nella successiva
migrazione al tempo fisso, il chiamante passerà `velocità_px_s × fixed_dt` allo
stesso solver. Questo evita di cambiare contemporaneamente collisioni e ritmo
di gioco. Il determinismo garantito riguarda gli stessi input nello stesso
ambiente; AI riproducibile e loop a tempo fisso sono passaggi successivi.

### 5. Cattura e invarianti da collegare

Prima di trasformare la scia in `FILLED`, verificare anche il tratto appena
aggiunto dal giocatore contro il corpo del boss: il giocatore viene aggiornato
dopo il boss e può creare una sovrapposizione nello stesso tick. Un contatto è
una morte, non una cattura seguita da espulsione del boss dal muro.

Validare il seme BFS e l'assenza di sovrapposizione del corpo con la frontiera
prima della mutazione. L'intera transazione deve preservare un boss in area
libera: non basta controllare il centro dopo il riempimento. Nessun rollback
parziale della canvas. Questo punto appartiene alla chiusura della Fase 1 insieme
al solver, perché la nuova hitbox non deve poter nascere dentro una parete.

### 6. Sequenza realizzativa e matrice di accettazione

| Passo | Consegna verificabile |
| --- | --- |
| 1A | Geometria AABB/griglia pura e regressione del muro x=200–201 px |
| 1B | Substep, scansione per asse, primo contatto e consumo del residuo |
| 1C | Integrazione boss, eventi di morte e validazione della cattura |
| 1D | Test di invarianza e sessione manuale; documentazione dei risultati |

Test da implementare prima di dichiarare risolto il difetto:

- Muro verticale/orizzontale di una cella, in entrambi i versi, a velocità
  ordinarie e superiori al limite previsto nei livelli.
- Nessun muro: spostamento richiesto preservato, inclusi componenti frazionari,
  asse fermo e velocità zero. Nessun movimento introdotto dal solver.
- Tangenza, angolo interno/esterno, due pareti vicine, più rimbalzi e corridoio
  appena sufficiente al corpo: niente compenetrazione e riflessioni corrette.
- Attraversamento di scia/player fra posizione iniziale e finale; protezione
  delle zone sicure; un solo evento di morte.
- Nuova linea che chiude vicino al boss e cattura concava: seme e corpo validi
  prima/dopo, nessuna conquista sopra il boss.
- Ingressi invalidi e non finiti rifiutati prima di mutare lo stato.
- Stessa griglia, posizione e spostamento: stesso risultato; raddoppiare la
  densità dei substep non cambia l'esito geometrico nei casi di riferimento.
- Suite completa: nessuna regressione nei 22 test attuali. Il difetto dei
  missili resta dichiarato aperto fino alla loro estensione dedicata.

I test del solver useranno piccole griglie in memoria, senza SDL o ritardi
reali. I test di integrazione fisseranno esplicitamente tempo e comportamento
casuale; nessuna dipendenza dalla durata della suite o dall'ordine dei test.

## Regole di lavoro e continuità

Operazioni Git esclusivamente all'utente, inclusi controlli di stato e diff.
Aggiornare questo report a ogni task con codice effettivamente completato,
risultati dei test, limiti aperti e prossimo passo. La roadmap generale è
approvata; la Fase 1 non è completata con il solo aggiornamento dello sprite.
