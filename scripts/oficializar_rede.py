#!/usr/bin/env python3
"""
oficializar_rede.py — a proposta vira a Rede de empresas oficial (decisão do autor, 13/11/2026:
"todas as de proposta ficaram oficiais! pode subir na versão 1.0 ainda").

Lê rede-ge-proposta.html, já com as etapas aplicadas (gerar_proposta.py → rede_etapa2.py a rede_etapa5.py),
tira as marcas de teste e grava rede-ge.html:
  - sai a faixa amarela "Proposta em teste…";
  - o selo volta a "rede · v1.0.0";
  - os links internos apontam para as páginas oficiais (painel.html e rede-ge.html);
  - sai a marca <meta name="proposta">.
Ordem no build_tudo.sh: ... → rede_etapa5.py → oficializar_painel.py → oficializar_rede.py.
"""
import os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEM = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'rede-ge-proposta.html')
DESTINO = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, 'rede-ge.html')
s = open(ORIGEM, encoding='utf-8').read()
assert 'rede_etapa5' in s, 'rode rede_etapa2.py a rede_etapa5.py antes'

s, k = re.subn(r'<div class="faixa-proposta">.*?</div>\n?', '', s, count=1, flags=re.S)
assert k == 1, 'faixa da proposta não achada'
assert s.count('<span class="badge">rede · v1.0.0 · proposta</span>') == 1, 'selo da proposta não achado'
s = s.replace('<span class="badge">rede · v1.0.0 · proposta</span>', '<span class="badge">rede · v1.0.0</span>')
s = s.replace('painel-proposta.html', 'painel.html').replace('rede-ge-proposta.html', 'rede-ge.html')
s, k = re.subn(r'<meta name="proposta" content="[^"]*">\n?', '', s)
assert k >= 1, 'marca <meta name="proposta"> não achada'
assert 'faixa-proposta">' not in s and 'v1.0.0 · proposta' not in s
open(DESTINO, 'w', encoding='utf-8').write(s)
print('rede oficial gravada:', DESTINO, len(s.encode()), 'bytes')
