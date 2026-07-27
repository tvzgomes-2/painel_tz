# Análise e plano de melhorias — Site Tarifa Zero e Grupos Econômicos

Nota de planejamento do projeto. Consolida a análise técnica do painel v0.2, o feedback recebido de 5 leitores ([`FEEDBACK.md`](./FEEDBACK.md)) e o pedido da orientadora (mais gráficos e grandes números). Organizada em fases priorizadas por consenso × esforço.

*Escrita em 24/07/2026. Painel analisado: v0.2 (publicado em https://tvzgomes-2.github.io/painel_tz/).*

**Reestruturado em 26/07/2026** para organizar o backlog pelas 4 páginas do site (índice/hub, Painel Brasil, Rede da ARS, Pesquisa colaborativa) em vez de uma lista única de fases — ver Seção 0 e Registro de decisões. Os números de Fase originais foram preservados (não renumerados) para não quebrar as referências já feitas neste documento.

---

## 0. Arquitetura do site *(decidido 25/07/2026; refinado 26/07/2026)*

O repositório passou de "um painel" para **um site com páginas independentes**, cada uma com seu próprio banco de dados e seu próprio número de versão:

- **`index.html`** — hub do site. Página pequena, editada à mão (não gerada por script), com o resumo da pesquisa e um card de acesso por página. Mostra só as páginas já publicadas.
- **`painel.html`** (tag **TZ**, "Painel Brasil") — panorama nacional de Tarifa Zero. É o que antes se chamava `index.html`; todo o conteúdo da Seção 1 abaixo é sobre esta página especificamente. Gerado por `scripts/montar_html.sh`, não editar direto.
- **`rede-ge.html`** (tag **GE**, "Rede da ARS", planejado) — estrutura de poder dos grupos econômicos do transporte coletivo (rede societária/CNPJ da tese). Escopo confirmado 26/07/2026 (era ambíguo — resolvido: é a rede de sócios, não monitoramento de redes sociais). Primeiro rascunho recebido (visualização D3.js de rede, ~7.680 empresas do núcleo + mundo pequeno via sócios) em `rede-ge-rascunho/` (fora do git — ver Seção 2). Ainda não é o `rede-ge.html` publicado; só aparece no hub quando estiver pronto (sem placeholder "em construção" clicável — o card já existe no hub, mas sem link, para sinalizar que vem por aí).
- **`pesquisa.html`** ("Pesquisa colaborativa", formulário de contribuição) — do ponto de vista de **navegação**, não é um card do hub: é acessada como uma camada/CTA a partir do Painel Brasil (ex.: "não achou seu município? envie um novo caso ou estudo"), não uma página que o leitor visita direto pelo `index.html`. Do ponto de vista de **desenvolvimento**, porém, é tratada nesta ROADMAP como a 4ª página do site — arquivo próprio (`pesquisa.html`, editado à mão, como o `index.html`), backlog próprio (Seção 3) e histórico próprio — pelo mesmo motivo de `painel.html`/`rede-ge.html`: conteúdo e ciclo de vida independentes. Ainda sem número de versão publicado (ver `VERSIONING.md`). *(Decisão de escopo confirmada em 26/07/2026 — ver Registro de decisões.)*

**Versionamento:** a regra em `VERSIONING.md` é uma só, mas cada página conta seu próprio número (Painel Brasil segue de v0.3; Rede da ARS e Pesquisa colaborativa começam do zero quando publicadas). O site como um todo não tem número de versão — tem uma **era**, nomeada com modo de transporte em ordem alfabética (**Era Andarilho**, letra A, é a atual), trocada só quando acontece um evento "major" na definição do VERSIONING.md (novo painel irmão publicado, ou redesign completo de alguma página).

---

## 1. Página: Painel Brasil (TZ)

### 1.1 Diagnóstico do estado atual

#### O que está funcionando (confirmado pelo feedback)

- **Ordenação por clique na tabela TZ** — elogiada explicitamente (Carol); manter.
- **Notas metodológicas** — apontadas como diferencial útil (Gabriel); manter e não cortar.
- **Legibilidade geral dos dados** — "bem fáceis de analisar" (Gabriel), "ficou muito bom" (Ivan).
- **Arquitetura de arquivo único** — abre em qualquer navegador, publica como página estática, zero dependência.

#### Fragilidades identificadas (feedback + análise técnica)

**Mapa (o bloco com mais críticas — 4 dos 5 leitores):**

1. Sem bordas estaduais — pedido 3× (Ivan 2×, Carol). Ao filtrar, municípios "flutuam" sem referência geográfica.
2. Bordas municipais quase invisíveis (stroke escuro 0.3px sobre fundo escuro) — "difícil ver assim muito escuro" (Carol).
3. Sem zoom/pan — pedido 2× (Daniel, Ricardo). Na escala nacional é impraticável clicar num município do Sudeste (Ricardo não achou São Caetano do Sul).
4. Tooltip mostra só a métrica do "colorir por" — Ivan quer os dados completos do município no hover.
5. Tooltip responde a municípios fora do recorte quando há filtro de UF ativo (Ricardo).
6. Estética "de Excel" (Ivan) — sem destaque visual para os municípios TZ, que são o assunto do painel.

**Gráficos e leitura estatística:**

7. Os dois blocos de barras (comparação TZ×Não-TZ e % por eixo) usam a mesma linguagem visual mas respondem perguntas diferentes — o olho tenta comparar o que não é comparável (Daniel).
8. No bloco "% por eixo", o `n=` junto da % sugere comparabilidade absoluta entre categorias; falta dizer que a proporção é *dentro* de cada categoria (Daniel).
9. Associação visual barra↔rótulo ambígua no bloco "% por eixo" — rótulo mais perto da barra errada (Daniel).
10. **Cards de resumo são estáticos** — não reagem aos filtros. Quando se seleciona uma UF, os "grandes números" continuam nacionais. É exatamente a lacuna que o pedido da orientadora expõe.
11. **Nenhum gráfico temporal** — a base tem `tz_ano` (ano de início) e `tz_fim` para os 154 municípios, mas o painel não mostra a linha do tempo de adoções/revogações. É provavelmente o gráfico de maior valor analítico ausente.

**Estrutura e acesso:**

12. Página muito longa — sem colapsar seções, não dá pra ver mapa + tabela juntos (Ivan).
13. Cards e controles desalinhados — grids diferentes (Carol).
14. Títulos de seção pouco destacados (Carol, Gabriel).
15. Siglas sem explicação para leigos — IBEU, IDH, PDMU, REGIC, NTU, arranjo metropolitano (Ricardo).
16. Espaçamento apertado entre mapa e painel lateral (Gabriel).
17. Só tema escuro — Gabriel prefere claro (gosto pessoal, sem consenso; tratar como opção, não troca).

**Dados (registrado, não é retrabalho do painel):**

18. Duplicata Palmas-TO no arquivo-mestre (155 vs 154) e São Caetano do Sul desatualizado — pendências na fonte, documentadas no CHANGELOG.
19. Variável de presença de grupo econômico por município ainda ausente — o painel descreve correlações, não testa a hipótese central.

### 1.2 Plano de melhorias por fase

Critério de priorização: nº de pessoas que pediram × valor analítico × esforço técnico. Fases 1–2 são pré-requisito de qualidade; a Fase 3 é o pedido da orientadora e a maior entrega de valor novo.

#### Fase 1 — Legibilidade e correções rápidas *(só CSS/texto; esforço baixo)*

| # | Item | Origem |
|---|------|--------|
| 1.1 | Título maior + acrescentar "(TZ)" após "Tarifa Zero" | Ivan (2×) |
| 1.2 | Títulos de seção maiores/negrito (h2 e o "TZ × Não-TZ") | Carol, Gabriel |
| 1.3 | Alinhar cards de resumo com a linha de controles (mesmo grid) | Carol |
| 1.4 | Bloco "% por eixo": subtítulo explicando que a % é calculada dentro de cada categoria; reposicionar rótulo→barra sem ambiguidade | Daniel |
| 1.5 | Glossário de siglas (IBEU, IDH, PDMU, REGIC, NTU, arranjo) — painel colapsável antes das notas metodológicas | Ricardo |
| 1.6 | Mais respiro entre mapa e painel lateral (gap do grid) | Gabriel |

#### Fase 2 — Mapa *(o bloco mais criticado; esforço médio)*

| # | Item | Nota técnica |
|---|------|--------------|
| 2.1 | **Bordas estaduais sempre visíveis** | Derivar camada de UF dissolvendo os municípios no mapshaper (`-dissolve`) — acréscimo estimado de ~100–200 KB no topojson; desenhar como camada de linha acima dos municípios |
| 2.2 | Bordas municipais mais claras (stroke mais visível) | Só CSS |
| 2.3 | Destaque dos municípios TZ **sem glow** (decisão do autor, 24/07/2026): usar borda/stroke mais forte e clara nos TZ ativos | Substitui o "outer glow" pedido pelo Ivan — glow descartado por preferência estética e risco de performance; o objetivo dele (TZ saltar aos olhos, tirar a "cara de Excel") é atendido por contorno destacado |
| 2.4 | **Auto-encaixe do mapa na seleção** (decisão do autor, 24/07/2026 — no lugar de zoom/pan livre): ao filtrar uma UF, o mapa enquadra automaticamente a UF; duplo clique num município dá zoom local; botão "↺ Brasil" volta ao enquadramento nacional | Animação do viewBox pro bounding box do recorte; determinístico (todos veem o mesmo enquadramento, prints reproduzíveis), sem conflito pinça×rolagem no celular; resolve os dois casos relatados (Daniel e Ricardo) |
| 2.5 | Tooltip completo nos municípios TZ (situação, início, REGIC, arranjo, pop, PIB pc, motorização) | Reusar os dados já embutidos |
| 2.6 | Suprimir tooltip/hover fora do recorte quando há filtro ativo | Checagem no handler de mousemove |

#### Fase 3 — Grandes números e novos gráficos *(pedido da orientadora; esforço médio-alto, maior valor novo)*

| # | Item | Detalhe |
|---|------|---------|
| 3.1 | **Cards dinâmicos (grandes números que reagem ao recorte)** | Ao filtrar UF/faixa/REGIC, os cards recalculam: nº de municípios no recorte, nº TZ ativas, % TZ, **população vivendo com TZ** (soma da pop dos municípios ativos — número forte para apresentações), PIB pc mediano do recorte |
| 3.2 | **Linha do tempo de adoções** | Gráfico de barras/linha por ano de início (`tz_ano`), com revogações marcadas — mostra a aceleração recente da política, hoje invisível no painel |
| 3.3 | TZ por região e por UF | Barras horizontais simples (contagem + %), completando os eixos já existentes |
| 3.4 | Gráfico de dispersão PIB pc × motorização | Pontos = municípios, TZ destacados em cor — visualiza a comparação que hoje só existe como mediana em barra |
| 3.5 | Diferenciar visualmente os dois blocos de barras | Trocar a forma de um deles (ex.: % por eixo vira dot plot ou barras com escala explícita 0–100%) para separar "comparação pareada" de "proporção por categoria" (Daniel) |

#### Fase 4 — Estrutura e conforto *(esforço baixo-médio)*

| # | Item | Status |
|---|------|--------|
| 4.1 | Seções colapsáveis (comparação, % por eixo, glossário, notas) — permite ver mapa + tabela juntos (Ivan) | ✅ Implementado 26/07/2026 — `<details><summary>`, abertas por padrão (`open`), estilo reaproveita `.panel h2`; glossário já usava o padrão antes |
| 4.2 | Toggle tema claro/escuro (preferência do Gabriel vira opção sem impor a ninguém) |
| 4.3 | Revisão mobile: painel foi lido no celular (print do Ivan) — conferir touch no mapa, tabela com rolagem horizontal |

#### Fase 5 — Dados futuros e melhorias adiadas *(fora do escopo imediato)*

- Zoom/pan livre no mapa (roda do mouse/pinça + arrastar) — adiado em favor do auto-encaixe (item 2.4); reavaliar só se leitores sentirem falta de exploração livre após a Fase 2.
- Viagens antes × depois da adoção (Ivan) — exige série temporal de demanda por município; não existe na base.
- Investimento em infra antes × depois (Ivan) — idem, possível recorte via FINBRA série 2019–2023 já coletada (explorar antes de descartar).
- **Variável de presença de grupo econômico por município** (rede ARS/CNPJ) — quando integrada, vira o eixo central do painel e o teste da hipótese da tese.
- Correções na fonte: duplicata Palmas-TO e situação de São Caetano do Sul (base-mestre).

#### Fase 8 — Repositório de estudos e enriquecimento *(prioridade imediata, criada 26/07/2026)*

| # | Item | Status |
|---|------|--------|
| 8.1 | Mapear qual estudo acadêmico/grey literature (NTU, Ministério das Cidades etc.) pesquisa qual município | ✅ Parcial 26/07/2026 — crosswalk com 11 dos ~19 arquivos de `casos por fonte` (88 municípios, 181 entradas); faltam `Completude das fichas.xlsx`, `Dataverse Santini/`, `Passe.Livre.nas.Eleicoes.xlsx`, `Quadro TZ Brasil.xlsx`, `Tabela_A_1_-_Entrevistas...csv`, `cidades com tarifa zero universal no Brasil - 2024.xlsx`, `observatório TZ.csv` |
| 8.2 | Validar se a base atual suporta a relação N:N estudo↔município; se precisar mudar estrutura, sobe **minor** (ver VERSIONING.md) | ✅ Resolvido por fora da base municipal — o crosswalk vive num JSON à parte (`scripts/casos_por_fonte.json`, chave `Município\|UF`), sem alterar `base_municipal_v3.csv`; não conta como mudança estrutural, ficou como patch (v0.4) |
| 8.3 | Desenhar a visualização no painel (ex.: "este município tem N estudos vinculados", com lista) | ✅ Implementado 26/07/2026 (3 opções testadas) → 27/07/2026 decidido: ficaram a coluna "Fontes" com expansão inline na tabela e a seção "Fontes" no card de município; o painel separado "Repositório de fontes por município" foi removido. Bloco de referências ABNT dos estudos acadêmicos citados adicionado como seção própria. |
| 8.4 | **Legislação da TZ por município** (pedido 27/07/2026) — já existe levantamento em [[Analise Legislacao Tarifa Zero]] (cofre da tese: `04 - Análises/Pesquisa legal/`), 137 municípios, 62 com norma identificada. Antes de trazer ao painel: atualizar da base de 137 para os 155 canônicos (por código IBGE, não nome) e decidir o formato de exibição — provavelmente reaproveitando a arquitetura de crosswalk já criada em 8.1-8.3 | ⏳ Registrado como pendência em [[Pendências]] (cofre da tese); implementação ainda não iniciada |

---

## 2. Página: Rede da ARS (GE)

### Fase 9 — Corrigir e unificar o rascunho *(recebido 26/07/2026, não publicável ainda)*

**Decisões do autor (26/07):** não usar as versões "enxutas" (Empresa→Sócio, Sócio→Empresa) — foram só a base de construção deste arquivo completo, não entram no site. Foco: tornar o rascunho mais rápido e funcional, com análise de UX; a rede deve virar uma "janela" dentro da página (como o mapa coroplético é uma janela dentro do Painel Brasil), com outras informações sobre a rede e as empresas do setor ao redor dela — não uma tela cheia isolada.

**Análise técnica do rascunho (21.571 nós, 17.503 ligações):**

| # | Achado | Recomendação |
|---|------|--------------|
| 9.1 | **Paleta correta** — o rascunho usa os hex certos da identidade (`#0E0E10`/`#FF2D6B`/`#1A54C7`/`#F5E400`/`#FAF9F5`); `painel.html`/`index.html` usavam uma paleta antiga (`#0b0b0e`/`#f43f6f`/`#ffd400`/`#2b50d9`) | ✅ Corrigido 26/07/2026 no Painel Brasil (`head.html`/`logic.js`/`painel.html`) — ver Registro de decisões. `index.html` ainda não conferido/corrigido. |
| 9.2 | **Arquitetura de renderização já é boa**: usa `<canvas>` (não milhares de nós SVG no DOM), `d3.quadtree()` para hit-test eficiente no hover/clique, e o layout de força roda em lotes via `requestAnimationFrame` (não trava a thread) | Manter essa base — não é o gargalo principal |
| 9.3 | **Peso do arquivo (5,4 MB) é quase todo um único `RAW` JSON** com chaves repetidas por registro (`id`, `label`, `kind`, `tipo`, `componente`, `tam_componente`, `capital`, `porte` × 21.571 nós) | Converter para formato colunar (mesmo padrão já usado em `municipios_dados_col.json` do Painel Brasil) — deve cortar boa parte do peso sem perder dado |
| 9.4 | **Layout de força calculado no navegador a cada carregamento** (~21k nós) — é provavelmente a causa do "alguns segundos" de espera ao ligar "mostrar rede completa" | Pré-calcular o layout (posições x/y) uma vez, em build/script, e embutir as posições prontas — mesma filosofia do Painel Brasil (geometria pré-processada, não recalculada em tempo real) |
| 9.5 | Busca (`input` na caixa de texto) filtra os 21k nós a cada tecla, sem debounce | Adicionar debounce curto (~150-200ms) — melhoria pequena, mas barata |
| 9.6 | **Redesenho estrutural pedido pelo autor**: a rede vira uma "janela" (como o mapa do Painel Brasil) dentro de um layout tipo dashboard — cards de KPI (nº empresas, nº sócios, capital social, maior agrupamento — já existem como painel lateral, migram para cards fixos), tabela/lista de empresas do setor, notas metodológicas — replicando a gramática visual já usada em `head.html`/`logic.js` (`.grid`, `.card`, `.panel`, `.rightcol`) em vez de tela cheia com painel deslizante | Maior item da Fase — replanejar como um novo `head-ge.html`/`logic-ge.html` seguindo o padrão de construção do Painel Brasil (fonte legível + build), não editar o HTML autocontido direto |

### Fase 6.2 — Link cruzado com o Painel Brasil *(futuro, depende de publicação)*

| # | Item | Depende de |
|---|------|-----------|
| 6.2 | Link cruzado para a Rede da ARS a partir do Painel Brasil (ex.: ao ver um município TZ, mostrar se algum grupo econômico mapeado atua ali) | Página `rede-ge.html` publicada |

---

## 3. Página: Pesquisa colaborativa (Form)

Formulário único de contribuição (`pesquisa.html`) — aceita estudo acadêmico, grey literature, dado operacional de empresa ou sugestão de novo caso municipal, com revisão antes de incorporar ao Painel Brasil.

**Estado atual (26/07/2026):** incorporados os campos específicos do antigo levantamento em Microsoft Forms ("Mapeamento Bibliográfico sobre Tarifa Zero no Brasil") como referência de campo — Autoras(es) e Ano de publicação (fieldset "Detalhes da contribuição"), Foco principal do texto e Empresas operadoras/grupos econômicos citados (novo fieldset "Foco e atores citados") — sem replicar a estrutura de 3 páginas/blocos do MS Form original, que ficava restrito a mapeamento bibliográfico. O MS Form em si também está incompleto (campo "Tipo de Documento" com uma única opção cadastrada, uma pergunta de página 2 ainda sem título) — não é fonte de verdade, só ponto de partida.

#### Fase 1 (Form) — Ativar o envio

| # | Item | Status |
|---|------|--------|
| 1.1 | Configurar o backend de envio (Formspree) — endpoint `https://formspree.io/f/xpqvkqnk` criado pelo autor | ✅ Configurado 26/07/2026. Integração via **Vanilla JS/AJAX** (`@formspree/ajax` por CDN, sem bundler — condizente com o site ser HTML/CSS/JS puro publicado no GitHub Pages), não a versão "Basic HTML" (que recarregaria a página no domínio do Formspree) nem React (não há bundler/framework no repositório). `action`/`method` no `<form>` continuam como fallback caso o JS não carregue. Adicionados `data-fs-field`/`data-fs-error` nos campos obrigatórios (nome, e-mail, título, descrição) e `data-fs-success`/`data-fs-error` de formulário, estilizados com as cores da identidade (verde=sucesso, rosa=erro) em vez do visual padrão da lib |
| 1.2 | Testar o envio ponta a ponta com o backend configurado | ⏳ Pendente — envolve gerar uma submissão real no Formspree do autor; perguntar antes de disparar um teste |

#### Fase 2 (Form) — Revisão de conteúdo

| # | Item | Status |
|---|------|--------|
| 2.1 | Revisar o texto final de todas as perguntas | ⏳ Pendente — aviso removido (2.2) a pedido do autor antes da revisão de texto propriamente dita, para não expor o aviso a testadores reais; o texto das perguntas ainda não passou por revisão final |
| 2.2 | Remover o aviso de rascunho | ✅ Removido 26/07/2026, a pedido do autor (ver Registro de decisões) — antecipado em relação ao plano original (que previa remover só depois de 2.1 concluído) |

#### Fase 6.1 — CTA contextual no Painel Brasil *(depende da Fase 1)*

| # | Item | Status |
|---|------|--------|
| 6.1 | CTA contextual "não achou seu município? envie um novo caso ou estudo" dentro do painel, apontando para `pesquisa.html` | ✅ Implementado 26/07/2026 — como rodapé da tabela de casos TZ (opção usada entre as duas exemplificadas), não no painel de detalhe do município. Bloco `.cta-pesquisa` (borda rosa, botão de destaque), replicado em `head.html` e `painel.html` |

---

## 4. Identidade institucional e créditos *(cross-page — UFABC autorizado 26/07/2026; Laplan pendente)*

⚠️ **Pendência aberta (26/07/2026): o rodapé de créditos ainda não satisfaz o autor.** Já passou por 3 rodadas de ajuste (tamanho dos logos, reagrupamento do espaçamento, correção do logo da Polo) e o autor segue insatisfeito, sem um ponto específico novo apontado na última rodada — ver item 7.9. Não tratar como resolvido só porque os itens técnicos abaixo estão ✅; falta uma reavaliação mais de fundo (possivelmente redesenho, não só CSS pontual) antes de considerar esta seção fechada.

Aplica-se ao site como um todo. **Decisão 26/07/2026:** a linha de logos institucionais (UFABC + PGT + Laplan) e a linha de apoio técnico (Polo) são replicadas em **todas as páginas publicadas** (`painel.html`, `index.html`, `pesquisa.html`) — não só no Painel Brasil. Informações específicas de cada página (ex.: linha de "Fontes" de dados do Painel Brasil, versão v0.3) **não** são replicadas, só o bloco de créditos institucionais. `index.html` e `pesquisa.html` não têm toggle claro/escuro (são páginas de tema único), então mostram sempre a versão negativa dos logos — sem necessidade da lógica `html[data-theme="light"]`.

| # | Item | Status |
|---|------|--------|
| 7.1a | Autorização da orientadora para uso do logo **UFABC** | ✅ Recebida 26/07/2026 |
| 7.1b | Autorização para uso do logo **Laplan** | ⏳ Pendente (único logo ainda faltando na seção de créditos) |
| 7.2 | Logo UFABC — versão **negativa** (branco+amarelo, fundo escuro) e **principal** (verde+amarelo, fundo claro), SVG/EPS/PNG, 3 layouts cada (extenso, sigla-abaixo, sigla-lateral) — salvos em `assets/logos/ufabc/{negativo,principal}/` | ✅ Completo 26/07/2026 (as duas variantes de tema resolvidas) |
| 7.3 | Seção de créditos no Painel Brasil: autoria, orientação, instituições de apoio (UFABC, Laplan), apoio técnico (Polo Planejamento), fonte de dados — logo troca entre negativa/principal conforme o toggle de tema | ✅ Implementado 26/07/2026 em `head.html`/`painel.html`. Laplan como texto "(logo em autorização)", sem imagem, até 7.1b |
| 7.5 | Logo **Polo Planejamento** — inicialmente recebido como lockup combinado "POLO + TcUrbes" (marca-irmã, submarca de serviço); depois de conferir o `AF POLO-TC MANUAL-IDENTIDADE v3.8.pdf` (p.11 e 55-57), ficou claro que "TcUrbes" é uma submarca separada com ícone e mínimo de tamanho próprios, e o "TC" fica ilegível em qualquer redução de rodapé. Recortado para usar só o ícone + "POLO" (a unidade mínima legível definida no manual, p.11), extraído do SVG oficial sem redesenhar nada. Versão negativa (branco) e colorida/principal (ícone azul `#2997C1` + texto cinza `#46494A`), salvas em `assets/logos/polo/{negativo,principal}/logo-polo-icon-{negativo,principal}.svg` | ✅ Corrigido 26/07/2026 — os arquivos "POLO TC" completos (svg antigo) ficaram no repositório, sem uso |
| 7.6 | Logo **PGT (sigla) corrigido.** A versão anterior (23/07) era uma reconstrução livre em texto (fonte Poppins, cores aproximadas), não uma reprodução fiel — apontada pelo autor como de baixa qualidade. Substituída por um recorte/recoloração feita a partir dos arquivos originais reais: monograma extraído em alta definição do arquivo negativo (`ppgt_300-1.png`, 300×300, branco monocromático) e coloração (P+G em vermelho `#E5322C`, T em preto) inferida do arquivo colorido original de baixa resolução (`Prancheta_1dialogiod.jpg`, 184×110, a mesma fonte que o ROADMAP já registrava como "ilegível"). Resultado: PNG (não SVG — vetorização não foi possível neste ambiente, ver nota abaixo), salvo em `assets/logos/pgt/{negativo,principal}/logo-pgt-sigla-{negativo,principal}.png`, substituindo a referência no rodapé. Os SVGs falsos anteriores foram mantidos no repositório (não apagados), só deixaram de ser referenciados. | ✅ Corrigido 26/07/2026 — pendente: extenso (monograma + texto completo) segue com o mesmo problema antigo, não foi tratado nesta rodada |
| 7.7 | Rodapé de créditos reestruturado: logos institucionais (UFABC + PGT + Laplan) passaram para a mesma linha do nome do autor e da orientadora, agrupados num bloco só à esquerda (evita o vão duplo de um `space-between` de 3 itens); Polo + texto "Apoio técnico" viraram uma linha própria abaixo. Tamanho dos logos aumentado (24px → 34px em ambas as linhas), a pedido do autor ("achei os logos pequenos") | ✅ Implementado 26/07/2026 em `head.html`/`painel.html` |
| 7.8 | Linha de logos institucionais (UFABC + PGT + Laplan) e linha de apoio técnico (Polo) replicadas em `index.html` e `pesquisa.html`, seguindo o mesmo padrão do Painel Brasil — só o bloco de créditos, não a linha de fontes/versão (específica do Painel Brasil) | ✅ Implementado 26/07/2026 |
| 7.4 | Regras de uso obrigatórias (Manual de Identidade Visual UFABC, ago/2018): nunca redesenhar/recolorir a marca (usar sempre o arquivo oficial); tamanho mínimo 1,5cm de largura; manter área de interferência (margem de respiro) ao redor; em fundo escuro usar a negativa colorida (branco+amarelo, já a que temos) | Regra a seguir na implementação de 7.3 |
| 7.9 | **Revisar o rodapé de créditos de novo — autor ainda não satisfeito**, mesmo depois de 7.5/7.6/7.7/7.8. Antes de mexer de novo, vale perguntar ao autor o que especificamente incomoda agora (pode não ser mais logo/espaçamento) e considerar se o problema é de CSS pontual ou de concepção (talvez o bloco de créditos esteja tentando mostrar informação demais numa faixa muito fina) | ⏳ Aberto 26/07/2026 |

---

## 5. Riscos e cuidados

- **Tamanho do arquivo:** hoje 4,4 MB (Painel Brasil); camada de UF e novos gráficos acrescentam pouco (~5%), mas monitorar — o limite prático de conforto em 4G é ~10 MB.
- **Auto-encaixe × tooltip:** com o viewBox mudando no auto-encaixe/duplo clique, recalibrar posição do tooltip e hit-areas.
- **Não perder o que funciona:** ordenação da tabela, notas metodológicas e arquitetura de arquivo único são elogiados — nenhuma fase deve sacrificá-los.
- **Cards dinâmicos e n pequeno:** ao filtrar recortes com poucos municípios TZ (ex. uma UF com 1–2 casos), os grandes números podem sugerir robustez que não existe — exibir sempre o `n` junto e, abaixo de um limiar, sinalizar "amostra pequena".

## 6. Registro de decisões

- **24/07/2026 — v0.3 entregue.** Fase 1 completa; Fase 2 completa (com contorno no lugar do glow e auto-encaixe no lugar de zoom/pan); da Fase 3, entregues 3.1 (cards dinâmicos) e 3.2 (linha do tempo); da Fase 4, antecipado o 4.2 (toggle claro/escuro, a pedido do autor). Pendentes para v0.4: 3.3 (TZ por região/UF), 3.4 (dispersão), 3.5 (diferenciar os dois blocos de barras — mitigado com subtítulos), 4.1 (seções colapsáveis) e 4.3 (revisão mobile). Detalhes no CHANGELOG (v0.3) e checklist no FEEDBACK.md.

- **25/07/2026 — Versionamento formalizado (Opção A: remapeamento retroativo).** Adotado esquema semântico v0.x (prototipagem) → v1.0.0 (lançamento para grupos de pesquisa) → patch/minor/major pós-lançamento. As versões antes chamadas v1/v2/v3 foram renomeadas para v0.1/v0.2/v0.3 (mudança só de rótulo, no CHANGELOG, no selo da UI e neste ROADMAP) — sem isso, "v3" já publicado colidia com o "v0.2" que as anotações de planejamento do autor já usavam para descrever o mesmo painel. Política completa no CHANGELOG.md.

- **24/07/2026 — Glow descartado.** O "outer glow" nos municípios TZ (pedido do Ivan, 2×) não será usado — preferência estética do autor + risco de performance de filtros SVG. O objetivo por trás do pedido (destacar visualmente os TZ) será atendido com contorno/stroke destacado (item 2.3).
- **24/07/2026 — Auto-encaixe em vez de zoom/pan livre.** Entre zoom/pan manual e enquadramento automático pela seleção, escolhido o auto-encaixe (+ duplo clique para zoom local + botão de reset): resolve os dois casos relatados, é determinístico (prints reproduzíveis) e evita o conflito pinça×rolagem no celular. Zoom/pan livre adiado para a Fase 5.
- *(a preencher conforme as fases forem sendo implementadas — anotar versão/commit de cada item entregue, espelhando o checklist do FEEDBACK.md)*

- **26/07/2026 — Fases 7 e 8 criadas a partir do plano estratégico interno.** Identidade institucional/créditos (Fase 7) e repositório de estudos/enriquecimento (Fase 8) não tinham Fase própria; Fase 8 é a prioridade imediata. Detalhe da estratégia (contatos, cronograma de divulgação, escopo da Rede da ARS) fica em `estrategia-interna/PLANO-ESTRATEGICO.md` (não publicável) — este ROADMAP só registra as ações de produto derivadas dela.

- **26/07/2026 — Autorização do logo UFABC recebida; arquivos salvos em `assets/logos/ufabc/`.** Versão negativa (branco+amarelo, para fundo escuro) em SVG e EPS, 3 variantes de layout. Logo Laplan e versão para tema claro seguem pendentes (Fase 7.1b, 7.2b) — seção de créditos (7.3) só deve ser implementada depois dessas duas decisões, ou parcialmente com UFABC agora (a definir).

- **26/07/2026 — Fase 7 completa para UFABC.** Recebida também a versão principal (verde+amarelo, tema claro) — Fase 7.2b resolvida. Seção de créditos implementada no rodapé do Painel Brasil (logo troca com o tema, apoio técnico Polo Planejamento listado). Laplan aparece só como texto até a autorização (7.1b) chegar.

- **26/07/2026 — Escopo da Rede da ARS confirmado; Fase 9 criada.** É a rede societária/CNPJ (não monitoramento de redes sociais, como uma leitura do brainstorm original sugeria). Primeiro rascunho recebido e guardado em `rede-ge-rascunho/` (fora do git, não publicável ainda). Achado: o rascunho usa a paleta oficial da identidade visual corretamente; `painel.html`/`index.html` é que estão com uma paleta antiga levemente diferente — a correção de cor deve ir no sentido painel→identidade, não o inverso.

- **26/07/2026 — Logo PGT recriado; análise técnica da Fase 9 concluída.** Arquivo original do PGT (184×110px, jpg comprimido) estava ilegível — recriado como SVG vetorial fiel (monograma PG/T + versão estendida com o nome do programa), nas variantes negativa/principal, salvo em `assets/logos/pgt/` e já incluído na seção de créditos junto com UFABC. Análise do rascunho da Rede da ARS: arquitetura de renderização (canvas + quadtree + RAF em lotes) já é sólida; os problemas reais são peso do JSON (formato não-colunar) e layout de força recalculado no navegador a cada carga — ambos resolvíveis pré-processando dados/posições em build, no mesmo espírito do Painel Brasil. Redesenho estrutural (rede como "janela" num dashboard, não tela cheia) é o maior item pendente da Fase 9 — ainda não iniciado.

- **26/07/2026 — `pesquisa.html` incorpora campos do antigo MS Form.** Levantada a estrutura completa do formulário "Mapeamento Bibliográfico sobre Tarifa Zero no Brasil" (Microsoft Forms, 3 páginas). Decisão: usar só como referência de campos (Autoras, Ano de publicação, Foco principal do texto, Empresas/grupos econômicos citados), incorporados ao formulário único já existente em `pesquisa.html` — não replicar a ramificação por tipo de documento nem a divisão em páginas do MS Form, que é mais restrita (só bibliografia) e está ela mesma incompleta (campo de tipo de documento com uma única opção; uma pergunta sem título). Alternativas consideradas e descartadas: substituir o form genérico pela estrutura bibliográfica inteira; ou ramificar campos por "Tipo de contribuição".

- **26/07/2026 — Logo Polo Planejamento recebido e implementado.** Duas variantes da marca "POLO TC" (TC é uma submarca da Polo Planejamento) (negativa/branco para fundo escuro, colorida/principal — laranja `#ef7720`, cinza `#46494a`, azul `#2997c1` — para fundo claro), salvas em `assets/logos/polo/{negativo,principal}/logo-polo-{negativo,principal}.svg` e incluídas na seção de créditos (`head.html`/`painel.html`) ao lado de UFABC e PGT, com troca automática pelo toggle de tema. Com isso, o único logo pendente da Fase 7 volta a ser só o da Laplan (7.1b). *Nota: o build completo (`montar_html.sh`) não roda neste ambiente por faltarem os JSONs intermediários (`build/geo.topojson`, `stats.json`, `municipios_dados_col.json`, fora do git) — a mudança foi replicada manualmente e de forma idêntica em `head.html` (fonte) e `painel.html` (publicado); confirmar consistência na próxima rodada de build local.*

- **26/07/2026 — Logo PGT (sigla) corrigido; rodapé reestruturado.** O autor apontou que a reconstrução anterior do PGT (23/07 — texto solto em Poppins simulando o monograma) "ficou ruim". Em vez de tentar uma segunda reconstrução livre, foram usados dois arquivos originais recém-enviados: `ppgt_300-1.png` (versão negativa oficial, 300×300, branco monocromático) para extrair a silhueta real do monograma em boa resolução, e `Prancheta_1dialogiod.jpg` (184×110 — o mesmo arquivo já registrado como "ilegível" nesta ROADMAP) só para inferir a divisão de cor (P+G em vermelho `#E5322C`, T em preto), já que nele o desenho é o mesmo mas em baixíssima resolução. O resultado é um PNG (não SVG): tentou-se vetorizar via ferramenta Adobe, mas ela exige URL pública para a imagem de entrada, indisponível neste ambiente; não havia `potrace` nem permissão de root no sandbox para instalar. Ficou registrado como pendência caso se queira uma versão vetorial no futuro (precisaria rodar localmente ou hospedar a imagem publicamente). Os SVGs antigos (fake) não foram apagados, só deixaram de ser referenciados. Aproveitando a rodada, o autor pediu também: (a) logos maiores no rodapé (24px→34px/30px) e (b) os logos institucionais (UFABC, PGT, Laplan) na mesma linha do nome do autor e da orientadora, com o logo da Polo + "Apoio técnico" isolados numa linha própria abaixo — ambos implementados em `head.html` e replicados manualmente em `painel.html` (o build via `montar_html.sh` não roda neste ambiente, faltam os JSONs intermediários — mesma ressalva já registrada na entrada do logo da Polo).

- **26/07/2026 — Rodapé simplificado: nome/orientadora em uma linha cada, versão movida para junto das fontes.** Texto "Doutorado em Planejamento e Gestão do Território / PPG-PGT · UFABC" removido do bloco do autor — essa informação agora é transmitida pelos logos (UFABC + PGT) já presentes na mesma linha. Blocos viram só "Thiago Von Zeidler Gomes · Doutorando" e "Prof.ª Dr.ª Silvana Maria Zioni · Orientadora" (nome em negrito, cargo depois, separados por "·" — mantendo o separador já usado no resto do rodapé em vez do "|" mencionado informalmente pelo autor). "Painel v0.3 · 2026" saiu do bloco da orientadora e foi para a linha de fontes, no rodapé mais abaixo.

- **26/07/2026 — ROADMAP reestruturado por página; `pesquisa.html` confirmado como 4ª página de desenvolvimento.** Backlog reorganizado em torno das 4 páginas do site (Seções 1–3, mais a Seção 4 cross-page de identidade institucional) em vez de uma lista única de fases; números de Fase originais preservados. Decisão de escopo sobre o Form: **navegação** continua como camada/CTA a partir do Painel Brasil (sem card próprio no hub `index.html` por enquanto — isso fica para uma decisão futura, se e quando fizer sentido promovê-lo), mas **desenvolvimento** passa a tratar `pesquisa.html` como página independente nesta ROADMAP, com seu próprio backlog (Seção 3) e, futuramente, seu próprio versionamento — pelo mesmo motivo que já se aplica a `painel.html` e `rede-ge.html`.

- **26/07/2026 — Rodapé de créditos ainda "muito ruim" no print; logo da Polo trocado por versão só "POLO" após checar o manual oficial.** O autor mandou um print do rodapé já com as correções desta rodada e considerou o resultado ainda fraco, apontando dois problemas concretos: o vão enorme entre os logos institucionais e o nome da orientadora (efeito de `justify-content:space-between` com 3 blocos numa linha larga), e a marca da Polo ilegível (o "TC" virando um borrão). Em vez de tentar mais um ajuste de tamanho/CSS às cegas, o autor mandou o manual de identidade da Polo (`AF POLO-TC MANUAL-IDENTIDADE v3.8.pdf`, 66 páginas) para checar a forma correta. Achados (p.11 e 55-57): a marca "POLO" (ícone + palavra) tem tamanho mínimo definido e documentado (35px de largura digital); o "TC" faz parte de **TcUrbes**, uma submarca de serviço da Polo com ícone e regras próprias, usada em conjunto com a POLO só em contextos específicos (não é uma "sigla" da Polo, como presumido antes) — o arquivo enviado já veio com as duas coladas, por isso o "TC" nunca teria tamanho legível num rodapé pequeno, não importa o quanto se aumentasse. Correções: (1) logo da Polo recortado para usar só ícone+"POLO" (extraído do SVG oficial, sem redesenhar formas), resolvendo a ilegibilidade na raiz em vez de só aumentar o tamanho; (2) layout da linha institucional reagrupado — nome do autor e logos (UFABC/PGT/Laplan) viraram um bloco único à esquerda (`.fleft`), com a orientadora sozinha à direita, eliminando o vão duplo. Replicado em `head.html` e `painel.html` (mesma ressalva de build manual já registrada acima).

- **26/07/2026 — Linha de logos institucionais e de apoio técnico replicadas em todas as páginas.** A pedido do autor, o bloco de créditos (UFABC + PGT + Laplan, e Polo + "Apoio técnico") deixou de ser exclusivo do Painel Brasil e passou a aparecer também em `index.html` (hub) e `pesquisa.html` (Form) — as únicas 3 páginas hoje publicadas/em uso. Informação específica de cada página (linha de fontes de dados e versão do Painel Brasil) não foi replicada, só o bloco de créditos institucionais. Como `index.html` e `pesquisa.html` não têm toggle claro/escuro, mostram sempre a versão negativa dos logos, sem a lógica `html[data-theme="light"]` (que só existe no Painel Brasil).

- **26/07/2026 — Paleta do Painel Brasil corrigida para a identidade oficial (Fase 9.1) + status "Ativa" virou verde + seções colapsáveis (Fase 4.1).** Numa mesma rodada de ajustes estéticos pedida pelo autor: (1) `--rosa`/`--amarelo`/`--azul` trocados dos hex antigos (`#f43f6f`/`#ffd400`/`#2b50d9`) para os oficiais (`#FF2D6B`/`#F5E400`/`#1A54C7`), `--verde` (`#6FBE44`) adicionado, `--bg` alinhado a `#0E0E10` — em `head.html`, `logic.js`, `painel.html` e também `index.html` (que tinha a mesma paleta antiga, não coberta pela Fase 9.1 original mas corrigida por consistência); (2) municípios com situação "Ativa" (mapa, tabela, tags, gráfico de linha do tempo) passaram de amarelo para verde — `TZ_COLORS_HEX`, `tzUi()` e as variáveis `--tz-ativa`/`--tz-outline`/`--tag-ativa-fg` atualizadas em `logic.js` e nos dois HTMLs; rosa passou a marcar exclusivamente "Encerrada". Variantes de tema claro recalculadas para contraste (`#2e7d32` como verde escurecido, substituindo o `#a68a00`/`#8a6d00` do amarelo escurecido); (3) as 4 seções indicadas no item 4.1 (comparação, % por eixo, glossário — já colapsável antes —, notas) viraram `<details>/<summary>` abertos por padrão, reaproveitando o estilo de `.panel h2`. Todas as mudanças replicadas identicamente em `head.html` (fonte) e `painel.html` (publicado), já que o build via `montar_html.sh` não roda neste ambiente.

- **26/07/2026 — CTA de contribuição adicionado ao Painel Brasil (Fase 6.1).** Bloco `.cta-pesquisa` inserido como rodapé da tabela de casos TZ (dentro do mesmo painel, logo abaixo de `#tzTable`), com o texto "Não achou seu município na lista, ou tem um estudo, dado ou caso que devêssemos considerar?" e botão apontando para `pesquisa.html`. Replicado manualmente em `head.html` (fonte) e `painel.html` (publicado), já que o build via `montar_html.sh` não roda neste ambiente (mesma ressalva de outras entradas desta seção). Cor do botão usa `var(--rosa)` da paleta atual do painel (ainda não corrigida para a identidade oficial — pendência já registrada na Fase 9.1).

- **26/07/2026 — v0.4: Fase 8 (repositório de fontes) implementada + 2 gráficos novos; escore de grupo econômico deliberadamente deixado de fora.** Ao revisar o painel com o autor após os ajustes estéticos, três decisões: (1) o escore `cnpj_nucleo_*` (variável-teste da hipótese central, preliminar — 11 grupos, pendência aberta da fusão Barata/Pekin-Constantino) **não entra no painel agora** — autor pediu para esperar a pendência fechar antes de expor essa variável publicamente; (2) Fase 8 implementada com as 3 formas de exibição de fontes por município simultâneas (coluna+expansão na tabela, card lateral, painel-repositório), para decidir depois qual manter; (3) dos dados novos da base (matriz modal Censo 2022, série de motorização/frota 2013-2022), ambos viraram gráfico novo no painel — ver v0.4 no CHANGELOG.md para o detalhe técnico. Pendência de `cnpj_nucleo_*` registrada em [[Pendências]] (cofre da tese) para reavaliar quando a checagem de clusterização fechar.

- **27/07/2026 — v0.4 (2ª passagem, mesmo dia): correções após primeiro uso real do painel.** Ao usar o painel pela primeira vez, o autor pediu uma sequência de reversões e ajustes que resolvem as 3 opções deixadas em aberto na Fase 8 e corrigem decisões estéticas da 1ª passagem — mantido como v0.4 (não subiu para v0.5; ainda é a mesma rodada de ajustes estéticos + Fase 8 do dia): (1) "Ativa" volta de verde para amarelo (a paleta oficial se mantém — só a escolha de cor por status é revertida); (2) das 3 formas de exibição de fontes testadas, o painel "Repositório de fontes por município" foi removido, mantendo coluna+expansão na tabela e card de detalhe; em seu lugar entrou um bloco de referências ABNT dos estudos acadêmicos citados (Santini 2019, Pereira 2023, Angelo 2023, Vermander 2021, Brinco 2017 — citekeys conferidos em `biblioteca.bib`); (3) os dois gráficos testados na 1ª passagem (evolução da motorização; meio de transporte por barras separadas) foram descartados e substituídos por um único gráfico de partição modal em barra 100% empilhada, destacando Ônibus (azul) e Ativo=a pé+bicicleta (rosa) — únicas cores da identidade usadas, sem combinar com amarelo/verde; (4) tema claro removido (painel passa a ser só escuro); (5) logo do PGT trocado da sigla raster para o logotipo extenso oficial em SVG, e todos os logos do rodapé ampliados; (6) no card de município, "PDMU (2025)"→"PlanMob (2025)" e "Tarifa reconciliada"→"Tarifa" (mostrando "Gratuito (TZ universal)" quando ativa); (7) card "TZ ativas" agora explicita "universal", novo card "TZ parciais" (32, exclui as 324 gratuidades eleitorais/eventuais por serem fenômeno distinto), card "TZ encerradas" e filtro "Sede × satélite" removidos do topo; (8) citação pública restrita a artigos acadêmicos — coluna "Fontes" da tabela e card de detalhe passam a filtrar `fontesFor()` para tipo "Estudo acadêmico" apenas (38 municípios, 69 entradas), excluindo relatórios institucionais (NTU), reportagens de jornal/revista e levantamentos de coleta própria (planilha "Municípios com FFPT") — o crosswalk bruto (`casos_por_fonte.json`, 181 entradas) não muda, só o que é exibido/citado no painel. Ver v0.4 no CHANGELOG.md.

- **26/07/2026 — Ajustes de UX no formulário antes do teste com usuários.** Testando `pesquisa.html` antes de enviar para testadores humanos, o autor apontou três pontos: (1) o aviso "Rascunho de conteúdo" no topo não devia aparecer para quem vai testar o formulário de verdade — removido do HTML a pedido do autor (item 2.2 antecipado; a revisão de texto em si, item 2.1, segue pendente); (2) a mensagem de sucesso do Formspree aparecia em inglês ("Thank you!") e só a borda usava o verde da identidade, o texto ficava branco — corrigido via callback `renderSuccess` do `@formspree/ajax` (a lib preenche o `data-fs-success` com texto próprio em runtime, não dava pra sobrescrever só com HTML estático) para exibir texto em português com a cor de texto também em verde (`var(--verde)`); (3) não havia campo de upload de arquivo — adicionado `<input type="file" name="arquivo">` (aceita PDF/DOC/XLS/PPT/CSV, até 25 MB) e `enctype="multipart/form-data"` no `<form>`, confirmado com o autor que o plano do Formspree é pago (upload de arquivo não existe no plano gratuito).

- **26/07/2026 — Formulário de `pesquisa.html` ativado.** O autor criou o endpoint no Formspree (`https://formspree.io/f/xpqvkqnk`) e pediu para integrar seguindo o guia mais adequado ao ambiente. Escolhida a integração **Vanilla JS/AJAX** (`@formspree/ajax`, via CDN, sem bundler) em vez de "Basic HTML" (recarregaria a página inteira no domínio formspree.io, quebrando a identidade visual) ou React (o repositório não usa framework/bundler nenhum — é HTML/CSS/JS puro publicado no GitHub Pages). `action`/`method` do `<form>` continuam apontando pro endpoint como fallback se o JS não carregar. Adicionados atributos `data-fs-field`/`data-fs-error` nos 4 campos obrigatórios (nome, e-mail, título, descrição) e um bloco de sucesso/erro no topo do formulário, estilizados com as cores da identidade em vez do CSS padrão da biblioteca. O aviso de "envio ainda não está ativo" foi removido do topo da página — o aviso de conteúdo-rascunho (Fase 2, ainda pendente) foi mantido. Falta testar o envio ponta a ponta (item 1.2) — não fiz um envio de teste sem perguntar, já que isso geraria uma notificação real na caixa do autor.
