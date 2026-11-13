# Cobertura tarifária (receita tarifária ÷ receitas totais do ônibus) a partir da PEMOB 2021-2024. Rodar dentro de 03 - Dados/_data/PEMOB/. 26/09/2026. Saída bruta: há erros de unidade nas respostas (ex.: Campina Grande 2023).
import openpyxl,re,glob,csv,sys
def num(v):
    if v is None: return None
    s=str(v).strip()
    if s in ("NR","NA","","-","None"): return None
    s=re.sub(r"[R$\s]","",s)
    if "," in s and "." in s: s=s.replace(".","").replace(",",".")
    elif "," in s: s=s.replace(",",".")
    try: return float(s)
    except: return None
out=[]
for f in sorted(glob.glob("pemob_20*.xlsx"))+["Pemob2019_Municipal.xlsx","BancodeDados_PemobMunicipal_2020.xlsx"]:
    wb=openpyxl.load_workbook(f,read_only=True); ws=wb.worksheets[0]
    rows=list(ws.iter_rows(values_only=True))
    # find header rows: question row and code row
    qi=None
    for i,r in enumerate(rows[:6]):
        if any(c and re.search(r"receita tarif",str(c),re.I) for c in r): qi=i;break
    if qi is None: print(f,"sem receita tarifária"); continue
    Q=rows[qi]
    def col(pat):
        for j,c in enumerate(Q):
            if c and re.search(pat,str(c),re.I): return j
    jt=col(r"receita tarif\w* anual por [ôo]nibus"); jb=col(r"benef[ií]cios tarif\w* .*por [ôo]nibus"); jc=col(r"subven[cç][aã]o.*por [ôo]nibus"); jd=col(r"publicidade.*por [ôo]nibus"); je=col(r"outras fontes.*por [ôo]nibus")
    jtar=col(r"valor da atual tarifa predominante")
    # data start: first row whose first cell looks like IBGE code
    for r in rows[qi+1:]:
        if not r or not r[0] or not re.match(r"^\d{7}$",str(r[0]).strip()): continue
        t=num(r[jt]) if jt is not None else None
        ex=[num(r[j]) if j is not None else None for j in (jb,jc,jd,je)]
        tot=(t or 0)+sum(x or 0 for x in ex)
        cob=(t/tot) if (t is not None and tot>0) else None
        out.append([f,r[0],r[1],r[2],t]+ex+[cob, num(r[jtar]) if jtar is not None else None])
    print(f,len(Q),"cols",jt,jb,jc,jd,je,jtar)
w=csv.writer(open("cobertura_tarifaria_pemob_2021-2024 (bruto, 26-09-2026).csv","w",newline=""))
w.writerow(["arquivo","ibge","uf","mun","rec_tar","sub_benef","subvencao","public","outras","cobertura","tarifa"]); w.writerows(out)
print(len(out))
