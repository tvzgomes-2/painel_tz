"""Gráfico do Cap. 6 — preço do quilômetro e custo por habitante nos contratos de Tarifa Zero
(camada 1, destinatário ii; retrato da base-mestre de 01/10/2026; saída de cap6_dados.py).
Gera _attachments/tese-cap6-03-preco-km-custo-hab.svg/.png. r25, 05/10/2026."""
import pandas as pd
from pathlib import Path
from estilo_figuras import aplicar_estilo, figura, salvar, cor
R = Path(__file__).resolve().parents[2]
import os
d = pd.read_csv(R / '03 - Dados/_data/Analises_Cap6' / os.environ.get('TZ_CAP6_SAIDA', 'cap6_analise12_destinatario.csv'))  # r56
aplicar_estilo()
fig, (a1, a2) = figura('plena', razao=1.35, ncols=2)
k = d[d.rkm.notna()].sort_values('rkm')
lab = lambda r: f"{r['Município']} ({r['UF']})"
a1.barh([lab(r) for _, r in k.iterrows()], k.rkm, color=cor('azul'), height=0.62)
med = k.rkm.median()
a1.axvline(med, color=cor('preto'), lw=0.9, ls='--'); a1.text(med + 0.2, -1.0, 'mediana R$ ' + f'{med + 1e-9:.2f}'.replace('.', ','), fontsize=7, va='center', ha='left')
a1.axvline(5.64, color=cor('rosa'), lw=0.9, ls=':'); a1.text(5.44, -1.0, 'R$ 5,64', fontsize=7, color=cor('rosa'), ha='right', va='center')
a1.set_xlabel('R$ por km (n = %d)' % len(k)); a1.set_xlim(0, 17); a1.set_ylim(-1.6, len(k) - 0.4)
a1.set_title('A. Preço do quilômetro', loc='left', fontsize=9)
h = d[d.custo_hab.notna()].sort_values('custo_hab')
a2.barh([lab(r) for _, r in h.iterrows()], h.custo_hab, color=cor('preto'), height=0.62)
m2 = h.custo_hab.median()
a2.axvline(m2, color=cor('rosa'), lw=0.9, ls='--'); a2.text(m2 + 4, -1.0, 'mediana R$ ' + f'{m2:.1f}'.replace('.', ','), fontsize=7, va='center', ha='left', color=cor('rosa')); a2.set_ylim(-1.6, len(h) - 0.4)
a2.set_xlabel('R$ por hab. ao ano (n = %d)' % len(h)); a2.set_title('B. Custo anual por habitante', loc='left', fontsize=9)
for ax in (a1, a2):
    ax.tick_params(axis='y', labelsize=7); ax.tick_params(axis='x', labelsize=7)
    for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
salvar(fig, Path(os.environ.get('SAIDA', R / '_attachments')) / 'tese-cap6-03-preco-km-custo-hab.svg', png=True, auditar=False)
print(len(k), med, len(h), m2)
