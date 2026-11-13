# -*- coding: utf-8 -*-
"""auditar_notas_normas.py (06/11/2026) — confere se cada ato municipal em normas/<UF>/ tem nota em "Normas padronizadas" (por município e número).
Ignora os arquivos estaduais e federais (prefixo "UF - "). Lista os arquivos sem número de ato reconhecido (candidatos a capturas/). Uso (da raiz): python _meta/scripts/auditar_notas_normas.py"""
import os, re, unicodedata, collections
R=os.getcwd(); N=os.path.join(R,"03 - Dados/_data/Legislacao e contratos TZ/normas"); P=os.path.join(R,"04 - Análises/Pesquisa legal/Normas padronizadas")
def sa(s): return unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()
def nn(s): return re.sub(r"\D","",s or "").lstrip("0")
notas=collections.defaultdict(set); notafile={}
for f in os.listdir(P):
    if not f.endswith(".md") or f.startswith("_"): continue
    t=open(os.path.join(P,f),encoding="utf-8").read(3000)
    m=re.search(r'^municipio:\s*"?([^"\n]+)',t,re.M); n=re.search(r'^numero:\s*"?([^"\n]+)',t,re.M)
    if m and n: notas[re.sub(r"[^a-z]","",sa(m.group(1)))].add(nn(n.group(1).split("/")[0]))
TIPO=r"(?:Lei Complementar|LC|EMC|Emenda[^\d]{0,30}|Lei Org[aâ]nica|Lei Ordin[aá]ria|Lei|Decreto(?: Legislativo)?|Portaria|Resolu[cç][aã]o|Medida Provis[oó]ria|Instru[cç][aã]o Normativa)"
NUM=re.compile(TIPO+r"\s*(?:n[ºo°.]*\s*)?([\d][\d\.]*)\s*(?:[-/]\s*(\d{2,4})|,\s*de\s+\d{1,2}\s+de\s+\w+\s+de\s+(\d{4}))",re.I)
atos=collections.OrderedDict(); estad=0; outros=[]
for uf in sorted(os.listdir(N)):
    d=os.path.join(N,uf)
    if not os.path.isdir(d): continue
    for f in sorted(os.listdir(d)):
        if re.match(r"[A-Z]{2} - ",f): estad+=1; continue          # estadual/federal: aba Nacionais e estaduais
        mm=re.match(r"(.+?)-([A-Z]{2}) [-—] (.+)$",f)
        if not mm: outros.append((uf,f)); continue
        mun,u,rest=mm.groups(); mu=re.sub(r"[^a-z]","",sa(mun))
        m2=NUM.search(rest)
        if not m2: outros.append((uf,f)); continue
        key=(mun,u,nn(m2.group(1)),m2.group(2) or m2.group(3))
        atos.setdefault(key,[]).append(f)
falta=[]
for (mun,u,n,a),fs in atos.items():
    mu=re.sub(r"[^a-z]","",sa(mun)); ks=[k for k in notas if k==mu or k.startswith(mu) or mu.startswith(k)]
    if not any(n in notas[k] for k in ks): falta.append((u,mun,n,a,fs[0]))
print(f"arquivos estaduais/federais (fora): {estad} · atos municipais distintos: {len(atos)} · com nota: {len(atos)-len(falta)} · SEM nota: {len(falta)} · arquivos sem número de ato reconhecido: {len(outros)}")
for x in falta: print(" SEM NOTA:",x[0],x[1],"| nº",x[2],x[3],"|",x[4][:120])
for x in outros: print(" ? :",x[0],"|",x[1][:130])
