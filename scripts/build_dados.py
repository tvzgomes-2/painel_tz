# -*- coding: utf-8 -*-
"""
build_dados.py — gera ../dados.html, a página de downloads dos dados da tese (13/11/2026, v1.0.0).

Lê a pasta dados/ (o depósito citado na tese, release dados-v1.0.0, DOI 10.5281/zenodo.24186039)
e NUNCA escreve nela. Só entram na página os arquivos versionados no git (`git ls-files`): os
roteiros que o .gitignore deixa fora do depósito, por trazerem nomes de sócios no código, não
aparecem. De cada arquivo: tamanho, SHA-256 (de dados/SHA256SUMS.txt) e, nos CSV, linhas e
colunas. A descrição de cada pacote, o que ficou de fora e as ressalvas vêm de dados/README.md,
para a página não contar uma história diferente do depósito.

Uso:  python3 scripts/build_dados.py        (da raiz do repositório)
"""
import csv, html, json, os, re, subprocess, sys
from collections import OrderedDict, defaultdict
from urllib.parse import quote

csv.field_size_limit(sys.maxsize)
RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DADOS = os.path.join(RAIZ, 'dados')
OUT = os.path.join(RAIZ, 'dados.html')
VERSAO = 'v1.0.0'
DOI_V, DOI_C = '10.5281/zenodo.24186039', '10.5281/zenodo.24186038'
GH = 'https://github.com/tvzgomes-2/painel_tz'
TAG = 'dados-v1.0.0'
e = html.escape

arqs = subprocess.run(['git', '-c', 'core.quotepath=off', 'ls-files', '-z', 'dados'], cwd=RAIZ,
                      capture_output=True, check=True).stdout.decode('utf-8').split('\0')
arqs = sorted(a[len('dados/'):] for a in arqs if a)
sha = {}
for ln in open(os.path.join(DADOS, 'SHA256SUMS.txt'), encoding='utf-8'):
    p = ln.rstrip('\n').split(None, 1)
    if len(p) == 2: sha[p[1].strip()] = p[0]

# ---- README do depósito ----
rd = open(os.path.join(DADOS, 'README.md'), encoding='utf-8').read()
def md(t):
    t = e(t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*(.+?)\*', r'<i>\1</i>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    return t
def secao(tit):
    m = re.search(r'^## ' + re.escape(tit) + r'\s*\n(.*?)(?=^## |\Z)', rd, re.S | re.M)
    return m.group(1).strip() if m else ''
pac = OrderedDict()
for ln in secao('Pacotes').splitlines():
    m = re.match(r'\|\s*`([^`]+)/`\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$', ln)
    if m: pac[m.group(1)] = (m.group(2), m.group(3))
# itens do README do depósito que a página não repete (decisão do autor, 13/11/2026); seguem no README
OMITIR = ('**Comprovantes e respostas dos pedidos', '**Três colunas da Base Municipal v3')
def lista(t):
    itens = [md(x[2:].strip()) for x in t.splitlines() if x.startswith('- ') and not x[2:].strip().startswith(OMITIR)]
    return '<ul>' + ''.join(f'<li>{i}</li>' for i in itens) + '</ul>'
abertura = md(rd.split('## Pacotes')[0].split('\n\n', 3)[-1].strip().split('\n\n')[-1])
# 13/11/2026 (autor): a página descreve o conteúdo; a data da base fica só no versionamento (rodapé e CHANGELOG)
abertura = 'Cada pacote corresponde ao que o Quadro α.1 do Volume II (Apêndices) atribui a cada apêndice. Os arquivos vêm em CSV, com dicionário das colunas e SHA-256.'

# ---- referências (aba Referências, 13/11/2026: só livros e capítulos, teses e artigos — decisão do autor) ----
REFS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'referencias_tz.json'), encoding='utf-8'))
def grupo_ref(chave, titulo):
    itens = REFS[chave]
    MARCA = '<span class="rsl" title="Faz parte do corpus da revisão sistemática da literatura (Apêndice C)">RSL</span> '
    ATR = ' data-rsl="1"'
    lis = ''.join(f'<li data-q="{e(r["q"])}"{ATR if r.get("rsl") else ""}>{MARCA if r.get("rsl") else ""}{r["h"]}</li>' for r in itens)
    return f'<section class="refgrupo" id="ref-{chave}"><h2>{titulo} <span class="nref">{len(itens)}</span></h2><ol class="refs">{lis}</ol></section>'
GRUPOS_REF = [('livros', 'Livros e capítulos de livro'), ('teses', 'Teses e dissertações'), ('artigos', 'Artigos'), ('eventos', 'Trabalhos em eventos'), ('outros', 'Relatórios e outros documentos')]
N_REFS = sum(len(REFS[k]) for k, _ in GRUPOS_REF)
REFERENCIAS = ''.join(grupo_ref(k, t) for k, t in GRUPOS_REF if REFS[k])

# ---- arquivos ----
def tam(n):
    for u in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or u == 'GB':
            return (f'{n:.0f} {u}' if u == 'B' else f'{n:.1f} {u}').replace('.', ',')
        n /= 1024
