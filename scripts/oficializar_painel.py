#!/usr/bin/env python3
"""
oficializar_painel.py — a proposta vira o Painel Brasil oficial (decisão do autor, 13/11/2026:
"painel podemos substituir pelo proposto!").

Lê painel-proposta.html, já com as duas etapas aplicadas (gerar_proposta.py + proposta_etapa2.py), tira as
marcas de teste e grava painel.html:
  - sai a faixa amarela "Proposta em teste…";
  - o selo volta a "painel · v1.0.0";
  - os links internos apontam para as páginas oficiais (painel.html; a Rede segue em rede-ge.html até a
    proposta da Rede ser aprovada — ela já entende #GE-… e #mun-…).
Ordem no build_tudo.sh: montar_html.sh → montar_rede_ge.sh → gerar_proposta.py → proposta_etapa2.py →
rede_etapa2.py → oficializar_painel.py.
"""
import os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEM = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'painel-proposta.html')
DESTINO = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, 'painel.html')
s = open(ORIGEM, encoding='utf-8').read()
assert 'proposta_etapa2' in s, 'rode proposta_etapa2.py antes'

s, k = re.subn(r'<div class="faixa-proposta">.*?</div>\n', '', s, count=1, flags=re.S)
assert k == 1, 'faixa da proposta não achada'
s = s.replace('<span class="badge">painel · v1.0.0 · proposta</span>', '<span class="badge">painel · v1.0.0</span>')
s = s.replace('painel-proposta.html', 'painel.html')
s = s.replace('rede-ge-proposta.html', 'rede-ge.html')
s = s.replace('<meta name="proposta" content="proposta_etapa2">\n', '')
# 13/11/2026 (autor): o site deixa de se apresentar como protótipo ou instrumento exploratório
s = s.replace(' — instrumento exploratório da pesquisa; não substitui a análise da tese.', ' — o método completo e os limites estão na tese.')
open(DESTINO, 'w', encoding='utf-8').write(s)
print('painel oficial gravado:', DESTINO, len(s.encode()), 'bytes')
