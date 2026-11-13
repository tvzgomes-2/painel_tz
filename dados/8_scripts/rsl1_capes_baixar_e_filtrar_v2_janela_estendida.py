#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSL1 — CAPES: baixa e filtra os XLSX do Catálogo de Teses e Dissertações,
com DESCOBERTA DINÂMICA de recursos via CKAN — v2, janela estendida
(decisão do autor, 11/09/2026: estender a 1987-2020, além dos 2021-2024
já baixados e triados na v1).

Por que esta v2 existe, e por que ela NÃO hardcoda os anos novos:
  A v1 (`rsl1_capes_baixar_e_filtrar.py`) hardcoda 4 URLs de XLSX
  (2021-2024), confirmadas manualmente via CKAN `package_show` em
  09-09-2026. Eu (Claude) não consigo hoje confirmar da mesma forma se
  os anos 2013-2020 (e o legado 1987-2012) estão no MESMO pacote CKAN,
  em pacote(s) separado(s), ou se existem como XLSX de todo — o domínio
  `dadosabertos.capes.gov.br` está fora da lista liberada no proxy da
  sessão na nuvem (bloqueado, 403) e o `device_bash` nesta máquina está
  fora do ar desde a atualização do Windows de 08/09/2026 (falha de
  montagem). Hardcodar URLs adivinhadas seria exatamente o tipo de
  "conceito tomado como dado" que a calibragem deste cofre (Becker)
  manda evitar. Em vez disso, esta v2 DESCOBRE os recursos em tempo de
  execução, na sua máquina, quando você rodar — e informa com clareza
  o que encontrou e o que não encontrou, antes de baixar qualquer coisa.

Patch de 12/09/2026 (pós-download do legado 1987-2012): o layout legado do
CAPES usa nomes de coluna em PascalCase (`TituloTese`, `ResumoTese`,
`PalavrasChave`, `NomePrograma`, `NomeIes`, `Autor`, `Orientador_1`,
`DataDefesa`, `URLTextoCompleto`, `Nivel`, `GrandeAreaDescricao`,
`AreaConhecimento`), diferente do layout moderno (2013+, prefixos
`NM_`/`DS_`) que a v2 original hardcodava. Confirmado nos 26 anos
1987-2012 via `diagnostico_headers_capes_legado.py` (cabeçalho idêntico e
completo — 41 colunas — em todos eles; não é corrupção pontual, é um
segundo formato de exportação, constante). `ALIASES_CABECALHO` abaixo
mapeia cada campo esperado para a lista de nomes possíveis (moderno
primeiro, legado depois); três campos não têm equivalente no layout
legado (`DS_ABSTRACT`, `DS_KEYWORD` — sem resumo em inglês separado nos
anos legados; `ID_PRODUCAO_INTELECTUAL` — sem id único) e são tratados
como ausência esperada, não erro — ver `CAMPOS_SEM_EQUIVALENTE_LEGADO`.
Evidência bruta em `diagnostico_headers_capes_legado.txt`, na mesma pasta.

O que mudou da v1:
  1. RECURSOS deixa de ser uma lista fixa. `descobrir_recursos()` consulta
     a API CKAN (`package_show`, e se necessário `package_search`) e monta
     a lista de anos disponíveis a partir do padrão de nome
     `br-capes-btd-<ano>` nos recursos retornados — no MESMO pacote da v1
     por padrão, e em pacotes adicionais informados por --package-id ou
     encontrados por --buscar-pacotes.
  2. Novo modo `--listar`: só descobre e imprime o que existe (ano, pacote,
     URL, tamanho se disponível) e para — sem baixar nada. RODE ISTO
     PRIMEIRO, sempre, antes de --so-baixar ou execução completa.
  3. Tamanho esperado deixa de ser obrigatório: se o CKAN não informar
     `size` para um recurso, o script tenta HEAD request (Content-Length)
     e, se isso também falhar, baixa sem verificação estrita de tamanho
     (avisando claramente no log e no CSV de execução) — em vez de crashar
     ou de inventar um número.
  4. Se a descoberta via API falhar (rede, mudança de endpoint, etc.), o
     script cai de volta para os 4 recursos fixos da v1 (2021-2024) — nunca
     fica pior do que a v1 já era, só não estende a janela naquele caso.
  5. Todo o resto (padrões de busca Blocos A-E, filtro local via openpyxl,
     formato dos dois CSVs de saída, retomada idempotente de download) é
     IDÊNTICO à v1 — copiado verbatim. Isto não é uma reescrita: é a v1
     mais a camada de descoberta que faltava para a janela estendida.

Uso:
    pip install openpyxl

    # 1) SEMPRE primeiro — só olha o que existe, não baixa nada:
    python rsl1_capes_baixar_e_filtrar_v2_janela_estendida.py --listar

    # 2) Depois de conferir a lista, baixar e filtrar o que quiser:
    python rsl1_capes_baixar_e_filtrar_v2_janela_estendida.py \\
        --dest "C:\\...\\doutorado\\03 - Dados\\_data\\CAPES" \\
        --out  "C:\\...\\doutorado\\06 - Acadêmico\\...\\RSL..." \\
        --anos 2013 2014 2015 2016 2017 2018 2019 2020

  --dest            pasta onde os XLSX brutos ficam salvos (mesma da v1).
  --out             pasta onde os dois CSVs de resultado são salvos.
  --anos            subconjunto de anos a processar (default: todos os
                     descobertos). Ex.: --anos 2013 2014
  --so-baixar       baixa e para, não filtra.
  --so-filtrar      pula o download, assume que os XLSX já estão em --dest
                     (precisa que --listar/execução anterior já tenha
                     resolvido os nomes de arquivo — ver --listar).
  --listar          só descobre e imprime os recursos disponíveis; não
                     baixa nem filtra nada. Roda primeiro, sempre.
  --package-id ID   pacote(s) CKAN adicionais a consultar, além do pacote
                     padrão da v1 (dbb9b83e-7779-4b99-89d2-1ff8099f36f6).
                     Pode repetir a flag.
  --buscar-pacotes  além do(s) pacote(s) acima, tenta `package_search` por
                     termos como "capes-btd" e "teses e dissertacoes" para
                     achar outros pacotes que possam conter o legado
                     1987-2012 (não confirmado que exista como XLSX aberto
                     — este modo só reporta o que a API devolver).

