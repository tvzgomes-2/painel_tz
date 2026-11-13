# -*- coding: utf-8 -*-
"""
exportar_colunar.py — gera ../build/municipios_dados_col.json (o bloco data-muni do painel) a partir de
../build/municipios_dados.json. Substitui o one-liner documentado no montar_html.sh (13/11/2026, v1.0.0).

Para o painel ficar mais leve sem perder função (decisão do autor, 13/11/2026: "manter autocontido,
mas limpar dados pesados"):
  - saem as colunas que o painel não usa em lugar nenhum (lista SEM_USO, conferida contra logic.js e
    head.html — o script falha se alguma delas passar a ser usada);
  - os números com casas demais (ex.: 12.19363492257042) ficam com 5 algarismos significativos, o
    que nenhum formato de exibição do painel ultrapassa.
O municipios_dados.json completo continua em build/, para quem precisar.
"""
import json, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, '..', 'build', 'municipios_dados.json')
OUT = os.path.join(BASE, '..', 'build', 'municipios_dados_col.json')
SEM_USO = ['rec_total', 'desp_tcu', 'ext_via', 'pdmu_2016', 'concessao', 'concessionaria', 'frota_bus', 'gps_bus',
           'partido_16', 'passe_1t', 'passe_2t', 'passe_abrang', 'tz_regua_aba', 'munic_isencao_total',
           'pct_transporte_desp', 'desp_transporte', 'investimentos', 'pdmu_obrigado_2025', 'prefeito_2024',
           'partido_2024', 'ext_viaria_osm', 'densidade_viaria']

codigo = open(os.path.join(BASE, 'logic.js'), encoding='utf-8').read() + open(os.path.join(BASE, 'head.html'), encoding='utf-8').read()
usadas = [c for c in SEM_USO if re.search(r"(\.|'|\"|\b)" + re.escape(c) + r"\b", codigo)]
if usadas:
    raise SystemExit(f'ERRO: colunas marcadas como sem uso aparecem no código: {usadas}. Tire-as de SEM_USO.')

def enxuga(v):
    if isinstance(v, float):
        if v != v: return None
        r = float(f'{v:.5g}')
        return int(r) if r.is_integer() and abs(r) < 1e15 else r
    return v

d = json.load(open(SRC, encoding='utf-8'))
cols = [c for c in d[0].keys() if c not in SEM_USO]
out = {'cols': cols, 'data': [[enxuga(r[c]) for c in cols] for r in d]}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
print(f'municipios_dados_col.json: {len(cols)} colunas (saíram {len(SEM_USO)}), {os.path.getsize(OUT)/1024:.0f} KB')

# partição modal (Censo 2022): as seis chaves se repetem nos 5.570 municípios; vão uma vez só,
# e o painel remonta o objeto (logic.js, MODAL_RAW). 13/11/2026.
MSRC = os.path.join(BASE, 'modal_por_municipio.json')
MOUT = os.path.join(BASE, '..', 'build', 'modal_col.json')
m = json.load(open(MSRC, encoding='utf-8'))
mk = ['ativo', 'automovel', 'motocicleta', 'onibus', 'outros', 't']
assert all(sorted(v) == sorted(mk) for v in m.values()), 'partição modal com chaves diferentes'
with open(MOUT, 'w', encoding='utf-8') as f:
    json.dump({'cols': mk, 'data': {k: [v[c] for c in mk] for k, v in m.items()}}, f, ensure_ascii=False, separators=(',', ':'))
print(f'modal_col.json: {len(m)} municípios, {os.path.getsize(MOUT)/1024:.0f} KB')
