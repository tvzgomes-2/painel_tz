#!/usr/bin/env python3
"""calcular_osm_viario_onibus_ciclo.py — a partir do OpenStreetMap (OSM), por
município (5.570), calcula:

  A) EXTENSÃO DO SISTEMA VIÁRIO, COM CLASSIFICAÇÃO (hierarquia viária usual
     de PDMU): estrutural (motorway/trunk/primary), coletora (secondary/
     tertiary), local (residential/unclassified/living_street/service).
  B) TRANSPORTE COLETIVO POR ÔNIBUS:
     B1. extensão de corredor/faixa exclusiva de ônibus (tags busway=lane|
         track, lanes:psv, highway=busway) — via, não relação;
     B2. nº de pontos de ônibus (nós highway=bus_stop / public_transport=
         platform+bus=yes);
     B3. nº de terminais/estações de ônibus (amenity=bus_station).
     B4. rotas de ônibus (relações OSM route=bus, com ref/operador) — extensão
         somada de todas as linhas que passam pelo município (proxy de oferta
         de serviço; ruas com várias linhas contam mais de uma vez) e nº de
         rotas distintas. CONFIRMADO utilizável no teste do DF (20/07/2026:
         27 relações, todas com geometria de linha válida) — ver ressalva
         abaixo sobre a incerteza original e o que muda se algum UF falhar.
  C) EXTENSÃO CICLOVIÁRIA: ciclovia (highway=cycleway, segregada) e
     ciclofaixa (tag cycleway=lane/track sobre via comum) — mesma dicotomia
     das variáveis (muito esparsas) que já vieram do SIMU, para comparar.

⚠️ Sobre B4 (rotas de ônibus): a documentação do pyrosm só demonstra
get_data_by_custom_criteria(keep_relations=True) para POIs/edifícios
(relações do tipo multipolígono) — não garantia, a priori, que uma relação
"sequência ordenada de vias" (route=bus, não um polígono fechado) viesse como
LineString utilizável. TESTADO no DF (20/07/2026): funcionou — 27 relações,
todas com geometria de linha válida (23 MultiLineString + 4 LineString), e
os dados foram agregados normalmente. Ainda assim, o script sempre salva uma
amostra de diagnóstico por UF (`_data/OSM/diagnostico_rotas_onibus/`) — se
algum UF vier com geometria quebrada/vazia (qualidade do mapeamento OSM varia
muito por região), o script avisa e simplesmente não agrega aquele UF nessa
variável (sem quebrar o resto). Se isso acontecer em muitos UFs, a alternativa
seria a Overpass API (melhor ferramenta para relações, mas por consulta via
internet, não pelo .pbf local).

⚠️⚠️ VALIDAÇÃO CONTRA DADO OFICIAL (teste no DF, 20/07/2026) — leitura obrigatória:
Comparei os resultados do DF com fontes oficiais (DER-DF, SEMOB-DF, DFTrans):
  - Viário estrutural: 1.744 km (OSM) × 1.902,5 km oficial — ✅ ~92%.
  - Ciclovia+ciclofaixa: 614,5 km (OSM) × 687–745 km oficial — ✅ ~85-90%.
  - Corredor/faixa exclusiva de ônibus: 8 km (OSM) × ~104 km oficial ("faixas
    marginais e BRT") — ⚠️ muito subestimado (~8% do esperado).
  - ROTAS DE ÔNIBUS (relações route=bus): 27 (OSM) × 724 linhas oficiais
    (DFTrans) — 🔴 GRAVEMENTE subestimado (~4% de cobertura).
Conclusão: o OSM tem excelente cobertura de infraestrutura FÍSICA visível
(vias, ciclovias), mas cobertura muito fraca de dados de OPERAÇÃO de
transporte público (linhas, corredores — exige mapeamento especializado).
`extensao_rotas_onibus_km`/`n_rotas_onibus_osm`/`extensao_corredor_onibus_km`
NÃO servem como medida de QUANTIDADE de oferta de ônibus — variam mais com o
esforço de mapeamento colaborativo local (que pode correlacionar com renda/
escolaridade do município) do que com o serviço real.

⚠️⚠️⚠️ TESTE DE DISCRIMINAÇÃO EM 10 MUNICÍPIOS (20/07/2026) — reprovado como
indício de SISTEMA MUNICIPAL, mantido só como presença bruta:
A ideia original era usar os 4 sinais (pontos/terminais/rotas/corredor) como
"indício de existência" de sistema de ônibus (`indicio_onibus_osm`, positivo/
sensível: ausência não prova ausência). Testado contra uma amostra
deliberada de 10 municípios médios/pequenos com rótulo conhecido pela MUNIC
2020 (5 confirmados COM sistema intramunicipal, 5 confirmados SEM) — ver
`valida_municipios()` / `--municipios`. Resultado: 0% falso-negativo, mas
100% FALSO-POSITIVO — o OSM "achou sinal" nos 10 casos, inclusive nos 5 sem
sistema. `sinais_onibus_osm` nem separa os grupos (média 2,0 sinais no grupo
COM × 2,2 no grupo SEM). Hipótese mais provável: a MUNIC pergunta se o
município OPERA sistema próprio (concessão municipal), enquanto o OSM marca
QUALQUER ônibus que passe pelo território (linha intermunicipal, metropolitana,
rodoviária de longa distância) — são construtos diferentes, não um erro de
medição corrigível com mais sinal ou limiar mais alto. Caso ilustrativo:
Almirante Tamandaré (RM Curitiba, servido pela rede metropolitana RIT) tem 92
pontos de ônibus no OSM e MUNIC diz "não tem sistema [próprio]".
DECISÃO (20/07/2026, com o autor): manter a variável, mas RENOMEADA e
reframed — `presenca_onibus_osm` (antes `indicio_onibus_osm`) significa só
"há infraestrutura/linha de ônibus de algum tipo no território", não
"o município tem sistema de transporte coletivo organizado". Provavelmente
sem poder explicativo para a hipótese da tese (grupos econômicos × Tarifa
Zero) — registrar como variável descritiva, com esta ressalva sempre citada
junto. `n_pontos_onibus_osm` continua sendo o sinal individual mais robusto
dos quatro por ser o mais fácil de mapear, mas também não distingue os
grupos no teste (ver `_data/OSM/validacao_10_municipios/relatorio.csv`).
O script ainda cruza `presenca_onibus_osm` com a MUNIC 2020 na consolidação
completa (todas as UFs) e imprime a taxa de falso-negativo — mas o teste de
10 municípios é a evidência que importa (n=1 do DF era só verdadeiro-positivo,
não testava o caso "sem sistema").

⚠️ ATUALIZAÇÃO (20/07/2026): duas correções/adições:
  1) `extensao_viaria_total_km` agora soma SÓ as classes motorizadas (estrutural+
     coletora+local) — antes somava tudo que get_network("all") devolve
     (ciclovia, calçada, trilha...), inflando ~21% do total. Caminhos de
     pedestre (footway/path/pedestrian/steps/corridor) viraram variável
     própria, `extensao_pedestres_km`. O resto (track, bridleway etc.) é
     descartado — nem soma ao total, nem vira variável.
  2) Novo modo `--municipios COD1 COD2 ...`: roda o pipeline só para uma lista
     de cod_ibge (não a UF inteira) — foi o que permitiu o teste de
     discriminação acima. Salva em `_data/OSM/validacao_10_municipios/`
     (separado do cache retomável `por_uf/`) + `relatorio.csv`.

FONTE: extratos regionais do Brasil (Geofabrik) — ver baixar/carrega abaixo.
MÉTODO (igual em A/B/C): pyrosm (engine out-of-core) recorta a bbox da UF;
gpd.overlay faz a interseção geométrica com os polígonos municipais (parte a
via exatamente na fronteira — sem contar em dobro, sem atribuir inteira a 1
município); comprimento geodésico via pyproj.Geod (WGS84, sem depender de
projeção). Pontos (B2/B3) usam junção espacial simples (ponto-em-polígono).

⚠️ TAREFA PESADA. Teste primeiro com 1 UF pequena:
    python calcular_osm_viario_onibus_ciclo.py --uf DF
Depois, para rodar tudo (retomável — pode interromper e retomar):
    python calcular_osm_viario_onibus_ciclo.py

REQUISITOS: pip install pyrosm geopandas shapely pyproj
"""
import argparse, os, sys, time, json, urllib.request, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
from pyproj import Geod
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
ESPACIAL = os.path.join(V, "espacial", "BR_Municipios_2022.shp")
OSM_DIR = os.path.join(V, "OSM")
POR_UF_DIR = os.path.join(OSM_DIR, "por_uf")
DIAG_DIR = os.path.join(OSM_DIR, "diagnostico_rotas_onibus")
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")

