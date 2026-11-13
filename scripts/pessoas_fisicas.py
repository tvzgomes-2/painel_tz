# -*- coding: utf-8 -*-
"""
pessoas_fisicas.py — localiza nomes de sócios pessoas físicas num texto (13/11/2026, v0.16).

Regra do site: nenhum nome de sócio pessoa física nem CPF. A razão social das empresas e o
nome de mercado dos grupos podem ficar (marca e dado público).

A lista de nomes vem do quadro de sócios da Receita Federal recortado pela pesquisa
(`socios_filtrado_6cnaes.csv`, no cofre — fora do repositório, porque é o próprio dado
pessoal) e, quando existem, dos sócios da segunda camada usados na aba Além do ônibus.
A busca é por nome completo, palavra a palavra, sem acento e sem caixa: "Eliana Martins
Pinto Santoni" casa com ELIANA MARTINS PINTO SANTONI; um sobrenome solto não casa.

Uso como módulo:   from pessoas_fisicas import nomes_pf, achar, mascarar
Uso como varredura: python3 scripts/pessoas_fisicas.py painel.html rede-ge.html ...
"""
import csv, os, re, sys, unicodedata

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(BASE_DIR, '..', '..', 'doutorado')
CNPJ = os.path.join(VAULT, '03 - Dados', '_data', 'CNPJ')
FONTES = [os.path.join(CNPJ, 'filtrados (6 CNAEs transporte, 24-07-2026)', 'socios_filtrado_6cnaes.csv')]
for nome in ('socios_segunda_camada.csv', 'socios_empresas_nivel2b_bruto.csv'):
    for raiz, _, arqs in os.walk(CNPJ):
        if nome in arqs:
            FONTES.append(os.path.join(raiz, nome)); break
MIN_PALAVRAS = 3          # nome completo; "JOAO SILVA" sozinho não basta para afirmar que é a pessoa
RE_PAL = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+")
_NOMES = None


def norm(s):
    s = unicodedata.normalize('NFD', str(s))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').upper()


def nomes_pf():
    """Conjunto de nomes de sócios PF, cada um como tupla de palavras normalizadas."""
    global _NOMES
    if _NOMES is not None:
        return _NOMES
    _NOMES = set()
    for f in FONTES:
        if not os.path.exists(f):
            continue
        with open(f, encoding='utf-8-sig', newline='') as fh:
            for r in csv.DictReader(fh):
                tipo = (r.get('tipo_socio') or '').strip().upper()
                nome = r.get('nome_socio_ou_razao_social') or r.get('nome_socio') or ''
                if tipo and tipo != 'PF':
                    continue
                t = tuple(RE_PAL.findall(norm(nome)))
                if len(t) >= MIN_PALAVRAS:
                    _NOMES.add(t)
    if not _NOMES:
        raise SystemExit('ERRO: lista de sócios pessoas físicas não encontrada — sem ela não há como garantir o filtro.')
    return _NOMES


def achar(texto):
    """[(início, fim, nome)] de cada nome completo de sócio PF no texto."""
    nomes = nomes_pf()
    maxn = max(len(t) for t in nomes)
    pals = [(m.start(), m.end(), norm(m.group(0))) for m in RE_PAL.finditer(texto)]
    out, i = [], 0
    while i < len(pals):
        hit = None
        for n in range(min(maxn, len(pals) - i), MIN_PALAVRAS - 1, -1):
            if tuple(p[2] for p in pals[i:i + n]) in nomes:
                hit = n; break
        if hit:
            out.append((pals[i][0], pals[i + hit - 1][1], texto[pals[i][0]:pals[i + hit - 1][1]]))
            i += hit
        else:
            i += 1
    return out


# O nome que é parte da razão social de uma empresa ("Fulano de Tal Transportes Ltda") ou do
# nome de mercado de um grupo ("Grupo Fulano") é marca e dado público e fica (regra do site).
RE_DEPOIS = re.compile(r"^\W{0,3}(&|LTDA|ME\b|EIRELI|EPP\b|S\.?/?A\b|TRANSPORTES?\b|TURISMO\b|COM[EÉ]RCIO\b|"
                       r"SERVI[CÇ]OS\b|EMPREENDIMENTOS\b|PARTICIPA[CÇ]|VIA[CÇ][AÃ]O\b|EXPRESSO\b)", re.I)
RE_ANTES = re.compile(r"(GRUPO|FAM[IÍ]LIA)\W{0,3}$", re.I)
RE_MERCADO = re.compile(r'"(mercado|nome)":"$')     # campo de nome de mercado da Rede de empresas


def contexto(texto, a, b):
    """'razão social', 'nome de mercado' ou 'pessoa'."""
    if RE_DEPOIS.match(texto[b:b + 30]):
        return 'razão social'
    if RE_ANTES.search(texto[max(0, a - 12):a]) or RE_MERCADO.search(texto[max(0, a - 12):a]):
        return 'nome de mercado'
    return 'pessoa'


def mascarar(texto, troca='[pessoa física]'):
    """Troca cada nome de sócio PF que não seja razão social nem nome de mercado por `troca`;
    devolve (texto, [nomes trocados])."""
    hits = [h for h in achar(texto) if contexto(texto, h[0], h[1]) == 'pessoa']
    for a, b, _ in reversed(hits):
        texto = texto[:a] + troca + texto[b:]
    return texto, [h[2] for h in hits]


if __name__ == '__main__':
    print(f'{len(nomes_pf()):,} nomes de sócios PF ({len(FONTES)} arquivo(s) de origem)')
    total = 0
    for arq in sys.argv[1:]:
        txt = open(arq, encoding='utf-8').read()
        hits = achar(txt)
        total += len(hits)
        print(f'{arq}: {len(hits)} ocorrência(s)')
        pessoas = 0
        for a, b, n in hits:
            c = contexto(txt, a, b)
            pessoas += c == 'pessoa'
            print(f'   {c:15s} {n!r}  …{txt[max(0, a - 60):a]}[{n}]{txt[b:b + 40]}…'.replace('\n', ' '))
        total += pessoas - len(hits)
        print(f'   → fora de razão social e nome de mercado: {pessoas}')
    sys.exit(1 if total else 0)
