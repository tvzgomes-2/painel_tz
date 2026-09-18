# -*- coding: utf-8 -*-
"""
build_legislacao_padrao.py — padroniza a legislacao e incorpora a tabela consolidada do cofre.

Roda DEPOIS de build_legislacao.py, que continua sendo a fonte dos 137 registros
(mecanismo, fundo e ressalvas vem dos .md da Pesquisa legal). Este script:

  1. le scripts/legislacao_tz.json (saida do build_legislacao.py);
  2. le a "Tabela consolidada - Legislacao, contratos e reguas" mais recente do cofre,
     que cobre os 178 casos canonicos e traz link do texto e confiabilidade por caso;
  3. decompoe cada norma em tipo / numero / ano / data e grava tambem a string curta
     de exibicao e a extensa, para o painel nunca mais depender do formato da origem.

Por que decompor em vez de limpar a string: as 173 strings de origem usam 11 grafias
para 3 tipos normativos ("Lei", "Lei Municipal", "Lei Ordinaria", "Lei Ordinaria
Municipal"...), numero com e sem separador de milhar, e data em tres formatos. Um
campo por informacao deixa a exibicao ser uma decisao do painel, nao da planilha.

A coluna de norma da tabela tem celulas preenchidas com "nao encontrei" / "nao
localizada": isso NAO e uma norma, e sim a informacao de que a busca foi feita e deu
em nada. Vira o flag `buscada`, que o painel usa para nao dizer "ainda nao passou pela
busca de norma" a quem ja passou.

Saida: sobrescreve scripts/legislacao_tz.json com os campos novos, preservando
mecanismo/fundo/nota. Rode a partir da raiz do repositorio:
    python3 scripts/build_legislacao.py && python3 scripts/build_legislacao_padrao.py
"""
import json, re, unicodedata, glob, os
from pathlib import Path
import pandas as pd

VAULT = Path.home() / "mnt" / "doutorado" / "03 - Dados" / "_data" / "casos por fonte"
REPO = Path.home() / "mnt" / "painel TZ"
OUT = REPO / "scripts" / "legislacao_tz.json"

MESES = ['janeiro','fevereiro','março','abril','maio','junho','julho','agosto',
         'setembro','outubro','novembro','dezembro']
MES_IX = {m: i + 1 for i, m in enumerate(MESES)}

def low(s):
    return unicodedata.normalize("NFKD", (s or "")).lower()

# ordem importa: "lei complementar" antes de "lei"
TIPOS = [(r"lei\s+complementar", "Lei Complementar"),
         (r"decreto\s+legislativo", "Decreto Legislativo"),
         (r"decreto", "Decreto"),
         (r"lei\s+ordin[áa]ria", "Lei Ordinária"),
         (r"lei", "Lei Ordinária")]

NEGATIVA = re.compile(r"^(não encontrei|não localizad|sem lei|não identificad|n/?a$|—$|-$)", re.I)

def milhar(n):
    """2199 -> 2.199 ; 945 -> 945 ; ja separado fica como esta."""
    if "." in n:
        return n
    return f"{int(n):,}".replace(",", ".") if n.isdigit() and len(n) > 3 else n

def parse_norma(s):
    """Decompoe uma string de norma. Devolve None se nao houver tipo+numero."""
    tipo = None
    for pat, nome in TIPOS:
        if re.search(r"\b" + pat + r"\b", low(s)):
            tipo = nome
            break
    m = re.search(r"n?[ºo°]?\s*([\d][\d.]*)\s*(?:/(\d{4}))?", s)
    if not (tipo and m):
        return None
    numero = milhar(m.group(1).rstrip("."))
    ano_barra = m.group(2)

    data = None
    d = re.search(r"de\s+(\d{1,2})[ºo°]?\s+de\s+(\w+)\s+de\s+(\d{4})", low(s))
    if d and d.group(2) in MES_IX:
        data = f"{d.group(3)}-{MES_IX[d.group(2)]:02d}-{int(d.group(1)):02d}"
    else:
        d2 = re.search(r"(\d{2})/(\d{2})/(\d{4})", s)
        if d2:
            data = f"{d2.group(3)}-{d2.group(2)}-{d2.group(1)}"

    ano = int(data[:4]) if data else (int(ano_barra) if ano_barra else None)
    if ano is None:
        y = re.search(r"\b(?:19|20)\d{2}\b", s)
        ano = int(y.group(0)) if y else None
    if ano is None:
        return None

    reg = {"tipo": tipo, "numero": numero, "ano": ano,
           "norma": f"{tipo} nº {numero}/{ano}"}
    if data:
        y, mm, dd = data.split("-")
        dia = "1º" if int(dd) == 1 else str(int(dd))
        reg["data"] = data
        reg["norma_ext"] = f"{tipo} nº {numero}, de {dia} de {MESES[int(mm)-1]} de {y}"
    # segunda norma citada na mesma celula
    resto = s[m.end():]
    m2 = re.search(r"\b[Ll]ei[^\d]{0,30}n?[ºo°]?\s*([\d][\d.]*)/(\d{4})", resto)
    if m2:
        reg["extra"] = f"Lei nº {milhar(m2.group(1))}/{m2.group(2)}"
    return reg

