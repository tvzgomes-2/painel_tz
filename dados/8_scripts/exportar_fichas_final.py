#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""exportar_fichas_final.py — PDF das fichas municipais na arquitetura de
apresentacao definida pelo autor em 19/09/2026.

======================================================================
A DIVISAO DE TRABALHO ENTRE COFRE E EXPORT
======================================================================
* **Cofre** (`reestruturar_fichas.py`): frontmatter para Dataview e caixa de
  auditoria. O dado fica em bullets, porque os cinco geradores escrevem e
  reescrevem bullets ancorados por titulo — virar tabela la quebraria os cinco.
* **Export** (este arquivo): cartao de cabecalho, condensacao dos bullets em
  tabelas de 2-3 colunas, ordem das secoes, limpeza editorial.

➡️ Dataview le frontmatter e `chave:: valor`, **nao le tabela markdown como
dado**. Por isso a tabela vive aqui, onde serve ao olho, e os campos vivem la,
onde servem ao script.

======================================================================
LIMPEZA EDITORIAL — no export, nunca no cofre
======================================================================
Notas de rodada ("linha regerada a partir do cruzamento conferido em
02/09/2026"), datas em titulo e navegacao do Obsidian sao **proveniencia**: no
cofre dizem de onde veio cada linha. Num documento de deposito sao ruido. Some
aqui, permanece la.

Sai tambem a **populacao do §2**, que CONTRADIZ o perfil socioeconomico: de 208
fichas com as duas, 176 divergem (mediana 3,7%). Fica a do perfil, com fonte e
ano declarados.

As ressalvas metodologicas repetidas (CadUnico disjunto, cruzamento CNPJ,
CTP/CTPU, contagem de mencoes) vao UMA vez, na nota de abertura — eram ~700
linhas identicas ao longo do documento.

USO  python exportar_fichas_final.py
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
FDIR = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Fichas por município")
SAIDA = os.path.join(RAIZ, "02 - Tese", "Leitura")
NOME = "Fichas municipais de Tarifa Zero"
VERSAO = "versão de leitura — " + datetime.now().strftime("%d/%m/%Y")

UF = {'AC': 'Acre', 'AL': 'Alagoas', 'AM': 'Amazonas', 'AP': 'Amapá', 'BA': 'Bahia',
      'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás',
      'MA': 'Maranhão', 'MG': 'Minas Gerais', 'MS': 'Mato Grosso do Sul',
      'MT': 'Mato Grosso', 'PA': 'Pará', 'PB': 'Paraíba', 'PE': 'Pernambuco',
      'PI': 'Piauí', 'PR': 'Paraná', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte',
      'RO': 'Rondônia', 'RR': 'Roraima', 'RS': 'Rio Grande do Sul', 'SC': 'Santa Catarina',
      'SE': 'Sergipe', 'SP': 'São Paulo', 'TO': 'Tocantins'}

FORA_LINHA = [
    r"consta em \[\[", r"^\s*-\s*Análise:\s*\[\[",
    r"Ver ressalva obrigatória no template",
    r"^\s*_Verificação manual \(critério", r"_Fonte: .?base_municipal_v3",
    r"^\s*_Fonte: filtrados \(6 CNAEs",
    r"^\s*-\s*⚠️\s*As duas faixas do CadÚnico", r"^\s*-\s*⚠️\s*Ressalva obrigatória",
    r"^\s*-\s*🚨\s*\*\*O cruzamento mede ENDEREÇO",
    r"^\s*-\s*⚠️\s*Ressalvas: mistura de anos-safra",
    r"^\s*⚠️\s*\*\*O que a contagem é e o que não é",
    r"^\s*-\s*\*\*População \(2022\):\*\*", r"nenhuma matéria coletada",
    r"\*\*Impulsionador\(es\):\*\*\s*não documentado",
    r"\*\*Limitante\(s\):\*\*\s*não documentado",
    r"^\s*-\s*\*\*Frota / linhas / demanda:\*\*\s*(Não mencionado|—)\s*/",
    r"^\s*-\s*\*\*[^*]+:\*\*\s*—\s*$",
    r"^\s*_Camada atual:[^_]*Sem registro de mudança[^_]*_\s*$",
    r"^<!-- caixa-auditoria",
]
FORA_TRECHO = [
    (r"\s*·?\s*\*linha regerada a partir do cruzamento conferido em [\d/-]+\*", ""),
    (r"\s*\(cobertura verificada em [\d/-]+\)", ""),
    (r"\s*—\s*verificação manual \([\d/-]+\)", ""),
    (r"\s*\(gerado\)", ""), (r"\s*·?\s*\(verificad[oa] em [\d/-]+\)", ""),
    (r"\s*\(Banco Municipal v3[^)]*\)", ""), (r"\s*\(Base Municipal v3\)", ""),
    (r"\s*—\s*dados do BD CNPJ", ""), (r"\s*\(Cap \d+\)", ""),
]

NOTA_METODO = """
# Nota metodológica

As ressalvas abaixo valem para **todas** as fichas deste documento. Estão aqui uma
vez, e não repetidas em cada município.

**Ausência de medida não é medida de ausência.** Campo vazio significa dado não
apurado, não fenômeno inexistente. Quando a fonte mediu e deu zero, a ficha diz.

**Grupos econômicos — o cruzamento mede endereço, não operação.** A presença de
estabelecimento do núcleo-transporte (CNAE 4921301 e 4921302) num município não
comprova que o grupo opera a linha de Tarifa Zero dali. A auditoria de setembro de
2026 mostrou, em Araraquara, que dos quatro grupos atribuídos apenas um era
operador urbano — um é rodoviário, dois são garagem ou agência — e que o sócio do
consórcio local sequer aparecia. Afirmação causal exige checagem contra a pesquisa
de operador.

**CadÚnico — as faixas de renda são disjuntas, não aninhadas.** Em 4.773 dos 5.570
municípios a faixa de extrema pobreza é maior que a de pobreza, o que só faz
sentido se forem categorias separadas. Não ler como "X famílias em pobreza, das
quais Y em extrema".

**Simulação de financiamento sobre a folha (CTP/CTPU).** Mistura anos-safra (RAIS
2022, salário SIDRA 2024, Censo 2022); a folha é aproximada por vínculos ×
salário médio, não pela soma de salários reais; informalidade é dado amostral
preliminar.

**Cobertura na revisão sistemática.** A contagem mede menções nos *fichamentos* —
notas de leitura do autor —, não nos textos originais. Indício de cobertura, não
prova.

**Fontes dos blocos padronizados.** IBGE (Censo 2022 e estimativas), REGIC 2018,
PIB municipal 2021, CadÚnico (ago/2025), SENATRAN, MUNIC 2012-2020, RAIS 2022,
SIDRA 2024, microdados do Censo 2022 e base de CNPJ filtrada por seis CNAEs de
transporte.

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
"""


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def delink(s):
    return re.sub(r"\[\[([^\]]+)\]\]",
                  lambda m: (m.group(1).split("|")[1] if "|" in m.group(1)
                             else m.group(1).split("#")[0]), s)


def limpar(t):
    for pat, rep in FORA_TRECHO:
        t = re.sub(pat, rep, t, flags=re.I)
    t = "\n".join(l for l in t.split("\n")
                  if not any(re.search(p, l, re.I) for p in FORA_LINHA))
    return re.sub(r"\n{3,}", "\n\n", t)


def bloco(txt, pat):
    m = re.search(pat + r"[^\n]*\n(.*?)(?=^#{2,4}\s|\Z)", txt, re.S | re.M)
    return m.group(1).strip() if m else ""


def pares(b):
    """'- **Rótulo:** valor' -> [(rótulo, valor)]. Linha sem rótulo vira (None, l)."""
    out = []
    for l in b.split("\n"):
        l = l.strip()
        if not l.startswith("-"):
            continue
        m = re.match(r"-\s*\*\*(.+?):?\*\*:?\s*(.*)", l)
        if m:
            out.append((m.group(1).strip(), m.group(2).strip().rstrip(".")))
        else:
            v = re.sub(r"^-\s*", "", l)
            if v:
                out.append((None, v))
    return out


def cel(par):
    if par is None:
        return ""
    rot, val = par
    val = val.replace("|", "\\|")
    return (f"**{rot}:** {val}" if rot else val)


def tabela(cols, larg=None):
    """cols = [(titulo, [pares])] -> tabela markdown com as colunas lado a lado."""
    cols = [c for c in cols if c[1]]
    if not cols:
        return ""
    n = max(len(c[1]) for c in cols)
    cab = "| " + " | ".join(c[0] for c in cols) + " |"
    sep = "|" + "|".join([" :--- "] * len(cols)) + "|"
    linhas = [cab, sep]
    for i in range(n):
        linhas.append("| " + " | ".join(
            cel(c[1][i] if i < len(c[1]) else None) for c in cols) + " |")
    return "\n".join(linhas) + "\n"


def lista(b):
    return "\n".join("- " + cel(p) for p in pares(b)) + "\n" if pares(b) else ""


def prosa(b):
    """Blocos narrativos saem como parágrafos, não bullets."""
    out = []
    for rot, val in pares(b):
        out.append((f"**{rot}.** {val}" if rot else val))
    return "\n\n".join(out) + "\n" if out else ""


def monta_ficha(txt, fm):
    t = limpar(txt)
    t = delink(t)
    B = lambda p: bloco(t, p)

    perfil = B(r"^###\s*Perfil socioeconômico")
    mob = B(r"^###\s*Contexto de mobilidade")
    quant = B(r"^##\s*Dados quantitativos")
    dados = B(r"^##\s*2\.")
    leg = B(r"^##\s*5\.")
    ge = B(r"^##+\s*.{0,6}Grupos econ")
    ra = B(r"^##+\s*Régua analítica")
    rd = B(r"^##+\s*Régua descritiva")
    fat = B(r"^##+\s*Fatores impulsionadores")
    bib = B(r"^##\s*3\.")
    mat = B(r"^##\s*4\.")
    rsl = B(r"^##\s*Literatura da RSL")
    trab = B(r"^##\s*Trabalhos que referenciam")
    brief = B(r"^##\s*1\.\s*Briefing")
    aud = B(r"^##\s*Auditoria, alertas")

    out = []

    # --- cartão de cabeçalho
    l1 = [f"**Código IBGE:** {fm.get('codigo_ibge','—')}"]
    if fm.get("ano_inicio"):
        l1.append(f"**Início:** {fm['ano_inicio']}")
    if fm.get("situacao"):
        l1.append(f"**Situação:** {fm['situacao']}")
    l2 = []
    if fm.get("camada"):
        l2.append(f"**Camada:** {fm['camada']}")
    if fm.get("tipologia_analitica"):
        l2.append(f"**Tipologia:** {fm['tipologia_analitica']}")
    if fm.get("status_ficha"):
        l2.append(f"**Status:** {fm['status_ficha']}")
    out.append(" · ".join(l1))
    if l2:
        out.append(" · ".join(l2))
    out.append("")

    # --- síntese executiva
    b1 = re.split(r"\n###\s", brief)[0].strip()
    if b1:
        out.append("> " + re.sub(r"\n+", "\n> ", b1) + "\n")

    # --- 1. painel de dados (3 colunas)
    tab = tabela([("Perfil socioeconômico", pares(perfil)),
                  ("Contexto de mobilidade", pares(mob)),
                  ("Financiamento e trabalho", pares(quant))])
    if tab:
        out.append("#### 1. Painel de dados e indicadores\n")
        out.append(tab)

    # --- 2. arranjo institucional e operacional
    inst = [p for p in pares(dados)
            if p[0] and re.match(r"(?i)(operador|motiva|frota|% do orç|site)", p[0])
            and not re.match(r"(?i)motiva", p[0] or "")]
    corpo2 = tabela([("Operação e política", inst), ("Grupos econômicos (CNPJ)", pares(ge))])
    if corpo2:
        out.append("#### 2. Arranjo institucional e operacional\n")
        out.append(corpo2)

    # --- 3. base normativa
    if leg.strip():
        out.append("#### 3. Base normativa\n")
        out.append(lista(leg))
        extra = bloco(t, r"^###\s*📜 Normas padronizadas")
        if extra:
            out.append(extra + "\n")
        contr = bloco(t, r"^##+\s*Dados de contratação")
        if contr:
            out.append("**Contratos e licitação**\n\n" + contr + "\n")

    # --- 4. trajetória, gênese e mecanismos
    mot = [p for p in pares(dados) if p[0] and re.match(r"(?i)motiva", p[0])]
    p4 = []
    if mot:
        p4.append("**Gênese e motivação.** " + mot[0][1])
    if fat.strip():
        p4.append(prosa(fat).strip())
    reg = []
    # ⚠️ O bloco do PORTÃO tem de entrar aqui: é o critério que DEFINE a camada
    # desde 10/09/2026. Sem esta linha o exportador o descartava — o dado chegava
    # à ficha e sumia no PDF, que é onde a classificação é lida e discutida.
    port = B(r"^###\s*Portão de acesso")
    if port.strip():
        reg.append("**Portão de acesso**\n\n" + lista(port).strip())
    if rd.strip():
        reg.append("*Régua descritiva:* " + re.sub(r"[_*]", "", rd.strip().split("\n")[0]))
    if ra.strip():
        reg.append(prosa(ra).strip())
    if p4 or reg:
        out.append("#### 4. Trajetória, gênese e mecanismos\n")
        out += [x + "\n" for x in p4]
        if reg:
            out.append("**Posicionamento nas réguas**\n\n" + "\n\n".join(reg) + "\n")

    # --- 5. literatura, fontes e cobertura
    p5 = [x for x in (lista(bib), lista(mat), rsl.strip(), trab.strip()) if x.strip()]
    if p5:
        out.append("#### 5. Literatura, fontes e cobertura\n")
        out += [x + "\n" for x in p5]

    # --- 6. caixa de auditoria
    if aud.strip():
        corpo = re.sub(r"^_Notas críticas realocadas[^\n]*\n", "", aud, flags=re.M).strip()
        if corpo:
            out.append("#### 6. Auditoria, alertas e pendências\n")
            out.append(corpo + "\n")

    return "\n".join(out)


def frontmatter(txt):
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return {}
    d = {}
    for l in m.group(1).split("\n"):
        mm = re.match(r"^(\w+):\s*(.*)$", l)
        if mm and mm.group(2).strip():
            d[mm.group(1)] = mm.group(2).strip().strip('"')
    return d


def base_mestre():
    import openpyxl
    p = os.path.join(RAIZ, "03 - Dados", "_data", "casos por fonte",
                     "Municípios TZ - consolidado.xlsx")
    ws = openpyxl.load_workbook(p, read_only=True, data_only=True)["consolidado"]
    rows = list(ws.iter_rows(values_only=True))
    h = [str(x).strip() for x in rows[0]]
    ci = {k: i for i, k in enumerate(h)}
    return {(norm(r[ci['Município']]), str(r[ci['UF']] or '').strip())
            for r in rows[1:] if r[ci['Município']]}


def main():
    if not os.path.isdir(FDIR):
        sys.exit(f"🔴 não achei as fichas em {FDIR}")
    os.makedirs(SAIDA, exist_ok=True)
    mestre = base_mestre()
    fichas, fora = [], 0
    for p in sorted(glob.glob(FDIR + "/*.md")):
        if "MOC" in p:
            continue
        txt = open(p, encoding="utf-8", errors="replace").read()
        fm = frontmatter(txt)
        mun, uf = fm.get("municipio", os.path.basename(p)[8:-3]), fm.get("uf", "")
        if "ficha-auto-rsl" in txt.split("---", 2)[1] and (norm(mun), uf) not in mestre:
            fora += 1
            continue
        fichas.append({"mun": mun, "uf": uf, "corpo": monta_ficha(txt, fm)})
    fichas.sort(key=lambda x: (x["uf"], norm(x["mun"])))

    md = ["% " + NOME, "% Thiago Von Zeidler Gomes",
          "% Orientadora: Prof.ª Dra. Silvana Zioni · " + VERSAO + "\n",
          "# " + NOME + "\n",
          f"Este documento reúne a ficha de cada um dos **{len(fichas)} municípios** do "
          "recorte de Tarifa Zero desta pesquisa, organizadas por unidade da federação. "
          "Cada ficha segue a mesma estrutura: cartão de identificação, síntese "
          "executiva, painel de dados, arranjo institucional e operacional, base "
          "normativa, trajetória e mecanismos, literatura e cobertura, e — quando há — "
          "a caixa de auditoria com as notas críticas do caso.\n",
          "O travessão (—) indica dado não disponível na fonte. "
          "Fonte: elaboração do autor a partir do acervo da pesquisa (2026).\n",
          NOTA_METODO]
    for uf in sorted({f["uf"] for f in fichas}):
        grp = [f for f in fichas if f["uf"] == uf]
        md.append(f"\n## {uf} — {UF.get(uf, uf)} ({len(grp)})\n")
        for f in grp:
            md.append(f"\n### {f['mun']} — {uf}\n")
            md.append(f["corpo"] + "\n")

    tmp = tempfile.mkdtemp()
    mdp = os.path.join(tmp, "f.md")
    open(mdp, "w", encoding="utf-8", newline="\n").write("\n".join(md))
    docx = os.path.join(SAIDA, NOME + ".docx")
    print(f"{len(fichas)} fichas · {fora} stubs da RSL fora")
    print("gerando .docx…")
    subprocess.run(["pandoc", mdp, "-f", "markdown+raw_attribute+pipe_tables",
                    "-o", docx, "--toc", "--toc-depth=2"], check=True)
    print("convertendo para PDF…")
    subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf",
                    "--outdir", SAIDA, docx], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(SAIDA, NOME + ".pdf")
    if not os.path.exists(pdf):
        sys.exit("🔴 LibreOffice não produziu o PDF")
    print(f"\n✅ {pdf}  ({os.path.getsize(pdf)/1e6:.1f} MB)")
    curtas = sorted(fichas, key=lambda x: len(x["corpo"]))[:10]
    print("\n⚠️ fichas mais curtas — falta pesquisa, não formatação:")
    for f in curtas:
        print(f"   {len(f['corpo']):>6} car.  {f['mun']}/{f['uf']}")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
