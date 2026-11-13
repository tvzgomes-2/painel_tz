"""Figura do Cap. 4 (01/10/2026; ordem invertida a pedido do autor: Tarifa Zero à esquerda, modelo tarifado à direita): a régua descritiva, no esquema de 18/09/2026 (A.1.4 de Regras de classificação
das réguas): contínuo de gratuidade, piso constitucional e camadas 1 Universal (a-d), 2 Parcial (a-d), 3 Encerradas.
Sem contagens: os números ficam no Cap. 5. Paleta: rampa rosa (ordinal), cinza para o que não é Tarifa Zero."""
import os, matplotlib as mpl
mpl.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
B=os.path.expanduser('~/mnt/doutorado'); A=f'{B}/_attachments'
TINTA,FRACA='#0E0E10','#5D5D64'
R=['#FFE3EB','#FFC2D3','#FF8FAE','#FF5C88','#FF2D6B']; CINZA=['#EEEEF1','#DCDCE0','#C3C3CC']
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Poppins','Segoe UI','Calibri','DejaVu Sans'],'font.size':7.5,'svg.fonttype':'none'})
cm=1/2.54
fig=plt.figure(figsize=(16*cm,9.6*cm)); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,160); ax.set_ylim(-4,92); ax.axis('off')
def box(x,y,w,h,fc,title,sub='',tc=TINTA,fs=7.5,bold=True,ec='none',ls='-'):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=1.2',fc=fc,ec=ec,lw=0.8,ls=ls))
    ax.text(x+w/2,y+h-3.2,title,ha='center',va='top',fontsize=fs,color=tc,fontweight='bold' if bold else 'normal',wrap=True)
    if sub: ax.text(x+w/2,y+h-8.2,sub,ha='center',va='top',fontsize=6.0,color=tc,linespacing=1.25)
# contínuo
ax.text(4,88,'CONTÍNUO DE GRATUIDADE',fontsize=7,color=FRACA,fontweight='bold')
ax.annotate('',xy=(4,80.5),xytext=(156,80.5),arrowprops=dict(arrowstyle='-|>',color=FRACA,lw=1))
ax.text(4,76,'gratuito para todos',fontsize=6.5,color=FRACA); ax.text(156,76,'tarifado',fontsize=6.5,color=FRACA,ha='right')
box(126,56,30,17,CINZA[0],'Modelo tarifado','usuário paga o custo\npela tarifa')
box(93,56,30,17,CINZA[1],'Subsídio','tarifa social, aporte\nque reduz o preço')
box(60,56,30,17,CINZA[2],'Gratuidades legais','estudantes, PcD e\noutros grupos')
box(4,56,53,17,R[4],'Tarifa Zero','sem pagamento no embarque;\ncamadas abaixo',tc='white')
# piso
ax.plot([4,156],[52.5,52.5],color=TINTA,lw=1.2)
ax.text(4,49.5,'PISO CONSTITUCIONAL — gratuidade aos maiores de 65 anos (CF, art. 230, § 2º; Lei 10.741/2003, art. 39),\nválida em todo sistema urbano. É ponto de partida comum, não camada.',fontsize=6.2,color=TINTA,va='top',linespacing=1.3)
# pergunta
ax.text(4,40,'Há alguma condição para viajar sem pagar?',fontsize=7.5,color=TINTA,fontweight='bold')
# camadas
box(82,8,74,28,R[0],'',ec=R[3])
ax.text(119,33,'2 · PARCIAL — há portão de pessoa, tempo ou espaço',ha='center',va='top',fontsize=7,fontweight='bold',color=TINTA)
sub2=[('2a','grupo\nsocial'),('2b','espaço\nou linha'),('2c','dias da\nsemana'),('2d','eventos')]
for i,(k,t) in enumerate(sub2):
    box(84+i*18,10.5,16,18,R[1],k,t)
box(4,8,74,28,R[2],'',ec=R[4])
ax.text(41,33,'1 · UNIVERSAL — sem portão, ou com portão anotado',ha='center',va='top',fontsize=7,fontweight='bold',color=TINTA)
sub1=[('1a','ausência\nde portão'),('1b','procedimento\n(cadastro)'),('1c','residência'),('1d','prazo\ndeclarado,\nvigente')]
for i,(k,t) in enumerate(sub1):
    box(6+i*18,10.5,16,18,R[3] if k!='1a' else R[4],k,t,tc='white')
ax.text(4,4.2,'3 · ENCERRADAS — políticas que terminaram, descritas por início, fim e motivação (por desenho ou por trajetória)\ne pelo subtipo do último desenho antes do fim.',fontsize=6.2,color=FRACA,va='top',linespacing=1.3)
fig.savefig(f'{A}/cap4-regua-descritiva.svg'); fig.savefig(f'{A}/cap4-regua-descritiva.png',dpi=300); print('ok')
