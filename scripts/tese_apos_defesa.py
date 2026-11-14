#!/usr/bin/env python3
"""
tese_apos_defesa.py — enquanto a tese não for defendida, o site não oferece os PDFs (decisão do autor, 13/11/2026:
"precisamos tirar os pdfs do trabalho e colocar que entrarão após a defesa da banca em dezembro").

Último passo do build (11d, depois de build_dados.py). Nas páginas já montadas:
  - dados.html: os botões dos dois volumes dão lugar ao cartaz "A tese · Dois volumes · disponível após a defesa",
    colado como lambe-lambe (tortinho, rasgado, com fita), na âncora #tese;
  - painel.html: o mesmo cartaz, menor, no lugar dos botões dos volumes; os links "Na tese: Seção …" e
    "Abrir o Volume II" passam a levar ao cartaz em dados.html#tese;
  - rede-ge.html: o botão "Volume I — Capítulo 8 (PDF)" passa a levar ao cartaz.
Depois da defesa: tirar este passo do build_tudo.sh e devolver os PDFs a tese/ (e ao git).

Uso:  python3 scripts/tese_apos_defesa.py        (da raiz do repositório)
"""
import os, random, re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = 'assets/figuras/tese-apos-a-defesa.jpg'
V1 = 'tese/Tese%20-%20Volume%20I%20-%20Texto.pdf'
V2 = 'tese/Tese%20-%20Volume%20II%20-%20Ap%C3%AAndices.pdf'
ALT = ('Cartaz: A tese, em dois volumes. Volume I, Texto: introdução, nove capítulos e referências. Volume II, Apêndices: '
       'métodos, testes, fichas municipais e fontes. Disponível após a defesa: os dois volumes serão publicados em acesso '
       'aberto depois da defesa, prevista para a semana de 14 a 18 de dezembro de 2026.')

# borda rasgada: pontos com tremor nas quatro bordas e um rasgo fundo no canto de baixo à direita (semente fixa)
rnd = random.Random(1412)
def borda(p0, p1, n, amp, para_dentro):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = p0[0] + (p1[0] - p0[0]) * t; y = p0[1] + (p1[1] - p0[1]) * t
        d = rnd.uniform(0, amp)
        x += para_dentro[0] * d; y += para_dentro[1] * d
        pts.append((x, y))
    return pts
P = []
P += borda((0, 0.3), (100, 0.2), 40, 0.55, (0, 1))          # topo: só um fio irregular
P += borda((99.8, 0), (99.7, 91), 30, 0.35, (-1, 0))        # direita
P += [(99.2, 93.0), (97.6, 95.2), (95.4, 97.0), (93.0, 98.6), (90.6, 99.5)]   # canto de baixo levemente arrancado
P += borda((89, 99.7), (0.3, 99.6), 34, 0.6, (0, -1))       # base
P += borda((0.2, 99.6), (0.3, 0), 30, 0.35, (1, 0))         # esquerda
POLY = ', '.join(f'{x:.1f}% {y:.1f}%' for x, y in P)
CSS = ('<style>/* tese_apos_defesa: cartaz lambe-lambe no lugar dos PDFs da tese */'
       '.lambe{position:relative;display:block;width:100%;max-width:340px;margin:18px auto 10px;transform:rotate(-2.8deg);'
       'filter:drop-shadow(4px 7px 7px rgba(0,0,0,.55));}'
       '.lambe.mini{max-width:250px;margin:14px 0 8px;transform:rotate(2.2deg);}'
       f'.lambe .papel{{position:relative;clip-path:polygon({POLY});background:#f4f2ee;}}'
       '.lambe img{display:block;width:100%;height:auto;}'
       '.lambe .papel::after{content:"";position:absolute;inset:0;pointer-events:none;'
       'background:linear-gradient(97deg,transparent 31%,rgba(0,0,0,.07) 32%,transparent 34%),'
       'linear-gradient(176deg,transparent 58%,rgba(255,255,255,.18) 59%,transparent 61%),'
       'radial-gradient(ellipse at 20% 10%,rgba(255,255,255,.12),transparent 55%),'
       'radial-gradient(ellipse at 85% 90%,rgba(0,0,0,.14),transparent 50%);mix-blend-mode:multiply;}'
       '.lambe .fita{position:absolute;z-index:2;width:34%;height:22px;background:rgba(236,226,186,.62);'
       'box-shadow:0 1px 2px rgba(0,0,0,.25);}'
       '.lambe .fita.f1{top:-9px;left:-5%;transform:rotate(-34deg);} .lambe .fita.f2{top:-8px;right:-4%;transform:rotate(29deg);}'
       '.lambe-leg{font-size:12.5px;color:var(--muted);text-align:center;max-width:360px;margin:4px auto 0;line-height:1.5;}'
       '.lambe.mini + .lambe-leg{text-align:left;margin:4px 0 0;}'
       '</style>')
