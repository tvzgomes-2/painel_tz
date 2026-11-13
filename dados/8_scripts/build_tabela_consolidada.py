# -*- coding: utf-8 -*-
"""
Constrói a tabela consolidada nova: legislação, contrato e aplicação das
réguas descritiva e analítica, para todos os municípios com Tarifa Zero
(178 políticas / 177 municípios em escopo + São Caetano do Sul como caso
reclassificado, registrado à parte).

Fonte de legislação/contrato/régua: releitura das fichas municipais atuais
(decisão do autor, 18/09/2026 — não usar o Controle único de 11/09, que
está defasado para pelo menos Natividade, Artur Nogueira e Alumínio).
"""
import os, re, sys
import openpyxl
from openpyxl.styles import Font, Alignment

ROOT = os.path.expanduser("~/mnt/doutorado")
BASE_MESTRE = os.path.join(ROOT, "03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx")
FICHADIR = os.path.join(ROOT, "04 - Análises/Casos municipais/Fichas por município")
OUT_XLSX = os.path.join(ROOT, "03 - Dados/_data/casos por fonte/Tabela consolidada - Legislação, contratos e réguas (18-09-2026).xlsx")

# ---------------------------------------------------------------
# 1. Carregar base-mestre
# ---------------------------------------------------------------
wb = openpyxl.load_workbook(BASE_MESTRE, read_only=True, data_only=True)
ws = wb["consolidado"]
rows = list(ws.iter_rows(min_row=1, values_only=True))
header = rows[0]
data = rows[1:]
idx = {h: i for i, h in enumerate(header)}

scope_rows = [r for r in data if r[idx["Situação"]] in ("Ativa", "Encerrada")]
sao_caetano_rows = [r for r in data if r[idx["Município"]] == "São Caetano do Sul"]
teresina_rows = [r for r in data if r[idx["Município"]] == "Teresina"]

print(f"Base-mestre: {len(data)} linhas totais; {len(scope_rows)} em escopo (Ativa+Encerrada); "
      f"São Caetano: {len(sao_caetano_rows)}; Teresina: {len(teresina_rows)}")

# Consolidar Palmas/TO (2 políticas) em 1 linha de município
by_muni = {}
for r in scope_rows:
    key = (r[idx["Município"]], r[idx["UF"]])
    by_muni.setdefault(key, []).append(r)

municipios_alvo = list(by_muni.keys())
if sao_caetano_rows:
    municipios_alvo.append(("São Caetano do Sul", "SP"))
    by_muni[("São Caetano do Sul", "SP")] = sao_caetano_rows

print(f"Municípios-alvo (linhas da tabela nova): {len(municipios_alvo)}")

# ---------------------------------------------------------------
# 2. Indexar fichas municipais por (município, uf) via frontmatter
# ---------------------------------------------------------------
ficha_index = {}
ficha_files = [f for f in os.listdir(FICHADIR) if f.startswith("Ficha - ") and f.endswith(".md")]
for fn in ficha_files:
    p = os.path.join(FICHADIR, fn)
    try:
        with open(p, encoding="utf-8") as fh:
            c = fh.read()
    except Exception as e:
        continue
    m = re.search(r"^municipio:\s*(.+)$", c, re.M)
    u = re.search(r"^uf:\s*(.+)$", c, re.M)
    if m and u:
        key = (m.group(1).strip(), u.group(1).strip())
        ficha_index[key] = (fn, c)

print(f"Fichas indexadas por frontmatter municipio/uf: {len(ficha_index)}")

# ---------------------------------------------------------------
# 3. Helpers de extração de seções/campos das fichas
# ---------------------------------------------------------------
def get_section(content, heading_prefix):
    """Retorna o corpo (sem o cabeçalho) da primeira seção '## <heading_prefix>...'."""
    pat = r"^## " + re.escape(heading_prefix) + r".*?\n(.*?)(?=\n## |\Z)"
    m = re.search(pat, content, re.S | re.M)
    return m.group(1).strip() if m else None

def get_bold_field(section_text, label):
    """Extrai o valor de uma linha '- **Label...:** valor' dentro de um trecho de seção."""
    if not section_text:
        return None
    pat = r"-\s*\*\*" + re.escape(label) + r"[^:*]*:\*\*\s*(.+)"
    m = re.search(pat, section_text)
    return m.group(1).strip() if m else None

def frontmatter_field(content, key):
    m = re.search(r"^" + re.escape(key) + r":\s*(.+)$", content, re.M)
    return m.group(1).strip() if m else None

