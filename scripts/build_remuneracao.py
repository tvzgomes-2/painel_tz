# -*- coding: utf-8 -*-
"""
build_remuneracao.py — gera scripts/remuneracao_tz.json: COMO o operador da Tarifa Zero é
pago e QUANTO custa, por município (Seções 7.2 a 7.4 da tese; pedido do autor, 23/10/2026:
"a seção de remuneração do cap 7 é importante ser incorporada").

Fontes, todas do pacote 5 da tese ("05 Arranjo, contratos e custos.xlsx"):
  - destinatario_contrapartida: o destinatário do recurso em quatro categorias (operação
    pública, operador pago pela oferta, pago pela demanda, recurso ao usuário). Só a coluna
    do DESTINATÁRIO entra — a contrapartida não (ver fronteira abaixo).
  - arranjo_D1_D5: a fórmula de remuneração (por km, valor global fixo, por veículo, custo
    do serviço, por passageiro, combinações) e a força da prova da leitura.
  - preco_km_41_contratos: preço do quilômetro em reais de maio de 2026 (IPCA).
  - custo_por_habitante: valor anual do contrato lido ÷ população de 2022.

FRONTEIRA (decisões do autor de 23/10/2026): entra a remuneração — quem recebe, por qual
fórmula, quem carrega o risco de demanda e quanto se paga. Fica FORA a contrapartida e a
posição no plano analítico (gestão do comum, garantia de receita sem controle,
"Bolsa-Empresário"), suspensas até a defesa (12.6); e fica fora a coluna de grupo econômico
de custo_por_habitante e qualquer nota que cite grupo (a análise de grupos vai para a Rede
da ARS).

Uso:  python3 scripts/build_remuneracao.py        (da raiz do repositório)
"""
import json, os, re
from collections import Counter, defaultdict
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(BASE_DIR, '..', '..', 'doutorado')
PACOTE = os.path.join(VAULT, '01 - Projeto', 'Envio à orientadora — 24-11-2026',
                      '02 Bases de dados (xlsx)', '05 Arranjo, contratos e custos.xlsx')
BASE_JSON = os.path.join(BASE_DIR, '..', 'build', 'municipios_dados.json')
OUT = os.path.join(BASE_DIR, 'remuneracao_tz.json')
RE_GRUPO = re.compile(r'grupos? econ|GE-\d{3}|\bgrupo [A-Z]', re.I)

def txt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return None
    s = re.sub(r'\s+', ' ', str(v)).strip()
    return None if s.lower() in ('', 'nan', 'none', 'sem informação', 'não apurado') else s

def cod7(v):
    try: return str(int(float(v)))
    except (TypeError, ValueError): return None

import unicodedata
def chave(n, uf):
    s = unicodedata.normalize('NFD', str(n)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r"[^A-Za-z0-9 ]", ' ', s)).strip().upper() + '|' + str(uf).strip().upper()
base = json.load(open(BASE_JSON, encoding='utf-8'))
NOME2COD = {chave(r['nome'], r['uf']): str(r['id']) for r in base}
ALIAS = {'EMBU DAS ARTES|SP': '3515004'}
def cod_nome(n, uf):
    k = chave(n, uf); return NOME2COD.get(k) or ALIAS.get(k)

out = defaultdict(dict)
cont = Counter()

DEST = {'(i) operação pública': 'publica', '(ii) oferta': 'oferta', '(iii) demanda': 'demanda',
        '(iv) usuário': 'usuario', 'privado, remuneração não apurada': 'privado_nd'}
dc = pd.read_excel(PACOTE, sheet_name='destinatario_contrapartida')
for _, r in dc.iterrows():
    c = cod7(r.get('Código IBGE')); d = DEST.get(txt(r.get('dest4')))
    if c and d: out[c]['dest'] = d; cont['destinatário'] += 1

PROVA = {'cláusula lida': 'alta', 'edital/TR': 'alta', 'fonte secundária': 'media'}
d5 = pd.read_excel(PACOTE, sheet_name='arranjo_D1_D5')
for _, r in d5.iterrows():
    c = cod7(r.get('Código IBGE')); comp = txt(r.get('Remuneração — componentes'))
    if not c or not comp or comp.startswith('não se aplica'): continue
    out[c]['comp'] = comp
    p = PROVA.get(txt(r.get('Remuneração — leitura')))
    if p: out[c]['comp_prova'] = p
    cont['fórmula'] += 1

FONTE_KM = {'doc': 'lido em documento', 'sec': 'fonte secundária', 'calc': 'valor anual ÷ quilometragem do termo de referência'}
pk = pd.read_excel(PACOTE, sheet_name='preco_km_41_contratos')
for _, r in pk.iterrows():
    c = cod_nome(r['mun'], r['uf'])
    if not c: cont['preço/km sem município'] += 1; continue
    nota = txt(r.get('nota'))
    if nota and RE_GRUPO.search(nota):
        nota = None; cont['nota de preço/km retirada (cita grupo)'] += 1
    out[c].setdefault('km', []).append({'v': round(float(r['v26']), 2), 'fonte': FONTE_KM.get(str(r['src']), str(r['src'])),
                                        'arr': txt(r.get('A')), 'nota': nota})
    cont['contratos com preço/km'] += 1

ch = pd.read_excel(PACOTE, sheet_name='custo_por_habitante')
for _, r in ch.iterrows():
    c = cod_nome(r['municipio'], r['uf'])
    if not c: cont['custo/hab sem município'] += 1; continue
    arr = txt(r.get('arranjo'))
    if arr and RE_GRUPO.search(arr): arr = None
    out[c].setdefault('hab', []).append({'v': round(float(r['r_hab_ano']), 2), 'ano': int(r['ano_preco']), 'arr': arr})
    cont['contratos com custo/hab'] += 1

out = {k: out[k] for k in sorted(out, key=int)}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, separators=(',', ':')); f.write('\n')
print(f'remuneracao_tz.json: {len(out)} municípios, {os.path.getsize(OUT)/1024:.0f} KB')
for k, v in cont.most_common(): print(f'   {v:4d}  {k}')
