# Photo viewpoint 0.5.0 — importazione da immagini

È un aggiornamento dello stesso plugin e dei layer già compatibili. Il nuovo
metodo affianca l'inserimento in tre clic, senza sostituirlo.

## Due metodi di creazione

- **Crea il punto e associa la foto**: icona viewpoint → immagine. È la procedura
  precedente: tre clic, poi codice e riferimento alla fotografia.
- **Crea viewpoints da immagini**: icona immagine → viewpoint. Selezioni più file
  e il plugin prepara un record per ciascuna foto scelta.

Prima scegli come attivo il layer Photo viewpoint (o un layer creato dal plugin
con altro nome). Se non ne hai uno, usa Crea layer foto. Il nome non è vincolante:
il plugin usa campi e CRS, non una corrispondenza letterale del nome del layer.

## Importazione multipla

1. Premi Crea viewpoints da immagini e seleziona uno o più file.
2. Nel dialogo controlla nome file, disponibilità del GPS e azimut proposto.
3. I valori predefiniti iniziali sono azimut 0°, FOV 40°, lunghezza grafica 20 m.
   Puoi cambiarli prima dell'importazione.
4. Le righe in rosso non hanno una posizione GPS utilizzabile. Possono restare
   spuntate per essere posizionate dopo, oppure puoi escluderle togliendo la spunta.
   Il pulsante Escludi tutte le immagini senza GPS fa questa selezione in un colpo.
5. Conferma: ogni riga spuntata crea un record con photo, metadati e parametri.
6. Salva le modifiche del layer per conservare l'importazione.

Se i punti con GPS sono fuori dall’inquadratura corrente, usa Zoom al layer
dal menu contestuale del layer. I record senza geometria non hanno estensione.

Il codice è proposto dal nome del file senza estensione. Nomi già presenti
ricevono suffissi _2, _3…; puoi cambiarli successivamente in tabella. Reimportare
lo stesso file in una nuova operazione crea un nuovo record, non sovrascrive il
precedente. Annullare il dialogo non crea record; il lotto importato è annullabile
come singola operazione nel buffer di modifica.

## Coordinate e direzione

Con GPS utilizzabile la geometria iniziale deriva dalle coordinate gps_x/gps_y,
trasformate dal GPS nel CRS metrico del layer. Non viene inventata una posizione
se GPS è assente, corrotto o il datum non è riconosciuto. Se GPSMapDatum è assente
vale l'assunzione WGS84 già descritta nella guida EXIF.

Una GPSImgDirection riferita al nord vero (T) viene convertita in azimut della
griglia del CRS usando la proiezione di un breve segmento geodetico. Un valore
riferito al nord magnetico (M), o privo di riferimento, rimane nei metadati ma
non viene usato automaticamente: manca la declinazione magnetica. In quel caso
l'azimut del viewpoint usa il default mostrato nel dialogo.

FOV e lunghezza grafica usano sempre i default del dialogo: questa versione non
ricava un'apertura ottica da sensore/focale, né scambia la distanza del soggetto
con la lunghezza grafica del cono. Dopo l'importazione si correggono con le
normali maniglie di Modifica presa. I punti con GPS possono anche essere spostati.

## Foto senza GPS: nessuna coordinata fittizia

Le foto spuntate senza posizione creano record con geometria NULL. Restano nella
tabella con i loro dati, ma non vengono disegnate sulla mappa: non sono collocate
all'origine 0,0, al centro dello schermo o vicino ad altre prese.

Dopo l'importazione si apre **Foto da posizionare**, un pannello laterale. Lo
stesso pannello si può riaprire con il pulsante dedicato (fotografia con avviso),
anche dopo aver salvato e riaperto il progetto:

1. Seleziona una foto nell'elenco.
2. Premi Posiziona sulla mappa.
3. Clicca il punto di presa. Si crea la geometria e compare il simbolo con i default.
4. Usa Modifica presa per orientamento, apertura e lunghezza.

Esc annulla solo lo strumento di posizionamento: il record rimane in attesa.
Il pannello permette anche di eliminare il record selezionato, con conferma;
non elimina mai il file immagine. Aggiorna elenco rilegge le geometrie, utile dopo
Annulla/Ripristina o modifiche esterne al pannello. Le foto già collocate spariscono
dall'elenco. Record senza geometria sono supportati dal provider (es. GeoPackage
oppure shape NULL nello SHP); il funzionamento va verificato nei formati scelti.

Il campo **vp_status** distingue needs_pos e positioned. È uno stato della
geometria, non una valutazione della qualità del GPS. Un punto corretto a mano
può essere positioned anche con metadati GPS assenti.

## distGPS: distanza dal GPS originario

**distGPS** è un campo numerico reale con un'espressione QGIS di valore predefinito
configurata per ricalcolarsi agli aggiornamenti. Non è una distanza 3D: è la
distanza planimetrica, nelle unità metriche del CRS, fra gps_x/gps_y e la geometria.

- Al punto iniziale ricavato da GPS vale 0.
- Dopo uno spostamento di 3 m in X e 4 m in Y vale 5 m.
- Se GPS o geometria mancano vale NULL, non 0.
- Gli strumenti del plugin e le modifiche geometriche native QGIS aggiornano il
  valore attraverso il default con applicazione agli aggiornamenti.
- Il movimento della geometria non cambia gps_lat, gps_lon, gps_alt, gps_x o gps_y.

Salva sia le modifiche del layer sia il progetto: la colonna è nel dataset,
l'espressione di aggiornamento appartiene alla configurazione QGIS del layer.
Il plugin ripristina la configurazione sui layer compatibili quando si avvia o
si riapre il progetto. Una modifica fatta da un altro programma al solo SHP non
esegue l'espressione QGIS: il campo non è un trigger interno al file SHP.
Se assegni un altro CRS al layer, rileggi i metadati prima di confrontare X/Y.

## Prova pratica raccomandata

Importa un JPG georeferenziato e uno senza GPS. Controlla due righe in tabella,
una geometria visibile e un elemento nel pannello. Posiziona la seconda foto e
modifica le maniglie. Sposta la prima e verifica distGPS e coordinate GPS immutate.
Prova Annulla, salva layer/progetto e riapri. Per il test tecnico nella console:

```python
import prese_fotografiche.smoke_test_import as t
t.run()
```

I test Python verificano default, duplicati, geometrie mancanti, distanze e
annullamento del lotto con layer simulati. QGIS non è presente nell'ambiente di
sviluppo: selezione file, pannello, direzione geodetica, aggiornamento automatico
e persistenza nei provider richiedono il collaudo reale in QGIS 3.44/macOS.
