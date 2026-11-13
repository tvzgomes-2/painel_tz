#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""enriquecer_perfil_socioeconomico.py — escreve o bloco
"### Perfil socioeconômico (Base Municipal v3)" em cada ficha municipal, dentro
de "## 1. Briefing", ao lado de "### Contexto de mobilidade".

======================================================================
POR QUE
======================================================================
A camada socioeconomica estava na base e nao chegava as fichas. Medido em
19/09/2026 sobre 272 fichas: PIB per capita, IDH, IBEU, taxa de urbanizacao e
hierarquia REGIC apareciam em **1** ficha (Araraquara, escrita a mao);
motorizacao em 6; CadUnico em 4. E **78 fichas nao tinham nem populacao** — 57
stubs da RSL com "nao pesquisado" e 21 com travessao. Tudo isso esta em
`base_municipal_v3.csv` com cobertura 5.570/5.570.

======================================================================
🔴 DUAS COLUNAS QUE ESTE SCRIPT SE RECUSA A USAR COMO ESTAO
======================================================================
1. **`area_km2` NAO e escrita.** Conferida contra populacao/densidade, diverge
   em **140 de 5.570** municipios, com padrao de digito faltando: Corumbiara/RO
   diz 306 e o calculo da 3.007,6; Sena Madureira/AC diz 2.376 contra 24.319;
   Rio de Janeiro diz 12 contra 1.200. Nao e ruido, e erro sistematico de
   parsing. Em vez de area, o bloco traz **densidade**, que confere em 5.430.
   ➡️ Se a coluna for corrigida, acrescentar a linha aqui.

2. **CadUnico: pobreza e extrema pobreza sao faixas DISJUNTAS, nao aninhadas.**
   Em **4.773 de 5.570** municipios "extrema pobreza" e MAIOR que "pobreza" —
   o que so faz sentido se forem categorias separadas. Por isso o bloco escreve
   as duas lado a lado como faixas, e NUNCA "X em pobreza, dos quais Y em
   extrema", que seria leitura errada do dado.

======================================================================
NA != 0
======================================================================
Campo vazio vira "—", nunca zero, e municipio ausente da base nao recebe bloco
nenhum (e reportado). Ausencia de medida nao e medida de ausencia.

======================================================================
IDEMPOTENTE E NAO DESTRUTIVO
======================================================================
Substitui o bloco se ja existir; insere depois de "### Contexto de mobilidade"
(ou no fim da secao 1) se nao. Nao toca em nenhuma outra secao. Backup dos
originais antes de gravar.

USO
  python enriquecer_perfil_socioeconomico.py            # simula
  python enriquecer_perfil_socioeconomico.py --gravar   # grava, com backup