Ambos os CSVs de saída são candidatos A TRIAR — nenhum entra em
`corpus_rsl.csv` sem leitura e sem passar pelos filtros 1 e 2 do protocolo.
"""

import argparse
import csv
import io
import json
import os
import re
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date

# ---------------------------------------------------------------------------
# 1. Descoberta dinâmica de recursos via CKAN (substitui a lista fixa da v1)
# ---------------------------------------------------------------------------

CKAN_BASE = "https://dadosabertos.capes.gov.br/api/3/action"
PACKAGE_ID_PADRAO = "dbb9b83e-7779-4b99-89d2-1ff8099f36f6"  # confirmado em 09-09-2026, cobre ao menos 2021-2024
# Ampliado em 12/09/2026: o pacote legado 1987-2012 usa o nome
# "CAPES-BTD-<ano>-2019-11-01" (sem o prefixo "br-"), diagnosticado via
# --dump-recursos depois que a v1 deste regex reportava "0 anos reconhecidos"
# nesse pacote (falso negativo, nao pacote vazio). O "(?:br-)?" torna o
# prefixo opcional sem deixar de casar o padrao antigo.
PADRAO_NOME_ANO = re.compile(r"(?:br-)?capes-btd-(\d{4})", re.IGNORECASE)

# Fallback fixo — EXATAMENTE os 4 recursos da v1, para o caso de a API de
# descoberta falhar por qualquer razão (rede indisponível, endpoint mudou).
RECURSOS_FALLBACK_V1 = [
    {
        "ano": 2021, "pacote": PACKAGE_ID_PADRAO,
        "url": "https://dadosabertos.capes.gov.br/dataset/dbb9b83e-7779-4b99-89d2-1ff8099f36f6/resource/1dfdb53a-543d-4834-97e2-27df8cb8d83a/download/br-capes-btd-2021-2025-03-31.xlsx",
        "arquivo": "br-capes-btd-2021-2025-03-31.xlsx", "tamanho_esperado": 152425037,
    },
    {
        "ano": 2022, "pacote": PACKAGE_ID_PADRAO,
        "url": "https://dadosabertos.capes.gov.br/dataset/dbb9b83e-7779-4b99-89d2-1ff8099f36f6/resource/5aabb7a7-33ab-47b2-8b24-3e6765102f02/download/br-capes-btd-2022-2025-03-31.xlsx",
        "arquivo": "br-capes-btd-2022-2025-03-31.xlsx", "tamanho_esperado": 155092109,
    },
    {
        "ano": 2023, "pacote": PACKAGE_ID_PADRAO,
        "url": "https://dadosabertos.capes.gov.br/dataset/dbb9b83e-7779-4b99-89d2-1ff8099f36f6/resource/bb0e4a57-ea99-49e1-a859-36391f541797/download/br-capes-btd-2023-2025-03-31.xlsx",
        "arquivo": "br-capes-btd-2023-2025-03-31.xlsx", "tamanho_esperado": 168690508,
    },
    {
        "ano": 2024, "pacote": PACKAGE_ID_PADRAO,
        "url": "https://dadosabertos.capes.gov.br/dataset/dbb9b83e-7779-4b99-89d2-1ff8099f36f6/resource/4af59c52-78b3-450a-9167-bbc8b6c17808/download/br-capes-btd-2024-2025-12-01.xlsx",
        "arquivo": "br-capes-btd-2024-2025-12-01.xlsx", "tamanho_esperado": 168709069,
    },
]

TERMOS_BUSCA_PACOTES = ["capes-btd", "catalogo de teses e dissertacoes", "banco de teses"]


def _ckan_get(acao, **params):
    qs = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
    url = f"{CKAN_BASE}/{acao}" + (f"?{qs}" if qs else "")
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not payload.get("success"):
        raise RuntimeError(f"CKAN {acao} retornou success=false: {payload.get('error')}")
    return payload["result"]


def _recursos_de_pacote(package_id):
    """Consulta package_show e extrai (ano, url, arquivo, tamanho) de cada
    recurso cujo nome/URL bate com (br-)?capes-btd-<ano>. Um pacote pode ter
    recursos que não são XLSX de ano (documentação, dicionário de dados) —
    esses são ignorados silenciosamente (não batem no regex).

    Alguns pacotes (o legado 1987-2012, confirmado em 12/09/2026 via
    --dump-recursos) publicam o MESMO ano em dois formatos (CSV e XLSX) sob
    nomes que batem igualmente no regex. `filtrar_arquivo()` só sabe ler
    XLSX (openpyxl) — recursos que não sejam XLSX (por campo `format` ou,
    na ausência dele, pela extensão da URL) são descartados aqui, para não
    haver ambiguidade de qual dos dois um mesmo ano deveria usar."""
    resultado = _ckan_get("package_show", id=package_id)
    achados = []
    for r in resultado.get("resources", []):
        nome = r.get("name", "") or ""
        url = r.get("url", "") or ""
        m = PADRAO_NOME_ANO.search(nome) or PADRAO_NOME_ANO.search(url)
        if not m:
            continue
        formato = (r.get("format") or "").strip().upper()
        if not formato:
            formato = os.path.splitext(url.split("?")[0])[1].lstrip(".").upper()
        if formato and formato != "XLSX":
            continue
        ano = int(m.group(1))
        arquivo = os.path.basename(url.split("?")[0]) or f"br-capes-btd-{ano}.xlsx"
        tamanho = r.get("size")
        try:
            tamanho = int(tamanho) if tamanho not in (None, "") else None
        except (TypeError, ValueError):
            tamanho = None
        achados.append({
            "ano": ano, "pacote": package_id, "url": url,
            "arquivo": arquivo, "tamanho_esperado": tamanho,
        })
    return achados


def _pacotes_por_busca(termos):
    """package_search por cada termo — usado só quando --buscar-pacotes é
    pedido, para tentar localizar o legado 1987-2012 (ou outros anos) fora
    do pacote padrão. Não garante que o legado exista como XLSX aberto —
    só reporta o que a API devolver."""
    ids = set()
    for termo in termos:
        try:
            resultado = _ckan_get("package_search", q=termo, rows=20)
        except Exception as e:
            print(f"  [aviso] package_search('{termo}') falhou: {e}")
            continue
        for pacote in resultado.get("results", []):
            ids.add(pacote["id"])
    return sorted(ids)


def descobrir_recursos(package_ids_extra=None, buscar_pacotes=False):
    """Ponto de entrada da descoberta. Tenta o pacote padrão + extras +
    (opcionalmente) busca; cai para o fallback fixo da v1 se TUDO falhar."""
    package_ids = [PACKAGE_ID_PADRAO] + list(package_ids_extra or [])

    if buscar_pacotes:
        print("[descoberta] buscando pacotes adicionais via package_search "
              f"({', '.join(TERMOS_BUSCA_PACOTES)})...")
        extras = _pacotes_por_busca(TERMOS_BUSCA_PACOTES)
        for pid in extras:
            if pid not in package_ids:
                package_ids.append(pid)
        print(f"[descoberta] pacotes encontrados pela busca: {extras or '(nenhum)'}")

    todos = {}
    algum_sucesso = False
    for pid in package_ids:
        try:
            print(f"[descoberta] consultando package_show({pid})...")
            recursos_pacote = _recursos_de_pacote(pid)
            algum_sucesso = True
            for r in recursos_pacote:
                # Se o mesmo ano aparecer em dois pacotes, o primeiro pacote
                # consultado vence (o padrão tem prioridade) — registra o
                # conflito em vez de sobrescrever silenciosamente.
                if r["ano"] in todos and todos[r["ano"]]["pacote"] != r["pacote"]:
                    print(f"  [conflito] ano {r['ano']} aparece em dois pacotes "
                          f"({todos[r['ano']]['pacote']} e {r['pacote']}) — mantendo "
                          f"o primeiro encontrado ({todos[r['ano']]['pacote']}).")
                    continue
                todos[r["ano"]] = r
            print(f"  -> {len(recursos_pacote)} ano(s) reconhecido(s) neste pacote: "
                  f"{sorted(r['ano'] for r in recursos_pacote)}")
        except Exception as e:
            print(f"  [aviso] package_show({pid}) falhou: {e}")

    if not algum_sucesso:
        print("[descoberta] TODAS as consultas à API falharam (rede indisponível ou "
              "endpoint mudou). Caindo para os 4 recursos fixos da v1 (2021-2024) — "
              "a janela NÃO foi estendida nesta execução.")
        return list(RECURSOS_FALLBACK_V1)

    recursos = sorted(todos.values(), key=lambda r: r["ano"])
    anos_v1 = {r["ano"] for r in RECURSOS_FALLBACK_V1}
    anos_achados = {r["ano"] for r in recursos}
    if not anos_v1.issubset(anos_achados):
        faltando = sorted(anos_v1 - anos_achados)
        print(f"  [aviso] os anos {faltando} da v1 não apareceram na descoberta — "
              f"conferir manualmente antes de assumir que sumiram do portal.")
    return recursos


# ---------------------------------------------------------------------------
# 2. Colunas a varrer e de identificação (idêntico à v1)
# ---------------------------------------------------------------------------

CAMPOS_ALVO = [
    "NM_PRODUCAO", "DS_RESUMO", "DS_ABSTRACT", "DS_PALAVRA_CHAVE", "DS_KEYWORD",
]

CAMPOS_ID = [
    "NM_SUBTIPO_PRODUCAO", "NM_PROGRAMA", "NM_ENTIDADE_ENSINO",
    "NM_GRANDE_AREA_CONHECIMENTO", "NM_AREA_CONHECIMENTO",
    "NM_PRODUCAO", "NM_DISCENTE", "NM_ORIENTADOR", "DT_TITULACAO",
    "DS_URL_TEXTO_COMPLETO", "ID_PRODUCAO_INTELECTUAL",
]

# Alias: nome esperado -> lista de nomes possiveis no cabecalho do XLSX, em
# ordem de preferencia (layout moderno primeiro, legado depois). O primeiro
# que existir no arquivo e usado. Ver nota de patch 12/09/2026 no topo do
# arquivo para a evidencia por tras deste mapeamento.
ALIASES_CABECALHO = {
    "NM_PRODUCAO": ["NM_PRODUCAO", "TituloTese"],
    "DS_RESUMO": ["DS_RESUMO", "ResumoTese"],
    "DS_ABSTRACT": ["DS_ABSTRACT"],
    "DS_PALAVRA_CHAVE": ["DS_PALAVRA_CHAVE", "PalavrasChave"],
    "DS_KEYWORD": ["DS_KEYWORD"],
    "NM_SUBTIPO_PRODUCAO": ["NM_SUBTIPO_PRODUCAO", "Nivel"],
    "NM_PROGRAMA": ["NM_PROGRAMA", "NomePrograma"],
    "NM_ENTIDADE_ENSINO": ["NM_ENTIDADE_ENSINO", "NomeIes"],
    "NM_GRANDE_AREA_CONHECIMENTO": ["NM_GRANDE_AREA_CONHECIMENTO", "GrandeAreaDescricao"],
    "NM_AREA_CONHECIMENTO": ["NM_AREA_CONHECIMENTO", "AreaConhecimento"],
    "NM_DISCENTE": ["NM_DISCENTE", "Autor"],
    "NM_ORIENTADOR": ["NM_ORIENTADOR", "Orientador_1"],
    "DT_TITULACAO": ["DT_TITULACAO", "DataDefesa"],
    "DS_URL_TEXTO_COMPLETO": ["DS_URL_TEXTO_COMPLETO", "URLTextoCompleto"],
    "ID_PRODUCAO_INTELECTUAL": ["ID_PRODUCAO_INTELECTUAL"],
}

# Campos que legitimamente NAO existem no layout legado (1987-2012) - a
# ausencia deles e esperada, nao e sinal de layout quebrado.
#   DS_ABSTRACT / DS_KEYWORD: o catalogo legado nao coletava resumo/palavras-
#     chave em ingles como campo separado.
#   ID_PRODUCAO_INTELECTUAL: sem id unico por producao no layout legado - o
#     script sintetiza um id de candidato (nao e um ID oficial da CAPES,
#     nao usar como chave fora deste CSV de candidatos).
CAMPOS_SEM_EQUIVALENTE_LEGADO = {"DS_ABSTRACT", "DS_KEYWORD", "ID_PRODUCAO_INTELECTUAL"}

# ---------------------------------------------------------------------------
# 3. Expressões de busca — Blocos A-E, IDÊNTICO à v1 (copiado verbatim)
# ---------------------------------------------------------------------------

PADROES = [
    ("A", '"tarifa zero"', "frase", "tarifa zero"),
    ("A", '"passe livre"', "frase", "passe livre"),
    ("A", '"transporte gratuito"~2', "proximidade", ("transporte", "gratuito", 2)),
    ("A", '"isencao de tarifa"', "frase", "isencao de tarifa"),
    ("A", '"isencao tarifaria"', "frase", "isencao tarifaria"),
    ("A", '"gratuidade universal"', "frase", "gratuidade universal"),
    ("A", '"gratuidade total"', "frase", "gratuidade total"),
    ("A", '"gratuidade tarifaria"', "frase", "gratuidade tarifaria"),
    ("A", '"transporte sem cobranca"', "frase", "transporte sem cobranca"),
    ("A", "catraca(s)", "frase", "catraca"),
    ("A", '"sem catraca"', "frase", "sem catraca"),
    ("A", "destarifa*", "prefixo", r"\bdestarifa\w*"),

    ("B", '"fare-free"', "frase", "fare-free"),
    ("B", '"free public transport"', "frase", "free public transport"),
    ("B", '"free public transportation"', "frase", "free public transportation"),
    ("B", '"zero fare"', "frase", "zero fare"),
    ("B", '"zero tariff"', "frase", "zero tariff"),
    ("B", '"free fare"', "frase", "free fare"),
    ("B", '"free transit"', "frase", "free transit"),
    ("B", '"fare abolition"', "frase", "fare abolition"),

    ("C", "vermelhinho(s)", "frase", "vermelhinho"),
    ("C", '"busao 0800"', "frase", "busao 0800"),
    ("C", '"domingo tarifa zero"', "frase", "domingo tarifa zero"),
    ("C", '"tarifa zero de domingo"', "frase", "tarifa zero de domingo"),
    ("C", '"passe livre estudantil"', "frase", "passe livre estudantil"),
    ("C", '"passe livre eleitoral"', "frase", "passe livre eleitoral"),

    ("D", '"movimento passe livre"', "frase", "movimento passe livre"),
    ("D", '"movimento tarifa zero"', "frase", "movimento tarifa zero"),
    ("D", '"revolta tarifaria"', "frase", "revolta tarifaria"),
    ("D", '"jornadas de junho"', "frase", "jornadas de junho"),
    ("D", '"junho de 2013"', "frase", "junho de 2013"),

    ("E", '"vale-transporte"', "frase", "vale-transporte"),
    ("E", '"subsidio tarifario"', "frase", "subsidio tarifario"),
    ("E", '"subsidio ao transporte"', "frase", "subsidio ao transporte"),
    ("E", '"versement transport"', "frase", "versement transport"),
    ("E", '"producao quilometrica"', "frase", "producao quilometrica"),
    ("E", '"remuneracao por quilometro"', "frase", "remuneracao por quilometro"),
    ("E", '"contribuicao para disponibilizacao"', "frase", "contribuicao para disponibilizacao"),
    ("E", "CIDE AND transporte", "cooc", ("cide", "transporte")),
    ("E", "gratuidades (estrato proprio - NAO somar ao corpus)", "frase", "gratuidades"),
]


def normalizar(texto):
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.lower()


def compilar_padroes():
    compilados = []
    for bloco, legivel, tipo, dado in PADROES:
        if tipo == "frase":
            compilados.append((bloco, legivel, tipo, normalizar(dado)))
        elif tipo == "prefixo":
            compilados.append((bloco, legivel, tipo, re.compile(dado)))
        elif tipo == "proximidade":
            a, b, n = dado
            compilados.append((bloco, legivel, tipo, (normalizar(a), normalizar(b), n)))
        elif tipo == "cooc":
            a, b = dado
            compilados.append((bloco, legivel, tipo, (normalizar(a), normalizar(b))))
        else:
            raise ValueError(f"tipo de padrao desconhecido: {tipo}")
    return compilados


def casa(padrao_compilado, texto_norm, tokens):
    bloco, legivel, tipo, dado = padrao_compilado
    if tipo == "frase":
        return dado in texto_norm
    if tipo == "prefixo":
        return bool(dado.search(texto_norm))
    if tipo == "proximidade":
        a, b, n = dado
        pos_a = [i for i, t in enumerate(tokens) if t == a]
        pos_b = [i for i, t in enumerate(tokens) if t == b]
        return any(abs(i - j) <= n for i in pos_a for j in pos_b)
    if tipo == "cooc":
        a, b = dado
        return a in texto_norm and b in texto_norm
    return False


JANELA_TRECHO = 150

def extrair_trecho(padrao_compilado, valor_original, texto_norm, tokens, janela=JANELA_TRECHO):
    bloco, legivel, tipo, dado = padrao_compilado
    pos = None
    if tipo == "frase":
        pos = texto_norm.find(dado)
    elif tipo == "prefixo":
        m = dado.search(texto_norm)
        pos = m.start() if m else None
    elif tipo == "proximidade":
        a, b, n = dado
        pos_a = [i for i, t in enumerate(tokens) if t == a]
        pos_b = [i for i, t in enumerate(tokens) if t == b]
        melhor = None
        for i in pos_a:
            for j in pos_b:
                if abs(i - j) <= n and (melhor is None or abs(i - j) < melhor[0]):
                    melhor = (abs(i - j), min(i, j))
        if melhor:
            pos = texto_norm.find(tokens[melhor[1]])
    elif tipo == "cooc":
        a, b = dado
        candidatos_pos = [p for p in (texto_norm.find(a), texto_norm.find(b)) if p >= 0]
        pos = min(candidatos_pos) if candidatos_pos else None

    if pos is None or pos < 0:
        pos = 0
    ini = max(0, pos - janela)
    fim = min(len(valor_original), pos + janela)
    trecho = valor_original[ini:fim].replace("\n", " ").replace("\r", " ").replace(";", ",").strip()
    return f"{'…' if ini > 0 else ''}{trecho}{'…' if fim < len(valor_original) else ''}"


# ---------------------------------------------------------------------------
# 4. Download idempotente — igual à v1, com tamanho_esperado agora OPCIONAL
# ---------------------------------------------------------------------------

def instalar_contexto_ssl_robusto():
    contexto = None
    origem = "padrao do sistema"
    try:
        import truststore
        truststore.inject_into_ssl()
        contexto = ssl.create_default_context()
        origem = "truststore (verificacao nativa do SO - cobre CA corporativa/antivirus)"
    except ImportError:
        try:
            import certifi
            contexto = ssl.create_default_context(cafile=certifi.where())
            origem = f"certifi ({certifi.where()})"
        except ImportError:
            contexto = ssl.create_default_context()

    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=contexto))
    urllib.request.install_opener(opener)
    print(f"[ssl] contexto de verificacao: {origem}")


def obter_tamanho_via_head(url):
    """Usado quando o CKAN nao informa `size` do recurso (acontece com
    alguns datasets legados) - tenta descobrir o tamanho por HEAD antes de
    desistir da verificacao estrita."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as resp:
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl else None
    except Exception as e:
        print(f"  [aviso] HEAD para descobrir tamanho falhou ({e}) - seguindo sem "
              f"verificacao estrita de tamanho para este arquivo.")
        return None


