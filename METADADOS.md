# Metadados — dicionário de variáveis do painel

Descreve os 54 campos por município embutidos em `painel.html` (ver `municipios_dados_col.json` gerado por `scripts/build_data.py`). Nomes entre parênteses = nome da coluna na fonte original, quando diferente do usado no painel.

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

## Vulnerabilidade social (CadÚnico)

Fonte: **MDS/SAGI — API MI Social**, agregados municipais do Cadastro Único. Duas competências: **set/2022** (comparável a Gonçalves e Santini, 2023, em Mariana) e **ago/2025** (mais recente). Cobertura 5.570/5.570 municípios.

| Campo | Descrição | Fonte | Ano | Observações |
|---|---|---|---|---|
| `cadunico_cobertura` | Pessoas inscritas no CadÚnico / população × 100 | MDS/SAGI ÷ IBGE | ago/2025 | denominador `pop_2025`; proxy de demanda cativa |
| `cadunico_cobertura_2022` | Mesma medida na competência set/2022 | MDS/SAGI ÷ IBGE | set/2022 | denominador `pop_2022`; ⚠️ não comparável direto com a de 2025 — ver abaixo |
| `cadunico_pes` | Pessoas inscritas (absoluto) | MDS/SAGI | ago/2025 | |
| `cadunico_taxa_atualizacao` | Famílias com cadastro atualizado / cadastradas × 100 | MDS/SAGI | ago/2025 | medida do estoque **ativo**; indicador de capacidade administrativa |

**Como ler — três ressalvas.**

1. **Inscrição, não pobreza.** A cobertura depende da capacidade de busca ativa do CRAS. Dois municípios igualmente pobres podem ter coberturas distintas por qualidade de gestão. Declarar como *proxy de vulnerabilidade mediada por capacidade administrativa*.
2. **Estoque, não fotografia.** O campo conta cadastros acumulados, incluindo registros desatualizados de quem já saiu do município — daí **62 municípios pequenos acima de 100%** em set/2022. Multiplicando pela taxa de atualização, os casos acima de 100% caem para 3 e a média municipal converge para o agregado nacional (44,6%).
3. **Quebra de série entre as competências.** Desde jun/2023 (IN nº 1/SAGICAD/MDS, 02/06/2023) a renda registrada vem do **CNIS** quando maior que a autodeclarada — 2022 é pré-integração, 2025 é pós. E as réguas se moveram em direções opostas em termos reais: linha da pobreza R$ 210 → R$ 218 (+3,8%), meio salário mínimo R$ 606 → R$ 759 (+25,2%). A variação entre as duas mistura renda com instrumento de medida.

**Validação:** agregado nacional 90.525.701 pessoas / 203.080.756 hab = 44,6% em set/2022, compatível com o total oficial da competência. As identidades internas do CadÚnico (faixa 1 + faixa 2 = até ½ SM; + faixa 3 = total) fecham em 5.570/5.570 nas duas competências.

## Deslocamento para trabalho (Censo 2022, microdados da amostra)

| campo | descrição | fonte |
|---|---|---|
| `trab_fora` | % dos ocupados que trabalham em outro município | Censo 2022, microdados da amostra (`P1120 = 3`), agregado municipal |
| bloco `data-od` | matriz origem-destino nas duas direções, top-5 por município | idem, ver supressão abaixo |

**Supressão, e por que ela é parte do dado.** A origem é a versão de **acesso controlado** dos microdados, vinculada a termo de compromisso assinado — o painel é público. Dos 120.435 pares origem-destino, **57,6% se apoiam em uma única pessoa amostrada** (mediana de registros por célula = 1; terceiro quartil = 3). Publicar essas células seria erro de **custódia** (cruzar residência com local de trabalho a partir de um respondente é informação identificável) e de **estatística** (CV da ordem de 100%, lido como fato). Corte publicado: **top-5 destinos por município e mínimo de 5 registros amostrados por célula**, aplicado à célula e portanto igual nas duas direções — 16.560 pares, 80,3% do fluxo, 5.167 de 5.570 municípios. **403 municípios não mostram nada; ali a ausência é ausência de medição.** Os totais exibidos são de antes da supressão, e cada lista declara a fração do fluxo que cobre.

**Como ler.** A direção de **entrada** é a que interessa ao argumento da pesquisa: num município com Tarifa Zero, quem chega de fora paga tarifa intermunicipal para acessar o sistema gratuito; num polo sem TZ, o volume que entra é a mão de obra dos satélites que a gratuidade dos vizinhos não alcança. O marcador ◆ indica que o par é o **polo do próprio arranjo populacional** e ◇ que é outro município do mesmo arranjo — recorte do IBGE por integração de fato, diferente de região metropolitana por lei.

**O que o dado não diz.** Não há direção causal nem tempo de viagem por par (o tempo está no agregado municipal, não na célula OD); a pergunta do Censo é sobre o **trabalho principal**, então quem trabalha em mais de um município fica fora das listas (entra só no total); e o recorte é de 2022, anterior a boa parte das adesões recentes à Tarifa Zero.

**Reprodução.** `scripts/build_od.py` (aceita `TZ_VAULT` e `TZ_PAINEL_SCRIPTS` por variável de ambiente). O cache de pessoa a pessoa usado na análise que originou este dado fica **fora** do OneDrive, ao lado do zip de origem; ao pacote de replicação vão o script e o agregado, nunca o microdado.

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

FINBRA/Siconfi · IBGE (PIB, Censo 2022, REGIC 2018) · DENATRAN · MUNIC 2020 · PEMOB/SIMU (Ministério das Cidades) · TSE 2024 · DATASUS/SIM · OSM/Geofabrik · NTU (Anuário 2023/2025) · ANTP/SIMOB (histórico 2005–2017) · Observatório das Metrópoles (IBEU) · Atlas PNUD (IDH) · Base Polo Planejamento · Dataverse Santini (base-mestre TZ).
