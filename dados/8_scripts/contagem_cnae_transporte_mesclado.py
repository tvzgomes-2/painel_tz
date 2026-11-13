#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""contagem_cnae_transporte_mesclado.py — 01/10/2026 (Cap. 3, seção 3.5).

Conta estabelecimentos e CNPJs-base nas CNAEs em que o transporte de
passageiros se mistura: núcleo urbano (4921-3/01-02), intermunicipal
(4922-1/01-03), fretamento (4929-9/01-02), excursões/outros (4929-9/03-04,99),
escolar (4924-8/00) e saúde (8622-4/00 remoção; 8621-6/01-02 urgência).

PASSO 1 (pré-filtro textual, rodado na máquina do autor, ~37 s/GB):
  P='4921301|4921302|4922101|4922102|4922103|4929901|4929902|4929903|4929904|4929999|4924800|8622400|8621601|8621602'
  LC_ALL=C grep -a -E "$P" ESTABELECIMENTOS{i}.csv > ~/cnae/g{i}.txt   (i=1..9)
  ESTABELECIMENTOS0.csv (4 GB) em duas metades: head -c 2000000000 / tail -c +2000000001
  (a linha cortada na fronteira pode se perder: efeito de no máximo 1 registro).
PASSO 2 (este script): parse estrito das colunas 11 (CNAE principal) e 12
  (secundárias), deduplicação por CNPJ completo, ativos = situação '02'.
Validação: núcleo como CNAE principal reproduz o recorte canônico
  (48.400 estab. em qualquer situação; 14.988 ativos; 12.907 CNPJs-base).
Saídas: 03 - Dados/_data/Analises_Cap3/contagem_cnae_transporte_mesclado.{csv,json}
"""
import csv, glob, os, collections, json
G={'nucleo':{'4921301','4921302'},'intermun':{'4922101','4922102','4922103'},'fretamento':{'4929901','4929902'},
   'excursao_outros':{'4929903','4929904','4929999'},'escolar':{'4924800'},'saude_remocao':{'8622400'},'saude_urgencia':{'8621601','8621602'}}
CODES=set().union(*G.values())
fs=sorted(glob.glob(os.path.expanduser('~/cnae/g*.txt')))
seen=set()
est=collections.Counter(); estA=collections.Counter(); prin=collections.Counter(); prinA=collections.Counter()
codeA=collections.Counter(); codeAprin=collections.Counter()
base=collections.defaultdict(set)   # grupo -> cnpj_basico ativos (any)
baseprin=collections.defaultdict(set)
estAgroups=collections.Counter()  # combos of groups per active estab
anyA=set(); anyAll=0
for f in fs:
  with open(f,encoding='latin-1',errors='replace') as h:
    for r in csv.reader(h,delimiter=';'):
      if len(r)<21: continue
      key=(r[0],r[1],r[2])
      if key in seen: continue
      p=r[11].strip(); sec=set(x.strip() for x in r[12].split(',') if x.strip())
      allc=({p}|sec)&CODES
      if not allc: continue
      seen.add(key); anyAll+=1
      act = r[5].strip()=='02'
      gs=set(g for g,c in G.items() if allc&c)
      gp=set(g for g,c in G.items() if p in c)
      for g in gs:
        est[g]+=1
        if act: estA[g]+=1; base[g].add(r[0])
      for g in gp:
        prin[g]+=1
        if act: prinA[g]+=1; baseprin[g].add(r[0])
      if act:
        anyA.add(r[0]); estAgroups[tuple(sorted(gs))]+=1
        for c in allc: codeA[c]+=1
        if p in CODES: codeAprin[p]+=1
out={'estab_total':anyAll,'cnpj_base_ativos_any':len(anyA),
 'por_grupo':{g:{'estab':est[g],'estab_ativos':estA[g],'estab_principal':prin[g],'estab_ativos_principal':prinA[g],'cnpj_base_ativos':len(base[g]),'cnpj_base_ativos_principal':len(baseprin[g])} for g in G},
 'codigo_ativos':dict(codeA),'codigo_ativos_principal':dict(codeAprin)}
# overlaps with nucleo (cnpj base ativos)
n=base['nucleo']
out['nucleo_overlap_base']={g:len(n&base[g]) for g in G if g!='nucleo'}
out['nucleo_so']=len([b for b in n if all(b not in base[g] for g in G if g!='nucleo')])
nn=baseprin['nucleo']
out['nucleo_principal_base']=len(nn)
out['nucleo_principal_com_outro']={g:len(nn&base[g]) for g in G if g!='nucleo'}
out['combos_top']=[(list(k),v) for k,v in estAgroups.most_common(25)]
json.dump(out,open(os.path.expanduser('~/cnae/agg.json'),'w'),indent=1,ensure_ascii=False)
print(json.dumps(out,indent=1,ensure_ascii=False))
