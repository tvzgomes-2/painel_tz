# -*- coding: utf-8 -*-
"""Testes de integracao da colheita do sapl_varredura.py.

Servidor FALSO, sem rede: reproduz os tres modos de falha medidos na varredura
nacional de 10/09/2026 e prova que a colheita se recompoe em cada um.
  1. 'next' nulo em toda pagina  — o defeito de Paraguacu Paulista/SP (50 de 5.287)
  2. total_entries maior que o que a API serve — deve sair 'esgotado', nao 'sim'
  3. corte de paginacao — o fatiamento por ano deve recompor a base

Rodar:  python3 teste_sapl_colheita.py     (sai 1 se algo falhar)

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof. Dra. Silvana Zioni
"""
import os, sys, types, urllib.parse as up
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sapl_varredura as S

def args_padrao(**kw):
    a = types.SimpleNamespace(
        delay=0.0, timeout=5, max_paginas=2000, sem_page_size=False,
        sem_fatiar_ano=False, ano_inicial=1960, saida='/tmp')
    for k, v in kw.items():
        setattr(a, k, v)
    return a

def norma(i, ano):
    return dict(tipo='Lei', numero=str(i), ano=ano, data='%d-01-01' % ano,
                ementa='Norma %d de %d' % (i, ano), texto_integral='')

class Servidor(object):
    """Base: N normas distribuidas em anos, paginacao de 10."""
    def __init__(self, total, declara=None, ano_ini=1960, honra_ps=True,
                 manda_next=True, aceita_ano=True, teto_pagina=None,
                 serve_no_maximo=None, drf_404=False, erro_na_pagina1=None):
        self.total, self.declara = total, declara if declara is not None else total
        self.honra_ps, self.manda_next = honra_ps, manda_next
        self.aceita_ano, self.teto_pagina = aceita_ano, teto_pagina
        self.serve_no_maximo = serve_no_maximo
        self.drf_404 = drf_404
        self.erro_na_pagina1 = erro_na_pagina1
        anos = list(range(ano_ini, ano_ini + 67))
        self.itens = [norma(i, anos[i % len(anos)]) for i in range(total)]
        self.chamadas = 0

    def get_json(self, url, *a, **k):
        self.chamadas += 1
        q = up.parse_qs(up.urlparse(url).query)
        pag = int(q.get('page', ['1'])[0])
        if self.erro_na_pagina1 and pag == 1:
            return None, self.erro_na_pagina1
        ps = int(q.get('page_size', ['10'])[0]) if self.honra_ps else 10
        pool = self.itens
        if self.serve_no_maximo is not None:
            pool = pool[:self.serve_no_maximo]   # teto da BASE servida
        if 'ano' in q:
            if not self.aceita_ano:
                return {'detail': 'nao'}, ''
            pool = [x for x in pool if str(x['ano']) == q['ano'][0]]
        if self.teto_pagina and pag > self.teto_pagina:
            pag = self.teto_pagina          # repete a ultima: novos == 0
        ini = (pag - 1) * ps
        if self.drf_404 and ini >= len(pool) and pag > 1:
            return None, 'HTTP 404'         # DRF: "Invalid page"
        fatia = pool[ini:ini + ps]
        prox = None
        if self.manda_next and ini + ps < len(pool):
            prox = 'https://x/?page=%d' % (pag + 1)
        return {'pagination': {'total_entries': len(pool)},
                'results': fatia, 'next': prox}, ''

def roda(srv, **kw):
    S.Http.get_json = lambda self, url, *a, **k: srv.get_json(url)
    h = dict(cod_ibge='3500000', municipio='Teste', uf='SP',
             host='teste.sp.leg.br', endpoint='/api/norma/normajuridica/',
             total_normas=str(srv.declara))
    reg, linhas, ps = S._colhe_host(h, args_padrao(**kw), 'ua/teste')
    return reg, linhas

falhas = []
def caso(nome, reg, linhas, normas_esperadas, completo_esperado):
    ok = (len(linhas) == normas_esperadas and reg['completo'] == completo_esperado)
    print('%-4s %-52s normas=%d (esperado %d) · completo=%s (esperado %s)'
          % ('OK' if ok else 'FALHA', nome, len(linhas), normas_esperadas,
             reg['completo'], completo_esperado))
    if not ok:
        falhas.append(nome)
        if reg['erro']:
            print('       erro: %s' % reg['erro'][:160])