def info_csv(p):
    try:
        with open(p, encoding='utf-8-sig', newline='') as f:
            r = csv.reader(f); cab = next(r, []); n = sum(1 for _ in r)
        return n, cab
    except Exception:
        return None, None
def link(rel):
    if rel.lower().endswith('.md'):
        return f'{GH}/blob/main/dados/{quote(rel)}', False     # Markdown: o GitHub mostra formatado
    return 'dados/' + quote(rel), True

grupos = defaultdict(lambda: defaultdict(list))   # pacote -> subpasta -> arquivos
soltos = []
for a in arqs:
    partes = a.split('/')
    if len(partes) == 1: soltos.append(a); continue
    grupos[partes[0]]['/'.join(partes[1:-1])].append(a)

tot_bytes = sum(os.path.getsize(os.path.join(DADOS, a)) for a in arqs)
sem_sha = [a for a in arqs if a not in sha and a != 'SHA256SUMS.txt']

# dicionários: rótulo da coluna (Base Municipal v3) e preenchimento/exemplos (base de políticas)
DIC = {}
with open(os.path.join(DADOS, '2_base_municipal', 'base_municipal_v3_dicionario.csv'), encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f):
        if not r['id'].endswith('.csv'): DIC[('base_municipal_v3.csv', r['id'])] = ' · '.join(x for x in (r.get('rotulo'), r.get('fonte'), r.get('unidade')) if x)
with open(os.path.join(DADOS, '1_politicas', 'tz_dicionario.csv'), encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f):
        DIC[(r['arquivo'], r['coluna'])] = f"{r['preenchidas']} de {r['linhas']} preenchidas" + (f" · ex.: {r['exemplos']}" if r.get('exemplos') else '')

def linha(a):
    p = os.path.join(DADOS, a); href, baixa = link(a)
    nome = a.split('/')[-1]
    det, cols = '', ''
    if a.lower().endswith('.csv'):
        n, cab = info_csv(p)
        if n is not None:
            det = f'{n:,} linhas · {len(cab)} colunas'.replace(',', '.')
            arq = a.split('/')[-1]
            col = lambda c: (f'<span title="{e(DIC[(arq, c)])}" class="temdic">{e(c)}</span>' if (arq, c) in DIC else e(c))
            ndic = sum(1 for c in cab if (arq, c) in DIC)
            cols = (f'<details class="cols"><summary>colunas{" · com dicionário (passe o mouse)" if ndic else ""}</summary><div>{", ".join(col(c) for c in cab)}</div></details>')
    h = sha.get(a, '')
    return (f'<tr data-q="{e(a.lower())}"><td><a href="{href}"{" download" if baixa else " target=_blank rel=noopener"}>{e(nome)}</a>{cols}</td>'
            f'<td class="n">{tam(os.path.getsize(p))}</td><td class="n">{det}</td>'
            f'<td class="sha"><code title="{h}">{h[:12]}…</code></td></tr>' if h else
            f'<tr data-q="{e(a.lower())}"><td><a href="{href}"{" download" if baixa else ""}>{e(nome)}</a>{cols}</td><td class="n">{tam(os.path.getsize(p))}</td><td class="n">{det}</td><td class="sha">—</td></tr>')

blocos = []
for i, (pk, (desc, apend)) in enumerate(pac.items(), 1):
    sub = grupos.get(pk, {})
    n = sum(len(v) for v in sub.values())
    b = sum(os.path.getsize(os.path.join(DADOS, a)) for v in sub.values() for a in v)
    corpo = ''
    for sp in sorted(sub, key=lambda s: (s != '', s)):
        fs = sub[sp]
        tab = '<table class="arqs"><thead><tr><th>Arquivo</th><th>Tamanho</th><th>Conteúdo</th><th>SHA-256</th></tr></thead><tbody>' + ''.join(linha(a) for a in fs) + '</tbody></table>'
        if sp and len(fs) > 6:
            corpo += f'<details class="pasta"><summary><b>{e(sp)}/</b> — {len(fs)} arquivos ({tam(sum(os.path.getsize(os.path.join(DADOS, a)) for a in fs))})</summary>{tab}</details>'
        else:
            corpo += (f'<h4>{e(sp)}/</h4>' if sp else '') + tab
    # 13/11/2026 (autor): cada pacote abre recolhido; o cabeçalho é o botão que abre
    blocos.append(f'''<details class="pacote" id="p{i}">
  <summary class="phead"><span class="pnum">{i}</span><div><h2><code>{e(pk)}/</code></h2><p>{md(desc)}</p>
  <div class="pmeta">{n} arquivos · {tam(b)} · Apêndice {e(apend)} da tese · <a href="{GH}/tree/main/dados/{quote(pk)}" target="_blank" rel="noopener">ver no GitHub</a></div></div><span class="pseta" aria-hidden="true">▾</span></summary>
  {corpo}
</details>''')