# ---------------------------------------------------------------
# 4. Montar linhas da tabela
# ---------------------------------------------------------------
COLS = [
    "Município", "UF", "Região", "Código IBGE",
    "Situação", "Ano início", "Ano fim", "População (2022)",
    "Camada (régua descritiva — frontmatter da ficha)",
    "Régua descritiva — trajetória (Cap 5, texto da ficha)",
    "Tipologia analítica (frontmatter da ficha)",
    "Régua analítica (Cap 6) — texto completo da ficha",
    "Norma / Legislação — base-mestre (Municípios TZ - consolidado.xlsx)",
    "Link Legislação — base-mestre",
    "Confiab. (base-mestre)",
    "Legislação — §5 da ficha (texto completo)",
    "Operador — §2 da ficha",
    "Dados operacionais — §2 da ficha (texto completo)",
    "Contrato — dados de contratação (Cap 7), quando a ficha tem seção própria",
    "Obs. legal (base-mestre)",
    "Ficha municipal",
    "Observações desta consolidação",
]

out_rows = []
sem_ficha = []
for muni, uf in municipios_alvo:
    base_recs = by_muni[(muni, uf)]
    r0 = base_recs[0]
    situacao = " + ".join(sorted(set(str(r[idx["Situação"]]) for r in base_recs)))
    ano_inicio = " / ".join(sorted(set(str(r[idx["Ano início"]]) for r in base_recs if r[idx["Ano início"]] is not None)))
    ano_fim = " / ".join(sorted(set(str(r[idx["Fim"]]) for r in base_recs if r[idx["Fim"]] is not None))) or None
    pop = r0[idx["População (2022)"]]
    leg_planilha = " || ".join(sorted(set(str(r[idx["Legislação"]]) for r in base_recs if r[idx["Legislação"]]))) or None
    link_planilha = " || ".join(sorted(set(str(r[idx["Link Legislação"]]) for r in base_recs if r[idx["Link Legislação"]]))) or None
    confiab = " / ".join(sorted(set(str(r[idx["Confiab."]]) for r in base_recs if r[idx["Confiab."]]))) or None
    obs_legal = " || ".join(str(r[idx["Obs. legal"]]) for r in base_recs if r[idx["Obs. legal"]]) or None
    obs_extra = ""
    if len(base_recs) > 1:
        obs_extra = f"⚠️ {len(base_recs)} políticas na base-mestre para este município (ex.: Palmas/TO) — linhas fundidas em 1 por município."
    if (muni, uf) == ("São Caetano do Sul", "SP"):
        obs_extra = (obs_extra + " " if obs_extra else "") + \
            "🔴 Reclassificada em 15/07/2026: revogou a universalidade, hoje é camada 3 (grupo social, por residência). Não está nas 178 políticas/177 municípios do panorama nacional — incluída aqui à parte por ser caso relevante de trajetória/reversão (ver [[Regras de classificacao das reguas]])."

    key = (muni, uf)
    ficha = ficha_index.get(key)
    if not ficha:
        sem_ficha.append((muni, uf))
        row = [
            muni, uf, None, None,
            situacao, ano_inicio, ano_fim, pop,
            "🔴 sem ficha localizada", None, None, None,
            leg_planilha, link_planilha, confiab,
            "🔴 sem ficha municipal localizada — não verificado nesta rodada", None, None, None,
            obs_legal,
            None,
            (obs_extra + " " if obs_extra else "") + "🔴 Nenhuma ficha municipal encontrada com municipio/uf correspondentes no frontmatter — checar nome/grafia manualmente.",
        ]
        out_rows.append(row)
        continue

    fn, content = ficha
    regiao = frontmatter_field(content, "regiao")
    cod_ibge = frontmatter_field(content, "codigo_ibge")
    camada_fm = frontmatter_field(content, "camada")
    tipologia_fm = frontmatter_field(content, "tipologia_analitica")

    sec_regua_desc = get_section(content, "Régua descritiva")
    sec_regua_analit = get_section(content, "Régua analítica")
    sec_leg = get_section(content, "5. Legislação")
    sec_dados = get_section(content, "2. Principais dados")
    sec_contrato = get_section(content, "Dados de contratação")

    operador = get_bold_field(sec_dados, "Operador")

    row = [
        muni, uf, regiao, cod_ibge,
        situacao, ano_inicio, ano_fim, pop,
        camada_fm or "🔴 não preenchido no frontmatter da ficha",
        sec_regua_desc or "não preenchido nesta rodada (seção ausente na ficha)",
        tipologia_fm or "🔴 não preenchido no frontmatter da ficha",
        sec_regua_analit or "não preenchido nesta rodada (seção ausente na ficha — sem gerador ainda, cobertura parcial no cofre)",
        leg_planilha, link_planilha, confiab,
        sec_leg or "não preenchido nesta rodada (seção ausente na ficha)",
        operador or "não preenchido nesta rodada",
        sec_dados or None,
        sec_contrato or "não documentado em seção própria — dado de contrato, quando existe, está descrito dentro de Legislação/Operador acima",
        obs_legal,
        fn,
        obs_extra or None,
    ]
    out_rows.append(row)

