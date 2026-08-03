# Changelog e notas de metodologia

O site tem páginas independentes, cada uma com seu próprio número de versão (ver arquitetura em `ROADMAP.md` § 0). **Tudo abaixo é sobre a página Painel Brasil (`painel.html`, tag TZ)** — é a única página com histórico até agora. Quando `rede-ge.html` (Rede da ARS) for publicada, ganha sua própria seção de changelog, separada desta.

## Política de versionamento

Regra completa (fases, patch/minor/major, hierarquia de precedência, nota de remapeamento v1/v2/v3 → v0.1/v0.2/v0.3) em [`VERSIONING.md`](./VERSIONING.md). A regra é uma só para todas as páginas do site; o que muda é que cada página conta seu próprio número.

## v0.4.04 (atual — 2026-08-03)

Ampliação do universo canônico da pesquisa (155→170 municípios TZ universal) + parágrafo descritivo de TZ por município. Estrutura de banco intacta (mesmas colunas) — patch, não minor.

**Ampliação do universo canônico:**

- A pesquisa somou **16 casos próprios** de duas varreduras (141 candidatos verificados em 31/07/2026; funil orçamentário via SICONFI em 03/08/2026): **15 municípios com TZ universal ativa** (Maracaí/SP, Jucás/CE, Centenário do Sul/PR, Lidianópolis/PR, Venda Nova do Imigrante/ES, Brodowski/SP, Engenheiro Beltrão/PR, Tarumã/SP, Pains/MG, Rio das Flores/RJ, São Sebastião da Grama/SP, Águas de São Pedro/SP, Pedregulho/SP, Quaraí/RS, Colina/SP) e **1 encerrada** (Getulina/SP, programa "AMIGÃO", 13/04/2026→27/07/2026, encerrado por baixa demanda). Nenhum desses 16 usa a expressão "tarifa zero" nas fontes — todos usam nome próprio de programa, o que já era invisível às buscas usadas até agora.
- **5 novos casos de TZ parcial** (régua descritiva): Andrelândia/MG e Embu das Artes/SP (temporal-dias); Áurea/RS e Magé/RJ (espacial); Parauapebas/PA (grupo social, caso de transição legislativa). Áurea e Magé têm reclassificação sinalizada como **provisória** (a confirmar pelo autor) — a régua descritiva original as descrevia como "TZ ativa" bruta, mas o serviço não é circular intraurbano típico; o painel mostra a ressalva no card de detalhe do município.
- **Teresina/PI excluída do universo universal**: é um programa **estadual** de Metrô/VLT, não Tarifa Zero de ônibus municipal — a pesquisa cobre só sistemas de ônibus (decisão do autor, 03/08/2026). O registro **não foi apagado** dos dados (`tz_status` passa a `"Excluída (Metrô/VLT estadual — fora de escopo, 03/08/2026)"`, uma string que não bate com `'Ativa'`/`'Encerrada'` e por isso não conta em `tz_bin`), só sai da tabela pública e dos destaques — critério que já vinha sendo usado para casos como o de São Caetano do Sul (base desatualizada vs. cofre). Teresina era, até então, o maior "sede TZ" do painel (866 mil hab.) — o destaque agora passa para Itapetininga/SP.
- Totais recalculados com a mesma lógica de `scripts/build_stats.py` (medianas, crosstabs, cortes por faixa/REGIC/arranjo/modelo, destaques) — não só os números do topo. Painel: **159 ativas + 10 encerradas = 169** municípios TZ universal (número um pouco abaixo do canônico do cofre, 170, por uma divergência pré-existente e não resolvida nesta rodada — Palmas-TO aparece 2× no arquivo-fonte como "Encerrada" com datas diferentes, mas o modelo de dados do painel tem uma linha por município). **33 municípios** com TZ parcial (era 28).
- **Achado de qualidade de dado, registrado:** o dataset municipal do painel (base MUNIC/IBGE) usa o nome pré-2007 "Embu" para o que hoje é oficialmente Embu das Artes/SP (mesmo código IBGE, 3515004) — `camadas_tz.json` ganhou uma chave duplicada (`"Embu|SP"`) só para não perder o cruzamento; o nome exibido no painel é o do dataset ("Embu"), o vault da tese mantém o nome atual correto.
- Genealogia completa, ressalvas e decisões (inclusive as 3 reclassificações provisórias) documentadas em `CLAUDE.md` e `Pendências.md` do cofre da tese — não duplicadas aqui, ver lá para o detalhe acadêmico.

