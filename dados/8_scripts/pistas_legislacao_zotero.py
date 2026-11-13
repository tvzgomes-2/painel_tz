#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pistas_legislacao_zotero.py  (read-only)

Cruza os itens da antiga coleção "Leis de Tarifa Zero" do Zotero (biblioteca 1 / pessoal) com a
pasta `03 - Dados/_data/Legislacao e contratos TZ/normas/` e lista, como PISTAS para a pesquisa de
legislação, tudo o que o Zotero cita e que NÃO está (ou está só em forma precária) em normas/.

Fonte do Zotero: o backup `zotero.sqlite.pre-excluir-leis-tz-20261021.bak` (os 64 itens ainda existem
nele; 53 foram apagados do banco vivo em 21/10/2026). O script abre o banco SOMENTE LEITURA e nunca
escreve no Zotero nem em normas/.

Uso (a partir da raiz do cofre, ou informe os caminhos):
    python3 _meta/scripts/pistas_legislacao_zotero.py
    python3 _meta/scripts/pistas_legislacao_zotero.py --bak /caminho/zotero.sqlite.pre-...bak \
        --normas "03 - Dados/_data/Legislacao e contratos TZ/normas" --saida _meta

Saídas (na pasta --saida):  `Pistas de legislação (Zotero x normas) AAAA-MM-DD.md` e `.csv`.

Status por item (pista, do mais forte ao mais fraco):
  1 MUNICIPIO_AUSENTE      nenhum arquivo do município em normas/
  2 ATO_AUSENTE            há arquivos do município, mas o nº do ato citado no Zotero não aparece em nenhum
  3 SO_FORMA_PRECARIA      o ato aparece só como .html ou só como OCR/.txt (sem PDF/DOC original)
  4 ATO_CITADO_AUSENTE     o ato principal está na pasta, mas outro ato citado no título/destaques não está
  5 SEM_NUMERO_NO_ITEM     item genérico ("Tarifa Zero de X - UF"); conferir se a instituidora está na pasta
  6 MUNICIPIO_NAO_IDENTIFICADO
  0 COBERTO                ato com nº conferido em PDF/DOC original (não é pista; vai no anexo)
