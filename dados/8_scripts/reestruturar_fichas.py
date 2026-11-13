#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""reestruturar_fichas.py — parte de COFRE da nova arquitetura de ficha
(diretrizes do autor, 19/09/2026). Faz duas coisas, e só duas:

1. **Campos de Dataview no frontmatter.** Extraidos do conteudo que ja existe na
   ficha, nunca inventados: ano_inicio, situacao, operador, custeio,
   remuneracao, escore_cnpj, n_estab_nucleo, n_grupos_ge, status_ficha.
   ➡️ Isto — e nao a tabela — e o que da o "ganho Dataview" do plano: o Dataview
   le frontmatter e campos inline `chave:: valor`, e **nao le tabela markdown
   como dado**. A tabela serve o olho humano no PDF; o frontmatter serve o
   script que alimenta as tabelas-resumo dos capitulos.

2. **Caixa de auditoria (§6).** Recolhe o que hoje esta espalhado no meio dos
   dados — callouts `[!warning]`/`[!note]`, linhas "a revisar", divergencias de
   fonte ja registradas — e junta no fim da ficha, sob
   "## Auditoria, alertas e pendencias". Decisao do autor: **realoca o que ja
   existe, nao abre checklist vazio** — 272 caixas em branco seriam convite, nao
   conteudo.

======================================================================
O QUE ESTE SCRIPT NAO FAZ, DE PROPOSITO
======================================================================
**Nao reordena as secoes de dados e nao transforma bullet em tabela.** Os cinco
geradores (perfil socioeconomico, contexto de mobilidade, dados quantitativos,
literatura da RSL, grupos economicos) escrevem e reescrevem blocos de bullets
ancorados por titulo. Virar tabela no cofre quebraria os cinco de uma vez, e
editar uma celula a mao e bem pior que editar um bullet.

➡️ A ordem das secoes e a condensacao em tabelas de 2-3 colunas acontecem no
**export** (`exportar_fichas_final.py`), onde nao ha o que quebrar. O cofre fica
com o dado; o PDF, com a diagramacao.

IDEMPOTENTE. Simula por padrao. Backup antes de gravar.

