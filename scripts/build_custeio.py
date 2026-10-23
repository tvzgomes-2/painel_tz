# -*- coding: utf-8 -*-
"""
build_custeio.py — gera scripts/custeio_tz.json: o que o ATO da política escreve sobre o
custeio (Seção 7.5 e Tabela 9 da tese; pedido do autor, 23/10/2026: "aplique tudo").

Fonte: aba `custeio_no_ato` do pacote 5 da tese (150 atos lidos com arquivo, base de
21/10/2026): instrumento (lei, lei complementar, decreto), o que o texto diz sobre a fonte
(dotação genérica, sem cláusula, fontes específicas, classificação orçamentária), as fontes
nomeadas e a condição que o próprio ato impõe à gratuidade.

A ESCALA DE COMPROMISSO (Quadro 28: receita vinculada / fundo / dotação / orçamento geral)
não tem uma coluna por política no pacote — a tese a apresenta em contagens. Por isso ela
entra no painel como bloco fixo, com os números do Quadro 28, e não daqui.

Uso:  python3 scripts/build_custeio.py        (da raiz do repositório)
"""
import json, os, re, unicodedata
from collections import Counter
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(BASE_DIR, '..', '..', 'doutorado')
PACOTE = os.path.join(VAULT, '01 - Projeto', 'Envio à orientadora — 24-11-2026',
                      '02 Bases de dados (xlsx)', '05 Arranjo, contratos e custos.xlsx')
BASE_JSON = os.path.join(BASE_DIR, '..', 'build', 'municipios_dados.json')
OUT = os.path.join(BASE_DIR, 'custeio_tz.json')

def txt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return None
    s = re.sub(r'\s+', ' ', str(v)).strip()
    return s or None
def chave(n, uf):
    s = unicodedata.normalize('NFD', str(n)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r"[^A-Za-z0-9 ]", ' ', s)).strip().upper() + '|' + str(uf).strip().upper()
base = json.load(open(BASE_JSON, encoding='utf-8'))
NOME2COD = {chave(r['nome'], r['uf']): str(r['id']) for r in base}
ALIAS = {'EMBU DAS ARTES|SP': '3515004'}

def nome_ato(arquivo, mun, uf):
    """'Mata de São João-BA - Lei 945-2023 (11-12-2023) - texto integral (SAPL).pdf' -> 'Lei 945-2023 (11-12-2023)'"""
    a = txt(arquivo)
    if not a: return None
    a = re.sub(r'\.(pdf|txt|docx?|html?)$', '', a, flags=re.I)
    a = re.sub(r'^.*?-' + re.escape(uf) + r'\s*-\s*', '', a)
    # só o instrumento, o número e a data: o resto do nome do arquivo é descrição de trabalho,
    # sem acento e com marcas internas ("captura do Zotero", "SAPL")
    m = re.match(r'(Lei Complementar|Lei Ordin[aá]ria|Lei|LC|Decreto(?: Legislativo)?|Portaria|Resolu[cç][aã]o|Contrato)'
                 r'(?:\s+(?:n[º°o.]*|municipal))?\s*([\d][\d./-]*)(?:[,\s]+de\s+[^—-]{4,30}?\d{4})?(\s*\(\d{2}-\d{2}-\d{4}\))?', a, re.I)
    if not m: return None
    return re.sub(r'\s+', ' ', m.group(0)).strip()

df = pd.read_excel(PACOTE, sheet_name='custeio_no_ato')
out, cont, sem = {}, Counter(), []
for _, r in df.iterrows():
    mun, uf = txt(r['municipio']), txt(r['uf'])
    cod = NOME2COD.get(chave(mun, uf)) or ALIAS.get(chave(mun, uf))
    if not cod: sem.append(f'{mun}/{uf}'); continue
    e = {k: v for k, v in {
        'ato': nome_ato(r.get('arquivo'), mun, uf), 'instr': txt(r.get('instrumento')),
        'leit': txt(r.get('leitura')), 'fontes': txt(r.get('fontes')),
        'classif': txt(r.get('classificacao_orcamentaria')), 'cond': txt(r.get('condicionante'))}.items() if v}
    out.setdefault(cod, []).append(e)
    cont[e.get('leit', '?')] += 1
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({k: out[k] for k in sorted(out, key=int)}, f, ensure_ascii=False, separators=(',', ':')); f.write('\n')
print(f'custeio_tz.json: {sum(len(v) for v in out.values())} atos em {len(out)} municípios, {os.path.getsize(OUT)/1024:.0f} KB')
for k, v in cont.most_common(): print(f'   {v:4d}  {k}')
if sem:
    print('  [ERRO] sem município na base:', sem); raise SystemExit(1)