**Novo: parágrafo descritivo de TZ por município:**

- O card "Município selecionado" ganhou um parágrafo gerado por template (não escrito à mão — cobre todos os municípios do painel, TZ ou não) logo abaixo do nome, explicando a situação de Tarifa Zero daquele município: universal ativa (com início e operador, se houver), encerrada (com período), parcial (com a(s) camada(s) e ressalva de reclassificação provisória, se houver), excluída por escopo (caso Teresina) ou sem TZ mapeada (com a ressalva de que o painel já mediu subnotificação em varreduras anteriores, então ausência aqui não é prova de ausência real). Implementado em `gerarParagrafoTZ()`, reaproveitando os mesmos campos já estruturados (`tz_status`, `tz_ano`, `tz_fim`, `tz_operador`, `camadasFor()`).

## v0.4.03 (2026-07-29)

Sub-patch de v0.4 (mesma exceção do v0.x.NN, ver `VERSIONING.md`): rodada de 8 pontos de melhoria pedidos pelo autor sobre o v0.4.02 ("Tudo nesta rodada (v0.4.03)"), cobrindo rodapé, identidade visual do mapa, régua descritiva, uma página nova de conceitos e um primeiro score de população.

**Rodapé — logo do Laplan + hiperlinks:**

- Logo do Laplan processado a partir do arquivo fornecido pelo autor (recorte + conversão seletiva de preto/cinza para branco, preservando o vermelho e a transparência) e adicionado ao rodapé de `painel.html`, `index.html` e `pesquisa.html`, no mesmo tratamento negativo já usado para PGT/UFABC. **Limitação conhecida:** o arquivo de origem é um recorte de thumbnail do WordPress que trunca o texto "LABORATÓRIO DE" antes do nome completo do instituto — usado assim por falta de um arquivo-fonte melhor.
- Todos os logos do rodapé (UFABC, PGT, Laplan, POLO) ganharam hiperlink para o site oficial de cada instituição, nas três páginas.

**Régua descritiva — gradação por saturação (substitui o contorno tracejado do v0.4.02):**

- O contorno tracejado amarelo (`.tzparcial`) do v0.4.02 foi identificado pelo autor como uma visualização ruim e foi substituído por **preenchimento em variação de saturação do amarelo** (`corParcial()`): quanto mais camadas parciais (2a/3/4) um município acumula, mais perto do amarelo pleno ele fica — sem nunca chegar lá, para não ser confundido com a universal. Gradação por **contagem de camadas**, não por tipo (não há hierarquia documentada entre 2a/3/4 na régua). Fica dentro da família do amarelo já usado para TZ ativa — não introduz cor nova, mantém a regra da identidade visual.
- Legenda do mapa (quando colorido por status de TZ) passa a mostrar 3 amostras de gradação (1/2/3 camadas) em vez do símbolo de contorno tracejado.

**Filtro por camada da régua:**

- Novo seletor "Régua descritiva (camada)" nos controles do painel — filtra o mapa e a tabela por universal (1), temporal-dias (2a), espacial-periférica (3) ou grupo social (4). Reage junto com os demais filtros (UF, faixa, REGIC, arranjo, modelo).

**Seção "TZ × Não-TZ" redesenhada:**

- Sai da coluna lateral do mapa e vira uma caixa de largura total, abaixo do mapa, com as métricas organizadas em **colunas** (grid responsivo) em vez de empilhadas — mesmo conteúdo (medianas por indicador), só reorganizado.

**Nova página `verbetes.html`:**

- Página pública nova, no mesmo padrão visual do site, com os 5 verbetes já liberados no cofre da tese: **Tarifa Zero**, **Grupos econômicos** (os dois pilares da hipótese) e **A Régua da Tarifa Zero** / **Régua Descritiva** / **Régua Analítica** (o instrumento de medição, Eixo 3). Lista, sem linkar, os outros 12 verbetes já escritos mas ainda represados pelo autor — mesma decisão de liberação progressiva já adotada no cofre (`Verbetes - MOC.md`).
- Link para a página adicionado no cabeçalho de `painel.html` e `pesquisa.html`, e como novo card na página inicial (`index.html`).

**Score: população abrangida pela Tarifa Zero (v1):**

