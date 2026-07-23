# -*- coding: utf-8 -*-
"""
build_data.py — gera municipios_dados.json a partir das fontes brutas.

Documentação do método, não um script "rode e funcione" para terceiros: os
arquivos de origem (base_municipal_v3.csv, Municípios TZ - consolidado.xlsx)
são parte do cofre de pesquisa privado do autor e NÃO estão neste repositório
público. Os caminhos abaixo assumem a estrutura local do autor, com as pastas
"painel TZ" (este repo) e "doutorado" (cofre privado) como irmãs dentro do
OneDrive — ajuste conforme necessário para rodar de fato.

Saída: ../build/municipios_dados.json (pasta local, não versionada)
"""
import pandas as pd
import numpy as np
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.join(BASE_DIR, '..', '..', 'doutorado')  # cofre privado, não incluído neste repo
OUT_DIR = os.path.join(BASE_DIR, '..', 'build')
os.makedirs(OUT_DIR, exist_ok=True)

base = pd.read_csv(os.path.join(VAULT, '03 - Dados', '_data', 'Base Municipal v3', 'base_municipal_v3.csv'),
                    dtype={'cod_ibge': str}, low_memory=False)
base['cod_ibge'] = base['cod_ibge'].str.zfill(7)

tz = pd.read_excel(os.path.join(VAULT, '03 - Dados', '_data', 'casos por fonte', 'Municípios TZ - consolidado.xlsx'),
                    sheet_name='consolidado')

name_uf_to_code = {(r['nome_mun'].strip().lower(), r['uf']): r['cod_ibge'] for _, r in base.iterrows()}
missing = tz['Código IBGE'].isna()
print('linhas sem Codigo IBGE no arquivo canonico:', missing.sum())
for idx in tz[missing].index:
    key = (str(tz.loc[idx, 'Município']).strip().lower(), tz.loc[idx, 'UF'])
    code = name_uf_to_code.get(key)
    if code is None:
        print('  NAO ENCONTRADO:', tz.loc[idx, ['Município', 'UF']].tolist())
    tz.loc[idx, 'Código IBGE'] = code

tz['cod_ibge'] = tz['Código IBGE'].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(7)
dup_mask = tz['cod_ibge'].duplicated(keep=False)
print('duplicatas de cod_ibge no canonico (ver CHANGELOG.md — Palmas-TO):')
print(tz[dup_mask][['Município', 'UF', 'Situação', 'Ano início']])

tz_dedup = tz.drop_duplicates(subset='cod_ibge', keep='first')
print('canonico apos dedup:', tz_dedup.shape)

tz_small = tz_dedup[['cod_ibge', 'Situação', 'Ano início', 'Fim', '% orçamento', 'Operador']].rename(
    columns={'Situação': 'tz_situacao_mestre', 'Ano início': 'tz_ano_mestre', 'Fim': 'tz_fim_mestre'})

df = base.merge(tz_small, on='cod_ibge', how='left')
df['tz_status'] = np.where(df['tz_situacao_mestre'].notna(), df['tz_situacao_mestre'], 'Não TZ')
print(df['tz_status'].value_counts())

# --- modelo de prestação (MUNIC 2020): categórica derivada dos 5 flags 0/1 ---
flag_cols = ['munic_concessao_2020', 'munic_permissao_2020', 'munic_autorizacao_2020',
             'munic_prestacao_direta_2020', 'munic_nao_regulamentado_2020']
labels = {'munic_concessao_2020': 'Concessão', 'munic_permissao_2020': 'Permissão',
          'munic_autorizacao_2020': 'Autorização', 'munic_prestacao_direta_2020': 'Prestação direta',
          'munic_nao_regulamentado_2020': 'Não regulamentado'}


def modelo_prestacao(row):
    if all(pd.isna(row[c]) for c in flag_cols):
        return None  # não respondeu MUNIC 2020
    ativos = [labels[c] for c in flag_cols if row[c] == 1]
    if len(ativos) == 0:
        return 'Nenhum informado'
    if len(ativos) == 1:
        return ativos[0]
    return 'Misto (' + ' + '.join(ativos) + ')'


df['modelo_prestacao'] = df.apply(modelo_prestacao, axis=1)
print(df['modelo_prestacao'].value_counts(dropna=False))


def simplifica_modelo(v):
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if v.startswith('Misto'):
        return 'Misto (2+ modelos)'
    return v


df['modelo_prestacao_simples'] = df['modelo_prestacao'].apply(simplifica_modelo)

# simplifica rótulo REGIC (tira sufixo de arranjo populacional)
df['regic_simples'] = df['regic_hierarquia_2018'].str.extract(r'^([^(]+\([^)]+\))')[0].str.strip()

# --- sede vs satélite dentro do arranjo populacional (REGIC 2018) ---
import unicodedata