GEOFABRIK = "https://download.geofabrik.de/south-america/brazil/{regiao}-latest.osm.pbf"

UF_REGIAO = {
    "AC": "norte", "AP": "norte", "AM": "norte", "PA": "norte",
    "RO": "norte", "RR": "norte", "TO": "norte",
    "DF": "centro-oeste", "GO": "centro-oeste", "MT": "centro-oeste", "MS": "centro-oeste",
    "PR": "sul", "RS": "sul", "SC": "sul",
    "AL": "nordeste", "BA": "nordeste", "CE": "nordeste", "MA": "nordeste",
    "PB": "nordeste", "PE": "nordeste", "PI": "nordeste", "RN": "nordeste", "SE": "nordeste",
    "ES": "sudeste", "MG": "sudeste", "RJ": "sudeste", "SP": "sudeste",
}
ORDEM_UF = sorted(UF_REGIAO, key=lambda uf: ["norte", "centro-oeste", "sul", "nordeste", "sudeste"].index(UF_REGIAO[uf]))

# --- classificação viária (hierarquia usual de PDMU) ---
CLASSE_VIARIA = {
    "motorway": "estrutural", "motorway_link": "estrutural",
    "trunk": "estrutural", "trunk_link": "estrutural",
    "primary": "estrutural", "primary_link": "estrutural",
    "secondary": "coletora", "secondary_link": "coletora",
    "tertiary": "coletora", "tertiary_link": "coletora",
    "residential": "local", "living_street": "local",
    "unclassified": "local", "service": "local",
}
CICLOFAIXA_TAGS = {"lane", "opposite_lane", "track", "opposite_track", "shared_lane", "share_busway"}
BUSWAY_TAGS = {"lane", "track", "opposite_lane", "opposite_track"}
# infraestrutura de pedestres — não é "sistema viário" (não veicular), mas tem
# valor analítico próprio (caminhabilidade); reportada à parte, não somada ao total.
PEDESTRE_TAGS = {"pedestrian", "footway", "path", "steps", "corridor"}
# resto (track, bridleway, raceway, escape etc.) — nem viário motorizado nem
# pedestre reconhecível; ambíguo/marginal, descartado (nem soma ao total, nem
# vira variável própria), conforme decisão de 20/07/2026.

