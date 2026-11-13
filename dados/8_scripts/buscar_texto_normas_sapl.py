#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buscar_texto_normas_sapl.py — busca no SAPL da Câmara o texto completo das
normas de Tarifa Zero achadas em 11/09/2026 pelo cruzamento PlanMob × TPC ×
TZ, para os 23 municípios em que essa busca achou uma lei/decreto concreto
(número e ano) e que ainda não têm o texto completo arquivado no cofre.

CONTEXTO
  `Tabela cruzada - PlanMob x Legislação TPC x TZ (SAPL) (11-09-2026).xlsx`
  achou, por busca direta no SAPL de cada câmara, a lei-base da TZ em 23 dos
  39 municípios do cruzamento (os outros 16 não acharam nada, ver a ficha de
  cada um). Isso já está registrado nas fichas municipais (bloco "Cruzamento
  SAPL"), mas só com o NÚMERO da norma — o texto completo (para citar na
  tese, conferir vínculo com TZ, e alimentar `normas_padronizadas`) ainda
  não foi buscado.

  13 desses 23 municípios não têm NENHUMA norma no corpus
  `normas_padronizadas` ainda. Outros 9 já têm alguma norma documentada,
  mas em pelo menos um caso (Eusébio/CE) o número documentado (960) é
  DIFERENTE do achado pelo cruzamento (1.024) — a norma certa pode não ser
  a que já está arquivada. Por isso o script busca os 23, não só os 13.

  ⚠️ RODAR NA SUA MÁQUINA — mesmo motivo dos scripts anteriores desta pasta:
  o proxy de saída do ambiente de nuvem bloqueia estes domínios.

O QUE O SCRIPT FAZ
  1. Para cada município, baixa a lista completa de normas do SAPL (mesma
     paginação de dois formatos já documentada em
     `ler_normas_arturnogueira.py`).
  2. Casa por NÚMERO e ANO (não por tipo — o cruzamento às vezes registrou
     "Lei" onde o SAPL classifica como "Lei Ordinária" etc.).
  3. Quando acha, pega o detalhe da norma (endpoint singular) e IMPRIME
     todas as chaves do JSON — este script não pressupõe qual campo do SAPL
     tem o texto integral (isso varia entre instalações), então mostra tudo
     para eu decidir o próximo passo com base no que existe de verdade.
  4. Tenta detectar automaticamente um campo que pareça um arquivo (URL ou
     caminho terminando em .pdf/.doc/.docx, ou começando com /media/) e
     baixa esse arquivo para a subpasta de saída.
  5. Sinaliza (🎯/·) se a ementa da norma casada bate com palavras-chave de
     transporte/tarifa — não decide sozinho, só ajuda a triar.

SAÍDA (pasta --saida, padrão "saida_normas_sapl/")
  - Um `.json` por norma encontrada com o detalhe completo (para eu revisar
    os campos disponíveis).
  - Um arquivo baixado por norma quando um campo de arquivo foi detectado
    (nome: "<Município>-<UF> - <tipo> <numero>-<ano>.<ext>").
  - `resumo.csv`: município, uf, tipo, numero, ano, achou?, id_sapl,
    ementa, bate_palavra_chave?, arquivo_baixado?, campos_disponiveis.

