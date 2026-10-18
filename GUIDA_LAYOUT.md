# Foto nel layout — versione 0.3.0

Aggiornamento dello stesso plugin. I layer esistenti restano utilizzabili.
La disposizione iniziale non tiene conto di mappa, titoli, legende, altre foto
né altri elementi grafici: la sovrapposizione è consentita.

## Generare immagini con proporzioni corrette

1. Prepara un layout statico con una mappa che mostra il layer Prese fotografiche.
   Il layout deve usare millimetri e ogni presa deve avere un JPG locale in photo.
2. Nella finestra principale apri Foto nel layout e scegli layout, mappa e layer.
3. Imposta **Larghezza massima** e **Altezza massima**. Sono i limiti del riquadro
   di adattamento, non dimensioni imposte identiche a tutte le foto.
4. Premi Genera / aggiorna. Ciascuna foto rispetta il proprio rapporto d'aspetto:
   per esempio con massimo 40 × 30 mm, una foto 4000 × 2000 diventa 40 × 20 mm;
   una foto 2000 × 4000 diventa 15 × 30 mm.

Sono considerate anche le rotazioni EXIF che scambiano larghezza e altezza.
Le immagini non vengono stirate o ritagliate. Il riquadro nativo QGIS usa
ZoomResizeFrame: durante il ridimensionamento grafico adatta il bordo alla foto.
La funzione resta da collaudare in QGIS/macOS per i diversi file e orientamenti.

La prima disposizione è in righe a partire dal margine pagina, indipendente
dalla mappa e da tutti gli altri elementi. Puoi sovrapporre le foto anche fra loro.
Se le foto sono numerose o grandi, alcune possono uscire dalla pagina: il plugin
lo segnala ma non le omette. Riposizionale prima di esportare.

## Modificare posizione e dimensioni nel layout

Usa Seleziona / sposta elementi nel layout. Seleziona la FOTO, trascinala per
spostarla e usa le maniglie del riquadro per ridimensionarla. La didascalia segue
il bordo inferiore e la linea mantiene il collegamento al punto di presa.
In alternativa usa Posizione e dimensione nelle proprietà dell'elemento foto.
Non trascinare soltanto la didascalia o la linea; non ruotare il riquadro foto.

Per un ridimensionamento proporzionale usa una maniglia d'angolo. La modalità
nativa ZoomResizeFrame conserva il rapporto del contenuto e riadatta il frame.
Controlla il risultato delle maniglie nel tuo QGIS: non cambiare la modalità
immagine in Stretch, che provocherebbe una deformazione.

## Salvare posizione e dimensioni nella tabella del layer

Riapri Foto nel layout, scegli la stessa mappa e lo stesso layer, poi premi
**Salva posizioni e dimensioni (pf_x, pf_y, dimX, dimY)**.

| Campo | Tipo | Significato |
| --- | --- | --- |
| pf_x | Decimale | X dell'angolo superiore sinistro della foto in mm dal bordo sinistro della pagina |
| pf_y | Decimale | Y dello stesso angolo in mm dall'alto della pagina |
| pf_map | Testo | Identificativo della mappa cui sono associate le impostazioni |
| dimX | Decimale | Larghezza effettiva del riquadro foto in mm |
| dimY | Decimale | Altezza effettiva del riquadro foto in mm |
| Didascalia | Testo | Descrizione aggiunta sotto il nome della fotografia |

Questi campi vengono creati se mancanti alla prima generazione o al salvataggio.
I nomi sono compatibili con il limite di 10 caratteri dello SHP. Didascalia ha
lunghezza 254 caratteri quando il campo viene creato, adatta alla tabella DBF.
Il testo preesistente non viene sovrascritto dal salvataggio delle misure.

**Salva le modifiche del layer in QGIS e salva anche il progetto .qgz.** Il plugin
non esegue commit automatici. Creazione dei campi e aggiornamenti sono annullabili
nella cronologia del layer; gli elementi del layout sono salvati nel progetto.

## Come vengono riutilizzati i valori

- pf_x e pf_y validi ripristinano la posizione.
- dimX e dimY validi ripristinano la dimensione, anche se supera i massimi del dialogo.
- La coppia dimX/dimY deve rispettare le proporzioni dell'immagine. Se la modifichi
  con valori incompatibili, la foto viene adattata entro quella coppia di limiti
  conservando il rapporto d'aspetto; non viene deformata.
- Con dimX/dimY NULL o non validi si usano i massimi del dialogo. Per ricalcolare
  tutte le foto con nuovi massimi, svuota entrambi i campi dimensione.
- Con pf_x/pf_y NULL si torna alla disposizione iniziale.
- Le impostazioni valgono per pf_map. Con pf_map vuoto si possono usare in una
  mappa diversa. È memorizzata una sola configurazione per presa nel layer;
  salvarne un'altra sostituisce quella precedente.

Puoi modificare i valori anche dalla tabella, quindi rigenerare il layout.

## Campo Didascalia

Compila Didascalia in tabella e riesegui Genera / aggiorna. Il testo visualizzato è:

```
F001 — ingresso_nord.jpg
Accesso principale al fabbricato
```

La prima riga contiene il codice/nome della presa e il nome del file immagine.
La descrizione viene aggiunta sotto, se presente. La larghezza segue la foto e
l'altezza del testo viene ricalcolata durante il ridimensionamento. Controlla i
codici e i nomi file molto lunghi e la leggibilità dopo riduzioni importanti.

## Aggiornamento e limiti

Dopo cambi a inquadratura, scala, rotazione/posizione della mappa, geometrie dei
punti, photo o Didascalia, esegui Genera / aggiorna. Prima salva posizione e misure
manuali da conservare. La rigenerazione sostituisce soltanto gli elementi creati
per quella mappa; non cambia né rimuove gli altri elementi del layout.
Le foto sono collocate sopra gli elementi già presenti; puoi poi modificarne
l'ordine con i comandi nativi del layout.

La presenza del layer e la visibilità alla scala sono controllate; i punti sono
scelti in base alla geometria nel rettangolo della mappa con CRS e rotazione.
Filtri del provider sono rispettati. Non sono valutati filtri di simbologia per
singola feature, clipping a sagome o filtri temporali. Atlante non supportato.
Sono usate soltanto foto locali leggibili, non URL web. Le immagini non sono
incorporate nel progetto: conserva i file originali.

Dopo riapertura del progetto, con il plugin attivo, vengono ripristinati i
collegamenti al movimento delle foto. Dopo eliminazioni o riordino delle feature,
soprattutto negli SHP, rigenera. Senza plugin attivo i richiami restano elementi
statici. Verifica sempre la pagina esportata, comprese sovrapposizioni volute,
parti oltre i bordi e possibili incroci fra linee.

## Collaudo

Sintassi, rapporti d'aspetto, disposizione indipendente dagli altri elementi,
composizione della didascalia e salvataggio dei campi sono verificati senza QGIS.
Rendering e trascinamento richiedono il collaudo in QGIS 3.44 su macOS.
Prova con una foto orizzontale e una verticale, ridimensionale, salva le misure,
compila Didascalia e rigenera. Le misure devono essere ripristinate.

Test d'integrazione incluso, da eseguire nella console QGIS:

```python
import prese_fotografiche.smoke_test_layout as t
t.run()
```

Il test usa un layout e un layer isolati temporanei, senza salvare dati utente.
Se fallisce, copia il traceback completo.
