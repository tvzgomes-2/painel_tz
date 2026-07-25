# Changelog e notas de metodologia

## Política de versionamento (adotada 2026-07-25)

**Fase de prototipagem — v0.x:** enquanto o painel circula só entre orientação e equipe próxima, cada iteração soma um patch (v0.1, v0.2, v0.3...).

**Lançamento — v1.0.0:** quando o painel sair da prototipagem e for considerado pronto para circular em grupos de pesquisa.

**Pós-lançamento:**
- *Patch* (v1.0.1, v1.0.2...) — dados atualizados/enriquecidos ou correções pontuais, mesma estrutura de banco de dados.
- *Minor* (v1.1.0, v1.2.0...) — mudança estrutural no banco de dados; reseta o patch para zero.
- *Major* (v2.0.0) — redesign ou mudança conceitual grande.

**Hierarquia quando várias mudanças coincidem na mesma iteração:** mudança estrutural de BD (sobe minor) > feature/melhoria implementada (sobe patch) > enriquecimento de dados (não gera versão sozinha, entra dentro do patch da vez).

**Nota de remapeamento:** as versões antes chamadas de v1, v2 e v3 neste changelog foram renomeadas retroativamente para v0.1, v0.2 e v0.3 — mudança só de rótulo, sem alteração de conteúdo, para alinhar o histórico a esta política.

## v0.3 (atual — publicada 2026-07-24)

Release de melhorias guiada pelo feedback de 5 leitores (ver `FEEDBACK.md`) e pelo pedido da orientação (mais gráficos e grandes números). Mesmos dados da v0.2 — nenhuma mudança de base.

**Mapa:**

- Bordas estaduais sempre visíveis (camada de UFs dissolvida dos municípios, +17 KB) — o item mais pedido do feedback.
- Bordas municipais mais visíveis; contorno claro destacando os municípios TZ (decisão: contorno em vez do "glow" pedido — ver ROADMAP, registro de decisões).
- Auto-encaixe: selecionar UF no filtro enquadra o estado; duplo clique num município aproxima; botão "↺ Brasil" reseta. Strokes com `vector-effect: non-scaling-stroke` (espessura constante em qualquer zoom).
- Tooltip completo nos municípios TZ (situação, início/fim, REGIC, arranjo, população, PIB pc, motorização, operador); tooltip suprimido fora do recorte quando há filtro ativo.

**Grandes números e gráficos (pedido da orientadora):**

- Cards do topo agora são dinâmicos — recalculam conforme o recorte (UF/faixa/REGIC/arranjo/modelo), com aviso de "amostra pequena" quando há <5 municípios TZ no recorte. Novo indicador: **pessoas vivendo com TZ ativa** (soma da população dos municípios ativos; nacional: ~7,6 milhões).
- Novo gráfico: **linha do tempo das adoções** (por ano de início, com revogações abaixo do eixo), reagindo aos filtros — evidencia a aceleração recente (37 adoções só em 2023).

**Leitura e estrutura:**

- Cabeçalho reescrito: título oficial da tese ("Tarifa Zero e Grupos Econômicos no Brasil"), resumo da pesquisa (pergunta, hipótese e método — redigido a partir do projeto de qualificação, a revisar pelo autor) e link para este repositório. Sigla "(TZ)" definida na primeira menção do resumo.
- Títulos de seção maiores; cards e controles no mesmo grid (alinhados).
- Bloco "% por eixo": subtítulo explicando que a % é dentro de cada categoria; rótulo agora fica acima da própria barra (sem ambiguidade barra↔legenda).
- Glossário de siglas (IBEU, IDH, PDMU, REGIC, NTU, MUNIC, FINBRA, arranjo metropolitano, motorização) em bloco colapsável.
- **Toggle tema claro/escuro** (preferência salva no navegador); paleta neutra do mapa acompanha o tema.

**Identidade visual da pesquisa** (aplicada 24/07/2026, a partir da base de identidade do autor — rosa `#f43f6f` · amarelo `#ffd400` · azul `#2b50d9` sobre preto):

