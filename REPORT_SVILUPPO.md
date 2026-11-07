# UPIX 1989 — Stato tecnico e piano di sviluppo

Aggiornamento: **7 novembre 2026**. Ruolo operativo: Senior Game Engine Developer
e Technical Lead. Obiettivo: consolidamento verso Release Candidate.

## Regole vincolanti e stato attuale

- **Tutte le operazioni Git, anche di sola lettura, sono riservate all'utente.**
  Nessun comando Git eseguito in questo task. Regola conservata in `AGENTS.md`.
- Il piano generale è approvato. **Passi 1A, 1B e 1C implementati**; il collaudo
  esteso 1D e gli altri interventi della roadmap restano aperti.
- Campo operativo **800 × 600 px**, celle di 2 px, griglia **400 × 300**.
- Boss `boss2.png`: **80 × 58 px**, alpha e proporzioni preservati, centro sulla
  posizione logica. Corpo fisico **AABB 30 × 30 px**, indipendente dalla grafica.
- I dodici sfondi **01.svg–12.svg** sono caricati e svelati progressivamente.
- Musica normale **0,26**, musica durante il disegno **0,155**, effetto saldatrice
  **0,80**. L'ultima richiesta dimezza la riduzione precedente, da 0,21 a 0,105:
  la musica è quindi più udibile durante il disegno. Costante dedicata
  `DRAW_MUSIC_ATTENUATION = 0.105`; il volume attenuato è calcolato da quello normale.
- **70 test superati**, più diagnostica deterministica di 3.000 movimenti del
  solver senza penetrazioni e controllo visivo degli SVG renderizzati/rivelati.
- Ambiente verificato: Windows, Python **3.13.5**, Pygame **2.6.1**,
  `resvg_py` **0.5.0**. Dipendenze dichiarate in `requirements.txt`.

## Consegna corrente: Fase 1B e 1C

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
o vincoli alle velocità. La stessa AABB 30 × 30 serve per muri, scia e player;
il rendering conserva il suo arrotondamento separato. La scia viene interrogata
localmente tramite un insieme di celle, escludendo quelle già sicure.

AI, spari e timer rimangono eseguiti una volta per aggiornamento, non per
substep. Il movimento è ancora espresso in pixel/tick: la migrazione al tempo
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
rettangoli con dimensioni percentuali, gradienti e testo. Non sarebbe sufficiente
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

1. Cerca `public/assets/{level:02d}.svg` al cambio livello.
2. Rasterizza alla dimensione richiesta. Usa il font incluso in Pygame come
   sostituzione esplicita per il testo, senza scansione dei font di sistema.
3. Conserva proporzioni, alpha compositato su nero e centratura. Se il viewport
   ha un diverso rapporto di aspetto, applica bande nere.
4. Memorizza il PNG in una cache limitata a quattro elementi, con chiave che
   include percorso, timestamp e risoluzione. Modificare un SVG invalida la cache.
5. In caso di errore usa PNG/JPG dello stesso livello, poi lo sfondo procedurale.
   La sorgente effettiva è esposta da `Game.background_source` e stampata nel log.

La rasterizzazione non avviene durante il movimento o durante la BFS. Il frame
loop riutilizza la canvas: il bordo è inizialmente visibile, il resto rimane
coperto finché non viene conquistato. Alla vittoria appare tutto lo sfondo.
Sono stati verificati tutti i livelli **01–12**, il testo “Level 1”, i gradienti
e la corrispondenza pixel fra porzione rivelata e immagine rasterizzata.

`start.bat`, locale ed escluso secondo la preferenza dell'utente, ora preferisce
l'interprete `.venv`. Avviando direttamente il gioco con un altro interprete,
installarvi prima le dipendenze di `requirements.txt`; in assenza del renderer
viene esplicitamente usato il fallback raster.

### Workflow degli asset dopo questo task

L'integrazione dei dodici SVG è **completata**. Prossimi interventi: manifest dei
livelli con immagine/musica/boss/regole; eventuali SVG quadrati se si sceglierà
un campo 1:1; esportazione e controllo del pacchetto su PC pulito. Non è stata
modificata o eliminata alcuna risorsa originale. Restano le copie JPG rinominate
PNG create dallo script storico, da razionalizzare in una fase dedicata.

## Analisi tecnica: campo 1024 × 1024 px

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

Ultima sessione eseguita separatamente dalla suite, su questo PC con SDL dummy:

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
movimento, non tutta la griglia. A corpo 30 × 30, cella 2 e velocità invariati,
il numero nominale di celle candidate/substep rimane simile anche su un campo
più grande. Non ci si aspetta un fattore 2,1845 obbligatorio nel suo costo.
Le misure locali sono sensibili al carico e alle allocazioni; vanno ripetute su
hardware target. In `Game` si aggiunge la costruzione dell'insieme della scia,
che dipende dalla lunghezza del tracciato. Ingrandire anche corpo o velocità
aumenterebbe rispettivamente candidati o numero di substep.

Il boss 80 × 58 occupa oggi il 10% della larghezza e circa il 9,67% dell'altezza.
Su 1024 × 1024 scenderebbe a circa 7,81% e 5,66%: apparirebbe relativamente
più piccolo. Un fattore uniforme 1,28 darebbe circa **102 × 74 px**, mantenendo
la quota di larghezza ma non quella di altezza. Il passaggio da 4:3 a 1:1 non
consente di mantenere entrambe senza cambiare composizione; deformare lo sprite
non è la soluzione. La hitbox non deve cambiare automaticamente con il rendering.

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

1. Completare il collaudo 1D e le collisioni dei missili, ancora discrete.
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

Suite: **70 test superati** con:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Copertura: muro 200–201 px nei due versi e nel runtime, alta velocità, muri
orizzontali, angoli, tangenze, residuo, rimbalzi multipli, asse vincolato,
scia/player lungo il percorso, protezione dei muri, input invalidi, ripetibilità,
densità dei substep nei casi di riferimento, catture concave e senza scritture
parziali, audio, respawn, vittoria/livelli, tutti gli SVG, gradienti/testo, cache,
fallback, viewport quadrato e rendering del boss.

Diagnostica separata: **3.000 movimenti**, seme 1989 e componenti casuali
comprese fra −25 e +25 px/tick, mantenendo sempre il corpo libero. Una sequenza
più breve è conservata come regressione automatica. Controllo visivo di sfondo
intero, cattura parziale e inserimento 4:3 nel viewport quadrato.

I driver dummy non verificano ascolto reale, latenza degli altoparlanti,
presentazione sul monitor o difficoltà dei dodici livelli. Non sono stati
certificati tutti i casi patologici di geometria: 1D resta aperto.

Problemi ancora da affrontare:

- **Missili:** collisione discreta, possibile tunnelling attraverso muri sottili.
- **Tempo fisso:** movimento per frame e timer in millisecondi restano misti;
  velocità iniziale del boss non ancora uniformata dopo il cambio casuale.
- **Cattura:** sincrona e costosa; percentuale iniziale e score da chiarire.
- **Pausa/focus:** la partita non si sospende perdendo il focus.
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
| 1D | Aperta: collaudo esteso, sessioni reali e casi limite |
| Consolidamento restante | Missili continui, tempo fisso, percentuali coerenti |
| Fluidità e controllo | Cattura ottimizzata, pausa/focus, HUD score e volumi |
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
