#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ler_normas_arturnogueira.py — lê o conteúdo real das normas cadastradas no
SAPL de Artur Nogueira/SP, para checar se alguma trata de tarifa/transporte.

CONTEXTO
  A base canônica (`base_legislacao_contratos_175 (v3).csv`) tem Artur
  Nogueira/SP marcado como "não localizada (indício de que não existe —
  busca SAPL negativa)", com a conclusão de que o programa "Catraca Livre"
  (desde 2021) nunca passou pela Câmara — foi instituído por decreto ou ato
  administrativo do Executivo, sem tramitação legislativa.

  Na sondagem de domínio de 11/09/2026 (grafia oficial "Artur", sem H — o
  descobridor original testou "Arthur" e por isso não achou), confirmei que
  `sapl.arturnogueira.sp.leg.br` tem API SAPL funcionando **com normas
  cadastradas**. Isso contradiz "busca SAPL negativa" — mas não decide se a
  base está errada: a câmara pode simplesmente ter outras normas no SAPL
  (pauta normal) sem nenhuma relação com "Catraca Livre". Este script lê o
  conteúdo (tipo, número, ano, ementa) de cada norma cadastrada e sinaliza
  as que batem com palavras-chave de transporte/tarifa/gratuidade, para
  decidir com evidência, não com a mera existência da API.

  ⚠️ RODAR NA SUA MÁQUINA — mesmo motivo dos outros scripts desta pasta: o
  proxy de saída do ambiente de nuvem bloqueia este domínio.

USO
  python ler_normas_arturnogueira.py
  python ler_normas_arturnogueira.py --saida arturnogueira_normas.csv

SAÍDA
  Uma linha por norma no console (com marca 🎯 nas que batem palavra-chave
  de transporte/tarifa), e um CSV com tipo, número, ano, data, ementa e se
  bateu palavra-chave. Segue a paginação até o fim (o formato de paginação
  alternativo — `{"pagination":{"links":{"next":...}}}` — já documentado
  em sondagem_dominios_alternativos.py).

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof. Dra. Silvana Zioni
"""

import argparse
import csv
import sys

import requests

HOST = "sapl.arturnogueira.sp.leg.br"
PALAVRAS_CHAVE = [
    "tarifa", "gratuid", "passe livre", "catraca", "transporte coletivo",
    "transporte público", "passagem", "ônibus", "onibus", "subsídio",
    "subsidio", "concessão", "concessao", "operador",
]


def bate_palavra_chave(ementa: str) -> str:
    e = (ementa or "").lower()
    achadas = [p for p in PALAVRAS_CHAVE if p in e]
    return ", ".join(achadas)


def coletar(contato: str, timeout: int = 15):
    headers = {"User-Agent": f"pesquisa-doutorado-tarifazero ({contato})"}
    url = f"https://{HOST}/api/norma/normajuridica/?page=1"
    normas = []
    pagina = 1
    while url:
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()
        dados = r.json()
        resultados = dados.get("results", [])
        if not resultados and "pagination" in dados:
            # formato de paginação alternativo — resultados podem vir sob outra chave
            resultados = dados.get("results") or dados.get("normas") or []
        print(f"Página {pagina}: {len(resultados)} normas.")
        normas.extend(resultados)
        # próxima página, nos dois formatos de paginação já vistos
        prox = None
        if isinstance(dados.get("next"), str):
            prox = dados["next"]
        elif isinstance(dados.get("pagination"), dict):
            links = dados["pagination"].get("links", {})
            prox = links.get("next")
        url = prox
        pagina += 1
        if pagina > 200:  # cinto de segurança contra paginação em loop
            print("⚠️ Parando em 200 páginas — cinto de segurança.")
            break
    return normas


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--saida", default="arturnogueira_normas.csv")
    ap.add_argument("--contato", default="thiago@poloplanejamento.com")
    args = ap.parse_args()

    try:
        normas = coletar(args.contato)
    except Exception as e:
        print(f"ERRO ao coletar: {e}")
        return 1

    linhas = []
    for n in normas:
        tipo = n.get("tipo") or n.get("tipo_norma") or n.get("tipo_norma_display") or ""
        numero = n.get("numero", "")
        ano = n.get("ano", "")
        data = n.get("data") or n.get("data_publicacao") or ""
        ementa = n.get("ementa", "") or ""
        chave = bate_palavra_chave(ementa)
        marca = "🎯" if chave else "  "
        print(f"{marca} {tipo} {numero}/{ano} ({data}) — {ementa[:140]}")
        linhas.append([tipo, numero, ano, data, ementa, chave])

    with open(args.saida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tipo", "numero", "ano", "data", "ementa", "palavras_chave_batidas"])
        w.writerows(linhas)

    relevantes = [l for l in linhas if l[5]]
    print(f"\nTotal de normas lidas: {len(linhas)}")
    print(f"Salvo em {args.saida}")
    print(f"{len(relevantes)} normas batem alguma palavra-chave de transporte/tarifa.")
    if relevantes:
        print("Confira estas primeiro:")
        for tipo, numero, ano, data, ementa, chave in relevantes:
            print(f"  {tipo} {numero}/{ano} — chave: {chave}")
    else:
        print("Nenhuma bateu — reforça (não prova) que o SAPL não tem norma de TZ cadastrada.")


if __name__ == "__main__":
    sys.exit(main())