def parse_conf(v):
    """'alta (texto integral lido...)' -> ('alta', 'texto integral lido...')"""
    if v is None:
        return None, None
    s = re.sub(r"\s+", " ", str(v)).strip()
    if not s or s in ("—", "-", "nan"):
        return None, None
    m = re.match(r"(alta|média-alta|baixa-média|média|baixa)\b[\s:—-]*(.*)", low(s))
    if not m:
        return None, s
    rotulo = {"média-alta": "média", "baixa-média": "baixa"}.get(m.group(1), m.group(1))
    nota = s[m.end(1):].strip(" ()—-:;.")
    # o rotulo costuma vir como 'alta (texto lido...)': ao tirar o '(' de abertura sobra
    # um ')' orfao no meio da frase. Remove os fechamentos sem par, da esquerda para a direita.
    saldo, limpo = 0, []
    for ch in nota:
        if ch == "(":
            saldo += 1
        elif ch == ")":
            if saldo == 0:
                continue
            saldo -= 1
        limpo.append(ch)
    nota = "".join(limpo).strip(" —-:;.") or None
    return rotulo, nota

# ---------- 1. base: saida do build_legislacao.py ----------
reg = json.loads(OUT.read_text(encoding="utf-8"))
antes_com_norma = sum(1 for v in reg.values() if v.get("norma"))

# ---------- 2. tabela consolidada mais recente do cofre ----------
cands = sorted(glob.glob(str(VAULT / "Tabela consolidada - Legislação, contratos e réguas*.xlsx")),
               key=os.path.getmtime)
if not cands:
    raise SystemExit("tabela consolidada nao encontrada no cofre")
tab = cands[-1]
print(f"tabela consolidada: {os.path.basename(tab)}")
d = pd.read_excel(tab, sheet_name="consolidado")
col = lambda p: next(c for c in d.columns if c.startswith(p))
c_norma, c_link, c_conf = col("Norma"), col("Link"), col("Confiab")
d["cod"] = d["Código IBGE"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

novos = padronizados = com_link = buscadas = falhas = 0
nao_parseadas = []
for _, r in d.iterrows():
    cod = r["cod"]
    if not cod or cod == "nan":
        continue
    bruto = "" if pd.isna(r[c_norma]) else re.sub(r"\s+", " ", str(r[c_norma])).strip()
    alvo = reg.setdefault(cod, {})
    if bruto and not NEGATIVA.match(bruto):
        p = parse_norma(bruto)
        if p:
            if not alvo.get("norma"):
                novos += 1
            alvo.update(p)
            alvo["norma_orig"] = bruto
            padronizados += 1
        else:
            falhas += 1
            nao_parseadas.append(f"{r['Município']}/{r['UF']}: {bruto[:60]}")
            alvo["norma"] = bruto           # preserva o texto, sem fingir estrutura
            alvo["norma_orig"] = bruto
    elif bruto:
        alvo["buscada"] = True             # busca feita, norma nao localizada
        buscadas += 1
    if not pd.isna(r[c_link]) and str(r[c_link]).startswith("http"):
        alvo["link"] = str(r[c_link]).strip()
        com_link += 1
    cf, cn = parse_conf(r[c_conf])
    if cf:
        alvo["conf"] = cf
    if cn:
        alvo["conf_nota"] = cn
    if not alvo:
        reg.pop(cod, None)

# ---------- 3. padroniza tambem os registros que ja vinham do .md ----------
for cod, v in reg.items():
    if v.get("norma") and not v.get("tipo"):
        p = parse_norma(v["norma"])
        if p:
            v["norma_orig"] = v["norma"]
            v.update(p)
            padronizados += 1
        else:
            falhas += 1
            nao_parseadas.append(f"[{cod}] {v['norma'][:60]}")

OUT.write_text(json.dumps(reg, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
               encoding="utf-8")

com_norma = sum(1 for v in reg.values() if v.get("norma"))
estrut = sum(1 for v in reg.values() if v.get("tipo"))
com_data = sum(1 for v in reg.values() if v.get("data"))
print(f"legislacao_tz.json: {len(reg)} municipios ({antes_com_norma} -> {com_norma} com norma; +{novos} novas)")
print(f"  decompostas em tipo/numero/ano: {estrut} | com data completa: {com_data}")
print(f"  com link para o texto: {sum(1 for v in reg.values() if v.get('link'))}")
print(f"  marcadas como buscada-e-nao-localizada: {buscadas}")
print(f"  confiabilidade: " + ", ".join(
    f"{c}={sum(1 for v in reg.values() if v.get('conf')==c)}" for c in ("alta", "média", "baixa")))
if nao_parseadas:
    print(f"  NAO decompostas ({falhas}) — exibidas como vieram:")
    for x in nao_parseadas:
        print(f"    - {x}")
print(f"  tamanho: {OUT.stat().st_size/1024:.0f} KB")
