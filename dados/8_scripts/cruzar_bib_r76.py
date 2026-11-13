#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cruzar_bib_r76.py  (somente leitura)

Cruza (1) as citações autor-data do texto da tese (r76, via texto extraído com pandoc), (2) as listas de
REFERÊNCIAS e FONTES do mesmo texto, (3) os itens vivos do Zotero (biblioteca 1, banco aberto read-only) e
(4) as chaves de `biblioteca.bib`. Grava `cruzamento-bib-r76.csv`. Não altera tese, Zotero nem .bib.

Uso:  python3 cruzar_bib_r76.py --txt r76.txt --db zotero.sqlite --bib biblioteca.bib --saida cruzamento-bib-r76.csv
Heurístico: leia as linhas como pistas. Citações em narrativa ("Autor (2019)") e entre parênteses
("(Autor, 2019; Outro, 2020)") são extraídas por regex; a Seção D.3 (fichas) fica de fora.
"""
import argparse, collections, csv, difflib, re, sqlite3, sys, unicodedata

CONN = {'de', 'da', 'do', 'dos', 'das', 'del', 'van', 'von', 'di', 'du', 'la', 'le'}
STOP = {'quadro','figura','tabela','seção','secao','capítulo','capitulo','apêndice','apendice','gráfico','grafico','mapa','lei',
        'decreto','resolução','resolucao','portaria','emenda','art','artigo','anexo','item','tópico','cap','p','pp','cf','ver','ex',
        'janeiro','fevereiro','março','marco','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro',
        'jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez','ano','anos','em','de','até','entre'}
YEAR = r'((?:1[5-9]|20)\d\d)([a-z]{0,2})'

def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()).strip()

def asc(s):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower())

def ler(txt):
    L = open(txt, encoding='utf-8').read().split('\n')
    def ach(nome, ini=0):
        for i in range(ini, len(L)):
            if L[i].strip() == nome: return i
        return None
    # a 1ª ocorrência é o sumário; as listas são a ÚLTIMA ocorrência do título isolado antes dos apêndices
    ref = [i for i, l in enumerate(L) if l.strip() == 'REFERÊNCIAS'][-1]
    fon = [i for i, l in enumerate(L) if l.strip() == 'FONTES'][-1]
    apA = [i for i, l in enumerate(L) if l.startswith('APÊNDICE A —')][-1]
    d3 = [i for i, l in enumerate(L) if l.strip().startswith('D.3. As fichas municipais')][-1]
    apE = [i for i, l in enumerate(L) if l.startswith('APÊNDICE E —')][-1]
    return L, ref, fon, apA, d3, apE

def entradas(L, ini, fim, sec):
    out = []
    for i in range(ini + 1, fim):
        t = L[i].strip()
        if not t: continue
        out.append(dict(sec=sec, linha=i + 1, raw=t))
    return out

def prep_entry(e):
    t = re.sub(r'(Acesso em|Disponível em|Divulgado em)\s*:.*$', '', e['raw']).strip()
    anos = list(re.finditer(YEAR + r'(?![0-9])', t))
    e['ano'], e['suf'] = ('', '')
    if anos:
        m = anos[-1]; e['ano'], e['suf'] = m.group(1), m.group(2)
    head = e['raw'][:220]
    e['sobrenomes'] = {norm(w) for w in re.findall(r"\b[A-ZÀ-Ý][A-ZÀ-Ý'’\-]{1,}\b", head) if norm(w) not in CONN}
    e['url'] = (re.search(r'https?://\S+', e['raw']) or [None])[0] if re.search(r'https?://\S+', e['raw']) else ''
    e['doi'] = (re.search(r'10\.\d{4,9}/[^\s\]]+', e['raw']) or [None])[0] if re.search(r'10\.\d{4,9}/[^\s\]]+', e['raw']) else ''
    e['tokens'] = {w for w in norm(e['raw']).split() if len(w) > 3}
    return e

def secao_em(L, n):
    h = ''
    for i in range(n, -1, -1):
        t = L[i].strip()
        if 0 < len(t) < 130 and re.match(r'^(Capítulo \d+|CAPÍTULO|APÊNDICE [A-G]|INTRODUÇÃO|CONSIDERAÇÕES|\d+(\.\d+)* [A-ZÀ-Ý]|[A-G]\.\d+(\.\d+)* [A-ZÀ-Ý])', t):
            return t[:70]
    return ''

def autor_chaves(auth):
    """candidatos de chave a partir do trecho de autor da citação"""
    a = re.split(r'\s+(?:e|&)\s+|\s+et al\.?|;', auth.strip())[0].strip()
    toks = [w for w in re.findall(r"[A-Za-zÀ-ÿ'’\-]+", a)]
    if not toks: return [], ''
    cand = [asc(''.join(toks))]
    cand.append(asc(toks[0]))
    if len(toks) > 1: cand.append(asc(toks[-1]))
    return list(dict.fromkeys(c for c in cand if c)), a

def extrair_citacoes(L, faixas):
    cits = []
    pnar = re.compile(r"\b([A-ZÀ-Ý][\wÀ-ÿ'’\-]+(?:\s+(?:" + '|'.join(CONN) + r")\s+[A-ZÀ-Ý][\wÀ-ÿ'’\-]+|\s+e\s+[A-ZÀ-Ý][\wÀ-ÿ'’\-]+)*(?:\s+et al\.)?)\s*\(" + YEAR)
    ppar = re.compile(r'\(([^()]{0,360}?\b' + YEAR + r'[^()]{0,200}?)\)')
    for (a, b) in faixas:
        for i in range(a, b):
            t = L[i]
            if not t.strip(): continue
            for m in pnar.finditer(t):
                nm, ano, suf = m.group(1), m.group(2), m.group(3)
                if norm(nm.split()[0]) in STOP: continue
                cits.append((i + 1, nm, ano, suf, 'narrativa'))
            for m in ppar.finditer(t):
                partes = m.group(1).split(';'); buf = []
                for p in partes:
                    buf.append(p)
                    my = re.search(YEAR + r'(?![0-9])', p)
                    if not my: continue
                    txt = ';'.join(buf); buf = []
                    ya = re.search(YEAR + r'(?![0-9])', txt)
                    aut = re.sub(r'^\s*(apud|cf\.?|ver|v\.|e\.g\.,?|por exemplo,?|ex\.:?)\s+', '', txt[:ya.start()].strip(' ,;'), flags=re.I)
                    aut = re.sub(r'\bapud\b.*$', '', aut).strip(' ,;')
                    if not aut or not re.match(r'^[A-ZÀ-Ý]', aut) or len(aut) > 90: continue
                    if norm(aut.split()[0]) in STOP: continue
                    cits.append((i + 1, aut, ya.group(1), ya.group(2), 'parentese'))
    return cits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--txt', required=True); ap.add_argument('--db', required=True)
    ap.add_argument('--bib', required=True); ap.add_argument('--saida', required=True)
    a = ap.parse_args()
    L, ref, fon, apA, d3, apE = ler(a.txt)
    ents = [prep_entry(e) for e in entradas(L, ref, fon, 'REFERÊNCIAS') + entradas(L, fon, apA, 'FONTES')]
    faixas = [(0, ref), (apA, d3), (apE, len(L))]
    cits = extrair_citacoes(L, faixas)
    # Zotero vivo (read-only) + bib
    c = sqlite3.connect('file:%s?mode=ro' % a.db, uri=True)
    def campos(fid):
        return {r[0]: r[1] for r in c.execute("select d.itemID,v.value from itemData d join itemDataValues v using(valueID) where d.fieldID=?", (fid,))}
    chv, tit, url, doi, dat = campos(9), campos(1), campos(10), campos(8), campos(6)
    for i, ex in campos(19).items():          # a chave também vive na 1ª linha do Extra (Better BibTeX lê dali)
        m = re.match(r'\s*Citation Key:\s*(\S+)', ex or '')
        if m and (i not in chv or not chv[i]): chv[i] = m.group(1)
    itens = [r[0] for r in c.execute("select itemID from items where libraryID=1 and itemTypeID not in (3,1) and itemID not in (select itemID from deletedItems)")]
    zkeys = collections.defaultdict(list)
    for i in itens:
        if i in chv: zkeys[chv[i].lower()].append(i)
    bibtxt = open(a.bib, encoding='utf-8', errors='ignore').read()
    bkeys = {k.lower() for k in re.findall(r'^@\w+\{([^,\s]+),', bibtxt, re.M)}
    ttok = {i: {w for w in norm(tit.get(i, '')).split() if len(w) > 3} for i in itens}
    def nurl(u): return re.sub(r'^https?://(www\.)?', '', re.sub(r'[?#].*$', '', (u or '').strip().lower())).rstrip('/')
    uidx = {nurl(url[i]): i for i in itens if url.get(i)}
    didx = {doi[i].lower().strip(): i for i in itens if doi.get(i)}
    # lista -> item Zotero
    for e in ents:
        it = None; how = ''
        if e['url'] and nurl(e['url'].rstrip('.,);')) in uidx: it, how = uidx[nurl(e['url'].rstrip('.,);'))], 'url'
        elif e['doi'] and e['doi'].lower().rstrip('.,);') in didx: it, how = didx[e['doi'].lower().rstrip('.,);')], 'doi'
        else:
            best, bs = None, 0
            for i in itens:
                tk = ttok[i]
                if len(tk) < 3: continue
                s = len(tk & e['tokens']) / len(tk)
                if s > bs and s >= 0.85:
                    yy = (dat.get(i) or '')[:4]
                    if e['ano'] and yy and yy != e['ano'] and (chv.get(i, '').lower().find(e['ano']) < 0): continue
                    best, bs = i, s
            if best: it, how = best, 'titulo(%.2f)' % bs
        e['item'], e['how'] = it, how
        e['chave'] = chv.get(it, '') if it else ''
    # citações -> chave / lista / zotero / bib
    agg = collections.OrderedDict()
    for (ln, nm, ano, suf, tipo) in cits:
        cand, a1 = autor_chaves(nm)
        if not cand: continue
        k = (cand[0], ano + suf)
        g = agg.setdefault(k, dict(autor=a1, cand=cand, ano=ano + suf, locs=[], n=0))
        g['n'] += 1
        if len(g['locs']) < 3: g['locs'].append('l.%d %s' % (ln, secao_em(L, ln - 1)))
    rows = []
    for (ck, ya), g in agg.items():
        ano, suf = ya[:4], ya[4:]
        # na lista?
        toks = {norm(w) for w in re.findall(r"[A-Za-zÀ-ÿ'’\-]+", g['autor']) if norm(w) not in CONN}
        hits = [e for e in ents if e['ano'] == ano and e['suf'] == suf and toks & e['sobrenomes']]
        hits_sem_suf = [e for e in ents if e['ano'] == ano and toks & e['sobrenomes']]
        hits_outro_ano = [e for e in ents if e['ano'] != ano and toks & e['sobrenomes']]
        key_z = next((cc + ya for cc in g['cand'] if (cc + ya).lower() in zkeys), '')
        key_b = next((cc + ya for cc in g['cand'] if (cc + ya).lower() in bkeys), '')
        div, acao = '', ''
        # Se a citação está na lista, o vínculo com o Zotero vale pelo ITEM da lista (URL/DOI/título), não pela chave
        # derivada: o sufixo de letra do texto/lista NÃO coincide, em geral, com o sufixo da chave do Zotero.
        if hits:
            it = next((e['item'] for e in hits if e['item']), None)
            if it:
                kz = chv.get(it, '')
                key_z = kz; key_b = kz if kz.lower() in bkeys else ''
                if kz and kz.lower() != (g['cand'][0] + ya).lower() and not any(kz.lower() == (cc + ya).lower() for cc in g['cand']):
                    div = 'chave do Zotero (%s) difere de autor+ano+sufixo do texto (%s)' % (kz, g['cand'][0] + ya)
            else:
                key_z = key_b = ''
        chave = key_z or key_b or (g['cand'][0] + ya)
        if hits:
            na_lista = 'sim (%s)' % ', '.join('l.%d' % e['linha'] for e in hits[:2])
        elif hits_sem_suf:
            na_lista = 'parcial (sufixo)'; div = (div + '; ' if div else '') + 'lista tem o autor e o ano, mas com outro sufixo: ' + '; '.join(e['ano'] + e['suf'] for e in hits_sem_suf[:4])
        elif hits_outro_ano:
            na_lista = 'não'; div = 'lista tem o autor com outro ano: ' + '; '.join(sorted({e['ano'] + e['suf'] for e in hits_outro_ano})[:5])
        else:
            na_lista = 'não'
        if na_lista.startswith('sim') and key_z: acao = ''
        elif na_lista == 'não' and key_z: acao = 'Incluir na lista (item já existe no Zotero) ou trocar a citação'
        elif na_lista == 'não': acao = 'Decidir: incluir referência completa (buscar fonte) ou trocar a citação'
        elif na_lista.startswith('parcial'): acao = 'Conferir sufixo/ano entre texto e lista'
        elif not key_z: acao = 'Criar item no Zotero (está na lista)'
        if key_z and not key_b and not acao: acao = 'Aguardar export do Better BibTeX (item no Zotero, fora do .bib defasado)'
        rows.append(dict(tipo='CITAÇÃO', chave=chave, autor_ano='%s (%s)' % (g['autor'], ya), onde='; '.join(g['locs']) + (' [+%d]' % (g['n'] - 3) if g['n'] > 3 else ''),
                         na_lista=na_lista, no_bib='sim' if key_b else 'não', no_zotero='sim' if key_z else 'não', divergencia=div, acao=acao))
    for e in ents:
        it = e['item']; ch = e['chave']
        in_bib = 'sim' if ch and ch.lower() in bkeys else 'não'
        div, acao = '', ''
        if not it:
            acao = 'Criar item no Zotero (sem correspondência por URL, DOI ou título)'
        else:
            yy = (dat.get(it) or '')[:4]
            if e['ano'] and yy and yy != e['ano']: div += 'ano da lista %s × data do Zotero %s; ' % (e['ano'], yy)
            m = re.search(YEAR + r'$', ch or '')
            if ch and e['suf'] and not ch.lower().endswith(e['ano'] + e['suf']): div += 'sufixo da lista (%s%s) × chave %s; ' % (e['ano'], e['suf'], ch)
            if not e['suf'] and ch and re.search(r'\d{4}[a-z]{1,2}$', ch): div += 'lista sem sufixo × chave %s; ' % ch
            if in_bib == 'não': acao = 'Aguardar export do Better BibTeX (item no Zotero, fora do .bib defasado)'
            if div: acao = 'Conferir divergência; ' + acao
        rows.append(dict(tipo='LISTA-' + e['sec'], chave=ch, autor_ano=e['raw'][:110], onde='lista, l.%d' % e['linha'], na_lista='sim',
                         no_bib=in_bib, no_zotero='sim' if it else 'não', divergencia=(div + ('[casou por ' + e['how'] + ']' if it else '')).strip(), acao=acao.strip()))
    # ---- pós-processamento (r76, 21/10/2026): separar ruído de extração, marcar escopo e montar o mapa de sufixos ----
    sobren = set()
    for (ln_,) in c.execute("select distinct cr.lastName from creators cr join itemCreators ic using(creatorID) join items i using(itemID) where i.libraryID=1 and cr.lastName is not null"):
        for w in re.findall(r"[A-Za-zÀ-ÿ'’\-]+", ln_):
            if norm(w) not in CONN: sobren.add(norm(w))
    PROMPT = {norm(x) for x in ['Hirata','Rett','Cheibub','Marinho','Botelho','Menezes','Silva','Cadaval','Campos','Santini','Néspoli','Correia','Andrade',
              'Barbosa','Brasileiro','Biondi','Filho','Muñoz','Susilo','Ulian','Marshall','Leme','Paixão','Maggio de Moraes','Ramos','Vargas de Faria',
              'Queiroz da Silva','Lopes','Ribeiro','Sampaio','Santarém','Pereira','Zioni','Vermander','Banister','Hymel','Huré','Passalacqua','Poinsot',
              'Gregori','Stiel','Graehler','Bicalho','Mucci','Erhardt']}
    def ruido(r):
        if r['tipo'] != 'CITAÇÃO' or r['na_lista'].startswith('sim') or r['no_zotero'] == 'sim': return ''
        au = r['autor_ano'].rsplit(' (', 1)[0]
        if re.search(r'\d|R\$|/|\bLei\b|\bLC\b|\bPEC\b|\bEC\b|Contrato|Preg|Mensagem|Parte [A-G]|Operador|Linhas|Dec\.', au): return 'número, valor ou ato normativo'
        toks = [norm(w) for w in re.findall(r"[A-Za-zÀ-ÿ'’\-]+", au) if norm(w) not in CONN]
        if any(t in PROMPT for t in toks): return ''
        if any(t in sobren for t in toks): return ''
        if r['divergencia'].startswith('lista tem o autor com outro ano'): return ''
        return 'autor ausente da lista e dos criadores do Zotero (provável sigla, topônimo, linha de ônibus ou termo comum)'
    descart = [(r, ruido(r)) for r in rows]
    desc_rows = [(r, m) for r, m in descart if m]
    rows = [r for r, m in descart if not m]
    for r in rows:
        if r['tipo'] == 'CITAÇÃO' and r['na_lista'] == 'não' and r['no_zotero'] == 'não':
            au = r['autor_ano'].rsplit(' (', 1)[0]
            toks = [norm(w) for w in re.findall(r"[A-Za-zÀ-ÿ'’\-]+", au) if norm(w) not in CONN]
            if any(t in PROMPT for t in toks): r['acao'] = 'Item do prompt r76: sem entrada na lista; decidir incluir referência (buscar fonte) ou trocar a citação (lista para o Word rN)'
        if r['tipo'].startswith('LISTA') and r['no_zotero'] == 'não':
            r['acao'] = 'Fora do escopo desta rodada (decisão de 21/10/2026: só os itens do prompt); manter na fila para criar no Zotero'
    mapa = []
    for e in ents:
        ch = e.get('chave') or ''
        if e.get('item') and ch and e['ano'] and e['suf'] != (re.search(r'\d{4}([a-z]{0,2})$', ch) or [0, ''])[1]:
            mapa.append(dict(tipo='MAPA-SUFIXO', chave=ch, autor_ano=e['raw'][:90], onde='lista, l.%d' % e['linha'], na_lista='sim',
                             no_bib='sim' if ch.lower() in bkeys else 'não', no_zotero='sim',
                             divergencia='tese %s%s -> Zotero %s' % (e['ano'], e['suf'], ch), acao='Word: manter o sufixo da tese; Zotero: manter a chave (mapear por título/URL)'))
    rows = rows + mapa
    with open(a.saida.replace('.csv', '_descartados.csv'), 'w', newline='', encoding='utf-8-sig') as fh2:
        w2 = csv.writer(fh2, delimiter=';')
        w2.writerow(['autor-ano (extraído)', 'onde no texto', 'motivo do descarte'])
        for r, m in desc_rows: w2.writerow([r['autor_ano'], r['onde'], m])
    print('descartados como ruído:', len(desc_rows), '| linhas de mapa de sufixo:', len(mapa))
    with open(a.saida, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(['tipo', 'chave', 'autor-ano', 'onde no texto', 'na lista?', 'no bib?', 'no Zotero?', 'divergência', 'ação proposta'])
        for r in rows: w.writerow([r['tipo'], r['chave'], r['autor_ano'], r['onde'], r['na_lista'], r['no_bib'], r['no_zotero'], r['divergencia'], r['acao']])
    cnt = collections.Counter((r['tipo'], r['na_lista'].split(' ')[0], r['no_zotero'], r['no_bib']) for r in rows)
    print('entradas:', len(ents), '| citações distintas:', len(agg), '| chaves no bib:', len(bkeys), '| chaves no Zotero:', len(zkeys))
    for k, v in sorted(cnt.items()): print(k, v)

if __name__ == '__main__':
    main()