geod = Geod(ellps="WGS84")


def log(msg):
    print(msg, flush=True)


def comprimento_km(geom):
    if geom is None or geom.is_empty:
        return 0.0
    try:
        if isinstance(geom, MultiLineString):
            return sum(geod.geometry_length(g) for g in geom.geoms) / 1000.0
        return geod.geometry_length(geom) / 1000.0
    except Exception:
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
    log(f"  {len(g)} municípios, CRS convertido para EPSG:4326")
    return g[["cod_ibge", "nome_mun", "sigla_uf", "geometry"]]


def clipa_e_mede(linhas_gdf, munis_uf, cols_extra):
    """Interseciona linhas com os polígonos municipais e devolve o gdf com 'cod_ibge' e 'km'."""
    cols = ["id", "geometry"] + cols_extra
    cols = [c for c in cols if c in linhas_gdf.columns]
    linhas = linhas_gdf[cols].copy()
    clip = gpd.overlay(linhas, munis_uf[["cod_ibge", "geometry"]], how="intersection", keep_geom_type=False)
    clip = clip[clip.geometry.type.isin(["LineString", "MultiLineString"])]
    if clip.empty:
        return clip
    clip["km"] = clip.geometry.apply(comprimento_km)
    return clip


# ============================================================
# A + B1 + C — tudo vem de UMA leitura de get_network("all")
# ============================================================
def le_rede_viaria(osm):
    net = osm.get_network(
        network_type="all",
        extra_attributes=["cycleway", "busway", "lanes:psv", "psv", "surface"],
    )
    return net


