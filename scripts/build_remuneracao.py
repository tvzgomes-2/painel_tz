# -*- coding: utf-8 -*-
"""
build_remuneracao.py — gera scripts/remuneracao_tz.json: COMO o operador da Tarifa Zero é
pago e QUANTO custa, por município (Seções 7.2 a 7.4 da tese; pedido do autor, 23/10/2026:
"a seção de remuneração do cap 7 é importante ser incorporada").

Fontes, todas do pacote 5 da tese ("05 Arranjo, contratos e custos.xlsx"):
  - destinatario_contrapartida: o destinatário do recurso em quatro categorias (operação
    pública, operador pago pela oferta, pago pela demanda, recurso ao usuário). Só a coluna
    do DESTINATÁRIO entrava até a v0.15; desde a v1.0.0 (13/11/2026) entra também a contrapartida.
  - arranjo_D1_D5: a fórmula de remuneração (por km, valor global fixo, por veículo, custo
    do serviço, por passageiro, combinações) e a força da prova da leitura.
  - preco_km_41_contratos: preço do quilômetro em reais de maio de 2026 (IPCA).
  - custo_por_habitante: valor anual do contrato lido ÷ população de 2022.

FRONTEIRA (decisões do autor de 23/10/2026): entra a remuneração — quem recebe, por qual
fórmula, quem carrega o risco de demanda e quanto se paga. Desde 13/11/2026 entra a contrapartida (três estados); fica FORA a
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
# 13/11/2026 (v1.0.0): base de 11/11/2026. As abas do pacote 5 de 22/10 dão lugar às tabelas
# depositadas em dados/5_arranjo_contratos/ (DOI 10.5281/zenodo.24186039) — lidas, nunca escritas
# — e, no arranjo A1–A6, ao levantamento harmonizado com a base de 11/11 (r102), que é o que a
# tese usa e não está no depósito. TZ_PACOTE5 volta ao pacote antigo, para refazer a v0.15.
DADOS5 = os.path.join(BASE_DIR, '..', 'dados', '5_arranjo_contratos')
CSV5 = {'arranjo_D1_D5': 'arranjo_operacional_D1_D5.csv', 'destinatario_contrapartida': 'destinatario_contrapartida.csv',
        'preco_km_41_contratos': 'preco_km_contratos.csv', 'custo_por_habitante': 'custo_habitante_contratos.csv',
        'custeio_no_ato': 'custeio_no_ato.csv',
        'arranjo_A1_A6': os.path.join(VAULT, '03 - Dados', '_data', 'Analises_Cap5_r75', 'arranjo_A1-A6_base-2026-11-11_r102.csv')}
def ler(aba):
    if os.environ.get('TZ_PACOTE5'):
        return pd.read_excel(os.environ['TZ_PACOTE5'], sheet_name=aba)
    f = CSV5[aba]
    f = f if os.path.isabs(f) else os.path.join(DADOS5, f)
    print(f'fonte de {aba}: {os.path.relpath(f, os.path.join(BASE_DIR, ".."))}')
    return pd.read_csv(f)
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
dc = ler('destinatario_contrapartida')
for _, r in dc.iterrows():
    c = cod7(r.get('Código IBGE')); d = DEST.get(txt(r.get('dest4')))
    if c and d: out[c]['dest'] = d; cont['destinatário'] += 1
    # 13/11/2026 (v1.0.0, decisão do autor: "atualizar tudo para base nova"): a CONTRAPARTIDA entra,
    # nos três estados da regra B.1.3 (com, sem, não apurado) e com os itens: C controle social,
    # T transparência específica do programa, D monitoramento de desempenho. Segue fora a posição
    # de cada política no plano analítico (Seção 7.6 da tese).
    est = txt(r.get('Contrapartida — estado')) or ('não apurado' if c else None)
    if c and est:
        out[c]['cp'] = {'com': 'com', 'sem': 'sem'}.get(est, 'nd')
        itens = txt(r.get('Contrapartida — itens'))
        if itens: out[c]['cpi'] = itens.replace(' ', '')
        leit = txt(r.get('Contrapartida — leitura'))
        if leit: out[c]['cpl'] = leit
        cont['contrapartida ' + out[c]['cp']] += 1

PROVA = {'cláusula lida': 'alta', 'edital/TR': 'alta', 'fonte secundária': 'media'}
d5 = ler('arranjo_D1_D5')
for _, r in d5.iterrows():
    c = cod7(r.get('Código IBGE')); comp = txt(r.get('Remuneração — componentes'))
    if not c or not comp or comp.startswith('não se aplica'): continue
    out[c]['comp'] = comp
    p = PROVA.get(txt(r.get('Remuneração — leitura')))
    if p: out[c]['comp_prova'] = p
    cont['fórmula'] += 1

FONTE_KM = {'doc': 'lido em documento', 'sec': 'fonte secundária', 'calc': 'valor anual ÷ quilometragem do termo de referência'}
pk = ler('preco_km_41_contratos')
for _, r in pk.iterrows():
    c = cod_nome(r['mun'], r['uf'])
    if not c: cont['preço/km sem município'] += 1; continue
    nota = txt(r.get('nota'))
    if nota and RE_GRUPO.search(nota):
        nota = None; cont['nota de preço/km retirada (cita grupo)'] += 1
    out[c].setdefault('km', []).append({'v': round(float(r['v26']), 2), 'fonte': FONTE_KM.get(str(r['src']), str(r['src'])),
                                        'arr': txt(r.get('A')), 'nota': nota})
    cont['contratos com preço/km'] += 1

ch = ler('custo_por_habitante')
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
