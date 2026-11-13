"""MUNIC 2020 (IBGE), bloco Transporte: regime do ônibus intramunicipal (delegação × prestação direta) e
isenção formal de tarifa para 'toda a população', por faixa de população, com cruzamento com a base-mestre de TZ.
Proposta de análise para o Cap. 3 (regime de operação) e o Cap. 5 (reestimativa de TZ). 01/10/2026.
Variáveis: Mtra19 (existe ônibus intramunicipal), Mtra1911 concessão, Mtra192 concessão por licitação, Mtra1912 permissão,
Mtra1913 autorização, Mtra1914 prestação direta pela prefeitura, Mtra1915 não regulamentado, Mtra2010 isenção 'toda a população'.
As categorias de regime não são exclusivas. A MUNIC é autodeclaratória: 'toda a população' isenta é declaração, não prova de TZ (NA ≠ 0)."""
import os, csv, openpyxl
B=os.path.expanduser('~/mnt/doutorado'); D=f'{B}/03 - Dados/_data'; OUT=f'{D}/Analises_Cap3'
ws=openpyxl.load_workbook(f'{D}/MUNIC/Base_MUNIC_2020.xlsx',read_only=True)['Transporte']
rows=list(ws.iter_rows(values_only=True)); h=list(rows[0]); R=rows[1:]; ix=lambda c:h.index(c)
REG=[('concessao','Mtra1911'),('concessao_licitada','Mtra192'),('permissao','Mtra1912'),('autorizacao','Mtra1913'),('prestacao_direta','Mtra1914'),('nao_regulamentado','Mtra1915'),('isencao_toda_populacao','Mtra2010')]
FX={'1 - Até 5000':'até 20 mil','2 - 5001 até 10000':'até 20 mil','3 - 10001 até 20000':'até 20 mil','4 - 20001 até 50000':'20 a 100 mil','5 - 50001 até 100000':'20 a 100 mil','6 - 100001 até 500000':'acima de 100 mil','7 - Maior que 500000':'acima de 100 mil'}
com=[r for r in R if r[ix('Mtra19')]=='Sim']
def linha(nome,rr):
    d={'recorte':nome,'municipios_com_onibus':len(rr)}
    for k,c in REG: d[k]=sum(1 for r in rr if r[ix(c)]=='Sim')
    d['so_prestacao_direta']=sum(1 for r in rr if r[ix('Mtra1914')]=='Sim' and all(r[ix(c)]!='Sim' for c in ('Mtra1911','Mtra1912','Mtra1913','Mtra1915')))
    return d
out=[linha('Brasil',com)]+[linha(f,[r for r in com if FX[r[ix('Faixa_pop')]]==f]) for f in ('até 20 mil','20 a 100 mil','acima de 100 mil')]
# cruzamento com a base-mestre (Ativa/Encerrada, início até 2020)
b=openpyxl.load_workbook(f'{D}/casos por fonte/Municípios TZ - consolidado.xlsx',read_only=True,data_only=True).worksheets[0]
br=list(b.iter_rows(values_only=True)); bh=list(br[0]); ci,si,ai=bh.index('Código IBGE'),bh.index('Situação'),bh.index('Ano início')
tz20=set()
for r in br[1:]:
    try:
        if r[si] in ('Ativa','Encerrada') and int(str(r[ai])[:4])<=2020: tz20.add(str(int(r[ci]))[:6])
    except Exception: pass
iso={str(r[ix('CodMun')])[:6] for r in com if r[ix('Mtra2010')]=='Sim'}
iso_dir={str(r[ix('CodMun')])[:6] for r in com if r[ix('Mtra2010')]=='Sim' and r[ix('Mtra1914')]=='Sim'}
cruz={'isencao_toda_populacao_munic':len(iso),'dos_quais_prestacao_direta':len(iso_dir),'base_tz_inicio_ate_2020':len(tz20),'coincidem':len(iso&tz20),'munic_sem_registro_na_base':len(iso-tz20),'base_sem_declaracao_munic':len(tz20-iso)}
with open(f'{OUT}/munic2020_regime_por_faixa.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
with open(f'{OUT}/munic2020_isencao_x_base_tz.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['medida','n']); [w.writerow([k,v]) for k,v in cruz.items()]
for d in out: print(d)
print(cruz)
