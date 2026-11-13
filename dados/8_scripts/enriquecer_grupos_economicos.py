#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""enriquecer_grupos_economicos.py — escreve o bloco
"## Grupos econômicos (Cap 7) — dados do BD CNPJ" nas fichas municipais que
ainda NÃO o têm, a partir das bases de CNPJ do cofre.

======================================================================
POR QUE ESTE SCRIPT EXISTE
======================================================================
Era o último bloco de ficha SEM gerador. Os blocos com script estavam em 272 de
272 fichas; este, em 201 — faltava em 71. Bloco sem script e bloco que ficha
nova nasce sem sao a mesma coisa, e foi o que produziu a lacuna.

======================================================================
FONTES — as tres, conferidas contra fichas ja escritas
======================================================================
1. `confianca_nucleo_por_municipio.csv` (3.405 municipios)
     -> nivel_confianca, escore_confianca, n_cnpj_nucleo
2. `estabelecimentos_por_municipio_6cnaes.csv` (5.369 municipios)
     -> n_estab_ativos_nucleo  (nucleo = CNAE 4921301 + 4921302)
3. `painel TZ/scripts/grupos_por_municipio.json` (796 municipios)
     -> [[nome do grupo, GE-id], ...]

Validacao feita antes de escrever: reproduzidos os numeros de 170 fichas que ja
tinham o bloco. Ibate 5 estabelecimentos, Canoas 15, escore/nivel batendo.

======================================================================
⚠️ O QUE ESTE SCRIPT NAO ESCREVE, E POR QUE
======================================================================
* **"Validacao do operador"** — a linha existe nas fichas antigas citando uma
  "amostra de validacao operador x CNPJ (51 municipios)". Essa amostra NAO esta
  em arquivo nenhum do cofre: o texto so existe dentro das proprias fichas. Sem
  fonte, a linha nao e gerada — escrever "nao avaliado" para todo mundo seria
  inventar um universo de validacao que nao se pode conferir.
* **Municipio ausente das bases** vira "nao medido", nunca zero. Ausencia de
  medida nao e medida de ausencia (NA != 0) — a mesma regra que tirou o OSM das
  fichas em 16/09/2026.
* **Fichas que JA tem o bloco nao sao tocadas.** Inclui as duas variantes
  escritas a mao (Araraquara e Vicosa), que trazem analise do autor.

======================================================================
⚠️ A RESSALVA DO n_ge VAI DENTRO DO BLOCO, NAO NO RODAPE
======================================================================
A auditoria de 09/09/2026 mostrou que o cruzamento municipio x grupo mede
ENDERECO DE ESTABELECIMENTO, nao operacao urbana: em Araraquara atribuia 4
grupos, dos quais so 1 e operador urbano (um e rodoviario, dois sao
garagem/agencia ja refutados), e faltava o GE-005, socio do consorcio desde
2016. Por isso o bloco gerado diz isso na propria linha do grupo, e nao numa
nota de rodape que o leitor pula.

USO
  python enriquecer_grupos_economicos.py            # simula
  python enriquecer_grupos_economicos.py --gravar   # grava, com backup
