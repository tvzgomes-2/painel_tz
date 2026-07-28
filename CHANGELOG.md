# Changelog e notas de metodologia

O site tem páginas independentes, cada uma com seu próprio número de versão (ver arquitetura em `ROADMAP.md` § 0). **Tudo abaixo é sobre a página Painel Brasil (`painel.html`, tag TZ)** — é a única página com histórico até agora. Quando `rede-ge.html` (Rede da ARS) for publicada, ganha sua própria seção de changelog, separada desta.

## Política de versionamento

Regra completa (fases, patch/minor/major, hierarquia de precedência, nota de remapeamento v1/v2/v3 → v0.1/v0.2/v0.3) em [`VERSIONING.md`](./VERSIONING.md). A regra é uma só para todas as páginas do site; o que muda é que cada página conta seu próprio número.

## v0.4.01 (atual — 2026-07-28)

Sub-patch de v0.4 (decisão do autor — ver `VERSIONING.md` § Exceção sub-patch v0.x.NN): terceira passagem, incorpora os achados da consolidação de referências (bibliografia + notícias mapeadas) feita no cofre a pedido do autor. Mesma estrutura de banco (nenhuma coluna nova na base municipal — dados novos entram como crosswalks à parte, no mesmo padrão do `casos_por_fonte.json` da Fase 8).

**Referências bibliográficas:**

- Bloco ABNT ganha uma segunda lista, **"Referências adicionais"**, com as 8 referências acadêmicas levantadas na consolidação de 3 documentos do autor (artigo ANPET/versão cega, PGT092, Observatório de Tarifa Zero) que **não têm citekey no Zotero** (`biblioteca.bib`) — confirmado por leitura completa do `.bib` via `bibtexparser` + similaridade de título (não só sobrenome+ano, método refinado a pedido do autor após a primeira tentativa ter gerado falsos positivos). Mantida separada da lista original (que é só sobre os 5 estudos citados no crosswalk de Fontes) porque essas 8 ainda não estão vinculadas a um município específico.
- Uma delas (Kębłowski 2024, "Fare-free public transport: An international perspective") está sinalizada com ⚠ como possível duplicata/versão anterior de `keblowski2025a` (já no Zotero, título 2025 diferente) — decisão deixada para o autor, não resolvida aqui.
- Uma referência (Campos; Santini, 2024) está com dados de publicação incompletos na fonte de origem — sinalizado no próprio texto da citação, "a conferir antes de citar".

**Notícias por município (nova seção, separada de Fontes):**

- Novo crosswalk `casos_por_noticia.json`, gerado a partir de `05 - Referências/Reportagens por município` (cofre) — 42 municípios, 70 matérias de imprensa.
- Card de detalhe do município ganha seção **"Notícias"**, ao lado (não junto) da seção "Fontes" — mantém a separação decidida na Fase 8 entre estudo acadêmico (citação pública em "Fontes") e reportagem de jornal/revista/site (agora com seção própria, sem se misturar com a citação acadêmica).
- Não altera a tabela principal nem a coluna "Fontes" (que segue restrita a estudo acadêmico) — notícias aparecem só no card expandido do município selecionado.

## v0.4 (2026-07-27)

Rodada de ajustes estéticos + Fase 8 (repositório de estudos), em duas passagens no mesmo dia — a segunda corrige e substitui partes da primeira a partir do primeiro uso real do painel (feedback direto do autor). Mesma estrutura de banco (nenhuma coluna nova na base municipal em si — os dados novos usam agregados pré-computados à parte; ver nota abaixo).

**Identidade visual:**

- Paleta corrigida dos hex antigos (`#f43f6f`/`#ffd400`/`#2b50d9`) para os oficiais (`#FF2D6B`/`#F5E400`/`#1A54C7`), com `--verde` (`#6FBE44`) adicionado — alinhado com `pesquisa.html`/`index.html` (Fase 9.1 do ROADMAP).
- Status "Ativa" passou por verde e voltou para **amarelo** (mapa, tags, tabela, linha do tempo) — decisão final do autor após ver as duas opções; rosa marca só "Encerrada".
- Tema claro removido — painel passa a ser **só escuro**; toggle, CSS e lógica de tema retirados.
- Logo do PGT trocado da sigla (raster) para o logotipo extenso oficial (SVG); todos os logos do rodapé ampliados (34px → 46px).

**Estrutura e grandes números:**

