"""Figura da Análise VIII do Cap. 3 (01/10/2026): tarifa de ônibus urbano e diesel em valores reais (R$ de 2024).
Tarifa: painel encadeado 1995-2024 (1995-2004 estimado a partir de Carvalho e Pereira, 2011; 2005-2024 painel ANTP/SIMU/PEMOB).
Diesel: ANP, Levantamento de Preços de Combustíveis, deflacionado pelo IPCA. Sem anotações de regime: a leitura por
sub-período está no Anexo A (Análise VIII). Paleta do Design System de Figuras."""
import pandas as pd, os, matplotlib as mpl
mpl.use('Agg'); import matplotlib.pyplot as plt
B=os.path.expanduser('~/mnt/doutorado'); D=f'{B}/03 - Dados/_data/Base Municipal v3'; A=f'{B}/_attachments'
ROSA,AZUL,TINTA,FRACA,GRADE='#FF2D6B','#1A54C7','#0E0E10','#5D5D64','#DBDBE4'
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Poppins','Segoe UI','Calibri','DejaVu Sans'],'font.size':8,
 'axes.edgecolor':'#C3C3CC','axes.labelcolor':TINTA,'xtick.color':FRACA,'ytick.color':FRACA,'axes.spines.top':False,'axes.spines.right':False,
 'axes.grid':True,'grid.color':GRADE,'grid.linewidth':0.5,'legend.frameon':False,'figure.facecolor':'white','axes.facecolor':'white','svg.fonttype':'none'})
cm=1/2.54
t=pd.read_csv(f'{D}/painel_tarifa_onibus_1995_2024.csv'); d=pd.read_csv(f'{D}/diesel_anp_real_2004_2024.csv')
fig,ax=plt.subplots(figsize=(16*cm,6.5*cm)); fig.set_layout_engine('constrained')
e=t[t.ano<=2005]; o=t[t.ano>=2005]
ax.plot(e.ano,e.tarifa_real_2024,color=ROSA,lw=1.6,ls='--',marker='o',ms=3,mfc='white',label='Tarifa de ônibus, 1995–2004 (estimada)')
ax.plot(o.ano,o.tarifa_real_2024,color=ROSA,lw=1.8,marker='o',ms=3,label='Tarifa de ônibus, 2005–2024 (mediana observada)')
ax.plot(d.ano,d['preco_diesel_real_2024_R$_litro'],color=AZUL,lw=1.6,marker='s',ms=2.5,label='Diesel, R$ por litro (ANP)')
for yr in (2005,2024):
    v=float(t.loc[t.ano==yr,'tarifa_real_2024'].iloc[0]); ax.annotate(f'{v+1e-6:.2f}'.replace('.',','),(yr,v),xytext=(0,-12) if yr==2005 else (0,6),textcoords='offset points',ha='center',fontsize=7,color=TINTA)
ax.set_ylabel('R$ de 2024 (IPCA)'); ax.set_xlim(1994.5,2024.5); ax.set_ylim(0,None)
ax.set_xticks(range(1995,2025,5)); ax.legend(loc='lower right',fontsize=7)
fig.savefig(f'{A}/cap3-analise-VIII-tarifa-real-diesel.svg'); fig.savefig(f'{A}/cap3-analise-VIII-tarifa-real-diesel.png',dpi=300)
print('ok')
