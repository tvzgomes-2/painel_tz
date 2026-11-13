#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sapl_varredura.py — varre as APIs SAPL das câmaras municipais brasileiras
procurando normas por TERMO EXATO.

Termos padrão: "plano de mobilidade", "tarifa zero", "passe livre",
"fundo municipal de transporte", "fundo de transporte",
"fundo municipal de mobilidade", "fundo de mobilidade".

POR QUE ISSO FUNCIONA
  O SAPL (sistema de legislação do Interlegis, usado por milhares de câmaras)
  expõe uma API pública que devolve, em uma chamada: tipo, número, ano, data,
  ementa e o LINK DO PDF do texto integral. Descoberto em 09/09/2026:
      https://sapl.<municipio>.<uf>.leg.br/api/norma/normajuridica/?numero=N&ano=A
  Confirmado em Irati/PR (Lei 4.241/2016, PlanMob) e Monte Mor/SP (Lei 3.254/2024).

O QUE ESPERAR — não é uniforme, e isso está medido
  De 33 municípios testados manualmente, 19 tinham host .leg.br que resolve;
  das chamadas à API, algumas devolveram a norma, outras vieram vazias e uma
  deu erro 400 (versões diferentes de SAPL). E DECRETOS DO EXECUTIVO NÃO ESTÃO
  no SAPL da câmara — é registro do Legislativo. Um PlanMob aprovado por decreto
  (Palmas/TO, Garopaba/SC) não será encontrado aqui.

GARANTIA DO "TERMO TODO"
  A busca do servidor é apenas um filtro grosso: alguns SAPL fazem AND de
  palavras, outros ignoram o parâmetro. Por isso o script SEMPRE refiltra no
  cliente exigindo a FRASE CONTÍGUA (sem acento, minúscula, pontuação
  normalizada). "passe livre" nunca casa com "passe" + "livre" soltos.

USO — colheita ampla (recomendado)
  python3 sapl_varredura.py descobrir --municipios lista.csv --prioridade tz.csv
  python3 sapl_varredura.py corpus    --prioridade tz.csv    # baixa TODAS as normas
  python3 sapl_varredura.py filtrar                          # aplica os termos, offline

USO — busca dirigida (mais rápida, menos exaustiva)
  python3 sapl_varredura.py municipios                       # baixa a lista do IBGE
  python3 sapl_varredura.py descobrir --uf SP --workers 16    # acha os hosts vivos
  python3 sapl_varredura.py buscar    --uf SP                 # consulta os termos no servidor
  python3 sapl_varredura.py autoteste                         # testa a lógica offline

  Retoma sozinho: rodar de novo pula o que já está no CSV de saída. Em "corpus",
  só pula host CONCLUÍDO — host interrompido no meio é refeito do zero, para o
  corpus nunca ficar pela metade e se dizer completo.

CORPUS × BUSCAR — a diferença importa
  "buscar" manda UMA alternativa de cada grupo ao servidor como filtro grosso;
  as demais só entram no refiltro do que voltou. Se o SAPL fizer substring em
  vez de AND de palavras, "plano municipal de mobilidade urbana" não volta na
  consulta "plano de mobilidade" — e some. "corpus" baixa a base inteira uma
  vez; daí em diante qualquer termo novo se aplica offline, sem tocar as
  câmaras de novo. É mais lento na primeira passada e exaustivo depois.

--prioridade lista.csv
  CSV com coluna cod_ibge. Esses municípios vão para o INÍCIO da fila, em
  "descobrir" e em "corpus" — para colher primeiro os casos de Tarifa Zero e
  ter resultado útil antes de a varredura nacional terminar.

COMPLETUDE DA COLHEITA — quatro estados (v1.1, 10-09-2026)
  A coluna "completo" do CSV de hosts diz o que aconteceu, e a diferença é
  metodológica: um corpus que se declara completo estando pela metade é o pior
  defeito possível, porque a falta não parece falta — parece o total.
    sim       colheu o que a descoberta declarava.
    esgotado  paginamos ATÉ O FIM (página que não trouxe registro novo) e ainda
              ficou abaixo do total declarado. A diferença é DO SERVIDOR: o
              "total_entries" pode contar norma que a API não serve (não
              publicada, restrita). Estado TERMINAL — não é refeito.
    parcial   ficou abaixo por motivo que pode ser NOSSO (bateu no
              --max-paginas). Refeito na próxima rodada.
    nao       erro de rede ou resposta inválida. Refeito na próxima rodada.

  🔴 O DEFEITO CORRIGIDO NA v1.1. A paginação parava quando a resposta não
  trazia o link "next" — e existe SAPL que devolve "next" nulo em TODA página.
  Nesses hosts a colheita terminava na página 1 e se dizia completa. Medido em
  Paraguaçu Paulista/SP: 50 de 5.287 normas na paginação normal e exatamente 10
  por ano no fatiamento (uma página por consulta — a assinatura do corte).
  A parada agora é empírica: avança enquanto a página TRAZ REGISTRO NOVO.
  Afetados na varredura nacional de 10/09/2026: Paraguaçu Paulista/SP,
  Canoinhas/SC, Rio Bonito do Iguaçu/PR e Ibirajuba/PE.

  🔴 E O 404 NÃO É FALHA. O Django REST Framework responde 404 ("Invalid page")
  à página ALÉM da última. Depois da página 1 e com registro na mão, isso é o
  FIM DA COLEÇÃO — tratá-lo como erro deixava o host em "nao" e o refazia a cada
  rodada sem nunca convergir. Medido em Rio Bonito do Iguaçu/PR (902 de 1.249) e
  Ibirajuba/PE (170 de 226): os dois terminam agora em "esgotado", que é o
  diagnóstico correto. 404 na PÁGINA 1 continua sendo erro (endpoint errado).
  Testes de integração (servidor falso, sem rede): _meta/scripts/teste_sapl_colheita.py

  DEDUPLICAÇÃO. O corpus é apendado: host refeito numa rodada posterior grava as
  normas de novo. A fase "filtrar" descarta linha repetida por (host, tipo, número,
  ano) e informa quantas descartou. --sem-dedup desliga (só para auditar).