# 13/11/2026 (decisão do autor): Dados e Conceitos viram uma página só, com duas abas. Os verbetes têm
# a fonte em scripts/verbetes-fonte.html (verbetes.html virou um redirecionamento para dados.html#conceitos);
# o estilo, o rodapé e o conteúdo da aba Conceitos saem de lá.
CSS = open(os.path.join(RAIZ, 'scripts', 'verbetes-fonte.html'), encoding='utf-8').read()
w0 = CSS.index('<div class="wrap">') + len('<div class="wrap">')
w1 = CSS.index('<aside class="cta-dados"') if '<aside class="cta-dados"' in CSS else CSS.index('<footer>')
CONCEITOS = CSS[w0:w1].strip()
INTRO_CONCEITOS = re.search(r'<p class="resumo">(.*?)</p>', CSS, re.S).group(1)

estilo = re.search(r'<style>\s*:root\{.*?</style>\s*<style>.*?</style>', CSS, re.S).group(0)
estilo = re.sub(r'\.wrap\{max-width:760px;', '.wrap{max-width:1040px;', estilo)
estilo = re.sub(r'header h1\{([^}]*)max-width:760px;', r'header h1{\1max-width:1040px;', estilo)
estilo = estilo.replace('header .resumo{margin:0;color:var(--text);font-size:13.5px;line-height:1.6;max-width:760px;}',
                        'header .resumo{margin:0;color:var(--text);font-size:13.5px;line-height:1.6;max-width:820px;}')
extra = '''<style>
  /* página de dados (13/11/2026) */
  .wrap a{color:#8fb0ff;} .wrap a:hover{color:var(--amarelo);}
  .doi{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:16px;margin-bottom:26px;}
  @media (max-width:760px){ .doi{grid-template-columns:1fr;} }
  .box{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px 20px;}
  .box h3{margin:0 0 8px;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:var(--amarelo);}
  .box p{margin:0 0 8px;font-size:13px;line-height:1.6;}
  .cita{background:var(--panel2);border-left:3px solid var(--rosa);border-radius:6px;padding:10px 12px;font-size:12.5px;line-height:1.55;}
  .btn{display:inline-block;background:var(--rosa);color:#fff !important;font-weight:700;font-size:12.5px;text-decoration:none;padding:8px 14px;border-radius:6px;margin:4px 6px 4px 0;border:0;cursor:pointer;font-family:inherit;}
  .btn.sec{background:var(--panel2);border:1px solid var(--border);color:var(--text) !important;}
  .btn:hover{filter:brightness(1.1);}
  .btn.off{background:var(--panel2);border:1px dashed var(--border);color:var(--muted) !important;cursor:not-allowed;filter:none;}
  .rotcita{margin:0 0 4px !important;font-size:10.5px !important;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);}
  .num{display:flex;gap:22px;flex-wrap:wrap;margin:6px 0 2px;}
  .num div b{display:block;font-size:24px;font-weight:800;color:var(--text);}
  .num div span{font-size:11.5px;color:var(--muted);}
  .busca{display:flex;gap:10px;align-items:center;margin:0 0 18px;flex-wrap:wrap;}
  .busca input{flex:1 1 280px;background:var(--panel2);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:9px 12px;font:inherit;font-size:13px;}
  .busca span{font-size:12px;color:var(--muted);}
  .toc{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:24px;}
  .toc a{background:var(--panel2);border:1px solid var(--border);color:var(--text) !important;text-decoration:none;font-size:12px;font-weight:600;padding:6px 12px;border-radius:20px;}
  .toc a:hover{border-color:var(--rosa);}
  .pacote{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin-bottom:18px;scroll-margin-top:16px;}
  .phead{display:flex;gap:14px;align-items:flex-start;margin:0;cursor:pointer;list-style:none;}
  .phead::-webkit-details-marker{display:none;}
  .phead > div{flex:1 1 auto;min-width:0;}
  .pseta{flex:0 0 auto;font-size:18px;color:var(--muted);transition:transform .15s;margin-top:2px;}
  details.pacote[open] > .phead{margin-bottom:10px;} details.pacote[open] > .phead .pseta{transform:rotate(180deg);color:var(--amarelo);}
  details.pacote > .phead:hover .pseta{color:var(--amarelo);} details.pacote > .phead:hover h2{color:var(--amarelo);}
  .pnum{flex:0 0 auto;width:32px;height:32px;border-radius:50%;background:var(--rosa);color:#fff;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:15px;}
  .phead h2{margin:2px 0 4px;font-size:17px;} .phead h2 code{font-family:inherit;}
  .phead p{margin:0 0 4px;font-size:13px;line-height:1.55;}
  .pmeta{font-size:11.5px;color:var(--muted);}
  .pacote h4{margin:14px 0 4px;font-size:12px;color:var(--muted);font-weight:700;}
  table.arqs{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px;}
  table.arqs th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);border-bottom:1px solid var(--border);padding:5px 6px;font-weight:700;}
  table.arqs td{border-bottom:1px solid rgba(255,255,255,.05);padding:6px;vertical-align:top;}
  table.arqs td.n{white-space:nowrap;color:var(--muted);}
  table.arqs td.sha code{font-size:11px;color:var(--muted);cursor:copy;}
  table.arqs td a{word-break:break-word;}
  details.cols summary{font-size:11px;color:var(--muted);cursor:pointer;margin-top:2px;}
  details.cols div{font-size:11px;color:var(--muted);line-height:1.5;margin-top:4px;max-height:160px;overflow:auto;}
  details.pasta{margin-top:10px;border:1px solid var(--border);border-radius:8px;padding:8px 10px;background:var(--panel2);}
  details.pasta summary{cursor:pointer;font-size:12.5px;}
  .fora ul, .ress ul{margin:6px 0 0;padding-left:18px;} .fora li, .ress li{font-size:13px;line-height:1.6;margin-bottom:6px;}
  code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.92em;}
  /* abas como botões grandes (13/11/2026, autor: "tornar esses dois botões mais visíveis") */
  .abas{display:flex;gap:10px;margin:0 0 26px;flex-wrap:wrap;padding-bottom:14px;border-bottom:1px solid var(--border);}
  .abas button{background:var(--panel2);border:2px solid var(--border);color:var(--text);font:inherit;font-size:16px;font-weight:800;
    letter-spacing:.01em;padding:12px 26px;border-radius:10px;cursor:pointer;transition:border-color .15s,background .15s;}
  .abas button:hover{border-color:var(--amarelo);}
  .abas button[aria-selected="true"]{background:var(--amarelo);border-color:var(--amarelo);color:#0E0E10;}
  .abas button:focus-visible{outline:3px solid var(--rosa);outline-offset:2px;}
  @media (max-width:640px){ .abas button{flex:1 1 0;padding:11px 12px;font-size:15px;} }
  .intro-aba{font-size:13.5px;line-height:1.6;color:var(--muted);margin:0 0 20px;max-width:820px;}
  #aba-conceitos .verbete, #aba-conceitos .aviso{max-width:820px;}
  .refgrupo{margin:22px 0 0;}
  .refgrupo h2{font-size:17px;margin:0 0 10px;padding-bottom:6px;border-bottom:1px solid var(--border);}
  .refgrupo .nref{font-size:12px;font-weight:800;background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:1px 8px;margin-left:6px;vertical-align:middle;color:var(--muted);}
  ol.refs{list-style:none;margin:0;padding:0;max-width:900px;}
  ol.refs li{font-size:13.5px;line-height:1.55;padding:6px 0 6px 22px;text-indent:-22px;border-bottom:1px dashed rgba(255,255,255,.06);overflow-wrap:anywhere;}
  ol.refs li b{color:var(--text);}
  ol.refs li a{color:var(--rosa);}
  .rsl{display:inline-block;font-size:10.5px;font-weight:800;letter-spacing:.05em;color:#0E0E10;background:var(--rosa);border-radius:4px;padding:1px 6px;margin-right:4px;vertical-align:1px;text-indent:0;}
  .so-rsl{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--text);margin:0 12px;white-space:nowrap;cursor:pointer;}
  .temdic{border-bottom:1px dotted var(--muted);cursor:help;}
  @media (max-width:640px){ table.arqs th:nth-child(4), table.arqs td.sha{display:none;} .wrap{padding:20px 16px 50px;} }
</style>'''

