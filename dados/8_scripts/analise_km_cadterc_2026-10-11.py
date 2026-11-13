"""Preço do km da Tarifa Zero × CadTerc (Vol. 4, fretamento contínuo, data-base mai/2026) — Cap. 6/Seção 7.2.
Entrada: 03 - Dados/_data/Analises_Cap6/km_tz_cadterc_entrada_2026-10-11.csv (valores lidos no acervo e nas rodadas
de busca de 11/10/2026) e ipca_1737_2018-2026.json (IBGE/SIDRA, tabela 1737, número-índice).
Saída: km_tz_cadterc_saida_2026-10-11.csv e _attachments/tese-cap6-04-km-cadterc.svg/.png. r58, 11/10/2026."""
import json, os
from pathlib import Path
import pandas as pd
R = Path(__file__).resolve().parents[2]
D = R / '03 - Dados/_data/Analises_Cap6'
I = json.load(open(D / 'ipca_1737_2018-2026.json', encoding='utf-8')); BASE = '202605'
d = pd.read_csv(D / 'km_tz_cadterc_entrada_2026-10-11.csv')
d['fator_ipca'] = d.ref_aaaamm.astype(str).map(lambda p: I[BASE] / I[p])
d['rkm_mai2026'] = (d.rkm * d.fator_ipca).round(2)
# CadTerc Vol. 4 (set/2026, data-base mai/2026), Quadros 16 a 19: fixo R$/mês + variável R$/km, por veículo
CT = {'44 lugares, 2ª a domingo, diurno': (21054.24, 5.51), '44 lugares, 2ª a domingo, diuturno': (38339.37, 5.51),
      '24 lugares, 2ª a domingo, diurno': (15965.34, 3.35), '24 lugares, 2ª a domingo, diuturno': (30280.76, 3.35),
      'van, 2ª a domingo, diurno': (14215.05, 2.35)}
def ct(k, km): f, v = CT[k]; return f / km + v
faixas = pd.DataFrame([{'regime': k, **{f'{km} km/mês': round(ct(k, km), 2) for km in (4000, 6000, 8000)}} for k in CT])
d.to_csv(D / 'km_tz_cadterc_saida_2026-10-11.csv', index=False)
faixas.to_csv(D / 'km_cadterc_faixas_2026-10-11.csv', index=False)
principal = d[d.leitura.isin(['contrato', 'homologação', 'aditivo'])]
print(faixas.to_string(index=False))
print('principal:', len(principal), 'linhas;', principal.municipio.str.replace(r' \(micro\)', '', regex=True).nunique(), 'municípios')
# ── figura ──
from estilo_figuras import aplicar_estilo, figura, salvar, cor
aplicar_estilo()
p = principal.sort_values('rkm_mai2026').reset_index(drop=True)
fig, ax = figura('plena', razao=1.25)
y = range(len(p))
lo12, hi12 = ct('44 lugares, 2ª a domingo, diurno', 8000), ct('44 lugares, 2ª a domingo, diurno', 4000)
lo24, hi24 = ct('44 lugares, 2ª a domingo, diuturno', 8000), ct('44 lugares, 2ª a domingo, diuturno', 4000)
ax.axvspan(lo24, hi24, color=cor('tarifado'), alpha=0.55, lw=0, zorder=0)
ax.axvspan(lo12, hi12, color=cor('nao_apurado'), alpha=0.8, lw=0, zorder=0)
mic = p.veiculo.str.contains('micro')
ax.scatter(p.rkm_mai2026[~mic], [i for i, m in zip(y, mic) if not m], color=cor('tarifa_zero'), s=22, zorder=3, label='contrato de Tarifa Zero (R$ de mai/2026)')
ax.scatter(p.rkm_mai2026[mic], [i for i, m in zip(y, mic) if m], facecolor='white', edgecolors=cor('tarifa_zero'), linewidths=1.2, s=22, zorder=3, label='idem, micro-ônibus')
ax.set_yticks(list(y)); ax.set_yticklabels([(f"{m.replace(' (micro)', '')} ({u}), micro" if '(micro)' in m else f'{m} ({u})') for m, u in zip(p.municipio, p.uf)], fontsize=7)
ax.set_xlim(4, 18); ax.set_ylim(-1.2, len(p) - 0.3)
ax.set_xlabel('R$ por km, em reais de maio de 2026 (IPCA)', fontsize=8); ax.tick_params(axis='x', labelsize=7)
ax.text((lo12 + hi12) / 2, len(p) - 0.6, 'CadTerc, ônibus 44 lugares,\n2ª a domingo, diurno\n(4 a 8 mil km/mês)', fontsize=6.2, ha='center', va='top')
ax.text(min(hi24, 17.8) - 0.1, -0.9, 'idem, diuturno', fontsize=6.2, ha='right', va='center')
for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
ax.legend(loc='lower right', bbox_to_anchor=(1.0, 0.06), fontsize=6.5, frameon=False)
salvar(fig, Path(os.environ.get('SAIDA', R / '_attachments')) / 'tese-cap6-04-km-cadterc.svg', png=True, auditar=False)
print('figura ok', round(lo12, 2), round(hi12, 2), round(lo24, 2), round(hi24, 2))
