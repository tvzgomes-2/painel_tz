#!/usr/bin/env bash
# build_tudo.sh — monta o site inteiro a partir das fontes, na ordem certa, e para no primeiro erro
# (13/11/2026, v1.0.0). Rodar da raiz do repositório:  bash scripts/build_tudo.sh
# Pré-requisitos: o cofre "doutorado" ao lado deste repositório (ou TZ_VAULT), a pasta build/ com
# geo.topojson (preparar_geometria.sh) e Python com pandas, openpyxl e python-docx.
# Não mexe em dados/ nem faz commit. Os arquivos *-proposta.html são intermediários do passo 11b (não versionados).
set -euo pipefail
cd "$(dirname "$0")/.."
passo() { echo; echo "== $*"; }
passo "1. base municipal + base-mestre do congelamento";  python3 scripts/build_data.py > build/log_build_data.txt && tail -3 build/log_build_data.txt
passo "2. estatísticas";                                  python3 scripts/build_stats.py | tail -1
passo "3. régua (camadas)";                              python3 scripts/build_camadas.py | head -2
passo "4. adoção por porte";                             python3 scripts/build_curva_porte.py | head -2
passo "5. fichas do Apêndice H";                         python3 scripts/build_fichas.py | head -1
passo "6. arranjo, remuneração e contrapartida, custeio"; python3 scripts/build_arranjo.py | grep "arranjo_tz"; python3 scripts/build_remuneracao.py | grep "remuneracao_tz"; python3 scripts/build_custeio.py | grep "custeio_tz"
passo "7. base legal";                                   python3 scripts/build_legislacao_base.py | head -1
passo "8. revisão sistemática";                          python3 scripts/build_rsl.py | tail -1
passo "9. dados enxutos para o painel";                  python3 scripts/exportar_colunar.py
passo "10. conferência com o congelamento";              python3 scripts/conferir_congelamento.py
passo "11. páginas";                                     python3 scripts/atualizar_numeros.py; bash scripts/montar_html.sh; bash scripts/montar_rede_ge.sh
passo "11b. revisão de lançamento (13/11/2026): painel e rede oficiais"
python3 scripts/gerar_proposta.py; python3 scripts/proposta_etapa2.py | tail -1; python3 scripts/proposta_etapa3.py | tail -1
python3 scripts/rede_etapa2.py | tail -1; python3 scripts/rede_etapa3.py | tail -1; python3 scripts/rede_etapa4.py | tail -1; python3 scripts/rede_etapa5.py | tail -1
python3 scripts/oficializar_painel.py; python3 scripts/oficializar_rede.py
passo "11c. dados e conceitos (com a aba Podcast)";      python3 scripts/build_dados.py
passo "11d. a tese só depois da defesa (tirar este passo depois da banca)"; python3 scripts/tese_apos_defesa.py
passo "12. dados pessoais (nomes de sócios PF)";         python3 scripts/pessoas_fisicas.py painel.html rede-ge.html dados.html index.html verbetes.html pesquisa.html | grep -a "ocorrência\|→" || true
echo; echo "Pronto. Confira o resumo da varredura acima (só razão social e nome de mercado podem ficar) e rode o teste no navegador antes do commit."