nav = ('<nav class="sitenav" aria-label="Páginas do site"><a class="marca" href="index.html">Transporte Público em <b>Crise</b></a><span class="links">'
       '<a href="painel.html">Painel Brasil</a><a href="rede-ge.html">Rede de empresas</a>'
       '<a href="dados.html" aria-current="page">Dados e conceitos</a><a href="pesquisa.html">Contribua</a></span></nav>')
rodape = re.search(r'<footer>.*?</footer>', CSS, re.S)
rodape = rodape.group(0) if rodape else ''
# 13/11/2026: o título do depósito acompanha o da tese (Volume I r103: "Transporte público em crise:
# o papel dos grupos econômicos nas experiências de Tarifa Zero no Brasil"). Duas citações: a tese
# e os dados. Folhas e data da defesa da tese entram depois da defesa [A CONFIRMAR].
TIT_TESE = 'Transporte público em crise'
SUB_TESE = 'o papel dos grupos econômicos nas experiências de Tarifa Zero no Brasil'
cita_tese = (f'GOMES, Thiago Von Zeidler. <b>{TIT_TESE}</b>: {SUB_TESE}. 2026. Tese (Doutorado em Planejamento e Gestão '
             'do Território) – Programa de Pós-Graduação em Planejamento e Gestão do Território, Universidade Federal do ABC, '
             'São Bernardo do Campo, 2026. Orientadora: Silvana Zioni.')
cita = (f'GOMES, Thiago Von Zeidler. <b>{TIT_TESE}</b>: {SUB_TESE} — dados, scripts e painel da tese de doutorado. '
        'Versão 2026-11-11. [<i>S. l.</i>]: Zenodo, 2026. Conjunto de dados. DOI: '
        f'<a href="https://doi.org/{DOI_V}">https://doi.org/{DOI_V}</a>.')
