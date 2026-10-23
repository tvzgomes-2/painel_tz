# -*- coding: utf-8 -*-
"""
aplicar_rsl_8_9.py — fecha as pendências 8.9(c) e 8.9(d) do ROADMAP a partir do anexo da
revisão sistemática (pacote 6 da tese, "06 Revisão sistemática da literatura.xlsx"), como
o autor indicou em 23/10/2026 ("para ambos precisamos olhar os anexos de RSL").

(d) NTU "2023" × "2024". O corpus da RSL registra um só item — NTU (2024), "Tarifa zero
    nas cidades do Brasil" (1ª ed.) —, com "ntu2023" entre as chaves alternativas; a lista
    de referências da tese o data de abril de 2024. As entradas "NTU 2023" do crosswalk são
    essa publicação e passam a "NTU 2024".
(c) Cardozo et al. (2024; 2025). Os artigos analisam 106 e 44 experiências mas só NOMEIAM
    algumas; a lista que existe é a do índice da RSL (aba municipios_na_literatura), que
    registra os municípios nomeados em cada fichamento. Entram os que estão na base-mestre
    (Ouro Preto/MG é citado, mas não é caso de Tarifa Zero da base, e fica fora). As
    descrições vêm das fichas municipais (Apêndice D), não do resumo dos artigos.

Idempotente: rodar de novo não duplica entradas. Uso: python3 scripts/aplicar_rsl_8_9.py
"""
import json, os, io
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'casos_por_fonte.json')
cw = json.load(io.open(P, encoding='utf-8'))

ren = 0
for v in cw.values():
    for e in v:
        if e.get('fonte') == 'NTU 2023':
            e['fonte'] = 'NTU 2024'; ren += 1

C24 = 'análise exploratória nacional de 106 experiências (ANPET 38)'
C25 = 'entre as 44 experiências analisadas quanto aos impactos na motorização (ANPET 39)'
NOVAS = [
    ('Bombinhas|SC', 'Cardozo et al. 2024', f'adesão por licitação infrutífera para a concessão — gratuidade como solução residual; {C24}'),
    ('Paracambi|RJ', 'Cardozo et al. 2024', f'adesão por licitação infrutífera para a concessão — gratuidade como solução residual; {C24}'),
    ('Conchas|SP', 'Cardozo et al. 2024', f'registrado como a primeira experiência de Tarifa Zero identificada na literatura, com início em 1992; {C24}'),
    ('Jales|SP', 'Cardozo et al. 2024', f'demanda multiplicada por cinco após a gratuidade; {C24}'),
    ('Vargem Grande Paulista|SP', 'Cardozo et al. 2024', f'taxa cobrada das empresas cobria cerca de 70% do custo em 2022 e foi declarada inconstitucional em 2023; {C24}'),
    ('Formosa|GO', 'Cardozo et al. 2024', f'fundo municipal específico criado pela Lei 650/2021 (art. 11); {C24}'),
    ('Caucaia|CE', 'Cardozo et al. 2024', f'caso citado na {C24}'),
    ('Mariana|MG', 'Cardozo et al. 2024', f'caso citado na {C24}'),
    ('Maricá|RJ', 'Cardozo et al. 2024', f'caso citado na {C24}'),
    ('Caucaia|CE', 'Cardozo et al. 2025', f'citado {C25}'),
    ('Formosa|GO', 'Cardozo et al. 2025', f'citado {C25}'),
    ('Mariana|MG', 'Cardozo et al. 2025', f'citado {C25}'),
    ('Maricá|RJ', 'Cardozo et al. 2025', f'citado {C25}'),
    ('Paranaguá|PR', 'Cardozo et al. 2025', f'citado {C25}'),
]
add = 0
for chave, fonte, desc in NOVAS:
    lst = cw.setdefault(chave, [])
    if any(e.get('fonte') == fonte for e in lst):
        continue
    lst.append({'fonte': fonte, 'tipo': 'Estudo acadêmico', 'descricao': desc, 'ano': None, 'link': None})
    add += 1
cw = {k: cw[k] for k in sorted(cw)}
io.open(P, 'w', encoding='utf-8').write(json.dumps(cw, ensure_ascii=False, indent=1) + '\n')
print(f'NTU 2023 -> NTU 2024: {ren} entradas | Cardozo et al.: {add} entradas novas | municípios no crosswalk: {len(cw)}')
