# UPIX 1989 — Stato tecnico e piano di sviluppo

Aggiornamento: **7 novembre 2026**. Ruolo operativo: Senior Game Engine Developer
e Technical Lead. Obiettivo: consolidamento verso Release Candidate.

## Regole vincolanti e stato attuale

- **Tutte le operazioni Git, anche di sola lettura, sono riservate all'utente.**
  Nessun comando Git eseguito in questo task. Regola conservata in `AGENTS.md`.
- Il piano generale è approvato. **Collisioni Fase 1 estese ai missili**;
  avviata la Fase 2 con stati, pausa e orologio logico. Il collaudo esteso da
  Release Candidate e gli altri interventi della roadmap restano aperti.
- Campo operativo **800 × 600 px**, celle di 2 px, griglia **400 × 300**.
- Boss `boss2.png`: **96 × 70 px**, aumento del 20% con arrotondamento ai pixel.
  **Hitbox AABB 96 × 70 px uguale allo sprite**, secondo l'ultima correzione
  esplicita dell'utente, che sostituisce la precedente richiesta di mantenere
  30 × 30. Unico parametro condiviso: `BOSS_SIZE`; regola aggiornata in `AGENTS.md`.
- **Copertura SVG visibile all'avvio**, **immagine primaria PNG/JPG svelata
  dalla conquista**: ruoli separati per tutte le dodici coppie di asset.
- Musica normale **0,26**, musica durante il disegno **0,155**, effetto saldatrice
  **0,80**. L'ultima richiesta dimezza la riduzione precedente, da 0,21 a 0,105:
  la musica è quindi più udibile durante il disegno. Costante dedicata
  `DRAW_MUSIC_ATTENUATION = 0.105`; il volume attenuato è calcolato da quello normale.
- **91 test superati**, controllo del loop con P/ripresa/perdita focus e verifica
  visiva. La diagnostica storica di 3.000 movimenti riguardava il vecchio corpo:
  non viene presentata come collaudo esteso del nuovo boss.
- Ambiente verificato: Windows, Python **3.13.5**, Pygame **2.6.1**,
  `resvg_py` **0.5.0**. Dipendenze dichiarate in `requirements.txt`.

## Consegna corrente — Missili continui, stati e pausa

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

`SimulationClock` usa una sorgente monotona iniettabile. Conta soltanto i
millisecondi attivi; alla ripresa riallinea il riferimento reale senza sommare
la durata della pausa. Spari, cambio direzione del boss e HUD usano lo stesso
tempo logico. Una pausa lunga non causa spari anticipati o arretrati dell'AI.
Un nuovo livello azzera il timer dopo il caricamento degli asset; vittoria,
Game Over ed errore fisico lo fermano. La pausa è idempotente e non si attiva
sopra uno stato terminale.

Questo intervento **non è ancora la simulazione a passo fisso**: gli spostamenti
rimangono per tick. Corregge il tempo durante le pause, senza cambiare
contemporaneamente le velocità del gioco.

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

AI, spari e timer rimangono eseguiti una volta per aggiornamento, non per
substep, usando ora il tempo logico che esclude le pause. Il movimento è ancora espresso in pixel/tick: la migrazione al tempo
fisso non è inclusa in questa consegna e il gioco completo non è ancora
indipendente dal frame rate. Il determinismo del solver riguarda gli stessi
input nello stesso ambiente; non equivale a replay deterministico dell'AI.

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

L'integrazione dei dodici SVG è **completata**. Prossimi interventi: manifest dei
livelli con immagine/musica/boss/regole; eventuali SVG quadrati se si sceglierà
un campo 1:1; esportazione e controllo del pacchetto su PC pulito. I dodici SVG
sono stati modificati soltanto per eliminare le label centrali; le immagini
primarie non sono state modificate. Restano le copie JPG rinominate
PNG create dallo script storico, da razionalizzare in una fase dedicata.

## Analisi aggiornata — Possibilità di 1024 × 768 px

**Sì, 1024 × 768 è fattibile** e conserva il rapporto 4:3 di campo e SVG.
Il codice operativo rimane a 800 × 600: la richiesta è stata trattata come
valutazione tecnica, senza attivare una migrazione della griglia non necessaria
alla consegna su missili e pausa.

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

Benchmark corrente, con boss e hitbox **96 × 70**, eseguito isolatamente dalla
suite: cinque tagli verticali centrali e 100 chiamate al solver del boss.

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