MAX_TENTATIVAS = 6

def _tamanho_atual(tmp):
    return os.path.getsize(tmp) if os.path.exists(tmp) else 0


def baixar(recurso, dest_dir):
    destino = os.path.join(dest_dir, recurso["arquivo"])
    esperado = recurso.get("tamanho_esperado")
    if esperado is None:
        esperado = obter_tamanho_via_head(recurso["url"])
        recurso["tamanho_esperado"] = esperado  # registra para o CSV de execucao

    if esperado is not None and os.path.exists(destino) and os.path.getsize(destino) == esperado:
        print(f"[{recurso['ano']}] ja baixado e completo ({esperado/1e6:.0f} MB) - pulando")
        return destino
    if esperado is None and os.path.exists(destino) and os.path.getsize(destino) > 0:
        print(f"[{recurso['ano']}] ja existe arquivo em {destino} e o tamanho esperado e "
              f"desconhecido - pulando (apague o arquivo manualmente para forcar rebaixar).")
        return destino

    tmp = destino + ".part"
    rotulo_tamanho = f"{esperado/1e6:.0f} MB esperados" if esperado else "tamanho esperado desconhecido"
    print(f"[{recurso['ano']}] baixando {recurso['arquivo']} ({rotulo_tamanho})...")

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        ja_tenho = _tamanho_atual(tmp)
        if esperado is not None and ja_tenho >= esperado:
            break

        req = urllib.request.Request(recurso["url"])
        modo_retomada = ja_tenho > 0
        if modo_retomada:
            req.add_header("Range", f"bytes={ja_tenho}-")
            print(f"  [tentativa {tentativa}/{MAX_TENTATIVAS}] retomando de {ja_tenho/1e6:.0f} MB...")
        elif tentativa > 1:
            print(f"  [tentativa {tentativa}/{MAX_TENTATIVAS}] recomecando do zero...")

        inicio = time.time()
        baixado_nesta_tentativa = 0
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                aceita_range = resp.status == 206
                if modo_retomada and not aceita_range:
                    print("  [aviso] servidor nao devolveu 206 (Partial Content) - "
                          "nao suporta retomada; reiniciando este arquivo do zero.")
                    ja_tenho = 0
                modo_escrita = "ab" if (modo_retomada and aceita_range) else "wb"
                with open(tmp, modo_escrita) as f:
                    while True:
                        bloco = resp.read(1024 * 256)
                        if not bloco:
                            break
                        f.write(bloco)
                        baixado_nesta_tentativa += len(bloco)
                        total_no_disco = ja_tenho + baixado_nesta_tentativa
                        if esperado:
                            pct = min(100, total_no_disco * 100 / esperado)
                            velocidade = baixado_nesta_tentativa / max(time.time() - inicio, 0.001) / 1e6
                            sys.stdout.write(f"\r  {pct:5.1f}%  ({total_no_disco/1e6:.0f}/{esperado/1e6:.0f} MB, "
                                              f"{velocidade:.1f} MB/s)")
                        else:
                            sys.stdout.write(f"\r  {total_no_disco/1e6:.0f} MB baixados (tamanho total desconhecido)")
                        sys.stdout.flush()
            print()
        except Exception as e:
            print(f"\n  [tentativa {tentativa}/{MAX_TENTATIVAS}] FALHOU: {e}")
            if tentativa == MAX_TENTATIVAS:
                print(f"[{recurso['ano']}] desistindo apos {MAX_TENTATIVAS} tentativas. "
                      f"O arquivo parcial ficou em {tmp} ({_tamanho_atual(tmp)/1e6:.0f} MB) - "
                      f"rode o script de novo mais tarde, ele retoma dai.")
                raise
            espera = min(30, 2 ** tentativa)
            print(f"  aguardando {espera}s antes de tentar de novo...")
            time.sleep(espera)

    tamanho_real = os.path.getsize(tmp)
    if esperado is not None and tamanho_real < esperado:
        raise RuntimeError(
            f"[{recurso['ano']}] download incompleto apos {MAX_TENTATIVAS} tentativas: "
            f"{tamanho_real} de {esperado} bytes esperados ({tamanho_real*100/esperado:.1f}%). "
            f"O arquivo parcial ficou em {tmp} - rode o script de novo."
        )
    if esperado is not None and tamanho_real > esperado:
        print(f"[{recurso['ano']}] AVISO: tamanho baixado ({tamanho_real} B) e MAIOR que o "
              f"esperado ({esperado} B) - o arquivo publicado pela CAPES deve ter mudado desde "
              f"a descoberta. Seguindo mesmo assim; registre isso na nota de execucao.")
    if esperado is None:
        print(f"[{recurso['ano']}] concluido sem verificacao estrita de tamanho "
              f"({tamanho_real/1e6:.0f} MB baixados) - tamanho esperado nao pode ser "
              f"determinado (CKAN e HEAD nao informaram).")
    os.replace(tmp, destino)
    return destino


