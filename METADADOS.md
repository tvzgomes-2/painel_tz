# Metadados — dicionário de variáveis do painel

Descreve os 54 campos por município embutidos em `index.html` (ver `municipios_dados_col.json` gerado por `scripts/build_data.py`). Nomes entre parênteses = nome da coluna na fonte original, quando diferente do usado no painel.

⚠️ = cobertura parcial ou ressalva de qualidade — ver coluna "Observações".

## Identificação e geografia

| Campo | Descrição | Fonte | Ano |
|---|---|---|---|
| `id` | Código IBGE do município (7 dígitos) | IBGE | — |
| `nome` | Nome do município | IBGE | — |
| `uf`, `uf_nome` | Sigla e nome da UF | IBGE | — |
| `regiao` | Grande região (Norte/Nordeste/etc.) | IBGE | — |
| `faixa_pop` | Faixa de população (5 categorias) | IBGE | 2022 |
| `pop` | População | IBGE Censo | 2022 |
| `cresc_pop` | Taxa de crescimento populacional | IBGE | 2010–2022 |

## Hierarquia urbana e arranjos metropolitanos (REGIC 2018)

| Campo | Descrição | Fonte | Ano | Observações |
|---|---|---|---|---|
| `regic_nivel` | Nível hierárquico ordinal, 1 (Metrópole) a 5 (Centro Local) | IBGE REGIC 2018 | 2018 | |
| `regic_label` | Rótulo da hierarquia (ex. "Metrópole (1C)") | IBGE REGIC 2018 | 2018 | |
| `arranjo_nome` | Nome do arranjo populacional ao qual o município pertence (vazio se nenhum) | IBGE REGIC 2018 | 2018 | só 938/5.570 municípios pertencem a algum arranjo |
| `tipo_arranjo` | "Sede/co-sede do arranjo", "Satélite do arranjo" ou "Fora de arranjo" | derivado (script próprio) | — | ⚠️ heurística: sede = nome do município aparece no nome do arranjo; ver `build_data.py` |

## Economia e fiscal

| Campo | Descrição | Fonte | Ano | Observações |
|---|---|---|---|---|
| `pib_pc` | PIB per capita (R$) | IBGE | 2021 | |
| `rec_total` | Receita total (R$) | FINBRA/Siconfi | — | |
| `rec_prop` | Receita própria (R$) | FINBRA/Siconfi | — | |
| `desp_tcu` | Despesa no transporte coletivo urbano (R$) | FINBRA | 2015 | |
| `desp_transporte` (desp_transporte_2022) | Despesa da função orçamentária Transporte (R$) | FINBRA/Siconfi (Anexo I-E) | 2022 | soma da linha de função 26 |
| `pct_transporte_desp` (pct_transporte_desp_2022) | % da despesa total gasta em Transporte | derivado | 2022 | |
| `investimentos` (investimentos_2022) | Investimentos, natureza 4.4 (R$) | FINBRA (Anexo I-D) | 2022 | |
| `pct_investimento_desp` (pct_investimento_desp_2022) | % da despesa total em investimento | derivado | 2022 | |

## Transporte e mobilidade