**Raccomandazione:** come prima evoluzione, finestra/viewport 1024 × 768 con
campo logico 800 × 600 e scala uniforme 1,28. La stessa trasformazione deve
proiettare grafica, coordinate e hitbox: il boss logico 96 × 70 apparirebbe circa
123 × 90, con lo stesso ingombro fisico sullo schermo. La BFS resterebbe a
120.000 celle. Questa separazione del viewport è una proposta, non codice già
attivato in questo task.

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
4. Separare risoluzione logica e viewport; definire un profilo quadrato con asset,
   scala grafica e bilanciamento espliciti. Una presentazione più grande con
   letterbox può essere valutata separatamente dal numero di celle simulate.
5. Ripetere benchmark su casi piccoli/grandi, forme concave, scie lunghe e PC
   target; attivare il nuovo profilo soltanto con risultati accettabili.

## Verifiche e limiti residui

Suite: **91 test superati** con:

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

Diagnostica storica sul precedente corpo del boss: **3.000 movimenti**, seme 1989 e componenti casuali
comprese fra −25 e +25 px/tick, mantenendo sempre il corpo libero. Una sequenza
più breve è conservata come regressione automatica. Controllo visivo di sfondo
intero, cattura parziale e inserimento 4:3 nel viewport quadrato.

I driver dummy non verificano ascolto reale, latenza degli altoparlanti,
presentazione sul monitor o difficoltà dei dodici livelli. Non sono stati
certificati tutti i casi patologici di geometria: 1D resta aperto.

Problemi ancora da affrontare:

- **Tempo fisso:** movimento per frame e timer in millisecondi restano misti;
  i timer ora escludono correttamente le pause, ma lo spostamento non è ancora
  indipendente dal frame rate. Velocità iniziale del boss non ancora uniformata
  dopo il cambio casuale.
- **Cattura:** sincrona e costosa; percentuale iniziale e score da chiarire.
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

Il gioco resta un prototipo giocabile con 12 livelli, 3 vite, un boss con
missili, obiettivo all'80%, movimento ortogonale continuo e morte per
autointersezione. Dopo il dodicesimo livello torna al primo; il punteggio si
azzera per livello e non è mostrato. Restano da progettare menu, impostazioni,
classifica locale, finale e boss realmente differenziati.

| Fase | Stato / consegna successiva |
| --- | --- |
| 1A | Completata: AABB/griglia e regressione del muro |
| 1B | Completata: substep, primo contatto e residuo |
| 1C | Completata: boss runtime e validazione della conquista |
| Collisioni missili | Completate: primo impatto continuo e assorbimento |
| 1D / collaudo RC | Regressioni automatiche estese; sessioni reali prolungate e bilanciamento ancora da completare |
| Fase 2 — stati/pausa | Implementati: P, focus, timer attivo e sospensione/ripresa audio |
| Consolidamento restante | Tempo fisso e percentuali coerenti |
| Fluidità e controllo | Cattura ottimizzata, HUD score e impostazioni dei volumi |
| Vertical slice | Tre livelli: tutorial cattura, spari anticipati, boss differenziato |
| Varietà | Una pressione anti-attesa e uno/due potenziamenti valutati separatamente |
| Campagna | Manifest 12 livelli, score cumulativo, bonus e finale |
| Release | Menu, salvataggi/classifica, pacchetto Windows e crediti verificati |

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
descrive anche miccia contro le esitazioni, ricompensa della modalità lenta e
separazione dei due Qix. Sono meccaniche da valutare singolarmente dopo il core.

Direzione approvata: identità vicina a Volfied, con immagine rivelata, boss LUKSO,
80% e decisioni geometriche. Insegnare prima rischio della scia e rientro,
anticipare visivamente gli spari, premiare il confinamento. Aggiungere una sola
pressione contro l'attesa, poi pochi potenziamenti leggibili e l'eventuale doppia
velocità. Due boss richiederanno BFS da entrambi oppure una condizione esplicita
di vittoria per separazione: non riutilizzare la BFS da un solo seme.

La strategia attuale resta preparare chiusure corte e sicure, poi confinare il
boss nella regione piccola per conquistare quella maggiore. Ogni tratto della
scia è vulnerabile. Il bordo rimane silenzioso: la saldatrice segnala soltanto
il tracciamento nel campo libero.
