#!/usr/bin/env python3
"""calcular_densidade_viaria_urbana.py — densidade viária URBANA de verdade
(km de viário DENTRO da mancha urbana / km² de área urbanizada), não o proxy
grosseiro que já tínhamos (`densidade_viaria_km_km2` = viário do município
INTEIRO / área total do município, que mistura estrada rural com malha
urbana e infla municípios grandes com mancha urbana pequena — comum no
Norte/interior).

MÉTODO:
  1) Baixa (uma vez, ~nacional) o shapefile "Áreas Urbanizadas do Brasil
     2019" do IBGE (geoftp.ibge.gov.br) — geometria da mancha urbana,
     não a estatística de área que já tínhamos integrada
     (`total_de_areas_urbanizadas_km2_2019`, essa é tabular, não dá pra
     recortar nada com ela).
  2) Reaproveita os extratos regionais do OSM (Geofabrik, .pbf) já baixados
     em `_data/OSM/` pelo `calcular_osm_viario_onibus_ciclo.py` — não baixa
     de novo.
  3) Por UF: lê o viário (mesma função `le_rede_viaria`), filtra só as
     classes motorizadas (mesmo `CLASSE_VIARIA` — consistente com
     `extensao_viaria_total_km`), recorta (`gpd.clip`) pela mancha urbana
     da UF e DEPOIS intersecta com os polígonos municipais (mesma
     `clipa_e_mede`) para atribuir cod_ibge. Ou seja: só conta o pedaço de
     via que está dentro da mancha urbada E dentro do município.
  4) Gera `extensao_viaria_urbana_km` (+ quebra por classe) e
     `densidade_viaria_urbana_km_km2` = extensao_viaria_urbana_km /
     total_de_areas_urbanizadas_km2_2019 (já integrada).

⚠️ RESSALVA (descompasso temporal): a mancha urbana é do mapeamento IBGE de
2019; o viário OSM reflete o mapeamento colaborativo atual (~2026). A
próxima edição de "Áreas Urbanizadas do Brasil" estava prevista para 2025,
foi adiada para 2026 e ainda não foi publicada (checado em 22/07/2026) — 2019
é a mais atual disponível. Bairros/vias novas fora da mancha de 2019 ficam
de fora do numerador — a densidade urbana calculada aqui é, se algo, uma
SUBESTIMATIVA para municípios com expansão urbana recente e acelerada.

Reaproveita funções de `calcular_osm_viario_onibus_ciclo.py` (mesma pasta):
CLASSE_VIARIA, comprimento_km, clipa_e_mede, le_rede_viaria,
carrega_municipios, baixa_pbf, UF_REGIAO, ORDEM_UF.

⚠️ TAREFA PESADA (novo download de rede + reprocessamento de todo o viário).
Testar primeiro com uma UF pequena:
    python calcular_densidade_viaria_urbana.py --uf DF
Depois, para rodar tudo (retomável — pode interromper e retomar):
    python calcular_densidade_viaria_urbana.py

⚠️ SP TRAVANDO (27/07/2026): rodar `--uf SP` de uma vez só vem falhando
(memória/tempo) — SP tem, de longe, o maior volume de viário + maior mancha
urbana do país, e o processamento de uma UF inteira roda em UMA bbox só
(`munis_uf.total_bounds`), sem dividir o trabalho. Adicionado o modo
`--lotes N`: divide a UF em N lotes geográficos menores e contíguos (grade
por latitude, em zigue-zague — não é divisão administrativa, é só um recorte
espacial para reduzir bbox/memória por rodada), processa e cacheia cada lote
separadamente (retomável lote a lote, não só UF a UF) e consolida no final em
`urbano_por_uf/SP.csv` (mesmo formato de sempre, sem mudar o resto do
pipeline). Uso recomendado para SP:
    python calcular_densidade_viaria_urbana.py --uf SP --lotes 8
Se travar/faltar memória mesmo assim, pode interromper (Ctrl+C) e rodar de
novo — os lotes já salvos em `urbano_por_uf/_lotes_SP/` não são reprocessados.
Ajustar N para cima (mais lotes menores) se ainda faltar memória.

REQUISITOS: mesmo ambiente conda "osm" já usado no script de viário/ônibus/
ciclovia (pyrosm, geopandas, shapely, pyproj).
"""
import argparse, os, sys, time, urllib.request
import numpy as np
import pandas as pd
import geopandas as gpd
import warnings
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from calcular_osm_viario_onibus_ciclo import (  # noqa: E402
    CLASSE_VIARIA, comprimento_km, clipa_e_mede, le_rede_viaria,
    carrega_municipios, baixa_pbf, UF_REGIAO, ORDEM_UF, log, V, OUT, BASE_CSV,
)

