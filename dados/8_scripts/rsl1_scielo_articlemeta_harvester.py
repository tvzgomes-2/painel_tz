#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSL1 — colheita de metadados via SciELO ArticleMeta (cobre o buraco dos sem-DOI)

O QUE ISSO RESOLVE E O QUE NÃO RESOLVE
---------------------------------------
A busca por proxy Crossref (`filter=prefix:10.1590`, ver [[RSL1 — SciELO por
proxy, Crossref em inglês retomada e o diagnóstico do Catálogo CAPES
(09-09-2026)]]) só alcança o que a SciELO indexa COM DOI. Ela mesma declara o
limite: "não substitui a SciELO — o proxy deixa fora o que a SciELO indexa
sem DOI e o anterior à adoção de DOI".

Este script NÃO faz busca por palavra-chave em tempo real — a ArticleMeta
(articlemeta.scielo.org, API pública e documentada, sem robots.txt de busca a
contornar) não é um motor de busca, é uma API de COLHEITA de metadados por
periódico. O formato do trabalho é igual ao do Catálogo CAPES: baixar os
metadados (título + resumo, nos dois/três idiomas do registro) de um conjunto
de periódicos e filtrar localmente pelas mesmas expressões já usadas no
protocolo do RSL1.

⚠️ DECISÃO DO AUTOR, NÃO MINHA: quais periódicos entram na colheita.
A lista abaixo (`PERIODICOS_PADRAO`) é um ponto de partida — os periódicos que
já apareceram como relevantes na busca por proxy Crossref (Cadernos
Metrópole, urbe, RAP) mais três correlatos óbvios (RBCS, EURE, Novos Estudos
CEBRAP). NÃO é "todo o SciELO": a coleção `scl` tem 427 periódicos (verificado
em 10/09/2026), e colher todos sem recorte temático é um projeto de escala
muito maior — provavelmente dias, não horas. Recomendação: rodar primeiro com
a lista padrão (pequena, ~6 periódicos, poucos milhares de artigos) e decidir
se vale expandir a partir do que aparecer.

