# Photo viewpoint 0.4.0 — aggiornamento

È lo stesso plugin, con lo stesso nome interno prese_fotografiche. I layer e i
progetti già creati restano utilizzabili. Il nome visibile del prodotto e il nome
predefinito del nuovo layer sono **Photo viewpoint**. La lingua segue QGIS:
italiano per it, inglese per le altre lingue. I nomi dei campi esistenti non cambiano.

## 1. Creazione su file o temporanea

Crea layer foto apre una finestra con nome, formato, CRS e cartella. Il nome
proposto è Photo viewpoint; inseriscilo senza estensione. Il CRS deve essere
proiettato con unità in metri e resta una tua scelta.

Puoi scegliere un layer temporaneo oppure GeoPackage (.gpkg), SHP (.shp), SQLite
(.sqlite) o FlatGeobuf (.fgb), se il relativo driver è disponibile nella tua
installazione. Il menu è limitato a questi formati, che possono conservare lo
schema vuoto dei campi: non elenca indistintamente tutte le esportazioni QGIS.
GeoPackage è la scelta raccomandata per nomi di campi, modifiche e testo.

La cartella iniziale coincide con quella del progetto QGIS salvato. Per un
progetto non salvato si usa la home del progetto se disponibile, altrimenti
Documenti. Con il formato temporaneo la scelta della cartella è disabilitata.
Non vengono sovrascritti file esistenti: scegli un altro nome se già presente.

Con un layer su file i dati hanno già una destinazione persistente: salva
normalmente le modifiche dopo gli inserimenti. Salva anche il progetto per
conservare lo stile. Il layer temporaneo va invece esportato prima di chiudere.
Non è più necessario esportare manualmente un nuovo layer creato su file.

## 2. Metadati delle immagini

Quando salvi una nuova presa con una foto, oppure usi Cambia immagine, il plugin
legge i metadati EXIF convenzionali dei JPEG e TIFF locali. Nessuna libreria Python
aggiuntiva è richiesta. Il file originale non è modificato e non è caricato online.

I dati del fotografo non sono sovrascritti: geometria del punto, azimuth, fov e
distance rimangono quelli definiti interattivamente. Le informazioni EXIF vanno
nei campi separati:

| Campo | Contenuto |
| --- | --- |
| gps_lat, gps_lon | Latitudine e longitudine originali EXIF in gradi decimali |
| gps_alt | Quota GPS in metri con segno, quando è presente il riferimento della quota |
| gps_dir | Direzione GPSImgDirection in gradi, quando presente |
| gps_dref | Riferimento T (nord vero) o M (magnetico) |
| gps_datum | Datum riportato nei metadati |
| gps_x, gps_y | Coordinate GPS trasformate nel CRS del layer |
| exif_date | Data/ora di scatto come testo originale, senza fuso orario dedotto |
| exif_cam | Marca e modello della fotocamera |
| exif_stat | Esito della lettura |

Per la trasformazione X/Y si assume WGS84 se manca il tag del datum. Se il file
riporta un datum diverso, non viene trasformato automaticamente: gps_x e gps_y
restano NULL e lo stato è datum_unknown. La quota non diventa una coordinata Z
nella geometria 2D. La direzione non è dedotta dai soggetti o dalla traiettoria.

Gli stati sono codici stabili: ok, no_gps, no_exif, unreadable, remote, empty,
datum_unknown. Un campo NULL significa che il valore non è disponibile, non zero.
Scegliendo un'altra immagine, i metadati mancanti nella nuova vengono svuotati
per non conservare valori della foto precedente.

Per le prese già presenti usa **Leggi metadati foto**: vengono elaborate le
feature selezionate, oppure tutte se non c'è una selezione. I campi mancanti
vengono aggiunti. Salva le modifiche del layer per renderle permanenti.

Limiti: niente HEIC, RAW, XMP-only, MakerNotes proprietarie o download di URL web.
Foto ritoccate/esportate possono aver perso GPS o EXIF; molti telefoni non salvano
la direzione. Sono supportati EXIF in APP1 JPEG e TIFF standard con offset nei
limiti dei dati letti. Le nuove integrazioni richiedono il collaudo nel tuo QGIS.

## 3. Preparazione internazionale e GitHub

Nel pacchetto trovi README.md in inglese, catalogo italiano/inglese, pagina
**docs/index.html** pronta per GitHub Pages, licenza GPL completa, test e guida
PUBLISHING.md. La cartella estratta può diventare la radice di un repository:
caricane i contenuti, senza un livello aggiuntivo di cartelle.

Repository, homepage, tracker ed email del manutentore sono intenzionalmente
vuoti finché non vengono definiti quelli reali. Non è stato creato un repository
GitHub né inviata una domanda di pubblicazione a QGIS. L'autore umano/manutentore
mantiene il progetto; ChatGPT/Codex è accreditato come assistenza allo sviluppo.

Prima della distribuzione pubblica occorrono account GitHub, email di contatto,
URL reali, collaudo desktop dei formati e delle funzioni, e revisione dei requisiti
QGIS aggiornati. Il programma tools/package.py può creare lo ZIP di release
inserendo i dati reali; non esegue pubblicazioni. Il pacchetto resta sperimentale.

## Prova suggerita

1. Crea un nuovo GeoPackage Photo viewpoint nella cartella del progetto.
2. Inserisci una presa con una foto JPEG di cui conosci GPS/EXIF; controlla i campi.
3. Chiudi l'editing salvando, riapri il dataset e controlla che i dati persistano.
4. Usa Cambia immagine con una foto priva di GPS: i vecchi valori devono svuotarsi.
5. Seleziona una vecchia presa e prova Leggi metadati foto.
6. Ripeti la creazione su SHP e controlla anche il salvataggio dei campi.

Per un test tecnico nella console Python QGIS:

```python
import prese_fotografiche.smoke_test_storage as t
t.run(iface)
```

I test Python senza QGIS coprono EXIF little/big-endian, coordinate emisferiche,
quota negativa, direzione, errori nei metadati, lingue e impaginazione numerica.
Le prove grafiche e la persistenza nei formati QGIS restano da completare sul Mac.
