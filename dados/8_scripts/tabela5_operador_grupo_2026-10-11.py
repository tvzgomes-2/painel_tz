# -*- coding: utf-8 -*-
"""Tabela 5 da tese (Cap. 6): operadores comprovados das políticas de Tarifa Zero, por pertencimento a grupo
econômico, porte e forma de contratação. Base congelada de 11/10/2026 (somente leitura).
Regras: CNPJ comprovado = CNPJ com 14 dígitos na coluna "Operador — CNPJ" da base-mestre; grupo = resultado do
cruzamento ("Operador × GE — resultado (cruzamento)") com operador em grupo econômico ou empresa isolada promovida
a grupo pelo capital; núcleo do ônibus = CNPJ básico com estabelecimento na camada "nucleo" do recorte de 6 CNAEs, com a CNAE como principal
(CNAE 4921-3/01 ou /02 como atividade principal); forma pela coluna "Prestação (eixo 2)". NA != 0.
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · revisão r56."""
import re, os, json, pandas as pd
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
F = os.path.join(R, '03 - Dados/_data/congelamento-2026-10-11/Municípios TZ - consolidado.xlsx')
EST = os.path.join(R, '03 - Dados/_data/CNPJ/filtrados (6 CNAEs transporte, 24-07-2026)/estabelecimentos_filtrado_6cnaes.csv')
m = pd.read_excel(F, sheet_name='consolidado'); e = m[m['Situação'].isin(['Ativa', 'Encerrada'])].copy()
def cnpjs(x): return re.findall(r'(\d{2})\.?(\d{3})\.?(\d{3})/?(\d{4})-?(\d{2})', str(x)) if pd.notna(x) else []
e['cn'] = e['Operador — CNPJ'].map(cnpjs); c = e[e.cn.str.len() > 0].copy()
c['bas'] = c.cn.map(lambda l: [''.join(t[:3]) for t in l])
nuc = set()
for ch in pd.read_csv(EST, dtype=str, usecols=['cnpj_basico', 'camada', 'tipo_match', 'matriz_filial'], chunksize=400000):
    nuc |= set(ch.loc[(ch.camada == 'nucleo') & (ch.tipo_match == os.environ.get('T5_MATCH', 'principal')), 'cnpj_basico'])
g = c['Operador × GE — resultado (cruzamento)'].fillna('').astype(str)
def tipo(r, gg):
    # os três componentes societários pequenos, sem código de grupo (Seção 6.6), não são dos 327 grupos
    if (r['Município'], r['UF']) in {('Governador Celso Ramos', 'SC'), ('Porto Belo', 'SC'), ('Tietê', 'SP')}: return 'nucleo'
    if gg.startswith('operador em grupo') or gg.startswith('operador é empresa isolada de grande'): return 'grupo'
    return 'nucleo' if any(b in nuc for b in r['bas']) else 'fora'
c['tipo'] = [tipo(r, gg) for (_, r), gg in zip(c.iterrows(), g)]
def forma(x):
    t = str(x).lower() if pd.notna(x) else ''
    if not t or t.startswith(('não encontrado', 'não apurado', 'a apurar')): return 'nd_pub'
    if t.startswith('contrat') and not re.search(r'aditivo|aditamento|adendo', t):
        return 'emerg_loc' if re.search(r'emergenc|dispensa|locação|locado', t) else 'novo'
    if re.search(r'aditivo|aditamento|adendo', t): return 'aditivo'
    if re.search(r'locação|locado', t): return 'emerg_loc' if 'motorista' in t else 'nd_pub'
    if re.search(r'prestação direta|execução direta|empresa pública|autarquia', t): return 'nd_pub'
    if t.startswith('concessão'): return 'novo'
    return 'novo'
c['forma'] = c['Prestação (eixo 2)'].map(forma)
c['grande'] = pd.to_numeric(c['População (2022)'], errors='coerce') >= 100000
T = pd.crosstab(c.tipo, c.forma, margins=True); T['grande'] = c.groupby('tipo').grande.sum(); T.loc['All', 'grande'] = c.grande.sum()
print(T.reindex(['grupo', 'nucleo', 'fora', 'All']).to_string())
print('grupo:', sorted(c.loc[c.tipo == 'grupo', 'Município'] + '/' + c.loc[c.tipo == 'grupo', 'UF']))
print('grupo aditivo:', sorted(c.loc[(c.tipo == 'grupo') & (c.forma == 'aditivo'), 'Município']))