- Cores semânticas: **amarelo = TZ ativa**, **rosa = encerrada/revogação**, azul = interface (links, barras, filtros) — no mapa, na linha do tempo, nas tags e na legenda.
- Título em caixa alta com "Tarifa Zero" destacado (amarelo + sublinhado rosa); títulos de seção em caixa alta com filete amarelo; selo "painel · v0.3" no estilo do adesivo da identidade.
- Rodapé no padrão da capa: autor/programa à esquerda, orientadora à direita.
- No tema claro, os textos em amarelo usam tom escurecido para manter contraste (fills do mapa não mudam).
- Título do trabalho no cabeçalho: "Transporte Público em Crise — A influência dos grupos econômicos nas experiências de Tarifa Zero" (com "Crise" destacado, como na capa da identidade).
- Ajustes do autor: "Mapa coroplético" → "Mapa"; municípios com TZ encerrada têm contorno rosa (ativas seguem com contorno amarelo); caixa "Município selecionado" separada do bloco de comparação TZ×Não-TZ (painéis independentes).

## v0.2 (2026-07-23)

Reconstruído sobre `base_municipal_v3.csv` (234 variáveis), no lugar da v0.1 (`base_municipal_integrada_v2.csv`, 131 variáveis). Mesma geometria municipal (topojson simplificado) e mesmo cruzamento com a base-mestre de Tarifa Zero — só a base de atributos mudou.

Eixos novos:

- **Hierarquia urbana (REGIC 2018)** — nível 1 (Metrópole) a 5 (Centro Local), como proxy de centralidade/interesse comercial.
- **Sede × satélite de arranjo metropolitano** — deriva de `arranjo_pop_2018` + nome do município: "sede" quando o nome do município aparece no nome do arranjo, "satélite" caso contrário.
- **Modelo de prestação do serviço (MUNIC 2020)** — concessão / permissão / autorização / prestação direta / não regulamentado / misto. Cobertura parcial: só 1.727/5.570 municípios (31%) responderam esse módulo da pesquisa do IBGE.
- **Tarifa de ônibus reconciliada** (PEMOB > SIMU > ANTP/SIMOB) — cobertura muito baixa (111/5.570, 2%).
- **% do custo subsidiado (NTU)** — cobertura muito baixa (80/5.570, 1,4%).

### Achado descritivo (a interpretar com cautela)

Olhando só a hierarquia REGIC, municípios de nível 1 (Metrópole) têm a *maior* proporção de TZ (14,5%) — à primeira vista, o oposto do que a hipótese de bloqueio pelos grupos econômicos sugeriria. Decompondo por sede × satélite, porém: dos 31 municípios de nível 1 com TZ, **nenhum é a cidade-polo do arranjo metropolitano** — todos são satélites (ex.: Caucaia/Fortaleza, Canoas/Porto Alegre, seis municípios do entorno do Rio de Janeiro, São Caetano do Sul/São Paulo, Brumadinho/Belo Horizonte). Nenhuma das ~15-20 maiores metrópoles do país tem TZ na cidade-polo. Em arranjos menores, esse padrão não se sustenta (ex.: Teresina/PI, Itapetininga/SP e São João del Rei/MG são cidades-polo com TZ).

Isso é uma correlação descritiva, não um teste da hipótese central da tese — falta a variável de presença/atuação de grupo econômico por município (rede ARS/CNPJ) para isso.

## v0.1 (2026-07-20, preservada como histórico — não publicada neste repositório)

Primeira versão, construída sobre `base_municipal_integrada_v2.csv` (131 variáveis: FINBRA, PIB, frota, Censo 2022, Passe Livre eleitoral). Mapa coroplético + filtros por UF/faixa populacional/situação TZ + comparação TZ×não-TZ + lista dos municípios TZ. Guardada no cofre de pesquisa (não neste repositório).

## Pendências de qualidade de dados (v0.1 e v0.2, não corrigidas)

- **Duplicata no arquivo-mestre de TZ:** `Municípios TZ - consolidado.xlsx` tem 155 linhas (145 Ativa + 10 Encerrada), mas Palmas-TO aparece duas vezes como "Encerrada" (períodos 2023-02-02 e 2025-01-01/2025-02-03) — são 154 municípios únicos (145 ativas + 9 encerradas distintas). Não reconciliado ainda: pode ser duplicata de digitação ou dois episódios reais de implantação/revogação.
- **Desatualização pontual:** São Caetano do Sul consta como "Ativa" (a base-fonte é de abr/2026); a universalidade foi revogada em 15/07/2026. A planilha-mestre ainda não reflete essa mudança.

## Pipeline / reprodutibilidade

Scripts em `scripts/` (`build_data.py`, `build_stats.py`) documentam como os dados embutidos no `index.html` foram gerados a partir das fontes brutas. As fontes brutas (CSVs/XLSX) são parte do cofre de pesquisa privado do autor e **não estão incluídas neste repositório público** — os scripts servem como documentação do método, não para execução direta por terceiros. Ver também `FEEDBACK.md` para pendências de ajuste na visualização.