def classifica_e_mede(net, munis_uf):
    if net is None or len(net) == 0:
        return None
    net = net.set_crs(4326) if net.crs is None else net.to_crs(4326)
    for c in ["cycleway", "busway", "lanes:psv", "psv"]:
        if c not in net.columns:
            net[c] = None

    clip = clipa_e_mede(net, munis_uf, ["highway", "cycleway", "busway", "lanes:psv", "psv"])
    if clip.empty:
        return None

    clip["classe_viaria"] = clip["highway"].map(CLASSE_VIARIA)
    clip["is_pedestre"] = clip["highway"].isin(PEDESTRE_TAGS)
    clip["is_ciclovia"] = clip["highway"] == "cycleway"
    clip["is_ciclofaixa"] = (~clip["is_ciclovia"]) & clip["cycleway"].isin(CICLOFAIXA_TAGS)
    clip["is_corredor_onibus"] = (
        (clip["highway"] == "busway")
        | clip["busway"].isin(BUSWAY_TAGS)
        | (clip["lanes:psv"].notna() & (clip["lanes:psv"] != "0"))
        | (clip["psv"] == "designated")
    )

    # extensao_viaria_total_km = só classes motorizadas (estrutural+coletora+
    # local). Antes somava TUDO que get_network("all") devolve (inclui
    # ciclovia, calçada, trilha...), inflando ~21% do total com infraestrutura
    # não-viária. Pedestres agora é variável própria; o resto (track,
    # bridleway etc.) é descartado (decisão de 20/07/2026).
    motorizado = clip[clip.classe_viaria.notna()]
    g = motorizado.groupby("cod_ibge")["km"].sum().reset_index(name="extensao_viaria_total_km")
    for classe in ["estrutural", "coletora", "local"]:
        sub = motorizado[motorizado.classe_viaria == classe].groupby("cod_ibge")["km"].sum().reset_index(
            name=f"extensao_viaria_{classe}_km")
        g = g.merge(sub, on="cod_ibge", how="left")
    for nome, cond in [("pedestres", clip.is_pedestre), ("ciclovia", clip.is_ciclovia),
                       ("ciclofaixa", clip.is_ciclofaixa), ("corredor_onibus", clip.is_corredor_onibus)]:
        sub = clip[cond].groupby("cod_ibge")["km"].sum().reset_index(name=f"extensao_{nome}_km")
        g = g.merge(sub, on="cod_ibge", how="outer")
    for c in g.columns:
        if c != "cod_ibge":
            g[c] = g[c].fillna(0).round(2)
    return g


# ============================================================
# B2 + B3 — pontos e terminais de ônibus (nós/pontos, não vias)
# ============================================================
def le_pontos_onibus(osm, munis_uf):
    try:
        pts = osm.get_data_by_custom_criteria(
            custom_filter={"highway": ["bus_stop"], "public_transport": ["platform", "stop_position"]},
            osm_keys_to_keep=["highway", "public_transport"],
            keep_ways=False, keep_relations=False, keep_nodes=True,
        )
    except Exception as e:
        log(f"    !! erro lendo pontos de ônibus: {e}")
        return None
    if pts is None or len(pts) == 0:
        return None
    pts = pts.set_crs(4326) if pts.crs is None else pts.to_crs(4326)
    pts = pts[pts.geometry.type == "Point"]
    if pts.empty:
        return None
    j = gpd.sjoin(pts[["geometry"]], munis_uf[["cod_ibge", "geometry"]], how="inner", predicate="within")
    return j.groupby("cod_ibge").size().reset_index(name="n_pontos_onibus_osm")


def le_terminais_onibus(osm, munis_uf):
    try:
        term = osm.get_data_by_custom_criteria(
            custom_filter={"amenity": ["bus_station"]},
            osm_keys_to_keep=["amenity"],
            keep_ways=True, keep_relations=True, keep_nodes=True,
            extra_attributes=["name", "operator"],
        )
    except Exception as e:
        log(f"    !! erro lendo terminais de ônibus: {e}")
        return None
    if term is None or len(term) == 0:
        return None
    term = term.set_crs(4326) if term.crs is None else term.to_crs(4326)
    rep = gpd.GeoDataFrame(geometry=term.geometry.representative_point(), crs=term.crs)
    j = gpd.sjoin(rep, munis_uf[["cod_ibge", "geometry"]], how="inner", predicate="within")
    return j.groupby("cod_ibge").size().reset_index(name="n_terminais_onibus_osm")


