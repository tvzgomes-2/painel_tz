# Análise e plano de melhorias — Painel TZ

Nota de planejamento do projeto. Consolida a análise técnica do painel v0.2, o feedback recebido de 5 leitores ([`FEEDBACK.md`](./FEEDBACK.md)) e o pedido da orientadora (mais gráficos e grandes números). Organizada em fases priorizadas por consenso × esforço.

*Escrita em 24/07/2026. Painel analisado: v0.2 (publicado em https://tvzgomes-2.github.io/painel_tz/).*

---

## 0. Arquitetura do site *(decidido 25/07/2026)*

O repositório passou de "um painel" para **um site com páginas independentes**, cada uma com seu próprio banco de dados e seu próprio número de versão:

- **`index.html`** — hub do site. Página pequena, editada à mão (não gerada por script), com o resumo da pesquisa e um card de acesso por página. Mostra só as páginas já publicadas.
- **`painel.html`** (tag **TZ**, "Painel Brasil") — panorama nacional de Tarifa Zero. É o que antes se chamava `index.html`; todo o conteúdo deste ROADMAP (Fases 1-5) é sobre esta página especificamente. Gerado por `scripts/montar_html.sh`, não editar direto.
- **`rede-ge.html`** (tag **GE**, "Rede da ARS", planejado) — estrutura de poder dos grupos econômicos do transporte coletivo (rede societária/CNPJ da tese). Ainda não construído; só aparece no hub quando estiver pronto para publicar (sem placeholder "em construção" clicável — o card já existe no hub, mas sem link, para sinalizar que vem por aí).
- **Pesquisa de novos casos** — não é uma página/botão do hub. Vira uma chamada contextual *dentro* do Painel Brasil (ex.: ao navegar pelos casos municipais, um link tipo "não achou seu município? envie um novo caso ou estudo"), acionada só quando alguém quiser contribuir. Fica como item da Fase 6 (abaixo) até o formulário (Frente 1 das anotações de planejamento) ser redesenhado.

**Versionamento:** a regra em `VERSIONING.md` é uma só, mas cada página conta seu próprio número (Painel Brasil segue de v0.3; Rede da ARS começa do zero quando existir). O site como um todo não tem número de versão — tem uma **era**, nomeada com modo de transporte em ordem alfabética (**Era Andarilho**, letra A, é a atual), trocada só quando acontece um evento "major" na definição do VERSIONING.md (novo painel irmão publicado, ou redesign completo de alguma página).

## 1. Diagnóstico do estado atual

### O que está funcionando (confirmado pelo feedback)

- **Ordenação por clique na tabela TZ** — elogiada explicitamente (Carol); manter.
- **Notas metodológicas** — apontadas como diferencial útil (Gabriel); manter e não cortar.
- **Legibilidade geral dos dados** — "bem fáceis de analisar" (Gabriel), "ficou muito bom" (Ivan).
- **Arquitetura de arquivo único** — abre em qualquer navegador, publica como página estática, zero dependência.

### Fragilidades identificadas (feedback + análise técnica)

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

---

## 2. Plano de melhorias por fase

Critério de priorização: nº de pessoas que pediram × valor analítico × esforço técnico. Fases 1–2 são pré-requisito de qualidade; a Fase 3 é o pedido da orientadora e a maior entrega de valor novo.

### Fase 1 — Legibilidade e correções rápidas *(só CSS/texto; esforço baixo)*

| # | Item | Origem |
|---|------|--------|
| 1.1 | Título maior + acrescentar "(TZ)" após "Tarifa Zero" | Ivan (2×) |
| 1.2 | Títulos de seção maiores/negrito (h2 e o "TZ × Não-TZ") | Carol, Gabriel |
| 1.3 | Alinhar cards de resumo com a linha de controles (mesmo grid) | Carol |
| 1.4 | Bloco "% por eixo": subtítulo explicando que a % é calculada dentro de cada categoria; reposicionar rótulo→barra sem ambiguidade | Daniel |
| 1.5 | Glossário de siglas (IBEU, IDH, PDMU, REGIC, NTU, arranjo) — painel colapsável antes das notas metodológicas | Ricardo |
| 1.6 | Mais respiro entre mapa e painel lateral (gap do grid) | Gabriel |

### Fase 2 — Mapa *(o bloco mais criticado; esforço médio)*

| # | Item | Nota técnica |
|---|------|--------------|
| 2.1 | **Bordas estaduais sempre visíveis** | Derivar camada de UF dissolvendo os municípios no mapshaper (`-dissolve`) — acréscimo estimado de ~100–200 KB no topojson; desenhar como camada de linha acima dos municípios |
| 2.2 | Bordas municipais mais claras (stroke mais visível) | Só CSS |
| 2.3 | Destaque dos municípios TZ **sem glow** (decisão do autor, 24/07/2026): usar borda/stroke mais forte e clara nos TZ ativos | Substitui o "outer glow" pedido pelo Ivan — glow descartado por preferência estética e risco de performance; o objetivo dele (TZ saltar aos olhos, tirar a "cara de Excel") é atendido por contorno destacado |
| 2.4 | **Auto-encaixe do mapa na seleção** (decisão do autor, 24/07/2026 — no lugar de zoom/pan livre): ao filtrar uma UF, o mapa enquadra automaticamente a UF; duplo clique num município dá zoom local; botão "↺ Brasil" volta ao enquadramento nacional | Animação do viewBox pro bounding box do recorte; determinístico (todos veem o mesmo enquadramento, prints reproduzíveis), sem conflito pinça×rolagem no celular; resolve os dois casos relatados (Daniel e Ricardo) |
| 2.5 | Tooltip completo nos municípios TZ (situação, início, REGIC, arranjo, pop, PIB pc, motorização) | Reusar os dados já embutidos |
| 2.6 | Suprimir tooltip/hover fora do recorte quando há filtro ativo | Checagem no handler de mousemove |

### Fase 3 — Grandes números e novos gráficos *(pedido da orientadora; esforço médio-alto, maior valor novo)*

| # | Item | Detalhe |
|---|------|---------|
| 3.1 | **Cards dinâmicos (grandes números que reagem ao recorte)** | Ao filtrar UF/faixa/REGIC, os cards recalculam: nº de municípios no recorte, nº TZ ativas, % TZ, **população vivendo com TZ** (soma da pop dos municípios ativos — número forte para apresentações), PIB pc mediano do recorte |
| 3.2 | **Linha do tempo de adoções** | Gráfico de barras/linha por ano de início (`tz_ano`), com revogações marcadas — mostra a aceleração recente da política, hoje invisível no painel |
| 3.3 | TZ por região e por UF | Barras horizontais simples (contagem + %), completando os eixos já existentes |
| 3.4 | Gráfico de dispersão PIB pc × motorização | Pontos = municípios, TZ destacados em cor — visualiza a comparação que hoje só existe como mediana em barra |
| 3.5 | Diferenciar visualmente os dois blocos de barras | Trocar a forma de um deles (ex.: % por eixo vira dot plot ou barras com escala explícita 0–100%) para separar "comparação pareada" de "proporção por categoria" (Daniel) |

### Fase 4 — Estrutura e conforto *(esforço baixo-médio)*

| # | Item |
|---|------|
| 4.1 | Seções colapsáveis (comparação, % por eixo, glossário, notas) — permite ver mapa + tabela juntos (Ivan) |
| 4.2 | Toggle tema claro/escuro (preferência do Gabriel vira opção sem impor a ninguém) |
| 4.3 | Revisão mobile: painel foi lido no celular (print do Ivan) — conferir touch no mapa, tabela com rolagem horizontal |

### Fase 5 — Dados futuros e melhorias adiadas *(fora do escopo imediato)*

- Zoom/pan livre no mapa (roda do mouse/pinça + arrastar) — adiado em favor do auto-encaixe (item 2.4); reavaliar só se leitores sentirem falta de exploração livre após a Fase 2.
- Viagens antes × depois da adoção (Ivan) — exige série temporal de demanda por município; não existe na base.
- Investimento em infra antes × depois (Ivan) — idem, possível recorte via FINBRA série 2019–2023 já coletada (explorar antes de descartar).
- **Variável de presença de grupo econômico por município** (rede ARS/CNPJ) — quando integrada, vira o eixo central do painel e o teste da hipótese da tese.
- Correções na fonte: duplicata Palmas-TO e situação de São Caetano do Sul (base-mestre).

### Fase 6 — Integração com o site *(depende da Fase 0; esforço a estimar)*

| # | Item | Depende de |
|---|------|-----------|
| 6.1 | CTA contextual "não achou seu município? envie um novo caso ou estudo" dentro do painel (ex.: no painel de detalhe do município, ou como rodapé da tabela de casos) | Formulário de coleta redesenhado (Frente 1 das anotações de planejamento) — hoje só existe a versão antiga em Microsoft Forms |
| 6.2 | Link cruzado para a Rede da ARS quando ela existir (ex.: ao ver um município TZ, mostrar se algum grupo econômico mapeado atua ali) | Página `rede-ge.html` publicada |

### Fase 7 — Identidade institucional e créditos *(depende de autorização externa; ver plano estratégico interno)*

| # | Item | Depende de |
|---|------|-----------|
| 7.1 | Obter autorização da orientadora para uso dos logos UFABC e Laplan (cor, restrição de tamanho) | Confirmação da Prof.ª Silvana Zioni |
| 7.2 | Baixar logos em versão branca/transparente (PNG ou SVG) | 7.1 |
| 7.3 | Seção de créditos no Painel Brasil: autoria, orientação, instituições de apoio (UFABC, Laplan), apoio técnico (Polo Planejamento), fonte de dados | 7.1, 7.2 |
| 7.4 | Decidir se os logos institucionais ficam fora da paleta autoral (preto/rosa + 1 cor) — provavelmente rodapé neutro, não misturado com a identidade visual da pesquisa | — |

### Fase 8 — Repositório de estudos e enriquecimento *(próxima fase prioritária, 26/07/2026)*

| # | Item | Depende de |
|---|------|-----------|
| 8.1 | Mapear qual estudo acadêmico/grey literature (NTU, Ministério das Cidades etc.) pesquisa qual município | — |
| 8.2 | Validar se a base atual suporta a relação N:N estudo↔município; se precisar mudar estrutura, sobe **minor** (ver VERSIONING.md) | 8.1 |
| 8.3 | Desenhar a visualização no painel (ex.: "este município tem N estudos vinculados", com lista) | 8.2 |

---

## 3. Riscos e cuidados

- **Tamanho do arquivo:** hoje 4,4 MB; camada de UF e novos gráficos acrescentam pouco (~5%), mas monitorar — o limite prático de conforto em 4G é ~10 MB.
- **Auto-encaixe × tooltip:** com o viewBox mudando no auto-encaixe/duplo clique, recalibrar posição do tooltip e hit-areas.
- **Não perder o que funciona:** ordenação da tabela, notas metodológicas e arquitetura de arquivo único são elogiados — nenhuma fase deve sacrificá-los.
- **Cards dinâmicos e n pequeno:** ao filtrar recortes com poucos municípios TZ (ex. uma UF com 1–2 casos), os grandes números podem sugerir robustez que não existe — exibir sempre o `n` junto e, abaixo de um limiar, sinalizar "amostra pequena".

## 4. Registro de decisões

- **24/07/2026 — v0.3 entregue.** Fase 1 completa; Fase 2 completa (com contorno no lugar do glow e auto-encaixe no lugar de zoom/pan); da Fase 3, entregues 3.1 (cards dinâmicos) e 3.2 (linha do tempo); da Fase 4, antecipado o 4.2 (toggle claro/escuro, a pedido do autor). Pendentes para v0.4: 3.3 (TZ por região/UF), 3.4 (dispersão), 3.5 (diferenciar os dois blocos de barras — mitigado com subtítulos), 4.1 (seções colapsáveis) e 4.3 (revisão mobile). Detalhes no CHANGELOG (v0.3) e checklist no FEEDBACK.md.

- **25/07/2026 — Versionamento formalizado (Opção A: remapeamento retroativo).** Adotado esquema semântico v0.x (prototipagem) → v1.0.0 (lançamento para grupos de pesquisa) → patch/minor/major pós-lançamento. As versões antes chamadas v1/v2/v3 foram renomeadas para v0.1/v0.2/v0.3 (mudança só de rótulo, no CHANGELOG, no selo da UI e neste ROADMAP) — sem isso, "v3" já publicado colidia com o "v0.2" que as anotações de planejamento do autor já usavam para descrever o mesmo painel. Política completa no CHANGELOG.md.

- **24/07/2026 — Glow descartado.** O "outer glow" nos municípios TZ (pedido do Ivan, 2×) não será usado — preferência estética do autor + risco de performance de filtros SVG. O objetivo por trás do pedido (destacar visualmente os TZ) será atendido com contorno/stroke destacado (item 2.3).
- **24/07/2026 — Auto-encaixe em vez de zoom/pan livre.** Entre zoom/pan manual e enquadramento automático pela seleção, escolhido o auto-encaixe (+ duplo clique para zoom local + botão de reset): resolve os dois casos relatados, é determinístico (prints reproduzíveis) e evita o conflito pinça×rolagem no celular. Zoom/pan livre adiado para a Fase 5.
- *(a preencher conforme as fases forem sendo implementadas — anotar versão/commit de cada item entregue, espelhando o checklist do FEEDBACK.md)*

- **26/07/2026 — Fases 7 e 8 criadas a partir do plano estratégico interno.** Identidade institucional/créditos (Fase 7) e repositório de estudos/enriquecimento (Fase 8) não tinham Fase própria; Fase 8 é a prioridade imediata. Detalhe da estratégia (contatos, cronograma de divulgação, escopo da Rede da ARS) fica em `estrategia-interna/PLANO-ESTRATEGICO.md` (não publicável) — este ROADMAP só registra as ações de produto derivadas dela.
