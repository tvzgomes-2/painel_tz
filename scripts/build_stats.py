# -*- coding: utf-8 -*-
"""
build_stats.py — gera stats.json (agregados, cortes e listas) a partir de
municipios_dados.json (saída de build_data.py).

Ver nota de reprodutibilidade em build_data.py / CHANGELOG.md — depende de
dados privados do autor, não incluídos neste repositório.

Saída: ../build/stats.json
"""
import pandas as pd
import json
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, '..', 'build')

d = json.load(open(os.path.join(OUT_DIR, 'municipios_dados.json'), encoding='utf-8'))
df = pd.DataFrame(d)
df['tz_bin'] = df['tz_status'].apply(lambda x: 'TZ' if x in ('Ativa', 'Encerrada') else 'Não TZ')
df['rec_prop_pc'] = df['rec_prop'] / df['pop']

order_faixa = ['Inferior a 20 mil', 'Entre 20 e 100 mil', 'Entre 100 e 250 mil', 'Entre 250 e 500 mil', 'Acima de 500 mil']
order_regic = [1, 2, 3, 4, 5]
order_modelo = ['Concessão', 'Prestação direta', 'Permissão', 'Autorização', 'Não regulamentado', 'Misto (2+ modelos)']
order_arranjo = ['Sede/co-sede do arranjo', 'Satélite do arranjo', 'Fora de arranjo']

vars_ = ['pib_pc', 'motorizacao', 'ibeu', 'idh', 'cresc_pop', 'rec_prop_pc', 'taxa_obitos_transito', 'pct_investimento_desp']
breaks = {v: [round(x, 4) if x == x else None for x in df[v].quantile([0, 0.2, 0.4, 0.6, 0.8, 1.0]).tolist()] for v in vars_}
# esparsos: usar breaks só sobre quem tem dado
for v in ['tarifa', 'subsidio_ntu_pct']:
    s = df[v].dropna()
    breaks[v] = [round(x, 4) for x in s.quantile([0, 0.2, 0.4, 0.6, 0.8, 1.0]).tolist()]


def agg(g):
    return {
        'n': int(g.shape[0]),
        'pop_mediana': float(g['pop'].median()),
        'pib_pc_mediana': float(g['pib_pc'].median()),
        'motorizacao_mediana': float(g['motorizacao'].median()),
        'ibeu_mediana': float(g['ibeu'].median()),
        'idh_mediana': float(g['idh'].median(skipna=True)) if g['idh'].notna().any() else None,
        'rec_prop_pc_mediana': float(g['rec_prop_pc'].median()),
        'taxa_obitos_transito_mediana': float(g['taxa_obitos_transito'].median(skipna=True)) if g['taxa_obitos_transito'].notna().any() else None,
        'pdmu_pct': float((g['pdmu_2025'].astype(str).str.strip() == 'Sim').mean()),
        'pd_pct': float((g['plano_diretor'].astype(str).str.strip() == 'Sim').mean()),
    }


overall = {k: agg(g) for k, g in df.groupby('tz_bin')}

by_faixa = {f: {k: agg(g) for k, g in df[df['faixa_pop'] == f].groupby('tz_bin')} for f in order_faixa}
by_regic = {int(r): {k: agg(g) for k, g in df[df['regic_nivel'] == r].groupby('tz_bin')} for r in order_regic}
by_arranjo = {a: {k: agg(g) for k, g in df[df['tipo_arranjo'] == a].groupby('tz_bin')} for a in order_arranjo}
sub_modelo = df[df['modelo_prestacao_simples'].notna()]
by_modelo = {m: {k: agg(g) for k, g in sub_modelo[sub_modelo['modelo_prestacao_simples'] == m].groupby('tz_bin')} for m in order_modelo}


