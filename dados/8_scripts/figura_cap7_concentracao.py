"""Cap. 7 — concentração do capital social dos 327 grupos econômicos (tabela mestre de 12/08/2026)
e grupos por UF predominante (Panorama quantitativo dos 327, ago/2026). Gera
_attachments/tese-cap7-01-concentracao-327.svg/.png. r25, 05/10/2026."""
import pandas as pd, numpy as np
from pathlib import Path
from estilo_figuras import aplicar_estilo, figura, salvar, cor
R = Path(__file__).resolve().parents[1].parent
g = pd.read_excel(R / '03 - Dados/Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx', 'Resumo por grupo')
c = np.sort(g.capital_social_total_reais.fillna(0).values)[::-1]
cum = np.cumsum(c) / c.sum() * 100
aplicar_estilo()
fig, (a1, a2) = figura('plena', razao=1.9, ncols=2)
x = np.arange(1, len(c) + 1)
a1.plot(x, cum, color=cor('azul'), lw=1.6)
a1.plot([0, len(c)], [0, 100], color=cor('preto'), lw=0.6, ls=':')
for k in (5, 10, 26, 50):
    a1.plot(k, cum[k - 1], 'o', color=cor('rosa'), ms=4)
    a1.text(k + 6, cum[k - 1] - 3, f'{k} maiores: {cum[k-1]:.1f}%'.replace('.', ','), fontsize=7, va='top')
a1.set_xlim(0, 330); a1.set_ylim(0, 102)
a1.set_xlabel('grupos, do maior para o menor capital'); a1.set_ylabel('% do capital social acumulado')
a1.set_title('A. Concentração do capital (Gini 0,683)', loc='left', fontsize=9)
uf = pd.Series({'SP': 123, 'MG': 44, 'RJ': 28, 'RS': 23, 'BA': 15, 'PR': 13, 'SC': 11, 'PA': 11, 'GO': 10, 'PE': 9, 'MT': 7, 'ES': 7})
a2.barh(uf.index[::-1], uf.values[::-1], color=cor('preto'), height=0.62)
for i, v in enumerate(uf.values[::-1]): a2.text(v + 1.5, i, str(v), va='center', fontsize=7)
a2.set_xlabel('nº de grupos (UF predominante)'); a2.set_title('B. Grupos por UF predominante', loc='left', fontsize=9)
for ax in (a1, a2):
    ax.tick_params(labelsize=7)
    for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
salvar(fig, R / '_attachments/tese-cap7-01-concentracao-327.svg', png=True, auditar=False)
print(cum[[0, 4, 9, 25, 49]])