- Nova seção no painel somando quantas pessoas têm algum acesso a alguma camada de TZ. Metodologia v1 aprovada pelo autor (29/07/2026): camada universal soma 100% da população residente do município; camada 4/grupo social soma uma **estimativa** só quando há dado defensável — hoje só Belo Horizonte e Uberlândia (passe estudantil), usando "estudo_total" do Censo 2022 (proxy de deslocamento para estudo, carregado em `camadas_tz.json`) como aproximação do número de beneficiários, não a contagem real.
- **Deliberadamente não somado:** as demais camadas parciais sem dado sub-municipal defensável (temporal-dias/2a, espacial/3, e o caso de Curitiba/desempregados na camada 4) — o painel lista esses municípios como "sem estimativa" em vez de estimar sem base. Gratuidades por lei federal (idoso/PcD) também não somadas nesta v1: a base municipal não tem população idosa/PcD por município (pendência registrada em `Pendências.md` do cofre, 29/07/2026).
- Card de detalhe do município passa a mostrar a população estimada (quando existente) junto de cada camada da régua descritiva.

**Ajustes pós-uso (mesmo dia, dois pontos pedidos pelo autor depois de ver o v0.4.03 em uso):**

- Tabela "Municípios com Tarifa Zero universal" renomeada para "Municípios com Tarifa Zero (universal + parcial)": além dos 155 registros/154 municípios únicos da base-mestre universal, agora lista os **28 municípios com camada parcial** (2a/3/4, `camadas_tz.json`) que ainda não estavam no bucket universal — mesma regra de exclusividade já usada no card "TZ parciais" e no mapa (evita duplicar, por exemplo, Palmas e São Caetano do Sul, que a base principal já classifica como Ativa/Encerrada). Nova tag "Parcial" (amarelo) na coluna Situação; coluna "Início" usa uma extração best-effort de ano a partir do texto de "detalhe" de cada camada — 14 dos 28 municípios têm um ano identificável, os demais ficam "—" (sem inventar data).
- Cor de TZ ativa volta a ser **verde** (era amarelo desde a Fase 9) — mapa, tags, tabela e linha do tempo; amarelo fica reservado à gradação de TZ parcial (`corParcial`, acima), rosa continua em Encerrada/revogação. **Nota de identidade visual:** essa combinação usa verde + amarelo + rosa no mesmo painel, o que a princípio conflita com a regra de "nunca combinar duas das três cores (amarelo/azul/verde) entre si" da nota "Identidade Visual da Pesquisa" — regra pensada para peças gráficas isoladas (cartaz, slide), não para um painel com várias camadas de informação simultâneas que precisam ser distinguíveis. Registrado aqui como exceção deliberada, a formalizar na nota de identidade visual se o autor confirmar o critério para painéis multi-camada.
- Linha do tempo ganha o início das TZ parciais (amarelo), **empilhado** sobre a barra da universal (verde) em cada ano, com uma única escala vertical compartilhada — usa o mesmo `camadaAnoInicio()` da tabela. Primeira tentativa desenhou as duas séries lado a lado com escala própria cada uma; o autor notou que isso distorcia a leitura (uma barra pequena parecia tão alta quanto uma grande de outra série) — corrigido para empilhado/escala única no mesmo dia. Casos sem data identificável (passe estudantil de BH/Uberlândia, desempregados de Curitiba) não entram no gráfico. Revogações continuam abaixo do eixo, em rosa.
- Ordem de empilhamento das camadas no mapa reorganizada: não-TZ (base) → ativa → parcial → encerrada (topo) → limites de UF, cada uma em seu próprio grupo SVG (antes, ativa e encerrada dividiam um grupo único e parcial ficava junto do não-TZ). Legenda reordenada para acompanhar: Ativa, Parcial (1/2/3 camadas), Encerrada, Não TZ.
- Rampa de cor do parcial invertida: amarelo mais forte com **1** camada, decaindo (mais próximo do neutro) conforme acumula camadas — antes era o oposto (mais fraco com 1, mais forte com 3+).
- Linha do tempo ganha tooltip customizado (reaproveita o mesmo `#tooltip` do mapa) que lista os municípios ao passar o mouse sobre qualquer segmento da barra (universal, parcial ou revogação) — antes só mostrava a contagem via `<title>` nativo do SVG.
- Rodapé reestruturado em `painel.html`, `index.html`, `pesquisa.html` e `verbetes.html`: nomes (autor + orientadora) agora ficam agrupados de um lado (`.fnames`, empilhados), logos institucionais do outro (`.flogos`) — antes o autor ficava misturado com os logos de um lado e só a orientadora do outro, layout assimétrico. Logo da UFABC trocado da variante "sigla-lateral" (proporção ~1,64, lia-se pequena/quadrada) para a "extenso" (proporção ~4,95), agora com peso visual comparável a PGT/Laplan na mesma altura fixa de 46px.
- `verbetes.html`: removido o bloco de observação "Mais 12 verbetes escritos, ainda represados" — a decisão de liberação progressiva continua válida, só a caixa de aviso sobre os não publicados saiu da página pública.
- `FEEDBACK.md` e `ROADMAP.md`: identidades dos 5 leitores que deram feedback (nomes reais) substituídas por rótulos de papel (Colega 1-5, por ordem de 1ª aparição cronológica) em ambos os arquivos — são rastreados num repositório público (github.com/tvzgomes-2/painel_tz). A checklist de status que existia em `FEEDBACK.md` (desatualizada, parava em 25/07) foi removida de lá para não duplicar/divergir do que já é mantido aqui e no `ROADMAP.md`; `FEEDBACK.md` agora guarda só os relatos brutos, e o `ROADMAP.md` ganhou colunas de Status nas tabelas das Fases 1-3 (Fase 4 já tinha) para centralizar o que foi/não foi implementado.