def crosstab_pct(col, order):
    ct = pd.crosstab(df[col], df['tz_bin'])
    ctp = pd.crosstab(df[col], df['tz_bin'], normalize='index')
    out = {}
    for k in order:
        if k in ct.index:
            out[str(k)] = {
                'n_tz': int(ct.loc[k, 'TZ']) if 'TZ' in ct.columns else 0,
                'n_nao_tz': int(ct.loc[k, 'Não TZ']) if 'Não TZ' in ct.columns else 0,
                'pct_tz': round(float(ctp.loc[k, 'TZ']) if 'TZ' in ctp.columns else 0.0, 4),
            }
    return out


crosstabs = {
    'faixa_pop': crosstab_pct('faixa_pop', order_faixa),
    'regic_nivel': crosstab_pct('regic_nivel', order_regic),
    'tipo_arranjo': crosstab_pct('tipo_arranjo', order_arranjo),
    'modelo_prestacao_simples': crosstab_pct('modelo_prestacao_simples', order_modelo),
}

uf_names = df.drop_duplicates('uf')[['uf', 'uf_nome', 'regiao']].sort_values('uf_nome').to_dict(orient='records')

tz_cols = ['id', 'nome', 'uf', 'faixa_pop', 'pop', 'pib_pc', 'motorizacao', 'ibeu', 'idh', 'regic_nivel', 'regic_label',
           'tipo_arranjo', 'modelo_prestacao', 'tz_status', 'tz_ano', 'tz_fim', 'tz_pct_orc', 'tz_operador',
           'tarifa', 'subsidio_ntu_pct']
tz_list = df[df['tz_bin'] == 'TZ'][tz_cols].sort_values('pib_pc', ascending=False).to_dict(orient='records')

# lista dos sede/co-sede com TZ + os satélites de nível 1, para o quadro de destaque (ver CHANGELOG.md)
sedes_tz = df[(df['tipo_arranjo'] == 'Sede/co-sede do arranjo') & (df['tz_bin'] == 'TZ')][
    ['nome', 'uf', 'pop', 'regic_label', 'arranjo_nome']].sort_values('pop', ascending=False).to_dict(orient='records')
nivel1_tz = df[(df['regic_nivel'] == 1) & (df['tz_bin'] == 'TZ')][
    ['nome', 'uf', 'pop', 'regic_label', 'tipo_arranjo', 'arranjo_nome']].sort_values('pop', ascending=False).to_dict(orient='records')

stats = {
    'faixa_order': order_faixa, 'regic_order': order_regic, 'modelo_order': order_modelo, 'arranjo_order': order_arranjo,
    'breaks': breaks,
    'overall': overall, 'by_faixa': by_faixa, 'by_regic': by_regic, 'by_arranjo': by_arranjo, 'by_modelo': by_modelo,
    'crosstabs': crosstabs,
    'uf_list': uf_names,
    'tz_list': tz_list,
    'destaques': {'sedes_tz': sedes_tz, 'nivel1_tz': nivel1_tz},
    'totais': {
        'municipios': int(df.shape[0]),
        'tz_ativa': int((df['tz_status'] == 'Ativa').sum()),
        'tz_encerrada': int((df['tz_status'] == 'Encerrada').sum()),
        'nao_tz': int((df['tz_bin'] == 'Não TZ').sum()),
        'modelo_prestacao_n': int(df['modelo_prestacao_simples'].notna().sum()),
        'subsidio_ntu_n': int(df['subsidio_ntu_pct'].notna().sum()),
        'tarifa_n': int(df['tarifa'].notna().sum()),
    }
}


def clean_nan(o):
    if isinstance(o, dict):
        return {k: clean_nan(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean_nan(v) for v in o]
    if isinstance(o, float) and np.isnan(o):
        return None
    return o


stats = clean_nan(stats)

with open(os.path.join(OUT_DIR, 'stats.json'), 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, separators=(',', ':'), allow_nan=False)

print('ok, bytes:', len(json.dumps(stats)))
print('totais:', stats['totais'])
