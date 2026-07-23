# Changelog e notas de metodologia

## v2 (atual — publicada 2026-07-23)

Reconstruído sobre `base_municipal_v3.csv` (234 variáveis), no lugar da v1 (`base_municipal_integrada_v2.csv`, 131 variáveis). Mesma geometria municipal (topojson simplificado) e mesmo cruzamento com a base-mestre de Tarifa Zero — só a base de atributos mudou.

Eixos novos:

- **Hierarquia urbana (REGIC 2018)** — nível 1 (Metrópole) a 5 (Centro Local), como proxy de centralidade/interesse comercial.
- **Sede × satélite de arranjo metropolitano** — deriva de `arranjo_pop_2018` + nome do município: "sede" quando o nome do município aparece no nome do arranjo, "satélite" caso contrário.
- **Modelo de prestação do serviço (MUNIC 2020)** — concessão / permissão / autorização / prestação direta / não regulamentado / misto. Cobertura parcial: só 1.727/5.570 municípios (31%) responderam esse módulo da pesquisa do IBGE.
- **Tarifa de ônibus reconciliada** (PEMOB > SIMU > ANTP/SIMOB) — cobertura muito baixa (111/5.570, 2%).
- **% do custo subsidiado (NTU)** — cobertura muito baixa (80/5.570, 1,4%).

### Achado descritivo (a interpretar com cautela)

Olhando só a hierarquia REGIC, municípios de nível 1 (Metrópole) têm a *maior* proporção de TZ (14,5%) — à primeira vista, o oposto do que a hipótese de bloqueio pelos grupos econômicos sugeriria. Decompondo por sede × satélite, porém: dos 31 municípios de nível 1 com TZ, **nenhum é a cidade-polo do arranjo metropolitano** — todos são satélites (ex.: Caucaia/Fortaleza, Canoas/Porto Alegre, seis municípios do entorno do Rio de Janeiro, São Caetano do Sul/São Paulo, Brumadinho/Belo Horizonte). Nenhuma das ~15-20 maiores metrópoles do país tem TZ na cidade-polo. Em arranjos menores, esse padrão não se sustenta (ex.: Teresina/PI, Itapetininga/SP e São João del Rei/MG são cidades-polo com TZ).

Isso é uma correlação descritiva, não um teste da hipótese central da tese — falta a variável de presença/atuação de grupo econômico por município (rede ARS/CNPJ) para isso.

## v1 (2026-07-20, preservada como histórico — não publicada neste repositório)

Primeira versão, construída sobre `base_municipal_integrada_v2.csv` (131 variáveis: FINBRA, PIB, frota, Censo 2022, Passe Livre eleitoral). Mapa coroplético + filtros por UF/faixa populacional/situação TZ + comparação TZ×não-TZ + lista dos municípios TZ. Guardada no cofre de pesquisa (não neste repositório).

## Pendências de qualidade de dados (v1 e v2, não corrigidas)

- **Duplicata no arquivo-mestre de TZ:** `Municípios TZ - consolidado.xlsx` tem 155 linhas (145 Ativa + 10 Encerrada), mas Palmas-TO aparece duas vezes como "Encerrada" (períodos 2023-02-02 e 2025-01-01/2025-02-03) — são 154 municípios únicos (145 ativas + 9 encerradas distintas). Não reconciliado ainda: pode ser duplicata de digitação ou dois episódios reais de implantação/revogação.
- **Desatualização pontual:** São Caetano do Sul consta como "Ativa" (a base-fonte é de abr/2026); a universalidade foi revogada em 15/07/2026. A planilha-mestre ainda não reflete essa mudança.

## Pipeline / reprodutibilidade

Scripts em `scripts/` (`build_data.py`, `build_stats.py`) documentam como os dados embutidos no `index.html` foram gerados a partir das fontes brutas. As fontes brutas (CSVs/XLSX) são parte do cofre de pesquisa privado do autor e **não estão incluídas neste repositório público** — os scripts servem como documentação do método, não para execução direta por terceiros. Ver também `FEEDBACK.md` para pendências de ajuste na visualização.
