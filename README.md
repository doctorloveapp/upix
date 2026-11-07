# UPIX 1989

Tributo arcade a **Qix (1981)** e **Volfied (1989)**, sviluppato in Python con Pygame. Si conquistano porzioni del campo per rivelare un'immagine, evitando il boss e i suoi missili durante il tracciamento.

Il progetto è un **prototipo giocabile** con 12 livelli. Per analisi del codice, problemi aperti, fonti storiche e piano di sviluppo consultare [REPORT_SVILUPPO.md](REPORT_SVILUPPO.md), aggiornato il 7 novembre 2026.

## Installazione e avvio

Ambiente verificato: Windows, Python **3.13.5**, Pygame **2.6.1**. Altri sistemi o versioni di Python richiedono una verifica dedicata.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe Upqix89.py
```

Se Python è disponibile tramite il launcher Windows, usare `py -3` al posto di `python` per creare l'ambiente. Con Pygame già installato nell'interprete predefinito basta `python Upqix89.py`.

Gli asset vengono cercati rispetto a `Upqix89.py`, indipendentemente dalla cartella di avvio. `start.bat`, se presente localmente, salva l'output in `errorlog.txt` e mostra eventuali errori.

## Comandi e regole attuali

| Tasto | Azione |
| --- | --- |
| Frecce | Impostano la direzione del cursore |
| Q | Esce |
| R | Ricomincia dopo il Game Over |
| Spazio | Passa al livello successivo dopo la vittoria |

- Il movimento continua anche rilasciando la freccia. Una nuova freccia cambia direzione; durante il disegno non è possibile invertire direttamente il senso.
- Il cursore parte sul bordo sicuro. Entrando nel campo non conquistato crea una scia vulnerabile.
- La linea deve tornare a un'area sicura. Sono possibili percorsi ortogonali complessi, non soltanto rettangoli.
- La zona separata dal boss viene conquistata; quella raggiungibile dal boss rimane aperta.
- Boss e missili che toccano la scia fanno perdere una vita. Anche un'autointersezione fa perdere una vita.
- Il territorio conquistato protegge dai missili, con il limite delle collisioni discrete descritto nel report.
- Si parte con 3 vite. Dopo una morte si riparte dall'ultimo punto sicuro.
- La vittoria richiede almeno l'80%. Attualmente la percentuale include il bordo iniziale, ma si aggiorna solo dopo una cattura.
- Dopo il livello 12 si torna al livello 1 mantenendo le vite. Il punteggio interno si azzera a ogni livello e non è ancora mostrato nell'HUD.

## Audio della saldatrice

L'effetto è attivo **soltanto mentre il cursore traccia nel campo non conquistato**. È spento sul bordo e nelle aree sicure, alla chiusura della linea, alla morte, al cambio livello e all'uscita.

- `public/sounds/saldatrice.mp3`: registrazione originale, mantenuta come fallback.
- `public/sounds/saldatrice.wav`: stessa registrazione preparata per il gioco, con i primi 0,30 s rimossi, guadagno di 6 dB, limitatore e brevi dissolvenze per attenuare i clic.
- Un canale riservato riproduce il loop senza riavviarlo a ogni frame.
- Durante il tracciamento la musica passa da `0.26` a `0.10`; alla fine torna a `0.26`. L'effetto usa volume `0.80`.
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
├── README.md
├── REPORT_SVILUPPO.md        # Revisione tecnica e roadmap
├── requirements.txt
├── .gitignore
├── tests/
│   └── test_game.py          # Regressioni con driver SDL dummy
└── public/
    ├── assets/              # Livelli 01.png … 12.png e sorgenti grafici
    ├── icon/                # cursor_lukso.png, boss2.png e altre icone
    ├── music/               # Quattro tracce MP3
    └── sounds/              # Effetto originale MP3 e WAV preparato
```

`copy_images.ps1` è uno script storico che **copia** i JPG con estensione `.png`: non converte il formato. Pygame li decodifica comunque, ma la pipeline va corretta prima della distribuzione. Nessun asset è stato eliminato.

Il boss usa esclusivamente `boss2.png`: alpha preservato, proporzioni mantenute
entro 40 × 40 px (40 × 29 per l'asset attuale) e centro agganciato alla posizione
logica. La hitbox è indipendente dall'immagine. Se l'asset manca o è corrotto,
viene disegnato un cerchio; il vecchio `boss.png` non viene caricato.

## Architettura e cattura delle aree

Il campo 800 × 600 px usa celle da 2 px: **400 × 300 = 120.000 celle**. `grid[x][y]` contiene `EMPTY` o `FILLED`; la scia in corso è conservata separatamente.

Alla chiusura della linea, `fill_area()`:

1. Converte la scia in celle conquistate.
2. Esegue una BFS dalla cella del centro del boss, attraversando le celle libere.
3. Conquista le celle libere non raggiunte dalla BFS.
4. Copia sulla `canvas` le porzioni dell'immagine e aggiorna percentuale e punteggio.

Il flood fill inverso è adatto alle forme concave, purché il boss sia in una cella libera valida e le collisioni mantengano questo vincolo. **Non garantisce da solo che il boss non attraversi muri**. Con più boss occorrerà definire le regole e, se devono restare tutti in gioco, conservare l'unione delle regioni raggiungibili da tutti i boss attivi.

Il rendering riutilizza la `canvas`, evitando di ricostruire la maschera ogni frame. La cattura resta sincrona e può superare il budget di un frame: vedere le misure nel report.

## Verifiche

```powershell
python -m unittest discover -s tests -v
```

I 22 test verificano audio e transizioni, respawn, autointersezione, collisioni ordinarie, cattura e vittoria, progressione, caricamento dei 12 sfondi, alpha/proporzioni/centratura del boss, avvio da un'altra cartella, fallback multimediali e import senza finestre.

Usano driver SDL `dummy`: controllano mixer e segnale del WAV, **non l'ascolto dagli altoparlanti**. Non certificano l'assenza dei problemi aperti né sostituiscono una partita completa con audio reale.

## Repository

Il `.gitignore` esclude cache Python, ambienti virtuali, build, log, file degli editor, configurazioni private e salvataggi. Gli asset runtime e i test devono essere versionati. Le esclusioni locali di `Documenti` e `start.bat` aggiunte durante la revisione sono state rispettate.

**Tutti i comandi e le operazioni Git sono riservati all'utente**, inclusi i
controlli di sola lettura. Questa regola è conservata anche in `AGENTS.md`.
L'assistente modifica codice e documentazione ed esegue le verifiche applicative.