# ============================================================
# B4 — DIAGNÓSTICO: rotas de ônibus (relações route=bus)
# ============================================================
def rotas_onibus(osm, sigla, munis_uf):
    """B4 — rotas de ônibus (relações route=bus). Confirmado utilizável em teste
    (DF, 20/07/2026: 27 relações, todas com geometria de linha). Ainda assim,
    salva sempre uma amostra de diagnóstico (útil para conferir cobertura/
    qualidade da tag 'ref'/'operator' por região) e só agrega ao wide quando a
    geometria vier como (Multi)LineString válida.
    Semântica de 'extensao_rotas_onibus_km': é a soma do comprimento de TODAS
    as linhas de ônibus que passam pelo município — ruas compartilhadas por
    várias linhas contam mais de uma vez (proxy de oferta de serviço, não é
    comprimento físico de via — não confundir com extensao_corredor_onibus_km,
    que é a faixa/pista exclusiva física)."""
    os.makedirs(DIAG_DIR, exist_ok=True)
    try:
        rotas = osm.get_data_by_custom_criteria(
            custom_filter={"route": ["bus"]},
            osm_keys_to_keep=["route"],
            keep_nodes=False, keep_ways=False, keep_relations=True,
            extra_attributes=["ref", "operator", "network", "name"],
        )
    except Exception as e:
        log(f"    [B4] !! erro: {e}")
        return None
    if rotas is None or len(rotas) == 0:
        log(f"    [B4] {sigla}: nenhuma relação route=bus retornada.")
        return None
    tipos = rotas.geometry.type.value_counts().to_dict()
    log(f"    [B4] {sigla}: {len(rotas)} relações route=bus | tipos de geometria: {tipos}")
    amostra = rotas.drop(columns="geometry").head(5).to_dict("records")
    with open(os.path.join(DIAG_DIR, f"{sigla}_amostra.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"n": len(rotas), "tipos_geometria": {str(k): int(v) for k, v in tipos.items()},
                   "amostra": amostra}, fh, ensure_ascii=False, indent=2, default=str)

    usaveis = rotas[rotas.geometry.type.isin(["LineString", "MultiLineString"])].copy()
    if usaveis.empty:
        log(f"    [B4] {sigla}: 0 relações com geometria de linha utilizável — NÃO agregado. "
            f"Amostra em {DIAG_DIR}/{sigla}_amostra.json — considerar Overpass API para este item.")
        return None
    if "id" not in usaveis.columns:
        usaveis["id"] = usaveis.index

    clip = clipa_e_mede(usaveis, munis_uf, ["ref"])
    if clip.empty:
        log(f"    [B4] {sigla}: interseção com municípios ficou vazia — nada agregado.")
        return None
    km = clip.groupby("cod_ibge")["km"].sum().reset_index(name="extensao_rotas_onibus_km")
    n = clip.groupby("cod_ibge")["id"].nunique().reset_index(name="n_rotas_onibus_osm")
    g = km.merge(n, on="cod_ibge", how="outer")
    g["extensao_rotas_onibus_km"] = g["extensao_rotas_onibus_km"].round(2)
    log(f"    [B4] {sigla}: agregado — {len(usaveis)} rotas úteis, "
        f"{int(g.n_rotas_onibus_osm.sum())} rota×município, {g.extensao_rotas_onibus_km.sum():,.0f} km somados")
    return g


# ============================================================
def processa_uf(sigla, munis_uf, pbf_path):
    from pyrosm import OSM

    bbox = list(munis_uf.total_bounds)
    log(f"  [{sigla}] bbox={[round(x, 2) for x in bbox]} | {len(munis_uf)} municípios")
    # complete_relations=True: sem isso, uma rota/relação que cruza a borda da
    # bbox vem com geometria incompleta (aviso visto no teste do DF). Custa 2
    # passadas extras só quando alguma relação de fato precisa (opt-in).
    osm = OSM(pbf_path, bounding_box=bbox, engine="out_of_core", complete_relations=True)

    resultado = None

    net = le_rede_viaria(osm)
    if net is not None:
        log(f"  [{sigla}] {len(net)} vias lidas (highway=*)")
        r = classifica_e_mede(net, munis_uf)
        if r is not None:
            resultado = r
            log(f"  [{sigla}] viário total (motorizado): {r.extensao_viaria_total_km.sum():,.0f} km | "
                f"pedestres: {r.extensao_pedestres_km.sum():,.0f} km | "
                f"corredor ônibus: {r.extensao_corredor_onibus_km.sum():,.0f} km | "
                f"ciclovia: {r.extensao_ciclovia_km.sum():,.0f} km | "
                f"ciclofaixa: {r.extensao_ciclofaixa_km.sum():,.0f} km")

    pts = le_pontos_onibus(osm, munis_uf)
    if pts is not None:
        resultado = pts if resultado is None else resultado.merge(pts, on="cod_ibge", how="outer")
        log(f"  [{sigla}] pontos de ônibus (OSM): {int(pts.n_pontos_onibus_osm.sum())}")

    term = le_terminais_onibus(osm, munis_uf)
    if term is not None:
        resultado = term if resultado is None else resultado.merge(term, on="cod_ibge", how="outer")
        log(f"  [{sigla}] terminais/estações de ônibus (OSM): {int(term.n_terminais_onibus_osm.sum())}")

    rotas = rotas_onibus(osm, sigla, munis_uf)
    if rotas is not None:
        resultado = rotas if resultado is None else resultado.merge(rotas, on="cod_ibge", how="outer")

    return resultado