- Seções colapsáveis (comparação TZ×Não-TZ, % por eixo, notas metodológicas — glossário já era) — permite ver mapa + tabela juntos (Fase 4.1).
- CTA de contribuição ("não achou seu município? envie um caso ou estudo") como rodapé da tabela de casos, apontando para `pesquisa.html` (Fase 6.1).
- Card "TZ ativas" agora deixa explícito que é sobre a camada **universal**; novo card "TZ parciais" (32 = 24 temporal-dias + 4 espacial-periférico + 4 grupo social — exclui de propósito as 324 gratuidades eleitorais/eventuais, fenômeno distinto). Card "TZ encerradas" e o filtro "Sede × satélite" removidos do topo.

**Card "Município selecionado":**

- "PDMU (2025)" renomeado para **"PlanMob (2025)"**; "Tarifa reconciliada" renomeado para **"Tarifa"**, mostrando "Gratuito (TZ universal)" nos municípios com TZ ativa em vez de "sem dado".

**Fase 8 — repositório de estudos:**

- Crosswalk estudo/fonte → município construído a partir de 11 arquivos de `casos por fonte` (Santini 2019, Pereira 2023, Angelo 2023, Vermander 2021, brinco 2017, NTU 2023/2025, reportagens por município, TZ fim de semana, TZ bairros periféricos, municípios com FFPT) — 88 municípios, 181 entradas no crosswalk bruto (`casos_por_fonte.json`). Ainda faltam incorporar outros arquivos da pasta (ver Pendências.md).
- **Citação pública restrita a artigos acadêmicos** (decisão do autor, 27/07/2026): a coluna "Fontes" da tabela e o card de detalhe do município mostram só entradas com tipo "Estudo acadêmico" (38 municípios, 69 entradas) — relatórios institucionais (NTU), reportagens de jornal/revista e levantamentos de coleta própria (ex.: planilha "Municípios com FFPT") ficam de fora da citação, mesmo constando no crosswalk bruto.
- Nova coluna "Fontes" na tabela de municípios, com expansão inline por linha, e seção "Fontes" no card de município selecionado. Das 3 formas de exibição testadas, o painel separado "Repositório de fontes por município" foi descartado (ficaram só coluna+expansão e card).
- Novo bloco **"Referências bibliográficas"** em formato ABNT NBR 6023 para os 5 estudos acadêmicos citados no crosswalk de fontes (Santini 2019, Pereira 2023, Angelo 2023, Vermander 2021, Brinco 2017) — citekeys conferidos em `biblioteca.bib`.

**Gráfico de partição modal:**

- Testados dois gráficos novos com dados do Censo 2022/DENATRAN (evolução da motorização em linha; meio de transporte em 5 barras separadas por modo); ambos foram descartados e substituídos por um único gráfico **"Partição modal — TZ × Não-TZ"**, uma barra 100% empilhada por grupo (TZ/Não-TZ), destacando Ônibus (azul) e Ativo = a pé + bicicleta (rosa) — únicas cores da identidade usadas, sem combinar com amarelo/verde; Automóvel/Motocicleta/Outros em neutros.
- ⚠️ Os agregados usados no gráfico foram **pré-computados à parte** (script avulso, não o pipeline `montar_html.sh`/`build_stats.py` — que não roda neste ambiente) — mover para o build regular quando rodar localmente, para não depender de números "congelados" na próxima atualização de dados.

**Dois gráficos novos** (dados novos de `base_municipal_v3.csv`, adicionados fora deste ambiente — ver Pendências.md 26/07):

- **Evolução da motorização (DENATRAN, 2013-2022), TZ × Não-TZ** — grupo TZ restrito, em cada ano, aos municípios já adotantes até aquele ano (mesma correção cronológica da Análise II do Cap. 2).
- **Meio de transporte (Censo 2022), TZ × Não-TZ** — % de deslocamentos por modo, mesmo critério de corte (TZ até 2022, n=73).
- ⚠️ Os dois gráficos usam **agregados pré-computados à parte** (script avulso, não o pipeline `montar_html.sh`/`build_stats.py` — que não roda neste ambiente) — mover para o build regular quando rodar localmente, para não depender de números "congelados" na próxima atualização de dados.

## v0.3 (publicada 2026-07-24)

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

Scripts em `scripts/` (`build_data.py`, `build_stats.py`) documentam como os dados embutidos no `painel.html` foram gerados a partir das fontes brutas. As fontes brutas (CSVs/XLSX) são parte do cofre de pesquisa privado do autor e **não estão incluídas neste repositório público** — os scripts servem como documentação do método, não para execução direta por terceiros. Ver também `FEEDBACK.md` para pendências de ajuste na visualização.
