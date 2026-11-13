#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSL2 — raspagem da Biblioteca Web da ANTP (antp.org.br/biblioteca/)

O QUE ISSO RESOLVE
-------------------
A Frente A do RSL2 (busca por assunto na biblioteca da ANTP) estava parada porque o
portal antigo (antigo.antp.org.br) saiu do ar. A biblioteca migrou para
`antp.org.br/biblioteca/` e é servida por um endpoint JSON público, sem robots.txt
que a restrinja (verificado em 10/09/2026 — /robots.txt devolve a página 404
padrão do site, não um arquivo de regras):

    GET https://antp.org.br/_datasource/biblioteca/search/
        ?ddcKeywords=<assunto>
        &ddcAutor=<autor>
        &ddcDate_from=<AAAA-MM-DD ou vazio>
        &ddcDate_to=<AAAA-MM-DD ou vazio>
        &dgpCode=<keyCode do grupo/seção, ou vazio para todas>
        &dctCode=<keyCode da categoria, ou vazio>
        &sqlPage=<página, 1-based>

Resposta: JSON com `pages` (total/current), `records` (total) e `recordset`
(lista de {title, group, category, link, description, image_url}).

Descoberto lendo o JS inline da própria página (função `biblioteca_search`),
não por engenharia reversa de tráfego de rede — o endpoint é o que a página usa.

REGRA JÁ FIXADA NO PROTOCOLO DA RSL2 (não mexer sem decisão do autor):
    NUNCA usar filtro de data (`ddcDate_from`/`ddcDate_to`) — a mesma consulta
    devolve menos resultados com filtro de data do que sem, inclusive
    resultados recentes (achado de 08/09/2026, [[RSL — nota canonica da revisao (entrada unica dos quatro estratos)|RSL — nota canonica]] §8).

USO
---
    python3 rsl2_antp_biblioteca_scraper.py --out candidatos.csv \\
        "desoneração" "subsídio" "custeio" "vale-transporte" "financiamento" \\
        "evasão" "bilhetagem" "integração tarifária" "concessão" "permissão"

    # ou, para rodar de novo as 4 já executadas (conferência):
    python3 rsl2_antp_biblioteca_scraper.py --out conferencia.csv \\
        "tarifa zero" "gratuidade" "tarifa social" "passe livre"

Cada expressão é rodada isoladamente (não uma OR de todas — é assim que o
formulário original funciona, um `ddcKeywords` por consulta). O script pagina
até `pages.total`, deduplica por `link` (uma obra pode bater por mais de uma
expressão — a coluna `expressoes` registra todas as que a recuperaram) e grava
um CSV com `;` como separador, sem BOM, LF — no formato dos demais candidatos
da RSL (mesmo padrão do `corpus_rsl.csv`).

LIMITE HONESTO
--------------
Isto varre por ASSUNTO (a Frente A). NÃO substitui a varredura por Seção
(Frentes B/C, já feitas) nem invalida a regra já registrada de que as duas são
complementares — um item pode estar numa e não na outra (caso A34, RSL2
Frente A original). Rodar este script cobre o recall que faltava, não troca o
procedimento.

Nenhuma linha aqui entra em `corpus_rsl.csv` sem leitura e sem passar pela
regra de corte do núcleo duro (ver [[RSL2 — regra de corte e nucleo duro
(07-09-2026)]]): o que tratar do objeto (Tarifa Zero/gratuidade/isenção
tarifária) vai ao corpus; o resto vai a `fonte_documental` ou é descartado
como ruído, exatamente como já decidido para as 4 expressões executadas em
06/09.
"""

import argparse
import csv
import sys
import time
import unicodedata
from urllib.parse import urlencode
from urllib.request import urlopen, Request
import json

BASE = "https://antp.org.br/_datasource/biblioteca/search/"
USER_AGENT = "Mozilla/5.0 (compatible; RSL-PGT092-research-script/1.0; +pesquisa academica UFABC)"
SLEEP_BETWEEN_REQUESTS = 1.0  # segundos — ser gentil com um site de associação pequena, não do porte da SciELO/CAPES


def fetch_page(keyword, page, dgp_code="", dct_code=""):
    params = {
        "ddcKeywords": keyword,
        "ddcAutor": "",
        "ddcDate_from": "",   # NUNCA preencher — ver docstring
        "ddcDate_to": "",     # idem
        "dgpCode": dgp_code,
        "dctCode": dct_code,
        "sqlPage": page,
    }
    url = BASE + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all(keyword, dgp_code="", dct_code=""):
    """Pagina uma expressão até o fim e devolve a lista de registros."""
    records = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        data = fetch_page(keyword, page, dgp_code, dct_code)
        total_pages = int(data.get("pages", {}).get("total", 1) or 1)
        for rec in data.get("recordset", []):
            records.append({
                "title": (rec.get("title") or "").strip(),
                "group": (rec.get("group") or "").strip(),
                "category": (rec.get("category") or "").strip(),
                "link": (rec.get("link") or "").strip(),
                "description": " ".join((rec.get("description") or "").split()),
            })
        page += 1
        if page <= total_pages:
            time.sleep(SLEEP_BETWEEN_REQUESTS)
    return records


def clean_text(s):
    """Normaliza para comparação (dedupe por título quando não há link)."""
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def main():
    global SLEEP_BETWEEN_REQUESTS

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("keywords", nargs="+", help="expressões a rodar, uma consulta por expressão")
    ap.add_argument("--out", required=True, help="CSV de saída")
    ap.add_argument("--dgp-code", default="", help="restringir a um grupo/seção (keyCode); vazio = todas as seções")
    ap.add_argument("--sleep", type=float, default=SLEEP_BETWEEN_REQUESTS, help="segundos entre páginas (padrão 1.0)")
    args = ap.parse_args()

    SLEEP_BETWEEN_REQUESTS = args.sleep

    by_key = {}  # link (ou título normalizado, se sem link) -> registro consolidado
    for kw in args.keywords:
        sys.stderr.write(f"[rsl2-antp] buscando: {kw!r}\n")
        try:
            recs = fetch_all(kw, dgp_code=args.dgp_code)
        except Exception as e:
            sys.stderr.write(f"[rsl2-antp] ERRO em {kw!r}: {e}\n")
            continue
        sys.stderr.write(f"[rsl2-antp]   {len(recs)} resultado(s)\n")
        for rec in recs:
            key = rec["link"] or clean_text(rec["title"])
            if key not in by_key:
                by_key[key] = dict(rec, expressoes=[kw])
            elif kw not in by_key[key]["expressoes"]:
                by_key[key]["expressoes"].append(kw)
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    rows = list(by_key.values())
    sys.stderr.write(f"[rsl2-antp] total único (deduplicado por link/título): {len(rows)}\n")

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["expressoes", "titulo", "grupo", "categoria", "link", "descricao"])
        for r in rows:
            writer.writerow(["|".join(r["expressoes"]), r["title"], r["group"], r["category"], r["link"], r["description"]])

    sys.stderr.write(f"[rsl2-antp] gravado em {args.out}\n")


if __name__ == "__main__":
    main()