def valida_municipios(codigos):
    """Validação-alvo (20/07/2026): roda o pipeline só para uma amostra
    escolhida a dedo de municípios — 5 "sabemos que TEM" sistema de ônibus
    intramunicipal e 5 "sabemos que NÃO TEM", segundo a MUNIC 2020 (já
    integrada, `munic_onibus_intramun_2020`), com porte médio/pequeno
    (evitar capitais grandes). Objetivo: medir a taxa de falso-negativo/
    falso-positivo de `presenca_onibus_osm` em n=10 casos com rótulo
    conhecido, não só no n=1 do teste do DF. Restringe munis_uf aos
    municípios selecionados (não a UF inteira) — bbox pequena, roda rápido
    mesmo tendo que baixar o .pbf regional inteiro.
    Saída: `_data/OSM/validacao_10_municipios/{sigla}.csv` (não mistura com
    `por_uf/`, que é o cache retomável da rodada país inteiro) + relatório
    `_data/OSM/validacao_10_municipios/relatorio.csv` comparando MUNIC ×
    OSM município a município."""
    val_dir = os.path.join(OSM_DIR, "validacao_10_municipios")
    os.makedirs(val_dir, exist_ok=True)
    munis = carrega_municipios()
    codigos = [str(c).zfill(7) for c in codigos]
    sel = munis[munis.cod_ibge.isin(codigos)]
    faltando = set(codigos) - set(sel.cod_ibge)
    if faltando:
        log(f"!! cod_ibge não encontrados na malha municipal: {sorted(faltando)}")
    if sel.empty:
        sys.exit("Nenhum município válido em --municipios.")

    resultados = []
    for sigla, grupo in sel.groupby("sigla_uf"):
        regiao = UF_REGIAO[sigla]
        log(f"\n=== validação: {sigla} ({len(grupo)} município(s), região {regiao}) ===")
        out_csv = os.path.join(val_dir, f"{sigla}.csv")
        if os.path.exists(out_csv):
            log(f"[{sigla}] já processado nesta validação — pulando ({out_csv})")
            resultados.append(pd.read_csv(out_csv, dtype={"cod_ibge": str}))
            continue
        pbf = baixa_pbf(regiao)
        g = processa_uf(sigla, grupo, pbf)
        if g is not None:
            g.to_csv(out_csv, index=False)
            resultados.append(g)
        else:
            log(f"  !! {sigla}: nada extraído.")

    if not resultados:
        log("Nada extraído na validação."); return
    todos = pd.concat(resultados, ignore_index=True)
    todos = _computa_presenca_onibus(todos)
    todos = todos.merge(munis[["cod_ibge", "nome_mun", "sigla_uf"]], on="cod_ibge", how="left")

    munic_path = os.path.join(OUT, "munic_transporte_2020.csv")
    munic = pd.read_csv(munic_path, dtype={"cod_ibge": str})
    munic["cod_ibge"] = munic["cod_ibge"].astype(str).str.zfill(7)
    rel = todos.merge(munic[["cod_ibge", "munic_onibus_intramun_2020"]], on="cod_ibge", how="left")
    rel["rotulo_esperado"] = rel["munic_onibus_intramun_2020"].map({1: "TEM", 0: "NÃO TEM"})
    rel["osm_disse"] = rel["presenca_onibus_osm"].map({1: "presença", 0: "sem sinal"})
    rel["acerto"] = (
        ((rel.munic_onibus_intramun_2020 == 1) & (rel.presenca_onibus_osm == 1))
        | ((rel.munic_onibus_intramun_2020 == 0) & (rel.presenca_onibus_osm == 0))
    )
    cols_rel = ["cod_ibge", "nome_mun", "sigla_uf", "rotulo_esperado", "osm_disse", "acerto",
                "n_pontos_onibus_osm", "n_terminais_onibus_osm", "n_rotas_onibus_osm",
                "extensao_corredor_onibus_km", "sinais_onibus_osm"]
    cols_rel = [c for c in cols_rel if c in rel.columns]
    rel_out = rel[cols_rel].sort_values(["rotulo_esperado", "nome_mun"])
    rel_out.to_csv(os.path.join(val_dir, "relatorio.csv"), index=False)
    log("\n=== RELATÓRIO — validação em 10 municípios (rótulo MUNIC 2020 x presença de ônibus OSM) ===")
    log(rel_out.to_string(index=False))
    log("Nota: 'acerto' aqui testa se presenca_onibus_osm discrimina sistema MUNICIPAL organizado "
        "(rótulo MUNIC) — teste de 20/07/2026 deu 0% falso-negativo e 100% falso-positivo: a "
        "variável não separa os grupos. Ver decisão/ressalva no cabeçalho do script antes de usar.")
    n_tem = (rel.munic_onibus_intramun_2020 == 1).sum()
    n_nao = (rel.munic_onibus_intramun_2020 == 0).sum()
    fn = ((rel.munic_onibus_intramun_2020 == 1) & (rel.presenca_onibus_osm == 0)).sum()
    fp = ((rel.munic_onibus_intramun_2020 == 0) & (rel.presenca_onibus_osm == 1)).sum()
    if n_tem:
        log(f"Falso-negativo (MUNIC=TEM, OSM=sem sinal): {fn}/{n_tem} ({fn/n_tem*100:.0f}%)")
    if n_nao:
        log(f"Falso-positivo (MUNIC=NÃO TEM, OSM=presença): {fp}/{n_nao} ({fp/n_nao*100:.0f}%)")
    log(f"Relatório salvo em {os.path.join(val_dir, 'relatorio.csv')}")


