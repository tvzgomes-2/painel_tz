# -*- coding: utf-8 -*-
"""
conferir_congelamento.py — confere o Painel Brasil contra a base que a tese cita (13/11/2026, v1.0.0).

1. Linha a linha: situação e subtipo de cada uma das 193 políticas de dados/1_politicas/tz_base_mestre_*.csv
   contra build/municipios_dados.json.
2. Números canônicos do congelamento (03 - Dados/Congelamento da base — 11-11-2026.md, no cofre) contra os
   dados do painel. Trocar o dicionário ESPERADO a cada congelamento novo.
Sai com erro se qualquer coisa divergir — o build_tudo.sh para aí.
"""
import collections, glob, json, os, sys
import pandas as pd

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BASE = sorted(glob.glob(os.path.join(RAIZ, 'dados', '1_politicas', 'tz_base_mestre_*.csv')))[-1]
ESPERADO = {   # Congelamento da base — 11-11-2026, seções 2, 3 e 4
    'em escopo': 187, 'universal': 173, '1a': 152, '1b': 9, '1c': 8, '1d': 4, 'parcial ativa': 8, 'encerradas': 6,
    'aba 2 (municípios)': 45, '2a': 4, '2b': 10, '2c': 28, '2d': 1, '2e': 5, 'lacuna declarada': 26,
    'contrapartida com': 31, 'contrapartida sem': 94, 'contrapartida não apurada': 48,
}
d = {str(m['id']): m for m in json.load(open(os.path.join(RAIZ, 'build', 'municipios_dados.json'), encoding='utf-8'))}
cam = json.load(open(os.path.join(RAIZ, 'scripts', 'camadas_tz.json'), encoding='utf-8'))
rem = json.load(open(os.path.join(RAIZ, 'scripts', 'remuneracao_tz.json'), encoding='utf-8'))
b = pd.read_csv(BASE)
erros = []
for _, r in b.iterrows():
    cod = str(int(r['Código IBGE'])); m = d.get(cod)
    if m is None: erros.append(f'{r["Município"]}: fora da base municipal'); continue
    esp = 'Parcial (ativa)' if (r['Situação'] == 'Ativa' and r['Régua — aba'] != '1 Universal') else r['Situação']
    sub = None if pd.isna(r['Régua — subtipo']) else str(r['Régua — subtipo'])
    if m['tz_status'] != esp or (m['tz_regua_sub'] or None) != sub:
        erros.append(f'{r["Município"]}: painel {m["tz_status"]}/{m["tz_regua_sub"]} × base {esp}/{sub}')
uni = [m for m in d.values() if m['tz_status'] == 'Ativa']
sub = collections.Counter(m['tz_regua_sub'] for m in uni)
camc = collections.Counter(c['camada'] for v in cam.values() for c in v)
cp = collections.Counter((rem.get(str(m['id'])) or {}).get('cp', 'nd') for m in uni)
achado = {
    'em escopo': sum(m['tz_status'] in ('Ativa', 'Parcial (ativa)', 'Encerrada') for m in d.values()),
    'universal': len(uni), '1a': sub['1a'], '1b': sub['1b'], '1c': sub['1c'], '1d': sub['1d'],
    'parcial ativa': sum(m['tz_status'] == 'Parcial (ativa)' for m in d.values()),
    'encerradas': sum(m['tz_status'] == 'Encerrada' for m in d.values()),
    'aba 2 (municípios)': len(cam), '2a': camc['2a'], '2b': camc['2b'], '2c': camc['2c'], '2d': camc['2d'], '2e': camc['2e'],
    'lacuna declarada': sum(1 for m in d.values() if m.get('tz_prov')),
    'contrapartida com': cp['com'], 'contrapartida sem': cp['sem'], 'contrapartida não apurada': cp['nd'],
}
print(f'conferência com {os.path.basename(BASE)}: {len(b)} linhas, {len(erros)} divergência(s) linha a linha')
for k, v in ESPERADO.items():
    ok = achado[k] == v
    print(f'  {"ok " if ok else "ERRO"} {k:28s} congelamento {v:4d} · painel {achado[k]:4d}')
    if not ok: erros.append(f'{k}: {achado[k]} ≠ {v}')
for e in erros[:20]: print('  [ERRO]', e)
sys.exit(1 if erros else 0)
