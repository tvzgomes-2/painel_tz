#!/usr/bin/env python3
"""Lê saída COPY (texto) de uma tabela PostGIS no stdin e grava/anexa uma camada
num GeoPackage. Uso: copy2gpkg.py <gpkg> <layer> <w|a>"""
import sys, re
import geopandas as gpd
from shapely import from_wkb

GPKG, LAYER, MODE = sys.argv[1], sys.argv[2], sys.argv[3]
COPY_RE = re.compile(r'^COPY\s+("?[^". ]+"?)\.("?[^". ]+"?)\s*\((.*)\)\s+FROM stdin;')

def unesc(f):
    if f == r'\N': return None
    if '\\' not in f: return f
    return (f.replace(r'\t','\t').replace(r'\n','\n').replace(r'\r','\r').replace('\\\\','\\'))

cols=None; gidx=None; recs=[]; geoms=[]; in_copy=False
for line in sys.stdin:
    line=line.rstrip('\n')
    if not in_copy:
        m=COPY_RE.match(line)
        if m:
            cols=[c.strip().strip('"') for c in m.group(3).split(',')]
            gidx=cols.index('geom')
            in_copy=True
        continue
    if line==r'\.': break
    parts=line.split('\t')
    g=parts[gidx]
    geoms.append(from_wkb(bytes.fromhex(g)) if g and g!=r'\N' else None)
    rec={c:unesc(parts[i]) for i,c in enumerate(cols) if i!=gidx}
    recs.append(rec)

gdf=gpd.GeoDataFrame(recs, geometry=geoms, crs='EPSG:4674')
# GPKG reserva 'fid'; renomear colunas conflitantes
gdf=gdf.rename(columns={c:c+'_src' for c in gdf.columns if c.lower()=='fid'})
gdf.to_file(GPKG, layer=LAYER, driver='GPKG', mode=MODE)
print(f"{LAYER}: {len(gdf)} feições, {len(cols)-1} atributos -> {GPKG}", file=sys.stderr)
