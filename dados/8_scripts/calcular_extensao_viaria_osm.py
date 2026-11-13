#!/usr/bin/env python3
"""⚠️ SUPERADO — usar `calcular_osm_viario_onibus_ciclo.py` (mesma pasta).
Este script só calculava viário total sem classificação e não tratava
transporte coletivo por ônibus. Mantido apenas como histórico (não apagar
sem confirmação, conforme padrão do cofre); não rodar.

calcular_extensao_viaria_osm.py — extensão do sistema viário e da malha
cicloviária por município, calculada a partir do OpenStreetMap (OSM), para
completar o item pendente do Banco Municipal v3 ("extensão viária e
cicloviária"). O IBGE não publica essa série por município; o que tínhamos do
SIMU (`km_ciclovias_simu` etc.) é autodeclarado e muito esparso (95/5.570
municípios) — isto aqui é um cálculo geométrico direto sobre a malha viária
real, cobrindo todos os 5.570 municípios.

FONTE: extratos regionais do Brasil (Geofabrik), 5 arquivos .osm.pbf que juntos
cobrem o país (bem mais leve que baixar o arquivo nacional inteiro):
  https://download.geofabrik.de/south-america/brazil/{regiao}-latest.osm.pbf
  regioes: norte (150 MB) · centro-oeste (191 MB) · sul (400 MB) ·
           nordeste (415 MB) · sudeste (812 MB)

MÉTODO:
  1. Baixa o extrato regional (retomável — pula o que já existe).
  2. Para cada UF dessa região, recorta a malha viária (todas as vias,
     tag highway=*) dentro do retângulo envolvente dos seus municípios,
     usando pyrosm (engine out-of-core, memória limitada).
  3. Faz a interseção geométrica (geopandas.overlay) entre as vias e os
     polígonos municipais — isso PARTE as vias exatamente na fronteira do
     município, então uma via que atravessa 2 municípios tem seu
     comprimento corretamente dividido entre eles (não conta em dobro nem
     é atribuída inteira a um só).
  4. Comprimento calculado de forma GEODÉSICA (pyproj.Geod, elipsoide
     WGS84) — não depende de escolher uma projeção/CRS métrica.
  5. Classifica:
       - extensão viária total = soma de todas as linhas (qualquer highway=*)
       - extensão de CICLOVIA  = linhas com highway=='cycleway' (via
         segregada, com direito de passagem próprio)
       - extensão de CICLOFAIXA = linhas cuja tag cycleway indica pintura/
         sinalização sobre uma via comum (lane, track, shared_lane etc.)
     Essa distinção espelha a mesma dicotomia ciclovia × ciclofaixa usada
     nas variáveis `km_via_ciclovias`/`km_via_ciclofaixas` do SIMU — dá para
     comparar as duas fontes.
  6. Salva 1 CSV por UF (resumível — se um UF falhar ou você interromper,
     rode de novo e ele pula os UFs já prontos) e ao final concatena tudo e
     integra ao `base_municipal_v3.csv`.

⚠️ TAREFA PESADA. Recomendo testar primeiro com 1 UF pequena:
    python calcular_extensao_viaria_osm.py --uf DF
Depois, para rodar tudo (pode levar várias horas; é seguro interromper e
retomar depois, cada UF concluído fica marcado):
    python calcular_extensao_viaria_osm.py

REQUISITOS (instalar antes):
    pip install pyrosm geopandas shapely pyproj
(pyrosm tem wheel pronta para Windows/Python 3.14 — não deve precisar de
compilador, ao contrário do que aconteceu com o pysus.)
"""
import argparse, os, sys, time, urllib.request
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
from pyproj import Geod

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
ESPACIAL = os.path.join(V, "espacial", "BR_Municipios_2022.shp")
OSM_DIR = os.path.join(V, "OSM")
POR_UF_DIR = os.path.join(OSM_DIR, "por_uf")
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")

GEOFABRIK = "https://download.geofabrik.de/south-america/brazil/{regiao}-latest.osm.pbf"