## v0.4.02 (2026-07-29)

Sub-patch de v0.4 (mesma exceção do v0.x.NN, ver `VERSIONING.md`): leva a régua descritiva ampliada — além da universal — para o painel, a pedido do autor. Mesma estrutura de banco (novo crosswalk à parte, `camadas_tz.json`, mesmo padrão de `casos_por_fonte.json`/`casos_por_noticia.json`).

**Régua descritiva ampliada no mapa e no card de município:**

- Novo crosswalk `camadas_tz.json` — 30 municípios com camada 2a (temporal-dias, 24), 3 (espacial-periférica, 4) ou 4 (grupo social, 4) = 32 entradas (Belo Horizonte tem as três). Fontes: `camada2a_temporal_dias_analise.csv` e `tz_bairros_perifericos.csv` (cofre, `03 - Dados/_data/`) + a nota "Tipologias de Tarifa Zero (4 camadas)" para a camada 4 (sem CSV dedicado ainda).
- **Exclui de propósito a camada 2b/temporal-eventos** (324 gratuidades eleitorais/pontuais, decisão do STF) — mesma decisão já tomada para o card "TZ parciais" na Fase 8: é adesão por obrigação judicial, não escolha municipal, misturar inflaria o número e mudaria o sentido do que está sendo medido.
- **Mapa:** município com camada parcial e sem TZ universal ganha contorno tracejado amarelo (`.tzparcial`) — visualmente distinto do contorno sólido de TZ universal (`.tzpath`), sem introduzir cor nova (mesmo amarelo da identidade). Legenda atualizada quando o mapa está colorido por status de TZ.
- **Card de município:** nova seção "Camada da régua descritiva", ao lado de Fontes/Notícias, com o detalhe de cada camada e, quando existente, um alerta de conflito com a base principal.
- **Card "TZ parciais":** deixa de ser um número estático nacional (32, sem recorte por município) e passa a contar dinamicamente pelo crosswalk, reagindo ao filtro atual (UF/faixa/REGIC/arranjo/modelo) como os demais cards.
- **Achado de consistência (não resolvido aqui):** 2 dos 30 municípios têm conflito com a base principal — **São Caetano do Sul** ainda consta "Ativa" (universal) na base, mas já é grupo social desde a revogação de 15/07/2026; **Florianópolis** consta "Encerrada" (universal) na base, mas os dados novos sugerem que era, na verdade, temporal-dias (camada 2a) — sinalizado como "REVER" no crosswalk, não alterado no `tz_status` principal sem confirmação do autor. Por isso o card "TZ parciais" (28) exclui esses 2 para não contar duas vezes — ver comentário no código.

## v0.4.01 (2026-07-28)

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

Scripts em `scripts/` (`build_data.py`, `build_stats.py`) documentam como os dados embutidos no `painel.html` foram gerados a partir das fontes brutas. As fontes brutas (CSVs/XLSX) são parte do cofre de pesquisa privado do autor e **não estão incluídas neste repositório público** — os scripts servem como documentação do método, não para execução direta por terceiros. Ver `ROADMAP.md` (Fases 1-5) para o status de cada pendência de visualização; `FEEDBACK.md` guarda só os relatos brutos que originaram esses itens.
