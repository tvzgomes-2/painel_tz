# -*- coding: utf-8 -*-
"""
build_curva_porte.py — gera scripts/curva_porte.json: a adoção da Tarifa Zero universal
por faixa de porte, entre TODOS os municípios e entre os que têm INDÍCIO DE SISTEMA de
ônibus (item 12.9 do ROADMAP; Gráfico 14 e Seção 5.4 da tese).

Por que existe: a Tarifa Zero pressupõe um serviço, e o denominador certo não são os
5.570 municípios, mas os que têm sistema. Com esse denominador a forma da adoção por porte
muda: em vez de crescer com o porte, desenha um U invertido, com pico na faixa de 20 a 50
mil habitantes e ZERO acima de 500 mil — o achado mais forte do Capítulo 5, que o painel
não mostrava em lugar nenhum.

O índice (0 a 12 pontos, corte em 5) é o da "Análise V" da tese, calculado pelo script
CANÔNICO do artigo em elaboração "Quem tem ônibus?" (ENANPUR 2027), que este arquivo
executa sem copiar nem alterar:
  06 - Acadêmico/Artigos/1 - Em elaboração/XXII ENANPUR 2027 — método de detecção com IA/
      indice_indicio_familia_b.py

FRONTEIRA (23/10/2026): a classificação município a município é o produto central de um
artigo AINDA INÉDITO. Por isso a saída traz só CONTAGENS AGREGADAS por faixa, nacionais —
nenhum município, nenhuma pontuação individual. O preço é que o bloco não responde aos
filtros do painel, e o painel diz isso. Se o autor liberar a classificação por município,
basta exportar o booleano para a base e trocar a contagem para o recorte.

Uso:  python3 scripts/build_curva_porte.py        (da raiz do repositório)
"""
import json
import os
import runpy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(BASE_DIR, '..', '..', 'doutorado')
SCRIPT_IDX = os.path.join(VAULT, '06 - Acadêmico', 'Artigos', '1 - Em elaboração',
                          'XXII ENANPUR 2027 — método de detecção com IA', 'indice_indicio_familia_b.py')
DIR_BASE = os.path.join(VAULT, '03 - Dados', '_data', 'Base Municipal v3')
PAINEL = os.path.join(BASE_DIR, '..', 'build', 'municipios_dados.json')
OUT = os.path.join(BASE_DIR, 'curva_porte.json')
CORTE = 5.0

FAIXAS = [('<10', 'até 10 mil', 0, 1e4), ('10-20', '10 a 20 mil', 1e4, 2e4),
          ('20-50', '20 a 50 mil', 2e4, 5e4), ('50-100', '50 a 100 mil', 5e4, 1e5),
          ('100-500', '100 a 500 mil', 1e5, 5e5), ('>500', 'mais de 500 mil', 5e5, float('inf'))]

cwd = os.getcwd()
os.chdir(DIR_BASE)                       # o script canônico lê base_municipal_v3.csv do diretório atual
try:
    g = runpy.run_path(SCRIPT_IDX, run_name='indice_para_painel')   # não executa o bloco __main__
finally:
    os.chdir(cwd)
df = g['df']
idx = {str(int(c)).zfill(7): float(v) for c, v in zip(df['cod_ibge'], df['indice_familia_b'])}

with open(PAINEL, encoding='utf-8') as f:
    base = json.load(f)

def faixa(pop):
    for k, _, a, b in FAIXAS:
        if a <= pop < b:
            return k

agg = {k: {'rot': rot, 'n': 0, 'n_sist': 0, 'tz': 0, 'tz_sist': 0} for k, rot, _, _ in FAIXAS}
sem_idx = 0
for r in base:
    k = faixa(r.get('pop') or 0)
    v = idx.get(str(r['id']).zfill(7))
    if v is None:
        sem_idx += 1
        continue
    sist = v >= CORTE
    tz = r.get('tz_status') == 'Ativa'
    a = agg[k]
    a['n'] += 1; a['n_sist'] += sist; a['tz'] += tz; a['tz_sist'] += (tz and sist)

tot = {c: sum(a[c] for a in agg.values()) for c in ('n', 'n_sist', 'tz', 'tz_sist')}
out = {'corte': CORTE, 'retrato': '21/10/2026', 'faixas': [dict(k=k, **agg[k]) for k, *_ in FAIXAS], 'total': tot}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
    f.write('\n')

print(f"curva_porte.json — municípios sem índice: {sem_idx}")
print(f"  com indício (>= {CORTE:g}): {tot['n_sist']}   | TZ universal: {tot['tz']} "
      f"| TZ com indício: {tot['tz_sist']} ({100*tot['tz_sist']/tot['n_sist']:.1f}%)")
for a in out['faixas']:
    p_all = 100 * a['tz'] / a['n'] if a['n'] else 0
    p_sis = 100 * a['tz_sist'] / a['n_sist'] if a['n_sist'] else 0
    print(f"  {a['rot']:16} todos {a['tz']:3d}/{a['n']:5d} = {p_all:4.1f}%   com sistema {a['tz_sist']:3d}/{a['n_sist']:4d} = {p_sis:4.1f}%")