def strip_accents(s):
    if pd.isna(s):
        return s
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def tipo_arranjo(row):
    if pd.isna(row['arranjo_pop_2018']):
        return 'Fora de arranjo'
    nome = strip_accents(row['nome_mun']).lower().strip()
    arr = strip_accents(row['arranjo_pop_2018']).lower()
    return 'Sede/co-sede do arranjo' if nome in arr else 'Satélite do arranjo'


df['tipo_arranjo'] = df.apply(tipo_arranjo, axis=1)
print(df['tipo_arranjo'].value_counts(dropna=False))

cols = {
    'cod_ibge': 'id', 'nome_mun': 'nome', 'nome_uf': 'uf_nome', 'uf': 'uf', 'reg': 'regiao',
    'faixa_pop_2022': 'faixa_pop', 'pop_2022': 'pop', 'taxa__cresc_10_22': 'cresc_pop',
    'pib_per_capita_2021': 'pib_pc', 'rec_total': 'rec_total', 'rec_prop': 'rec_prop',
    'desp_tcu': 'desp_tcu', 'motorizacao_2023': 'motorizacao', 'ibeu': 'ibeu', 'idh': 'idh',
    'ext_via': 'ext_via', 'pd': 'plano_diretor', 'pdmu': 'pdmu_2016', 'conc_tcu': 'concessao',
    'concessionioria': 'concessionaria', 'frota_bus': 'frota_bus', 'gps_bus': 'gps_bus',
    'part_16': 'partido_16', 'passe_1turno_2022': 'passe_1t', 'passe_2turno_2022': 'passe_2t',
    'passe_abrangencia_2022': 'passe_abrang', 'tz_status': 'tz_status',
    'tz_ano_mestre': 'tz_ano', 'tz_fim_mestre': 'tz_fim', '% orçamento': 'tz_pct_orc', 'Operador': 'tz_operador',
    # --- campos novos (v3) ---
    'regic_nivel_2018': 'regic_nivel', 'regic_simples': 'regic_label',
    'arranjo_pop_2018': 'arranjo_nome', 'tipo_arranjo': 'tipo_arranjo',
    'modelo_prestacao': 'modelo_prestacao', 'modelo_prestacao_simples': 'modelo_prestacao_simples',
    'munic_isencao_total_2020': 'munic_isencao_total',
    'pct_transporte_desp_2022': 'pct_transporte_desp', 'desp_transporte_2022': 'desp_transporte',
    'pct_investimento_desp_2022': 'pct_investimento_desp', 'investimentos_2022': 'investimentos',
    'taxa_obitos_transito_100k_2019': 'taxa_obitos_transito',
    'tarifa_reconciliada': 'tarifa', 'tarifa_reconciliada_ano': 'tarifa_ano', 'tarifa_reconciliada_fonte': 'tarifa_fonte',
    'subsidio_pct_custo_ntu': 'subsidio_ntu_pct', 'subsidio_pct_custo_ntu_ano': 'subsidio_ntu_ano',
    'pdmu_possui_2025': 'pdmu_2025', 'pdmu_obrigado_2025': 'pdmu_obrigado_2025',
    'prefeito_2024': 'prefeito_2024', 'partido_2024': 'partido_2024',
    'extensao_viaria_total_km': 'ext_viaria_osm', 'densidade_viaria_km_km2': 'densidade_viaria',
}
out = df[list(cols.keys())].rename(columns=cols)

numeric_cols = ['pop', 'cresc_pop', 'pib_pc', 'rec_total', 'rec_prop', 'desp_tcu', 'motorizacao', 'ibeu', 'idh', 'ext_via',
                'regic_nivel', 'pct_transporte_desp', 'desp_transporte', 'pct_investimento_desp', 'investimentos',
                'taxa_obitos_transito', 'tarifa', 'subsidio_ntu_pct', 'ext_viaria_osm', 'densidade_viaria']
for c in numeric_cols:
    out[c] = pd.to_numeric(out[c], errors='coerce')

out['uf_nome'] = out['uf_nome'].str.title()
out['nome'] = out['nome'].str.title()

records = out.to_dict(orient='records')


def clean(v):
    if isinstance(v, float) and np.isnan(v):
        return None
    if pd.isna(v):
        return None
    return v


records = [{k: clean(v) for k, v in r.items()} for r in records]

with open(os.path.join(OUT_DIR, 'municipios_dados.json'), 'w', encoding='utf-8') as f:
    json.dump(records, f, ensure_ascii=False)

print('rows out:', len(records))
print('modelo_prestacao coverage (non-null):', sum(1 for r in records if r['modelo_prestacao'] is not None))
print('subsidio coverage:', sum(1 for r in records if r['subsidio_ntu_pct'] is not None))
print('tarifa coverage:', sum(1 for r in records if r['tarifa'] is not None))
