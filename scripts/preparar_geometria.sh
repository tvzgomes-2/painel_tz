#!/usr/bin/env bash
# preparar_geometria.sh — gera ../build/municipios.topojson a partir do
# shapefile de municípios do IBGE (BR_Municipios_2022.shp).
#
# Fonte do shapefile: parte do cofre privado (03 - Dados/_data/espacial/),
# não incluída neste repositório. Requer mapshaper (npm install -g mapshaper).
#
# Roda uma vez só — a geometria não muda entre v1/v2/v3 do painel, só os
# atributos (ver build_data.py). Resultado final: ~1,2 MB (simplificado e
# convertido para topojson, que deduplica fronteiras compartilhadas).

set -e
cd "$(dirname "$0")"
VAULT=../../doutorado
SHP="$VAULT/03 - Dados/_data/espacial/BR_Municipios_2022.shp"
BUILD=../build
mkdir -p "$BUILD"

mapshaper "$SHP" \
  -proj wgs84 \
  -simplify 8% keep-shapes \
  -filter-fields CD_MUN \
  -rename-fields cod_ibge=CD_MUN \
  -o format=geojson precision=0.0001 "$BUILD/municipios_simpl.geojson"

mapshaper "$BUILD/municipios_simpl.geojson" \
  -simplify 3% keep-shapes \
  -clean \
  -o format=topojson quantization=1e5 "$BUILD/municipios.topojson"

echo "gerado: $BUILD/municipios.topojson"