# ---------------------------------------------------------------------------
# 5. Filtro local — IDÊNTICO à v1
# ---------------------------------------------------------------------------

def filtrar_arquivo(caminho_xlsx, ano, padroes, contagem_por_string, candidatos_out):
    try:
        import openpyxl
    except ImportError:
        sys.exit("ERRO: openpyxl nao esta instalado. Rode: pip install openpyxl")

    print(f"[{ano}] abrindo {os.path.basename(caminho_xlsx)} (modo streaming)...")
    wb = openpyxl.load_workbook(caminho_xlsx, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]

    linhas = ws.iter_rows(values_only=True)
    cabecalho = next(linhas)
    cabecalho = list(cabecalho)

    idx = {}
    faltando_de_verdade = []
    sem_equivalente_neste_ano = []
    for nome in CAMPOS_ALVO + CAMPOS_ID:
        if nome in idx:
            continue
        encontrado = None
        for alias in ALIASES_CABECALHO.get(nome, [nome]):
            if alias in cabecalho:
                encontrado = alias
                break
        if encontrado is not None:
            idx[nome] = cabecalho.index(encontrado)
        elif nome in CAMPOS_SEM_EQUIVALENTE_LEGADO:
            idx[nome] = None
            sem_equivalente_neste_ano.append(nome)
        else:
            faltando_de_verdade.append(nome)

    if faltando_de_verdade:
        sys.exit(f"ERRO [{ano}]: coluna(s) {faltando_de_verdade} nao encontrada(s) no cabecalho "
                  f"nem em nenhum alias conhecido (layout moderno 2013+ ou legado 1987-2012). "
                  f"O layout do CAPES pode ter mudado de novo - conferir manualmente antes de "
                  f"prosseguir. Cabecalho completo deste arquivo: {cabecalho}")
    if sem_equivalente_neste_ano:
        aviso_id = (" ID_PRODUCAO_INTELECTUAL sera sintetizado como 'LEGADO-<ano>-<linha>' "
                    "(nao e id oficial da CAPES)." if "ID_PRODUCAO_INTELECTUAL" in sem_equivalente_neste_ano else "")
        print(f"[{ano}] aviso: {sem_equivalente_neste_ano} nao existem neste layout - "
              f"esperado para anos legados (1987-2012), seguindo sem eles.{aviso_id}")

    n_lidas = 0
    n_com_match = 0
    t0 = time.time()

    for linha in linhas:
        n_lidas += 1
        if n_lidas % 200000 == 0:
            print(f"  ... {n_lidas} linhas lidas ({time.time()-t0:.0f}s)")

        matches_desta_linha = []
        for campo in CAMPOS_ALVO:
            if idx[campo] is None:
                continue
            valor = linha[idx[campo]]
            if not valor:
                continue
            valor_str = str(valor)
            texto_norm = normalizar(valor_str)
            tokens = texto_norm.split()
            for p in padroes:
                if casa(p, texto_norm, tokens):
                    bloco, legivel = p[0], p[1]
                    trecho = extrair_trecho(p, valor_str, texto_norm, tokens)
                    matches_desta_linha.append((bloco, legivel, campo, trecho))
                    contagem_por_string[(ano, bloco, legivel)] = contagem_por_string.get((ano, bloco, legivel), 0) + 1

        if matches_desta_linha:
            n_com_match += 1
            blocos_e_strings = ", ".join(f"{b}:{s}" for b, s, _, _ in matches_desta_linha)
            campos = ", ".join(sorted(set(c for _, _, c, _ in matches_desta_linha)))
            trechos = " | ".join(f"{c}[{s}]: {t}" for _, s, c, t in matches_desta_linha)
            linha_saida = {"ano": ano, "blocos_e_strings": blocos_e_strings,
                            "campos_com_match": campos, "trechos": trechos}
            for nome in CAMPOS_ID:
                if idx[nome] is None:
                    linha_saida[nome] = f"LEGADO-{ano}-{n_lidas}" if nome == "ID_PRODUCAO_INTELECTUAL" else ""
                else:
                    linha_saida[nome] = linha[idx[nome]]
            candidatos_out.append(linha_saida)

    wb.close()
    print(f"[{ano}] {n_lidas} linhas lidas, {n_com_match} com pelo menos um match "
          f"({time.time()-t0:.0f}s)")