Heurístico: a conferência é por nº do ato no NOME do arquivo. Leia como pista, não como prova.
"""
import argparse, csv, datetime, os, re, sqlite3, sys, unicodedata, collections

VAULT = os.path.expanduser('~/mnt/doutorado')
BAK_PADRAO = os.path.expanduser('~/mnt/Zotero/zotero.sqlite.pre-excluir-leis-tz-20261021.bak')
NORMAS_PADRAO = os.path.join(VAULT, '03 - Dados/_data/Legislacao e contratos TZ/normas')
SAIDA_PADRAO = os.path.join(VAULT, '_meta')
COLECAO_LEIS = 11            # "Leis de Tarifa Zero" (biblioteca 1)
TIPO_STATUTE = 5

# Município quando o item do Zotero não o diz (conferido à mão no título/URL em 21/10/2026).
MANUAL = {
    2689: ('Eusébio', 'CE'), 2696: ('Aquiraz', 'CE'), 2700: ('Cerquilho', 'SP'),
    2710: ('Bombinhas', 'SC'), 2722: ('Balneário Camboriú', 'SC'), 2732: ('Guapimirim', 'RJ'),
    2733: ('Ibirité', 'MG'), 2746: ('Porto Feliz', 'SP'), 2751: ('Sarzedo', 'MG'),
    100: ('Santo André', 'SP'), 2681: ('Caucaia', 'CE'), 2763: ('São João del-Rei', 'MG'), 2769: ('Vilhena', 'RO'), 2750: ('São Sebastião do Alto', 'RJ'),
}

def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    return ' ' + re.sub(r'[^a-z0-9]+', ' ', s).strip() + ' '

def campo(c, i, fid):
    r = c.execute("select v.value from itemData d join itemDataValues v using(valueID) "
                  "where d.itemID=? and d.fieldID=?", (i, fid)).fetchone()
    return r[0] if r else ''

def tipo_arquivo(fn):
    e = fn.lower().rsplit('.', 1)[-1]
    if fn.lower().endswith('ocr.txt') or fn.lower().endswith('texto.txt') or e == 'txt' or 'ocr (' in fn.lower():
        return 'txt'
    if e in ('html', 'htm'): return 'html'
    return 'original'          # pdf, doc, docx, odt, xls...

def carregar_normas(pasta):
    muns = collections.defaultdict(list)     # (nome_norm, UF) -> [(arquivo, tipo)]
    nomes = {}
    for uf in sorted(os.listdir(pasta)):
        d = os.path.join(pasta, uf)
        if not os.path.isdir(d) or uf.startswith('_'):
            continue
        for fn in os.listdir(d):
            m = re.match(r'(.+?)-([A-Z]{2}) - ', fn)
            if not m:
                continue
            k = (norm(m.group(1)), m.group(2))
            muns[k].append((fn, tipo_arquivo(fn))); nomes[k] = m.group(1)
    return muns, nomes

ATO = re.compile(r'(Lei Complementar|Lei Ordin[áa]ria|Lei Municipal|Lei Org[âa]nica|Projeto de Lei(?: CM)?|Emenda|Decreto|Lei|PLC?|LC)\s*(?:n[ºo°\.]*\s*)?'
                 r'(\d{1,3}(?:\.\d{3})+|\d{1,5})(?:\s*/\s*(\d{4}))?', re.I)

def atos(texto):
    out, vistos = [], set()
    for m in ATO.finditer(texto or ''):
        num = m.group(2).replace('.', '').lstrip('0') or '0'
        if num in ('0',) or num in FEDERAIS: continue
        ano = m.group(3) or ''
        if not ano:
            m2 = re.match(r'[^0-9]{0,25}(?:de\s+\d{1,2}\s+de\s+\w+\s+de\s+|de\s+)(\d{4})', texto[m.end():m.end() + 60])
            ano = m2.group(1) if m2 else ''
        k = (num, ano)
        if k not in vistos:
            vistos.add(k); out.append((m.group(1).strip(), num, ano))
    return out

FEDERAIS = {'12587', '8987', '8666', '13460', '10098', '13146', '14000'}   # leis federais citadas (PNMU etc.): fora do escopo de normas/ municipais

def casa(num, fn):
    """Nº do ato = ato PRINCIPAL do arquivo (1º trecho depois de 'Município-UF - '); se o nome não começar
    por tipo de ato, cai para 'número em qualquer ponto do nome'. Evita falso positivo de decreto que só cita a lei."""
    f = re.sub(r'(?<=\d)\.(?=\d)', '', fn)
    seg = f.split(' - ', 1)[1] if ' - ' in f else f
    m = re.match(r'\s*(?:Lei Complementar|Lei Ordin[áa]ria|Lei Municipal|Lei Org[âa]nica|Projeto de Lei|Emenda a Lei Organica|Emenda|Decreto|Lei|PLC?|LC|MP|Medida Provisoria)\s*(?:n[ºo°\.]*\s*)?0*(\d+)', seg, re.I)
    if m:
        return m.group(1) == num
    return re.search(r'(?<![0-9])0*' + re.escape(num) + r'(?![0-9])', f) is not None

def identificar(i, titulo, extra, url, muns, nomes):
    if i in MANUAL:
        n, uf = MANUAL[i]; return n, uf
    m = re.search(r'Place:\s*([^,\n|]+),\s*([A-Z]{2})', extra)
    if m: return m.group(1).strip(), m.group(2)
    hay = norm(titulo + ' ' + extra + ' ' + re.sub(r'[-_/\.]', ' ', url))
    hits = [k for k in muns if k[0] in hay and re.search(r'\b' + k[1] + r'\b', titulo + ' ' + extra)]
    if hits:
        k = max(hits, key=lambda x: len(x[0])); return nomes[k], k[1]
    ms = re.findall(r"((?:[A-ZÀ-Ý][\w'’À-ÿ]+)(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ý][\w'’À-ÿ]+)*)\s*(?:[-–/]|\()\s*([A-Z]{2})\b", titulo)
    if ms: return ms[-1][0], ms[-1][1]
    return None, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bak', default=BAK_PADRAO); ap.add_argument('--normas', default=NORMAS_PADRAO)
    ap.add_argument('--saida', default=SAIDA_PADRAO)
    a = ap.parse_args()
    for p in (a.bak, a.normas):
        if not os.path.exists(p): sys.exit('não encontrei: ' + p)
    muns, nomes = carregar_normas(a.normas)
    c = sqlite3.connect('file:%s?mode=ro' % a.bak, uri=True)
    ids = [r[0] for r in c.execute(
        "select i.itemID from items i join collectionItems ci using(itemID) "
        "where ci.collectionID=? and i.itemTypeID=? and i.libraryID=1 order by i.itemID", (COLECAO_LEIS, TIPO_STATUTE))]
    linhas = []
    for i in ids:
        titulo, extra, url = campo(c, i, 1), campo(c, i, 19), campo(c, i, 10)
        chave_z = c.execute("select key from items where itemID=?", (i,)).fetchone()[0]
        notas = ' / '.join(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', n[0])).replace('Destaques:', '').strip()
                           for n in c.execute("select note from itemNotes where parentItemID=?", (i,)))
        anexos = '; '.join((r[0] or '').replace('storage:', '') for r in
                           c.execute("select path from itemAttachments where parentItemID=?", (i,)))
        mun, uf = identificar(i, titulo, extra, url, muns, nomes)
        k = (norm(mun), uf) if mun else None
        arqs = muns.get(k, []) if k else []
        citados = atos(titulo) + [x for x in atos(notas) if x[1:] not in [y[1:] for y in atos(titulo)]]
        principais = atos(titulo)
        achados = {}
        for (tp, num, ano) in citados:
            achados[(tp, num, ano)] = [(fn, t) for fn, t in arqs if casa(num, fn)]
        if mun is None:
            status, pista = '6 MUNICIPIO_NAO_IDENTIFICADO', 'Ler o título/URL e identificar o município; depois buscar o ato (SAPL, leismunicipais, diário oficial).'
        elif not arqs:
            status = '1 MUNICIPIO_AUSENTE'
            pista = 'Nenhum arquivo de %s-%s em normas/. Buscar o ato %s no SAPL/Câmara, leismunicipais.com.br ou diário oficial.' % (
                mun, uf, ', '.join(('%s %s%s' % (t, n, '/' + an if an else '')) for t, n, an in principais) or '(sem nº no item)')
        elif not principais:
            status = '5 SEM_NUMERO_NO_ITEM'
            inst = [fn for fn, t in arqs if re.search(r'tarifa zero|gratuit|passe livre|institui|programa', fn, re.I)]
            pista = ('Item genérico. Arquivos do município: %d (%s). %s' % (
                len(arqs), ', '.join(sorted({t for _, t in arqs})),
                'Há arquivo com nome de instituidora/gratuidade — conferir se é a lei do programa.' if inst else
                'Nenhum nome de arquivo sugere a lei instituidora — procurar a norma que criou a TZ.'))
        else:
            princ_ok = [(p, achados[p]) for p in principais]
            if all(not v for _, v in princ_ok):
                status = '2 ATO_AUSENTE'
                pista = 'Há arquivos de %s-%s, mas nenhum com o nº %s. Buscar esse ato (pode ser outra numeração/ano ou projeto vs lei sancionada).' % (
                    mun, uf, ', '.join('%s%s' % (n, '/' + an if an else '') for _, n, an in principais))
            elif all(any(t == 'original' for _, t in v) for _, v in princ_ok if v) and any(v for _, v in princ_ok):
                faltam = [p for p in citados if p[1:] not in [q[1:] for q, v in princ_ok if v] and not achados[p]]
                if faltam:
                    status = '4 ATO_CITADO_AUSENTE'
                    pista = 'Ato principal na pasta; falta na pasta: ' + ', '.join('%s %s%s' % (t, n, '/' + an if an else '') for t, n, an in faltam)
                else:
                    status, pista = '0 COBERTO', 'Ato conferido por nº em arquivo original.'
            else:
                status = '3 SO_FORMA_PRECARIA'
                pista = 'O ato só aparece como .html/.txt-OCR em normas/; obter o PDF/DOC oficial. Arquivos: ' + '; '.join(
                    fn[:70] + ' [' + t + ']' for v in [v for _, v in princ_ok] for fn, t in v)
        linhas.append(dict(status=status, itemID=i, zotero_key=chave_z, municipio=('%s-%s' % (mun, uf)) if mun else '?',
                           titulo=titulo, data=campo(c, i, 6), url=url, atos_citados='; '.join(
                               '%s %s%s' % (t, n, '/' + an if an else '') for t, n, an in citados),
                           n_arquivos_municipio=len(arqs), destaques=notas, anexos_zotero=anexos, pista=pista))
    linhas.sort(key=lambda x: (x['status'], x['municipio']))
    hoje = datetime.date.today().isoformat()
    os.makedirs(a.saida, exist_ok=True)
    base = os.path.join(a.saida, 'Pistas de legislação (Zotero x normas) %s' % hoje)
    cols = ['status', 'itemID', 'zotero_key', 'municipio', 'titulo', 'data', 'url', 'atos_citados',
            'n_arquivos_municipio', 'destaques', 'anexos_zotero', 'pista']
    with open(base + '.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter=';'); w.writeheader(); w.writerows(linhas)
    cont = collections.Counter(l['status'] for l in linhas)
    md = ['---', 'title: "Pistas de legislação (Zotero × normas) — %s"' % hoje, 'tags: [legislacao, pistas, zotero, normas, busca]',
          'publish: false', 'created: %s' % hoje, '---', '',
          '# Pistas de legislação — o que o Zotero citava e não está (ou está precário) em `normas/`', '',
          'Gerado por `_meta/scripts/pistas_legislacao_zotero.py` (somente leitura). Fonte: backup do Zotero de 21/10/2026 '
          '(coleção "Leis de Tarifa Zero", %d leis municipais) × `03 - Dados/_data/Legislacao e contratos TZ/normas/`. '
          'A conferência é **por número do ato no nome do arquivo** — trate como pista, não como prova.' % len(linhas), '',
          '| Status | Itens |', '|---|---:|'] + ['| %s | %d |' % (s, n) for s, n in sorted(cont.items())] + ['']
    for st in sorted(cont):
        if st.startswith('0'): continue
        md += ['## ' + st, '', '| Município | Ato / título | Pista | Onde está (Zotero / URL) |', '|---|---|---|---|']
        for l in [x for x in linhas if x['status'] == st]:
            md.append('| %s | %s | %s | %s |' % (l['municipio'], (l['titulo'] or '')[:110].replace('|', '/'),
                      l['pista'].replace('|', '/'), (l['url'] or ('item ' + l['zotero_key'])).replace('|', '/')))
            if l['destaques']:
                md.append('| | *Destaques anotados:* %s | | |' % l['destaques'].replace('|', '/')[:300])
        md.append('')
    md += ['## 0 COBERTO (anexo — não é pista)', ''] + ['- %s — %s' % (l['municipio'], (l['titulo'] or '')[:100])
          for l in linhas if l['status'].startswith('0')] + ['']
    open(base + '.md', 'w', encoding='utf-8').write('\n'.join(md))
    print('itens:', len(linhas)); [print(s, n) for s, n in sorted(cont.items())]
    print('saídas:', base + '.md', '| .csv')

if __name__ == '__main__':
    main()
