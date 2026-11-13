# -*- coding: utf-8 -*-
"""
atualizar_numeros.py — atualiza os números da capa (index.html) e dos Verbetes a partir dos mesmos dados
do painel (13/11/2026, v1.0.0). Antes, eram escritos à mão e podiam divergir do painel.
Cada número fica num elemento com data-n="chave"; a barra da capa, nos <rect data-barra="u|p|e">.
"""
import json, os, re
RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
d = json.load(open(os.path.join(RAIZ, 'build', 'municipios_dados.json'), encoding='utf-8'))
cam = json.load(open(os.path.join(RAIZ, 'scripts', 'camadas_tz.json'), encoding='utf-8'))
st = [m['tz_status'] for m in d]
N = {'universais': st.count('Ativa'), 'parciais_base': st.count('Parcial (ativa)'), 'encerradas': st.count('Encerrada'),
     'parciais_regua': len(cam)}
N['escopo'] = N['universais'] + N['parciais_base'] + N['encerradas']
fmt = lambda v: f'{v:,}'.replace(',', '.')
for arq in ('index.html', 'scripts/verbetes-fonte.html'):   # verbetes-fonte.html: a fonte dos verbetes, que entram em dados.html
    p = os.path.join(RAIZ, arq); s = open(p, encoding='utf-8').read(); n0 = s
    for k, v in N.items():
        s = re.sub(r'(<[^>]*\bdata-n="' + k + r'"[^>]*>)[^<]*(<)', lambda m: m.group(1) + fmt(v) + m.group(2), s)
    if arq == 'index.html':   # barra: universal, parcial (régua) e encerrada, na largura de 300
        tot = N['universais'] + N['parciais_regua'] + N['encerradas']; W, gap = 300, 2
        wu = round((W - 2 * gap) * N['universais'] / tot); wp = round((W - 2 * gap) * N['parciais_regua'] / tot); we = W - 2 * gap - wu - wp
        for k, x, w in (('u', 0, wu), ('p', wu + gap, wp), ('e', wu + wp + 2 * gap, we)):
            s = re.sub(r'<rect data-barra="' + k + r'" x="[\d.]+" y="4" width="[\d.]+"', f'<rect data-barra="{k}" x="{x}" y="4" width="{w}"', s)
    if s != n0: open(p, 'w', encoding='utf-8').write(s)
    print(f'{arq}: {"atualizado" if s != n0 else "sem mudança"} ({", ".join(f"{k} {v}" for k, v in N.items())})')
