"""Figuras das Análises III e IV do Cap. 2 (01/10/2026). Paleta do Design System de Figuras
(_meta/Design System de Figuras.md); estilo aplicado à mão porque tz.mplstyle não está em _meta/scripts."""
import pandas as pd, os, matplotlib as mpl
mpl.use('Agg'); import matplotlib.pyplot as plt
B=os.path.expanduser('~/mnt/doutorado'); D=f'{B}/03 - Dados/_data/Analises_Cap2'; A=f'{B}/_attachments'
ROSA,AZUL,VERDE,AMAR='#FF2D6B','#1A54C7','#326F00','#9F9400'; TINTA,FRACA,GRADE='#0E0E10','#5D5D64','#DBDBE4'
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Poppins','Segoe UI','Calibri','DejaVu Sans'],'font.size':8,
 'axes.edgecolor':'#C3C3CC','axes.labelcolor':TINTA,'xtick.color':FRACA,'ytick.color':FRACA,'axes.spines.top':False,'axes.spines.right':False,
 'axes.grid':True,'grid.color':GRADE,'grid.linewidth':0.5,'legend.frameon':False,'figure.facecolor':'white','axes.facecolor':'white','svg.fonttype':'none'})
cm=1/2.54
# ---- III
br=pd.read_csv(f'{D}/analise_III_brasil_ano.csv'); fx=pd.read_csv(f'{D}/analise_III_faixa_2023.csv')
fig,(a1,a2)=plt.subplots(1,2,figsize=(16*cm,7*cm),gridspec_kw={'width_ratios':[1.1,1]}); fig.set_layout_engine('constrained')
x=br.ano
a1.plot(x,br.pct_s451,color=AZUL,lw=1.6,marker='o',ms=3,label='15.451 Infraestrutura urbana')
a1.plot(x,br.pct_s782,color=VERDE,lw=1.6,marker='o',ms=3,label='26.782 Transporte rodoviário')
a1.plot(x,br.pct_s453+br.pct_fu26,color=ROSA,lw=1.6,ls='--',marker='o',ms=3,label='TPC — teto (15.453 + demais subf. da função 26)')
a1.plot(x,br.pct_s453,color=ROSA,lw=1.6,marker='o',ms=3,label='TPC — identificável (15.453)')
a1.set_ylabel('% da despesa municipal liquidada'); a1.set_xticks(list(x)); a1.set_ylim(0,None)
a1.legend(loc='upper left',bbox_to_anchor=(0,-0.14),ncol=1,fontsize=7)
a1.set_title('Brasil, 2019–2023',loc='left',fontsize=8,color=TINTA)
ordem=['Inferior a 20 mil','Entre 20 e 100 mil','Entre 100 e 250 mil','Entre 250 e 500 mil','Acima de 500 mil']
rot=['< 20 mil','20–100 mil','100–250 mil','250–500 mil','> 500 mil']
f=fx.set_index('faixa_pop_2022').loc[ordem]; import numpy as np; y=np.arange(len(ordem)); h=0.38
a2.barh(y+h/2,f.pct_s451+f.pct_s782,h,color=AZUL,label='Viário (15.451 + 26.782)')
a2.barh(y-h/2,f.pct_s453+f.pct_fu26,h,color=ROSA,label='TPC — teto')
for yy,v in zip(y+h/2,f.pct_s451+f.pct_s782): a2.text(v+0.1,yy,f'{v:.1f}'.replace('.',','),va='center',fontsize=7,color=TINTA)
for yy,v in zip(y-h/2,f.pct_s453+f.pct_fu26): a2.text(v+0.1,yy,f'{v:.1f}'.replace('.',','),va='center',fontsize=7,color=TINTA)
a2.set_yticks(y,rot); a2.invert_yaxis(); a2.set_xlabel('% da despesa liquidada'); a2.grid(axis='y',visible=False)
a2.legend(loc='upper left',bbox_to_anchor=(0,-0.18),ncol=1,fontsize=7); a2.set_title('Por faixa de população, 2023',loc='left',fontsize=8,color=TINTA)
fig.savefig(f'{A}/cap2-analise-III-finbra-viario-x-tpc.svg'); fig.savefig(f'{A}/cap2-analise-III-finbra-viario-x-tpc.png',dpi=300); plt.close(fig)
# ---- IV
fx=pd.read_csv(f'{D}/analise_IV_faixa.csv').set_index('faixa_pop_2022').loc[ordem]
rg=pd.read_csv(f'{D}/analise_IV_regiao.csv').set_index('regiao').loc[['N','NE','CO','SE','S']]
fig,(a1,a2)=plt.subplots(1,2,figsize=(16*cm,7*cm),sharex=True); fig.set_layout_engine('constrained')
def painel(ax,t,labels,tit):
    y=np.arange(len(t)); h=0.26
    for i,(c,cor_,lab) in enumerate([('auto',AZUL,'Automóvel'),('tpc',ROSA,'Transporte coletivo (ônibus, BRT, trem/metrô)'),('moto',VERDE,'Motocicleta')]):
        ax.barh(y+(i-1)*h,t[c],h,color=cor_,label=lab)
        for yy,v in zip(y+(i-1)*h,t[c]): ax.text(v+0.5,yy,f'{v:.0f}',va='center',fontsize=6.5,color=TINTA)
    ax.set_yticks(y,labels); ax.invert_yaxis(); ax.grid(axis='y',visible=False); ax.set_title(tit,loc='left',fontsize=8,color=TINTA)
painel(a1,fx,rot,'Por faixa de população'); painel(a2,rg,['Norte','Nordeste','Centro-Oeste','Sudeste','Sul'],'Por região')
fig.supxlabel('% das pessoas ocupadas que trabalham fora do domicílio, por meio de transporte para o trabalho (ponderado pela população)',fontsize=7.5,color=TINTA)
h_,l_=a1.get_legend_handles_labels(); fig.legend(h_,l_,loc='outside upper center',ncol=3,fontsize=7)
fig.savefig(f'{A}/cap2-analise-IV-censo-auto-x-tpc.svg'); fig.savefig(f'{A}/cap2-analise-IV-censo-auto-x-tpc.png',dpi=300); plt.close(fig)
print('ok')
