# UPIX 1989 - Documentazione Tecnica e Manuale Utente

## Introduzione
**UPIX 1989** è un tributo moderno ai classici arcade *Qix* e *Volfied*, sviluppato in Python con `pygame`. Il progetto combina meccaniche retrò con un'architettura software solida, offrendo un'esperienza di gioco fluida e reattiva.

---

## 🎮 Guida Rapida

### Prerequisiti
*   **Python 3.x** installato sul sistema.
*   Libreria **Pygame**.

### Installazione
1.  Clona o scarica la cartella del progetto.
2.  Apri il terminale nella cartella del progetto.
3.  Installa le dipendenze:
    ```bash
    pip install pygame
    ```

### Avvio del Gioco
Esegui il file principale:
```bash
python Upqix89.py
```

---

## 🕹️ Comandi di Gioco

| Tasto | Azione |
| :--- | :--- |
| **Frecce Direzionali** | Muovi il cursore (Disegna linee) |
| **Q** | Esci dal gioco |
| **R** | Riavvia il gioco (nella schermata Game Over) |
| **SPAZIO** | Passa al livello successivo (nella schermata Vittoria) |

---

## ⚙️ Meccaniche di Gioco

*   **Obiettivo**: Rivela almeno l'**80%** dell'immagine di sfondo disegnando rettangoli chiusi.
*   **Disegno**: Quando ti muovi fuori dalla zona sicura (l'area già svelata), tracci una linea. Chiudendo la linea su un'altra zona sicura, catturi l'area.
*   **Nemici**:
    *   **Boss**: Rimbalza nell'area non svelata. Se tocca la tua scia mentre stai disegnando, perdi una vita.
    *   **Missili**: Il boss spara missili verso di te. I missili si infrangono contro le aree già svelate (scudo).
*   **Vite**: Hai 3 vite a disposizione.

---

## 📂 Struttura del Progetto

Il gioco richiede una struttura di cartelle specifica per gli asset multimediali. Assicurati che la cartella `public` sia organizzata come segue:

```text
root/
├── Upqix89.py            # Codice sorgente principale
├── public/
│   ├── assets/         # Immagini dei livelli (01.png, 02.png...)
│   ├── icon/           # Icone UI (cursor_lukso.png, boss.png)
│   ├── music/          # Tracce audio (01pink.mp3, ...)
│   └── sounds/         # Effetti sonori (saldatrice.mp3)
```

> **Nota**: Il sistema include un meccanismo di **fallback**. Se mancano le immagini dei livelli, il gioco genererà automaticamente sfondi procedurali per evitare crash.

---

## 📘 Manuale di Sviluppo: Il Segreto del "Qix Perfetto"

Questa sezione è dedicata agli sviluppatori che vogliono capire **come** abbiamo risolto la sfida più grande nella programmazione di un clone di Qix: il riempimento delle aree.

### La Sfida Tecnica
In *Qix*, il giocatore può disegnare forme arbitrariamente complesse (spirali, forme a U, zig-zag). L'approccio ingenuo che molti tentano è:
1.  Registrare i punti del tracciato del giocatore.
2.  Cercare di calcolare geometricamente il poligono chiuso.
3.  Riempire quel poligono.

**Perché fallisce**: Questo approccio è un incubo matematico. Gestire auto-intersezioni, forme concave e capire "da che parte sta il dentro" porta quasi sempre a bug dove il gioco riempie l'area sbagliata o il nemico rimane bloccato nel muro.

### La Nostra Soluzione: "Inverse Flood Fill"
Invece di chiederci "Cosa ha disegnato il giocatore?", ci chiediamo: **"Dove può andare il nemico?"**.

Ecco l'algoritmo esatto che usiamo (visibile nella funzione `fill_area`):

1.  **Il Muro**: Quando il giocatore chiude un tracciato, quella linea diventa immediatamente un "Muro" (`FILLED`) nella griglia logica.
2.  **Il Secchiello (Flood Fill)**: Immagina di versare un secchio di vernice virtuale partendo dalla posizione esatta del Boss.
3.  **L'Espansione**: La "vernice" si espande in tutte le direzioni, fermandosi solo quando incontra un Muro o il bordo dello schermo.
4.  **L'Inversione (Il Trucco)**:
    *   Tutte le celle toccate dalla vernice sono "Zona Libera" (dove il Boss può muoversi).
    *   Tutte le celle che sono rimaste asciutte (e non erano già muri) significano una sola cosa: **sono state isolate dal giocatore**.
5.  **Cattura**: Il gioco converte automaticamente tutte le celle "asciutte" in aree conquistate (`FILLED`) e svela l'immagine sottostante.

### Perché è Infallibile
Questo metodo (basato sulla Teoria dei Grafi e non sulla Geometria) garantisce matematicamente due cose:
*   **Correttezza Topologica**: Non importa quanto sia strana la forma che disegni, se il Boss non può entrarci, è tua.
*   **Anti-Softlock**: È impossibile murare il Boss per errore. Se il Boss è dentro un'area, quella non verrà mai riempita perché il Flood Fill parte proprio da lui.

---

## 🧠 Analisi Tecnica (Note per Sviluppatori)

### Architettura del Sistema

#### Griglia Logica e Rendering
Il cuore del gioco si basa su una separazione netta tra la logica di gioco e la rappresentazione a schermo.
- **Risoluzione Logica**: Il campo di gioco è suddiviso in una griglia discreta definita da `CELL_SIZE` (impostato a 2px). Questo riduce la complessità computazionale rispetto a una gestione pixel-perfect pura, mantenendo però una fluidità visiva elevata ("Alta Risoluzione" percepita).
- **Stati della Cella**: Ogni cella della griglia può assumere due stati fondamentali: `EMPTY` (0) o `FILLED` (1).

### Soluzioni Algoritmiche

#### 1. L'Algoritmo di Cattura Aree (Flood Fill Inverso)
La sfida più complessa in un clone di Qix è determinare **quale** area riempire.
**Soluzione**:
1.  Quando il giocatore chiude un tracciato, eseguiamo un **Flood Fill (BFS)** partendo dal nemico.
2.  Tutte le celle raggiunte dal nemico rimangono `EMPTY`.
3.  Tutte le celle `EMPTY` che il nemico **non** può raggiungere sono, per esclusione, l'area catturata dal giocatore.
4.  Queste celle vengono convertite in `FILLED` e l'immagine viene svelata.

#### 2. Blitting Selettivo ("Reveal The Image")
Per ottimizzare il rendering a 60 FPS:
-   All'avvio, viene creata una `canvas` nera.
-   Il metodo `_reveal_pixel` copia i pixel dall'immagine nascosta alla `canvas` solo quando un'area viene conquistata.
-   Nel loop di gioco, viene disegnata solo la `canvas` finale, evitando calcoli di maschera costosi ad ogni frame.

### Valutazione Professionale e Miglioramenti Futuri
Il codice attuale (`test2.py`) è un ottimo esempio di prototipazione rapida che è evoluta in un prodotto stabile.

**Punti di Forza:**
*   **Robustezza**: Gestione delle eccezioni sui file mancanti (Fallback System).
*   **Performance**: Uso intelligente delle Surface di Pygame e algoritmi di riempimento ottimizzati.
*   **Leggibilità**: Codice ben commentato e strutturato in una classe `Game` coesa.

**Suggerimenti per il Refactoring (Next Steps):**
1.  **Separazione delle Responsabilità**: Spostare la logica del `Player`, `Enemy` e `Grid` in classi separate per migliorare la manutenibilità.
2.  **Configurazione Esterna**: Spostare le costanti (`WIDTH`, `COLORS`, `SPEED`) in un file `config.json` o `settings.py`.
3.  **State Pattern**: Implementare una macchina a stati per gestire meglio le transizioni (Menu -> Gioco -> Win/GameOver), attualmente gestite con flag booleani.
