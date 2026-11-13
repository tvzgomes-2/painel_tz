#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buscar_alternativos_sem_indicio.py — para os municípios classificados
"C · nada localizado" (nenhuma pista de norma de Tarifa Zero), tenta dois
caminhos alternativos automatizáveis: (1) varredura por palavra-chave na
ementa de TODAS as normas do SAPL da câmara — o mesmo método que resolveu
Artur Nogueira em 11/09/2026, generalizado para quem ainda não tem número
de lei nenhum; (2) a página do município no leismunicipais.com.br.

CONTEXTO
  O `Controle unico - legislacao PlanMob e contratos, 176 casos` classifica
  63 dos 176 casos como "C · nada localizado". O playbook já registrado no
  cofre para esses casos (`onde_buscar`, no Estado da legislação v4) é:
  "leismunicipais → SAPL → e-SIC à Câmara; imprensa para casos recentes".
  Este script automatiza os dois primeiros passos.

  De 63 "C", só 7 foram efetivamente CONSULTADOS até agora por algum método
  registrado (6 pelo cruzamento SAPL de 11/09, sem achar nada + 1, Piumhi,
  que na verdade achou — sai da lista "C"; mais 7 por busca geral em
  07/09/2026, também sem achar nada). Os outros 49 nunca foram tocados.
  Este script varre os 62 "C" restantes (todos, exceto Piumhi).

  ⚠️ ACHADO IMPORTANTE deste levantamento: em pelo menos 4 municípios
  (Dores do Indaiá/MG, Clevelândia/PR, Quatro Barras/PR, Rio Branco do
  Sul/PR) o cruzamento de 11/09 disse "não encontrei" a lei de TZ via
  busca por NÚMERO — mas a base já tem, desde antes, o texto completo lido
  e claramente sobre TZ (ex.: Clevelândia — Decreto nº 79/2023, "Institui
  e regulamenta o serviço de transporte coletivo urbano, gratuito,
  denominado PASSE LIVRE"). Ou seja, a busca por número do cruzamento tem
  falsos negativos — não decidir "sem indício" só com base nela. Por isso
  este script busca por PALAVRA-CHAVE na ementa (varredura completa), não
  por número — é mais lento, mas não depende de já saber o número certo.

  ⚠️ RODAR NA SUA MÁQUINA — mesmo motivo dos scripts anteriores desta
  pasta: o proxy de saída do ambiente de nuvem bloqueia estes domínios.

O QUE O SCRIPT FAZ
  1. Lê a lista de municípios "C" diretamente do arquivo único do cofre
     (não hardcoded — se a classificação mudar, o script acompanha).
  2. Para cada um, deriva o host do SAPL a partir de `url_sapl_provavel`
     (Estado da legislação v4) e faz a MESMA varredura completa por
     palavra-chave na ementa que resolveu Artur Nogueira — não busca por
     número, porque para estes municípios não temos número nenhum ainda.
  3. Em paralelo, tenta abrir a página do leismunicipais.com.br
     (`url_leismunicipais`) e detecta se caiu em paywall (heurística: falta
     de marcadores de conteúdo normativo como "Art." / "CONSIDERANDO" /
     "Câmara Municipal" no HTML, ou presença de marcadores de assinatura
     como "assine" / "cadastre-se" / "conteúdo completo para assinantes").
  4. NÃO decide por conta própria se um achado é a norma de TZ — só marca
     🎯 quando a ementa bate alguma palavra-chave, para eu revisar.

SAÍDA (pasta --saida, padrão "saida_alternativos/")
  - `resumo.csv`: município, uf, sapl_alcancavel, sapl_n_normas,
    sapl_achados (ementas que bateram palavra-chave, até 3, com id),
    leismunicipais_alcancavel, leismunicipais_parece_paywall,
    leismunicipais_trecho_relevante.
  - Um `.json` por município com TODAS as normas cujo ementa bateu alguma
    palavra-chave (não só a primeira) — para eu revisar sem perder achado.

USO
  python buscar_alternativos_sem_indicio.py
  python buscar_alternativos_sem_indicio.py --filtro "Anicuns,Arcos"
  python buscar_alternativos_sem_indicio.py --pular-leismunicipais   # só SAPL, mais rápido

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof. Dra. Silvana Zioni
"""

import argparse
import csv
import json
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

PASTA_DADOS = Path(__file__).resolve().parent.parent.parent / "03 - Dados" / "_data" / "Legislacao e contratos TZ"
ARQ_CONTROLE = "_historico/Controle unico - legislacao PlanMob e contratos, 176 casos (2026-09-11).csv"
ARQ_ESTADO = "_historico/Estado da legislacao - 176 casos (v4, 09-09-2026).csv"

PALAVRAS_CHAVE = [
    "tarifa", "gratuid", "passe livre", "catraca", "transporte coletivo",
    "transporte público", "transporte publico", "passagem", "ônibus", "onibus",
    "subsídio", "subsidio", "concessão", "concessao", "operador", "busão", "busao",
    "mobilidade gratuita", "passe social",
]

MARCADORES_PAYWALL = [
    "assine", "cadastre-se", "conteúdo completo para assinantes",
    "conteudo completo para assinantes", "faça login", "faca login", "planos e preços",
]
MARCADORES_CONTEUDO_NORMATIVO = [
    "art.", "considerando", "câmara municipal", "camara municipal", "prefeito municipal",
    "publicado no", "diário oficial", "diario oficial",
]


def normalizar(txt):
    return "".join(
        c for c in unicodedata.normalize("NFKD", txt or "") if not unicodedata.combining(c)
    ).lower()


def bate_palavra_chave(ementa):
    e = (ementa or "").lower()
    return [p for p in PALAVRAS_CHAVE if p in e]


def carregar(nome):
    caminho = PASTA_DADOS / nome
    with open(caminho, encoding="utf-8-sig") as f:
        primeira = f.readline()
    sep = ";" if primeira.count(";") > primeira.count(",") else ","
    return pd.read_csv(caminho, sep=sep, encoding="utf-8-sig", dtype=str)


def montar_alvos():
    controle = carregar(ARQ_CONTROLE)
    estado = carregar(ARQ_ESTADO)
    c = controle[controle["estado"].str.startswith("C", na=False)].copy()
    # Piumhi já achou número via cruzamento SAPL de 11/09 — não é mais "sem indício"
    c = c[~((c.municipio.str.strip() == "Piumhi") & (c.uf.str.strip() == "MG"))]
    estado["municipio_norm"] = estado.municipio.str.strip()
    estado["uf_norm"] = estado.uf.str.strip()
    alvos = []
    for _, row in c.iterrows():
        m, u = row["municipio"].strip(), row["uf"].strip()
        er = estado[(estado.municipio_norm == m) & (estado.uf_norm == u)]
        url_sapl = url_leis = None
        if len(er):
            url_sapl = er.iloc[0].get("url_sapl_provavel")
            url_leis = er.iloc[0].get("url_leismunicipais")
        alvos.append({"municipio": m, "uf": u, "url_sapl": url_sapl, "url_leis": url_leis})
    return alvos


def host_do_sapl(url_sapl):
    if not url_sapl or pd.isna(url_sapl):
        return None
    return urlparse(url_sapl).netloc


def varrer_sapl(host, contato, timeout=15):
    headers = {"User-Agent": f"pesquisa-doutorado-tarifazero ({contato})"}
    url = f"https://{host}/api/norma/normajuridica/?page=1"
    normas, pagina = [], 1
    while url:
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()
        dados = r.json()
        normas.extend(dados.get("results", []))
        prox = None
        if isinstance(dados.get("next"), str):
            prox = dados["next"]
        elif isinstance(dados.get("pagination"), dict):
            prox = dados["pagination"].get("links", {}).get("next")
        url = prox
        pagina += 1
        if pagina > 200:
            break
    return normas


def checar_leismunicipais(url, contato, timeout=15):
    if not url or (isinstance(url, float)):
        return {"alcancavel": False, "parece_paywall": None, "trecho_relevante": ""}
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": f"pesquisa-doutorado-tarifazero ({contato})"})
        texto = r.text.lower()
    except Exception as e:
        return {"alcancavel": False, "parece_paywall": None, "trecho_relevante": f"erro: {e}"}
    if r.status_code != 200:
        return {"alcancavel": False, "parece_paywall": None, "trecho_relevante": f"HTTP {r.status_code}"}
    tem_paywall = any(m in texto for m in MARCADORES_PAYWALL)
    tem_conteudo = any(m in texto for m in MARCADORES_CONTEUDO_NORMATIVO)
    achados = bate_palavra_chave(texto)
    trecho = ""
    if achados:
        i = texto.find(achados[0])
        trecho = texto[max(0, i - 80): i + 120].replace("\n", " ")
    return {
        "alcancavel": True,
        "parece_paywall": tem_paywall and not tem_conteudo,
        "trecho_relevante": trecho,
        "palavras_batidas": ", ".join(achados),
    }


def processar(alvo, contato, pasta_saida, pular_leismunicipais, linhas_resumo):
    municipio, uf = alvo["municipio"], alvo["uf"]
    print(f"\n=== {municipio}/{uf} ===")
    host = host_do_sapl(alvo["url_sapl"])
    sapl_alcancavel = False
    sapl_n_normas = 0
    achados_sapl = []
    if host:
        try:
            normas = varrer_sapl(host, contato)
            sapl_alcancavel = True
            sapl_n_normas = len(normas)
            for n in normas:
                chave = bate_palavra_chave(n.get("ementa", ""))
                if chave:
                    achados_sapl.append({
                        "id": n.get("id"), "tipo": n.get("tipo"), "numero": n.get("numero"),
                        "ano": n.get("ano"), "ementa": n.get("ementa"), "palavras": chave,
                    })
            print(f"  SAPL ({host}): {sapl_n_normas} normas, {len(achados_sapl)} bateram palavra-chave.")
        except Exception as e:
            print(f"  SAPL ({host}): 🔴 erro — {e}")
    else:
        print("  SAPL: sem host provável registrado.")

    leis_info = {"alcancavel": False, "parece_paywall": None, "trecho_relevante": "", "palavras_batidas": ""}
    if not pular_leismunicipais:
        leis_info = checar_leismunicipais(alvo["url_leis"], contato)
        estado_txt = "paywall" if leis_info["parece_paywall"] else ("ok" if leis_info["alcancavel"] else "inalcançável")
        print(f"  leismunicipais: {estado_txt}" + (f" — bateu: {leis_info.get('palavras_batidas')}" if leis_info.get("palavras_batidas") else ""))

    if achados_sapl:
        pasta_muni = pasta_saida / f"{municipio}-{uf}"
        pasta_muni.mkdir(parents=True, exist_ok=True)
        with open(pasta_muni / "achados_sapl_por_palavra_chave.json", "w", encoding="utf-8", newline="\n") as f:
            json.dump(achados_sapl, f, ensure_ascii=False, indent=2)

    linhas_resumo.append([
        municipio, uf, sapl_alcancavel, sapl_n_normas,
        "; ".join(f"id={a['id']} {a['tipo']} {a['numero']}/{a['ano']}" for a in achados_sapl[:3]),
        leis_info["alcancavel"], leis_info["parece_paywall"], leis_info.get("trecho_relevante", ""),
    ])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--saida", default="saida_alternativos")
    ap.add_argument("--contato", default="thiago@poloplanejamento.com")
    ap.add_argument("--filtro", default=None, help="substrings de município, separadas por vírgula")
    ap.add_argument("--pular-leismunicipais", action="store_true")
    args = ap.parse_args()

    pasta_saida = Path(args.saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    alvos = montar_alvos()
    print(f"{len(alvos)} municípios 'C · nada localizado' a varrer.")

    if args.filtro:
        termos = [normalizar(t.strip()) for t in args.filtro.split(",")]
        alvos = [a for a in alvos if any(t in normalizar(a["municipio"]) for t in termos)]
        if not alvos:
            print("Filtro não bateu com nenhum município.")
            return 1
        print(f"Filtrado para {len(alvos)}.")

    linhas_resumo = []
    for alvo in alvos:
        processar(alvo, args.contato, pasta_saida, args.pular_leismunicipais, linhas_resumo)
        time.sleep(0.3)

    caminho_resumo = pasta_saida / "resumo.csv"
    with open(caminho_resumo, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["municipio", "uf", "sapl_alcancavel", "sapl_n_normas", "sapl_achados_top3",
                    "leismunicipais_alcancavel", "leismunicipais_parece_paywall", "leismunicipais_trecho"])
        w.writerows(linhas_resumo)

    n_com_achado = sum(1 for l in linhas_resumo if l[4])
    print(f"\n=== Resumo: {n_com_achado}/{len(linhas_resumo)} municípios com algum achado por palavra-chave no SAPL ===")
    print(f"Detalhe em {caminho_resumo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
