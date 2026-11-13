import re  # A.1.15
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""retrato_base_cap5.py — retrato congelado da base de Tarifa Zero para o Cap. 5.

Uso: python3 retrato_base_cap5.py AAAA-MM-DD
Lê as cópias congeladas em 03 - Dados/_data/casos por fonte/retratos/<data>/
(base-mestre e régua), a MUNIC 2020 e a base municipal v3 (índice "Quem tem
ônibus?", família B, reconstruído por indice_indicio_familia_b.py), e grava
retrato_cap5.json na mesma pasta. Read-only sobre as fontes.
"""
import sys, os, json, collections, runpy
import pandas as pd, numpy as np, openpyxl
D = sys.argv[1] if len(sys.argv) > 1 else '2026-10-01'
R = os.path.expanduser('~/mnt/doutorado/03 - Dados/_data')
RET = f'{R}/casos por fonte/retratos/{D}'
m = pd.read_excel(f'{RET}/Municípios TZ - consolidado.xlsx', sheet_name=0)
out = {'data_corte': D}
out['situacao'] = m['Situação'].value_counts(dropna=False).to_dict()
esc = m[m['Situação'].isin(['Ativa', 'Encerrada'])].copy()
at = m[m['Situação'] == 'Ativa'].copy()
at_todas = at
at = at[at['Régua — aba'] == '1 Universal'].copy()  # camada 1 (universal); as 2 parciais permanentes da mestre ficam fora
out['em_escopo'] = len(esc); out['ativas'] = len(at_todas); out['ativas_camada1'] = len(at)
out['ativas_fora_camada1'] = at_todas.loc[at_todas['Régua — aba'] != '1 Universal', ['Município','UF','Régua — aba','Régua — subtipo']].values.tolist()
# régua: contagem pelas abas
wb = openpyxl.load_workbook(f'{RET}/Tipologias TZ - consolidado.xlsx', read_only=True, data_only=True)
reg = {}
for ws in wb.worksheets:
    if ws.title == 'RESUMO': continue
    rows = [r for r in ws.iter_rows(values_only=True)][1:]
    rows = [r for r in rows if r and r[0]]
    d = {'linhas': len(rows), 'municipios': len(set((r[0], r[1]) for r in rows))}
    if ws.title in ('1 Universal', '2 Parcial', '3 Encerradas'):
        d['subtipo'] = collections.Counter(st for r in rows for st in (re.findall(r'2[a-e]', str(r[2])) if ws.title == '2 Parcial' and r[2] else [str(r[2]) if r[2] else 'sem subtipo']))  # A.1.15: não exclusiva na aba 2
    reg[ws.title] = d
out['regua'] = reg
REG = {'N': 'Norte', 'NE': 'Nordeste', 'CO': 'Centro-Oeste', 'SE': 'Sudeste', 'S': 'Sul'}
UFR = {**{u: 'N' for u in 'AC AM AP PA RO RR TO'.split()}, **{u: 'NE' for u in 'AL BA CE MA PB PE PI RN SE'.split()},
       **{u: 'CO' for u in 'DF GO MS MT'.split()}, **{u: 'SE' for u in 'ES MG RJ SP'.split()}, **{u: 'S' for u in 'PR RS SC'.split()}}
at['reg'] = at['UF'].map(UFR).map(REG)
out['ativas_regiao'] = at['reg'].value_counts().to_dict()
out['ativas_uf_top'] = at['UF'].value_counts().head(8).to_dict()
bins = [0, 10000, 20000, 50000, 100000, 500000, 1e9]
labs = ['até 10 mil', '10-20 mil', '20-50 mil', '50-100 mil', '100-500 mil', 'acima de 500 mil']
pop = pd.to_numeric(at['População (2022)'], errors='coerce')
at['porte'] = pd.cut(pop, bins=bins, labels=labs, right=True)
out['ativas_porte'] = at['porte'].value_counts().reindex(labs).fillna(0).astype(int).to_dict()
out['ativas_pop_mediana'] = float(pop.median()); out['ativas_pop_max'] = float(pop.max())
out['ativas_pop_max_mun'] = at.loc[pop.idxmax(), 'Município']
ano = pd.to_numeric(esc['Ano início'].astype(str).str.extract(r'((?:19|20)\d\d)')[0], errors='coerce')  # r56: ano de quatro dígitos lido no campo (antes: só número puro)
out['inicio_por_ano_escopo'] = {int(k): int(v) for k, v in ano.value_counts().sort_index().items()}
out['inicio_sem_ano'] = int(ano.isna().sum())
# acumulado de ativas no fim de cada ano (ativas + encerradas ainda vigentes no ano)
fim = pd.to_numeric(esc['Fim'].astype(str).str.extract(r'(\d{4})')[0], errors='coerce')
cum = {}
for y in range(1990, 2027):
    cum[y] = int(((ano <= y) & (fim.isna() | (fim > y))).sum())
out['vigentes_por_ano'] = cum
col = 'Prova de operação — atualidade (2025/2026)'
out['prova_operacao_ativas'] = at_todas[col].astype(str).str.split('·').str[0].str.strip().value_counts().to_dict()
out['estado_terminal_escopo'] = esc['Estado terminal (completude)'].astype(str).str.split('—').str[0].str.strip().value_counts().to_dict()
out['estado_terminal_detalhe'] = esc['Estado terminal (completude)'].astype(str).value_counts().to_dict()
out['santini_abr2026_escopo'] = esc['No levantamento Santini (abr/2026)'].astype(str).value_counts().to_dict()
out['n_levantamentos_escopo'] = esc['Fontes — nº de levantamentos (recontagem)'].astype(str).value_counts().to_dict()
out['munic_onibus_escopo'] = esc['MUNIC 2020 (autodeclarado) — ônibus intramunicipal'].astype(str).value_counts().to_dict()
out['munic_isencao_escopo'] = esc["MUNIC 2020 (autodeclarado) — isenção 'toda a população'"].astype(str).value_counts().to_dict()
out['instrumento_base_escopo'] = esc['Instrumento — base da decisão'].astype(str).value_counts().to_dict()
out['prestacao_escopo'] = esc['Prestação (eixo 2)'].astype(str).value_counts().head(12).to_dict()
out['grupo_economico_escopo'] = esc['Grupo econômico'].astype(str).str[:40].value_counts().head(10).to_dict()
out['operador_ge_escopo'] = esc['Operador × GE — resultado (cruzamento)'].astype(str).value_counts().to_dict()
# denominador: MUNIC 2020 e índice (família B)
cwd = os.getcwd(); os.chdir(f'{R}/Base Municipal v3')
g = runpy.run_path(os.path.expanduser('~/mnt/doutorado/06 - Acadêmico/Artigos/1 - Em elaboração/XXII ENANPUR 2027 — método de detecção com IA/indice_indicio_familia_b.py'), run_name='lib')
os.chdir(cwd); b = g['df']
b['cod'] = pd.to_numeric(b['cod_ibge'] if 'cod_ibge' in b else b[[c for c in b.columns if 'ibge' in c.lower()][0]], errors='coerce')
b['porte'] = pd.cut(pd.to_numeric(b['pop_2022'], errors='coerce'), bins=bins, labels=labs, right=True)
codes_at = set(pd.to_numeric(at['Código IBGE'], errors='coerce').dropna().astype(int))
b['tz'] = b['cod'].isin(codes_at)
b['munic'] = b['munic_onibus_intramun_2020'] == 1
b['idx5'] = b['indice_familia_b'] >= 5
den = {}
for p in labs:
    s = b[b['porte'] == p]
    den[p] = {'municipios': int(len(s)), 'munic_com_onibus': int(s['munic'].sum()), 'indice_ge5': int(s['idx5'].sum()),
              'tz_ativas': int(s['tz'].sum()), 'tz_entre_munic': int((s['tz'] & s['munic']).sum()), 'tz_entre_idx5': int((s['tz'] & s['idx5']).sum())}
out['denominador_por_porte'] = den
out['denominador_total'] = {'municipios': int(len(b)), 'munic_com_onibus': int(b['munic'].sum()), 'indice_ge5': int(b['idx5'].sum()),
   'tz_casadas': int(b['tz'].sum()), 'tz_e_munic': int((b['tz'] & b['munic']).sum()), 'tz_e_idx5': int((b['tz'] & b['idx5']).sum()),
   'tz_mediana_indice': float(b.loc[b['tz'], 'indice_familia_b'].median()), 'demais_mediana_indice': float(b.loc[~b['tz'], 'indice_familia_b'].median())}
json.dump(out, open(f'{RET}/retrato_cap5.json', 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