def cartaz(mini=False, ident=True):
    cls = ' mini' if mini else ''
    ide = ' id="tese"' if ident else ''
    return (f'<figure class="lambe{cls}"{ide}><span class="fita f1"></span><span class="fita f2"></span>'
            f'<div class="papel"><img src="{IMG}" alt="{ALT}" loading="lazy" width="800" height="1000"></div></figure>'
            '<p class="lambe-leg">Os dois volumes entram aqui, em acesso aberto, depois da defesa, prevista para a semana de 14 a 18 de dezembro de 2026. Os dados da tese já estão abertos.</p>')

def grava(nome, fn):
    p = os.path.join(RAIZ, nome)
    s = open(p, encoding='utf-8').read()
    if 'tese_apos_defesa' in s:
        print(nome, 'já tratado'); return
    s = fn(s)
    assert V1 not in s and V2 not in s, f'{nome}: sobrou link para PDF da tese'
    s = s.replace('</head>', CSS + '\n<meta name="tese_apos_defesa" content="13/11/2026">\n</head>', 1)
    open(p, 'w', encoding='utf-8').write(s)
    print(nome, 'ok')

def f_dados(s):
    s, k = re.subn(r'<p style="margin-top:4px;"><a class="btn" href="' + re.escape(V1) + r'" download>[^<]*</a> <a class="btn" href="' + re.escape(V2) + r'" download>[^<]*</a></p>',
                   cartaz(), s, count=1)
    assert k == 1, 'dados.html: botões dos volumes não achados'
    s = s.replace('<h3>A tese, em dois volumes</h3>', '<h3>A tese, em dois volumes · depois da defesa</h3>', 1)
    s = s.replace('e os dois volumes da tese.', 'e, depois da defesa, os dois volumes da tese.')
    s = s.replace('e os dois volumes do texto.', 'e, depois da defesa, os dois volumes do texto.')
    s = s.replace('— além dos dois volumes da tese.', '— e, depois da defesa, os dois volumes da tese.')
    return s

def f_painel(s):
    s, k = re.subn(r'<a class="bt1" href="' + re.escape(V1) + r'"[^>]*>[^<]*</a><a class="bt1" href="' + re.escape(V2) + r'"[^>]*>[^<]*</a>',
                   cartaz(mini=True, ident=False), s, count=1)
    assert k == 1, 'painel.html: botões dos volumes não achados'
    s = s.replace(f'<a href="{V2}" target="_blank" rel="noopener">Abrir o Volume II (PDF) →</a>',
                  '<a href="dados.html#tese">O Volume II sai depois da defesa →</a>')
    s = s.replace(f'href="{V1}" target="_blank" rel="noopener"', 'href="dados.html#tese"')
    s = s.replace(f'href="{V2}" target="_blank" rel="noopener"', 'href="dados.html#tese"')
    return s

def f_rede(s):
    s = s.replace(f'<a class="bt2" href="{V1}" target="_blank" rel="noopener">Volume I — Capítulo 8 (PDF)</a>',
                  '<a class="bt2" href="dados.html#tese">A tese sai depois da defesa →</a>')
    s = s.replace(f'href="{V1}" target="_blank" rel="noopener"', 'href="dados.html#tese"')
    return s

grava('dados.html', f_dados)
grava('painel.html', f_painel)
grava('rede-ge.html', f_rede)