# Os dois volumes do texto: o botão aparece ativo quando o PDF estiver no repositório (pasta tese/);
# até lá, a página diz que o texto sai depois da defesa.
VOLUMES = [('Volume I — Texto', 'tese/Tese - Volume I - Texto.pdf'), ('Volume II — Apêndices', 'tese/Tese - Volume II - Apêndices.pdf')]
def botao_vol(rot, rel):
    if os.path.exists(os.path.join(RAIZ, rel)):
        return f'<a class="btn" href="{quote(rel)}" download>{e(rot)} (PDF, {tam(os.path.getsize(os.path.join(RAIZ, rel)))})</a>'
    return f'<span class="btn off" aria-disabled="true" title="Disponível depois da defesa">{e(rot)}</span>'
vol_ok = all(os.path.exists(os.path.join(RAIZ, r)) for _, r in VOLUMES)
jsonld = json.dumps({
    '@context': 'https://schema.org', '@type': 'Dataset',
    'name': f'{TIT_TESE}: {SUB_TESE} — dados, scripts e painel da tese de doutorado',
    'description': 'Base de políticas municipais de Tarifa Zero, régua de classificação, Base Municipal v3 dos 5.570 municípios, '
                   'testes da hipótese, rede de grupos econômicos do transporte coletivo (sem nomes de sócios pessoas físicas), arranjo e '
                   'contratos, revisão sistemática, normas padronizadas e scripts.',
    'url': 'https://tvzgomes-2.github.io/painel_tz/dados.html', 'identifier': f'https://doi.org/{DOI_V}', 'sameAs': f'https://doi.org/{DOI_C}',
    'version': '2026-11-11', 'license': 'https://creativecommons.org/licenses/by/4.0/', 'inLanguage': 'pt-BR', 'isAccessibleForFree': True,
    'creator': {'@type': 'Person', 'name': 'Thiago Von Zeidler Gomes', 'affiliation': 'Universidade Federal do ABC'},
    'contributor': {'@type': 'Person', 'name': 'Silvana Zioni', 'affiliation': 'Universidade Federal do ABC'},
    'keywords': ['Tarifa Zero', 'transporte público coletivo', 'grupos econômicos', 'política urbana', 'Brasil'],
    'spatialCoverage': 'Brasil',
    'distribution': [{'@type': 'DataDownload', 'encodingFormat': 'application/zip', 'contentUrl': f'{GH}/archive/refs/tags/{TAG}.zip'}],
}, ensure_ascii=False)
# ---- Podcast (aba própria): episódios em scripts/podcasts.json; áudios e transcrições em assets/podcast/ ----
POD = json.load(open(os.path.join(RAIZ, 'scripts', 'podcasts.json'), encoding='utf-8'))
def _transcricao(rel):
    p = os.path.join(RAIZ, rel)
    if not os.path.exists(p): return ''
    corpo = open(p, encoding='utf-8').read().split('\n\n', 1)[1]
    out = []
    for b in corpo.strip().split('\n\n'):
        m = re.match(r'^\((\d+:\d+) - (\d+:\d+)\)\n(.*)$', b, re.S)
        if b.startswith('[ATENÇÃO'):
            out.append(f'<p class="aviso">{e(b.strip()[1:-1])}</p>'); continue
        out.append(f'<p><span class="ts">{m.group(1)}</span> {e(m.group(3).strip())}</p>' if m else f'<p>{e(b.strip())}</p>')
    return ''.join(out)
def _episodio(ep):
    au, tx = ep['audio'], ep['transcricao']
    ok = os.path.exists(os.path.join(RAIZ, au))
    tam_au = tam(os.path.getsize(os.path.join(RAIZ, au))) if ok else ''
    ext = os.path.splitext(au)[1][1:].upper()
    def _lin(r):
        av = r[3] if len(r) > 3 else ''
        cls = ' class="av"' if av else ''
        nota = f'<p class="aviso">Atenção — o que a tese diz: {e(av)}</p>' if av else ''
        return f'<tr{cls}><td class="min">{e(r[0])}</td><td>{e(r[1])}{nota}</td><td class="onde">{e(r[2])}</td></tr>'
    rot = ''.join(_lin(r) for r in ep.get('roteiro', []))
    n_av = sum(1 for r in ep.get('roteiro', []) if len(r) > 3 and r[3])
    return (f'<article class="ep" id="podcast-{ep["n"]}"><div class="ep-cab"><span class="ep-n">Parte {ep["n"]}</span>'
            f'<h3>{e(ep["titulo"])}</h3><p class="ep-meta">{e(ep["duracao"])} · {e(ep["capitulos"])}</p></div>'
            f'<p class="ep-res">{e(ep["resumo"])}</p>'
            + (f'<audio controls preload="none" src="{quote(au)}"></audio>' if ok else '<p class="ep-meta">Áudio em preparação.</p>')
            + '<p class="ep-bt">'
            + (f'<a class="btn" href="{quote(au)}" download>Baixar o áudio ({ext}, {tam_au})</a> ' if ok else '')
            + f'<a class="btn sec" href="{quote(tx)}" download>Baixar a transcrição (TXT)</a></p>'
            + (f'<details class="ep-rot" open><summary>Onde está na tese · {len(ep["roteiro"]) - n_av} trechos e {n_av} avisos</summary>'
               f'<div class="tabwrap"><table class="cor rot"><thead><tr><th>Minuto</th><th>Assunto</th><th>Na tese</th></tr></thead><tbody>{rot}</tbody></table></div></details>' if rot else '')
            + f'<details class="ep-tx"><summary>Ler a transcrição</summary><p class="ep-meta">Transcrição automática, sem revisão. Os avisos em destaque dizem o que a tese diz onde a conversa simplifica demais ou erra.</p><div class="tx">{_transcricao(tx)}</div></details></article>')
