# Filiali Banco BPM e Crédit Agricole per regione

Sito statico (GitHub Pages): `index.html` è la pagina d'accesso con la mappa d'Italia; ogni regione ha la sua mappa in `<regione>/index.html`.

## Pubblicare su GitHub Pages
1. Crea un repository su GitHub e carica il contenuto di questa cartella.
2. Settings → Pages → *Deploy from a branch* → branch `main`, cartella `/ (root)`.
3. Il sito sarà su `https://<utente>.github.io/<repository>/`.

I link sono relativi, quindi funziona anche in sottocartella. Le mappe caricano Leaflet e le tessere OpenStreetMap da internet.

## Aggiornare i dati
```
sh tools/fetch.sh /percorso/dati      # scarica locator delle banche e confini ISTAT
python3 tools/build.py /percorso/dati # rigenera tutte le pagine
```
Fonti: bancobpm.it/trova-filiali, credit-agricole.it/filiali, confini openpolis/geojson-italy (ISTAT).