OSM_DIR = os.path.join(V, "OSM")
URBANO_DIR = os.path.join(V, "espacial", "areas_urbanizadas_2019")
URBANO_POR_UF_DIR = os.path.join(OSM_DIR, "urbano_por_uf")

# Não é um .zip único — o geoftp do IBGE serve os componentes soltos do
# shapefile (conferido em 22/07/2026 via listagem do diretório). Nome do
# arquivo é "AU_2022_..." (revisão/republicação de 2022), mas o conteúdo/ano
# de referência do mapeamento continua sendo 2019.
IBGE_URBANO_BASE_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/tipologias_do_territorio/"
    "areas_urbanizadas_do_brasil/2019/Shapefile/AreasUrbanizadas2019_Brasil/"
)
IBGE_URBANO_NOME_BASE = "AU_2022_AreasUrbanizadas2019_Brasil"
IBGE_URBANO_EXTENSOES = ["shp", "shx", "dbf", "prj", "cpg"]


def baixa_areas_urbanizadas():
    """Baixa (uma vez) os componentes do shapefile nacional de área
    urbanizada 2019 (IBGE, republicado em 2022 — mesmo conteúdo/ano de
    referência). Retomável: se já existe um .shp na pasta, não baixa de novo."""
    os.makedirs(URBANO_DIR, exist_ok=True)
    shp_path = os.path.join(URBANO_DIR, f"{IBGE_URBANO_NOME_BASE}.shp")
    if os.path.exists(shp_path) and os.path.getsize(shp_path) > 1_000_000:
        return shp_path
    for ext in IBGE_URBANO_EXTENSOES:
        url = f"{IBGE_URBANO_BASE_URL}{IBGE_URBANO_NOME_BASE}.{ext}"
        dest = os.path.join(URBANO_DIR, f"{IBGE_URBANO_NOME_BASE}.{ext}")
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            continue
        log(f"baixando {url} -> {dest} (pode demorar — .dbf tem ~37MB, .shp ~55MB)...")
        urllib.request.urlretrieve(url, dest)
        log(f"  ok ({os.path.getsize(dest)/1e6:.1f} MB)")
    if not os.path.exists(shp_path):
        sys.exit("!! .shp não apareceu depois do download. Confira a URL/nome do arquivo no geoftp do IBGE.")
    return shp_path


def carrega_areas_urbanizadas():
    shp = baixa_areas_urbanizadas()
    log(f"lendo mancha urbana: {shp}")
    g = gpd.read_file(shp)
    g = g.to_crs(4326)
    log(f"  {len(g)} polígonos de área urbanizada, CRS convertido para EPSG:4326")
    return g[["geometry"]]


def classifica_urbano(net, munis_uf, urbano_uf):
    """Filtra o viário motorizado, recorta pela mancha urbana (gpd.clip) e só
    DEPOIS intersecta com os municípios (clipa_e_mede) para atribuir
    cod_ibge — ou seja, só sobra o pedaço de via dentro da mancha urbana E
    dentro do município."""
    if net is None or len(net) == 0 or urbano_uf.empty:
        return None
    net = net.set_crs(4326) if net.crs is None else net.to_crs(4326)
    net_motor = net[net["highway"].isin(CLASSE_VIARIA.keys())].copy()
    if net_motor.empty:
        return None
    net_motor["classe_viaria"] = net_motor["highway"].map(CLASSE_VIARIA)

    try:
        mascara = urbano_uf.union_all()
    except AttributeError:
        mascara = urbano_uf.unary_union
    if mascara.is_empty:
        return None

    urbano_viario = gpd.clip(net_motor[["id", "geometry", "highway", "classe_viaria"]], mascara)
    urbano_viario = urbano_viario[urbano_viario.geometry.type.isin(["LineString", "MultiLineString"])]
    if urbano_viario.empty:
        return None

    clip = clipa_e_mede(urbano_viario, munis_uf, ["classe_viaria"])
    if clip.empty:
        return None

    g = clip.groupby("cod_ibge")["km"].sum().reset_index(name="extensao_viaria_urbana_km")
    for classe in ["estrutural", "coletora", "local"]:
        sub = clip[clip.classe_viaria == classe].groupby("cod_ibge")["km"].sum().reset_index(
            name=f"extensao_viaria_urbana_{classe}_km")
        g = g.merge(sub, on="cod_ibge", how="left")
    for c in g.columns:
        if c != "cod_ibge":
            g[c] = g[c].fillna(0).round(2)
    return g