PODCAST = ('<style>'
    '.pod-intro{max-width:900px;}'
    '.pod-nomes{font-size:12.5px;color:var(--muted);max-width:900px;margin:-4px 0 18px;}'
    '.ep{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin:0 0 18px;}'
    '.ep-cab h3{margin:2px 0 2px;font-size:20px;} .ep-n{display:inline-block;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:#111;background:var(--amarelo);padding:2px 8px;border-radius:4px;}'
    '.ep-meta{font-size:12.5px;color:var(--muted);margin:2px 0;} .ep-res{font-size:14px;line-height:1.6;max-width:900px;}'
    '.ep audio{width:100%;max-width:720px;margin:8px 0 6px;display:block;}'
    '.ep details{margin-top:12px;border-top:1px solid var(--border);padding-top:10px;} .ep details > summary{cursor:pointer;font-weight:700;font-size:14px;}'
    '.ep .tabwrap{overflow-x:auto;margin-top:8px;} table.cor{border-collapse:collapse;width:100%;min-width:640px;font-size:12.5px;}'
    'table.cor th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);padding:6px 8px;border-bottom:1px solid var(--border);}'
    'table.cor td{vertical-align:top;padding:8px;border-bottom:1px solid var(--border);line-height:1.5;} table.cor td.min{white-space:nowrap;font-weight:700;color:var(--amarelo);} table.cor td.onde{font-size:11.5px;color:var(--muted);min-width:110px;}'
    '.aviso{margin:6px 0 2px;padding:6px 10px;border-left:3px solid var(--rosa);background:rgba(255,45,107,.08);font-size:12.5px;line-height:1.5;color:var(--text);} table.cor tr.av td.min{color:var(--rosa);}'
    '.ep .tx{max-height:480px;overflow:auto;font-size:13px;line-height:1.6;padding-right:8px;} .ep .tx .ts{font-size:11px;font-weight:700;color:var(--muted);margin-right:4px;}'
    '</style>'
    f'<p class="intro-aba pod-intro">{e(POD["intro"])}</p>' + (f'<p class="pod-nomes">{e(POD["nomes"])}</p>' if POD.get('nomes') else '')
    + ''.join(_episodio(ep) for ep in POD['episodios']))

pagina = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dados e conceitos — Transporte Público em Crise</title>
<meta name="description" content="Os conceitos da pesquisa sobre Tarifa Zero e grupos econômicos e os dados que a tese cita, para baixar: oito pacotes em CSV, com dicionário, SHA-256 e DOI, e os dois volumes da tese.">
{re.search(r'<link rel="icon".*?>', CSS).group(0)}
<meta property="og:type" content="website">
<meta property="og:site_name" content="Transporte Público em Crise">
<meta property="og:title" content="Dados e conceitos — Transporte público em crise">
<meta property="og:description" content="Oito pacotes de dados abertos da tese, com DOI no Zenodo, e os dois volumes do texto.">
<meta property="og:url" content="https://tvzgomes-2.github.io/painel_tz/dados.html">
<meta property="og:image" content="https://tvzgomes-2.github.io/painel_tz/assets/og/compartilhar.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:locale" content="pt_BR">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
{estilo}
{extra}
<script type="application/ld+json">{jsonld}</script>
</head>
<body>
{nav}
<header>
  <h1>Dados <span class="hl">e conceitos</span> <span style="display:inline-block;font-size:11.5px;font-weight:800;text-transform:uppercase;background:var(--amarelo);color:#111;padding:3px 10px;border-radius:4px;margin-left:10px;vertical-align:middle;letter-spacing:.05em;transform:rotate(-2deg);">dados · {VERSAO}</span></h1>
  <p class="resumo">Os dados da tese, para baixar: as 193 políticas de Tarifa Zero e a régua que as classifica, a Base Municipal dos 5.570 municípios, os testes da hipótese, as empresas e ligações dos 327 grupos econômicos, os contratos e o custeio, a revisão sistemática, as 315 normas lidas e os scripts — além dos dois volumes da tese. Na aba Conceitos, um verbete para cada termo da pesquisa; em Referências, os livros, teses e artigos citados; em Podcast, três conversas em áudio sobre a tese.</p>
