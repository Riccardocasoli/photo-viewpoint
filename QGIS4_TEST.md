# Collaudo di Photo viewpoint 0.7.6

Questa è una versione sperimentale. Le prove automatiche sono passate su
QGIS 3.40.6 / Qt 5.15.15; la 0.7.0 è stata collaudata su QGIS 4.2.3. Le novità della 0.7.6 vanno ricontrollate su QGIS 4.

1. In QGIS 4 usa un nuovo profilo utente e una copia del progetto di prova.
2. Da **Plugin → Gestisci e installa plugin → Installa da ZIP**, seleziona
   `prese_fotografiche_v0.7.6.zip` senza estrarlo. Abilita Photo viewpoint.
3. Crea un layer in un CRS proiettato in metri, ad esempio EPSG:32632 se
   adatto alla zona. Prova un layer temporaneo e uno persistente.
4. Crea una presa con tre clic, assegna una foto, verifica l'anteprima,
   modifica la presa e prova annulla/ripristina. Salva e riapri il progetto.
5. Importa una foto con GPS e una senza GPS; posiziona la seconda a mano.
   Sposta la prima e verifica che `distGPS` si aggiorni.
6. Nel layout di stampa apri **Layout Photos** dalla sua barra o dal menu **Layout → Layout Photos**. Genera un
   richiamo, sposta e ridimensiona il riquadro e premi Generate / Update senza
   usare il salvataggio nel layer. Verifica che misure e posizione restino.
   Salva nel layer, elimina il riquadro e rigenera per verificare il recupero.
   Salva il progetto, riaprilo e ripeti l'aggiornamento.
7. Seleziona il layer delle prese, senza attivare Photo preview. Fermati sopra una presa con
   foto locale; muovi il puntatore di qualche pixel sullo stesso punto e verifica
   che resti visibile. Attendi due secondi e verifica che non compaia un secondo
   fumetto. Allontanati dalla presa, poi prova l’apertura al clic con Photo preview.
8. Nel layout scegli solo Caption, poi prova un secondo campo, cambiane l'ordine
   e imposta carattere, colore, allineamento e sfondo semitrasparente. Salva e
   riapri il progetto; verifica che le scelte siano riproposte. Prova anche
   a deselezionare tutti i campi per non mostrare alcuna didascalia.
9. Se qualcosa fallisce, annota versione QGIS/Qt, sistema operativo,
   azione eseguita e messaggio Python dalla scheda dei log.

## Per chi sviluppa

Con i sorgenti disponibili come pacchetto `prese_fotografiche`, nella
console Python di QGIS eseguire:

```python
from prese_fotografiche.tools.smoke_desktop import run
run(iface)
```

I test non sono inclusi nello ZIP destinato al catalogo. Dal repository
generare lo ZIP con `python tools/package.py --release`. Dopo il collaudo
QGIS 4, aggiornare prima i sorgenti GitHub e preparare la versione pubblica.

Verifica la lingua anche dopo un riavvio di QGIS: italiano se impostato, inglese altrimenti. Apri ciascun manuale HTML in un browser e controlla icone e schermate.