def _computa_presenca_onibus(todos):
    """'presenca_onibus_osm' (antes chamada indicio_onibus_osm): há QUALQUER
    infraestrutura/linha de ônibus mapeada no OSM dentro do território do
    município. NÃO é indício de sistema municipal organizado — teste de
    20/07/2026 em 10 municípios (5 confirmados com sistema, 5 sem, via MUNIC
    2020) deu 100% falso-positivo. Ver ressalva completa no cabeçalho do
    script antes de usar esta variável em qualquer análise."""
    for c in ["n_pontos_onibus_osm", "n_terminais_onibus_osm", "n_rotas_onibus_osm", "extensao_corredor_onibus_km"]:
        if c not in todos.columns:
            todos[c] = 0
    todos = todos.fillna({c: 0 for c in ["n_pontos_onibus_osm", "n_terminais_onibus_osm",
                                          "n_rotas_onibus_osm", "extensao_corredor_onibus_km"]})
    todos["sinais_onibus_osm"] = (
        (todos["n_pontos_onibus_osm"] > 0).astype(int)
        + (todos["n_terminais_onibus_osm"] > 0).astype(int)
        + (todos["n_rotas_onibus_osm"] > 0).astype(int)
        + (todos["extensao_corredor_onibus_km"] > 0).astype(int)
    )
    todos["presenca_onibus_osm"] = (todos["sinais_onibus_osm"] > 0).astype(int)
    return todos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uf", nargs="+", help="processar só estas siglas de UF (teste). Ex.: --uf DF")
    ap.add_argument("--municipios", nargs="+",
                     help="rodar só para estes cod_ibge (7 dígitos) — validação pontual, "
                          "não mexe no cache retomável de --uf/rodada completa. "
                          "Ex.: --municipios 3550308 4106902")
    args = ap.parse_args()

    if args.municipios:
        valida_municipios(args.municipios)
        return

    os.makedirs(POR_UF_DIR, exist_ok=True)
    munis = carrega_municipios()

    ufs = [u.upper() for u in args.uf] if args.uf else ORDEM_UF
    invalid = [u for u in ufs if u not in UF_REGIAO]
    if invalid:
        sys.exit(f"UF(s) inválida(s): {invalid}.")

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
                log(f"  !! nenhum município para UF={sigla} — confira SIGLA_UF."); continue
            g = processa_uf(sigla, munis_uf, pbf)
            if g is not None:
                g.to_csv(out_csv, index=False)
            else:
                log(f"  !! {sigla}: nada extraído.")
        except Exception as e:
            log(f"  !! ERRO em {sigla}: {e} — pulando (rode de novo depois).")
            import traceback; traceback.print_exc()
            continue

    log(f"\n--- concluído em {(time.time()-t0)/60:.1f} min | consolidando por UF ---")
    arqs = [os.path.join(POR_UF_DIR, f) for f in os.listdir(POR_UF_DIR) if f.endswith(".csv")]
    if not arqs:
        log("Nada a consolidar ainda."); return
    todos = pd.concat([pd.read_csv(a, dtype={"cod_ibge": str}) for a in arqs], ignore_index=True)

    # --- presença de ônibus no território (ver ressalva no cabeçalho: teste
    # de 10 municípios de 20/07/2026 mostrou que NÃO discrimina sistema
    # municipal organizado — 100% falso-positivo. Manter só como "há alguma
    # infraestrutura/linha de ônibus mapeada", não como indício de sistema.
    # Ausência de sinal também não prova ausência: é presença/ausência de
    # MAPEAMENTO, não necessariamente do serviço.) ---
    todos = _computa_presenca_onibus(todos)

    todos.to_csv(os.path.join(OUT, "osm_viario_onibus_ciclo.csv"), index=False)
    log(f"osm_viario_onibus_ciclo.csv: {len(todos)} municípios | "
        f"com presença de ônibus no território (qualquer sinal): {int(todos.presenca_onibus_osm.sum())}")

    # --- comparação com a MUNIC 2020 (institucional, 5.570 municípios) —
    # NÃO é validação de acurácia (já sabemos, pelo teste de 10 municípios,
    # que os construtos divergem: MUNIC pergunta por sistema PRÓPRIO/
    # concessão municipal; presenca_onibus_osm capta ônibus de QUALQUER
    # natureza no território). Mantido só como registro descritivo. ---
    munic_path = os.path.join(OUT, "munic_transporte_2020.csv")
    if os.path.exists(munic_path):
        munic = pd.read_csv(munic_path, dtype={"cod_ibge": str})
        munic["cod_ibge"] = munic["cod_ibge"].astype(str).str.zfill(7)
        cmp = todos.merge(munic[["cod_ibge", "munic_onibus_intramun_2020"]], on="cod_ibge", how="left")
        cmp = cmp.dropna(subset=["munic_onibus_intramun_2020"])
        if not cmp.empty:
            ct = pd.crosstab(cmp["munic_onibus_intramun_2020"].map({1: "MUNIC=Sim", 0: "MUNIC=Não"}),
                              cmp["presenca_onibus_osm"].map({1: "OSM=presença", 0: "OSM=sem sinal"}))
            log("\nComparação (não é teste de acurácia — ver ressalva) — presença OSM de ônibus "
                "× MUNIC 2020 (município tem ônibus intramunicipal?):")
            log(ct.to_string())
            falsos_neg = cmp[(cmp.munic_onibus_intramun_2020 == 1) & (cmp.presenca_onibus_osm == 0)]
            if len(cmp[cmp.munic_onibus_intramun_2020 == 1]) > 0:
                taxa_fn = len(falsos_neg) / len(cmp[cmp.munic_onibus_intramun_2020 == 1]) * 100
                log(f"Taxa de falso-negativo do OSM (MUNIC diz Sim, OSM não achou nada): {taxa_fn:.1f}%")

    if not os.path.exists(BASE_CSV):
        log(f"AVISO: {BASE_CSV} não encontrado — integração ao wide pulada."); return
    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].astype(str).str.zfill(7)
    novas_cols = [c for c in todos.columns if c != "cod_ibge"]
    base = base.drop(columns=[c for c in novas_cols if c in base.columns])
    base = base.merge(todos, on="cod_ibge", how="left")
    if "area_km2" in base.columns and "extensao_viaria_total_km" in base.columns:
        area = pd.to_numeric(base["area_km2"], errors="coerce")
        base["densidade_viaria_km_km2"] = (base["extensao_viaria_total_km"] / area).round(3)
    base.to_csv(BASE_CSV, index=False)
    log(f"OK — base_municipal_v3.csv atualizado: {base.shape[0]} x {base.shape[1]}")


if __name__ == "__main__":
    main()