| Campo | Descrição | Fonte | Ano | Observações |
|---|---|---|---|---|
| `motorizacao` (motorizacao_2023) | Motorização (veículos/habitante) | DENATRAN | 2023 | |
| `ext_via` | Extensão do sistema viário (km) | IBGE/POLO | 2010 | |
| `ext_viaria_osm` (extensao_viaria_total_km) | Extensão viária total motorizada — estrutural+coletora+local (km) | OSM/Geofabrik | mapeamento 2026 | validado ~92% contra DER-DF |
| `densidade_viaria` (densidade_viaria_km_km2) | Densidade viária (km de via / km² de área) | derivado (OSM + IBGE) | 2026 | |
| `concessao` (conc_tcu) | Sistema de transporte é concessionado | POLO | — | |
| `concessionaria` | Nome da concessionária | POLO | — | |
| `frota_bus` | Frota de ônibus | POLO | — | |
| `gps_bus` | Frota tem GPS | POLO | — | |
| `modelo_prestacao` / `modelo_prestacao_simples` | Modelo de prestação do serviço: Concessão / Permissão / Autorização / Prestação direta / Não regulamentado / Misto | MUNIC 2020 (IBGE) | 2020 | ⚠️ só 1.727/5.570 municípios (31%) responderam este módulo — amostra parcial, possivelmente não aleatória |
| `munic_isencao_total` (munic_isencao_total_2020) | Isenção tarifária para toda a população, autodeclarada | MUNIC 2020 (IBGE) | 2020 | ⚠️ cruzar com a base-mestre de TZ; pode ter ruído em municípios sem sistema formal |
| `pdmu_2016` (pdmu) | Possui Plano de Mobilidade Urbana | POLO | 2016/17 | |
| `pdmu_2025` (pdmu_possui_2025) | Possui PDMU, autodeclarado ao MCID | MCID/SEMOB (jul/2025) | 2025 | ⚠️ 89,2% de concordância simples com `pdmu_2016` (períodos/perguntas diferentes) |
| `pdmu_obrigado_2025` | Município obrigado a elaborar PDMU (Lei 12.587/2012 + Lei 14.000/2020) | MCID/SEMOB (jun/2025) | 2025 | |
| `taxa_obitos_transito` (taxa_obitos_transito_100k_2019) | Óbitos no trânsito por 100 mil habitantes | SIMU/DATASUS | 2019 | |
| `tarifa` / `tarifa_ano` / `tarifa_fonte` (tarifa_reconciliada) | Tarifa de ônibus mais recente disponível, com prioridade PEMOB > SIMU > ANTP | PEMOB/SIMU/ANTP (Min. Cidades) | variável por município | ⚠️ só 111/5.570 municípios (2%). PEMOB e SIMU divergem em ~35% dos casos onde os dois têm dado (até 44,7% de diferença) — ver nota completa na fonte original |
| `subsidio_ntu_pct` / `subsidio_ntu_ano` (subsidio_pct_custo_ntu) | % do custo do transporte coletivo subsidiado com recursos públicos (sistemas não-TZ com subsídio parcial) | NTU (Anuário 2023/2025) | 2023 ou 2025 | ⚠️ só 80/5.570 municípios (1,4%). Não confundir com a base-mestre de 155 municípios TZ — são conjuntos diferentes |

## Urbanismo

| Campo | Descrição | Fonte | Ano |
|---|---|---|---|
| `plano_diretor` (pd) | Possui Plano Diretor | IBGE | 2015 |
| `ibeu` | Índice de Bem-Estar Urbano | Observatório das Metrópoles | 2013 |
| `idh` | Índice de Desenvolvimento Humano Municipal | Atlas PNUD | 2010 |

## Política

| Campo | Descrição | Fonte | Ano | Observações |
|---|---|---|---|---|
| `partido_16` (part_16) | Partido do prefeito eleito em 2016 | TSE | 2016 | |
| `prefeito_2024` | Nome do prefeito eleito em 2024 | TSE 2024 | 2024 | ⚠️ cobertura 5.555/5.570 (99,7%); 1 município (Boa Esperança do Norte/MT) instalado após a base, fora do universo |
| `partido_2024` | Partido do prefeito eleito em 2024 | TSE 2024 | 2024 | |
| `passe_1t`, `passe_2t` (passe_1turno_2022/passe_2turno_2022) | Passe Livre no 1º/2º turno da eleição de 2022 | IDEC + Tarifa Zero BH | 2022 | |
| `passe_abrang` (passe_abrangencia_2022) | Abrangência do Passe Livre eleitoral | IDEC + Tarifa Zero BH | 2022 | |

## Tarifa Zero (base-mestre)

| Campo | Descrição | Fonte |
|---|---|---|
| `tz_status` | "Ativa", "Encerrada" ou "Não TZ" | Dataverse Santini v8 (abr/2026), cruzado por `cod_ibge` |
| `tz_ano` | Ano de início da Tarifa Zero | idem |
| `tz_fim` | Data/ano de encerramento (se aplicável) | idem |
| `tz_pct_orc` | % do orçamento municipal dedicado à TZ (conforme fonte) | idem |
| `tz_operador` | Operador do sistema | idem |

⚠️ Ver `CHANGELOG.md` para as duas pendências conhecidas nesse cruzamento (duplicata de Palmas-TO e desatualização de São Caetano do Sul).

## Fontes completas

FINBRA/Siconfi · IBGE (PIB, Censo 2022, REGIC 2018) · DENATRAN · MUNIC 2020 · PEMOB/SIMU (Ministério das Cidades) · TSE 2024 · DATASUS/SIM · OSM/Geofabrik · NTU (Anuário 2023/2025) · ANTP/SIMOB (histórico 2005–2017) · Observatório das Metrópoles (IBEU) · Atlas PNUD (IDH) · Base POLO Planejamento · Dataverse Santini (base-mestre TZ).
