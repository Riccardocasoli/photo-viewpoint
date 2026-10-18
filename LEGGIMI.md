# Photo viewpoint 0.6.0

È lo stesso plugin. L'interfaccia è ora in inglese; la documentazione completa è
in entrambe le lingue. Estrai una copia dello ZIP e apri MANUALE.html nel browser.

- docs/manual-it.html: presentazione e manuale italiano aggiornati.
- docs/manual-en.html: English presentation and user manual.
- README.md: panoramica tecnica e istruzioni per il repository.

Nuovi layer: code, caption, distGPS come primi campi del plugin, poi quelli di
servizio. caption ha lunghezza 2.000 nei formati adatti; SHP usa 254 per il limite
DBF e non può garantire 255+ caratteri Unicode. Per didascalie lunghe usa GeoPackage.

I vecchi codice/Didascalia continuano a funzionare con alias inglesi e ordine
visualizzato aggiornato. Non vengono riscritti automaticamente. Per ottenere
nomi fisici inglesi usa Apply viewpoint style → Create English-field GeoPackage
copy…; la copia lascia intatto l'originale.

La tavolozza apre quattro stili, dimensioni, etichette e salvataggio riutilizzabile.
SHP/FlatGeobuf: conserva insieme dati e QML. GeoPackage/SQLite: si tenta anche il
salvataggio predefinito nel database; leggi il messaggio e usa il QML se il provider
non lo consente. QML include la grafica SVG, senza collegamenti alla cartella plugin.

Installa come prima da ZIP e riavvia QGIS. Salva sempre le modifiche del layer e
il progetto. Le nuove funzioni di stile e copia richiedono il collaudo sul Mac.
Le guide GUIDA_0_*.md sono storiche: per la 0.6 fanno fede i due nuovi manuali.