</header>
<div class="wrap">
  <nav class="abas" role="tablist" aria-label="Dados e conceitos">
    <button type="button" role="tab" id="tab-conceitos" aria-controls="aba-conceitos" data-aba="conceitos">Conceitos</button>
    <button type="button" role="tab" id="tab-dados" aria-controls="aba-dados" data-aba="dados">Dados da tese</button>
    <button type="button" role="tab" id="tab-referencias" aria-controls="aba-referencias" data-aba="referencias">Referências</button>
    <button type="button" role="tab" id="tab-podcast" aria-controls="aba-podcast" data-aba="podcast">Podcast</button>
  </nav>
  <section class="aba" id="aba-conceitos" role="tabpanel" aria-labelledby="tab-conceitos" hidden>
  <p class="intro-aba">{INTRO_CONCEITOS}</p>
  {CONCEITOS}
  </section>
  <section class="aba" id="aba-referencias" role="tabpanel" aria-labelledby="tab-referencias" hidden>
  <p class="intro-aba">Os livros, capítulos de livro, teses e artigos citados na tese e os {REFS["n_corpus"]} trabalhos do corpus da revisão sistemática da literatura, cada um no grupo do seu tipo. A marca <span class="rsl">RSL</span> indica que o trabalho faz parte do corpus (protocolo e fichamentos no Apêndice C). Notícias, normas, relatórios, bases de dados, anais e dissertações citados fora do corpus estão na lista completa, no fim do Volume I.</p>
  <div class="busca"><input id="filtroRef" type="search" placeholder="Filtrar por autor, título ou ano…" autocomplete="off"><label class="so-rsl"><input type="checkbox" id="soRsl"> só o corpus da <span class="rsl">RSL</span></label><span id="contagemRef"></span></div>
  <div class="toc">{''.join(f'<a href="#ref-{k}">{t} · {len(REFS[k])}</a>' for k, t in GRUPOS_REF if REFS[k])}</div>
  {REFERENCIAS}
  </section>
  <section class="aba" id="aba-podcast" role="tabpanel" aria-labelledby="tab-podcast" hidden>
  {PODCAST}
  </section>
  <section class="aba" id="aba-dados" role="tabpanel" aria-labelledby="tab-dados">
  <p class="intro-aba">{abertura}</p>
  <div class="doi">
    <div class="box">
      <h3>Como citar</h3>
      <p class="rotcita">A tese</p>
      <div class="cita" id="citaTese">{cita_tese}</div>
      <p style="margin:6px 0 12px;"><button class="btn sec copia" type="button" data-alvo="citaTese">Copiar a citação da tese</button></p>
      <p class="rotcita">Os dados</p>
      <div class="cita" id="cita">{cita}</div>
      <p style="margin-top:6px;"><button class="btn copia" type="button" data-alvo="cita">Copiar a citação dos dados</button>
      <a class="btn sec" href="https://doi.org/{DOI_V}" target="_blank" rel="noopener">Ver no Zenodo</a></p>
      <p style="font-size:12px;color:var(--muted);">Para citar a versão mais recente, e não esta, use o DOI de todas as versões: <a href="https://doi.org/{DOI_C}">{DOI_C}</a>. Licenças: dados <b>CC BY 4.0</b> · scripts <b>MIT</b>.</p>
    </div>
    <div class="box">
      <h3>A tese, em dois volumes</h3>
      <p style="margin-top:4px;">{botao_vol(*VOLUMES[0])} {botao_vol(*VOLUMES[1])}</p>
      {'' if vol_ok else '<p style="font-size:12px;color:var(--muted);">O texto completo da tese fica disponível aqui depois da defesa; os dados já estão abertos.</p>'}
      <h3 style="margin-top:16px;">Os dados, completos</h3>
      <div class="num"><div><b>{len(pac)}</b><span>pacotes</span></div><div><b>{len(arqs):,}</b><span>arquivos</span></div><div><b>{tam(tot_bytes)}</b><span>no total</span></div></div>
      <p style="margin-top:8px;"><a class="btn" href="https://doi.org/{DOI_V}" target="_blank" rel="noopener">Arquivo completo no Zenodo</a>
      <a class="btn sec" href="{GH}/archive/refs/tags/{TAG}.zip">ZIP da release no GitHub</a></p>
    </div>
  </div>

  <div class="toc">{''.join(f'<a href="#p{i}">{i} · {e(pk.split("_", 1)[1].replace("_", " "))}</a>' for i, pk in enumerate(pac, 1))}<a href="#fora">o que ficou de fora</a></div>
  <div class="busca"><input id="filtro" type="search" placeholder="Filtrar arquivos pelo nome (ex.: regua, grupos, Alumínio)…" autocomplete="off"><span id="contagem"></span></div>

  {''.join(blocos)}

  <details class="pacote fora" id="fora"><summary class="phead"><div><h2 style="margin:0;font-size:17px;">O que ficou de fora, e por quê</h2></div><span class="pseta" aria-hidden="true">▾</span></summary>{lista(secao('O que ficou de fora, e por quê'))}</details>
  </section>
  {rodape.replace('<footer>', '<footer><div style="margin-bottom:8px;">Dados e conceitos ' + VERSAO + ' · era Canoa · base de 11/11/2026</div>', 1)}