USO
  python buscar_texto_normas_sapl.py
  python buscar_texto_normas_sapl.py --saida "saida_normas_sapl"
  python buscar_texto_normas_sapl.py --filtro "Eusébio,Palmas"   # sondagem parcial

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof. Dra. Silvana Zioni
"""

import argparse
import csv
import json
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

import requests

PALAVRAS_CHAVE = [
    "tarifa", "gratuid", "passe livre", "catraca", "transporte coletivo",
    "transporte público", "passagem", "ônibus", "onibus", "subsídio",
    "subsidio", "concessão", "concessao", "operador", "busão", "busao",
]

# (município, uf, host) -> lista de (tipo esperado, número, ano) a buscar.
# Curado à mão a partir do texto do cruzamento de 11/09/2026 — não por regex
# automática, porque as citações vêm em formatos muito distintos entre
# municípios (ver Cap "Becker": não confundir dado extraído automaticamente
# com o dado revisado). Tipo é só orientativo — o casamento é por número+ano.
ALVOS = [
    ("Mata de São João", "BA", "sapl.matadesaojoao.ba.leg.br", [("Lei", "945", "2023")]),
    ("Aquiraz", "CE", "sapl.aquiraz.ce.leg.br", [("Lei", "1279", "2018")]),
    ("Eusébio", "CE", "sapl.eusebio.ce.leg.br", [("Lei", "1024", "2011")]),
    ("Formosa", "GO", "sapl.formosa.go.leg.br", [("Lei", "650", "2021")]),
    ("Luziânia", "GO", "sapl.luziania.go.leg.br", [("Lei", "4595", "2023")]),
    ("Ijaci", "MG", "sapl.ijaci.mg.leg.br", [("Lei", "1511", "2025")]),
    ("Itatiaiuçu", "MG", "sapl.itatiaiucu.mg.leg.br", [("Lei", "1179", "2019")]),
    ("Lagoa da Prata", "MG", "sapl.lagoadaprata.mg.leg.br", [
        ("Lei", "384", "1989"), ("Lei", "2399", "2015"), ("Lei", "2470", "2015"),
        ("Lei", "2740", "2016"), ("Lei", "2784", "2016"),
    ]),
    ("Piumhi", "MG", "sapl.piumhi.mg.leg.br", [("Lei", "2709", "2023")]),
    ("Santana do Deserto", "MG", "sapl.santanadodeserto.mg.leg.br", [
        ("Decreto", "2999", "2021"), ("Lei", "1151", "2020"),
    ]),
    ("Sarzedo", "MG", "sapl.sarzedo.mg.leg.br", [("Lei", "934", "2023")]),
    ("Ribas do Rio Pardo", "MS", "sapl.ribasdoriopardo.ms.leg.br", [("Lei", "1355", "2023")]),
    ("Carambeí", "PR", "sapl.carambei.pr.leg.br", [("Lei", "1467", "2023")]),
    ("Irati", "PR", "sapl.irati.pr.leg.br", [("Lei", "5240", "2025")]),
    ("Ivaiporã", "PR", "sapl.ivaipora.pr.leg.br", [("Lei", "1141", "2001")]),
    ("Cantagalo", "RJ", "sapl.cantagalo.rj.leg.br", [("Lei", "2007", "2026")]),
    ("Cacoal", "RO", "sapl.cacoal.ro.leg.br", [("Lei", "5149", "2023")]),
    ("Vilhena", "RO", "sapl.vilhena.ro.leg.br", [("Lei", "6557", "2025")]),
    ("Ilha Comprida", "SP", "sapl.ilhacomprida.sp.leg.br", [("Lei", "2250", "2025")]),
    ("Monte Mor", "SP", "sapl.montemor.sp.leg.br", [("Lei", "3157", "2023")]),
    ("Piedade", "SP", "sapl.piedade.sp.leg.br", [("Decreto", "8970", "2022")]),
    ("Porto Feliz", "SP", "sapl.portofeliz.sp.leg.br", [("Lei", "5856", "2022")]),
    ("Palmas", "TO", "sapl.palmas.to.leg.br", [("Decreto", "2320", "2023"), ("Decreto", "2321", "2023")]),
]


def normalizar(txt):
    return "".join(
        c for c in unicodedata.normalize("NFKD", txt or "") if not unicodedata.combining(c)
    ).lower()


def bate_palavra_chave(ementa):
    e = (ementa or "").lower()
    achadas = [p for p in PALAVRAS_CHAVE if p in e]
    return ", ".join(achadas)


def listar_normas(host, contato, timeout=15):
    headers = {"User-Agent": f"pesquisa-doutorado-tarifazero ({contato})"}
    url = f"https://{host}/api/norma/normajuridica/?page=1"
    normas, pagina = [], 1
    while url:
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()
        dados = r.json()
        resultados = dados.get("results", [])
        normas.extend(resultados)
        prox = None
        if isinstance(dados.get("next"), str):
            prox = dados["next"]
        elif isinstance(dados.get("pagination"), dict):
            prox = dados["pagination"].get("links", {}).get("next")
        url = prox
        pagina += 1
        if pagina > 200:
            print("  ⚠️ parando em 200 páginas — cinto de segurança.")
            break
    return normas


def numero_bate(numero_api, numero_alvo):
    def limpar(s):
        return str(s).replace(".", "").lstrip("0") or "0"
    return limpar(numero_api) == limpar(numero_alvo)


def detectar_campo_arquivo(detalhe):
    """Procura no JSON de detalhe algo que pareça um arquivo para baixar.
    Não pressupõe o nome do campo — varre valores string do dicionário."""
    for chave, valor in detalhe.items():
        if isinstance(valor, str):
            v = valor.lower()
            if v.startswith("/media/") or v.startswith("http") and any(
                v.endswith(ext) for ext in (".pdf", ".doc", ".docx", ".odt")
            ):
                return chave, valor
            if any(v.endswith(ext) for ext in (".pdf", ".doc", ".docx", ".odt")):
                return chave, valor
    return None, None


def processar_municipio(municipio, uf, host, alvos, contato, pasta_saida, linhas_resumo):
    print(f"\n=== {municipio}/{uf} ({host}) ===")
    try:
        normas = listar_normas(host, contato)
    except Exception as e:
        print(f"  🔴 ERRO ao listar normas: {e}")
        for tipo, numero, ano in alvos:
            linhas_resumo.append([municipio, uf, tipo, numero, ano, "ERRO_LISTA", "", "", "", "", str(e)])
        return
    print(f"  {len(normas)} normas no SAPL.")

    for tipo, numero, ano in alvos:
        candidatos = [
            n for n in normas
            if numero_bate(n.get("numero", ""), numero) and str(n.get("ano", "")) == str(ano)
        ]
        if not candidatos:
            print(f"  ❌ não achei {tipo} {numero}/{ano}")
            linhas_resumo.append([municipio, uf, tipo, numero, ano, "NAO_ACHOU", "", "", "", "", ""])
            continue
        for norma in candidatos:
            norma_id = norma.get("id")
            ementa = norma.get("ementa", "")
            chave = bate_palavra_chave(ementa)
            marca = "🎯" if chave else "· "
            print(f"  {marca} achei id={norma_id} — {norma.get('tipo', tipo)} {numero}/{ano} — {ementa[:100]}")

            detalhe = dict(norma)
            campos_disponiveis = ""
            arquivo_baixado = ""
            if norma_id is not None:
                try:
                    r = requests.get(
                        f"https://{host}/api/norma/normajuridica/{norma_id}/",
                        timeout=15, headers={"User-Agent": f"pesquisa-doutorado-tarifazero ({contato})"},
                    )
                    r.raise_for_status()
                    detalhe = r.json()
                except Exception as e:
                    print(f"     ⚠️ não consegui pegar o detalhe (fico só com o resumo da lista): {e}")

            campos_disponiveis = ", ".join(sorted(detalhe.keys()))
            pasta_muni = pasta_saida / f"{municipio}-{uf}"
            pasta_muni.mkdir(parents=True, exist_ok=True)
            nome_base = f"{municipio}-{uf} - {tipo} {numero}-{ano}"
            with open(pasta_muni / f"{nome_base}.json", "w", encoding="utf-8", newline="\n") as f:
                json.dump(detalhe, f, ensure_ascii=False, indent=2)

            campo_arquivo, valor_arquivo = detectar_campo_arquivo(detalhe)
            if campo_arquivo:
                url_arquivo = urljoin(f"https://{host}/", valor_arquivo)
                ext = valor_arquivo.rsplit(".", 1)[-1].split("?")[0][:5]
                try:
                    r = requests.get(url_arquivo, timeout=30, headers={"User-Agent": f"pesquisa-doutorado-tarifazero ({contato})"})
                    r.raise_for_status()
                    caminho_arquivo = pasta_muni / f"{nome_base}.{ext}"
                    caminho_arquivo.write_bytes(r.content)
                    arquivo_baixado = str(caminho_arquivo)
                    print(f"     📄 arquivo baixado ({campo_arquivo}): {caminho_arquivo}")
                except Exception as e:
                    print(f"     ⚠️ achei campo de arquivo ({campo_arquivo}) mas não consegui baixar: {e}")
            else:
                print(f"     ℹ️ nenhum campo parece um arquivo — ver o .json para decidir (campos: {campos_disponiveis[:200]})")

            linhas_resumo.append([
                municipio, uf, tipo, numero, ano, "ACHOU", norma_id, ementa, chave,
                arquivo_baixado, campos_disponiveis,
            ])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--saida", default="saida_normas_sapl")
    ap.add_argument("--contato", default="thiago@poloplanejamento.com")
    ap.add_argument("--filtro", default=None, help="substrings de município, separadas por vírgula")
    args = ap.parse_args()

    pasta_saida = Path(args.saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    alvos = ALVOS
    if args.filtro:
        termos = [normalizar(t.strip()) for t in args.filtro.split(",")]
        alvos = [a for a in alvos if any(t in normalizar(a[0]) for t in termos)]
        if not alvos:
            print("Filtro não bateu com nenhum município da lista.")
            return 1

    linhas_resumo = []
    for municipio, uf, host, lista_alvos in alvos:
        processar_municipio(municipio, uf, host, lista_alvos, args.contato, pasta_saida, linhas_resumo)

    caminho_resumo = pasta_saida / "resumo.csv"
    with open(caminho_resumo, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["municipio", "uf", "tipo", "numero", "ano", "status", "id_sapl", "ementa",
                    "bate_palavra_chave", "arquivo_baixado", "campos_disponiveis"])
        w.writerows(linhas_resumo)

    achou = sum(1 for l in linhas_resumo if l[5] == "ACHOU")
    baixou = sum(1 for l in linhas_resumo if l[9])
    print(f"\n=== Resumo: {achou}/{len(linhas_resumo)} normas achadas · {baixou} arquivos baixados ===")
    print(f"Detalhe em {caminho_resumo} e um .json por norma em {pasta_saida}/<Município-UF>/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