# UF -> região (Geofabrik) e -> a ordem abaixo processa as regiões menores primeiro
UF_REGIAO = {
    # Norte (150 MB)
    "AC": "norte", "AP": "norte", "AM": "norte", "PA": "norte",
    "RO": "norte", "RR": "norte", "TO": "norte",
    # Centro-Oeste (191 MB)
    "DF": "centro-oeste", "GO": "centro-oeste", "MT": "centro-oeste", "MS": "centro-oeste",
    # Sul (400 MB)
    "PR": "sul", "RS": "sul", "SC": "sul",
    # Nordeste (415 MB)
    "AL": "nordeste", "BA": "nordeste", "CE": "nordeste", "MA": "nordeste",
    "PB": "nordeste", "PE": "nordeste", "PI": "nordeste", "RN": "nordeste", "SE": "nordeste",
    # Sudeste (812 MB) — deixado por último (o maior)
    "ES": "sudeste", "MG": "sudeste", "RJ": "sudeste", "SP": "sudeste",
}
ORDEM_UF = sorted(UF_REGIAO, key=lambda uf: ["norte", "centro-oeste", "sul", "nordeste", "sudeste"].index(UF_REGIAO[uf]))

CICLOFAIXA_TAGS = {"lane", "opposite_lane", "track", "opposite_track", "shared_lane", "share_busway"}

geod = Geod(ellps="WGS84")


def log(msg):
    print(msg, flush=True)


def comprimento_km(geom):
    """Comprimento geodésico (WGS84) em km, para LineString ou MultiLineString."""
    if geom is None or geom.is_empty:
        return 0.0
    try:
        if isinstance(geom, MultiLineString):
            return sum(geod.geometry_length(g) for g in geom.geoms) / 1000.0
        return geod.geometry_length(geom) / 1000.0
    except Exception:
        # fallback manual bem simples, caso a API do pyproj mude
        coords = []
        if isinstance(geom, LineString):
            coords = [list(geom.coords)]
        elif isinstance(geom, MultiLineString):
            coords = [list(g.coords) for g in geom.geoms]
        total_m = 0.0
        for c in coords:
            for (lon1, lat1), (lon2, lat2) in zip(c[:-1], c[1:]):
                _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
                total_m += dist
        return total_m / 1000.0


def baixa_pbf(regiao):
    os.makedirs(OSM_DIR, exist_ok=True)
    dest = os.path.join(OSM_DIR, f"{regiao}-latest.osm.pbf")
    if os.path.exists(dest) and os.path.getsize(dest) > 10_000_000:
        return dest
    url = GEOFABRIK.format(regiao=regiao)
    log(f"  baixando {url} -> {dest} (pode demorar alguns minutos)...")
    urllib.request.urlretrieve(url, dest)
    log(f"  ok ({os.path.getsize(dest)/1e6:.0f} MB)")
    return dest


def carrega_municipios():
    log(f"lendo malha municipal: {ESPACIAL}")
    g = gpd.read_file(ESPACIAL)
    g = g.rename(columns={"CD_MUN": "cod_ibge", "NM_MUN": "nome_mun", "SIGLA_UF": "sigla_uf"})
    g["cod_ibge"] = g["cod_ibge"].astype(str).str.zfill(7)
    g = g.to_crs(4326)
    log(f"  {len(g)} municípios, CRS original convertido para EPSG:4326")
    return g[["cod_ibge", "nome_mun", "sigla_uf", "geometry"]]