USO  python reestruturar_fichas.py [--gravar]
"""
import argparse
import datetime
import os
import re
import shutil
import sys

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
FDIR = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Fichas por município")
TIT_AUD = "## Auditoria, alertas e pendências"
MARCA = "<!-- caixa-auditoria: montada por reestruturar_fichas.py -->"


def secao(t, pat):
    m = re.search(pat + r"[^\n]*\n(.*?)(?=^#{2,3}\s|\Z)", t, re.S | re.M)
    return m.group(1) if m else ""


def campo(t, rot):
    m = re.search(r"\*\*" + rot + r":?\*\*:?\s*(.+)", t)
    return m.group(1).strip() if m else ""


def limpo(v, corte=90):
    v = re.sub(r"\[\[([^\]]+)\]\]",
               lambda m: m.group(1).split("|")[-1].split("#")[0], v)
    v = re.sub(r"[*_`]", "", v).strip().rstrip(".").strip()
    v = re.sub(r"\s+", " ", v)
    if not v or v in ("—", "-"):
        return ""
    if len(v) <= corte:
        return v
    # corta em limite de palavra: "Fichas Aprofun" num campo de metadado é pior
    # que reticências — o Dataview mostra o valor inteiro na tabela.
    return v[:corte].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"


def extrair(t):
    """Só lê o que a ficha já diz. Campo ausente vira string vazia, nunca zero
    nem valor plausível — NA != 0 vale também para metadado."""
    d = {}
    sit = campo(t, "Situação / modelo / início")
    if sit:
        partes = [p.strip() for p in sit.split("/")]
        if len(partes) >= 1 and partes[0] not in ("—", ""):
            d["situacao"] = limpo(partes[0], 40)
        if len(partes) >= 3:
            an = re.search(r"(1[89]\d{2}|20\d{2})", partes[2])
            if an:
                d["ano_inicio"] = an.group(1)
    for chave, rot in (("operador", "Operador"),
                       ("custeio", "Mecanismo de custeio"),
                       ("remuneracao", "Remuneração do operador")):
        v = limpo(campo(t, rot))
        if v and not re.match(r"(?i)^(não verificado|a levantar|—)", v):
            d[chave] = v
    m = re.search(r"escore (\d)/5,\s*(\d+)\s*CNPJ", t)
    if m:
        d["escore_cnpj"] = m.group(1)
    m = re.search(r"urbano\):\*\*\s*(\d+)", t)
    if m:
        d["n_estab_nucleo"] = m.group(1)
    m = re.search(r"estabelecimento no município:\*\*\s*(\d+)\s*—", t)
    d["n_grupos_ge"] = m.group(1) if m else "0"
    tip = re.search(r"^tipologia_analitica:\s*(.+)$", t, re.M)
    reg = campo(t, "Tipologia")
    a_checar = (not d.get("operador")) or "a classificar" in (reg or "").lower() \
        or "a classificar" in (tip.group(1).lower() if tip else "")
    d["status_ficha"] = "a checar" if a_checar else "consolidado"
    return d


def coletar_auditoria(t):
    """Tira do meio dos dados os callouts e as linhas 'a revisar'."""
    itens, resto, i = [], [], 0
    linhas = t.split("\n")
    while i < len(linhas):
        l = linhas[i]
        if re.match(r"^>\s*\[!(warning|caution|danger|attention|note|bug)\]", l, re.I):
            bloco = [l]
            i += 1
            while i < len(linhas) and linhas[i].lstrip().startswith(">"):
                bloco.append(linhas[i])
                i += 1
            itens.append("\n".join(bloco))
            continue
        if re.search(r"⚠️\s*\*\*a revisar\*\*|^\s*-\s*⚠️\s*\*\*a revisar", l, re.I):
            itens.append(l.strip())
            i += 1
            continue
        resto.append(l)
        i += 1
    return "\n".join(resto), itens


def aplicar(txt):
    fm = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not fm:
        return txt, "🔴 sem frontmatter"
    head, corpo = fm.group(1), txt[fm.end():]

    # ---- 1. caixa de auditoria
    # 🚨 A caixa ANTIGA e lida ANTES de ser removida, e seus itens voltam para a
    # nova. Sem isto o script destruia na 2a passada exatamente o que a 1a tinha
    # recolhido: a caixa era apagada inteira (com o conteudo), e coletar_auditoria
    # nao achava mais nada no corpo, porque os callouts ja estavam dentro dela.
    # Pego na simulacao da 2a passada, antes de qualquer gravacao.
    antigos = []
    m_old = re.search(re.escape(TIT_AUD) + r"(.*?)(?=\n##\s|\Z)", corpo, re.S)
    if m_old:
        bruto = m_old.group(1)
        bruto = bruto.replace(MARCA, "")
        bruto = re.sub(r"^_Notas críticas realocadas[^\n]*\n", "", bruto, flags=re.M)
        antigos = [b.strip() for b in re.split(r"\n\s*\n", bruto) if b.strip()]
        corpo = corpo[:m_old.start()] + corpo[m_old.end():]
    corpo, novos = coletar_auditoria(corpo)
    itens, vistos = [], set()
    for b in antigos + novos:                    # antigos primeiro: preserva a ordem
        chave = re.sub(r"\s+", " ", b)[:120]
        if chave not in vistos:
            vistos.add(chave)
            itens.append(b)
    if itens:
        caixa = ("\n" + TIT_AUD + "\n" + MARCA + "\n"
                 "_Notas críticas realocadas do corpo da ficha — a leitura factual "
                 "fica acima, o juízo metodológico fica aqui._\n\n"
                 + "\n\n".join(itens) + "\n")
        m = re.search(r"\n##\s*Liga[çc][õo]es", corpo)
        corpo = (corpo[:m.start()] + caixa + corpo[m.start():]) if m else corpo + caixa

    # ---- 2. frontmatter para Dataview
    d = extrair(txt)
    linhas = [l for l in head.split("\n")
              if not re.match(r"^(" + "|".join(d) + r"):", l)] if d else head.split("\n")
    for k in ("situacao", "ano_inicio", "operador", "custeio", "remuneracao",
              "escore_cnpj", "n_estab_nucleo", "n_grupos_ge", "status_ficha"):
        if k in d and d[k] != "":
            v = d[k]
            linhas.append(f'{k}: "{v}"' if re.search(r"[:#\"]", v) else f"{k}: {v}")
    novo = "---\n" + "\n".join(x for x in linhas if x.strip()) + "\n---\n" + corpo
    novo = re.sub(r"\n{3,}", "\n\n", novo)
    return novo, ("ok" if novo != txt else "igual")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(FDIR):
        sys.exit(f"🔴 não achei as fichas em {FDIR}")
    fichas = sorted(x for x in os.listdir(FDIR)
                    if x.startswith("Ficha") and x.endswith(".md") and "MOC" not in x)
    plano, erro, com_caixa, campos = [], [], 0, {}
    for nome in fichas:
        p = os.path.join(FDIR, nome)
        t = open(p, encoding="utf-8").read()
        novo, st = aplicar(t)
        if st.startswith("🔴"):
            erro.append(nome)
            continue
        if TIT_AUD in novo:
            com_caixa += 1
        for k, v in extrair(t).items():
            if v != "":
                campos[k] = campos.get(k, 0) + 1
        if novo != t:
            plano.append((nome, p, novo))
    print(f"{len(fichas)} fichas · {len(plano)} a alterar · {len(erro)} sem frontmatter")
    print(f"   caixa de auditoria em: {com_caixa}")
    print("   campos de Dataview preenchidos:")
    for k, v in sorted(campos.items(), key=lambda x: -x[1]):
        print(f"      {v:>4}/{len(fichas)}  {k}")
    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        if plano:
            print("\n--- prévia do frontmatter (1ª alterada):\n")
            print(re.match(r"^---\n.*?\n---\n", plano[0][2], re.S).group(0))
        return
    bk = os.path.join(RAIZ, "_meta", "_backups",
                      "reestrutura-" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M"))
    os.makedirs(bk, exist_ok=True)
    for nome, p, novo in plano:
        shutil.copy2(p, os.path.join(bk, nome))
        open(p, "w", encoding="utf-8", newline="\n").write(novo)
    print(f"\n✅ {len(plano)} fichas · backup em {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