"""
import argparse
import csv
import datetime
import json
import os
import re
import shutil
import sys

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
FDIR = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Fichas por município")
CNPJ = os.path.join(RAIZ, "03 - Dados", "_data", "CNPJ",
                    "filtrados (6 CNAEs transporte, 24-07-2026)")
CONF = os.path.join(CNPJ, "confianca_nucleo_por_municipio.csv")
ESTAB = os.path.join(CNPJ, "estabelecimentos_por_municipio_6cnaes.csv")
GRUPOS = os.path.join(RAIZ, "painel TZ", "scripts", "grupos_por_municipio.json")

TITULO = "## Grupos econômicos (Cap 7) — dados do BD CNPJ"
FONTE = ("_Fonte: filtrados (6 CNAEs transporte, 24-07-2026). "
         "Ver [[pesquisa dos CNPJs]] (§ \"Espacialização preliminar\")._")


def ler_csv(p, chave="cod_ibge"):
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8-sig", newline="") as f:
        return {(r.get(chave) or "").strip(): r for r in csv.DictReader(f)}


def inteiro(v):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def bloco(cod, conf, estab, grupos):
    """Monta o bloco. Cada linha só é escrita se a fonte dela responder."""
    L = [TITULO, FONTE]

    c = conf.get(cod)
    if c:
        niv = (c.get("nivel_confianca") or "").strip() or "—"
        esc = inteiro(c.get("escore_confianca"))
        n = inteiro(c.get("n_cnpj_nucleo"))
        L.append(f"- **Confiança do núcleo-transporte CNPJ:** {niv} "
                 f"(escore {esc}/5, {n} CNPJ(s) núcleo).")
    else:
        L.append("- **Confiança do núcleo-transporte CNPJ:** ⚠️ município fora da base "
                 "de confiança do núcleo — **não medido**, não é ausência de núcleo.")

    e = estab.get(cod)
    if e:
        nn = inteiro(e.get("n_estab_ativos_nucleo"))
        nx = inteiro(e.get("n_estab_ativos_expansao"))
        L.append("- **Estabelecimentos ativos (núcleo — 4921301 Municipal + 4921302 "
                 f"Metropolitano/intermunicipal urbano):** {nn}"
                 + (f" · expansão (6 CNAEs): {nx}." if nx is not None else "."))
    else:
        L.append("- **Estabelecimentos ativos (núcleo):** ⚠️ município fora da base de "
                 "estabelecimentos — **não medido**.")

    g = grupos.get(cod) or []
    if g:
        nomes = " · ".join(f"**{nome}** ({gid})" for nome, gid in
                           sorted((x[0], x[1]) for x in g))
        L.append(f"- **Grupo(s) econômico(s) com estabelecimento no município:** "
                 f"{len(g)} — {nomes}.")
        L.append("- 🚨 **O cruzamento mede ENDEREÇO DE ESTABELECIMENTO, não operação "
                 "urbana.** A auditoria de 09/09/2026 mostrou, em Araraquara, que dos "
                 "4 grupos atribuídos só 1 era operador urbano — um é rodoviário, dois "
                 "são garagem/agência já refutados — e faltava o sócio do consórcio. "
                 "**Conferir contra a pesquisa de operador antes de usar como evidência.**")
    else:
        L.append("- **Grupo(s) econômico(s) com estabelecimento no município:** nenhum "
                 "dos grupos reconhecidos tem estabelecimento núcleo mapeado aqui "
                 "⚠️ — resultado do cruzamento, que cobre 796 municípios; não é prova "
                 "de ausência de operador ligado a grupo.")

    L.append("- ⚠️ Ressalva obrigatória: presença de estabelecimento núcleo **não** "
             "comprova que o grupo opera a linha de TZ deste município — checar antes "
             "de qualquer afirmação causal. Ver [[pesquisa dos CNPJs]].")
    return "\n".join(L) + "\n"


def inserir(txt, novo):
    """Insere antes de '## Dados quantitativos'; senão antes de '## Ligações'."""
    for anc in (r"^## Dados quantitativos", r"^## Literatura da RSL", r"^## Ligações"):
        m = re.search(anc, txt, re.M)
        if m:
            return txt[:m.start()] + novo + "\n" + txt[m.start():], True
    return txt, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(FDIR):
        sys.exit(f"🔴 não achei as fichas em {FDIR} — rode da raiz do cofre ou defina TZ_VAULT")
    conf, estab = ler_csv(CONF), ler_csv(ESTAB)
    grupos = json.load(open(GRUPOS, encoding="utf-8")) if os.path.exists(GRUPOS) else {}
    print(f"fontes: confiança {len(conf)} · estabelecimentos {len(estab)} · grupos {len(grupos)}")

    fichas = sorted(f for f in os.listdir(FDIR)
                    if f.startswith("Ficha") and f.endswith(".md") and "MOC" not in f)
    plano, ja, sem_cod, sem_anc = [], 0, [], []
    for nome in fichas:
        p = os.path.join(FDIR, nome)
        txt = open(p, encoding="utf-8").read()
        if re.search(r"^##+\s*.{0,6}Grupos econ", txt, re.M):
            ja += 1
            continue
        m = re.search(r"^codigo_ibge:\s*(\d+)", txt, re.M)
        if not m:
            sem_cod.append(nome)
            continue
        cod = m.group(1)
        novo_txt, ok = inserir(txt, bloco(cod, conf, estab, grupos))
        if not ok:
            sem_anc.append(nome)
            continue
        plano.append((nome, p, novo_txt, cod in grupos, cod in conf))

    print(f"\n{len(fichas)} fichas · {ja} já tinham o bloco (intocadas) · {len(plano)} a preencher")
    print(f"   com grupo mapeado no cruzamento: {sum(1 for x in plano if x[3])}")
    print(f"   com linha na base de confiança:  {sum(1 for x in plano if x[4])}")
    if sem_cod:
        print(f"\n⚠️ sem codigo_ibge, não tocadas ({len(sem_cod)}): {', '.join(sem_cod[:5])}")
    if sem_anc:
        print(f"\n🔴 sem âncora de inserção ({len(sem_anc)}): {', '.join(sem_anc[:5])}")
    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        if plano:
            print("\n--- prévia (1ª ficha):\n")
            print(re.search(r"^## Grupos econômicos.*?(?=\n## )", plano[0][2], re.S | re.M).group(0))
        return
    bk = os.path.join(RAIZ, "_meta", "_backups",
                      "grupos-economicos-" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M"))
    os.makedirs(bk, exist_ok=True)
    for nome, p, novo_txt, _, _ in plano:
        shutil.copy2(p, os.path.join(bk, nome))
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(novo_txt)
    print(f"\n✅ {len(plano)} fichas preenchidas · backup em {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