ENDPOINTS (verificados manualmente em 10/09/2026, sem autenticação):
    GET /api/v1/journal/identifiers/?collection=scl
        -> lista todos os periódicos da coleção (code = ISSN)
    GET /api/v1/article/identifiers/?collection=scl&issn=<ISSN>&limit=&offset=
        -> pagina os PIDs (`code`) de um periódico
    GET /api/v1/article/?collection=scl&code=<PID>
        -> registro completo; título em `article.v12` (lista {l: idioma, _: texto}),
           resumo em `article.v83` (lista {l: idioma, a: texto com entidades HTML
           numéricas, ex. &#227; = ã — precisa unescape})

USO
---
    python3 rsl1_scielo_articlemeta_harvester.py --out candidatos_scielo.csv

    # com periódicos e expressões próprios:
    python3 rsl1_scielo_articlemeta_harvester.py --out saida.csv \\
        --issn 2236-9996 --issn 2175-3369 \\
        --keyword "tarifa zero" --keyword gratuidade

    # RETENTAR só os PIDs que deram timeout numa rodada anterior — pula a
    # listagem por periódico inteiro, busca cada PID direto, com timeout maior
    # e uma tentativa extra antes de desistir:
    python3 rsl1_scielo_articlemeta_harvester.py --out retry.csv \\
        --timeout 60 --retries 2 \\
        --pid S2236-99962021000200605 --pid S2236-99962026000100614 \\
        --pid S0102-69092017000100901 --pid S0102-69092020000200703 \\
        --pid S0102-69092022000300508 --pid S0101-33002024000300461

Filtro local: título+resumo (todos os idiomas do registro) contra as
expressões, sem acento e sem caixa — mesmo critério de "casa por trecho" já
usado no CAPES (ver [[RSL1 — CAPES triagem por título e resumo, filtros 1 e 3
(10-09-2026)]]). NENHUM candidato aqui entra em `corpus_rsl.csv` sem leitura
integral e sem decisão pelos filtros 1/2/3 do protocolo — é o mesmo próximo
passo que já vale para os 20 aprovados do CAPES e os 7 novos do Crossref.
"""

import argparse
import csv
import html
import sys
import time
import unicodedata
from urllib.parse import urlencode
from urllib.request import urlopen, Request
import json

BASE = "https://articlemeta.scielo.org/api/v1"
USER_AGENT = "Mozilla/5.0 (compatible; RSL-PGT092-research-script/1.0; +pesquisa academica UFABC)"
SLEEP_BETWEEN_REQUESTS = 0.3  # ArticleMeta é infraestrutura da SciELO, mais robusta que a ANTP, mas sem exagerar

# Periódicos SciELO Brasil já identificados como relevantes ao objeto (via a
# busca por proxy Crossref de 09/09/2026) + correlatos óbvios de ciência
# política/sociologia urbana. AJUSTAR conforme decisão do autor.
PERIODICOS_PADRAO = {
    "2236-9996": "Cadernos Metrópole",
    "2175-3369": "urbe — Revista Brasileira de Gestão Urbana",
    "0034-7612": "RAP — Revista de Administração Pública",
    "0102-6909": "RBCS — Revista Brasileira de Ciências Sociais",
    "0101-3300": "Novos Estudos CEBRAP",
    # EURE é chilena (coleção "chl", não "scl") — se o autor quiser incluir,
    # rodar com --collection chl --issn 0250-7161 separadamente.
}

# Bloco A (núcleo) do protocolo do RSL1 — conferir contra [[Expressões de
# busca do RSL1 — conjunto a executar (03-09-2026)]] antes de rodar valendo;
# isto é um ponto de partida, não a lista canônica.
KEYWORDS_PADRAO = ["tarifa zero", "gratuidade tarifaria", "passe livre", "isencao tarifaria"]


def strip_accents(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c))


def normalize(s):
    return strip_accents(s or "").lower()


def http_get_json(url, timeout=30, retries=1, backoff=2.0):
    """Busca JSON com retry simples em timeout/erro de rede.

    `retries=1` preserva o comportamento original (uma tentativa, sem retry).
    `retries=2` tenta de novo uma vez, com um pequeno backoff — foi para isso
    que este parâmetro foi acrescentado: os 6 PIDs que deram "The read
    operation timed out" na rodada de 10/09/2026 pareciam lentidão pontual da
    ArticleMeta, não bloqueio (mesmo padrão do HTTP 429 do Crossref em 03/09 —
    ver [[RSL1 — SciELO por proxy, Crossref em inglês retomada e o diagnóstico
    do Catálogo CAPES (09-09-2026)]] §3). Retry não é contornar bloqueio: é
    tolerar instabilidade de rede, e fica registrado como tal.
    """
    last_exc = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_exc = e
            if attempt < retries:
                time.sleep(backoff * attempt)
    raise last_exc


def list_journals(collection="scl"):
    url = f"{BASE}/journal/identifiers/?collection={collection}"
    data = http_get_json(url)
    return [obj["code"] for obj in data.get("objects", [])]


def list_article_pids(issn, collection="scl", page_size=1000, timeout=30, retries=1):
    """Pagina todos os PIDs de um periódico via offset/limit."""
    pids = []
    offset = 0
    while True:
        url = f"{BASE}/article/identifiers/?" + urlencode({
            "collection": collection, "issn": issn, "limit": page_size, "offset": offset
        })
        data = http_get_json(url, timeout=timeout, retries=retries)
        objs = data.get("objects", [])
        pids.extend(obj["code"] for obj in objs)
        total = int(data.get("meta", {}).get("total", 0))
        offset += page_size
        if offset >= total or not objs:
            break
        time.sleep(SLEEP_BETWEEN_REQUESTS)
    return pids


def fetch_article(pid, collection="scl", timeout=30, retries=1):
    url = f"{BASE}/article/?" + urlencode({"collection": collection, "code": pid})
    return http_get_json(url, timeout=timeout, retries=retries)


def issn_from_pid(pid):
    """Extrai o ISSN embutido no PID da SciELO — formato S<ISSN>AAAA......

    Ex.: 'S2236-99962021000200605'[1:10] == '2236-9996'. Usado no modo
    --pid para reconstituir de qual periódico é cada PID retentado, sem
    precisar que o autor informe o ISSN de novo na linha de comando.
    """
    if len(pid) >= 10 and pid[0] in ("S", "s"):
        return pid[1:10]
    return ""


def extract_titles_and_abstracts(article_record):
    art = article_record.get("article", {}) or {}
    titles = [html.unescape(item.get("_", "")) for item in art.get("v12", []) if item.get("_")]
    abstracts = [html.unescape(item.get("a", "")) for item in art.get("v83", []) if item.get("a")]
    return titles, abstracts


def build_doi_and_year(article_record):
    doi = article_record.get("doi", "")
    year = article_record.get("publication_year", "")
    return doi, year


def matches_any(text_blob_normalized, keywords_normalized):
    return [kw for kw in keywords_normalized if kw in text_blob_normalized]


def main():
    global SLEEP_BETWEEN_REQUESTS

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="CSV de saída")
    ap.add_argument("--collection", default="scl", help="coleção SciELO (padrão: scl = Brasil)")
    ap.add_argument("--issn", action="append", dest="issns", default=None,
                     help="ISSN de periódico a colher (repetir para vários). Se omitido, usa PERIODICOS_PADRAO.")
    ap.add_argument("--keyword", action="append", dest="keywords", default=None,
                     help="expressão a filtrar (repetir para várias). Se omitido, usa KEYWORDS_PADRAO.")
    ap.add_argument("--sleep", type=float, default=SLEEP_BETWEEN_REQUESTS)
    ap.add_argument("--list-journals", action="store_true",
                     help="só lista os periódicos da coleção (code;total_estimado) e sai — útil para escolher ISSNs")
    ap.add_argument("--pid", action="append", dest="pids", default=None,
                     help="PID específico a colher direto (repetir para vários) — pula a listagem por "
                          "periódico inteiro e vai direto ao artigo. Feito para retentar itens que deram "
                          "erro/timeout numa rodada anterior, sem precisar refazer a colheita completa do ISSN.")
    ap.add_argument("--timeout", type=float, default=30.0,
                     help="timeout de rede por requisição, em segundos (padrão: 30)")
    ap.add_argument("--retries", type=int, default=1,
                     help="tentativas por requisição antes de desistir (padrão: 1 = sem retry; "
                          "use 2 ou 3 para retentar timeouts pontuais)")
    args = ap.parse_args()
    SLEEP_BETWEEN_REQUESTS = args.sleep

    if args.list_journals:
        codes = list_journals(args.collection)
        sys.stderr.write(f"[scielo-am] {len(codes)} periódicos na coleção {args.collection!r}\n")
        for c in codes:
            print(c)
        return

    keywords = args.keywords or KEYWORDS_PADRAO
    keywords_norm = [normalize(k) for k in keywords]

    # work_items: lista de (issn, nome_periodico, pid) a buscar. Vem de duas
    # fontes possíveis, mutuamente exclusivas: --pid explícito (retry pontual,
    # sem listar o periódico de novo) ou a listagem normal por ISSN.
    work_items = []

    if args.pids:
        sys.stderr.write(f"[scielo-am] modo --pid: retentando {len(args.pids)} PID(s) específico(s), "
                          f"sem listagem por periódico (timeout={args.timeout}s, retries={args.retries})\n")
        for pid in args.pids:
            issn = issn_from_pid(pid)
            nome = PERIODICOS_PADRAO.get(issn, issn or "issn-desconhecido")
            work_items.append((issn, nome, pid))
    else:
        issns = args.issns or list(PERIODICOS_PADRAO.keys())
        for issn in issns:
            nome = PERIODICOS_PADRAO.get(issn, issn)
            sys.stderr.write(f"[scielo-am] periódico {issn} ({nome}) — listando PIDs...\n")
            try:
                pids = list_article_pids(issn, collection=args.collection,
                                          timeout=args.timeout, retries=args.retries)
            except Exception as e:
                sys.stderr.write(f"[scielo-am] ERRO listando {issn}: {e}\n")
                continue
            sys.stderr.write(f"[scielo-am]   {len(pids)} artigo(s) — colhendo metadados...\n")
            work_items.extend((issn, nome, pid) for pid in pids)

    rows = []
    erros = []
    for i, (issn, nome, pid) in enumerate(work_items, 1):
        try:
            rec = fetch_article(pid, collection=args.collection, timeout=args.timeout, retries=args.retries)
        except Exception as e:
            sys.stderr.write(f"[scielo-am]   ERRO em {pid}: {e}\n")
            erros.append(pid)
            continue
        titles, abstracts = extract_titles_and_abstracts(rec)
        blob = normalize(" ".join(titles + abstracts))
        hits = matches_any(blob, keywords_norm)
        if hits:
            doi, year = build_doi_and_year(rec)
            rows.append({
                "issn": issn,
                "periodico": nome,
                "pid": pid,
                "doi": doi,
                "ano": year,
                "titulo_pt_ou_primeiro": titles[0] if titles else "",
                "expressoes": "|".join(hits),
                "resumo_trecho": (abstracts[0][:400] if abstracts else ""),
            })
        if i % 200 == 0:
            sys.stderr.write(f"[scielo-am]   ...{i}/{len(work_items)} processados\n")
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    sys.stderr.write(f"[scielo-am] total de candidatos com match: {len(rows)}\n")
    if erros:
        sys.stderr.write(f"[scielo-am] {len(erros)} PID(s) ainda com erro após {args.retries} tentativa(s): "
                          + ", ".join(erros) + "\n")

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["issn", "periodico", "pid", "doi", "ano", "titulo_pt_ou_primeiro", "expressoes", "resumo_trecho"])
        for r in rows:
            writer.writerow([r["issn"], r["periodico"], r["pid"], r["doi"], r["ano"],
                              r["titulo_pt_ou_primeiro"], r["expressoes"], r["resumo_trecho"]])

    sys.stderr.write(f"[scielo-am] gravado em {args.out}\n")


if __name__ == "__main__":
    main()