ETIQUETA
  --delay (padrão 1,0 s por host) e User-Agent identificando a pesquisa.
  São endpoints públicos de câmaras municipais; não abuse. --contato SEU@EMAIL
  é boa prática.

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof. Dra. Silvana Zioni
"""
import os, re, csv, sys, json, time, socket, argparse, functools, unicodedata, urllib.parse
import urllib.request, urllib.error
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Console do Windows (cmd.exe / Anaconda Prompt) costuma vir em cp1252 e
# estoura UnicodeEncodeError ao imprimir "✓" ou nomes acentuados. Isto evita
# a classe inteira do problema, sem depender de 'chcp 65001'.
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

VERSAO = '1.1 (10-09-2026)'
UF_ALL = 'AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO'.split()

# Grupos de termos: "rótulo = frase | frase | ...".
# CADA alternativa é uma FRASE CONTÍGUA — o "termo todo" continua garantido.
# Os grupos existem porque a mesma coisa aparece com redações diferentes:
# "Plano Municipal de Mobilidade Urbana" NÃO contém a frase "plano de mobilidade"
# (a palavra "Municipal" fica no meio). Foi um defeito pego pelo autoteste em
# 09/09/2026: a lista antiga perdia justamente Monte Mor/SP, cuja ementa é
# "Institui o Plano Municipal de Mobilidade Urbana de Monte Mor".
TERMOS_PADRAO = [
    # --- o núcleo da tese ---
    'tarifa zero = tarifa zero | tarifa social zero | gratuidade tarifaria universal',
    'passe livre = passe livre',
    # 🔴 'isencao tarifaria' e 'isencao de tarifa' SAIRAM deste grupo em 10/09/2026:
    # na varredura de SC/MG casaram "isenção de tarifa de ÁGUA E ESGOTO" (Lagoa da
    # Prata 1942/2011) e "isenção de tarifa de MATANÇA DE GADO" (Piumhi 921/1986).
    # Tarifa nao e so de transporte. Foram para o grupo amplo, e as variantes com
    # o objeto explicito ficaram aqui.
    'gratuidade = transporte gratuito | transporte coletivo gratuito | '
    'transporte publico gratuito | transporte comunitario gratuito | '
    'transporte municipal gratuito | transporte urbano gratuito | '
    'gratuidade no transporte | gratuidade do* transporte | gratuidade universal | '
    'passagem gratuita | vedada a cobranca de tarifa | sem cobranca de tarifa | '
    'sem custo para o usuario | isencao de tarifa de transporte | '
    'isencao de* tarifa do* transporte | isento do pagamento de tarifa',
    # Grupo DELIBERADAMENTE AMPLO, para recall. Numa base de legislacao municipal
    # inteira "gratuito" tambem pega merenda, remedio e cemiterio — por isso vem
    # em grupo separado, identificado na coluna 'termo', e nao contamina os outros.
    'gratuito (amplo, revisar) = gratuito | gratuita | gratuidade | '
    'isencao tarifaria | isencao de* tarifa',
    # --- planos ---
    'planmob = plano de mobilidade | plano municipal de mobilidade | '
    'plano de mobilidade urbana | plano municipal de mobilidade urbana | '
    'plano diretor de mobilidade | plano de mobilidade urbana sustentavel',
    # --- fundos ---
    'fundo de transporte = fundo municipal de* transporte | fundo de* transporte',
    'fundo de mobilidade = fundo municipal de* mobilidade | fundo de* mobilidade',
    # --- o serviço, a concessão e a remuneração (legislação de ônibus) ---
    'transporte coletivo = transporte coletivo | transporte publico coletivo | '
    'servico de transporte coletivo | sistema de transporte coletivo',
    'onibus = onibus | transporte por onibus | linha de onibus | ponto de onibus | '
    'terminal rodoviario | terminal de onibus',
    'concessao = concessao do* servico de transporte | permissao do* servico de transporte | '
    'concessao do* transporte coletivo | permissao do* transporte coletivo | '
    'contrato de concessao de transporte',
    'tarifa = tarifa de onibus | tarifa do transporte coletivo | politica tarifaria | '
    'reajuste tarifario | revisao tarifaria | estrutura tarifaria',
    'subsidio = subsidio ao transporte | subvencao ao transporte | '
    'subsidio tarifario | subvencao tarifaria | equilibrio economico financeiro',
    'bilhetagem = bilhetagem eletronica | bilhete unico | cartao de transporte',
    'mobilidade urbana = mobilidade urbana | politica municipal de mobilidade',
]

def parse_grupo(t):
    """'rotulo = a | b' -> ('rotulo', ['a','b']). Sem '=', o rotulo e a propria frase."""
    if '=' in t:
        rot, alts = t.split('=', 1)
        return rot.strip(), [x.strip() for x in alts.split('|') if x.strip()]
    return t.strip(), [t.strip()]

# ---------------------------------------------------------------- normalização
def nfd(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    return ''.join(c for c in s if not unicodedata.combining(c))

def norm(s):
    """minúscula, sem acento, pontuação -> espaço, espaços colapsados."""
    s = nfd(s).lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

PREP_FLEX = ['de', 'do', 'da', 'dos', 'das']

@functools.lru_cache(maxsize=4096)
def _padrao(frase):
    """Compila UMA vez o regex da frase. Sem este cache, filtrar 1,7 milhao de
    normas por 13 grupos recompilava o mesmo padrao milhoes de vezes — medido
    em 10/09/2026: a fase 'filtrar' nao terminava em 2 minutos sobre 106 mil
    normas, e passou a levar segundos."""
    partes = norm(frase.replace('*', ' ASTERISCO ')).split()
    if not partes:
        return None
    peca = []
    i = 0
    while i < len(partes):
        w = partes[i]
        if i + 1 < len(partes) and partes[i + 1] == 'asterisco':
            if w in PREP_FLEX:
                peca.append('(?:' + '|'.join(PREP_FLEX) + ')')
            else:
                peca.append(re.escape(w))
            i += 2
            continue
        peca.append(re.escape(w))
        i += 1
    return re.compile(r'(?:^|\s)' + r'\s+'.join(peca) + r'(?:\s|$)')

def contem_frase_norm(t, frase):
    """Como contem_frase, mas recebe o texto JA normalizado — para quem filtra
    muitas frases contra o mesmo texto e nao quer normalizar 60 vezes."""
    if not t:
        return False
    pat = _padrao(frase)
    return pat is not None and pat.search(t) is not None

def contem_frase(texto, frase):
    """Frase CONTÍGUA, com fronteira de palavra. É a garantia do 'termo todo'.

    Única flexibilidade, e ela é explícita: escrever a preposição com '*'
    ('de*') aceita de|do|da|dos|das naquela posição — e só ali. Serve para o
    português real: o fundo de Irati chama-se "FUNDO MUNICIPAL DO TRANSPORTE
    PÚBLICO (FUMTRAP)", com 'do', e seria perdido por 'fundo municipal de
    transporte'. Nada mais é flexível: nenhuma palavra é opcional, nenhuma
    ordem é trocada, nada casa por radical.
    """
    return contem_frase_norm(norm(texto), frase)

# ------------------------------------------------------------------ hosts SAPL
PREP = {'de', 'do', 'da', 'dos', 'das', 'd'}

def slugs(municipio):
    """variantes de slug observadas no Interlegis."""
    base = norm(municipio)
    if not base:
        return []
    p = base.split()
    v = []
    v.append(''.join(p))                                   # riobrancodosul
    v.append('-'.join(p))                                  # rio-branco-do-sul
    sem = [x for x in p if x not in PREP]
    if sem != p:
        v.append(''.join(sem))                             # riobrancosul
        v.append('-'.join(sem))
    # NÃO gerar "só a 1ª palavra": em 09/09/2026 essa variante produziu
    # 'vargem.sp.leg.br' para VARGEM GRANDE PAULISTA — e Vargem/SP é outro
    # município, também presente na base de Tarifa Zero. Um falso positivo
    # desses atribui as leis de uma cidade a outra, silenciosamente.
    out = []
    for x in v:
        if x and x not in out:
            out.append(x)
    return out

def hosts_candidatos(municipio, uf, slugs_proibidos=None):
    """slugs_proibidos: slugs que pertencem a OUTRO município da mesma UF.

    Guarda de colisão de nome. Sem ela, 'Vargem Grande Paulista' pode gerar
    'vargem' e capturar as leis de Vargem/SP. A mesma família de armadilha de
    Palmas/TO x Palmas/PR e Pirapora/MG x Pirapora do Bom Jesus/SP.
    """
    uf = uf.lower()
    proib = set(slugs_proibidos or ())
    h = []
    for s in slugs(municipio):
        if s in proib:
            continue
        for pref in ('sapl.', ''):
            for corpo in (s, 'camara' + s, 'cm' + s):
                cand = '%s%s.%s.leg.br' % (pref, corpo, uf)
                if cand not in h:
                    h.append(cand)
    return h

def dns_ok(host, timeout=3.0):
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        socket.getaddrinfo(host, 443)
        return True
    except Exception:
        return False
    finally:
        socket.setdefaulttimeout(old)

# --------------------------------------------------------------------- HTTP
class Http:
    def __init__(self, ua, delay=1.0, timeout=20, tentativas=2):
        self.ua, self.delay, self.timeout, self.tentativas = ua, delay, timeout, tentativas
        self._ultimo = {}

    def get_json(self, url):
        host = urllib.parse.urlparse(url).netloc
        t = self._ultimo.get(host)
        if t is not None:
            espera = self.delay - (time.time() - t)
            if espera > 0:
                time.sleep(espera)
        err = None
        for i in range(self.tentativas + 1):
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': self.ua,
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Encoding': 'gzip, deflate'})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    dados = r.read()
                    enc = (r.headers.get('Content-Encoding') or '').lower()
                if 'gzip' in enc:
                    import gzip as _gz
                    dados = _gz.decompress(dados)
                elif 'deflate' in enc:
                    import zlib as _zl
                    try:
                        dados = _zl.decompress(dados)
                    except Exception:
                        dados = _zl.decompress(dados, -_zl.MAX_WBITS)
                self._ultimo[host] = time.time()
                txt = dados.decode('utf-8', 'replace').lstrip('\ufeff').strip()
                try:
                    return json.loads(txt), None
                except Exception:
                    # mostra o que veio: sem isso, "nao e JSON" nao diz nada
                    amostra = re.sub(r'\s+', ' ', txt[:300])
                    return None, 'resposta nao e JSON (%d bytes) | inicio: %s' % (len(dados), amostra)
            except urllib.error.HTTPError as e:
                err = 'HTTP %s' % e.code
                if e.code in (400, 401, 403, 404, 405):
                    break
            except Exception as e:
                err = type(e).__name__
            time.sleep(1.5 * (i + 1))
        self._ultimo[host] = time.time()
        return None, err

# ------------------------------------------------------------------- endpoints
ENDPOINTS = [
    ('norma',   '/api/norma/normajuridica/'),
    ('materia', '/api/materia/materialegislativa/'),
]
PARAMS_BUSCA = ['ementa', 'search', 'q']

def eh_resposta_sapl(j):
    if not isinstance(j, dict):
        return False
    return ('results' in j) or ('pagination' in j) or ('count' in j)

def resultados(j):
    if isinstance(j, dict):
        for k in ('results', 'objects', 'data'):
            if isinstance(j.get(k), list):
                return j[k]
    return []

def campo(d, *nomes):
    for n in nomes:
        if n in d and d[n] not in (None, ''):
            return d[n]
    return ''

def texto_busca(item):
    """junta os campos textuais onde o termo pode aparecer."""
    partes = []
    for k in ('ementa', 'observacao', 'indexacao', 'assuntos', 'titulo',
              'descricao', 'texto_articulado'):
        v = item.get(k)
        if isinstance(v, str):
            partes.append(v)
        elif isinstance(v, list):
            partes.append(' '.join(str(x) for x in v))
    return ' '.join(partes)

def link_pdf(item, host):
    for k in ('texto_integral', 'arquivo', 'texto_original', 'anexo'):
        v = item.get(k)
        if isinstance(v, str) and v:
            if v.startswith('http'):
                return v
            return 'https://%s%s' % (host, v if v.startswith('/') else '/' + v)
    return ''

# -------------------------------------------------------------------- IBGE
IBGE_UF = 'https://servicodados.ibge.gov.br/api/v1/localidades/estados/%s/municipios'
IBGE_TUDO = 'https://servicodados.ibge.gov.br/api/v1/localidades/municipios'

def _extrai_uf(m):
    try:
        return m['microrregiao']['mesorregiao']['UF']['sigla']
    except Exception:
        pass
    try:
        return m['regiao-imediata']['regiao-intermediaria']['UF']['sigla']
    except Exception:
        return ''

def baixar_municipios(http, saida):
    """Baixa por UF: 27 respostas pequenas em vez de uma de vários MB.
    Uma resposta gigante é justamente o que costuma falhar atrás de proxy."""
    bruto, faltou = [], []
    for uf in UF_ALL:
        j, err = http.get_json(IBGE_UF % uf)
        if isinstance(j, list) and j:
            for m in j:
                m.setdefault('_uf', uf)
            bruto.extend(j)
            print('  %s: %d municípios' % (uf, len(j)))
        else:
            faltou.append(uf)
            print('  %s: FALHOU (%s)' % (uf, err))
    if faltou:
        print('\nTentando o endpoint único para as UFs que faltaram: %s' % ','.join(faltou))
        j, err = http.get_json(IBGE_TUDO)
        if isinstance(j, list):
            for m in j:
                if _extrai_uf(m) in faltou:
                    bruto.append(m)
        else:
            print('  endpoint único também falhou: %s' % err)
    if not bruto:
        sys.exit('ERRO: não consegui a lista do IBGE.\n'
                 'Contorno: passe --municipios com um CSV de colunas '
                 'cod_ibge,municipio,uf (a lista de municípios do IBGE em CSV '
                 'serve; ou exporte do seu base_municipal_v3).')
    linhas = []
    for m in bruto:
        uf = m.get('_uf') or _extrai_uf(m)
        linhas.append({'cod_ibge': m['id'], 'municipio': m['nome'], 'uf': uf})
    vistos = set(); unicos = []
    for r in linhas:
        if r['cod_ibge'] in vistos:
            continue
        vistos.add(r['cod_ibge']); unicos.append(r)
    linhas = unicos
    linhas.sort(key=lambda r: (r['uf'], norm(r['municipio'])))
    with open(saida, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['cod_ibge', 'municipio', 'uf'])
        w.writeheader(); w.writerows(linhas)
    print('\nmunicípios gravados: %d -> %s' % (len(linhas), saida))
    if len(linhas) < 5500:
        print('⚠️  esperados ~5.570. Faltaram UFs — rode de novo (ele regrava) '
              'ou use --municipios com um CSV próprio.')
    return linhas

def ler_municipios(caminho):
    if not os.path.isfile(caminho):
        sys.exit('Rode primeiro: python3 sapl_varredura.py municipios')
    return list(csv.DictReader(open(caminho, encoding='utf-8-sig')))

# ------------------------------------------------------------------ CSV helper
def abrir_csv(caminho, colunas):
    novo = not os.path.isfile(caminho)
    f = open(caminho, 'a', encoding='utf-8-sig', newline='')
    w = csv.DictWriter(f, fieldnames=colunas)
    if novo:
        w.writeheader()
    return f, w

def chaves_feitas(caminho, cols):
    if not os.path.isfile(caminho):
        return set()
    out = set()
    for r in csv.DictReader(open(caminho, encoding='utf-8-sig')):
        out.add(tuple(r.get(c, '') for c in cols))
    return out

# ------------------------------------------------------------------- descobrir
COLS_HOST = ['cod_ibge', 'municipio', 'uf', 'host', 'dns', 'api', 'endpoint',
             'busca_param', 'total_normas', 'erro', 'visto_em']

def mapa_slugs(muns):
    """slug -> conjunto de (municipio, uf) que o geram. Base da guarda de colisão."""
    m = {}
    for x in muns:
        for s in slugs(x['municipio']):
            m.setdefault((s, x['uf']), set()).add(norm(x['municipio']))
    return m

def descobrir(args, http, muns):
    saida = os.path.join(args.saida, 'sapl_hosts.csv')
    MS = mapa_slugs(muns)
    feitos = {t[0] for t in chaves_feitas(saida, ['cod_ibge'])}
    alvo = _prioridade([m for m in muns if str(m['cod_ibge']) not in feitos],
                       args.prioridade, args.so_prioridade)
    print('descobrir: %d municípios (%d já feitos)' % (len(alvo), len(muns) - len(alvo)))
    f, w = abrir_csv(saida, COLS_HOST)
    try:
        for i, m in enumerate(alvo, 1):
            proib = {s for (s, uf), donos in MS.items()
                     if uf == m['uf'] and norm(m['municipio']) not in donos
                     for _ in (0,)}
            proib = {s for (s, uf), donos in MS.items()
                     if uf == m['uf'] and donos and norm(m['municipio']) not in donos}
            cands = hosts_candidatos(m['municipio'], m['uf'], proib)
            vivo = None
            with ThreadPoolExecutor(max_workers=min(args.workers, len(cands))) as ex:
                fut = {ex.submit(dns_ok, h): h for h in cands}
                for fu in as_completed(fut):
                    if fu.result():
                        h = fut[fu]
                        if vivo is None or h.startswith('sapl.'):
                            vivo = h
            reg = dict(cod_ibge=m['cod_ibge'], municipio=m['municipio'], uf=m['uf'],
                       host=vivo or '', dns='sim' if vivo else 'nao', api='',
                       endpoint='', busca_param='', total_normas='', erro='',
                       visto_em=time.strftime('%Y-%m-%d'))
            if vivo:
                achou = False
                for nome, ep in ENDPOINTS:
                    j, err = http.get_json('https://%s%s?page=1' % (vivo, ep))
                    if eh_resposta_sapl(j):
                        reg['api'] = 'sim'; reg['endpoint'] = ep
                        pg = j.get('pagination') or {}
                        reg['total_normas'] = pg.get('total_entries', j.get('count', ''))
                        for p in PARAMS_BUSCA:
                            j2, _ = http.get_json('https://%s%s?%s=%s'
                                                  % (vivo, ep, p, urllib.parse.quote('mobilidade')))
                            if eh_resposta_sapl(j2):
                                reg['busca_param'] = p; break
                        achou = True; break
                    else:
                        reg['erro'] = err or 'sem API SAPL'
                if not achou:
                    reg['api'] = 'nao'
            w.writerow(reg); f.flush()
            if i % 25 == 0:
                print('  %d/%d ... último: %s %s (%s)'
                      % (i, len(alvo), m['municipio'], m['uf'], reg['api'] or reg['dns']))
    finally:
        f.close()
    print('gravado: %s' % saida)

# ---------------------------------------------------------------------- buscar
COLS_ACH = ['cod_ibge', 'municipio', 'uf', 'host', 'endpoint', 'termo',
            'frase_casada', 'tipo', 'numero', 'ano', 'data', 'ementa',
            'link_pdf', 'campo_casado', 'colhido_em']

def buscar(args, http, muns):
    hosts_csv = os.path.join(args.saida, 'sapl_hosts.csv')
    if not os.path.isfile(hosts_csv):
        sys.exit('Rode primeiro a fase "descobrir".')
    hosts = [r for r in csv.DictReader(open(hosts_csv, encoding='utf-8-sig'))
             if r['api'] == 'sim' and r['host']]
    if args.uf:
        hosts = [r for r in hosts if r['uf'] in args.uf]
    saida = os.path.join(args.saida, 'sapl_achados.csv')
    log = open(os.path.join(args.saida, 'sapl_log.txt'), 'a', encoding='utf-8')
    feitos = chaves_feitas(saida, ['cod_ibge', 'termo'])  # termo = rótulo do grupo
    grupos = [parse_grupo(t) for t in args.termos]
    print('buscar: %d hosts com API × %d grupos de termos' % (len(hosts), len(grupos)))
    for rot, alts in grupos:
        print('   %-22s <- %s' % (rot, ' | '.join(alts)))
    f, w = abrir_csv(saida, COLS_ACH)
    try:
        for i, h in enumerate(hosts, 1):
            for rotulo, alts in grupos:
                if (h['cod_ibge'], rotulo) in feitos:
                    continue
                termo = alts[0]  # a 1a alternativa vai ao servidor como filtro grosso
                ep = h['endpoint'] or '/api/norma/normajuridica/'
                itens, err = [], None
                if h['busca_param']:
                    url = 'https://%s%s?%s=%s' % (h['host'], ep, h['busca_param'],
                                                  urllib.parse.quote(termo))
                    pag = 1
                    while pag <= args.max_paginas:
                        j, err = http.get_json(url + '&page=%d' % pag)
                        if not eh_resposta_sapl(j):
                            break
                        r = resultados(j)
                        itens.extend(r)
                        prox = (j.get('pagination') or {}).get('links', {}).get('next')
                        if not r or not prox:
                            break
                        pag += 1
                elif args.varrer_tudo:
                    pag = 1
                    while pag <= args.max_paginas:
                        j, err = http.get_json('https://%s%s?page=%d' % (h['host'], ep, pag))
                        if not eh_resposta_sapl(j):
                            break
                        r = resultados(j)
                        itens.extend(r)
                        if not r:
                            break
                        pag += 1
                else:
                    log.write('%s\t%s\tsem busca textual e --varrer-tudo desligado\n'
                              % (h['municipio'], rotulo))
                    continue
                # >>> a garantia do termo todo <<<
                n = 0
                for it in itens:
                    if not isinstance(it, dict):
                        continue
                    txt = texto_busca(it)
                    casou = next((a for a in alts if contem_frase(txt, a)), None)
                    if not casou:
                        continue
                    qual = ('ementa' if contem_frase(campo(it, 'ementa'), casou)
                            else 'outro campo')
                    w.writerow(dict(
                        cod_ibge=h['cod_ibge'], municipio=h['municipio'], uf=h['uf'],
                        host=h['host'], endpoint=ep, termo=rotulo,
                        frase_casada=casou,
                        tipo=campo(it, 'tipo', 'tipo_norma', 'tipo_materia'),
                        numero=campo(it, 'numero'), ano=campo(it, 'ano'),
                        data=campo(it, 'data', 'data_apresentacao', 'data_publicacao'),
                        ementa=re.sub(r'\s+', ' ', str(campo(it, 'ementa'))).strip()[:600],
                        link_pdf=link_pdf(it, h['host']), campo_casado=qual,
                        colhido_em=time.strftime('%Y-%m-%d %H:%M')))
                    n += 1
                f.flush()
                if err:
                    log.write('%s\t%s\terro: %s\n' % (h['municipio'], rotulo, err))
                if n:
                    print('  ✓ %-24s %-3s %-22s %d' % (h['municipio'][:24], h['uf'], rotulo, n))
            if i % 20 == 0:
                print('  ... %d/%d hosts' % (i, len(hosts)))
    finally:
        f.close(); log.close()
    print('gravado: %s' % saida)


# ---------------------------------------------------------------------- corpus
# POR QUE COLHER TUDO E FILTRAR DEPOIS
#   A fase "buscar" manda UMA alternativa de cada grupo ao servidor como filtro
#   grosso. Isso tem dois custos: (a) as demais alternativas so sao vistas se o
#   servidor devolver o item por acaso — se o SAPL fizer substring em vez de AND
#   de palavras, "plano municipal de mobilidade urbana" nao volta na consulta
#   "plano de mobilidade"; (b) cada termo novo exige bater de novo nos servidores.
#   Colher a base inteira uma vez resolve os dois: o filtro passa a ser local,
#   exaustivo, e qualquer termo novo se aplica offline, sem tocar as camaras de
#   novo — que e o padrao de replicabilidade que a pesquisa adota.
COLS_COR = ['cod_ibge', 'municipio', 'uf', 'host', 'endpoint', 'tipo', 'numero',
            'ano', 'data', 'ementa', 'texto', 'link_pdf', 'colhido_em']
COLS_COR_HOSTS = ['cod_ibge', 'municipio', 'uf', 'host', 'paginas', 'normas',
                  'esperado', 'completo', 'erro', 'colhido_em']

def _prioridade(muns_ou_hosts, caminho, so=False):
    """Ordena a lista pondo primeiro os cod_ibge listados no CSV de prioridade.
    Preserva a ordem original dentro de cada bloco — a prioridade so promove.
    Com so=True, DESCARTA o resto: roda apenas a lista de prioridade."""
    if not caminho:
        return muns_ou_hosts
    if not os.path.isfile(caminho):
        sys.exit('--prioridade: arquivo nao encontrado: %s' % caminho)
    alvo = {str(r.get('cod_ibge', '')).strip()
            for r in csv.DictReader(open(caminho, encoding='utf-8-sig'))}
    alvo.discard('')
    if not alvo:
        sys.exit('--prioridade: nenhuma coluna cod_ibge utilizavel em %s' % caminho)
    prim = [x for x in muns_ou_hosts if str(x['cod_ibge']) in alvo]
    resto = [x for x in muns_ou_hosts if str(x['cod_ibge']) not in alvo]
    if so:
        print('prioridade EXCLUSIVA: rodando so %d de %d municipios'
              % (len(prim), len(muns_ou_hosts)))
        return prim
    print('prioridade: %d de %d municipios promovidos ao inicio da fila'
          % (len(prim), len(muns_ou_hosts)))
    return prim + resto

# Um host que para de mandar 'next' antes do fim se declarava COMPLETO. Medido
# em 10/09/2026 na varredura nacional: Paraguacu Paulista/SP gravou 50 de 5.287
# normas e disse 'sim'. E o pior defeito possivel num corpus — nao parece falta,
# parece o total. Dai a terceira classe: 'parcial'.
# Respostas que significam "nao existe pagina depois desta" e nao "deu errado".
# O DRF devolve 404 a ?page= fora do intervalo; alguns SAPL devolvem 400.
FIM_DE_COLECAO = ('HTTP 404', 'HTTP 400')

FALTA_FRAC = 0.95   # colheu menos de 95% do esperado
FALTA_PISO = 50     # e a falta passa de 50 normas

def veredito(colhido, esperado, completo, esgotou=False):
    """Classifica a colheita do host em quatro estados.

    'sim'      — bate com o que a descoberta prometeu.
    'esgotado' — paginamos ATE O FIM (pagina que nao trouxe registro novo) e
                 ainda ficou abaixo do total declarado. ⚠️ A diferenca e do
                 SERVIDOR, nao nossa: o 'total_entries' pode contar norma que a
                 API nao serve (nao publicada, restrita). TERMINAL — nao refaz.
    'parcial'  — ficou abaixo por motivo que pode ser nosso (bateu no
                 --max-paginas). Refeito na proxima rodada.
    'nao'      — erro de rede ou resposta invalida.
    """
    if completo != 'sim':
        return completo
    try:
        e = int(esperado or 0)
    except (TypeError, ValueError):
        return completo
    if e > 0 and colhido < e * FALTA_FRAC and (e - colhido) > FALTA_PISO:
        return 'esgotado' if esgotou else 'parcial'
    return 'sim'

def _sonda_page_size(http, host, ep, base_n):
    """SAPL e Django REST Framework: alguns aceitam ?page_size=N e devolvem a
    pagina maior, outros ignoram o parametro. Sondar uma vez por host troca
    dezenas de requisicoes por uma — em 1,7 milhao de normas isso e a
    diferenca entre horas e dias. So adota se a pagina realmente cresceu."""
    for ps in (200, 100):
        j, _ = http.get_json('https://%s%s?page_size=%d&page=1' % (host, ep, ps))
        if eh_resposta_sapl(j) and len(resultados(j)) > base_n:
            return ps, len(resultados(j))
    return 0, base_n

def _uma_passada(h, args, ua, ps_forcado=None):
    """Uma passada de colheita no host. ps_forcado=0 desliga o page_size."""
    http = Http(ua, delay=args.delay, timeout=args.timeout)
    ep = h['endpoint'] or '/api/norma/normajuridica/'
    pag, err, completo = 1, '', 'nao'
    vistos, linhas = set(), []
    ps, esgotou = 0, False
    if ps_forcado is None:
        if not args.sem_page_size:
            j0, _ = http.get_json('https://%s%s?page=1' % (h['host'], ep))
            base_n = len(resultados(j0)) if eh_resposta_sapl(j0) else 0
            if base_n:
                ps, _t = _sonda_page_size(http, h['host'], ep, base_n)
    else:
        ps = ps_forcado
    sufixo = ('&page_size=%d' % ps) if ps else ''
    while pag <= args.max_paginas:
        j, e = http.get_json('https://%s%s?page=%d%s' % (h['host'], ep, pag, sufixo))
        if e:
            # 🔴 O Django REST Framework responde 404 ("Invalid page") a pagina
            # ALEM da ultima. Depois da pagina 1 e com registro na mao, isso e o
            # FIM DA COLECAO, nao falha de rede. Tratar como erro deixava o host
            # em 'nao' e o refazia a cada rodada sem nunca convergir. Medido em
            # 10/09/2026 em Rio Bonito do Iguacu/PR e Ibirajuba/PE.
            if e in FIM_DE_COLECAO and pag > 1 and linhas:
                completo, esgotou = 'sim', True
                err = err or 'fim da colecao sinalizado por %s na pagina %d' % (e, pag)
            else:
                err = e
            break
        if not eh_resposta_sapl(j):
            err = err or 'resposta nao e SAPL na pagina %d' % pag
            break
        itens = resultados(j)
        if not itens:
            completo, esgotou = 'sim', True
            break
        novos = 0
        for it in itens:
            if not isinstance(it, dict):
                continue
            chave = (str(campo(it, 'tipo', 'tipo_norma')),
                     str(campo(it, 'numero')), str(campo(it, 'ano')))
            if chave in vistos:
                continue
            vistos.add(chave)
            novos += 1
            linhas.append(dict(
                cod_ibge=h['cod_ibge'], municipio=h['municipio'], uf=h['uf'],
                host=h['host'], endpoint=ep,
                tipo=campo(it, 'tipo', 'tipo_norma', 'tipo_materia'),
                numero=campo(it, 'numero'), ano=campo(it, 'ano'),
                data=campo(it, 'data', 'data_apresentacao', 'data_publicacao'),
                ementa=re.sub(r'\s+', ' ', str(campo(it, 'ementa'))).strip()[:900],
                texto=re.sub(r'\s+', ' ', texto_busca(it)).strip()[:2000],
                link_pdf=link_pdf(it, h['host']),
                colhido_em=time.strftime('%Y-%m-%d %H:%M')))
        # 🔴 A PARADA NAO OLHA MAIS O LINK 'next' (corrigido em 10/09/2026).
        # Havia servidor que devolve 'next' nulo em TODA pagina — e a colheita
        # parava na pagina 1 sem nunca testar a 2. Medido em Paraguacu
        # Paulista/SP: 50 de 5.287 na paginacao normal, e exatamente 10 por ano
        # no fatiamento, ou seja, uma pagina por consulta. A condicao certa e
        # empirica: avanca enquanto a pagina TRAZ REGISTRO NOVO.
        if novos == 0:
            completo, esgotou = 'sim', True
            break
        pag += 1
    else:
        # Teto NOSSO, nao do servidor: marca 'parcial' para refazer na proxima
        # rodada, em vez de 'nao' (que se le como erro de rede).
        err = err or 'parou em --max-paginas=%d' % args.max_paginas
        completo, esgotou = 'parcial', False
    return linhas, pag, err, completo, ps, esgotou

def _anos_do_host(linhas, args):
    """Janela de anos a consultar. Comeca no --ano-inicial (padrao 1960, que cobre
    a legislacao municipal digitalizada) e vai ate o ano corrente. Se a passada
    anterior colheu algo, o menor ano visto puxa o inicio para tras — municipio
    com norma de 1948 nao fica de fora por causa do padrao."""
    fim = int(time.strftime('%Y'))
    ini = args.ano_inicial
    for l in linhas:
        try:
            a = int(str(l.get('ano'))[:4])
            if 1800 < a < ini:
                ini = a
        except (TypeError, ValueError):
            pass
    return list(range(ini, fim + 1))

def _fatia_por_ano(h, args, ua, anos):
    """Colhe o host ano a ano, com ?ano=YYYY.

    🔴 POR QUE ISTO EXISTE. Alguns SAPL cortam a paginacao antes do fim: param de
    mandar o link 'next' e a colheita termina com uma fracao da base, embora o
    'total_entries' prometa mais. Medido em 10/09/2026 em Paraguacu Paulista/SP
    (50 de 5.287), Rio Bonito do Iguacu/PR e Ibirajuba/PE — os tres com orcamento
    de pagina sobrando e sem page_size, o que descarta tanto o limite local como
    o parametro. Se o corte e na paginacao, consultar por ANO produz respostas
    pequenas, cada uma abaixo do corte, e o conjunto se recompoe.
    """
    http = Http(ua, delay=args.delay, timeout=args.timeout)
    ep = h['endpoint'] or '/api/norma/normajuridica/'
    vistos, linhas, err, tocou, teto = set(), [], '', 0, False
    ps = 0 if args.sem_page_size else 200   # pagina grande reduz as idas por ano
    sufixo = ('&page_size=%d' % ps) if ps else ''
    for ano in anos:
        pag = 1
        while pag <= args.max_paginas:
            j, e = http.get_json('https://%s%s?ano=%d&page=%d%s'
                                 % (h['host'], ep, ano, pag, sufixo))
            if e or not eh_resposta_sapl(j):
                # 404 depois da pagina 1 e o fim das normas DAQUELE ano (DRF),
                # nao falha: passa para o ano seguinte sem marcar erro.
                if e and not err and not (e in FIM_DE_COLECAO and pag > 1):
                    err = e
                break
            itens = resultados(j)
            if not itens:
                break
            tocou += 1
            novos = 0
            for it in itens:
                if not isinstance(it, dict):
                    continue
                chave = (str(campo(it, 'tipo', 'tipo_norma')),
                         str(campo(it, 'numero')), str(campo(it, 'ano')))
                if chave in vistos:
                    continue
                vistos.add(chave)
                novos += 1
                linhas.append(dict(
                    cod_ibge=h['cod_ibge'], municipio=h['municipio'], uf=h['uf'],
                    host=h['host'], endpoint=ep,
                    tipo=campo(it, 'tipo', 'tipo_norma', 'tipo_materia'),
                    numero=campo(it, 'numero'), ano=campo(it, 'ano'),
                    data=campo(it, 'data', 'data_apresentacao', 'data_publicacao'),
                    ementa=re.sub(r'\s+', ' ', str(campo(it, 'ementa'))).strip()[:900],
                    texto=re.sub(r'\s+', ' ', texto_busca(it)).strip()[:2000],
                    link_pdf=link_pdf(it, h['host']),
                    colhido_em=time.strftime('%Y-%m-%d %H:%M')))
            if novos == 0:      # mesma parada empirica da 1a passada
                break
            pag += 1
        else:
            teto = True         # bateu no --max-paginas dentro de um ano
    # se nenhuma consulta por ano devolveu nada, o parametro nao e aceito
    if not tocou:
        err = 'o endpoint nao aceita filtro por ano'
    if teto:
        err = (err + ' | ' if err else '') + ('parou em --max-paginas=%d em algum ano'
                                              % args.max_paginas)
        return linhas, len(anos), err, 'parcial', False
    return linhas, len(anos), err, ('sim' if linhas else 'nao'), bool(linhas)

def _colhe_host(h, args, ua):
    """Colhe UM host e devolve (registro, linhas, page_size).

    🔴 SEGUNDA PASSADA SEM page_size (10/09/2026). Alguns SAPL aceitam
    ?page_size pela METADE: devolvem mais que o default por pagina, mas perdem
    o link 'next' e a colheita para no meio se dizendo terminada. Medido em
    Paraguacu Paulista/SP (50 de 5.287 normas), Canoinhas/SC, Rio Bonito do
    Iguacu/PR e Ibirajuba/PE — os quatro reproduziram o MESMO numero em duas
    rodadas, o que descarta instabilidade de rede. Como o page_size e uma
    otimizacao nossa, o prejuizo tambem e: quando a passada com page_size sai
    'parcial', refaz-se o host sem ele e fica a colheita maior."""
    linhas, pag, err, completo, ps, esg = _uma_passada(h, args, ua)
    esperado = h.get('total_normas') or ''

    def curto():
        return veredito(len(linhas), esperado, completo, esg) in ('parcial', 'esgotado')

    # 2a passada: sem page_size, para o servidor que aceita o parametro pela metade
    if ps and curto():
        l2, p2, e2, c2, _, g2 = _uma_passada(h, args, ua, ps_forcado=0)
        if len(l2) > len(linhas):
            linhas, pag, err, completo, ps, esg = l2, p2, e2, c2, 0, g2
            err = (err + ' | ' if err else '') + 'refeito sem page_size'
    # 3a passada: fatiar por ano, para o servidor que corta a paginacao
    if not args.sem_fatiar_ano and curto():
        anos = _anos_do_host(linhas, args)
        l3, p3, e3, c3, g3 = _fatia_por_ano(h, args, ua, anos)
        if len(l3) > len(linhas):
            linhas, pag, err, completo, ps, esg = l3, p3, e3, c3, 0, g3
            err = (err + ' | ' if err else '') + ('fatiado por ano (%d anos)' % len(anos))
    return _fecha_registro(h, linhas, pag, err, completo, ps, esg)

def _fecha_registro(h, linhas, pag, err, completo, ps, esgotou=False):
    esperado = h.get('total_normas') or ''
    veredicto = veredito(len(linhas), esperado, completo, esgotou)
    if veredicto == 'esgotado' and not err:
        err = ('paginado ate o fim: colheu %d, e a descoberta declarava %s. '
               'A diferenca e do servidor — o total declarado pode contar norma '
               'que a API nao serve (nao publicada, restrita).'
               % (len(linhas), esperado))
    if veredicto == 'parcial' and not err:
        err = ('colheu %d de %s e parou antes do fim, sem esgotar — refazer'
               % (len(linhas), esperado))
    reg = dict(cod_ibge=h['cod_ibge'], municipio=h['municipio'], uf=h['uf'],
               host=h['host'], paginas=pag, normas=len(linhas),
               esperado=esperado, completo=veredicto,
               erro=err, colhido_em=time.strftime('%Y-%m-%d %H:%M'))
    return reg, linhas, ps

def corpus(args, http, muns):
    """Baixa TODAS as normas de cada host com API, paginando ate o fim.

    Paralelo por HOST (--workers). Cada host mantem o seu proprio --delay, entao
    a carga sobre cada camara e a mesma de antes; o que muda e quantas camaras
    sao atendidas ao mesmo tempo. Em 1,7 milhao de normas isso e a diferenca
    entre dois dias e algumas horas.
    """
    hosts_csv = os.path.join(args.saida, 'sapl_hosts.csv')
    if not os.path.isfile(hosts_csv):
        sys.exit('Rode primeiro a fase "descobrir".')
    hosts = [r for r in csv.DictReader(open(hosts_csv, encoding='utf-8-sig'))
             if r['api'] == 'sim' and r['host']]
    # a descoberta pode ter linhas repetidas (rodadas sobrepostas): fica a ultima
    unicos = {}
    for h in hosts:
        unicos[h['cod_ibge']] = h
    if len(unicos) != len(hosts):
        print('descoberta tinha %d linhas repetidas — mantida a ultima de cada'
              % (len(hosts) - len(unicos)))
    hosts = list(unicos.values())
    if args.uf:
        hosts = [r for r in hosts if r['uf'] in args.uf]
    hosts = _prioridade(hosts, args.prioridade, args.so_prioridade)
    if args.vazios == 'pular':
        antes = len(hosts)
        hosts = [h for h in hosts if int(h.get('total_normas') or 0) > 0]
        if antes != len(hosts):
            print('pulando %d hosts que a descoberta viu com base vazia '
                  '(use --vazios tentar para incluí-los)' % (antes - len(hosts)))
    saida = os.path.join(args.saida, 'sapl_corpus.csv')
    reg_csv = os.path.join(args.saida, 'sapl_corpus_hosts.csv')
    # so pula host JA CONCLUIDO: um host interrompido no meio e refeito do zero,
    # senao o corpus fica com um pedaco e se diz completo.
    feitos = set()
    if os.path.isfile(reg_csv):
        for r in csv.DictReader(open(reg_csv, encoding='utf-8-sig')):
            # 'esgotado' e terminal: paginamos ate o fim e o servidor deu menos.
            # Refazer nao muda o numero — muda so o tempo.
            if r.get('completo') in ('sim', 'esgotado'):
                feitos.add(r['cod_ibge'])
    alvo = [h for h in hosts if h['cod_ibge'] not in feitos]
    esperado = sum(int(h.get('total_normas') or 0) for h in alvo)
    print('corpus: %d hosts (%d ja completos) · %s normas esperadas · %d workers'
          % (len(alvo), len(hosts) - len(alvo),
             '{:,}'.format(esperado).replace(',', '.'), args.workers))
    ua = 'sapl_varredura/%s (pesquisa academica UFABC - Tarifa Zero%s)' % (
        VERSAO, '; ' + args.contato if args.contato else '')
    f, w = abrir_csv(saida, COLS_COR)
    fr, wr = abrir_csv(reg_csv, COLS_COR_HOSTS)
    lock = threading.Lock()
    feito_n, normas_n, incompletos = 0, 0, 0
    parciais, esgotados = [], []
    t0 = time.time()
    try:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
            fut = {ex.submit(_colhe_host, h, args, ua): h for h in alvo}
            for fu in as_completed(fut):
                h = fut[fu]
                try:
                    reg, linhas, ps = fu.result()
                except Exception as exc:
                    reg = dict(cod_ibge=h['cod_ibge'], municipio=h['municipio'],
                               uf=h['uf'], host=h['host'], paginas=0, normas=0,
                               esperado=h.get('total_normas') or '',
                               completo='nao', erro='excecao: %s' % type(exc).__name__,
                               colhido_em=time.strftime('%Y-%m-%d %H:%M'))
                    linhas, ps = [], 0
                with lock:
                    for l in linhas:
                        w.writerow(l)
                    wr.writerow(reg)
                    f.flush(); fr.flush()
                    feito_n += 1
                    normas_n += len(linhas)
                    if reg['completo'] == 'esgotado':
                        esgotados.append(reg)
                    elif reg['completo'] != 'sim':
                        incompletos += 1
                        parciais.append(reg)
                    marca = {'sim': 'ok ', 'esgotado': '== ', 'parcial': '~~ '}.get(
                        reg['completo'], '!! ')
                    print('  %s%-26s %-3s %6d normas em %3d pag%s  %s'
                          % (marca, h['municipio'][:26], h['uf'], len(linhas),
                             reg['paginas'], (' ps=%d' % ps) if ps else '',
                             str(reg['erro'])[:40]))
                    if feito_n % 25 == 0:
                        dec = time.time() - t0
                        falta = (len(alvo) - feito_n) * (dec / feito_n)
                        print('  ... %d/%d hosts · %s normas · %.0f min '
                              'decorridos, ~%.0f min restantes'
                              % (feito_n, len(alvo),
                                 '{:,}'.format(normas_n).replace(',', '.'),
                                 dec / 60, falta / 60))
    finally:
        f.close(); fr.close()
    print('\n%s normas colhidas de %d hosts · %d incompletos'
          % ('{:,}'.format(normas_n).replace(',', '.'), feito_n, incompletos))
    if esgotados:
        print('\n== estes hosts foram paginados ATE O FIM e o servidor entregou '
              'menos que o total que ele mesmo declara. NAO serao refeitos: a '
              'diferenca e do servidor, e vira indisponibilidade documentada.')
        for r in sorted(esgotados, key=lambda x: -(int(x['esperado'] or 0)
                                                   - int(x['normas'] or 0))):
            print('   %-26s %-3s %7s de %-8s declaradas' % (r['municipio'][:26],
                  r['uf'], r['normas'], r['esperado']))
    if parciais:
        print('\n🔴 estes hosts NAO estao completos e serao refeitos na proxima '
              'rodada (aumente --max-paginas se o motivo for esse):')
        for r in sorted(parciais, key=lambda x: -(int(x['esperado'] or 0)
                                                  - int(x['normas'] or 0))):
            print('   %-26s %-3s %7s de %-8s  %s'
                  % (r['municipio'][:26], r['uf'], r['normas'],
                     r['esperado'], str(r['erro'])[:60]))
    print('gravado: %s  e  %s' % (saida, reg_csv))

def filtrar(args, http, muns):
    """Aplica os grupos de termos ao corpus ja colhido. Offline, sem rede."""
    corp = os.path.join(args.saida, 'sapl_corpus.csv')
    if not os.path.isfile(corp):
        sys.exit('Rode primeiro a fase "corpus".')
    grupos = [parse_grupo(t) for t in args.termos]
    print('filtrar: %d grupos de termos sobre %s' % (len(grupos), corp))
    for rot, alts in grupos:
        print('   %-22s <- %s' % (rot, ' | '.join(alts)))
    saida = os.path.join(args.saida, 'sapl_achados.csv')
    if os.path.isfile(saida):     # refiltrar e barato; o arquivo e derivado
        os.replace(saida, saida + '.anterior')
        print('  (o sapl_achados.csv anterior virou sapl_achados.csv.anterior)')
    f, w = abrir_csv(saida, COLS_ACH)
    from collections import Counter
    conta, lidas, casadas, repetidas = Counter(), 0, 0, 0
    # 🔴 DEDUPLICACAO (v1.1). O corpus e APENDADO: host refeito numa rodada
    # posterior grava as normas de novo, e sem isto o mesmo achado aparecia duas
    # vezes na contagem. A chave e (host, tipo, numero, ano) — o mesmo par que
    # identifica a norma dentro da colheita.
    vistas = set()
    try:
        for r in csv.DictReader(open(corp, encoding='utf-8-sig')):
            lidas += 1
            if not args.sem_dedup:
                chave = '|'.join((r.get('host') or '', str(r.get('tipo') or ''),
                                  str(r.get('numero') or ''), str(r.get('ano') or '')))
                if chave in vistas:
                    repetidas += 1
                    continue
                vistas.add(chave)
            txt = (r.get('ementa') or '') + ' ' + (r.get('texto') or '')
            tn = norm(txt)          # normaliza UMA vez, nao uma por alternativa
            en = norm(r.get('ementa', ''))
            bateu = False
            for rotulo, alts in grupos:
                casou = next((a for a in alts if contem_frase_norm(tn, a)), None)
                if not casou:
                    continue
                bateu = True
                conta[rotulo] += 1
                w.writerow(dict(
                    cod_ibge=r['cod_ibge'], municipio=r['municipio'], uf=r['uf'],
                    host=r['host'], endpoint=r.get('endpoint', ''), termo=rotulo,
                    frase_casada=casou, tipo=r.get('tipo', ''),
                    numero=r.get('numero', ''), ano=r.get('ano', ''),
                    data=r.get('data', ''), ementa=r.get('ementa', ''),
                    link_pdf=r.get('link_pdf', ''),
                    campo_casado=('ementa' if contem_frase_norm(
                        en if en is not None else norm(r.get('ementa', '')), casou)
                        else 'outro campo'),
                    colhido_em=r.get('colhido_em', '')))
            if bateu:
                casadas += 1
    finally:
        f.close()
    if repetidas:
        print('\n%d linhas repetidas descartadas (host recolhido em outra rodada)'
              % repetidas)
    print('\n%d normas lidas%s · %d casaram ao menos um grupo'
          % (lidas, (' (%d unicas)' % len(vistas)) if repetidas else '', casadas))
    for rot, _ in grupos:
        print('  %-22s %6d' % (rot, conta[rot]))
    print('gravado: %s' % saida)


# -------------------------------------------------------------------- autoteste
def autoteste():
    ok = fail = 0
    def t(nome, got, exp):
        nonlocal ok, fail
        if got == exp:
            ok += 1
        else:
            fail += 1
            print('  FALHOU %s: obtido %r, esperado %r' % (nome, got, exp))
    # --- frase contígua
    t('frase exata', contem_frase('Institui o Programa Tarifa Zero no Município', 'tarifa zero'), True)
    t('acento/caixa', contem_frase('INSTITUI O PASSE LIVRE ESTUDANTIL', 'passe livre'), True)
    t('palavras soltas NAO casam',
      contem_frase('concede passe especial e acesso livre aos parques', 'passe livre'), False)
    t('parcial nao casa', contem_frase('tarifa zerada para idosos', 'tarifa zero'), False)
    t('planmob variante',
      contem_frase('Institui o Plano Municipal de Mobilidade Urbana', 'plano de mobilidade'), False)
    t('planmob direto',
      contem_frase('Institui o Plano de Mobilidade Urbana do Municipio', 'plano de mobilidade'), True)
    t('fundo', contem_frase('Cria o Fundo Municipal de Transporte Coletivo Urbano',
                            'fundo municipal de transporte'), True)
    t('pontuacao', contem_frase('gratuidade (tarifa zero) no transporte', 'tarifa zero'), True)
    t('fronteira', contem_frase('tarifa zerozinho', 'tarifa zero'), False)
    # --- slugs e hosts
    t('slug simples', slugs('Irati')[0], 'irati')
    t('slug composto', slugs('Rio Branco do Sul')[0], 'riobrancodosul')
    t('slug sem preposicao', 'riobrancosul' in slugs('Rio Branco do Sul'), True)
    t('slug acento', slugs('Araçariguama')[0], 'aracariguama')
    hs = hosts_candidatos('Irati', 'PR')
    t('host sapl primeiro', hs[0], 'sapl.irati.pr.leg.br')
    t('host sem prefixo', 'irati.pr.leg.br' in hs, True)
    t('host camara', 'sapl.camarairati.pr.leg.br' in hs, True)
    t('host monte mor', 'sapl.montemor.sp.leg.br' in hosts_candidatos('Monte Mor', 'SP'), True)
    t('nao gera so a 1a palavra', 'vargem' in slugs('Vargem Grande Paulista'), False)
    t('guarda de colisao bloqueia',
      any('vargem.sp' in h for h in hosts_candidatos('Vargem Grande Paulista', 'SP', {'vargem'})), False)
    t('slug completo sobrevive',
      'sapl.vargemgrandepaulista.sp.leg.br' in hosts_candidatos('Vargem Grande Paulista', 'SP'), True)
    ms = mapa_slugs([{'municipio': 'Palmas', 'uf': 'TO'}, {'municipio': 'Palmas', 'uf': 'PR'}])
    t('palmas TO e PR nao colidem (UFs distintas)',
      ('palmas', 'TO') in ms and ('palmas', 'PR') in ms, True)
    # --- resposta SAPL
    t('detecta sapl', eh_resposta_sapl({'pagination': {}, 'results': []}), True)
    t('nao sapl', eh_resposta_sapl({'erro': 'x'}), False)
    t('resultados', resultados({'results': [{'a': 1}]}), [{'a': 1}])
    t('link relativo', link_pdf({'texto_integral': '/media/x.pdf'}, 'h.leg.br'),
      'https://h.leg.br/media/x.pdf')
    t('link absoluto', link_pdf({'texto_integral': 'http://h/x.pdf'}, 'h.leg.br'), 'http://h/x.pdf')
    # --- grupos de termos (a correcao de 09/09/2026)
    rot, alts = parse_grupo('planmob = plano de mobilidade | plano municipal de mobilidade')
    t('grupo rotulo', rot, 'planmob')
    t('grupo alternativas', alts, ['plano de mobilidade', 'plano municipal de mobilidade'])
    t('grupo sem =', parse_grupo('tarifa zero'), ('tarifa zero', ['tarifa zero']))
    def casa_grupo(txt, grupo):
        _, aa = parse_grupo(grupo)
        return any(contem_frase(txt, a) for a in aa)
    def grupo(rotulo):
        """Acha o grupo pelo ROTULO, nunca pelo indice: a ordem de TERMOS_PADRAO
        muda quando termos novos entram, e um teste preso ao indice passa a
        testar outra coisa em silencio. Foi o que aconteceu em 09/09/2026."""
        for g in TERMOS_PADRAO:
            if parse_grupo(g)[0] == rotulo:
                return g
        raise AssertionError('grupo inexistente em TERMOS_PADRAO: %s' % rotulo)
    G = grupo('planmob')
    t('MONTE MOR pelo grupo',
      casa_grupo('Institui o Plano Municipal de Mobilidade Urbana de Monte Mor', G), True)
    t('IRATI pelo grupo',
      casa_grupo('INSTITUI O PLANO DE MOBILIDADE URBANA DO MUNICIPIO DE IRATI', G), True)
    t('ARACARIGUAMA pelo grupo',
      casa_grupo('Institui o Plano de Mobilidade Urbana do Municipio de Aracariguama', G), True)
    t('grupo nao pega plano diretor puro',
      casa_grupo('Dispoe sobre o Plano Diretor do municipio', G), False)
    t('grupo fundo pega Muzambinho',
      casa_grupo('Cria o Fundo Municipal de Transporte Coletivo Urbano de Muzambinho',
                 grupo('fundo de transporte')), True)
    t('grupo fundo pega FUMTRAP de Irati (preposicao flexionada)',
      casa_grupo('DISPOE SOBRE A CRIACAO DO FUNDO MUNICIPAL DO TRANSPORTE PUBLICO (FUMTRAP)',
                 grupo('fundo de transporte')), True)
    # --- grupos novos da colheita ampla (09/09/2026) ---
    t('gratuidade pega Araraquara (palavra no meio)',
      casa_grupo('Institui o transporte comunitario gratuito no municipio',
                 grupo('gratuidade')), True)
    t('gratuidade pega vedacao de cobranca',
      casa_grupo('Fica vedada a cobranca de tarifa aos usuarios',
                 grupo('gratuidade')), True)
    t('grupo amplo pega merenda (e por isso e separado)',
      casa_grupo('Dispoe sobre a merenda escolar gratuita',
                 grupo('gratuito (amplo, revisar)')), True)
    t('grupo gratuidade NAO pega merenda',
      casa_grupo('Dispoe sobre a merenda escolar gratuita',
                 grupo('gratuidade')), False)
    t('concessao pega preposicao flexionada',
      casa_grupo('Autoriza a concessao do servico de transporte coletivo urbano',
                 grupo('concessao')), True)
    t('onibus nao pega onibusario inventado (fronteira de palavra)',
      casa_grupo('Dispoe sobre o onibusario municipal', grupo('onibus')), False)
    t('planmob nao pega plano diretor estrategico',
      casa_grupo('Dispoe sobre o Plano Diretor Estrategico do Municipio',
                 grupo('planmob')), False)
    t('tarifa zero pega Sorocaba',
      casa_grupo('Institui a Tarifa Zero no transporte publico coletivo municipal',
                 grupo('tarifa zero')), True)
    # --- veredito com esgotamento (10/09/2026) ---
    t('esgotado: paginou ate o fim e o servidor deu menos',
      veredito(50, '5287', 'sim', esgotou=True), 'esgotado')
    t('parcial: ficou curto SEM esgotar (limite nosso)',
      veredito(50, '5287', 'sim', esgotou=False), 'parcial')
    t('esgotamento nao transforma colheita completa em esgotada',
      veredito(5287, '5287', 'sim', esgotou=True), 'sim')
    t('esgotamento nao mexe em quem falhou por rede',
      veredito(0, '5287', 'nao', esgotou=True), 'nao')

    # --- janela de anos do fatiamento (3a passada) ---
    _hoje = int(time.strftime('%Y'))
    class _A:
        ano_inicial = 1960
    t('anos: janela padrao vai de 1960 ao ano corrente',
      (_anos_do_host([], _A)[0], _anos_do_host([], _A)[-1]), (1960, _hoje))
    t('anos: norma antiga puxa o inicio para tras',
      _anos_do_host([{'ano': 1948}], _A)[0], 1948)
    t('anos: norma recente NAO empurra o inicio para frente',
      _anos_do_host([{'ano': 2024}], _A)[0], 1960)
    t('anos: ano invalido nao quebra a janela',
      _anos_do_host([{'ano': None}, {'ano': 'sem data'}, {'ano': '12'}], _A)[0], 1960)
    t('anos: ano como texto com data completa e aceito',
      _anos_do_host([{'ano': '1955-03-02'}], _A)[0], 1955)

    # --- veredito de colheita: 'sim' so quando bate com o esperado ---
    t('veredito: colheita completa', veredito(5287, '5287', 'sim'), 'sim')
    t('veredito: Paraguacu Paulista (50 de 5287) e parcial',
      veredito(50, '5287', 'sim'), 'parcial')
    t('veredito: Canoinhas (9484 de 11034) e parcial',
      veredito(9484, '11034', 'sim'), 'parcial')
    t('veredito: falta pequena segue completa (9278 de 9318)',
      veredito(9278, '9318', 'sim'), 'sim')
    t('veredito: falta de 40 em base pequena segue completa',
      veredito(921, '961', 'sim'), 'sim')
    t('veredito: sem esperado, nao inventa', veredito(10, '', 'sim'), 'sim')
    t('veredito: nao mexe em quem ja falhou', veredito(0, '5000', 'nao'), 'nao')
    t('veredito: colher mais que o esperado nao e parcial',
      veredito(5300, '5287', 'sim'), 'sim')

    # --- falsos positivos medidos na varredura de 10/09/2026 ---
    t('gratuidade NAO pega tarifa de agua e esgoto',
      casa_grupo('AUTORIZA O SAAE A CONCEDER ISENCAO DE TARIFA DE AGUA E ESGOTO',
                 grupo('gratuidade')), False)
    t('gratuidade NAO pega tarifa de matanca de gado',
      casa_grupo('Concede isencao de tarifa de matanca de gado e da outras providencias',
                 grupo('gratuidade')), False)
    t('gratuidade pega isencao com o objeto transporte',
      casa_grupo('Dispoe sobre isencao de tarifa de transporte coletivo urbano',
                 grupo('gratuidade')), True)
    t('grupo amplo ainda pega as isencoes soltas (para revisao)',
      casa_grupo('Concede isencao de tarifa de matanca de gado',
                 grupo('gratuito (amplo, revisar)')), True)

    # --- prioridade EXCLUSIVA (--so-prioridade) ---
    _lista2 = [{'cod_ibge': '1'}, {'cod_ibge': '3106200'}, {'cod_ibge': '2'}]
    import tempfile as _tf2
    _pc2 = os.path.join(_tf2.mkdtemp(), 'p.csv')
    _w2 = open(_pc2, 'w', encoding='utf-8', newline='')
    _w2.write('cod_ibge\n3106200\n'); _w2.close()
    t('so-prioridade descarta o resto',
      [x['cod_ibge'] for x in _prioridade(list(_lista2), _pc2, so=True)], ['3106200'])
    t('sem so-prioridade mantem tudo',
      len(_prioridade(list(_lista2), _pc2, so=False)), 3)
    # --- sonda de page_size: so adota se a pagina cresceu ---
    class _H:
        def __init__(self, tam): self.tam = tam
        def get_json(self, url):
            n = self.tam if 'page_size' in url else 10
            return {'results': [{'numero': i} for i in range(n)],
                    'pagination': {}}, None
    t('page_size adotado quando cresce', _sonda_page_size(_H(200), 'h', '/api/', 10)[0], 200)
    t('page_size recusado quando ignorado', _sonda_page_size(_H(10), 'h', '/api/', 10)[0], 0)

    # --- prioridade: promove sem perder ninguem ---
    import tempfile as _tf
    _d = _tf.mkdtemp()
    _pc = os.path.join(_d, 'prio.csv')
    io_w = open(_pc, 'w', encoding='utf-8', newline='')
    io_w.write('cod_ibge,municipio\n3552205,Sorocaba\n3106200,Belo Horizonte\n')
    io_w.close()
    _lista = [{'cod_ibge': '1'}, {'cod_ibge': '3106200'}, {'cod_ibge': '2'},
              {'cod_ibge': '3552205'}, {'cod_ibge': '3'}]
    _ord = _prioridade(list(_lista), _pc)
    t('prioridade promove os dois ao inicio',
      [x['cod_ibge'] for x in _ord][:2], ['3106200', '3552205'])
    t('prioridade nao perde ninguem', sorted(x['cod_ibge'] for x in _ord),
      sorted(x['cod_ibge'] for x in _lista))
    t('prioridade preserva a ordem do resto',
      [x['cod_ibge'] for x in _ord][2:], ['1', '2', '3'])
    t('sem arquivo de prioridade, lista intacta',
      [x['cod_ibge'] for x in _prioridade(list(_lista), '')],
      [x['cod_ibge'] for x in _lista])

    t('flex de* aceita do', contem_frase('fundo municipal do transporte publico',
                                        'fundo municipal de* transporte'), True)
    t('flex de* aceita de', contem_frase('fundo municipal de transporte coletivo',
                                         'fundo municipal de* transporte'), True)
    t('flex de* NAO vira coringa', contem_frase('fundo municipal para transporte',
                                                'fundo municipal de* transporte'), False)
    t('flex nao afrouxa o resto', contem_frase('fundo do transporte publico',
                                               'fundo municipal de* transporte'), False)
    t('sem asterisco segue rigido', contem_frase('fundo municipal do transporte',
                                                 'fundo municipal de transporte'), False)
    print('\nautoteste: %d ok, %d falhas' % (ok, fail))
    if fail:
        print('\n⚠️  Falhas acima indicam termo que precisa de outra alternativa no grupo.')
    return 0 if fail == 0 else 1

# ------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description='Varredura das APIs SAPL das câmaras municipais.')
    ap.add_argument('fase', choices=['municipios', 'descobrir', 'buscar',
                                 'corpus', 'filtrar', 'autoteste'])
    ap.add_argument('--saida', default='saida_sapl')
    ap.add_argument('--municipios', default='')
    ap.add_argument('--uf', nargs='*', default=[])
    ap.add_argument('--termos', nargs='*', default=None)
    ap.add_argument('--termos-arquivo', default='')
    ap.add_argument('--delay', type=float, default=1.0)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--timeout', type=int, default=20)
    ap.add_argument('--max-paginas', type=int, default=20)
    ap.add_argument('--varrer-tudo', action='store_true',
                    help='se o host nao tem busca textual, pagina tudo e filtra local (caro)')
    ap.add_argument('--sem-fatiar-ano', action='store_true',
                    help='nao tentar a 3a passada (consulta ano a ano) nos hosts '
                         'que voltarem parciais')
    ap.add_argument('--ano-inicial', type=int, default=1960,
                    help='primeiro ano do fatiamento por ano (padrão 1960)')
    ap.add_argument('--vazios', choices=['pular', 'tentar'], default='pular',
                    help='hosts que a descoberta viu com 0 normas: pular '
                         '(padrão) ou tentar de novo')
    ap.add_argument('--sem-dedup', action='store_true',
                    help='nao descarta linha repetida do corpus (host refeito) '
                         'ao filtrar — use so para auditar a repeticao')
    ap.add_argument('--sem-page-size', action='store_true',
                    help='nao sondar ?page_size (use se algum SAPL devolver '
                         'resultado inconsistente com a pagina grande)')
    ap.add_argument('--so-prioridade', action='store_true',
                    help='com --prioridade: roda SÓ esses municípios, em vez de '
                         'apenas promovê-los ao início da fila')
    ap.add_argument('--prioridade', default='',
                    help='CSV com coluna cod_ibge; esses municípios vão para o '
                         'início da fila (use a lista dos casos de Tarifa Zero)')
    ap.add_argument('--contato', default='', help='e-mail no User-Agent (boa prática)')
    a = ap.parse_args()

    if a.fase == 'autoteste':
        sys.exit(autoteste())

    os.makedirs(a.saida, exist_ok=True)
    ua = 'sapl_varredura/%s (pesquisa academica UFABC - Tarifa Zero%s)' % (
        VERSAO, '; ' + a.contato if a.contato else '')
    http = Http(ua, delay=a.delay, timeout=a.timeout)

    if a.termos_arquivo:
        a.termos = [l.strip() for l in open(a.termos_arquivo, encoding='utf-8')
                    if l.strip() and not l.startswith('#')]
    elif a.termos is None:
        a.termos = list(TERMOS_PADRAO)

    lista = a.municipios or os.path.join(a.saida, 'sapl_municipios.csv')
    if a.fase == 'municipios':
        baixar_municipios(http, lista); return
    if a.fase in ('filtrar', 'corpus', 'buscar'):
        # Estas fases partem do sapl_hosts.csv, nao da lista de municipios:
        # exigir a lista era defeito — quebrava com "Rode primeiro: municipios"
        # depois de um 'descobrir' que rodou com --municipios apontando para
        # outro arquivo. (Corrigido em 10/09/2026.)
        {'filtrar': filtrar, 'corpus': corpus, 'buscar': buscar}[a.fase](a, http, [])
        return
    muns = ler_municipios(lista)
    if a.uf:
        muns = [m for m in muns if m['uf'] in a.uf]
        print('filtro de UF: %s -> %d municípios' % (','.join(a.uf), len(muns)))
    # aqui so chega 'descobrir': as outras fases retornaram acima
    descobrir(a, http, muns)

if __name__ == '__main__':
    main()
