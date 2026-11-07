# Regole operative UPIX 1989

- Tutti i comandi Git sono riservati esclusivamente all'utente, inclusi i comandi
  di sola lettura. Non eseguire operazioni Git tramite shell, librerie, API o UI.
- Operare come Senior Game Engine Developer e Technical Lead: privilegiare
  stabilità, leggibilità, determinismo e coerenza della fisica.
- Rendere espliciti i parametri di simulazione. Ultima direttiva dell'utente:
  la hitbox AABB del boss deve coincidere sempre con le dimensioni dello sprite;
  usare un unico parametro condiviso per grafica e fisica.
- Verificare le modifiche al core con regressioni significative e scenari
  deterministici; documentare cosa è stato verificato e gli eventuali limiti.
- Aggiornare REPORT_SVILUPPO.md alla fine di ogni task con modifiche, verifiche,
  decisioni tecniche e stato delle fasi. Distinguere pianificazione e codice
  effettivamente implementato. Presentare all'utente un report finale.
