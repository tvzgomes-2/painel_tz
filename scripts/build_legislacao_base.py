# -*- coding: utf-8 -*-
"""
build_legislacao_base.py — gera scripts/legislacao_tz.json a partir da BASE CONGELADA de 11/11/2026
(v1.0.0, 13/11/2026; decisão do autor: "atualizar"). Substitui a cadeia build_legislacao.py +
build_legislacao_padrao.py, que lia o levantamento legal de 18/09/2026 e uma tabela consolidada
que não está mais no cofre.

Fontes (só leitura):
  - base-mestre do congelamento (mesmo arquivo de build_data.py): "Legislação", "Ato vigente que
    concede (eixo 1)", "Link Legislação", "Confiab.", "Norma lida (A.2e)", "Mecanismo de custeio";
  - dados/7_documentos/normas_padronizadas_catalogo.csv: as normas lidas, reescritas em notas
    padronizadas e depositadas (DOI 10.5281/zenodo.24186039). A ficha do município linka cada uma.

Campos de saída (os mesmos que o painel já lia, mais `estado` e `padr`):
  norma (rótulo curto), extra (outros atos citados), nota (texto da base), link, conf, conf_nota,
  estado ('lida' | 'sem norma' | 'não localizada'), buscada, mecanismo, padr [{arq, rot, func}].

Uso:  python3 scripts/build_legislacao_base.py        (da raiz do repositório, depois de build_data.py)
"""
import csv, json, os, re
from urllib.parse import quote
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(BASE_DIR, '..', '..', 'doutorado')
DADOS = os.path.join(VAULT, '03 - Dados', '_data')
CONG = os.environ.get('TZ_CONGELAMENTO') or sorted(
    d[len('congelamento-'):] for d in os.listdir(DADOS) if d.startswith('congelamento-'))[-1]
MESTRE = os.path.join(DADOS, f'congelamento-{CONG}', 'Municípios TZ - consolidado.xlsx')
CATALOGO = os.path.join(BASE_DIR, '..', 'dados', '7_documentos', 'normas_padronizadas_catalogo.csv')
GH = 'https://github.com/tvzgomes-2/painel_tz/blob/main/dados/7_documentos/normas_padronizadas/'
OUT = os.path.join(BASE_DIR, 'legislacao_tz.json')
ESCOPO = ('Ativa', 'Encerrada')

def txt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return None
    s = re.sub(r'\s+', ' ', str(v)).strip()
    return None if s.lower() in ('', 'nan', 'none', '—', '-') else s

RE_EMOJI = re.compile('[\u2600-\u27BF\U0001F300-\U0001FAFF\uFE0F]')
def limpo(s, corta_alerta=True):
    """Texto de leitura, sem marcas de trabalho: corta no primeiro alerta (🚨, ⚠), tira emoji e Markdown."""
    if not s: return s
    if corta_alerta: s = re.split(r'🚨|⚠', s)[0]
    s = RE_EMOJI.sub('', s).replace('**', '').replace('`', '')
    s = re.sub(r'(?<!\w)\*(?!\s)|(?<=\S)\*(?!\w)', '', s)
    return re.sub(r'\s{2,}', ' ', s).strip(' .;—-')

def primeiro(s):
    """O primeiro ato de um texto livre: corta no primeiro ' — ', ' (', ';', ' + ' ou ', que'."""
    if not s: return None
    p = re.split(r' — | \(|;| \+ |, que |: ', s, maxsplit=1)[0].strip(' ,.')
    return (p[0].upper() + p[1:]) if p else None

def resto(s):
    if not s or ' + ' not in s: return None
    r = s.split(' + ', 1)[1]
    return primeiro(r)

def conf(v):
    v = txt(v)
    if not v: return None, None
    m = re.match(r'(alta|média|media|baixa)', v, re.I)
    base = m.group(1).lower().replace('media', 'média') if m else None
    return base, (v if v.lower() not in ('alta', 'média', 'baixa') else None)

def estado(v):
    v = (txt(v) or '').lower()
    if v.startswith('lida'): return 'lida'
    if v.startswith('não existe'): return 'sem norma'
    if v.startswith('não localizada'): return 'não localizada'
    return None

t = pd.read_excel(MESTRE, sheet_name='consolidado')
t = t[t['Situação'].isin(ESCOPO)]
cat = {}
with open(CATALOGO, encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f):
        cat.setdefault((r['municipio'].strip().lower(), r['uf'].strip().upper()), []).append(r)

out, sem_cod = {}, []
for _, r in t.iterrows():
    try: cod = str(int(float(r['Código IBGE'])))
    except (TypeError, ValueError): sem_cod.append(r['Município']); continue
    ato, leg = txt(r.get('Ato vigente que concede (eixo 1)')), txt(r.get('Legislação'))
    e = {}
    norma = primeiro(ato) or primeiro(leg)
    est = estado(r.get('Norma lida (A.2e)'))
    if norma and est != 'sem norma': e['norma'] = norma
    ex = resto(ato)
    if ex and ex != norma: e['extra'] = ex
    leg = limpo(leg)
    if leg and leg != norma: e['nota'] = leg if len(leg) <= 420 else leg[:417].rsplit(' ', 1)[0] + '…'
    link = txt(r.get('Link Legislação'))
    if link and link.startswith('http'): e['link'] = link
    c, cn = conf(r.get('Confiab.'))
    if c: e['conf'] = c
    if cn: e['conf_nota'] = limpo(cn, False)
    if est: e['estado'] = est
    if est in ('sem norma', 'não localizada'): e['buscada'] = True
    mec = txt(r.get('Mecanismo de custeio'))
    mec = limpo(mec)
    if mec and not mec.lower().startswith('não verificado'):
        e['mecanismo'] = mec if len(mec) <= 220 else mec[:217].rsplit(' ', 1)[0] + '…'
    pad = cat.get((str(r['Município']).strip().lower(), str(r['UF']).strip().upper()), [])
    if pad:
        e['padr'] = [{'arq': GH + quote(p['arquivo']),
                      'rot': f"{p['tipo_norma']} {p['numero']}/{p['ano']}".strip(),
                      'func': p.get('funcao_gratuidade') or None} for p in sorted(pad, key=lambda p: (p['ano'], p['numero']))]
    out[cod] = e

out = {k: out[k] for k in sorted(out, key=int)}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1); f.write('\n')
from collections import Counter
print(f'legislacao_tz.json: {len(out)} políticas (base {CONG}), {os.path.getsize(OUT)/1024:.0f} KB')
print('  estado da norma:', dict(Counter(v.get('estado') for v in out.values())))
print('  com nota padronizada no depósito:', sum(1 for v in out.values() if v.get('padr')),
      '| notas linkadas:', sum(len(v.get('padr', [])) for v in out.values()))
if sem_cod: print('  [ERRO] sem código IBGE:', sem_cod)