def gravar_csv_validado(caminho, linhas, campos):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=campos, delimiter=";", lineterminator="\n")
    w.writeheader()
    w.writerows(linhas)
    texto = buf.getvalue()
    checagem = list(csv.reader(io.StringIO(texto), delimiter=";"))
    tamanhos = {len(r) for r in checagem}
    assert len(tamanhos) == 1, f"CSV desalinhado: tamanhos de linha {tamanhos}"
    assert len(checagem) == len(linhas) + 1, "numero de linhas nao bate apos reparse"
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.write(texto)


# ---------------------------------------------------------------------------
# 6. main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", help="pasta para os XLSX brutos (obrigatorio, exceto com --listar)")
    ap.add_argument("--out", help="pasta para os CSVs de resultado (obrigatorio, exceto com --listar)")
    ap.add_argument("--anos", nargs="*", type=int, default=None, help="subconjunto de anos, ex.: --anos 2013 2014")
    ap.add_argument("--so-baixar", action="store_true", help="so baixa os XLSX, nao filtra")
    ap.add_argument("--so-filtrar", action="store_true", help="pula o download, assume XLSX ja em --dest")
    ap.add_argument("--listar", action="store_true", help="so descobre e imprime os recursos disponiveis; nao baixa nem filtra")
    ap.add_argument("--package-id", action="append", default=[], help="pacote(s) CKAN adicionais a consultar (pode repetir)")
    ap.add_argument("--buscar-pacotes", action="store_true", help="tenta localizar pacotes adicionais via package_search")
    ap.add_argument("--dump-recursos", metavar="PACKAGE_ID",
                     help="diagnostico: imprime TODOS os recursos de um pacote (nome, formato, url, tamanho), "
                          "sem passar pelo regex br-capes-btd-<ano> — usar quando um pacote aparece com "
                          "'0 anos reconhecidos' mas pode ter arquivos com outro padrao de nome (ex.: o "
                          "legado 1987-2012, cujo slug nao segue 'br-capes-btd-...'). Nao baixa nada.")
    args = ap.parse_args()

    if args.dump_recursos:
        print(f"[dump] consultando package_show({args.dump_recursos}) sem filtro de regex...\n")
        resultado = _ckan_get("package_show", id=args.dump_recursos)
        recursos = resultado.get("resources", [])
        if not recursos:
            print("  (pacote existe mas nao tem nenhum recurso listado)")
        for r in recursos:
            tam = r.get("size")
            tam_str = f"{int(tam)/1e6:.1f} MB" if tam not in (None, "") else "tamanho nao informado"
            print(f"  - nome: {r.get('name')!r}")
            print(f"    formato: {r.get('format')!r}  tamanho: {tam_str}")
            print(f"    url: {r.get('url')}")
            print()
        return

    print("[descoberta] iniciando (isto faz chamadas de rede a dadosabertos.capes.gov.br)...")
    recursos_todos = descobrir_recursos(package_ids_extra=args.package_id, buscar_pacotes=args.buscar_pacotes)

    if args.listar:
        print(f"\n{len(recursos_todos)} recurso(s) descoberto(s):\n")
        for r in sorted(recursos_todos, key=lambda x: x["ano"]):
            tam = f"{r['tamanho_esperado']/1e6:.0f} MB" if r.get("tamanho_esperado") else "tamanho desconhecido"
            print(f"  {r['ano']}  [{r['pacote']}]  {tam}\n    {r['url']}")
        anos_v1 = {r["ano"] for r in RECURSOS_FALLBACK_V1}
        anos_novos = sorted({r["ano"] for r in recursos_todos} - anos_v1)
        print(f"\nAnos ja cobertos na v1 (2021-2024): {sorted(anos_v1 & {r['ano'] for r in recursos_todos})}")
        print(f"Anos NOVOS encontrados (alem da v1): {anos_novos or '(nenhum — a janela nao foi estendida por esta via)'}")
        print("\nNenhum arquivo foi baixado (--listar). Rode de novo sem --listar, com --anos "
              "escolhido a partir desta lista, quando estiver pronto para baixar.")
        return

    if not args.dest or not args.out:
        sys.exit("ERRO: --dest e --out sao obrigatorios fora do modo --listar.")

    os.makedirs(args.dest, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)

    recursos = [r for r in recursos_todos if args.anos is None or r["ano"] in args.anos]
    if not recursos:
        sys.exit("nenhum recurso selecionado - conferir --anos (rode --listar primeiro para ver o que existe)")

    caminhos = {}
    anos_falhos_download = []
    if not args.so_filtrar:
        instalar_contexto_ssl_robusto()
        for r in recursos:
            try:
                caminhos[r["ano"]] = baixar(r, args.dest)
            except Exception as e:
                if isinstance(e, urllib.error.URLError) and "CERTIFICATE_VERIFY_FAILED" in str(e):
                    sys.exit(
                        "\nFalha de certificado SSL mesmo com truststore/certifi tentados.\n"
                        "Rode NA ORDEM e tente de novo apos cada passo:\n"
                        "  1) pip install truststore\n"
                        "  2) pip install pip-system-certs\n"
                        "  3) Pergunte ao TI se ha proxy/antivirus com inspecao de TLS.\n"
                    )
                print(f"\n[{r['ano']}] FALHA NO DOWNLOAD - pulando este ano: {e}\n")
                anos_falhos_download.append(r["ano"])
    else:
        for r in recursos:
            caminho = os.path.join(args.dest, r["arquivo"])
            if not os.path.exists(caminho):
                sys.exit(f"--so-filtrar pedido mas {caminho} nao existe")
            caminhos[r["ano"]] = caminho

    if args.so_baixar:
        print("Download concluido (--so-baixar). Encerrando sem filtrar.")
        return

    padroes = compilar_padroes()
    contagem_por_string = {}
    candidatos = []
    anos_falhos_filtro = []

    for r in recursos:
        if r["ano"] not in caminhos:
            continue
        try:
            filtrar_arquivo(caminhos[r["ano"]], r["ano"], padroes, contagem_por_string, candidatos)
        except Exception as e:
            print(f"\n[{r['ano']}] FALHA AO FILTRAR - pulando este ano: {e}\n")
            anos_falhos_filtro.append(r["ano"])

    anos_ok = [r["ano"] for r in recursos if r["ano"] not in anos_falhos_download and r["ano"] not in anos_falhos_filtro]
    recursos_ok = [r for r in recursos if r["ano"] in anos_ok]

    hoje = date.today().isoformat()

    campos_candidatos = ["ano", "blocos_e_strings", "campos_com_match", "trechos"] + CAMPOS_ID
    caminho_candidatos = os.path.join(args.out, f"CAPES_candidatos_janela_estendida_{hoje}.csv")
    gravar_csv_validado(caminho_candidatos, candidatos, campos_candidatos)
    print(f"\nGravado: {caminho_candidatos}  ({len(candidatos)} candidatos)")

    linhas_execucao = []
    for r in recursos_ok:
        for bloco, legivel, tipo, dado in PADROES:
            n = contagem_por_string.get((r["ano"], bloco, legivel), 0)
            linhas_execucao.append({
                "data": hoje, "estrato": "RSL1",
                "base": f"Catalogo de Teses CAPES - XLSX {r['ano']} (janela estendida, pacote {r['pacote']})",
                "string": legivel, "bloco": bloco,
                "filtro_data": "sem recorte", "n_resultados": n,
            })
    campos_execucao = ["data", "estrato", "base", "string", "bloco", "filtro_data", "n_resultados"]
    caminho_execucao = os.path.join(args.out, f"CAPES_execucao_por_string_janela_estendida_{hoje}.csv")
    gravar_csv_validado(caminho_execucao, linhas_execucao, campos_execucao)
    print(f"Gravado: {caminho_execucao}  ({len(linhas_execucao)} linhas)")

    print("\nPROXIMO PASSO: nenhum destes candidatos entra em corpus_rsl.csv sem leitura "
          "e sem passar pelos filtros 1 e 2 do protocolo. Junte estes dois CSVs aos da v1 "
          "(2021-2024) antes de rodar a triagem por titulo e resumo (mesmo metodo da nota "
          "'RSL1 — CAPES triagem por titulo e resumo, filtros 1 e 3').")

    anos_falhos = sorted(set(anos_falhos_download) | set(anos_falhos_filtro))
    if anos_falhos:
        print(f"\n⚠️  ANOS NAO PROCESSADOS: {anos_falhos} - os CSVs acima cobrem so "
              f"{sorted(anos_ok)}. Rode de novo so para os anos que faltaram.")
        sys.exit(1)


if __name__ == "__main__":
    main()