def divide_em_lotes(munis_uf, n_lotes):
    """Divide os municípios de uma UF em N lotes geograficamente compactos e
    contíguos (não é divisão administrativa — a malha `BR_Municipios_2022.shp`
    só tem CD_MUN/NM_MUN/SIGLA_UF/AREA_KM2, sem mesorregião/RGI — checado
    27/07/2026). Método: grade por faixas de latitude (nº de faixas ~
    proporcional à razão altura/largura da bbox da UF, para faixas nem muito
    finas nem muito largas), com ordenação em zigue-zague (boustrophedon)
    dentro de cada faixa — mantém cada lote como um bloco geográfico contíguo
    (bbox pequena), em vez de espalhado pela UF inteira. Só reduz a CARGA por
    rodada (bbox menor = menos viário OSM + menos polígonos de área
    urbanizada para cruzar de uma vez); não muda o resultado final, que é
    consolidado por soma depois."""
    g = munis_uf.copy()
    cent = g.geometry.centroid
    g["_cx"], g["_cy"] = cent.x, cent.y
    minx, miny, maxx, maxy = g.total_bounds
    largura, altura = (maxx - minx) or 1e-6, (maxy - miny) or 1e-6
    linhas = int(round((n_lotes * altura / largura) ** 0.5)) or 1
    linhas = max(1, min(linhas, n_lotes))
    g["_faixa"] = pd.cut(g["_cy"], bins=linhas, labels=False, duplicates="drop")
    partes = []
    for faixa_id, grupo in g.groupby("_faixa"):
        partes.append(grupo.sort_values("_cx", ascending=(faixa_id % 2 == 0)))
    ordenado = pd.concat(partes) if partes else g
    lotes_idx = np.array_split(np.arange(len(ordenado)), n_lotes)
    labels = np.empty(len(ordenado), dtype=int)
    for i, idx in enumerate(lotes_idx):
        labels[idx] = i
    ordenado = ordenado.drop(columns=["_cx", "_cy", "_faixa"])
    ordenado["_lote"] = labels
    return ordenado


def processa_uf_urbano_em_lotes(sigla, munis_uf, pbf_path, urbano, n_lotes):
    """Como `processa_uf_urbano`, mas dividindo a UF em N lotes geográficos
    menores (ver `divide_em_lotes`) — cada lote é processado com sua própria
    bbox (bem menor que a UF inteira) e cacheado separadamente em
    `urbano_por_uf/_lotes_{sigla}/`, retomável lote a lote. Ao final, soma os
    lotes num único resultado por município (não deveria haver duplicata
    entre lotes, já que a divisão é por município inteiro, não por recorte de
    geometria — mas o `groupby().sum()` protege mesmo assim)."""
    lote_dir = os.path.join(URBANO_POR_UF_DIR, f"_lotes_{sigla}")
    os.makedirs(lote_dir, exist_ok=True)
    munis_lotes = divide_em_lotes(munis_uf, n_lotes)
    partes = []
    for lote_id in range(n_lotes):
        grupo = munis_lotes[munis_lotes["_lote"] == lote_id].drop(columns=["_lote"])
        if grupo.empty:
            continue
        lote_csv = os.path.join(lote_dir, f"{sigla}__lote{lote_id+1:02d}_de_{n_lotes}.csv")
        if os.path.exists(lote_csv):
            log(f"  [{sigla}] lote {lote_id+1}/{n_lotes} já processado — pulando ({lote_csv})")
            partes.append(pd.read_csv(lote_csv, dtype={"cod_ibge": str}))
            continue
        log(f"  [{sigla}] lote {lote_id+1}/{n_lotes} — {len(grupo)} município(s)")
        try:
            g = processa_uf_urbano(f"{sigla}-L{lote_id+1:02d}", grupo, pbf_path, urbano)
        except Exception as e:
            log(f"  !! ERRO no lote {lote_id+1}/{n_lotes} de {sigla}: {e} — pulando este lote "
                f"(rode o script de novo depois; os demais lotes já salvos não são reprocessados).")
            import traceback; traceback.print_exc()
            continue
        if g is not None:
            g.to_csv(lote_csv, index=False)
            partes.append(g)
        else:
            pd.DataFrame(columns=["cod_ibge", "extensao_viaria_urbana_km"]).to_csv(lote_csv, index=False)
    if not partes:
        return None
    todos = pd.concat(partes, ignore_index=True)
    todos["cod_ibge"] = todos["cod_ibge"].astype(str).str.zfill(7)
    return todos.groupby("cod_ibge", as_index=False).sum(numeric_only=True)