</div>
<script>
(() => {{
  // abas: #conceitos, ou o id de um verbete, abre Conceitos; o resto abre Dados
  const abas = [...document.querySelectorAll('.abas button')];
  const abre = (nome, alvo, grava) => {{
    abas.forEach(b => b.setAttribute('aria-selected', b.dataset.aba === nome ? 'true' : 'false'));
    document.querySelectorAll('section.aba').forEach(sc => sc.hidden = sc.id !== 'aba-' + nome);
    if (grava) history.replaceState(null, '', '#' + nome);
    if (alvo) setTimeout(() => alvo.scrollIntoView({{ block: 'start' }}), 30);
  }};
  abas.forEach(b => b.addEventListener('click', () => abre(b.dataset.aba, null, true)));
  const daHash = () => {{
    const h = decodeURIComponent(location.hash.slice(1));
    const el = h && document.getElementById(h);
    if (h === 'conceitos' || (el && el.closest('#aba-conceitos'))) abre('conceitos', h === 'conceitos' ? null : el);
    else if (h === 'referencias' || (el && el.closest('#aba-referencias'))) abre('referencias', h === 'referencias' ? null : el);
    else if (h === 'podcast' || (el && el.closest('#aba-podcast'))) abre('podcast', h === 'podcast' ? null : el);
    else abre('dados', el && h !== 'dados' ? el : null);
  }};
  const abrePacote = () => {{ const el = document.getElementById(decodeURIComponent(location.hash.slice(1))); if (el && el.matches('details.pacote')) el.open = true; }};
  window.addEventListener('hashchange', () => {{ daHash(); abrePacote(); }}); daHash(); abrePacote();
  document.querySelectorAll('.toc a[href^="#p"], .toc a[href="#fora"]').forEach(a => a.addEventListener('click', () => {{ const el = document.getElementById(a.getAttribute('href').slice(1)); if (el) el.open = true; }}));
  document.querySelectorAll('#aba-conceitos a[href^="#"]').forEach(a => a.addEventListener('click', ev => {{
    const el = document.getElementById(a.getAttribute('href').slice(1)); if (el) {{ ev.preventDefault(); history.replaceState(null, '', a.getAttribute('href')); el.scrollIntoView({{ block: 'start' }}); }}
  }}));
  // filtro das referências
  const fr = document.getElementById('filtroRef'), cr = document.getElementById('contagemRef');
  const lr = [...document.querySelectorAll('ol.refs li')];
  const normR = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ł/g, 'l').replace(/Ł/g, 'L').toLowerCase();
  const aplicaR = () => {{
    const q = normR(fr.value.trim()); let n = 0;
    const so = document.getElementById('soRsl').checked;
    for (const li of lr) {{ const ok = (!q || normR(li.dataset.q).includes(q)) && (!so || !!li.dataset.rsl); li.hidden = !ok; n += ok ? 1 : 0; }}
    document.querySelectorAll('section.refgrupo').forEach(sg => {{ sg.hidden = (!!q || so) && !sg.querySelectorAll('li:not([hidden])').length; }});
    cr.textContent = (q || so) ? n + ' referência(s)' : lr.length + ' referências';
  }};
  fr.addEventListener('input', aplicaR); document.getElementById('soRsl').addEventListener('change', aplicaR); aplicaR();
  const f = document.getElementById('filtro'), cont = document.getElementById('contagem');
  const linhas = [...document.querySelectorAll('table.arqs tbody tr')];
  const norm = s => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
  const aplica = () => {{
    const q = norm(f.value.trim()); let n = 0;
    for (const tr of linhas) {{ const ok = !q || norm(tr.dataset.q).includes(q); tr.hidden = !ok; n += ok; }}
    document.querySelectorAll('details.pasta').forEach(d => {{ const vis = d.querySelectorAll('tbody tr:not([hidden])').length; d.hidden = !!q && !vis; if (q && vis) d.open = true; }});
    document.querySelectorAll('details.pacote[id^="p"]').forEach(s => {{ const vis = s.querySelectorAll('tbody tr:not([hidden])').length; s.hidden = !!q && !vis; if (q && vis) s.open = true; }});
    cont.textContent = q ? n + ' arquivo(s)' : linhas.length + ' arquivos';
  }};
  f.addEventListener('input', aplica); aplica();
  document.querySelectorAll('button.copia').forEach(bt => bt.addEventListener('click', async () => {{
    const rot = bt.textContent, t = document.getElementById(bt.dataset.alvo).innerText;
    try {{ await navigator.clipboard.writeText(t); bt.textContent = 'Copiada'; }} catch (_) {{ bt.textContent = 'Selecione e copie'; }}
    setTimeout(() => bt.textContent = rot, 2000);
  }}));
  document.querySelectorAll('td.sha code').forEach(c => c.addEventListener('click', async () => {{
    try {{ await navigator.clipboard.writeText(c.title); const o = c.textContent; c.textContent = 'copiado'; setTimeout(() => c.textContent = o, 1200); }} catch (_) {{}}
  }}));
}})();
</script>
</body>
</html>
'''
open(OUT, 'w', encoding='utf-8').write(pagina)
print(f'dados.html: {len(pac)} pacotes, {len(arqs)} arquivos ({tam(tot_bytes)}), {os.path.getsize(OUT)/1024:.0f} KB')
if sem_sha: print('  sem SHA-256 no manifesto:', sem_sha)