def processa_uf(sigla, munis_uf, pbf_path):
    from pyrosm import OSM

    bbox = list(munis_uf.total_bounds)  # [minx, miny, maxx, maxy]
    log(f"  [{sigla}] bbox={[round(x, 2) for x in bbox]} | {len(munis_uf)} municípios")
    osm = OSM(pbf_path, bounding_box=bbox, engine="out_of_core")
    net = osm.get_network(network_type="all", extra_attributes=["cycleway", "surface"])
    if net is None or len(net) == 0:
        log(f"  [{sigla}] !! nenhuma via encontrada — pulando (confira a bbox/arquivo).")
        return None
    log(f"  [{sigla}] {len(net)} vias lidas do OSM")

    net = net.set_crs(4326) if net.crs is None else net.to_crs(4326)
    cols = ["id", "highway", "geometry"] + (["cycleway"] if "cycleway" in net.columns else [])
    net = net[cols].copy()
    if "cycleway" not in net.columns:
        net["cycleway"] = None

    clipped = gpd.overlay(net, munis_uf[["cod_ibge", "geometry"]], how="intersection", keep_geom_type=False)
    clipped = clipped[clipped.geometry.type.isin(["LineString", "MultiLineString"])]
    if clipped.empty:
        log(f"  [{sigla}] !! interseção vazia — pulando.")
        return None

    clipped["km"] = clipped.geometry.apply(comprimento_km)
    clipped["is_ciclovia"] = clipped["highway"] == "cycleway"
    clipped["is_ciclofaixa"] = (~clipped["is_ciclovia"]) & clipped["cycleway"].isin(CICLOFAIXA_TAGS)

    g = clipped.groupby("cod_ibge").agg(
        extensao_viaria_km=("km", "sum"),
    ).reset_index()
    g_ciclo = clipped[clipped.is_ciclovia].groupby("cod_ibge")["km"].sum().reset_index(name="extensao_ciclovia_km")
    g_faixa = clipped[clipped.is_ciclofaixa].groupby("cod_ibge")["km"].sum().reset_index(name="extensao_ciclofaixa_km")
    g = g.merge(g_ciclo, on="cod_ibge", how="left").merge(g_faixa, on="cod_ibge", how="left")
    for c in ["extensao_viaria_km", "extensao_ciclovia_km", "extensao_ciclofaixa_km"]:
        g[c] = g[c].fillna(0).round(2)

    log(f"  [{sigla}] OK — viário total: {g.extensao_viaria_km.sum():,.0f} km | "
        f"ciclovia: {g.extensao_ciclovia_km.sum():,.0f} km | ciclofaixa: {g.extensao_ciclofaixa_km.sum():,.0f} km")
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uf", nargs="+", help="processar só estas siglas de UF (teste). Ex.: --uf DF")
    args = ap.parse_args()

    os.makedirs(POR_UF_DIR, exist_ok=True)
    munis = carrega_municipios()

    ufs = [u.upper() for u in args.uf] if args.uf else ORDEM_UF
    invalid = [u for u in ufs if u not in UF_REGIAO]
    if invalid:
        sys.exit(f"UF(s) inválida(s): {invalid}. Use siglas de 2 letras.")

    t0 = time.time()
    for sigla in ufs:
        out_csv = os.path.join(POR_UF_DIR, f"{sigla}.csv")
        if os.path.exists(out_csv):
            log(f"[{sigla}] já processado — pulando ({out_csv})")
            continue
        regiao = UF_REGIAO[sigla]
        log(f"\n=== {sigla} (região {regiao}) ===")
        try:
            pbf = baixa_pbf(regiao)
            munis_uf = munis[munis.sigla_uf == sigla]
            if munis_uf.empty:
                log(f"  !! nenhum município encontrado para UF={sigla} na malha municipal — confira SIGLA_UF.")
                continue
            g = processa_uf(sigla, munis_uf, pbf)
            if g is not None:
                g.to_csv(out_csv, index=False)
        except Exception as e:
            log(f"  !! ERRO em {sigla}: {e} — pulando (rode de novo depois para tentar de novo).")
            import traceback; traceback.print_exc()
            continue

    log(f"\n--- concluído em {(time.time()-t0)/60:.1f} min | consolidando resultados por UF ---")
    arqs = [os.path.join(POR_UF_DIR, f) for f in os.listdir(POR_UF_DIR) if f.endswith(".csv")]
    if not arqs:
        log("Nenhum resultado por UF encontrado ainda — nada a consolidar."); return
    todos = pd.concat([pd.read_csv(a, dtype={"cod_ibge": str}) for a in arqs], ignore_index=True)
    todos.to_csv(os.path.join(OUT, "extensao_viaria_osm.csv"), index=False)
    log(f"extensao_viaria_osm.csv: {len(todos)} municípios (de {len(ufs)} UF processadas nesta rodada)")

    if not os.path.exists(BASE_CSV):
        log(f"AVISO: {BASE_CSV} não encontrado — não integrei ao wide (só salvei o CSV consolidado)."); return
    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].astype(str).str.zfill(7)
    for c in ["extensao_viaria_km", "extensao_ciclovia_km", "extensao_ciclofaixa_km"]:
        if c in base.columns:
            base = base.drop(columns=[c])
    base = base.merge(todos[["cod_ibge", "extensao_viaria_km", "extensao_ciclovia_km", "extensao_ciclofaixa_km"]],
                       on="cod_ibge", how="left")
    if "area_km2" in base.columns:
        area = pd.to_numeric(base["area_km2"], errors="coerce")
        base["densidade_viaria_km_km2"] = (base["extensao_viaria_km"] / area).round(3)
    base.to_csv(BASE_CSV, index=False)
    log(f"OK — base_municipal_v3.csv atualizado: {base.shape[0]} x {base.shape[1]} "
        f"({base.extensao_viaria_km.notna().sum()} municípios com extensão viária calculada)")


if __name__ == "__main__":
    main()