def processa_uf_urbano(sigla, munis_uf, pbf_path, urbano):
    from pyrosm import OSM

    bbox = list(munis_uf.total_bounds)
    log(f"  [{sigla}] bbox={[round(x, 2) for x in bbox]} | {len(munis_uf)} municípios")
    osm = OSM(pbf_path, bounding_box=bbox, engine="out_of_core")
    net = le_rede_viaria(osm)
    if net is None or len(net) == 0:
        log(f"  [{sigla}] nenhuma via lida.")
        return None

    # pré-filtro espacial (bbox) da mancha urbana antes do clip fino — evita
    # rodar o clip contra o shapefile nacional inteiro a cada UF.
    minx, miny, maxx, maxy = bbox
    urbano_uf = urbano.cx[minx:maxx, miny:maxy]
    if urbano_uf.empty:
        log(f"  [{sigla}] nenhum polígono de área urbanizada nesta bbox — 0 km urbano.")
        return None

    g = classifica_urbano(net, munis_uf, urbano_uf)
    if g is not None:
        log(f"  [{sigla}] viário urbano: {g.extensao_viaria_urbana_km.sum():,.0f} km "
            f"({len(g)} municípios com via na mancha urbana)")
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uf", nargs="+", help="processar só estas siglas de UF (teste). Ex.: --uf DF")
    ap.add_argument("--lotes", type=int, default=None,
                     help="dividir a(s) UF(s) processada(s) em N lotes geográficos menores, "
                          "retomável lote a lote — usar para UFs muito pesadas (SP) que travam "
                          "de uma vez só. Ex.: --uf SP --lotes 8")
    args = ap.parse_args()

    os.makedirs(URBANO_POR_UF_DIR, exist_ok=True)
    munis = carrega_municipios()
    urbano = carrega_areas_urbanizadas()

    ufs = [u.upper() for u in args.uf] if args.uf else ORDEM_UF
    invalid = [u for u in ufs if u not in UF_REGIAO]
    if invalid:
        sys.exit(f"UF(s) inválida(s): {invalid}.")

    t0 = time.time()
    for sigla in ufs:
        out_csv = os.path.join(URBANO_POR_UF_DIR, f"{sigla}.csv")
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
            if args.lotes and args.lotes > 1:
                g = processa_uf_urbano_em_lotes(sigla, munis_uf, pbf, urbano, args.lotes)
            else:
                g = processa_uf_urbano(sigla, munis_uf, pbf, urbano)
            if g is not None:
                g.to_csv(out_csv, index=False)
            else:
                log(f"  !! {sigla}: nada extraído (salvando csv vazio p/ não reprocessar).")
                pd.DataFrame(columns=["cod_ibge", "extensao_viaria_urbana_km"]).to_csv(out_csv, index=False)
        except Exception as e:
            log(f"  !! ERRO em {sigla}: {e} — pulando (rode de novo depois).")
            import traceback; traceback.print_exc()
            continue

    log(f"\n--- concluído em {(time.time()-t0)/60:.1f} min | consolidando por UF ---")
    arqs = [os.path.join(URBANO_POR_UF_DIR, f) for f in os.listdir(URBANO_POR_UF_DIR) if f.endswith(".csv")]
    if not arqs:
        log("Nada a consolidar ainda."); return
    todos = pd.concat([pd.read_csv(a, dtype={"cod_ibge": str}) for a in arqs if os.path.getsize(a) > 0],
                       ignore_index=True)
    if todos.empty or "cod_ibge" not in todos.columns:
        log("Nenhum dado urbano extraído ainda (rodadas vazias)."); return
    todos["cod_ibge"] = todos["cod_ibge"].astype(str).str.zfill(7)
    todos = todos.groupby("cod_ibge", as_index=False).sum(numeric_only=True)  # por segurança, se UF duplicar município

    if not os.path.exists(BASE_CSV):
        log(f"AVISO: {BASE_CSV} não encontrado — integração ao wide pulada."); return
    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].astype(str).str.zfill(7)
    novas_cols = [c for c in todos.columns if c != "cod_ibge"]
    base = base.drop(columns=[c for c in novas_cols if c in base.columns])
    base = base.merge(todos, on="cod_ibge", how="left")
    for c in novas_cols:
        base[c] = base[c].fillna(0)

    if "total_de_areas_urbanizadas_km2_2019" in base.columns:
        area_urb = pd.to_numeric(base["total_de_areas_urbanizadas_km2_2019"], errors="coerce")
        base["densidade_viaria_urbana_km_km2"] = (base["extensao_viaria_urbana_km"] / area_urb).round(3)
        # onde a área urbanizada é 0/NaN mas há viário urbano medido (raro — mancha
        # pequena demais para o polígono do IBGE 2019 captar), deixar NaN em vez de
        # inf/erro: sinaliza para conferência manual, não descarta o numerador.
    else:
        log("AVISO: total_de_areas_urbanizadas_km2_2019 não encontrada — densidade_viaria_urbana_km_km2 não calculada.")

    base.to_csv(BASE_CSV, index=False)
    log(f"OK — base_municipal_v3.csv atualizado: {base.shape[0]} x {base.shape[1]}")
    log(f"extensao_viaria_urbana_km: soma={base['extensao_viaria_urbana_km'].sum():,.0f} km | "
        f"municípios com >0: {(base['extensao_viaria_urbana_km']>0).sum()}/{len(base)}")


if __name__ == "__main__":
    main()