"""
import argparse
import csv
import datetime
import os
import re
import shutil
import sys

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
FDIR = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Fichas por município")
BASE = os.path.join(RAIZ, "03 - Dados", "_data", "Base Municipal v3", "base_municipal_v3.csv")
TITULO = "### Perfil socioeconômico (Base Municipal v3)"


def n(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", ".")
    if s in ("", "-", "—", "nan", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def br(x, casas=0):
    if x is None:
        return "—"
    return f"{x:,.{casas}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def pct(x, casas=1):
    return "—" if x is None else br(x, casas) + "%"


def txt(v):
    s = (str(v).strip() if v is not None else "")
    return s if s and s.lower() not in ("nan", "none", "-") else "—"


def bloco(r):
    L = [TITULO]

    # --- porte e forma urbana
    p22, p25 = n(r.get("pop_2022")), n(r.get("pop_2025"))
    faixa, dens = txt(r.get("faixa_pop_2022")), n(r.get("densid_pop__22"))
    cag = n(r.get("pop_cagr_2010_2022"))
    s = f"- **População:** {br(p22)} (2022) → {br(p25)} (2025)"
    if faixa != "—":
        s += f" · faixa: {faixa.lower()}"
    if dens is not None:
        s += f" · densidade {br(dens, 1)} hab/km²"
    if cag is not None:
        s += f" · crescimento 2010-2022 {'+' if cag >= 0 else ''}{pct(cag, 2)} a.a."
    L.append(s.rstrip(".") + ".")   # evita "a.a.." quando a linha já termina em ponto
    # ⚠️ area_km2 fica FORA de proposito — ver cabeçalho deste arquivo.

    # --- posição na rede urbana
    hier = txt(r.get("regic_hierarquia_2018")).split(" - ")[0]
    infl = txt(r.get("regic_regiao_infl_2018"))
    arr = txt(r.get("arranjo_pop_ibge"))
    pos = txt(r.get("posicao_arranjo"))
    s = f"- **Posição na rede urbana (REGIC 2018):** {hier}"
    if arr != "—":
        s += f" · {arr}, como **{pos}**"
    elif pos != "—":
        s += f" · {pos}"
    if infl != "—":
        s += f" · região de influência: {infl}"
    L.append(s + ".")

    # --- renda e desenvolvimento
    pib, idh, ibeu = n(r.get("pib_per_capita_2021")), n(r.get("idh")), n(r.get("ibeu"))
    urb = n(r.get("taxa_urbanizacao_2022"))
    s = f"- **Renda e desenvolvimento:** PIB per capita 2021 R$ {br(pib)}"
    if idh is not None:
        s += f" · IDH {br(idh, 3)}"
    if ibeu is not None:
        s += f" · IBEU {br(ibeu, 3)}"
    if urb is not None:
        s += f" · urbanização {pct(urb, 1)}"
    L.append(s + ".")

    # --- motorização
    m25, m13 = n(r.get("taxa_motorizacao_2025")), n(r.get("taxa_motorizacao_2013"))
    if m25 is not None:
        s = f"- **Motorização:** {br(m25, 1)} veículos por mil habitantes (2025)"
        if m13:
            s += (f" · era {br(m13, 1)} em 2013 "
                  f"({'+' if m25 >= m13 else ''}{pct((m25 - m13) / m13 * 100, 1)})")
        L.append(s + ".")

    # --- vulnerabilidade (bloco pedido pelo autor)
    cpes = n(r.get("cadunico_pes_202508"))
    ccob = n(r.get("cadunico_cobertura_pct_202508"))
    catu = n(r.get("cadunico_taxa_atualizacao_pct_202508"))
    s = f"- **CadÚnico (ago/2025):** {br(cpes)} pessoas cadastradas"
    if ccob is not None:
        s += f", cobertura {pct(ccob, 1)} da população"
    if catu is not None:
        s += f" · atualização cadastral {pct(catu, 1)}"
    L.append(s + ".")

    fpob = n(r.get("cadunico_fam_sit_pobreza_202508"))
    fext = n(r.get("cadunico_fam_sit_extrema_pobreza_202508"))
    pbf = n(r.get("cadunico_pes_benef_pbf_202508"))
    s = (f"- **Faixas de renda no CadÚnico:** {br(fpob)} famílias em situação de "
         f"pobreza · {br(fext)} em extrema pobreza")
    if pbf is not None:
        s += f" · {br(pbf)} pessoas beneficiárias do Bolsa Família"
    L.append(s + ".")
    L.append("- ⚠️ As duas faixas do CadÚnico são **disjuntas, não aninhadas** — em 4.773 "
             "dos 5.570 municípios a de extrema pobreza é maior que a de pobreza. Não ler "
             "como \"X em pobreza, dos quais Y em extrema\".")

    # --- renda de quem sai x quem fica (microdados Censo 2022)
    sai, fica = n(r.get("md22_renda_media_saem")), n(r.get("md22_renda_media_ficam"))
    if sai is not None and fica is not None:
        dif = (sai / fica - 1) * 100 if fica else None
        s = (f"- **Renda média do trabalho (Censo 2022, microdados):** quem trabalha "
             f"**fora** do município R$ {br(sai)} · quem **fica** R$ {br(fica)}")
        if dif is not None:
            s += f" — diferença de {'+' if dif >= 0 else ''}{pct(dif, 1)}"
        L.append(s + ".")

    L.append("_Fonte: `base_municipal_v3.csv` (IBGE Censo 2022 e estimativas, REGIC 2018, "
             "PIB municipal 2021, CadÚnico ago/2025, SENATRAN, microdados do Censo 2022)._")
    return "\n".join(L) + "\n"


def aplicar(txt_ficha, novo):
    m = re.search(r"^### Perfil socioeconômico.*?(?=\n^#{2,3} |\Z)", txt_ficha, re.S | re.M)
    if m:
        # ⚠️ Compara por CONTEÚDO, não byte a byte: a captura arrasta a linha em
        # branco que separa do próximo cabeçalho, e sem isto cada passada trocava
        # um "\n" e o script se dizia "272 a alterar" eternamente. Idempotência
        # se verifica no arquivo, e foi assim que este caso apareceu.
        if m.group(0).strip() == novo.strip():
            return txt_ficha, "igual"
        cauda = "\n" if m.group(0).endswith("\n") else ""
        return txt_ficha[:m.start()] + novo.rstrip("\n") + "\n" + cauda + txt_ficha[m.end():], "substituído"
    ctx = re.search(r"^### Contexto de mobilidade.*?(?=\n^#{2,3} |\Z)", txt_ficha, re.S | re.M)
    if ctx:
        return txt_ficha[:ctx.end()] + "\n\n" + novo + txt_ficha[ctx.end():], "inserido"
    m1 = re.search(r"^## 1\.[^\n]*\n", txt_ficha, re.M)
    if not m1:
        return txt_ficha, "🔴 sem âncora"
    prox = re.search(r"^## ", txt_ficha[m1.end():], re.M)
    corte = m1.end() + (prox.start() if prox else len(txt_ficha) - m1.end())
    return txt_ficha[:corte].rstrip() + "\n\n" + novo + "\n\n" + txt_ficha[corte:], "inserido"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(FDIR):
        sys.exit(f"🔴 não achei as fichas em {FDIR}")
    with open(BASE, encoding="utf-8-sig", newline="") as f:
        base = {(r.get("cod_ibge") or "").strip(): r for r in csv.DictReader(f)}

    fichas = sorted(x for x in os.listdir(FDIR)
                    if x.startswith("Ficha") and x.endswith(".md") and "MOC" not in x)
    plano, sem = [], []
    for nome in fichas:
        p = os.path.join(FDIR, nome)
        t = open(p, encoding="utf-8").read()
        m = re.search(r"^codigo_ibge:\s*(\d+)", t, re.M)
        if not m or m.group(1) not in base:
            sem.append(nome)
            continue
        novo_t, acao = aplicar(t, bloco(base[m.group(1)]))
        if novo_t != t:
            plano.append((nome, p, novo_t, acao))
    ins = sum(1 for x in plano if x[3] == "inserido")
    print(f"{len(fichas)} fichas · {len(plano)} a alterar · {len(sem)} sem match na base")
    print(f"   bloco inserido: {ins} · substituído: {len(plano)-ins}")
    if sem:
        print("   sem código IBGE/linha na base:", ", ".join(sem[:5]))
    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        if plano:
            print("\n--- prévia:\n" + re.search(r"^### Perfil socioeconômico.*?(?=\n^#{2,3} |\Z)",
                                                plano[0][2], re.S | re.M).group(0))
        return
    bk = os.path.join(RAIZ, "_meta", "_backups",
                      "perfil-socioeconomico-" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M"))
    os.makedirs(bk, exist_ok=True)
    for nome, p, novo_t, _ in plano:
        shutil.copy2(p, os.path.join(bk, nome))
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(novo_t)
    print(f"\n✅ {len(plano)} fichas gravadas · backup em {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
