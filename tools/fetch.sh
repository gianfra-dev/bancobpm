#!/bin/sh
# Scarica le fonti nella cartella indicata (default ./data). Uso: sh fetch.sh [cartella]
D=${1:-data}; mkdir -p "$D/g"; B=https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson
curl -sL -A "Mozilla/5.0" -o "$D/bt.html" https://www.bancobpm.it/trova-filiali/tutte-le-filiali/
curl -sL -A "Mozilla/5.0" -o "$D/ca.html" https://www.credit-agricole.it/filiali
curl -sL -o "$D/prov.geojson" $B/limits_IT_provinces.geojson
curl -sL -o "$D/g/regions.geojson" $B/limits_IT_regions.geojson
for i in $(seq 1 20); do curl -sL -o "$D/g/com$i.geojson" $B/limits_R_${i}_municipalities.geojson; done