# 1. O DEFEITO CORRIGIDO: 'next' nulo em toda pagina.
caso('next nulo em toda pagina (o defeito de Paraguacu)',
     *roda(Servidor(5287, manda_next=False)), normas_esperadas=5287,
     completo_esperado='sim')

# 2. Servidor normal, com 'next' — nao pode regredir.
caso('servidor normal com next',
     *roda(Servidor(5287)), normas_esperadas=5287, completo_esperado='sim')

# 3. total_entries MAIOR que o que a API serve: esgotado, nao parcial.
caso('total declarado errado (serve 50, declara 5287)',
     *roda(Servidor(5287, serve_no_maximo=50, manda_next=False)),
     normas_esperadas=50, completo_esperado='esgotado')

# 4. Corte de paginacao com filtro por ano funcionando: fatiamento recompoe.
caso('corta na pagina 1 mas aceita ?ano (fatiamento)',
     *roda(Servidor(670, teto_pagina=1, manda_next=False)),
     normas_esperadas=670, completo_esperado='sim')

# 5. Corte de paginacao E sem filtro por ano: fica esgotado, com erro explicito.
reg, linhas = roda(Servidor(5287, teto_pagina=1, manda_next=False, aceita_ano=False))
caso('corta na pagina 1 e nao aceita ?ano', reg, linhas,
     normas_esperadas=200, completo_esperado='esgotado')   # 1 pagina de 200

# 6. --max-paginas apertado: e limite NOSSO, entao 'parcial' (refaz).
caso('limite nosso de paginas (--max-paginas=3)',
     *roda(Servidor(5287, manda_next=False, aceita_ano=False), max_paginas=3),
     normas_esperadas=600, completo_esperado='parcial')   # 3 x 200

# 7. DRF responde 404 a pagina alem da ultima: e o FIM, nao falha de rede.
caso('404 na pagina alem da ultima (DRF) e o fim da colecao',
     *roda(Servidor(5287, manda_next=False, drf_404=True)),
     normas_esperadas=5287, completo_esperado='sim')

# 8. 404 + total declarado maior do que a API serve: esgotado, nao 'nao'.
caso('404 no fim e total declarado maior (Rio Bonito/Ibirajuba)',
     *roda(Servidor(5287, serve_no_maximo=902, manda_next=False, drf_404=True,
                    aceita_ano=False)),
     normas_esperadas=902, completo_esperado='esgotado')

# 9. 404 JA NA PAGINA 1 continua sendo erro (endpoint errado), nunca 'esgotado'.
caso('404 na pagina 1 continua erro',
     *roda(Servidor(5287, manda_next=False, aceita_ano=False,
                    erro_na_pagina1='HTTP 404')),
     normas_esperadas=0, completo_esperado='nao')

# 9b. Pagina 1 vazia com total declarado alto: e falta DO SERVIDOR (esgotado).
caso('pagina 1 vazia e total declarado alto',
     *roda(Servidor(5287, serve_no_maximo=0, manda_next=False, aceita_ano=False)),
     normas_esperadas=0, completo_esperado='esgotado')

# 10. DEDUPLICACAO NO FILTRO: host refeito apenda linhas: o achado nao pode dobrar.
def teste_dedup():
    import csv, tempfile, os as _os
    d = tempfile.mkdtemp()
    corp = _os.path.join(d, 'sapl_corpus.csv')
    with io.open(corp, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=S.COLS_COR)
        w.writeheader()
        linha = dict.fromkeys(S.COLS_COR, '')
        linha.update(cod_ibge='3500000', municipio='Teste', uf='SP',
                     host='teste.sp.leg.br', endpoint='/api/norma/normajuridica/',
                     tipo='Lei', numero='123', ano='2024',
                     ementa='Institui a Tarifa Zero no municipio.')
        w.writerow(linha); w.writerow(linha)      # host recolhido duas vezes
    a = args_padrao(saida=d, termos=['tarifa zero'], sem_dedup=False)
    S.filtrar(a, None, None)
    ach = list(csv.DictReader(io.open(_os.path.join(d, 'sapl_achados.csv'),
                                      encoding='utf-8-sig')))
    ok = len(ach) == 1
    print('%-4s %-52s achados=%d (esperado 1)'
          % ('OK' if ok else 'FALHA', 'linha repetida nao dobra o achado', len(ach)))
    if not ok:
        falhas.append('dedup no filtro')

import io
print()
teste_dedup()

print()
print('RESULTADO: %s' % ('TODOS OK' if not falhas else 'FALHOU: ' + ', '.join(falhas)))
sys.exit(1 if falhas else 0)
