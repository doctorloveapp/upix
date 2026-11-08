# UPIX 1989 — Release Windows x64

Avviare **UPIX1989.exe**. Il pacchetto include Python, Pygame, renderer SVG,
musiche e asset: non serve installare Python o FFmpeg sul PC di destinazione.
La build è destinata a Windows 10/11 a 64 bit. macOS, Linux e Windows a 32 bit
richiedono pacchetti distinti; non è certificata ogni combinazione hardware/driver.

L'EXE funziona da solo. `game_manifest.json`, se presente accanto all'EXE, permette
di modificare i parametri senza ricompilare. In sua assenza viene usata la copia
inclusa nel programma. Per tornare ai valori inclusi, spostare la copia esterna.
Riavviare il gioco dopo una modifica. Gli asset rimangono quelli della build;
cambiare percorsi a file non inclusi può attivare i fallback.

I record personali vengono salvati in:

```text
%LOCALAPPDATA%\UPIX1989\highscores.json
```

Il log d'avvio si trova nella stessa cartella (`launcher.log`). Spostare l'EXE
non cancella i record. Le impostazioni debug restano solo in memoria.

Comandi: frecce o controller per muoversi, Spazio/X per lo scudo, P per la pausa,
Invio/A per confermare, Esc/B per tornare indietro. Dopo la morte attendere
l'esplosione e rilasciare la direzione prima di ripartire. Dopo il livello 12
si può continuare in New Game Plus oppure registrare il punteggio e terminare.

L'audio della release è già normalizzato rispetto a `02gold.mp3`. I file
originali sono conservati. Modificare i parametri di normalizzazione richiede
rigenerare la cache e la build dal progetto sorgente; il lettore usa gli originali
se una cache non corrisponde alla configurazione.

Per ricreare la release dal repository, su Windows x64 con FFmpeg nel PATH:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe tools\build_release.py
```

Il comando prepara solo i brani nuovi/cambiati e genera `dist/UPIX1989.exe`,
il manifest esterno e `build_info.json` con hash SHA-256 e versione Python.
La prima preparazione audio può richiedere alcuni minuti; non viene eseguita
durante la simulazione. Conservare il manifest insieme alla build da distribuire.