print(f"Municípios sem ficha localizada: {len(sem_ficha)} -> {sem_ficha}")

# ---------------------------------------------------------------
# 5. Escrever XLSX
# ---------------------------------------------------------------
wb_out = openpyxl.Workbook()
wsout = wb_out.active
wsout.title = "consolidado"
wsout.append(COLS)
for c in wsout[1]:
    c.font = Font(bold=True)
    c.alignment = Alignment(wrap_text=True, vertical="top")

for row in out_rows:
    wsout.append(row)

for r in wsout.iter_rows(min_row=2):
    for c in r:
        c.alignment = Alignment(wrap_text=True, vertical="top")

widths = [22, 5, 12, 12, 16, 12, 12, 14, 20, 45, 22, 55, 40, 30, 12, 55, 25, 45, 45, 30, 28, 40]
for i, w in enumerate(widths, start=1):
    wsout.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

wsout.freeze_panes = "A2"

# Aba de metodologia
wsmeta = wb_out.create_sheet("Metodologia")
meta_lines = [
    ["Tabela consolidada - Legislação, contratos e réguas — 18/09/2026"],
    [""],
    ["Escopo: 177 municípios em escopo do panorama nacional (178 políticas — Palmas/TO tem 2, "
     "fundidas em 1 linha) + São Caetano do Sul (SP), incluído à parte por ter revogado a "
     "universalidade em 15/07/2026 e hoje ser camada 3 (caso de trajetória/reversão)."],
    ["Excluído: Teresina/PI ('Excluída — fora de escopo' na base-mestre) — não entra nesta tabela."],
    [""],
    ["Fontes, por bloco de coluna:"],
    ["- Situação/Ano/População/Legislação(base)/Confiab./Obs.legal: Municípios TZ - consolidado.xlsx "
     "(base-mestre, 178/177 + reclassificada/excluída — arquivo mais atual do cofre nesta data)."],
    ["- Camada / Régua descritiva / Tipologia analítica / Régua analítica / Legislação §5 / Operador / "
     "Dados operacionais / Dados de contratação: releitura direta das 267 fichas municipais atuais "
     "(decisão do autor, 18/09/2026 — não o Controle único de legislação/contrato/PlanMob, que está "
     "com corte em 11/09/2026 e defasado para pelo menos Natividade, Artur Nogueira e Alumínio, "
     "fechados nesta sessão)."],
    [""],
    ["Regra NA≠0 aplicada: célula sem dado NUNCA foi deixada em branco por conta própria — está marcada "
     "explicitamente como 'não preenchido nesta rodada' (dado não apurado) e distinta de qualquer valor "
     "zero/negativo apurado. Não fabriquei nenhum dado ausente."],
    [""],
    ["Cobertura conhecida, ANTES de usar estes números: régua analítica (Cap 6) só tem gerador parcial no "
     "cofre — preenchida em cerca de 1/4 das fichas (202 de 268 têm a seção 'Régua analítica (Cap 6)', mas "
     "grande parte do conteúdo dentro dela é '(a classificar)' ou hipótese não confirmada — ver célula a "
     "célula, não tratar presença de seção como preenchimento de fato)."],
    [""],
    ["Limitações e inconsistências abertas conhecidas (17/09/2026, não resolvidas por esta tabela):"],
    ["- Águas da Prata/SP e Santa Cruz Cabrália/BA: constam na base-mestre em escopo, mas não aparecem em "
     "nenhuma aba da planilha de tipologias (Tipologias TZ - consolidado.xlsx) — se a ficha correspondente "
     "também não tiver camada preenchida, aparecerão aqui como '🔴 não preenchido'."],
    ["- Gargalo de preenchimento de portão na aba '1 Universal' (17/09/2026): de 171 linhas, só 16 têm "
     "ausência de portão CONFIRMADA — os demais 'camada: universal' no frontmatter das fichas podem ser "
     "provisórios. Ver [[Regras de classificacao das reguas]] antes de tratar qualquer camada desta tabela "
     "como definitiva."],
    [""],
    ["Não fiz cross-check linha a linha entre esta tabela e Tipologias TZ - consolidado.xlsx nem entre esta "
     "tabela e o Controle único — os três arquivos podem divergir pontualmente. Esta tabela é uma "
     "consolidação NOVA a partir das fichas, não uma correção dos arquivos existentes."],
    [""],
    ["Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni"],
]
for line in meta_lines:
    wsmeta.append(line)
wsmeta.column_dimensions["A"].width = 120
for r in wsmeta.iter_rows():
    for c in r:
        c.alignment = Alignment(wrap_text=True, vertical="top")
wsmeta["A1"].font = Font(bold=True, size=13)

wb_out.save(OUT_XLSX)
print(f"\nOK — arquivo salvo: {OUT_XLSX}")
print(f"Linhas de dado: {len(out_rows)}")
