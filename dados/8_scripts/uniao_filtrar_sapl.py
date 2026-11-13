#!/usr/bin/env python3
"""Reaplica os grupos de termos da filtrar() do sapl_varredura.py sobre a
UNIAO de dois corpus.csv (o antigo saida_sapl/ e o recrawl saida_sapl_recrawl_*/),
sem nunca materializar um arquivo unido em disco -- streaming dos dois arquivos
em sequencia, com a MESMA dedup por (host,tipo,numero,ano) que a filtrar() usa.

Motivo: o recrawl feito hoje coletou MENOS normas que o corpus antigo em varios
hosts grandes (Campinas -46%, Canoinhas -81%, Fortaleza, Joao Pessoa, Erechim,
Paraguacu Paulista, Rio Bonito do Iguacu -- todos com o mesmo padrao
'fatiado por ano' e ainda assim abaixo do 'esperado', marcados 'esgotado' e
portanto terminais/nao re-tentados). O corpus antigo, apesar de ter sido
escrito por varias rodadas de corpus() ao longo de 10 dias (e por isso conter
duplicatas), parece ter uma cobertura efetiva MAIOR nesses hosts via uniao de
passadas parciais diferentes. Este script testa se a uniao dedupada recupera
essa cobertura.

Uso:
    python3 uniao_filtrar_sapl.py <pasta_scripts> <corpus_antigo.csv> <corpus_novo.csv> <saida.csv>
"""
import sys, os, csv
from collections import Counter

def main():
    pasta_scripts, corp_antigo, corp_novo, saida = sys.argv[1:5]
    os.makedirs(os.path.dirname(saida) or '.', exist_ok=True)
    sys.path.insert(0, pasta_scripts)
    import sapl_varredura as sv

    grupos = [sv.parse_grupo(t) for t in sv.TERMOS_PADRAO]
    print('grupos:', [g[0] for g in grupos])

    vistas = set()
    conta = Counter()
    lidas = repetidas = casadas = 0

    f = open(saida, 'w', encoding='utf-8-sig', newline='')
    w = csv.DictWriter(f, fieldnames=sv.COLS_ACH)
    w.writeheader()

    for origem, caminho in (('antigo', corp_antigo), ('novo', corp_novo)):
        n_arquivo = 0
        with open(caminho, encoding='utf-8-sig') as fh:
            for r in csv.DictReader(fh):
                lidas += 1
                n_arquivo += 1
                chave = '|'.join((r.get('host') or '', str(r.get('tipo') or ''),
                                   str(r.get('numero') or ''), str(r.get('ano') or '')))
                if chave in vistas:
                    repetidas += 1
                    continue
                vistas.add(chave)
                txt = (r.get('ementa') or '') + ' ' + (r.get('texto') or '')
                tn = sv.norm(txt)
                en = sv.norm(r.get('ementa', ''))
                bateu = False
                for rotulo, alts in grupos:
                    casou = next((a for a in alts if sv.contem_frase_norm(tn, a)), None)
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
                        campo_casado=('ementa' if sv.contem_frase_norm(en, casou) else 'outro campo'),
                        colhido_em=r.get('colhido_em', '')))
                if bateu:
                    casadas += 1
        print(f'  {origem}: {n_arquivo} linhas lidas de {caminho}')
    f.close()

    print(f'\n{lidas} normas lidas ({len(vistas)} unicas apos dedup por host,tipo,numero,ano) '
          f'· {repetidas} repetidas descartadas · {casadas} casaram ao menos um grupo')
    for rot, _ in grupos:
        print('  %-22s %6d' % (rot, conta[rot]))
    print('gravado:', saida)

if __name__ == '__main__':
    main()
